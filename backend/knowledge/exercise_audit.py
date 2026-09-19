"""Egzersiz kütüphanesi kalite/audit raporu.

Selector üretimde yalnızca ``expert_curated`` kayıtları kullanır. Bu modül ise
ham havuzun tamamını ölçer; böylece üretime kapalı kayıtlar sessizce kaybolmaz
ve veri genişletme işi ölçülebilir bir kuyruğa dönüşür.
"""
from __future__ import annotations

from collections import Counter

from sqlalchemy.orm import Session

from models import ExerciseLibraryItem
from knowledge.exercise_library import VALID_EQUIPMENT, VALID_TYPES
from knowledge.verify_pmid import KNOWN_RESEARCH_PMIDS

VALID_GROUPS = {
    "Göğüs", "Sırt", "Quadriceps", "Hamstring & Glute", "Omuz",
    "Biceps", "Triceps", "Karın", "Baldır",
}
VALID_EVIDENCE_SCOPES = {"direct", "muscle_group", "general_mechanistic"}


def _valid_evidence_refs(value: str | None) -> bool:
    refs = [part.strip() for part in (value or "").split(",") if part.strip()]
    return bool(refs) and all(
        ref.startswith("PMID:") and ref.removeprefix("PMID:") in KNOWN_RESEARCH_PMIDS
        for ref in refs
    )


def audit_exercise_library(db: Session) -> dict:
    """Kütüphanenin üretim uygunluğunu ve iyileştirme kuyruğunu raporlar."""
    rows = db.query(ExerciseLibraryItem).order_by(ExerciseLibraryItem.id.asc()).all()
    evidence = Counter((row.evidence_level or "unverified") for row in rows)
    sources = Counter((row.source or "unknown") for row in rows)
    groups = Counter((row.muscle_group or "unknown") for row in rows)

    missing_metadata = {
        "selection_reason": [row.name for row in rows if not (row.selection_reason or "").strip()],
        "muscle_head": [row.name for row in rows if not (row.muscle_head or "").strip()],
        "rom_profile": [row.name for row in rows if not (row.rom_profile or "").strip()],
        "technique_cue": [row.name for row in rows if not (row.technique_cue or "").strip()],
        "evidence_refs": [row.name for row in rows if row.evidence_level == "expert_curated" and not _valid_evidence_refs(row.evidence_refs)],
        "evidence_scope": [row.name for row in rows if row.evidence_level == "expert_curated" and row.evidence_scope not in VALID_EVIDENCE_SCOPES],
    }
    invalid = {
        "muscle_group": sorted({row.name for row in rows if row.muscle_group not in VALID_GROUPS}),
        "equipment": sorted({row.name for row in rows if row.equipment not in VALID_EQUIPMENT}),
        "exercise_type": sorted({row.name for row in rows if row.exercise_type not in VALID_TYPES}),
    }

    duplicate_names: dict[str, list[str]] = {}
    by_name: dict[str, list[str]] = {}
    for row in rows:
        key = " ".join((row.name or "").lower().split())
        by_name.setdefault(key, []).append(row.name)
    for key, names in by_name.items():
        if key and len(names) > 1:
            duplicate_names[key] = names

    production_eligible = sum(
        1 for row in rows
        if not row.pending_review
        and row.evidence_level == "expert_curated"
        and row.muscle_group in VALID_GROUPS
        and row.equipment in VALID_EQUIPMENT
        and row.exercise_type in VALID_TYPES
        and bool((row.evidence_refs or "").strip())
        and row.evidence_scope in VALID_EVIDENCE_SCOPES
    )
    return {
        "total": len(rows),
        "production_eligible": production_eligible,
        "quarantined": len(rows) - production_eligible,
        "evidence_levels": dict(evidence),
        "sources": dict(sources),
        "groups": dict(groups),
        "missing_metadata": {key: sorted(value) for key, value in missing_metadata.items()},
        "invalid": invalid,
        "duplicate_names": duplicate_names,
    }


if __name__ == "__main__":
    import json
    from database import SessionLocal, migrate_schema

    migrate_schema()
    db = SessionLocal()
    try:
        print(json.dumps(audit_exercise_library(db), ensure_ascii=False, indent=2))
    finally:
        db.close()
