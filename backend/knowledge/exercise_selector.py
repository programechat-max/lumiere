"""Egzersiz seçici — geniş kütüphaneden kas grubu/hedef/ekipmana göre
EN İYİ hipertrofi hareketlerini rankleyip seçer (Faz 6).

Kullanıcı "kas kütlesi + göğüs + evde dumbbell" derse, 600 kaydı AI'ya basmak
yerine o kas grubuna uygun, ekipman/kontrendikasyon filtreli, tam-germe
öncelikli, goals="hypertrophy" olan top-N hareketi döndürür. Bu hem prompt
bütçesini korur hem de "saçma sapan hareket yazmasın" isteğinin motorudur.

Rankleme skoru (0-100):
  30  goals içinde hypertrophy / strength varlığı
  25  tam-germe (`stretch_mediated`) — bilimsel öncelik
  20  kütüphane kaynağı: local_tr (elle küratörlü) > parquet_import
  15  seviye uyumu (beginner kadrosu yüksek, advanced'e karma)
  10  usage_count (AI'nın zamanla öğrenmesi) + MET>4 bonusu (yoğunluk)
"""
import logging
import re

from sqlalchemy import or_
from sqlalchemy.orm import Session

from models import ExerciseLibraryItem

logger = logging.getLogger(__name__)

# Lumiere kas grubu -> İngilizce arama anahtarları (parquet primary_muscles eşleşmesi için)
MUSCLE_KEYWORDS = {
    "Göğüs": ["pectoral", "chest"],
    "Sırt": ["latissimus", "rhomboid", "trapezius", "back", "erector"],
    "Quadriceps": ["quadricep", "quad"],
    "Hamstring & Glute": ["hamstring", "glute", "glut"],
    "Omuz": ["deltoid", "shoulder"],
    "Biceps": ["biceps", "brachialis"],
    "Triceps": ["triceps"],
    "Karın": ["abdominis", "obliq", "core", "abdominal"],
    "Baldır": ["gastrocnemius", "soleus", "calf"],
}

EX_TYPE_PRIORITY = {
    "primary_compound": 5,
    "secondary_compound": 4,
    "stretch_isolation": 5,
    "shortened_isolation": 3,
    "metabolic": 1,
    "unilateral": 3,
    "core_prehab": 2,
}

# FAZ 7 — bilimsel baş/yüklenme profili öncelikleri
MUSCLE_HEAD_LABELS = {
    "long_head": "long head",
    "lateral_head": "lateral head",
    "medial_head": "medial head",
    "upper": "üst baş",
    "lower": "alt baş",
    "clavicular": "clavicular baş",
    "sternal": "sternal baş",
    "rectus_femoris": "rectus femoris",
    "vastus_medialis": "vastus medialis",
    "biceps_femoris": "biceps femoris (uzun baş)",
    "semitendinosus": "semitendinosus",
    "soleus": "soleus başı",
    "gastrocnemius": "gastrocnemius başı",
    "upper_traps": "üst trapez",
    "rear_delt": "arka deltoid",
    "obliques": "oblique'ler",
}
# rom_profile önceliği: lengthened (bilimsel öncelik) > full > shortened > partial
ROM_PRIORITY = {"lengthened": 8, "full": 5, "shortened": 3, "partial": 1, "isometric": 1}


def _norm(text: str) -> str:
    return " ".join((text or "").strip().lower().split())


def _score(ex: ExerciseLibraryItem, level: str, allow_stretches: bool) -> float:
    score = 0.0

    # 1) Hedef uyumu (30 puan)
    goals = _norm(ex.goals or "")
    if "hypertrophy" in goals:
        score += 30
    elif "strength" in goals:
        score += 20
    if "rehab" in goals:
        score -= 5

    # 2) Tam-germe (25 puan) — bilimsel kural
    if allow_stretches and ex.stretch_mediated:
        score += 25

    # 3) Kütüphane kaynağı (20 puan): elle küratörlü daha güvenilir
    if (ex.source or "") == "local_tr":
        score += 20
    elif (ex.source or "") == "parquet_import":
        score += 12

    # 4) Seviye uyumu (15 puan)
    diff = (ex.difficulty or "intermediate").lower()
    if level == "beginner":
        score += 15 if diff == "beginner" else (5 if diff == "intermediate" else -5)
    elif level == "advanced":
        score += 15 if diff != "beginner" else 0
    else:  # intermediate (varsayılan)
        score += 10 if diff in ("beginner", "intermediate") else 0

    # 5) FAZ 7 — literatür destekli stimulus_rating (0-10) -> 0-12 puan
    if ex.stimulus_rating is not None:
        score += min(12.0, float(ex.stimulus_rating) * 1.2)

    # 6) FAZ 7 — ROM profili (lengthened-state overload önceliği)
    score += ROM_PRIORITY.get(ex.rom_profile or "", 4)

    # 7) Kullanım + yoğunluk (10 puan)
    score += min(6, ex.usage_count or 0)
    if ex.met and ex.met >= 5:
        score += 4

    # 8) Hareket tipi önceliği (küçük bonus)
    score += EX_TYPE_PRIORITY.get(ex.exercise_type or "", 0) * 0.5
    return score


