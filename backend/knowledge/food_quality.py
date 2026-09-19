"""Üretim besin kayıtları için ortak güvenilirlik kapısı.

Besin kayıtları yalnızca güvenilir bir kaynaktan gelmeli, makro değerleri
fiziksel olarak mümkün olmalı ve bekleyen inceleme kuyruğunda olmamalıdır.
Bu kontrol prompt aday havuzu ile öğün doğrulamasında aynı şekilde kullanılır.
"""
from __future__ import annotations

from dataclasses import dataclass


TRUSTED_FOOD_SOURCES = {"local_tr", "usda"}


@dataclass(frozen=True)
class FoodQuality:
    eligible: bool
    issues: tuple[str, ...]


def assess_food(food) -> FoodQuality:
    issues: list[str] = []
    if getattr(food, "pending_review", False):
        issues.append("pending_review")
    if (getattr(food, "source", None) or "") not in TRUSTED_FOOD_SOURCES:
        issues.append("untrusted_source")

    values = [
        getattr(food, "calories_per_100g", None),
        getattr(food, "protein_per_100g", None),
        getattr(food, "carbs_per_100g", None),
        getattr(food, "fats_per_100g", None),
    ]
    if any(value is None for value in values):
        issues.append("missing_macro")
    elif any(float(value) < 0 for value in values):
        issues.append("negative_macro")
    elif float(values[0]) <= 0 or float(values[0]) > 1000:
        issues.append("invalid_calories")
    else:
        macro_kcal = 4 * float(values[1]) + 4 * float(values[2]) + 9 * float(values[3])
        # Lifli/alkol ve USDA yuvarlaması nedeniyle küçük sapmaya izin verilir;
        # büyük sapma bozuk veya yanlış eşleşmiş kayda işaret eder.
        if macro_kcal and not 0.55 <= float(values[0]) / macro_kcal <= 1.35:
            issues.append("macro_calorie_inconsistency")

    score = getattr(food, "match_score", None)
    if getattr(food, "usda_fdc_id", None) and score is not None and float(score) < 0.5:
        issues.append("low_match_score")
    return FoodQuality(eligible=not issues, issues=tuple(issues))


def is_food_production_eligible(food) -> bool:
    return assess_food(food).eligible
