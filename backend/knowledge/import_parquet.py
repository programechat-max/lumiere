"""0000.parquet egzersiz kutuphanesi import edici (Faz 6 - genis veri katmani).

Kullanim:  ~/Downloads/0000.parquet dosyasini exercise_library_items tablosuna aktarir.
Idempotent: isim + source eslesmesi olan kayit dokunulmaz.
Kas gruplari Ingilizce muskul adlarindan Lumiere'in Turkce gruplarina cevrilir;
ekipman ana kategorilere normalize edilir (barbell/dumbbell/cable/machine/
bodyweight/kettlebell/band). Ingilizce isim korunur, Almanca/Ispanyolca karsiliklar
alias'a eklenir - boylece kutuphaneyi 35'ten ~600 kayda cikaririz.
"""
import logging
import os
import re

from sqlalchemy.orm import Session

from models import ExerciseLibraryItem
from knowledge.exercise_library import VALID_EQUIPMENT, VALID_TYPES

logger = logging.getLogger(__name__)

DEFAULT_PARQUET = os.path.expanduser("~/Downloads/0000.parquet")

# Ingilizce tekil kas adi -> Lumiere Turkce grup
MUSCLE_MAP = {
    "rectus_abdominis": "Karın", "transverse_abdominis": "Karın", "obliques": "Karın",
    "hip_flexors": "Karın",
    "erector_spinae": "Sırt", "latissimus_dorsi": "Sırt", "rhomboids": "Sırt",
    "trapezius": "Sırt", "quadratus_lumborum": "Sırt",
    "pectoralis_major": "Göğüs", "serratus_anterior": "Göğüs",
    "anterior_deltoid": "Omuz", "lateral_deltoid": "Omuz", "posterior_deltoid": "Omuz",
    "deltoid": "Omuz", "supraspinatus": "Omuz",
    "biceps_brachii": "Biceps", "brachialis": "Biceps", "brachioradialis": "Biceps",
    "forearm_extensors": "Biceps", "forearm_flexors": "Biceps", "forearms": "Biceps",
    "triceps_brachii": "Triceps",
    "quadriceps": "Quadriceps",
    "hamstrings": "Hamstring & Glute", "gluteus_maximus": "Hamstring & Glute",
    "gluteus_medius": "Hamstring & Glute", "abductors": "Hamstring & Glute",
    "adductors": "Hamstring & Glute",
    "gastrocnemius": "Baldır", "soleus": "Baldır", "calves": "Baldır",
}

# parquet equipment -> ana kategori (VALID_EQUIPMENT ile uyumlu)
EQUIPMENT_MAP = {
    "barbell": "barbell", "ez_bar": "barbell", "smith_machine": "machine",
    "cable": "cable", "dumbbell": "dumbbell", "kettlebell": "kettlebell",
    "machine": "machine", "leg_press": "machine", "flat_bench": "machine",
    "bench": "machine", "air_bike": "machine", "incline_bench": "machine",
    "bodyweight": "bodyweight", "pull_up_bar": "bodyweight", "ab_wheel": "bodyweight",
    "rings": "bodyweight", "stability_ball": "bodyweight",
    "suspension_trainer": "bodyweight", "exercise_ball": "bodyweight",
    "resistance_band": "band", "loop_band": "band", "band": "band",
    "none": "bodyweight", "": "bodyweight", None: "bodyweight",
}
def _norm(text: str) -> str:
    return " ".join((text or "").strip().lower().split())


def _map_muscle(primary: str) -> str:
    tokens = [t for t in re.split(r"[\|,]", primary or "") if t]
    for tok in tokens:
        mapped = MUSCLE_MAP.get(tok.strip().lower())
        if mapped:
            return mapped
    return "Diğer"


def _map_exercise_type(row) -> str | None:
    mechanic = str(row.get("mechanic") or "").lower()
    force = str(row.get("force_type") or "").lower()
    category = str(row.get("category") or "").lower()
    body = str(row.get("body_part") or "").lower()
    goals = str(row.get("goals") or "").lower()
    is_uni = bool(row.get("is_unilateral"))
    if category == "cardio" or "cardio" in goals:
        return "metabolic"
    if mechanic == "compound" and force in ("push", "pull", "dynamic"):
        return "secondary_compound" if is_uni else "primary_compound"
    if "core" in body or "core" in goals or "rectus_abdominis" in str(row.get("primary_muscles") or ""):
        return "core_prehab"
    if force == "static" or category == "stretching":
        return "stretch_isolation"
    if mechanic == "isolation":
        return "shortened_isolation"
    return "secondary_compound"


def _map_contraindications(row) -> str:
    tags = str(row.get("tags") or "")
    contras = []
    name = _norm(row.get("name_en") or "")
    if "deadlift" in name or "good morning" in name or "back lever" in name or "back squat" in name:
        contras.append("lower_back")
    if "overhead" in name or "handstand" in name or "pull-up" == name or "chin-up" in name:
        contras.append("shoulder")
    if "squat" in name or "lunge" in name or "jump" in name or "step-up" in name:
        if "knee_safe" not in tags:
            contras.append("knee")
    return ",".join(contras)


