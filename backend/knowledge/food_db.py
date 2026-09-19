"""
FoodItem kütüphanesi — aday besin seçimi, USDA fallback ve makro doğrulama.

generate_meal_plan akışı:
1. search_candidate_foods(): diyet kısıtları + hedefe uyum + kategori karışımıyla
   lokal tablodan aday besin listesi (AI SADECE bu adaylardan seçer).
2. Tabloda olmayan bir malzeme adı gelirse resolve_food_name(): önce tabloda
   eşleşme ara, yoksa USDA'da ara (sonucu tabloya yaz, ai_added + pending_review).
3. verify_and_fix_meal_plan(): plan üretildikten sonra makroları tablodan yeniden
   hesapla; sapma %5'i aşarsa porsiyon gramajını düzelt.
"""
import logging
import re

from sqlalchemy.orm import Session

from models import FoodItem
from knowledge.usda_client import search_foods_usda
from knowledge.food_quality import is_food_production_eligible
from config import settings

logger = logging.getLogger(__name__)

MAX_ADAPT_CALORIE_DEV = 0.05  # %5 sapma sınırı (plan kuralıyla tutarlı)


def _norm(text: str) -> str:
    return " ".join((text or "").strip().lower().split())


def _diet_allows(dietary_notes: str | None, tags: set) -> bool:
    """Kullanıcının diyet kısıt notları ile besinin tag kümesi uyumlu mu?
    - Vegan: mutlaka 'vegan' tag'i taşımalı (hayvansal içerik hariç).
    - Vejetaryen: 'vegan' veya 'vegetarian' tag'i yeterli.
    - Glutensiz: 'gluten_free' tag'i zorunlu.
    - Laktozsuz/süt alerjisi: 'lactose_free' zorunlu (vegan ürünler de uygundur).
    Boş not her şeye izin verir; bilinmeyen kısıtlar yok sayılır (graceful)."""
    notes = _norm(dietary_notes)
    if not notes:
        return True
    if "vegan" in notes:
        if "vegan" not in tags:
            return False
    elif "vejetaryen" in notes or "vegetarian" in notes:
        if "vegan" not in tags and "vegetarian" not in tags:
            return False
    if "gluten" in notes or "glutensiz" in notes:
        if "gluten_free" not in tags:
            return False
    if "laktoz" in notes or "lactose" in notes or "süt" in notes or "sut" in notes:
        if "lactose_free" not in tags and "vegan" not in tags:
            return False
    return True


def search_candidate_foods(db: Session, dietary_notes: str | None = None, limit_per_category: int = 10) -> list[dict]:
    """Lokal tablodan diyet kısıtlarına uyan aday besinleri kategori karışımıyla döndürür.
    AI prompt'una bu liste besin ADAY HAVUZU olarak girer."""
    foods = [
        food for food in db.query(FoodItem).all()
        if is_food_production_eligible(food)
    ]

    candidates = []
    for f in foods:
        tags = {_norm(t) for t in (f.dietary_tags or "").split(",") if t}
        if not _diet_allows(dietary_notes, tags):
            continue
        candidates.append(f)

    # Kategori başına sınır: havuz çok büyümesin (prompt bütçesi)
    by_category = {}
    for f in candidates:
        by_category.setdefault(f.category or "other", []).append(f)
    selected = []
    for cat, items in sorted(by_category.items()):
        # protein yoğunluk sırasıyla ilk N tanesi
        items.sort(key=lambda x: (x.protein_per_100g or 0), reverse=True)
        for f in items[:limit_per_category]:
            selected.append({
                "name": f.name,
                "category": f.category,
                "calories_per_100g": f.calories_per_100g,
                "protein_per_100g": f.protein_per_100g,
                "carbs_per_100g": f.carbs_per_100g,
                "fats_per_100g": f.fats_per_100g,
                "typical_portion_g": f.typical_portion_g,
            })
    return selected


