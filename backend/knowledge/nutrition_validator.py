"""Deterministik öğün planı kalite kapısı.

LLM'nin beyan ettiği kalori/makrolar, doğrulanmış FoodItem değerlerinden
ayrıdır. Bu modül ikisini karşılaştırır ve planın hedefe gerçek anlamda
yaklaşıp yaklaşmadığını raporlar.
"""
from __future__ import annotations

from collections.abc import Iterable
import re


def _ingredient_parts(item: dict) -> list[str]:
    raw = item.get("ingredients") or item.get("description") or ""
    return [part.strip() for part in re.split(r"[,\n;]+", str(raw)) if len(part.strip()) >= 3]


def _has_explicit_quantity(text: str) -> bool:
    return bool(re.search(r"\d+(?:[.,]\d+)?\s*(?:g|gram|ml|adet|ölçü|kasık|kaşık)", text.lower()))


def _number(value, default=0.0) -> float:
    try:
        return max(0.0, float(value or 0))
    except (TypeError, ValueError):
        return default


def validate_meal_plan(items: Iterable[dict], targets: dict | None = None,
                       dietary_notes: str | None = None, db=None) -> dict:
    errors: list[str] = []
    warnings: list[str] = []
    normalized = list(items or [])
    totals = {key: 0.0 for key in ("calories", "protein", "carbs", "fats")}
    matched_ingredients = 0
    unresolved_ingredients = 0
    for index, item in enumerate(normalized, 1):
        name = item.get("meal_name") or f"Öğün {index}"
        values = {key: _number(item.get(key)) for key in totals}
        if not str(item.get("meal_name") or "").strip():
            errors.append(f"{name}: öğün adı eksik.")
        if values["calories"] <= 0:
            errors.append(f"{name}: kalori değeri pozitif olmalı.")
        macro_kcal = values["protein"] * 4 + values["carbs"] * 4 + values["fats"] * 9
        if macro_kcal and abs(macro_kcal - values["calories"]) / values["calories"] > 0.2:
            warnings.append(f"{name}: kalori-makro hesabı %20'den fazla sapıyor.")
        for key in totals:
            totals[key] += values[key]
        if db is not None:
            # Bu kapı yalnızca mevcut yerel/USDA kaydını okur; doğrulama sırasında
            # yeni, incelenmemiş besin yazılması güven sınırını aşar.
            from knowledge.food_db import resolve_food_name, _clean_ingredient_name
            from knowledge.food_quality import is_food_production_eligible
            parts = _ingredient_parts(item)
            item_matched = 0
            item_unresolved = 0
            unresolved_parts = []
            for part in parts:
                food = resolve_food_name(db, _clean_ingredient_name(part), save_unresolved=False)
                if food is not None and is_food_production_eligible(food):
                    matched_ingredients += 1
                    item_matched += 1
                else:
                    unresolved_ingredients += 1
                    item_unresolved += 1
                    unresolved_parts.append(part)
            if parts and item_matched == 0:
                errors.append(f"{name}: hiçbir malzeme doğrulanmış besin kaydına eşleşmedi.")
            elif parts and item_unresolved:
                if any(_has_explicit_quantity(part) for part in unresolved_parts):
                    errors.append(f"{name}: miktarı belirtilen bir veya daha fazla malzeme doğrulanamadı.")
                else:
                    warnings.append(f"{name}: bazı ölçüsüz tamamlayıcı malzemeler doğrulanamadı.")

    targets = targets or {}
    deviations = {}
    for key in totals:
        target = _number(targets.get(key))
        if target:
            deviations[key] = round((totals[key] - target) / target, 3)
    if deviations.get("calories", 0) and abs(deviations["calories"]) > 0.15:
        errors.append("Günlük kalori hedefi %15'ten fazla sapıyor.")
    if deviations.get("protein", 0) < -0.20:
        errors.append("Günlük protein hedefi %20'den fazla eksik.")

    notes = (dietary_notes or "").lower()
    joined = " ".join(str(item.get("description") or "") for item in normalized).lower()
    forbidden = ()
    if "vegan" in notes:
        forbidden = ("tavuk", "et", "balık", "somon", "yumurta", "yoğurt", "peynir", "whey")
    elif "vejetaryen" in notes or "vegetarian" in notes:
        forbidden = ("tavuk", "et", "balık", "somon")
    found = [word for word in forbidden if word in joined]
    if found:
        errors.append(f"Diyet kısıtlaması ihlali görüldü: {', '.join(found)}.")

    return {"valid": not errors, "errors": errors, "warnings": warnings,
            "totals": {key: round(value, 1) for key, value in totals.items()},
            "deviations": deviations,
            "ingredient_coverage": {
                "matched": matched_ingredients,
                "unresolved": unresolved_ingredients,
            }}


def assert_valid_meal_plan(*args, **kwargs) -> dict:
    report = validate_meal_plan(*args, **kwargs)
    if not report["valid"]:
        raise ValueError("Öğün planı bilgi katmanı doğrulamasından geçmedi: " + " | ".join(report["errors"]))
    return report
