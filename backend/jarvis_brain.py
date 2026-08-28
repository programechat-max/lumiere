"""
Jarvis Zeka Katmanı — ham Gemini API'sinin üzerine inşa edilen güçlendirme motoru.

Bu modül API'yi "100 kat güçlü" kılan şeyler:
1. CANLI VERİ SNAPSHOT'I — profil değil, bugünün gerçek makroları/antrenmanı/ilerlemesi
2. AKILLI HAFIZA RETRIEVAL — 40 kaydın hepsini değil, mesaja en alakalı 15'ini seçer
3. SOHBET GEÇMİŞİ — son N mesaj bağlamda kalır, Jarvis konuşmayı unutmaz
4. ÇİFT AŞAMALI YANIT — intent işlendikten sonra koçluk zenginleştirmesi
5. OTOMATİK HAFIZA ÇIKARIMI — her sohbetten gizli tercih/not madenciliği
6. PROAKTİF BRİEFİNG — açılışta durum özeti + öneriler
7. HAZIRLIK SKORU — check-in + veri ile bugün ağır mı hafif mi antrenman
"""
import json
import logging
import re
from datetime import date, datetime, timedelta

import crud
import progression

logger = logging.getLogger(__name__)

# Paylaşılan GenAI client ve sarmalayıcı
from genai_client import MODEL_NAME, _GenerativeModel

# Mesaj içeriğine göre hangi hafıza kategorileri öncelikli
CATEGORY_BOOST = {
    "food": {"preference": 3, "note": 2, "insight": 1},
    "workout": {"preference": 2, "insight": 2, "physique_analysis": 3, "note": 1},
    "injury": {"preference": 3, "note": 3, "physique_analysis": 2},
    "sleep": {"note": 3, "preference": 2},
    "general": {"preference": 2, "insight": 2, "analysis": 1, "note": 1},
}

FOOD_WORDS = {"yemek", "öğün", "kalori", "protein", "kahvaltı", "öğle", "akşam", "yedi", "yedim", "tarif", "beslenme", "makro", "karb", "yağ"}
WORKOUT_WORDS = {"antrenman", "set", "tekrar", "ağırlık", "bench", "squat", "deadlift", "program", "spor", "kas", "hareket", "salon", "deload"}
INJURY_WORDS = {"sakat", "ağrı", "diz", "omuz", "bel", "incinme", "kısıt"}
SLEEP_WORDS = {"uyku", "yorgun", "dinlen", "uyandım", "gece"}


def _tokenize(text: str) -> set:
    words = re.findall(r"[a-zA-ZçğıöşüÇĞİÖŞÜ0-9]+", (text or "").lower())
    return {w for w in words if len(w) > 2}


def _detect_query_domain(message: str) -> str:
    words = _tokenize(message)
    if words & FOOD_WORDS:
        return "food"
    if words & WORKOUT_WORDS:
        return "workout"
    if words & INJURY_WORDS:
        return "injury"
    if words & SLEEP_WORDS:
        return "sleep"
    return "general"


