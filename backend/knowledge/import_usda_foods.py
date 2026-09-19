"""USDA FoodData Central bulk import - FAZ 6.

42 küratörlü besini ~300-500'e çıkarır: temel besin listesini (staples) USDA
FDC'de sorgular, FDPIR (Foundation/SR Legacy) kayıtlarından makroları alır ve
`source='usda'` + `pending_review=False` (FDPIR = otoriter) olarak tabloya yazar.
Idempotent: aynı isim + kaynağa ait kayıt varsa atlar.

Kullanım:
    cd backend && ../.venv/bin/python -m knowledge.import_usda_foods
İsteğe bağlı:  --limit N (varsayılan 300), --per-query N (varsayılan 6)
"""
from __future__ import annotations

import argparse
import logging
import re
import time

from database import SessionLocal
from models import FoodItem
from knowledge.usda_client import search_foods_usda, get_food_details_usda

logger = logging.getLogger(__name__)

# Temel besin çekirdeği: AI öğün planlarının gerçekten kullandığı temel gıdalar.
# Türkçe sorgu -> USDA İngilizce arama terimi.
STAPLE_QUERIES: list[tuple[str, str]] = [
    # protein kaynakları
    ("tavuk göğsü", "chicken breast, raw"), ("hindi göğsü", "turkey breast, raw"),
    ("dana bonfile", "beef sirloin, raw"), ("dana kıyma", "ground beef, raw"),
    ("kuzu pirzola", "lamb chop, raw"), ("somon", "atlantic salmon, raw"),
    ("ton balığı", "canned tuna in water"), ("sardalya", "canned sardines in oil"),
    ("karides", "shrimp, raw"), ("morina", "cod fillet, raw"),
    ("yumurta", "egg, whole, raw"), ("yumurta beyazı", "egg white, raw"),
    ("süzme yoğurt", "greek yogurt, plain"), ("yoğurt", "yogurt, plain, whole milk"),
    ("labne", "labneh"), ("süt", "milk, whole"), ("az yağlı süt", "milk, 1% fat"),
    ("lor peyniri", "cottage cheese"), ("cheddar", "cheddar cheese"),
    ("mozzarella", "mozzarella cheese, whole milk"), ("parmesan", "parmesan cheese"),
    ("kaburga", "pork loin, raw"), ("dana dil", "beef tongue"),
    ("karaciğer", "beef liver, raw"), ("kalp", "beef heart"),
    # tahıllar & baklagiller
    ("yulaf", "oats, dry rolled"), ("pirinç (beyaz)", "white rice, dry"),
    ("pirinç (esmer)", "brown rice, dry"), ("bulgur (kuru)", "bulgur, dry"),
    ("kinoa", "quinoa, dry"), ("makarna (kuru)", "pasta, dry, enriched"),
    ("tam buğday makarna", "whole wheat pasta, dry"), ("kuskus", "couscous, dry"),
    ("beyaz ekmek", "white bread"), ("tam buğday ekmeği", "whole wheat bread"),
    ("çavdar ekmeği", "rye bread"), ("tortilla", "flour tortilla"),
    ("kuru fasulye (kuru)", "kidney beans, dry"), ("nohut (kuru)", "chickpeas, dry"),
    ("mercimek (kuru)", "lentils, dry"), ("maş fasulyesi", "mung beans, dry"),
    ("börülce", "black-eyed peas, dry"), ("soya fasulyesi", "soybeans, dry"),
    ("tofu", "tofu, firm"), ("tempeh", "tempeh"),
    # sebzeler
    ("brokoli", "broccoli, raw"), ("karnabahar", "cauliflower, raw"),
    ("ıspanak", "spinach, raw"), ("kabak", "zucchini, raw"),
    ("patlıcan", "eggplant, raw"), ("domates", "tomato, raw"),
    ("salatalık", "cucumber, raw"), ("biber (yeşil)", "green bell pepper, raw"),
    ("soğan", "onion, raw"), ("sarımsak", "garlic, raw"),
    ("havuç", "carrot, raw"), ("pancar", "beetroot, raw"),
    ("lahana", "cabbage, raw"), ("marul", "lettuce, romaine"),
    ("roka", "arugula, raw"), ("maydanoz", "parsley, raw"),
    ("mantar", "white mushroom, raw"), ("mısır", "sweet corn, raw"),
    ("tatlı patates", "sweet potato, raw"), ("patates", "potato, raw"),
    ("kuşkonmaz", "asparagus, raw"), ("pırasa", "leek, raw"),
    ("kereviz", "celery, raw"), ("turp", "radish, raw"),
    ("enginar", "globe artichoke, raw"), ("bamya", "okra, raw"),
    # meyveler
    ("elma", "apple, raw"), ("muz", "banana, raw"),
    ("portakal", "orange, raw"), ("mandalina", "tangerine, raw"),
    ("üzüm", "grapes, raw"), ("çilek", "strawberries, raw"),
    ("karpuz", "watermelon, raw"), ("kavun", "cantaloupe, raw"),
    ("şeftali", "peach, raw"), ("armut", "pear, raw"),
    ("ananas", "pineapple, raw"), ("mango", "mango, raw"),
    ("kiwi", "kiwifruit, raw"), ("nar", "pomegranate, raw"),
    ("erik", "plum, raw"), ("kiraz", "cherries, raw"),
    ("limon", "lemon, raw"), ("avokado", "avocado, raw"),
    ("incir (taze)", "figs, raw"), ("hurma (taze)", "dates, medjool"),
    # yağlar & kuruyemiş
    ("zeytinyağı", "olive oil, extra virgin"), ("ayçiçek yağı", "sunflower oil"),
    ("tereyağı", "butter, salted"), ("tereyağı (sade)", "ghee"),
    ("hindistan cevizi yağı", "coconut oil"), ("avokado yağı", "avocado oil"),
    ("ceviz (kuru)", "walnuts"), ("badem (kuru)", "almonds"),
    ("fındık (kuru)", "hazelnuts"), ("fıstık (kuru)", "pistachios"),
    ("kaju", "cashews"), ("yer fıstığı", "peanuts, raw"),
    ("fıstık ezmesi", "peanut butter"), ("badem ezmesi", "almond butter"),
    ("chia tohumu", "chia seeds"), ("keten tohumu", "flaxseed"),
    ("kabak çekirdeği", "pumpkin seeds"), ("ayçekirdeği", "sunflower kernels"),
    # diğer / tamamlayıcı
    ("bal", "honey"), ("tahin (kuru)", "sesame seeds, whole"),
    ("hurma (kuru)", "dried dates"), ("kuru incir", "dried figs"),
    ("kuru üzüm", "raisins"), ("kuru kayısı (kuru)", "dried apricots"),
    ("whey protein", "whey protein isolate"), ("kazein", "casein protein powder"),
    ("mısır nişastası", "corn starch"), ("kakao (toz)", "cocoa powder, unsweetened"),
]

