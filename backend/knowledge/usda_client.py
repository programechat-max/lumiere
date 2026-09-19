"""
USDA FoodData Central API istemcisi (public domain besin verisi).

API anahtarı (USDA_API_KEY) tanımlı olmasa da demo erişim çalışır ama hız
sınırı düşüktür; üretimde anahtar tanımlanmalı (https://fdc.nal.usda.gov/api-key-signup).

Hata durumunda None döner - çağıran taraf lokal tabloyla devam eder (graceful
fallback, uygulama asla bozulmaz).
"""
import logging
import re
from urllib.parse import quote

from config import settings
from knowledge.cache import TTL_USDA_FOOD, cached

logger = logging.getLogger(__name__)

USDA_BASE_URL = "https://api.nal.usda.gov/fdc/v1"

try:
    import requests
except ImportError:  # pragma: no cover
    requests = None

# USDA dataType önceliği: Foundation + SR Legacy = en doğrulanmış veri
PREFERRED_DATA_TYPES = ["Foundation", "SR Legacy"]

# FAZ 7 — mikro besin alanları: (USDA nutrient kodu/yaygın adı -> FoodItem kolonu)
MICRO_MAP = {
    "Sodium, Na": "sodium_mg",
    "Potassium, K": "potassium_mg",
    "Calcium, Ca": "calcium_mg",
    "Iron, Fe": "iron_mg",
    "Magnesium, Mg": "magnesium_mg",
    "Zinc, Zn": "zinc_mg",
    "Vitamin D (D2 + D3)": "vitamin_d_ug",
    "Vitamin D (D2 + D3), International Units": "vitamin_d_ug",
    "Vitamin D": "vitamin_d_ug",
    "Vitamin B-12": "vitamin_b12_ug",
    "Vitamin C, total ascorbic acid": "vitamin_c_mg",
}
# Günlük referans değerler (mg veya µg) — Jarvis mikro yorumlaması için
MICRO_REFERENCE_DEFAULT = {
    "sodium_mg": 2000.0,
    "potassium_mg": 3500.0,
    "calcium_mg": 1000.0,
    "iron_mg": 14.0,
    "magnesium_mg": 400.0,
    "zinc_mg": 11.0,
    "vitamin_d_ug": 15.0,
    "vitamin_b12_ug": 2.4,
    "vitamin_c_mg": 80.0,
}


def _api_key() -> str:
    return settings.USDA_API_KEY or "DEMO_KEY"


def usda_configured() -> bool:
    return requests is not None


def _query_match_score(query: str, name: str) -> float:
    """Basit ve denetlenebilir kelime örtüşmesi (0-1); sessiz yanlış eşleşmeyi önler."""
    query_words = {w for w in re.findall(r"[a-z0-9]+", (query or "").lower()) if len(w) > 2}
    name_words = set(re.findall(r"[a-z0-9]+", (name or "").lower()))
    if not query_words:
        return 0.0
    return round(sum(word in name_words for word in query_words) / len(query_words), 3)


def _pick_best_nutrients(food: dict) -> dict | None:
    """USDA food objesinden 100g başına makroları + mikro besinleri çıkar.
    Foundation/SR Legacy foodNutrients şeması: {nutrient: {name, unitNumber}}
    FAZ 7: makro + mikro (MICRO_MAP eşleşmesi) tek dict'te."""

    def _nutrient_value(fn: dict):
        value = fn.get("amount")
        if value is None:
            value = fn.get("value")
        return value

    try:
        macro_map = {
            "Energy": "calories",
            "Protein": "protein",
            "Carbohydrate, by difference": "carbs",
            "Total lipid (fat)": "fats",
        }
        result = {}
        micros = {}
        for fn in food.get("foodNutrients", []):
            name = fn.get("nutrient", {}).get("name") or fn.get("nutrientName")
            key = macro_map.get(name)
            if not key:
                # Foundation Foods'ta enerji/yağ varyant isimleri var:
                # "Energy (Atwater Specific Factors)", "Total fat (NLEA)" vb.
                lname = (name or "").lower()
                if lname.startswith("energy"):
                    key = "calories"
                elif lname.startswith("total lipid") or lname.startswith("total fat"):
                    key = "fats"
                elif lname.startswith("carbohydrate"):
                    key = "carbs"
                elif lname == "protein":
                    key = "protein"
            if key:
                value = _nutrient_value(fn)
                # BUG FIX: SR Legacy detay kayıtlarında enerji hem kcal hem kJ birimli
                # iki girdi olarak gelir; döngü son girdiyle eziyordu (4.184x saçmalık).
                # kcal birimli girdiyi tercih et, kJ ise 4.184 ile çevir.
                unit = (fn.get("unitName") or fn.get("unit") or "").lower()
                if key == "calories" and value is not None:
                    if unit == "kj":
                        result["calories"] = round(float(value) / 4.184, 1)
                    else:
                        result.setdefault("calories", float(value or 0))  # ilk kcal girdisi kazanır
                    continue
                if value is not None:
                    result[key] = float(value or 0)
                continue
            # FAZ 7: mikro besin eşleşmesi
            micro_key = MICRO_MAP.get(name or "")
            if micro_key:
                value = _nutrient_value(fn)
                if value is not None:
                    micros[micro_key] = float(value or 0)
        if "calories" not in result:
            return None
        result["micros"] = micros
        return result
    except Exception:
        return None