def build_live_snapshot(db, user_id: int = None) -> dict:
    """Bugünün ve son 7 günün GERÇEK verilerini tek dict'te toplar."""
    profile = crud.get_or_create_profile(db, user_id)
    today = date.today()
    meals_today = crud.get_nutrition_logs_by_date(db, today, user_id)
    sets_today = crud.get_workout_logs_by_date(db, today, user_id)
    meal_plan = crud.get_meal_plan(db, user_id)
    deload = progression.check_deload_needed(db, user_id)
    suggestions = progression.get_all_suggestions(db, user_id)
    nutrition_7d = crud.get_nutrition_history(db, days=7, user_id=user_id)
    volume_7d = crud.get_weekly_volume_by_muscle_group(db, days=7, user_id=user_id)
    metrics = crud.get_body_metrics(db, days=14, user_id=user_id)
    checkin = crud.get_today_checkin(db, user_id)

    cal_eaten = sum(m.calories or 0 for m in meals_today)
    prot_eaten = sum(m.protein or 0 for m in meals_today)
    carb_eaten = sum(m.carbs or 0 for m in meals_today)
    fat_eaten = sum(m.fats or 0 for m in meals_today)

    cal_target = profile.daily_calorie_target or 2200
    prot_target = profile.daily_protein_target or 140

    days_with_nutrition = [d for d in nutrition_7d if d.get("calories", 0) > 0]
    avg_cal_7d = sum(d["calories"] for d in days_with_nutrition) / len(days_with_nutrition) if days_with_nutrition else 0
    avg_prot_7d = sum(d["protein"] for d in days_with_nutrition) / len(days_with_nutrition) if days_with_nutrition else 0

    weight_trend = []
    for m in metrics:
        if m.weight:
            weight_trend.append({"date": str(m.date), "weight": m.weight})

    weight_delta = None
    if len(weight_trend) >= 2:
        weight_delta = weight_trend[-1]["weight"] - weight_trend[0]["weight"]

    programs = crud.get_workout_programs(db)
    program_summary = []
    for p in programs:
        ex_names = [e.name for e in p.exercises]
        program_summary.append({"day": p.day_name, "exercises": ex_names})

    increase_suggestions = [s for s in suggestions if s.get("suggestion") == "increase_weight"]

    return {
        "today": str(today),
        "weekday": today.strftime("%A"),
        "hour": datetime.now().hour,
        "profile_goal": profile.goal,
        "nutrition_today": {
            "meals_logged": len(meals_today),
            "calories_eaten": cal_eaten,
            "protein_eaten": prot_eaten,
            "carbs_eaten": carb_eaten,
            "fats_eaten": fat_eaten,
            "calories_remaining": max(0, cal_target - cal_eaten),
            "protein_remaining": max(0, prot_target - prot_eaten),
            "calories_target": cal_target,
            "protein_target": prot_target,
            "meal_names": [m.meal_name for m in meals_today],
        },
        "workout_today": {
            "sets_logged": len(sets_today),
            "exercises": list({s.exercise_name for s in sets_today}),
        },
        "week_stats": {
            "avg_calories_7d": round(avg_cal_7d, 0),
            "avg_protein_7d": round(avg_prot_7d, 0),
            "volume_by_muscle": volume_7d,
            "weight_delta_14d": weight_delta,
        },
        "deload": deload,
        "progression_ready": increase_suggestions[:5],
        "program_days": len(programs),
        "meal_plan_meals": len(meal_plan),
        "checkin": {
            "mood": checkin.mood if checkin else None,
            "energy": checkin.energy if checkin else None,
            "sleep_quality": checkin.sleep_quality if checkin else None,
            "readiness_score": checkin.readiness_score if checkin else None,
        } if checkin else None,
    }


def snapshot_to_prompt_block(snapshot: dict) -> str:
    n = snapshot["nutrition_today"]
    w = snapshot["workout_today"]
    ws = snapshot["week_stats"]
    lines = [
        f"\n═══ CANLI DURUM SNAPSHOT ({snapshot['today']}, {snapshot['weekday']}, saat ~{snapshot['hour']}) ═══",
        f"BUGÜN BESLENME: {n['calories_eaten']:.0f}/{n['calories_target']:.0f} kcal "
        f"({n['calories_remaining']:.0f} kcal KALDI), "
        f"{n['protein_eaten']:.0f}/{n['protein_target']:.0f}g protein "
        f"({n['protein_remaining']:.0f}g KALDI). Kayıtlı öğünler: {n['meal_names'] or 'henüz yok'}.",
        f"BUGÜN ANTRENMAN: {w['sets_logged']} set kaydedildi. Hareketler: {w['exercises'] or 'henüz yok'}.",
        f"SON 7 GÜN ORTALAMA: {ws['avg_calories_7d']:.0f} kcal/gün, {ws['avg_protein_7d']:.0f}g protein/gün.",
    ]
    if ws.get("weight_delta_14d") is not None:
        lines.append(f"KİLO TRENDİ (14 gün): {ws['weight_delta_14d']:+.1f} kg.")
    if snapshot["deload"].get("needs_deload"):
        lines.append(
            f"⚠️ DELOAD UYARISI AKTİF: {snapshot['deload'].get('reason', 'Yorgunluk/durağanlık tespit edildi')}"
        )
    if snapshot["progression_ready"]:
        pr_lines = [f"{s['exercise_name']} → {s.get('message', 'ağırlık artır')}" for s in snapshot["progression_ready"]]
        lines.append("İLERLEME HAZIR (ağırlık artırılabilir): " + "; ".join(pr_lines))
    if snapshot.get("checkin"):
        c = snapshot["checkin"]
        lines.append(
            f"BUGÜNKÜ CHECK-IN: enerji {c.get('energy')}/5, uyku {c.get('sleep_quality')}/5, "
            f"hazırlık skoru {c.get('readiness_score') or '?'}/100."
        )
    lines.append("═══ SNAPSHOT SONU ═══\n")
    return "\n".join(lines)


