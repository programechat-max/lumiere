"""Karantinadaki egzersizler için açık ve izlenebilir onay kapısı."""
from __future__ import annotations

import datetime

from models import ExerciseLibraryItem
from knowledge.exercise_library import VALID_EQUIPMENT, VALID_TYPES
from knowledge.exercise_audit import VALID_GROUPS
from knowledge.verify_pmid import KNOWN_RESEARCH_PMIDS

REQUIRED_REVIEW_FIELDS = (
    "muscle_head", "stimulus_rating", "rom_profile", "selection_reason", "technique_cue",
    "evidence_refs",
)
VALID_ROM = {"full", "lengthened", "shortened", "partial", "isometric"}


def approve_exercise(db, exercise_id: int, reviewer: str, review_note: str) -> ExerciseLibraryItem:
    """Eksiksiz editoryal inceleme sonrası tek bir egzersizi üretime açar."""
    item = db.query(ExerciseLibraryItem).filter(ExerciseLibraryItem.id == exercise_id).first()
    if item is None:
        raise ValueError("Egzersiz bulunamadı.")
    if not reviewer or not review_note:
        raise ValueError("Onay için reviewer ve review_note zorunludur.")
    if item.muscle_group not in VALID_GROUPS:
        raise ValueError("Geçersiz kas grubu.")
    if item.equipment not in VALID_EQUIPMENT or item.exercise_type not in VALID_TYPES:
        raise ValueError("Geçersiz ekipman veya egzersiz tipi.")
    if item.rom_profile not in VALID_ROM:
        raise ValueError("Geçerli ROM profili zorunludur.")
    if any(getattr(item, field) in (None, "") for field in REQUIRED_REVIEW_FIELDS):
        raise ValueError("Kas başı, uyarım puanı, ROM, teknik ipucu ve seçim gerekçesi tamamlanmalı.")
    if not 0 <= float(item.stimulus_rating) <= 10:
        raise ValueError("stimulus_rating 0-10 aralığında olmalı.")
    refs = [part.strip() for part in (item.evidence_refs or "").split(",") if part.strip()]
    allowed_refs = {f"PMID:{pmid}" for pmid in KNOWN_RESEARCH_PMIDS}
    if not refs or any(ref not in allowed_refs for ref in refs):
        raise ValueError("En az bir doğrulanmış PMID referansı zorunlu.")

    item.pending_review = False
    item.evidence_level = "expert_curated"
    item.evidence_source = "manual_review"
    if item.evidence_scope not in {"direct", "muscle_group", "general_mechanistic"}:
        item.evidence_scope = "general_mechanistic"
    item.reviewed_by = reviewer.strip()[:120]
    item.reviewed_at = datetime.datetime.utcnow()
    item.review_note = review_note.strip()[:1000]
    db.commit()
    db.refresh(item)
    return item


def list_review_queue(db, limit: int = 100) -> list[dict]:
    rows = (db.query(ExerciseLibraryItem)
            .filter(ExerciseLibraryItem.pending_review.is_(True))
            .order_by(ExerciseLibraryItem.id.asc()).limit(limit).all())
    return [{
        "id": row.id, "name": row.name, "muscle_group": row.muscle_group,
        "equipment": row.equipment, "exercise_type": row.exercise_type,
        "missing": [field for field in REQUIRED_REVIEW_FIELDS if getattr(row, field) in (None, "")],
    } for row in rows]
