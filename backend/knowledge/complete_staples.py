"""FAZ 7 — Eksik staples tamamlama geçişi.

`import_usda_foods` ilk geçişte sonuçsuz kalan sorgular için: SR Legacy odaklı
ham arama + katı anahtar-kelime eşleşmesi + detail (kJ-fix'li) + makro sanity
kapısı. Uyan kayıt yoksa yazmaz, "failed" listesinde bildirir (elle kürasyona
bırakır). Idempotent: tabloda TR adı olan staple'ları atlar.

Kullanım: cd backend && ../.venv/bin/python -m knowledge.complete_staples
"""
from __future__ import annotations

import logging
import re
import time

from database import SessionLocal
from models import FoodItem
from knowledge.usda_client import get_food_details_usda, _api_key, USDA_BASE_URL
from knowledge.import_usda_foods import STAPLE_QUERIES, _guess_category, _guess_dietary_tags, _slug

logger = logging.getLogger(__name__)

try:
    import requests
except ImportError:  # pragma: no cover
    requests = None

# çoklu-bileşen/yanlış-kategori tuzakları
_EXCLUDE_WORDS = ("mix", "mixture", "combination", "combo", "starter", "formula",
                  "infant", "entree", "flavored", "flavour", "seasoned", "breaded",
                  "battered", "frozen entree", "with other", "prepared entr")


def _sig_words(en_query: str) -> list[str]:
    words = []
    for w in re.sub(r"[^a-z0-9 ]", " ", en_query.lower()).split():
        if len(w) > 2 and w not in ("raw", "and", "with", "from") and w not in words:
            words.append(w)
    return words


def _search_sr_legacy(en_query: str, page_size: int = 8) -> list[dict]:
    """SR Legacy odaklı ham arama (client'in Foundation-önceliğine ek takip)."""
    if requests is None:
        return []
    try:
        resp = requests.get(
            f"{USDA_BASE_URL}/foods/search",
            params={"api_key": _api_key(), "query": en_query,
                    "pageSize": page_size, "dataType": "SR Legacy"},
            timeout=10,
        )
        time.sleep(0.6)
        if resp.status_code != 200:
            logger.warning("[COMPLETE] arama basarisiz status=%s q=%s", resp.status_code, en_query)
            return []
        return resp.json().get("foods", []) or []
    except Exception as exc:
        logger.warning("[COMPLETE] arama hatasi q=%s: %s", en_query, exc)
        return []


def _sanity_ok(kcal: float, p: float, k: float, y: float) -> bool:
    est = 4 * (p or 0) + 4 * (k or 0) + 9 * (y or 0)
    if est <= 0 or kcal <= 0 or kcal > 950:
        return False
    return est * 0.6 <= kcal <= est * 1.35


def _pick_candidate(en_query: str, foods: list[dict]) -> dict | None:
    words = _sig_words(en_query)
    if not words:
        return None
    scored = []
    for f in foods:
        desc_l = (f.get("description") or "").lower()
        if any(w in desc_l for w in _EXCLUDE_WORDS):
            continue
        matches = sum(1 for w in words if w in desc_l)
        stem_matches = sum(1 for w in words if any(dw.startswith(w[:5]) for dw in desc_l.split()))
        if max(matches, stem_matches) < max(1, len(words) - 1):
            continue
        scored.append((max(matches, stem_matches), f.get("fdcId"), f.get("description", "")))
    if not scored:
        return None
    scored.sort(key=lambda t: (-t[0], t[1]))
    return {"fdc_id": scored[0][1], "description": scored[0][2], "matched": scored[0][0], "total": len(words)}


def complete_staples(sleep_s: float = 1.1) -> dict:
    db = SessionLocal()
    added, skipped, failed = 0, 0, 0
    failed_items: list[tuple[str, str]] = []
    try:
        existing = {_slug(n) for (n,) in db.query(FoodItem.name).all()}
        for tr_name, en_query in STAPLE_QUERIES:
            if _slug(tr_name) in existing:
                skipped += 1
                continue
            cand = _pick_candidate(en_query, _search_sr_legacy(en_query))
            if not cand or not cand.get("fdc_id"):
                failed += 1
                failed_items.append((tr_name, "aday yok"))
                logger.warning("[COMPLETE] aday yok: %s (%s)", tr_name, en_query)
                continue
            det = get_food_details_usda(cand["fdc_id"])
            if not det or not _sanity_ok(det["calories"], det["protein"], det["carbs"], det["fats"]):
                failed += 1
                reason = f"sanity/detail basarisiz fdc={cand['fdc_id']} {cand['description']}" if det else f"detail alinamadi fdc={cand['fdc_id']}"
                failed_items.append((tr_name, reason))
                logger.warning("[COMPLETE] sanity basarisiz: %s -> %s", tr_name, cand)
                time.sleep(0.4)
                continue
            db.add(FoodItem(
                name=tr_name,
                aliases=det["description"][:120],
                category=_guess_category(tr_name, det),
                calories_per_100g=round(det["calories"], 1),
                protein_per_100g=round(det["protein"], 1),
                carbs_per_100g=round(det["carbs"], 1),
                fats_per_100g=round(det["fats"], 1),
                source="usda",
                usda_fdc_id=det["fdc_id"],
                dietary_tags=_guess_dietary_tags(det),
                pending_review=False,
                sodium_mg=(det.get("micros") or {}).get("sodium_mg"),
                potassium_mg=(det.get("micros") or {}).get("potassium_mg"),
                calcium_mg=(det.get("micros") or {}).get("calcium_mg"),
                iron_mg=(det.get("micros") or {}).get("iron_mg"),
                magnesium_mg=(det.get("micros") or {}).get("magnesium_mg"),
                zinc_mg=(det.get("micros") or {}).get("zinc_mg"),
                vitamin_d_ug=(det.get("micros") or {}).get("vitamin_d_ug"),
                vitamin_b12_ug=(det.get("micros") or {}).get("vitamin_b12_ug"),
                vitamin_c_mg=(det.get("micros") or {}).get("vitamin_c_mg"),
            ))
            db.commit()
            existing.add(_slug(tr_name))
            added += 1
            print(f"  + {tr_name}: [{det['description']}] kcal={det['calories']} P={det['protein']} K={det['carbs']} Y={det['fats']}")
            time.sleep(sleep_s)
        return {"added": added, "skipped": skipped, "failed": failed, "failed_items": failed_items}
    finally:
        db.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s: %(message)s")
    summary = complete_staples()
    print(f"✅ Staples tamamlama bitti: added={summary['added']} skipped={summary['skipped']} failed={summary['failed']}")
    for tr, reason in summary["failed_items"]:
        print(f"   ! {tr}: {reason}")