def format_candidate_pool(db: Session, dietary_notes: str | None = None,
                          limit_per_category: int = 10) -> str:
    """Doğrulanmış besin adaylarını deterministik prompt metnine çevirir.

    Besin tablosu boşsa modelin uydurma makro/malzeme üretmesine izin verilmez;
    üst akış validator'da planı durdurur.
    """
    candidates = search_candidate_foods(
        db, dietary_notes=dietary_notes, limit_per_category=limit_per_category
    )
    if not candidates:
        return (
            "ÜRETİM DURDURULMALI: bu diyet kısıtları için doğrulanmış besin "
            "adayı bulunamadı. Besin/makro uydurma."
        )
    lines = []
    for food in candidates:
        lines.append(
            f"{food['name']} ({food.get('category') or 'other'}): "
            f"{food['calories_per_100g']:.1f} kcal, "
            f"P {food['protein_per_100g']:.1f}g, "
            f"K {food['carbs_per_100g']:.1f}g, "
            f"Y {food['fats_per_100g']:.1f}g / 100g"
        )
    return "\n".join(lines)


def resolve_food_name(db: Session, name: str, save_unresolved: bool = True) -> FoodItem | None:
    """Bir malzeme adını tabloda eşleştir; bulunamazsa USDA'da ara ve tabloya yaz.
    Çekim eklerine dayanıklı içerir-mantığı; çok kelimeli adaylarda ('tavuk göğsü
    ızgara' gibi) önce tüm metin, olmazsa kelime kademeli kısaltılmış hali denenir."""
    norm = _norm(name)
    if not norm:
        return None

    # 1) Birebir / takma ad eşleşmesi (SQL içerir-mantığı, çekim eklerine dayanıklı)
    # Aday sorguları: önce tam metin, sonra pişirme yöntemi/bağlaç kelimeleri
    # ayıklanarak kısaltılmış isimler, en son çekim eki kırpılmış stem.
    candidate_queries = []
    candidate_queries.append(norm)
    tokens = [t for t in norm.split() if len(t) >= 3]
    for k in range(min(3, len(tokens)) - 1, 0, -1):
        phrase = " ".join(tokens[:k])
        if len(phrase) >= 4:
            candidate_queries.append(phrase)
    stem = norm[:-2] if len(norm) > 5 else norm  # son çekim eklerini kırp ("tavuğu" -> "tavuk")
    if stem != norm and stem not in candidate_queries:
        candidate_queries.append(stem)

    def _word_match(q: str, item: FoodItem) -> bool:
        """Kelime sınırına duyarlı tam kelime geçişi (örn. 'yumurta' adı
        'menemen yumurtalı' alias'ıyla EŞLEŞMEMELİ; 'yumurta (haşlanmış)' ile eşleşmeli)."""
        pattern = re.compile(rf"(?<![a-zçğıöşü0-9]){re.escape(q)}(?![a-zçğıöşü0-9])")
        return bool(pattern.search(_norm(item.name)) or pattern.search(_norm(item.aliases or "")))

    first_contains = None
    for q in dict.fromkeys(candidate_queries):
        rows = (
            db.query(FoodItem)
            .filter(FoodItem.name.ilike(f"%{q}%") | FoodItem.aliases.ilike(f"%{q}%"))
            .order_by(FoodItem.pending_review.asc(), FoodItem.id.asc())
            .all()
        )
        if not rows:
            continue
        exact = next((r for r in rows if _word_match(q, r)), None)
        if exact:
            return exact
        if first_contains is None:
            first_contains = rows[0]
    if first_contains:
        return first_contains

    # 2) USDA fallback (cache'li) — bulunursa tabloya kalıcı yaz
    if settings.USDA_FALLBACK_ENABLED:
        usda_results = search_foods_usda(name, limit=1)
        if usda_results:
            best = usda_results[0]
            if float(best.get("match_score", 0.0)) < 0.5:
                logger.warning("[FOOD_DB] USDA eşleşmesi düşük güvenle reddedildi: %s -> %s (%.2f)",
                               name, best.get("name"), best.get("match_score", 0.0))
                return None
            existing = db.query(FoodItem).filter(FoodItem.usda_fdc_id == best["fdc_id"]).first()
            if existing:
                return existing
            micros = best.get("micros", {})
            item = FoodItem(
                name=best["name"][:120],
                aliases=norm,
                category="usda_imported",
                calories_per_100g=best["calories"],
                protein_per_100g=best["protein"],
                carbs_per_100g=best["carbs"],
                fats_per_100g=best["fats"],
                typical_portion_g=100,
                source="ai_added",
                usda_fdc_id=best["fdc_id"],
                match_score=float(best.get("match_score", 0.0)),
                # Canlı USDA eşleşmesi kalıcı olacaksa inceleme kuyruğuna girer.
                # save_unresolved=False çağrısında ise yalnızca transient nesne
                # döndürülür; üretim tablosuna sessizce yazılmaz.
                pending_review=save_unresolved,
                # FAZ 7: USDA'dan gelen mikro besinler (100g başına)
                sodium_mg=micros.get("sodium_mg"),
                potassium_mg=micros.get("potassium_mg"),
                calcium_mg=micros.get("calcium_mg"),
                iron_mg=micros.get("iron_mg"),
                magnesium_mg=micros.get("magnesium_mg"),
                zinc_mg=micros.get("zinc_mg"),
                vitamin_d_ug=micros.get("vitamin_d_ug"),
                vitamin_b12_ug=micros.get("vitamin_b12_ug"),
                vitamin_c_mg=micros.get("vitamin_c_mg"),
            )
            if save_unresolved:
                db.add(item)
                db.commit()
                db.refresh(item)
                logger.info("[FOOD_DB] USDA adayı inceleme kuyruğuna eklendi: %s (fdc_id=%s)", item.name, item.usda_fdc_id)
            return item
    return None