def retrieve_relevant_memories(db, user_message: str, limit: int = 15, user_id: int = None) -> list:
    """Mesaja en alakalı hafıza kayıtlarını skorlayarak seçer."""
    domain = _detect_query_domain(user_message)
    boost_map = CATEGORY_BOOST.get(domain, CATEGORY_BOOST["general"])
    query_words = _tokenize(user_message)
    all_memories = crud.get_all_memories(db, user_id=user_id)

    scored = []
    for mem in all_memories:
        mem_words = _tokenize(f"{mem.content} {mem.keywords or ''}")
        overlap = len(query_words & mem_words)
        score = overlap * 2.0
        score += boost_map.get(mem.category, 0)
        score += (mem.importance or 5) * 0.3
        if mem.category == "analysis":
            score += 0.5
        days_old = (datetime.utcnow() - (mem.updated_at or mem.created_at)).days if mem.created_at else 30
        score += max(0, 3 - days_old * 0.1)
        if overlap > 0 or score >= 3:
            scored.append((score, mem))

    if not scored and all_memories:
        durable = [m for m in all_memories if m.category != "analysis"]
        analyses = [m for m in all_memories if m.category == "analysis"]
        durable.sort(key=lambda m: (m.importance or 5, m.id), reverse=True)
        return (durable[:12] + analyses[:2])[:limit]

    scored.sort(key=lambda x: -x[0])
    selected = [m for _, m in scored[:limit]]
    crud.touch_memory_access(db, [m.id for m in selected])
    return selected


