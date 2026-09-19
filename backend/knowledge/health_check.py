"""Knowledge layer üretim öncesi bütünlük kapısı.

Bu kontrol klinik yeterlilik iddia etmez; bilgi katmanının beklenen veri
sözleşmelerini ve üretim selector'larının güvenli aday havuzunu doğrular.
"""
from __future__ import annotations

from models import ResearchNote
from knowledge.evidence_exercises import evidence_exercise_count
from knowledge.evidence_topics import EVIDENCE_TOPICS
from knowledge.exercise_audit import audit_exercise_library, VALID_GROUPS
from knowledge.food_audit import audit_food_library
from knowledge.volume_landmarks import VOLUME_LANDMARKS, VOLUME_EVIDENCE
from knowledge.verify_pmid import KNOWN_RESEARCH_PMIDS


def run_health_check(db) -> dict:
    checks: dict[str, dict] = {}

    exercise = audit_exercise_library(db)
    # Audit raporu tüm kayıtları içerir; üretim kapsamını doğrudan DB'den ölç.
    from models import ExerciseLibraryItem
    production_rows = db.query(ExerciseLibraryItem).filter(
        ExerciseLibraryItem.pending_review.is_(False),
        ExerciseLibraryItem.evidence_level == "expert_curated",
    ).all()
    group_counts = {group: sum(1 for row in production_rows if row.muscle_group == group)
                    for group in VALID_GROUPS}
    checks["exercise_library"] = {
        "ok": (
            exercise["production_eligible"] >= evidence_exercise_count()
            and all(count > 0 for count in group_counts.values())
        ),
        "production_eligible": exercise["production_eligible"],
        "expected_curated": evidence_exercise_count(),
        "group_counts": group_counts,
        "missing_evidence_refs": exercise["missing_metadata"]["evidence_refs"],
        "missing_evidence_scope": exercise["missing_metadata"]["evidence_scope"],
    }

    food = audit_food_library(db)
    checks["food_library"] = {
        "ok": food["production_eligible"] > 0,
        "production_eligible": food["production_eligible"],
        "quarantined": food["quarantined"],
    }

    volume_ok = all(
        all(key in landmark for key in ("MEV", "MAV", "MRV", "freq"))
        and landmark["MEV"] <= landmark["MAV"] <= landmark["MRV"]
        and landmark["freq"] >= 1
        and landmark.get("evidence_refs", VOLUME_EVIDENCE["refs"]) == VOLUME_EVIDENCE["refs"]
        and landmark.get("evidence_scope", VOLUME_EVIDENCE["scope"]) == VOLUME_EVIDENCE["scope"]
        and landmark.get("evidence_confidence", VOLUME_EVIDENCE["confidence"]) in {"low", "moderate", "high"}
        for landmark in VOLUME_LANDMARKS.values()
    )
    checks["volume_landmarks"] = {"ok": volume_ok, "groups": len(VOLUME_LANDMARKS)}

    topic_failures = []
    for topic in EVIDENCE_TOPICS:
        for study in topic.get("key_studies", []):
            pmid = str(study.get("pmid") or "")
            if not pmid.isdigit() or study.get("link") != f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/":
                topic_failures.append(topic.get("topic"))
    checks["evidence_topics"] = {
        "ok": not topic_failures,
        "topics": len(EVIDENCE_TOPICS),
        "failures": topic_failures,
    }

    notes = db.query(ResearchNote).filter(ResearchNote.is_active.is_(True)).all()
    note_failures = []
    for note in notes:
        refs = [part.strip().removeprefix("PMID:") for part in (note.evidence_refs or "").split(",") if part.strip()]
        if not refs or any(ref not in KNOWN_RESEARCH_PMIDS for ref in refs):
            note_failures.append(note.title)
    checks["research_notes"] = {
        "ok": bool(notes) and not note_failures,
        "active": len(notes),
        "failures": note_failures,
    }

    return {"ok": all(check["ok"] for check in checks.values()), "checks": checks}


if __name__ == "__main__":
    import json
    import sys
    from database import SessionLocal, migrate_schema
    from knowledge.seed_knowledge import seed_all

    migrate_schema()
    db = SessionLocal()
    try:
        seed_all(db)
        report = run_health_check(db)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        sys.exit(0 if report["ok"] else 1)
    finally:
        db.close()