def seed_turkish_expansion(db: Session) -> int:
    """FAZ 6 — Türk mutfağı genişletmesini (knowledge.turkish_foods) tabloya ekler.
    Idempotent: aynı isimde kayıt varsa atlar. Yeni eklenen besin sayısını döner."""
    from knowledge.turkish_foods import TURKISH_FOODS_EXPANSION

    existing = {row[0].lower() for row in db.query(FoodItem.name).all()}
    added = 0
    for spec in TURKISH_FOODS_EXPANSION:
        if spec["name"].lower() in existing:
            continue
        item = FoodItem(
            name=spec["name"],
            aliases=spec.get("aliases", ""),
            category=spec.get("category", "dish_tr"),
            calories_per_100g=spec["kcal"],
            protein_per_100g=spec["p"],
            carbs_per_100g=spec["c"],
            fats_per_100g=spec["f"],
            typical_portion_g=spec.get("portion"),
            source="local_tr",
            dietary_tags=spec.get("tags", ""),
            pending_review=False,
        )
        db.add(item)
        existing.add(spec["name"].lower())
        added += 1
    if added:
        db.commit()
    return added


def _seed_turkish_expansion(db: Session) -> None:
    """Uygulama açılışında Türk mutfağı genişletmesini (idempotent) uygula."""
    try:
        seed_turkish_expansion(db)
    except Exception as exc:  # noqa: BLE001
        logger.warning("[FOOD_DB] Türk besin genişletmesi atlandı: %s", exc)


def _extract_portion_g(text: str, default_portion: int | None) -> float:
    """Malzeme metninden gramaj çıkar: '150g ızgara tavuk' -> 150.0, yoksa porsiyon varsayımı."""
    match = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:g|gram)\b", (text or "").lower())
    if match:
        return float(match.group(1).replace(",", "."))
    return float(default_portion or 100)


def _clean_ingredient_name(text: str) -> str:
    """Malzeme adından arama için gürültüyü atar: baştaki gramaj ('150g tavuk' -> 'tavuk'),
    parantez notu ('(ızgara)' -> ''), bağlaçlar. Kalori/makro için porsiyon gramajı
    ayrıca _extract_portion_g ile orijinal metinden alınır."""
    cleaned = (text or "").lower()
    cleaned = re.sub(r"^\s*\d+(?:[.,]\d+)?\s*(?:g|gram)\b", " ", cleaned)  # baştaki gramaj
    cleaned = re.sub(r"[\(\[].*?[\)\]]", " ", cleaned)                      # parantez içeriği
    cleaned = re.sub(r"\b(?:ve|with|ile)\b", " ", cleaned)                  # bağlaçlar
    return " ".join(cleaned.split())