def memories_to_prompt_block(memories: list) -> str:
    if not memories:
        return "\n(Henüz kayıtlı hafıza yok — kullanıcıyı tanımaya başlıyorsun.)\n"

    durable = [m for m in memories if m.category != "analysis"]
    analyses = [m for m in memories if m.category == "analysis"]
    sections = []

    if durable:
        lines = []
        for m in durable:
            imp = "★" * min(5, (m.importance or 5) // 2)
            lines.append(f"- [{m.category}|önem:{imp}] {m.content}")
        sections.append("İLGİLİ KALICI HAFIZA (bu mesajla en alakalı kayıtlar — YOK SAYMA):\n" + "\n".join(lines))

    if analyses:
        sections.append(
            "EN SON ANALİZ:\n" + "\n".join(f"- {m.content[:500]}..." if len(m.content) > 500 else f"- {m.content}" for m in analyses)
        )

    return "\nJARVIS HAFIZA (akıllı retrieval — sadece alakalı kayıtlar):\n" + "\n\n".join(sections) + "\n"


def conversation_to_prompt_block(history: list) -> str:
    if not history:
        return ""
    lines = ["\nSON SOHBET GEÇMİŞİ (bağlam için — tutarlı kal):"]
    for msg in history[-12:]:
        role = "Kullanıcı" if msg.role == "user" else "Jarvis"
        content = (msg.content or "")[:400]
        lines.append(f"{role}: {content}")
    lines.append("")
    return "\n".join(lines)


def compute_readiness_score(mood: int, energy: int, sleep_quality: int, soreness: int, deload_needed: bool) -> float:
    """0-100 hazırlık skoru — yüksek = ağır antrenmana hazır."""
    base = ((mood or 3) + (energy or 3) + (sleep_quality or 3)) / 15 * 70
    soreness_penalty = ((soreness or 2) - 1) * 8
    score = max(0, min(100, base - soreness_penalty - (25 if deload_needed else 0)))
    return round(score, 1)


def build_enhanced_system_prompt(db, user_message: str, base_persona: str, intent_instructions: str, user_id: int = None) -> str:
    """Ham API yerine zenginleştirilmiş system prompt."""
    profile = crud.get_or_create_profile(db, user_id)
    snapshot = build_live_snapshot(db, user_id)
    relevant_memories = retrieve_relevant_memories(db, user_message, user_id=user_id)
    history = crud.get_chat_history(db, limit=12, user_id=user_id)

    profile_block = f"""
KULLANICI PROFİLİ:
- Yaş: {profile.age or '?'}, Boy: {profile.height or '?'} cm, Kilo: {profile.current_weight or '?'} kg
- Hedef: {profile.goal} ({profile.target_physique or '-'}), Hedef kilo: {profile.target_weight or '-'}
- Deneyim: {profile.experience_months or 0} ay, Odak: {profile.focus_muscle_group or 'genel'}
- Aktivite: {profile.activity_level}
- Beslenme kısıtları: {profile.dietary_notes or '-'}
- Rutin/uyku: {profile.schedule_notes or '-'}
- Sakatlık: {profile.injury_notes or 'yok'}
- Günlük hedefler: {profile.daily_calorie_target} kcal, {profile.daily_protein_target}g P, {profile.daily_carb_target}g K, {profile.daily_fat_target}g Y
"""

    meal_plan = crud.get_meal_plan(db, user_id)
    if meal_plan:
        plan_lines = "\n".join(
            f"- {m.meal_name} ({m.time_target}): {m.description} [{m.calories:.0f} kcal, {m.protein:.0f}g P]"
            for m in meal_plan
        )
        plan_block = f"\nGÜNCEL BESLENME PLANI:\n{plan_lines}\n"
    else:
        plan_block = "\n(Aktif beslenme planı yok.)\n"

    programs = crud.get_workout_programs(db, user_id)
    if programs:
        prog_lines = []
        for p in programs:
            exs = ", ".join(f"{e.name} ({e.target_sets}x{e.target_reps})" for e in p.exercises)
            prog_lines.append(f"- {p.day_name}: {exs}")
        program_block = f"\nAKTİF ANTRENMAN PROGRAMI:\n" + "\n".join(prog_lines) + "\n"
    else:
        program_block = "\n(Aktif antrenman programı yok.)\n"

    return (
        base_persona
        + profile_block
        + snapshot_to_prompt_block(snapshot)
        + memories_to_prompt_block(relevant_memories)
        + plan_block
        + program_block
        + conversation_to_prompt_block(history)
        + intent_instructions
    )


ENRICHMENT_INTENTS = {
    "chat", "explain_why", "coaching_advice", "daily_checkin", "compare_period",
    "query_history", "remember",
}


def enrich_reply_with_coaching(db, user_message: str, result: dict, user_id: int = None) -> dict:
    """Intent işlendikten sonra koçluk zenginleştirmesi — ikinci Gemini pass.

    Jarvis artık KESİNLİKLE:
    - SADECE kullanıcının sorduğu/istediği şeye odaklanır
    - Kullanıcı KALORİ/MAKRO sormadıkça ASLA kalori, makro, protein, karbonhidrat, yağ kelimelerini kullanmaz
    - Kullanıcı "bugün ne yedim", "kalorim kaç", "makrolarım" gibi SORU sormadıkça beslenme verisini SÖYLEMEZ
    - Kullanıcı "kalan kalori", "kalan protein" sormadıkça "kaldı", "kalan", "hedef" kelimelerini KULLANMAZ
    - Cevaplar MAX 1-2 CÜMLE - konkret, eyleme geçirilebilir, doğrudan
    - "Efendim" hitabı kalsın ama gevezelik YOK
    """
    intent = result.get("intent", "chat")
    if intent not in ENRICHMENT_INTENTS and not result.get("_force_enrich"):
        return result

    reply = (result.get("jarvis_reply") or "").strip()
    if result.get("_food_reply_is_final") or result.get("_skip_enrich"):
        return result

    snapshot = build_live_snapshot(db, user_id)
    profile = crud.get_or_create_profile(db, user_id)

    # Kullanıcı mesajının konusunu tespit et
    msg_lower = user_message.lower()
    asks_about_nutrition = any(w in msg_lower for w in ["kalori", "makro", "protein", "karbonhidrat", "karb", "yağ", "yedim", "yedi", "yiyecek", "öğün", "beslenme", "kaldı", "kalan", "hedef"])
    asks_about_workout = any(w in msg_lower for w in ["antrenman", "set", "tekrar", "ağırlık", "bench", "squat", "deadlift", "program", "spor", "kas", "hareket", "salon", "deload"])
    asks_about_progress = any(w in msg_lower for w in ["gelişim", "ilerleme", "kilo", "vücut", "ölçüm", "grafik", "chart"])
    asks_why = any(w in msg_lower for w in ["neden", "niçin", "why"])
    asks_advice = any(w in msg_lower for w in ["ne yapmalı", "öneri", "tavsiye", "ne önerir", "nasıl"])

    enrich_prompt = f"""
Kullanıcı mesajı: "{user_message}"
Intent: {intent}
Mevcut taslak yanıtın: "{reply or '(boş — sen üret)'}"

KULLANICI KONU BAĞLAMI:
- Beslenme sordu mu: {asks_about_nutrition}
- Antrenman sordu mu: {asks_about_workout}
- Gelişim/kilo sordu mu: {asks_about_progress}
- "Neden" sordu mu: {asks_why}
- Tavsiye istedi mi: {asks_advice}

MEVCUT VERİ (SADECE İLGİLİ OLANI KULLAN):
- Bugün yenen: {snapshot['nutrition_today']['calories_eaten']:.0f} kcal, {snapshot['nutrition_today']['protein_eaten']:.0f}g protein
- Bugün antrenman: {snapshot['workout_today']['sets_logged']} set
- Hedef: {profile.goal}
- Deload: {snapshot['deload'].get('needs_deload', False)}
- Hazırlık skoru: {snapshot.get('checkin', {}).get('readiness_score') if snapshot.get('checkin') else 'yok'}

GÖREV: Jarvis tonunda (efendim), SADECE kullanıcının SORDUĞU şeye CEVAP VER.

KESİN KURALLAR - BUNA HER MESAJDA UY:
1. Kullanıcı KALORİ/MAKRO/PROTEİN/KARB/YAĞ sormadıkça BU KELİMELERİ ASLA KULLANMA
2. Kullanıcı "kalan/kaldı/hedef" sormadıkça BU KELİMELERİ ASLA KULLANMA
3. Basit onay/durum bildirimi ise TEK KISA CÜMLE
4. Gerçek soru/tavsiye ise MAX 2 CÜMLE - paragraf YAZMA
5. Ders verme, motivasyon konuşması, "bunu unutma" eklemeleri YOK
6. Sadece kullanıcının ISTEDİĞİ cevabı ver, ekstra bağlam YOK
7. "Efendim" kalsın ama her cümlenin SOMUT bir amacı olsun
8. SADECE düz metin, JSON YOK

ÖRNEKLER:
- Kullanıcı: "bench 80x8" → "Kaydedildi efendim - bench 80kg × 8 tekrar."
- Kullanıcı: "bugün çok yorgunum" → "Anladım efendim. Bugün hafif antrenman veya dinlenme günü yapalım."
- Kullanıcı: "neden squat önerdin?" → "Squat, quad ve glute'yi aynı anda en verimli yüklüyor efendim."
- Kullanıcı: "kalorim kaç?" → "Bugün {snapshot['nutrition_today']['calories_eaten']:.0f}/{snapshot['nutrition_today']['calories_target']:.0f} kcal efendim."
- Kullanıcı: "merhaba" → "Merhaba efendim, nasıl yardımcı olabilirim?"
"""
    try:
        model = _GenerativeModel(model_name=MODEL_NAME)
        response = model.generate_content(enrich_prompt, generation_config={"temperature": 0.4})
        enriched = (response.text or "").strip()
        if enriched and len(enriched) > 10:
            result["jarvis_reply"] = enriched
            result["_enriched"] = True
    except Exception as e:
        logger.warning("[JARVIS_BRAIN] Yanıt zenginleştirme atlandı: %s", e)

    return result


def extract_implicit_memories(db, user_message: str, assistant_reply: str, user_id: int = None):
    """Sohbetten otomatik hafıza madenciliği — kullanıcı açıkça 'hatırla' demese bile."""
    if len(user_message.strip()) < 15:
        return

    prompt = f"""
Aşağıdaki sohbetten, kullanıcı hakkında KALICI olarak hatırlanması gereken bilgi var mı?

Kullanıcı: {user_message}
Jarvis: {assistant_reply}

SADECE JSON dön:
{{"memories": [
  {{"category": "preference|note|insight", "content": "...", "importance": 1-10, "memory_key": "diet.fish|schedule.sleep|injury.knee|null", "keywords": "virgülle,anahtar,kelimeler"}}
]}}

KURALLAR:
- Geçici/single-use bilgi EKLEME (bugün ne yedi gibi — o zaten log'da)
- Kalıcı tercih, alışkanlık, kısıtlama, hedef değişikliği EKLE
- Zaten bilinen bariz şeyleri tekrarlama
- Hiç kalıcı bilgi yoksa: {{"memories": []}}
"""
    try:
        model = _GenerativeModel(model_name=MODEL_NAME)
        response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json", "temperature": 0.2},
        )
        data = json.loads(response.text)
        for mem in data.get("memories", [])[:3]:
            content = (mem.get("content") or "").strip()
            if len(content) < 8:
                continue
            crud.create_memory(
                db,
                category=mem.get("category", "note"),
                content=content,
                importance=min(10, max(1, int(mem.get("importance", 5)))),
                keywords=mem.get("keywords", ""),
                memory_key=mem.get("memory_key") if mem.get("memory_key") != "null" else None,
                user_id=user_id,
            )
    except Exception as e:
        logger.debug("[JARVIS_BRAIN] Implicit memory extraction skipped: %s", e)