def select_exercises(
    db: Session,
    muscle_group: str,
    equipment: list[str] | None = None,
    injury_notes: str | None = None,
    goal: str = "hypertrophy",
    level: str = "intermediate",
    limit: int = 10,
    include_stretches: bool = True,
) -> list[ExerciseLibraryItem]:
    """Kas grubu için en iyi hareketleri seçer (ranklenmiş liste).

    - equipment: kullanıcının elindeki cihazlar (['dumbbell','bodyweight'])
    - injury_notes: sakatlık metni (diz/omuz/bel içerirse o bölge hariç)
    - goal: hypertrophy | strength | cut | recomp (hedef etiketine yansır)
    """
    keywords = MUSCLE_KEYWORDS.get(muscle_group) or [muscle_group.lower()]
    kw_like = [f"%{k}%" for k in keywords]

    # Önce kas grubu TAM eşleşmesi (güvenilir); eşleşen varsa name/alias
    # aramasına düşme - "Chest-Supported Row" gibi adı chest geçen sırt
    # hareketleri göğüs havuzuna girmesin.
    exact = (
        db.query(ExerciseLibraryItem)
        .filter(
            ExerciseLibraryItem.pending_review == False,  # noqa: E712
            ExerciseLibraryItem.muscle_group == muscle_group,
            ExerciseLibraryItem.evidence_level == "expert_curated",
        )
        .all()
    )
    if exact:
        items = list(exact)
    else:
        items = (
            db.query(ExerciseLibraryItem)
            .filter(
                ExerciseLibraryItem.pending_review == False,  # noqa: E712
                ExerciseLibraryItem.evidence_level == "expert_curated",
                or_(
                    ExerciseLibraryItem.muscle_group == muscle_group,
                    *[ExerciseLibraryItem.name.ilike(pat) for pat in kw_like],
                    *[ExerciseLibraryItem.aliases.ilike(pat) for pat in kw_like],
                ),
            )
            .all()
        )

    # Ekipman filtresi
    if equipment:
        allowed = {_norm(e) for e in equipment}
        items = [i for i in items if (i.equipment or "bodyweight").lower() in allowed]

    # Kontrendikasyon filtresi (sakatlık)
    notes = _norm(injury_notes)
    banned = set()
    if any(k in notes for k in ("diz", "knee", "quad tendon")):
        banned.add("knee")
    if any(k in notes for k in ("omuz", "shoulder", "rotator")):
        banned.add("shoulder")
    if any(k in notes for k in ("bel", "lower back", "lomber", "spine")):
        banned.add("lower_back")
    if banned:
        items = [
            i for i in items
            if not banned & {
                _norm(t) for t in re.split(r"[,|]", i.contraindications or "") if t
            }
        ]

    # Hedef ek filtre: cut'te hypertrophy/texture öncelikli
    if goal == "cut":
        items = [i for i in items if "hypertrophy" in (i.goals or "") or "strength" in (i.goals or "")]

    scored = sorted(
        items,
        key=lambda ex: _score(ex, level, include_stretches),
        reverse=True,
    )
    seen = set()
    result = []
    for ex in scored:
        key = _norm(ex.name)
        if key in seen:
            continue
        seen.add(key)
        result.append(ex)
        if len(result) >= limit:
            break
    return result


def format_selected_pool(db: Session, muscle_groups: list[str], equipment: list[str] | None = None,
                         injury_notes: str | None = None, goal: str = "hypertrophy",
                         level: str = "intermediate", per_group: int = 8) -> str:
    """Birden çok kas grubu için seçili havuzu prompt metnine çevirir.
    'Kas grubu: hareket listesi' biçiminde deterministik bir blok verir.
    FAZ 7: her seçimde kasın hedef başı (muscle_head) ve ROM profili de yazılır -
    böylece AI aynı gün aynı kasın TÜM başlarını kapsayan seçim yapabilir (ör.
    triceps: long_head + lateral_head + medial_head)."""
    lines = []
    for mg in muscle_groups:
        sel = select_exercises(db, mg, equipment=equipment, injury_notes=injury_notes,
                               goal=goal, level=level, limit=per_group)
        if not sel:
            lines.append(f"{mg}: ÜRETİM DURDURULMALI - onaylı hareket adayı bulunamadı; hareket uydurma.")
            continue
        entries = []
        for ex in sel:
            meta = f"{ex.exercise_type or 'isolation'}"
            if ex.stretch_mediated:
                meta += ",tam-germe"
            if ex.unilateral:
                meta += ",tek-taraf"
            if ex.muscle_head:
                meta += f",baş:{ex.muscle_head}"
            if ex.rom_profile:
                meta += f",ROM:{ex.rom_profile}"
            entries.append(f"{ex.name} ({ex.muscle_group},{meta},{ex.equipment})")
        lines.append(f"{mg}: " + " | ".join(entries))
    return "\n".join(lines)