def verify_and_fix_meal_plan(db: Session, plan_items: list[dict]) -> tuple[list[dict], bool]:
    """Plan makrolarını tablodan yeniden hesaplar; AI'nın beyan ettiği öğün
    kalorisi doğrulanmış tablo değerinden %5'ten fazla sapıyorsa AI değerleri
    atılıp DOĞRU tablo değerleri yazılır. İkinci dönüş: düzeltme yapıldı mı.
    Malzeme eşleşemezse AI değerleri olduğu gibi korunur (graceful)."""
    if not plan_items:
        return plan_items, False
    fixed = False
    result = []
    for item in plan_items:
        item = dict(item)
        ingredients = item.get("ingredients") or item.get("description") or ""
        computed = {"calories": 0.0, "protein": 0.0, "carbs": 0.0, "fats": 0.0}
        matched_any = False
        # Malzeme satırlarını virgül/satır bazında ayır
        parts = re.split(r"[,\n;]+", ingredients)
        for part in parts:
            part = part.strip()
            if not part or len(part) < 3:
                continue
            food = resolve_food_name(db, _clean_ingredient_name(part), save_unresolved=False)
            if not food or not is_food_production_eligible(food):
                continue
            matched_any = True
            portion = _extract_portion_g(part, food.typical_portion_g)
            factor = portion / 100.0
            computed["calories"] += (food.calories_per_100g or 0) * factor
            computed["protein"] += (food.protein_per_100g or 0) * factor
            computed["carbs"] += (food.carbs_per_100g or 0) * factor
            computed["fats"] += (food.fats_per_100g or 0) * factor

        if matched_any and item.get("calories"):
            declared = float(item["calories"] or 0)
            if declared > 0 and computed["calories"] > 0:
                dev_ratio = abs(computed["calories"] - declared) / declared
                if dev_ratio > MAX_ADAPT_CALORIE_DEV:
                    # AI tahmini doğrulanan değerden sapıyor: düzeltme gerekli.
                    fixed = True
        if matched_any:
            # Beyan edilen makrolar yerine tablodan hesaplanan DOĞRU değerleri yaz.
            item["calories"] = round(computed["calories"], 0)
            item["protein"] = round(computed["protein"], 1)
            item["carbs"] = round(computed["carbs"], 1)
            item["fats"] = round(computed["fats"], 1)
        result.append(item)
    return result, fixed


# --- FAZ 7: ELLE (METİN) ÖĞÜN GİRİŞİ DOĞRULAMA ------------------------------
# Kullanıcı "150g tavuk göğsü, 180g pirinç, salata" gibi elle girer; bu fonksiyon
# tarifi malzemelere ayırır, her malzemeyi FoodItem tablosunda/USDA'da eşleştirir
# ve makro + MİKRO değerleri doğrulanmış tablo verisinden hesaplar. LLM tahmini
# kullanılmaz - sadece gramaj (porsiyon) tahmini LLM'dendir, besin değerleri kod
# tarafından doğrulanmış veriden gelir.

def _micro_from_item(food: FoodItem, factor: float) -> dict:
    """Bir besin kaydının mikro besinlerini porsiyon faktörüyle ölçekler."""
    return {
        "sodium_mg": round((food.sodium_mg or 0) * factor, 1),
        "potassium_mg": round((food.potassium_mg or 0) * factor, 1),
        "calcium_mg": round((food.calcium_mg or 0) * factor, 1),
        "iron_mg": round((food.iron_mg or 0) * factor, 2),
        "magnesium_mg": round((food.magnesium_mg or 0) * factor, 1),
        "zinc_mg": round((food.zinc_mg or 0) * factor, 2),
        "vitamin_d_ug": round((food.vitamin_d_ug or 0) * factor, 2),
        "vitamin_b12_ug": round((food.vitamin_b12_ug or 0) * factor, 2),
        "vitamin_c_mg": round((food.vitamin_c_mg or 0) * factor, 1),
    }