def generate_proactive_briefing(db, user_id: int = None) -> dict:
    """Chat açıldığında gösterilecek proaktif durum özeti."""
    snapshot = build_live_snapshot(db, user_id)
    if not snapshot:
        snapshot = {}
    profile = crud.get_or_create_profile(db, user_id)
    n = snapshot.get("nutrition_today", {})
    w = snapshot.get("workout_today", {})

    suggestions = []
    if n.get("protein_remaining", 0) > 40 and n.get("calories_eaten", 0) > 0:
        suggestions.append(f"Bugün hâlâ {n['protein_remaining']:.0f}g protein alman gerekiyor efendim.")
    elif n.get("calories_eaten", 0) == 0:
        suggestions.append("Bugün henüz bir öğün kaydetmedin — kahvaltı veya planındaki ilk öğünü hatırlatayım mı?")

    if snapshot.get("progression_ready"):
        ex = snapshot["progression_ready"][0]["exercise_name"]
        suggestions.append(f"{ex} için ağırlık artırma zamanı gelmiş görünüyor.")

    if snapshot.get("deload", {}).get("needs_deload"):
        suggestions.append("Deload haftası gerekebilir — bu hafta hacmi %40 azaltmayı düşün.")

    if w.get("sets_logged", 0) == 0 and snapshot.get("program_days", 0) > 0:
        suggestions.append("Bugün henüz antrenman kaydı yok — programına göre hareket edelim mi?")

    greeting = "Günaydın" if snapshot.get("hour", 0) < 12 else ("İyi günler" if snapshot.get("hour", 0) < 18 else "İyi akşamlar")

    briefing_text = (
        f"{greeting} efendim. "
        f"Bugün {n.get('calories_eaten', 0):.0f}/{n.get('calories_target', 0):.0f} kcal "
        f"({n.get('calories_remaining', 0):.0f} kaldı), "
        f"{n.get('protein_eaten', 0):.0f}/{n.get('protein_target', 0):.0f}g protein. "
        f"Antrenman: {w.get('sets_logged', 0)} set."
    )

    checkin = snapshot.get("checkin") or {}
    return {
        "briefing": briefing_text,
        "suggestions": suggestions[:4],
        "snapshot": snapshot,
        "readiness": checkin.get("readiness_score"),
        "goal": profile.goal,
    }