def _is_stretch_mediated(row) -> bool:
    name = _norm(row.get("name_en") or "")
    desc = _norm(row.get("description_en") or "")
    text = f"{name} {desc}"
    if "stretch" in text or "lengthen" in text or "extended" in text:
        return True
    tags = str(row.get("tags") or "")
    return "stretch" in tags

def import_parquet(db: Session, path: str = None) -> dict:
    """Parquet dosyasini tabloya aktarir. Idempotent. Donus: {added, skipped}"""
    path = path or DEFAULT_PARQUET
    if not os.path.exists(path):
        logger.warning("[IMPORT] Parquet yok: %s - atlaniyor", path)
        return {"added": 0, "skipped": 0}

    try:
        import pandas as pd
        df = pd.read_parquet(path)
    except Exception as exc:
        logger.warning("[IMPORT] Parquet okunamadi: %s", exc)
        return {"added": 0, "skipped": 0}

    existing = {
        _norm(f"{i.name}::{i.source or ''}")
        for i in db.query(ExerciseLibraryItem).filter(ExerciseLibraryItem.source == "parquet_import").all()
    }
    added = 0
    skipped = 0
    for _, row in df.iterrows():
        raw_name = str(row.get("name_en") or "").strip()
        if not raw_name:
            continue
        name = _title(raw_name)
        key = _norm(f"{name}::parquet_import")
        if key in existing:
            skipped += 1
            continue

        muscle = _map_muscle(str(row.get("primary_muscles") or ""))
        aliases = ", ".join(x for x in [str(row.get("name_de") or ""), str(row.get("name_es") or "")] if x)
        equipment = EQUIPMENT_MAP.get(str(row.get("equipment") or "").strip().lower(), "bodyweight")
        if equipment not in VALID_EQUIPMENT:
            equipment = "bodyweight"
        ex_type = _map_exercise_type(row)
        if ex_type not in VALID_TYPES:
            ex_type = "secondary_compound"

        goals_raw = str(row.get("goals") or "") if not pd.isna(row.get("goals")) else ""
        tags_raw = str(row.get("tags") or "") if not pd.isna(row.get("tags")) else ""
        desc = str(row.get("description_en") or "") if not pd.isna(row.get("description_en")) else ""
        cues = str(row.get("instructions_en") or "") if not pd.isna(row.get("instructions_en")) else ""
        met_val = row.get("met")
        met = float(met_val) if met_val is not None and not pd.isna(met_val) else None

        difficulty = str(row.get("difficulty") or "intermediate").lower()
        if difficulty not in ("beginner", "intermediate", "advanced"):
            difficulty = "intermediate"

        item = ExerciseLibraryItem(
            name=name[:200],
            aliases=aliases[:300] or "",
            muscle_group=muscle,
            secondary_muscles=str(row.get("secondary_muscles") or "")[:300],
            exercise_type=ex_type,
            stretch_mediated=_is_stretch_mediated(row),
            unilateral=bool(row.get("is_unilateral")),
            equipment=equipment,
            technique_cue=cues[:1000] or None,
            rep_range_bias=_rep_bias(row),
            contraindications=_map_contraindications(row),
            selection_reason=(goals_raw or "parquet_import")[:500],
            # Ham parquet verisi kapsamlı kaynak/metadata denetiminden geçene
            # kadar üretim adayı değildir; audit kuyruğunda görünür kalmalı.
            pending_review=True,
            difficulty=difficulty,
            force_type=str(row.get("force_type") or "") or None,
            mechanic=str(row.get("mechanic") or "") or None,
            goals=goals_raw[:300] or "",
            tags=tags_raw[:300] or "",
            met=met,
            body_part=str(row.get("body_part") or "") or None,
            description=desc[:800] or None,
            image_start=str(row.get("image_flat_start") or "") if not pd.isna(row.get("image_flat_start")) and row.get("image_flat_start") else None,
            image_peak=str(row.get("image_flat_peak") or "") if not pd.isna(row.get("image_flat_peak")) and row.get("image_flat_peak") else None,
            image_main=str(row.get("image_flat_main") or "") if not pd.isna(row.get("image_flat_main")) and row.get("image_flat_main") else None,
            is_bodyweight=bool(row.get("is_bodyweight")),
            source="parquet_import",
            evidence_level="unverified",
            evidence_source="parquet_import_unreviewed",
        )
        db.add(item)
        existing.add(key)
        added += 1

    db.commit()
    logger.info("[IMPORT] Parquet: +%d eklenen, %d atlanan", added, skipped)
    return {"added": added, "skipped": skipped}


def _rep_bias(row) -> str:
    goals = str(row.get("goals") or "")
    if "strength" in goals:
        return "6-10"
    if "power" in goals:
        return "3-6"
    if "endurance" in goals:
        return "12-20"
    return "8-12"


def _title(name: str) -> str:
    words = str(name or "").split()
    return " ".join(w[:1].upper() + w[1:] if w else w for w in words)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    from database import SessionLocal
    db = SessionLocal()
    try:
        print(import_parquet(db))
    finally:
        db.close()
