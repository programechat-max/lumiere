"""AI üretim fonksiyonları ile knowledge kapılarının uçtan uca testleri."""
import json
from types import SimpleNamespace

import ai_core
import crud
from knowledge.food_db import resolve_food_name
from knowledge.seed_knowledge import seed_all


class _FakeModel:
    response_text = "[]"

    def __init__(self, *args, **kwargs):
        pass

    def generate_content(self, *args, **kwargs):
        return SimpleNamespace(text=self.response_text)


def test_generate_meal_plan_runs_food_pool_and_validator(db_session, test_user, monkeypatch):
    seed_all(db_session)
    foods = [
        resolve_food_name(db_session, "tavuk göğsü", save_unresolved=False),
        resolve_food_name(db_session, "yulaf", save_unresolved=False),
        resolve_food_name(db_session, "pirinç", save_unresolved=False),
    ]
    portions = [200, 100, 300]
    totals = {
        key: sum((getattr(food, f"{key}_per_100g") or 0) * portion / 100
                 for food, portion in zip(foods, portions))
        for key in ("calories", "protein", "carbs", "fats")
    }
    crud.update_profile(db_session, {
        "daily_calorie_target": totals["calories"],
        "daily_protein_target": totals["protein"],
        "daily_carb_target": totals["carbs"],
        "daily_fat_target": totals["fats"],
    }, user_id=test_user.id)

    _FakeModel.response_text = json.dumps([
        {"meal_name": "Öğün 1", "time_target": "08:00", "description": "200g tavuk göğsü (ızgara)",
         "calories": 1, "protein": 1, "carbs": 1, "fats": 1},
        {"meal_name": "Öğün 2", "time_target": "12:00", "description": "100g yulaf",
         "calories": 1, "protein": 1, "carbs": 1, "fats": 1},
        {"meal_name": "Öğün 3", "time_target": "18:00", "description": "300g pirinç (haşlanmış)",
         "calories": 1, "protein": 1, "carbs": 1, "fats": 1},
    ])
    monkeypatch.setattr(ai_core, "_GenerativeModel", _FakeModel)

    result = ai_core.generate_meal_plan(
        db_session, save=False, user_id=test_user.id, raise_on_error=True
    )
    assert len(result) == 3
    assert sum(item.calories for item in result) == round(totals["calories"])


def test_generate_workout_program_runs_library_and_split_gates(db_session, test_user, monkeypatch):
    seed_all(db_session)
    _FakeModel.response_text = json.dumps([
        {"day_name": "Full Body A", "exercises": [
            {"name": "Incline Dumbbell Press", "target_sets": 1, "target_reps": "6-10", "muscle_group": "Göğüs"},
            {"name": "Chest-Supported Row", "target_sets": 1, "target_reps": "8-12", "muscle_group": "Sırt"},
            {"name": "ATG Back Squat", "target_sets": 1, "target_reps": "6-10", "muscle_group": "Quadriceps"},
            {"name": "Hanging Leg Raise", "target_sets": 1, "target_reps": "10-15", "muscle_group": "Karın"},
        ]},
        {"day_name": "Full Body B", "exercises": [
            {"name": "Chest-Supported Row", "target_sets": 1, "target_reps": "8-12", "muscle_group": "Sırt"},
            {"name": "Overhead Barbell Press", "target_sets": 1, "target_reps": "6-10", "muscle_group": "Omuz"},
            {"name": "Romanian Deadlift", "target_sets": 1, "target_reps": "6-10", "muscle_group": "Hamstring & Glute"},
        ]},
        {"day_name": "Full Body C", "exercises": [
            {"name": "Cable Crossover", "target_sets": 1, "target_reps": "10-15", "muscle_group": "Göğüs"},
            {"name": "ATG Back Squat", "target_sets": 1, "target_reps": "6-10", "muscle_group": "Quadriceps"},
            {"name": "Incline Dumbbell Curl", "target_sets": 1, "target_reps": "10-15", "muscle_group": "Biceps"},
            {"name": "Cable Triceps Pushdown", "target_sets": 1, "target_reps": "10-15", "muscle_group": "Triceps"},
        ]},
    ])
    monkeypatch.setattr(ai_core, "_GenerativeModel", _FakeModel)

    result = ai_core.generate_workout_program(
        db_session, save=False, user_id=test_user.id, questionnaire={"days_per_week": 3},
        raise_on_error=True,
    )
    assert len(result) == 3
    assert result[0].day_name == "Full Body A"