def process_checkin(db, mood: int, energy: int, sleep_quality: int, soreness: int, notes: str = None, user_id: int = None) -> dict:
    """Günlük check-in kaydet ve Jarvis koçluk yanıtı üret."""
    deload = progression.check_deload_needed(db, user_id)
    score = compute_readiness_score(mood, energy, sleep_quality, soreness, deload.get("needs_deload", False))

    checkin = crud.upsert_daily_checkin(db, {
        "mood": mood,
        "energy": energy,
        "sleep_quality": sleep_quality,
        "soreness": soreness,
        "notes": notes,
        "readiness_score": score,
    }, user_id)

    snapshot = build_live_snapshot(db)
    advice = "normal"
    if score >= 75:
        advice = "heavy"
        msg = f"Hazırlık skorun {score}/100 efendim — bugün ağır antrenman için yeşil ışık yanıyor."
    elif score >= 50:
        advice = "moderate"
        msg = f"Skor {score}/100 — orta yoğunlukta antrenman uygun, dinlemeyi de ihmal etme."
    else:
        advice = "light"
        msg = f"Skor {score}/100 — bugün hafif antrenman veya aktif dinlenme daha akıllıca olur efendim."

    if deload.get("needs_deload"):
        msg += " Deload uyarısı da aktif — hacmi düşürmeyi ciddiye al."

    crud.create_memory(
        db, category="note",
        content=f"Check-in {date.today()}: enerji {energy}/5, uyku {sleep_quality}/5, hazırlık {score}/100.",
        importance=4,
        memory_key=f"checkin.{date.today().isoformat()}",
        keywords="checkin,enerji,uyku,hazırlik",
    )

    return {
        "checkin": {
            "mood": checkin.mood,
            "energy": checkin.energy,
            "sleep_quality": checkin.sleep_quality,
            "soreness": checkin.soreness,
            "readiness_score": score,
            "notes": checkin.notes,
        },
        "training_advice": advice,
        "jarvis_reply": msg,
        "snapshot": snapshot,
    }


def handle_compare_period(db, days: int = 7) -> str:
    """Bu hafta vs geçen hafta karşılaştırması."""
    this_week = crud.get_nutrition_history(db, days=days)
    workout_this = crud.get_workout_logs_range(db, days=days)
    workout_prev = crud.get_workout_logs_range(db, days=days * 2)
    prev_count = len(workout_prev) - len(workout_this)

    avg_cal = sum(d["calories"] for d in this_week) / max(1, len(this_week))
    volume = crud.get_weekly_volume_by_muscle_group(db, days=days)

    lines = [
        f"SON {days} GÜN vs ÖNCEKİ {days} GÜN:",
        f"- Ortalama günlük kalori: {avg_cal:.0f} kcal",
        f"- Antrenman set sayısı: bu dönem {len(workout_this)}, önceki dönem ~{max(0, prev_count)}",
        f"- Kas hacmi (set): {volume}",
    ]
    return "\n".join(lines)
