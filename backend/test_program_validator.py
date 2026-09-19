import pytest

from knowledge.program_validator import validate_program, validate_split_compliance
from knowledge.seed_knowledge import seed_all


@pytest.fixture
def seeded_exercise_db(db_session):
    seed_all(db_session)
    return db_session


def test_validator_rejects_invalid_set_count():
    programs = [{
        "day_name": "Pazartesi",
        "exercises": [{
            "name": "Incline Barbell Bench Press", "muscle_group": "Göğüs",
            "target_sets": 9, "target_reps": "8-12",
        }],
    }]
    report = validate_program(programs, level="intermediate", goal="recomp")
    assert report["valid"] is False
    assert any("1-8" in error for error in report["errors"])


def test_validator_reports_low_volume_but_accepts_safe_program():
    programs = [{
        "day_name": "Pazartesi",
        "exercises": [{
            "name": "Incline Barbell Bench Press", "muscle_group": "Göğüs",
            "target_sets": 3, "target_reps": "8-12",
        }],
    }]
    report = validate_program(programs, level="intermediate", goal="recomp")
    assert report["valid"] is True
    assert report["warnings"]


def test_validator_reports_missing_muscle_heads(seeded_exercise_db):
    report = validate_program([{
        "day_name": "Push",
        "exercises": [{
            "name": "Cable Lateral Raise", "muscle_group": "Omuz",
            "target_sets": 6, "target_reps": "12-15",
        }],
    }], db=seeded_exercise_db)
    assert report["valid"] is True
    assert "Omuz" in report["head_coverage"]
    assert any("kas başı kapsaması" in warning for warning in report["warnings"])


def test_split_validator_rejects_missing_template_group():
    report = validate_split_compliance(
        [{"day_name": "Push A", "exercises": [
            {"muscle_group": "Göğüs", "name": "x", "target_sets": 3}
        ]}],
        [{"day_title": "Push A", "focus": "Göğüs", "groups": ["Göğüs", "Omuz", "Triceps"]}],
    )
    assert report["valid"] is False
    assert any("kas grupları eksik" in error for error in report["errors"])


def test_validator_rejects_unknown_muscle_group():
    report = validate_program([{
        "day_name": "Pazartesi",
        "exercises": [{"name": "Incline Barbell Bench Press", "muscle_group": "Boyun", "target_sets": 3}],
    }])
    assert report["valid"] is False
    assert any("bilinmeyen kas grubu" in error for error in report["errors"])


def test_validator_rejects_library_muscle_mismatch(seeded_exercise_db):
    report = validate_program([{
        "day_name": "Pazartesi",
        "exercises": [{
            "name": "Incline Barbell Bench Press", "muscle_group": "Sırt",
            "target_sets": 3, "target_reps": "8-12",
        }],
    }], db=seeded_exercise_db)
    assert report["valid"] is False
    assert any("kas grubu uyuşmuyor" in error for error in report["errors"])


def test_split_validator_rejects_unexpected_template_group():
    report = validate_split_compliance(
        [{"day_name": "Push A", "exercises": [
            {"muscle_group": "Göğüs", "name": "x", "target_sets": 3},
            {"muscle_group": "Quadriceps", "name": "y", "target_sets": 3},
        ]}],
        [{"day_title": "Push A", "focus": "Göğüs", "groups": ["Göğüs"]}],
    )
    assert report["valid"] is False
    assert any("ek kas grupları" in error for error in report["errors"])
