"""
Eksik/gelişmeyen kas bölgesi tespiti — elle girilen focus_muscle_group'ın
otomatikleştirilmiş hali. Haftalık hacim vs MAV hedefi, progression stagnasyonu,
kilo trendi ve kullanıcının hedefini birleştirip program prompt'una girecek
"ODAK BÖLGELER" talimatı üretir.
"""
import logging
import json

from sqlalchemy.orm import Session

import crud
import models
from progression import check_deload_needed

logger = logging.getLogger(__name__)

# Kas grubunun ağırlık katsayısı: hacim hedefi hesabında kullanılır (ai_core kuralıyla tutarlı)
MUSCLE_WEIGHTS = {
    "Göğüs": 1.0, "Sırt": 1.0, "Quadriceps": 1.2, "Hamstring & Glute": 1.1,
    "Omuz": 0.8, "Biceps": 0.6, "Triceps": 0.6, "Karın": 0.5,
}


def detect_weak_areas(db: Session, user_id: int = None) -> dict:
    """Kullanıcının son 7 gün verisinden eksik/gelişmeyen bölgeleri tespit eder.
    Döner: {focus_regions: [..], reasons: {region: sebep}, deload: {...}, weekly_volume: {...}}"""
    reasons = {}
    scores = {}  # bölge -> 0-10 eksiklik skoru (yüksek = daha eksik)

    volume = crud.get_weekly_volume_by_muscle_group(db, days=7, user_id=user_id) or {}
    deload = check_deload_needed(db, user_id)

    # 1) Hacim eksikliği: yalnızca gerçekten kayıt varsa yorumla. Yeni kullanıcıda
    # "0 set" verisini eksik kas sanmak, bütün vücudu yanlışlıkla odak yapıyordu.
    if volume:
        for muscle, weight in MUSCLE_WEIGHTS.items():
            sets = 0
            if isinstance(volume, dict):
                for key, val in volume.items():
                    if muscle.lower().split(" ")[0] in str(key).lower():
                        sets = int(val or 0)
                        break
            if sets == 0:
                scores[muscle] = 8.0
                reasons[muscle] = "Son 7 günde 0 set - haftalık hacim hedefinin altında."
            elif sets < 4 * weight:
                scores[muscle] = 5.0
                reasons[muscle] = f"Son 7 günde sadece {sets} set - hacim hedefinin belirgin altında."

    # 2) Onboarding videosundan açıkça görülen gecikmiş bölgeleri ekle. Düşük
    # güvenli veya serbest metinli sonuçlar burada planı etkileyemez.
    if user_id:
        try:
            memory = (db.query(models.UserMemory)
                      .filter(models.UserMemory.user_id == user_id,
                              models.UserMemory.category == "onboarding_video_analysis")
                      .order_by(models.UserMemory.id.desc()).first())
            data = json.loads(memory.content) if memory else {}
            if data.get("program_eligible") and data.get("confidence") in {"high", "medium"}:
                for region in data.get("focus_regions", [])[:3]:
                    if region in MUSCLE_WEIGHTS:
                        scores[region] = max(scores.get(region, 0), 7.0)
                        reasons[region] = "Onboarding videosunda gözlenen bölgesel gelişim önceliği."
        except (TypeError, json.JSONDecodeError):
            logger.warning("Yapılandırılmış onboarding video analizi okunamadı.")

    # 2) Stagnasyon: 3 antrenmandır ağırlığı artmayan hareketlerin kas grubu = gelişmeyen bölge
    for name in deload.get("stagnant_exercises", []):
        region = _resolve_region(db, name, user_id)
        if region:
            scores[region] = max(scores.get(region, 0), 6.0)
            reasons[region] = reasons.get(region, "") + f" '{name}' hareketinde ilerleme durdu (stagnasyon)."

    # Eksiklik skoruna göre sırala, üst 2 bölgeyi odak olarak seç
    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    focus_regions = [region for region, score in ranked[:2] if score >= 5.0]

    return {
        "focus_regions": focus_regions,
        "reasons": reasons,
        "weekly_volume": volume,
        "deload": deload,
    }


def _resolve_region(db: Session, exercise_name: str, user_id: int = None) -> str | None:
    """Hareket adını kütüphaneden kas grubuna çevirir (bilgi katmanı entegrasyonu)."""
    from knowledge.exercise_library import match_exercise_name
    match = match_exercise_name(db, exercise_name)
    if match:
        return match.muscle_group
    # Kütüphane boşsa hareket adından kaba eşleşme
    name = (exercise_name or "").lower()
    coarse = [("göğüs", "Göğüs"), ("press", "Göğüs"), ("fly", "Göğüs"),
              ("pull", "Sırt"), ("row", "Sırt"), ("lat", "Sırt"),
              ("squat", "Quadriceps"), ("leg", "Quadriceps"), ("lunge", "Quadriceps"),
              ("deadlift", "Hamstring & Glute"), ("curl", "Biceps"),
              ("extension", "Triceps"), ("raise", "Omuz"), ("lateral", "Omuz")]
    for keyword, region in coarse:
        if keyword in name:
            return region
    return None


def format_weak_areas_block(weak: dict | None) -> str:
    """Tespit sonucunu program prompt'una girecek talimat bloğuna çevirir."""
    if not weak or not weak.get("focus_regions"):
        return "ODAK BÖLGELER: Veriden belirgin eksik bölge tespit edilmedi - hacmi bölgelere dengeli dağıt."
    lines = [f"ODAK BÖLGELER: Bu bölgeler eksik/gelişmiyor - programda hacmi ÖNCELİKLİ ver:"]
    for region in weak["focus_regions"]:
        reason = weak.get("reasons", {}).get(region, "").strip()
        lines.append(f"- {region}: {reason or 'hacim hedefinin altında'}")
    lines.append("Bu bölgelere fazladan 2-4 set ekle; diğer bölgelerde hacmi MAV hedefinde tut.")
    return "\n".join(lines)
