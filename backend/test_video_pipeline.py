import json
from types import SimpleNamespace

import ai_core
import models


def test_physique_media_persists_normalized_structured_analysis(db_session, test_user, monkeypatch):
    class FakeModel:
        def __init__(self, *args, **kwargs):
            pass

        def generate_content(self, *args, **kwargs):
            return SimpleNamespace(text=json.dumps({
                "report": "Gözlem raporu",
                "memory_summary": "Sırt önceliği gözlendi.",
                "training_instruction": "Sırt hacmini artır.",
                "focus_regions": ["Sırt", "uydurma serbest metin"],
                "observations": ["Tekrarlanan yapılandırılmış gözlem"],
                "confidence": "high",
            }))

    monkeypatch.setattr(ai_core, "_GenerativeModel", FakeModel)
    result = ai_core.analyze_physique_media(
        b"fake-image", "image/jpeg", db=db_session, user_id=test_user.id
    )

    assert result["program_eligible"] is True
    assert result["focus_regions"] == ["Sırt"]
    memory = db_session.query(models.UserMemory).filter(
        models.UserMemory.user_id == test_user.id,
        models.UserMemory.category == "onboarding_video_analysis",
    ).first()
    assert memory is not None
    assert json.loads(memory.content)["confidence"] == "high"
    assert db_session.query(models.UserMemory).filter(
        models.UserMemory.user_id == test_user.id,
        models.UserMemory.category == "physique_analysis",
    ).count() == 0


def test_empty_observations_are_not_program_eligible():
    result = ai_core._normalize_physique_analysis({
        "focus_regions": ["Sırt"], "observations": [], "confidence": "high"
    })
    assert result["program_eligible"] is False
    assert result["focus_regions"] == []


def test_build_system_prompt_exposes_only_eligible_structured_video(db_session, test_user):
    db_session.add(models.UserMemory(
        user_id=test_user.id,
        category="onboarding_video_analysis",
        content=json.dumps({
            "report": "SERBEST_RAPOR_SIZMAMALI",
            "memory_summary": "SERBEST_OZET_SIZMAMALI",
            "focus_regions": ["Sırt"],
            "observations": ["Yapılandırılmış gözlem"],
            "confidence": "high",
            "program_eligible": True,
        }),
    ))
    db_session.commit()

    prompt = ai_core.build_system_prompt(db_session, test_user.id)

    assert "ONBOARDING VİDEO ANALİZİ" in prompt
    assert '"focus_regions": ["Sırt"]' in prompt
    assert "SERBEST_RAPOR_SIZMAMALI" not in prompt
    assert "SERBEST_OZET_SIZMAMALI" not in prompt


def test_build_system_prompt_hides_ineligible_video(db_session, test_user):
    db_session.add(models.UserMemory(
        user_id=test_user.id,
        category="onboarding_video_analysis",
        content=json.dumps({
            "focus_regions": ["Sırt"],
            "observations": ["Düşük güvenli gözlem"],
            "confidence": "low",
            "program_eligible": False,
        }),
    ))
    db_session.commit()

    prompt = ai_core.build_system_prompt(db_session, test_user.id)

    assert "ONBOARDING VİDEO ANALİZİ" not in prompt
    assert "Düşük güvenli gözlem" not in prompt