def search_foods_usda(query: str, limit: int = 5) -> list | None:
    """USDA FDC'de arama yapar, [{name, fdc_id, calories, protein, carbs, fats}]
    listesi döner. Hata/yapılandırılmamış durumda None döner (lokal tabloyla devam)."""
    if requests is None:
        return None
    cache_key = f"knowledge:usda:search:{query.lower().strip()}:{limit}"
    def _producer():
        try:
            params = {
                "api_key": _api_key(),
                "query": query,
                "pageSize": min(limit, 25),
                "dataType": ",".join(PREFERRED_DATA_TYPES),
                "sortBy": "dataType.keyword",
            }
            resp = requests.get(
                f"{USDA_BASE_URL}/foods/search", params=params, timeout=8
            )
            if resp.status_code != 200:
                logger.warning("[USDA] Arama başarısız status=%s query=%s", resp.status_code, query)
                return None
            data = resp.json()
            results = []
            for food in data.get("foods", []):
                macros = _pick_best_nutrients(food)
                if not macros:
                    continue
                results.append({
                    "name": (food.get("description") or "").title()[:120],
                    "fdc_id": food.get("fdcId"),
                    "category": food.get("dataType"),
                    "calories": round(macros.get("calories", 0), 1),
                    "protein": round(macros.get("protein", 0), 1),
                    "carbs": round(macros.get("carbs", 0), 1),
                    "fats": round(macros.get("fats", 0), 1),
                    # FAZ 7: mikro besinler (100g başına, mg/µg)
                    "micros": macros.get("micros", {}),
                    "match_score": _query_match_score(query, food.get("description") or ""),
                })
                if len(results) >= limit:
                    break
            return results or None
        except Exception as exc:
            logger.warning("[USDA] API erişilemedi (lokal tabloyla devam ediliyor): %s", exc)
            return None
    return cached(cache_key, ttl=TTL_USDA_FOOD, producer=_producer)


def get_food_details_usda(fdc_id: int) -> dict | None:
    """FAZ 7 — Tek bir FDC kaydının detayını (makro + mikro) getirir.
    Import scriptinin mevcut USDA satırlarını mikro besinlerle zenginleştirmesi
    (backfill) için kullanılır. Hata durumunda None döner (graceful)."""
    if requests is None or not fdc_id:
        return None
    try:
        # NOT: 'nutrients' filtresi Foundation kayıtlarında enerjiyi düşürüyor
        # (enerji "Energy (Atwater Specific Factors)", 208 dışında). Bu yüzden
        # filtresiz çekiyoruz; isim bazlı eşleşme _pick_best_nutrients'ta yapılıyor.
        resp = requests.get(
            f"{USDA_BASE_URL}/food/{int(fdc_id)}",
            params={"api_key": _api_key()},
            timeout=8,
        )
        if resp.status_code != 200:
            logger.warning("[USDA] Detay sorgusu başarısız status=%s fdc_id=%s", resp.status_code, fdc_id)
            return None
        food = resp.json()
        macros = _pick_best_nutrients(food)
        if not macros:
            return None
        return {
            "fdc_id": food.get("fdcId") or fdc_id,
            "description": (food.get("description") or "").title()[:120],
            "category": food.get("dataType"),
            "calories": macros.get("calories", 0.0),
            "protein": macros.get("protein", 0.0),
            "carbs": macros.get("carbs", 0.0),
            "fats": macros.get("fats", 0.0),
            "micros": macros.get("micros", {}),
        }
    except Exception as exc:
        logger.warning("[USDA] Detay erişilemedi (fdc_id=%s): %s", fdc_id, exc)
        return None