def verify_manual_meal(db: Session, description: str, llm_portion_hints: list[dict] | None = None,
                       dietary_notes: str | None = None) -> dict:
    """Elle girilen öğün tarifini doğrulanmış makro + mikro değerlerine çevirir.

    description: "150g tavuk göğsü, 180g pirinç, 1 kase çorba"
    llm_portion_hints: LLM'in tespit ettiği [{"ingredient": "tavuk göğsü", "portion_g": 150}]
                       (opsiyonel - gramaj tahminini LLM yapar ama değerleri kod doğrular)

    Döndürür:
      {
        "items": [{"name", "portion_g", "calories", "protein", "carbs", "fats",
                   "fiber_g", "micros", "source", "matched_food_id", "confidence"}],
        "totals": {"calories", "protein", "carbs", "fats", "fiber_g", "micros"},
        "verified_count": N, "unresolved": ["..."],
        "validation_source": "usda|local_db|llm_estimate"
      }
    """
    from knowledge.usda_client import MICRO_REFERENCE_DEFAULT

    items: list[dict] = []
    unresolved: list[str] = []

    # LLM gramaj ipuçları varsa onları kullan, yoksa metni virgül/satır bazında ayır
    parts: list[tuple[str, float | None]] = []
    if llm_portion_hints:
        for hint in llm_portion_hints:
            ing = (hint.get("ingredient") or "").strip()
            if ing:
                parts.append((ing, hint.get("portion_g")))
    else:
        for part in re.split(r"[,\n;+]", description or ""):
            part = part.strip()
            if part and len(part) >= 3:
                parts.append((part, None))

    for raw_part, hinted_g in parts:
        clean = _clean_ingredient_name(raw_part)
        if not clean:
            continue
        food = resolve_food_name(db, clean, save_unresolved=False)
        if not food or not is_food_production_eligible(food):
            unresolved.append(clean)
            continue
        # Porsiyon: LLM ipucu > metindeki gramaj ('150g') > tipik porsiyon varsayımı
        portion = hinted_g if hinted_g else _extract_portion_g(raw_part, food.typical_portion_g or 100)
        portion_assumed = False
        if portion <= 0:
            # FAZ 8 (Protocol B): belirsiz gramajda standart ağırlık kullanıldı -
            # kullanıcıya açıkça belirtilir (portion_assumed=True)
            portion = float(food.typical_portion_g or 100)
            portion_assumed = True
        elif not hinted_g and _extract_portion_g(raw_part, None) is None:
            portion_assumed = True
        factor = portion / 100.0

        # Kaynak sınıflandırması: fdc_id'li veya USDA'dan import edilmiş her şey "usda",
        # tablodaki küratörlü kayıtlar (local_tr/seed) "local_db" — ikisi de DOĞRULANMIŞ.
        src_raw = (food.source or "local_db")
        if src_raw == "usda" or src_raw == "ai_added" or food.usda_fdc_id:
            source = "usda"
        else:
            source = "local_db"
        match_score = float(food.match_score if food.match_score is not None else 1.0)
        confidence = "high" if match_score >= 0.8 else "medium" if match_score >= 0.5 else "low"
        items.append({
            "name": food.name,
            "portion_g": round(portion, 1),
            "portion_assumed": portion_assumed,
            "calories": round((food.calories_per_100g or 0) * factor, 1),
            "protein": round((food.protein_per_100g or 0) * factor, 1),
            "carbs": round((food.carbs_per_100g or 0) * factor, 1),
            "fats": round((food.fats_per_100g or 0) * factor, 1),
            "fiber_g": round((food.fiber_per_100g or 0) * factor, 1),
            "micros": _micro_from_item(food, factor),
            "source": source,
            "matched_food_id": food.id,
            "match_score": round(match_score, 3),
            "confidence": confidence,
        })

    totals_micro = {k: 0.0 for k in MICRO_REFERENCE_DEFAULT}
    for it in items:
        for k in totals_micro:
            totals_micro[k] += it.get("micros", {}).get(k, 0)

    # Doğrulama kaynağı: en az bir USDA eşleşmesi varsa "usda", tablo kaydı varsa
    # "local_db"; hiçbir malzeme eşleşmediyse "llm_estimate" (AI tahmini fallback).
    if not items:
        dominant_source = "llm_estimate"
    elif any(it["source"] == "usda" for it in items):
        dominant_source = "usda"
    else:
        dominant_source = "local_db"

    totals = {
        "calories": round(sum(it["calories"] for it in items), 1),
        "protein": round(sum(it["protein"] for it in items), 1),
        "carbs": round(sum(it["carbs"] for it in items), 1),
        "fats": round(sum(it["fats"] for it in items), 1),
        "fiber_g": round(sum(it.get("fiber_g", 0) for it in items), 1),
        "micros": {k: round(v, 2) for k, v in totals_micro.items()},
    }

    return {
        "items": items,
        "totals": totals,
        "verified_count": len(items),
        "unresolved": unresolved,
        "validation_source": dominant_source,
        "portion_hint_used": bool(llm_portion_hints),
        # FAZ 8 (Protocol B): standart ağırlık varsayılan malzemeler - yanıtta açıkça belirtilir
        "assumed_portions": [it["name"] for it in items if it.get("portion_assumed")],
    }
