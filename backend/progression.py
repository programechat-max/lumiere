"""
Progressive overload motoru.
Bu bilinçli olarak AI'ye değil, sabit bir kurala dayanıyor: "hedef tekrar aralığının
üstüne çıktıysan ağırlığı artır" fitness'ta iyi bilinen, güvenilir bir prensiptir.
AI yorumu (ai_core.generate_weekly_analysis) bunu tamamlar ama karar buradan çıkar.
"""
import re
from sqlalchemy.orm import Session

import crud

# Ağırlığı artırırken yuvarlanacak en küçük birim (kg)
WEIGHT_INCREMENT = 2.5


def _parse_rep_range(target_reps: str):
    """'8-12' -> (8, 12). Tek sayı ise (n, n). Parse edilemezse None."""
    if not target_reps:
        return None
    match = re.findall(r"\d+", target_reps)
    if not match:
        return None
    if len(match) == 1:
        return int(match[0]), int(match[0])
    return int(match[0]), int(match[-1])


def suggest_for_exercise(db: Session, exercise_name: str, target_reps: str, user_id: int = None):
    """Tek bir hareket için son antrenman verisine bakıp öneri üretir."""
    logs = crud.get_last_session_logs_for_exercise(db, exercise_name, user_id=user_id)
    rep_range = _parse_rep_range(target_reps)

    if not logs:
        return {
            "exercise_name": exercise_name,
            "status": "no_data",
            "message": "Henüz kayıt yok - ilk antrenmanını gir, oradan devam ederiz.",
        }

    last_date = str(logs[0].date)
    last_weight = max((l.weight_lifted or 0) for l in logs)
    reps_list = [l.reps_done or 0 for l in logs]
    min_reps = min(reps_list)

    if rep_range is None:
        return {
            "exercise_name": exercise_name,
            "status": "unknown_range",
            "last_date": last_date,
            "last_weight": last_weight,
            "message": f"Son antrenman: {last_weight}kg. Hedef tekrar aralığı tanımlı değil, karşılaştırma yapılamıyor.",
        }

    low, high = rep_range

    if min_reps >= high:
        # Tüm setlerde üst sınıra ulaşılmış veya geçilmiş -> ağırlığı artır
        new_weight = last_weight + WEIGHT_INCREMENT if last_weight else last_weight
        return {
            "exercise_name": exercise_name,
            "status": "increase_weight",
            "last_date": last_date,
            "last_weight": last_weight,
            "suggested_weight": new_weight,
            "message": (
                f"Son antrenmanda {last_weight}kg ile tüm setlerde {high}+ tekrara ulaştın. "
                f"Bir sonraki antrenmanda {new_weight}kg dene, tekrarı {low}'a düşür."
            ),
        }
    elif min_reps < low:
        return {
            "exercise_name": exercise_name,
            "status": "hold_weight",
            "last_date": last_date,
            "last_weight": last_weight,
            "suggested_weight": last_weight,
            "message": (
                f"Son antrenmanda {last_weight}kg ile hedef tekrarın ({low}) altında kaldın. "
                f"Aynı ağırlıkta kal, önce tekrar hedefini yakala."
            ),
        }
    else:
        return {
            "exercise_name": exercise_name,
            "status": "add_reps",
            "last_date": last_date,
            "last_weight": last_weight,
            "suggested_weight": last_weight,
            "message": (
                f"Son antrenmanda {last_weight}kg ile aralık içindesin. Aynı ağırlıkta kal, "
                f"bu sefer bir set daha fazla tekrar yapmayı hedefle."
            ),
        }


def get_all_suggestions(db: Session, user_id: int = None):
    """Aktif programdaki tüm hareketler için önerileri toplar."""
    programs = crud.get_workout_programs(db, user_id)
    suggestions = []
    seen = set()
    for program in programs:
        for ex in program.exercises:
            key = ex.name.lower()
            if key in seen:
                continue
            seen.add(key)
            suggestions.append(suggest_for_exercise(db, ex.name, ex.target_reps, user_id))
    return suggestions


# Deload tespiti eşikleri - bilinen fitness prensiplerine dayanır:
# ard arda 3 antrenmanda ağırlık artmıyorsa (stagnasyon) veya ortalama RPE çok
# yüksekse (aşırı yorgunluk), vücut toparlanamıyor demektir - hafifletme haftası gerekir.
DELOAD_SESSION_COUNT = 3
DELOAD_HIGH_RPE_THRESHOLD = 8.5


def check_deload_needed(db: Session, user_id: int = None):
    """Aktif programdaki her hareket için son birkaç antrenumanı inceleyip genel bir
    deload (hafifletme haftası) önerisi gerekip gerekmediğini kontrol eder.
    Kural tabanlı - AI yorumuna değil gerçek veriye dayanır."""
    programs = crud.get_workout_programs(db, user_id)
    exercise_names = set()
    for program in programs:
        for ex in program.exercises:
            exercise_names.add(ex.name)

    stagnant_exercises = []
    high_fatigue_exercises = []

    for name in exercise_names:
        sessions = crud.get_recent_sessions_for_exercise(db, name, session_count=DELOAD_SESSION_COUNT, user_id=user_id)
        if len(sessions) < DELOAD_SESSION_COUNT:
            continue  # Yeterli geçmiş yok, değerlendirme yapılamaz

        session_max_weights = []
        all_rpes = []
        for session_date, logs in sessions.items():
            session_max_weights.append(max((l.weight_lifted or 0) for l in logs))
            all_rpes.extend(l.rpe for l in logs if l.rpe is not None)

        # Stagnasyon: en yeni antrenmandaki ağırlık, en eski antrenmandakinden yüksek DEĞİLSE
        # (session_max_weights sıralaması en yeniden en eskiye)
        if session_max_weights[0] <= session_max_weights[-1]:
            stagnant_exercises.append(name)

        if all_rpes:
            avg_rpe = sum(all_rpes) / len(all_rpes)
            if avg_rpe >= DELOAD_HIGH_RPE_THRESHOLD:
                high_fatigue_exercises.append((name, round(avg_rpe, 1)))

    needs_deload = len(stagnant_exercises) >= 2 or len(high_fatigue_exercises) >= 2

    return {
        "needs_deload": needs_deload,
        "stagnant_exercises": stagnant_exercises,
        "high_fatigue_exercises": high_fatigue_exercises,
    }
