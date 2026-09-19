import pytest

from knowledge.nutrition_validator import validate_meal_plan
from knowledge.seed_knowledge import seed_all


@pytest.fixture
def seeded_food_db(db_session, monkeypatch):
    monkeypatch.setattr("config.settings.USDA_FALLBACK_ENABLED", False)
    seed_all(db_session)
    return db_session


def test_meal_validator_rejects_large_target_deviation():
    report = validate_meal_plan(
        [{"meal_name": "Kahvaltı", "description": "yumurta", "calories": 100,
          "protein": 10, "carbs": 5, "fats": 2}],
        targets={"calories": 2000, "protein": 140},
    )
    assert report["valid"] is False
    assert any("kalori" in error.lower() for error in report["errors"])


def test_meal_validator_rejects_vegan_violation():
    report = validate_meal_plan(
        [{"meal_name": "Öğle", "description": "150g tavuk ve pirinç", "calories": 500,
          "protein": 40, "carbs": 45, "fats": 12}],
        dietary_notes="vegan",
    )
    assert report["valid"] is False
    assert any("diyet" in error.lower() for error in report["errors"])


def test_unresolved_ingredients_cannot_be_marked_verified(seeded_food_db):
    report = validate_meal_plan(
        [{"meal_name": "Öğün", "description": "250g hayali süper gıda",
          "calories": 400, "protein": 30, "carbs": 40, "fats": 10}],
        db=seeded_food_db,
    )
    assert report["valid"] is False
    assert report["ingredient_coverage"] == {"matched": 0, "unresolved": 1}


def test_unresolved_ingredient_with_quantity_is_error(seeded_food_db):
    report = validate_meal_plan(
        [{"meal_name": "Öğün", "description": "150g tavuk göğsü, 100g hayali garnitür",
          "calories": 300, "protein": 40, "carbs": 10, "fats": 8}],
        db=seeded_food_db,
    )
    assert report["valid"] is False
    assert report["ingredient_coverage"] == {"matched": 1, "unresolved": 1}
    assert any("miktarı belirtilen" in error for error in report["errors"])
