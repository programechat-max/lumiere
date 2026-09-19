"""Besin kütüphanesinin üretim kalite raporu."""
from __future__ import annotations

from collections import Counter

from models import FoodItem
from knowledge.food_quality import assess_food


def audit_food_library(db) -> dict:
    rows = db.query(FoodItem).order_by(FoodItem.id.asc()).all()
    qualities = {row.id: assess_food(row) for row in rows}
    eligible = [row for row in rows if qualities[row.id].eligible]
    quarantined = [row for row in rows if not qualities[row.id].eligible]
    return {
        "total": len(rows),
        "production_eligible": len(eligible),
        "quarantined": len(quarantined),
        "sources": dict(Counter((row.source or "unknown") for row in rows)),
        "categories": dict(Counter((row.category or "other") for row in eligible)),
        "quarantine_reasons": dict(Counter(
            issue for row in quarantined for issue in qualities[row.id].issues
        )),
        "quarantined_items": [
            {"id": row.id, "name": row.name, "issues": list(qualities[row.id].issues)}
            for row in quarantined
        ],
    }


def format_food_audit(report: dict) -> str:
    return "\n".join([
        f"Besin toplamı: {report['total']}",
        f"Üretime uygun: {report['production_eligible']}",
        f"İnceleme karantinası: {report['quarantined']}",
        f"Karantina nedenleri: {report['quarantine_reasons'] or 'yok'}",
    ])


if __name__ == "__main__":
    from database import SessionLocal
    db = SessionLocal()
    try:
        print(format_food_audit(audit_food_library(db)))
    finally:
        db.close()