# FDPIR (Foundation Foods / SR Legacy) önceliği - otoriter analiz kayıtları
_PREFERRED_DATA_TYPES = {"Foundation", "SR Legacy"}


def _pick_best_filtered(hits: list[dict], en_query: str) -> dict | None:
    """Sorgu terimine göre alaka filtresi uygular (import scriptinin kullanacağı).
    Tam-phrase değil KELİME bazlı: 'canned tuna in water' -> {canned, tuna, water};
    kayıt adında en az yarıdan fazlası geçmeli, yoksa None (yanlış besin yazma riski)."""
    global en_keywords
    terms = [t.strip() for t in re.split(r"[,(]", en_query) if t.strip()]
    words: set[str] = set()
    for t in terms:
        for w in t.split():
            w = w.lower()
            if len(w) > 2 and w not in ("and", "the", "for"):
                words.add(w)
    en_keywords = words
    try:
        if not hits:
            return None

        def _score(hit: dict) -> tuple:
            desc = (hit.get("name") or "").lower()
            matched = sum(1 for w in en_keywords if w in desc)
            is_foundation = 0 if hit.get("category") == "Foundation" else 1
            return (-matched, is_foundation, hit.get("fdc_id", 0))

        pool = sorted(hits, key=_score)
        top = pool[0]
        # Ana kelime muayenesi: en az 1 anahtar kelime eşleşmezse kayma sayılır.
        top_matched = -_score(top)[0]
        if top_matched < max(1, len(en_keywords) // 2):
            return None
        top["match_score"] = round(top_matched / max(1, len(en_keywords)), 3)
        if top["match_score"] < 0.5:
            return None
        return top
    finally:
        en_keywords = set()


# alaka kontrolü için modül-seviyesi durum (tek iş parçacıklı CLI script)
en_keywords: set = set()


def _slug(text: str) -> str:
    """'Chicken Breast, Raw' -> 'chicken breast raw' (ad karşılaştırma normalizasyonu)."""
    return re.sub(r"[^a-z0-9 ]", "", (text or "").lower()).strip()


def import_staple_foods(limit: int = 300, per_query: int = 6, sleep_s: float = 0.4) -> dict:
    """Temel besin çekirdeğini USDA'dan çeker ve FoodItem tablosuna yazar."""
    from sqlalchemy import func

    db = SessionLocal()
    added = skipped = failed = 0
    try:
        existing_names = {
            _slug(n) for (n,) in db.query(FoodItem.name).all()
        }
        existing_fdc = {
            f for (f,) in db.query(FoodItem.usda_fdc_id).filter(FoodItem.usda_fdc_id.isnot(None)).all()
        }

        for tr_name, en_query in STAPLE_QUERIES:
            if added >= limit:
                break
            # idempotency: bu sorgunun TR adı zaten tabloda mı? (usda kaynaklı da olsa local_tr da olsa)
            slug_tr = _slug(tr_name)
            if slug_tr in existing_names:
                skipped += 1
                continue

            hits = search_foods_usda(en_query, limit=per_query)
            best = _pick_best_filtered(hits, en_query)
            if not best or not best.get("fdc_id"):
                failed += 1
                logger.warning("[USDA_IMPORT] Sonuç yok: %s (%s)", tr_name, en_query)
                continue
            if best["fdc_id"] in existing_fdc:
                skipped += 1
                continue

            item = FoodItem(
                name=tr_name,
                aliases=best["name"][:120],
                category=_guess_category(tr_name, best),
                calories_per_100g=best["calories"],
                protein_per_100g=best["protein"],
                carbs_per_100g=best["carbs"],
                fats_per_100g=best["fats"],
                source="usda",
                usda_fdc_id=best["fdc_id"],
                match_score=best.get("match_score"),
                dietary_tags=_guess_dietary_tags(best),
                pending_review=False,
                # FAZ 7: mikro besinler (100g başına, mg/µg)
                sodium_mg=(best.get("micros") or {}).get("sodium_mg"),
                potassium_mg=(best.get("micros") or {}).get("potassium_mg"),
                calcium_mg=(best.get("micros") or {}).get("calcium_mg"),
                iron_mg=(best.get("micros") or {}).get("iron_mg"),
                magnesium_mg=(best.get("micros") or {}).get("magnesium_mg"),
                zinc_mg=(best.get("micros") or {}).get("zinc_mg"),
                vitamin_d_ug=(best.get("micros") or {}).get("vitamin_d_ug"),
                vitamin_b12_ug=(best.get("micros") or {}).get("vitamin_b12_ug"),
                vitamin_c_mg=(best.get("micros") or {}).get("vitamin_c_mg"),
            )
            db.add(item)
            db.commit()  # her kayıt ayrı commit - yarıda kesilse bile veri korunur
            existing_names.add(slug_tr)
            existing_fdc.add(best["fdc_id"])
            added += 1
            time.sleep(sleep_s)  # USDA rate-limit nezaketi

        db.commit()
        total = db.query(func.count(FoodItem.id)).scalar()
        logger.info("[USDA_IMPORT] Tamamlandı: +%d eklendi, %d atlandı, %d başarısız. Toplam besin: %d",
                    added, skipped, failed, total)
        return {"added": added, "skipped": skipped, "failed": failed, "total": total}
    finally:
        db.close()


def backfill_micros(limit: int = 100, sleep_s: float = 0.4) -> dict:
    """FAZ 7 — Mevcut USDA kaynaklı FoodItem satırlarının mikro kolonlarını FDC
    detail (food/{id}) uç noktasından doldurur. Idempotent: mikro verisi zaten
    dolu satırlar atlanır; kritik makrolar tutarlıysa yazılmaz (güvenli etiket)."""
    from sqlalchemy import func

    db = SessionLocal()
    updated = skipped = failed = 0
    try:
        rows = (
            db.query(FoodItem)
            .filter(FoodItem.usda_fdc_id.isnot(None))
            .filter(
                # yarım dolu satırlar da kuyruğa girsin: herhangi bir mikro kolon
                # boşsa detail'den tamamlanır (güvenli etiket sadece boş kolonlara yazar)
                FoodItem.sodium_mg.is_(None)
                | FoodItem.potassium_mg.is_(None)
                | FoodItem.calcium_mg.is_(None)
                | FoodItem.iron_mg.is_(None)
                | FoodItem.magnesium_mg.is_(None)
                | FoodItem.zinc_mg.is_(None)
                | FoodItem.vitamin_d_ug.is_(None)
                | FoodItem.vitamin_b12_ug.is_(None)
                | FoodItem.vitamin_c_mg.is_(None)
            )
            .limit(limit)
            .all()
        )
        logger.info("[USDA_BACKFILL] %d satır mikro zenginleştirme kuyruğunda.", len(rows))
        for item in rows:
            detail = get_food_details_usda(item.usda_fdc_id)
            if not detail:
                failed += 1
                time.sleep(sleep_s)
                continue
            micros = detail.get("micros") or {}
            if not micros:
                # kayıt Foundation/SR Legacy mikro içermiyor - tekrar denememek için
                # Na kolonunu 0.0 ile işaretle (0 gerçek 0'dır, None = bilinmiyor)
                item.sodium_mg = 0.0
                updated += 1
            else:
                item.sodium_mg = micros.get("sodium_mg", 0.0)
                item.potassium_mg = micros.get("potassium_mg")
                item.calcium_mg = micros.get("calcium_mg")
                item.iron_mg = micros.get("iron_mg")
                item.magnesium_mg = micros.get("magnesium_mg")
                item.zinc_mg = micros.get("zinc_mg")
                item.vitamin_d_ug = micros.get("vitamin_d_ug")
                item.vitamin_b12_ug = micros.get("vitamin_b12_ug")
                item.vitamin_c_mg = micros.get("vitamin_c_mg")
                updated += 1
            db.commit()
            time.sleep(sleep_s)  # USDA rate-limit nezaketi
        total = db.query(func.count(FoodItem.id)).scalar()
        logger.info("[USDA_BACKFILL] Tamamlandı: %d güncellendi, %d başarısız. Toplam besin: %d",
                    updated, failed, total)
        return {"updated": updated, "failed": failed, "total": total}
    finally:
        db.close()


def _guess_category(tr_name: str, best: dict) -> str:
    n = (tr_name or "").lower()
    if any(k in n for k in ("tavuk", "hindi", "dana", "kuzu", "somon", "ton", "sardalya",
                            "karides", "morina", "yumurta", "kaburga", "karaciğer", "kalp",
                            "dil", "bonfile", "kıyma", "pirzola")):
        return "protein_source"
    if any(k in n for k in ("süt", "yoğurt", "peynir", "labne", "whey", "kazein")):
        return "dairy"
    if any(k in n for k in ("yağ", "tereyağı", "ceviz", "badem", "fındık", "fıstık", "kaju",
                            "chia", "keten", "çekirdek", "avokado")):
        return "fat"
    if any(k in n for k in ("elma", "muz", "portakal", "mandalina", "üzüm", "çilek", "karpuz",
                            "kavun", "şeftali", "armut", "ananas", "mango", "kiwi", "nar",
                            "erik", "kiraz", "limon", "incir", "hurma", "kayısı")):
        return "fruit"
    if any(k in n for k in ("brokoli", "karnabahar", "ıspanak", "kabak", "patlıcan", "domates",
                            "salatalık", "biber", "soğan", "sarımsak", "havuç", "pancar",
                            "lahana", "marul", "roka", "maydanoz", "mantar", "mısır", "patates",
                            "kuşkonmaz", "pırasa", "kereviz", "turp", "enginar", "bamya")):
        return "vegetable"
    if any(k in n for k in ("yulaf", "pirinç", "bulgur", "kinoa", "makarna", "kuskus", "ekmek",
                            "tortilla", "fasulye", "nohut", "mercimek", "börülce", "tofu",
                            "tempeh", "soya")):
        return "grain"
    return "other"


def _guess_dietary_tags(best: dict) -> str:
    tags = []
    p, kcal = best.get("protein", 0.0), best.get("calories", 0.0)
    if p >= 15:
        tags.append("high_protein")
    # hayvansal/vegetarian kaba tahmin - doğru etiketleme resolve aşamasında kullanıcı
    # tercihleriyle birleşir; burada mühürsüz bırakmak yerine temel etiket veriyoruz
    return ",".join(tags)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="USDA temel besin bulk import + mikro backfill")
    parser.add_argument("--limit", type=int, default=300, help="maksimum eklenecek besin sayısı")
    parser.add_argument("--per-query", type=int, default=6, help="sorgu başına USDA sonuç sayısı")
    parser.add_argument("--backfill-micros", action="store_true",
                        help="yeni kayıt ekleme; mevcut USDA satırlarının mikro kolonlarını FDC detail'den doldur")
    parser.add_argument("--backfill-limit", type=int, default=100, help="backfill'de işlenecek maksimum satır")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s: %(message)s")
    if args.backfill_micros:
        summary = backfill_micros(limit=args.backfill_limit)
        print(f"✅ USDA mikro backfill bitti: {summary}")
    else:
        summary = import_staple_foods(limit=args.limit, per_query=args.per_query)
        print(f"✅ USDA import bitti: {summary}")
