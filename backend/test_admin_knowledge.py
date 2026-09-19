"""Bilgi katmanı operasyon uçları (/api/v1/admin/knowledge/*) testleri.

Karantina -> editoryal onay akışının HTTP kapısı; RBAC koruması ve denetim izi
(AuditLog) dahil. Health_check uçları da üretim bütünlük kapısı olarak doğrulanır.
"""
import models
from knowledge.seed_knowledge import seed_all


def _exercise_payload(item: models.ExerciseLibraryItem) -> dict:
    return {
        "id": item.id, "name": item.name, "pending_review": item.pending_review,
        "evidence_level": item.evidence_level, "evidence_source": item.evidence_source,
        "reviewed_by": item.reviewed_by,
    }


def _seeded_item(db_session) -> models.ExerciseLibraryItem:
    """Onaya hazır (tüm metadata dolu) karantina egzersizi üretir."""
    item = models.ExerciseLibraryItem(
        name="Review Queue Exercise", muscle_group="Göğüs", equipment="dumbbell",
        exercise_type="secondary_compound", pending_review=True,
        muscle_head="overall", stimulus_rating=7.5, rom_profile="full",
        technique_cue="Kontrollü hareket", selection_reason="Kademeli yüklenebilir.",
        evidence_refs="PMID:36662126",
    )
    db_session.add(item)
    db_session.commit()
    db_session.refresh(item)
    return item


def test_review_queue_lists_pending_exercises(db_session, client, test_user, auth_headers):
    test_user.role = "ADMIN"
    db_session.commit()
    _seeded_item(db_session)
    res = client.get("/api/v1/admin/knowledge/exercises/review-queue", headers=auth_headers)
    assert res.status_code == 200
    ids = [row["id"] for row in res.json()["items"]]
    assert len(ids) == 1


def test_approve_rejects_incomplete_metadata(db_session, client, test_user, auth_headers):
    test_user.role = "ADMIN"
    db_session.commit()
    item = _seeded_item(db_session)
    item.technique_cue = ""
    db_session.commit()
    res = client.post(
        f"/api/v1/admin/knowledge/exercises/{item.id}/approve",
        headers=auth_headers, json={"review_note": "Eksik metadata."},
    )
    assert res.status_code == 422


def test_approve_opens_exercise_and_writes_audit(db_session, client, test_user, auth_headers):
    test_user.role = "ADMIN"
    db_session.commit()
    item = _seeded_item(db_session)
    res = client.post(
        f"/api/v1/admin/knowledge/exercises/{item.id}/approve",
        headers=auth_headers, json={"review_note": "Metadata ve kullanım profili kontrol edildi."},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["pending_review"] is False
    assert body["evidence_level"] == "expert_curated"
    assert body["evidence_source"] == "manual_review"
    assert body["reviewed_by"] == test_user.email
    db_session.refresh(item)
    assert item.pending_review is False
    log = (db_session.query(models.AuditLog)
           .filter(models.AuditLog.action == "admin.approve_exercise")
           .order_by(models.AuditLog.id.desc()).first())
    assert log is not None and log.actor_user_id == test_user.id
    assert log.resource == f"exercise_library_item:{item.id}"


def test_knowledge_health_reports_seeded_layer(db_session, client, test_user, auth_headers):
    test_user.role = "ADMIN"
    db_session.commit()
    seed_all(db_session)
    res = client.get("/api/v1/admin/knowledge/health", headers=auth_headers)
    assert res.status_code == 200
    report = res.json()
    assert report["ok"] is True
    assert all(check["ok"] for check in report["checks"].values())