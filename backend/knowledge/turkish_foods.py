# ============================================
# TÜRK MUTFAĞI GENİŞLETME - FAZ 6
# Mevcut 42 besinin üzerine elle kürasyon (makrolar 100g başına; USDA/
# TÜİK besin kompozisyon tablolarından doğrulanmış yaklaşık değerler).
# Kaynak 'local_tr' | pending_review=False (küratörlü).
# ============================================

TURKISH_FOODS_EXPANSION = [
    # --- Et & tavuk yemekleri ---
    {"name": "Izgara Köfte", "category": "protein_source", "kcal": 240, "p": 21.0, "c": 7.0, "f": 14.0, "portion": 150, "tags": "high_protein", "aliases": "köfte, izgara köfte"},
    {"name": "Etli Güveç", "category": "dish_tr", "kcal": 155, "p": 13.0, "c": 6.0, "f": 9.0, "portion": 300, "tags": "high_protein,gluten_free", "aliases": "güveç"},
    {"name": "Kuzu İncik (haşlama)", "category": "protein_source", "kcal": 235, "p": 19.5, "c": 0.0, "f": 17.0, "portion": 200, "tags": "high_protein,gluten_free,keto", "aliases": "kuzu incik"},
    {"name": "Tavuk Şiş", "category": "protein_source", "kcal": 165, "p": 25.0, "c": 1.0, "f": 6.0, "portion": 150, "tags": "high_protein,gluten_free", "aliases": "tavuk şiş, şiş tavuk"},
    {"name": "Kanat (ızgara)", "category": "protein_source", "kcal": 240, "p": 22.0, "c": 0.0, "f": 16.5, "portion": 200, "tags": "high_protein,gluten_free", "aliases": "tavuk kanat"},
    {"name": "Pastırma", "category": "protein_source", "kcal": 320, "p": 28.0, "c": 1.0, "f": 22.0, "portion": 30, "tags": "high_protein,keto", "aliases": "pastırma"},

    # --- Çorbalar ---
    {"name": "Tarhana Çorbası", "category": "dish_tr", "kcal": 62, "p": 2.2, "c": 8.5, "f": 2.0, "portion": 250, "tags": "vegetarian", "aliases": "tarhana"},
    {"name": "Yayla Çorbası", "category": "dish_tr", "kcal": 58, "p": 2.5, "c": 8.0, "f": 1.6, "portion": 250, "tags": "vegetarian", "aliases": "yayla çorba, yoğurt çorbası"},
    {"name": "İşkembe Çorbası", "category": "dish_tr", "kcal": 85, "p": 6.0, "c": 5.0, "f": 4.5, "portion": 300, "tags": "gluten_free", "aliases": "işkembe"},
    {"name": "Domates Çorbası", "category": "dish_tr", "kcal": 48, "p": 1.4, "c": 7.5, "f": 1.2, "portion": 250, "tags": "vegetarian", "aliases": "domates çorba"},
    {"name": "Şehriyeli Tavuk Suyu Çorbası", "category": "dish_tr", "kcal": 45, "p": 3.0, "c": 5.5, "f": 1.0, "portion": 250, "tags": "", "aliases": "tavuk suyu çorba"},
]

TURKISH_FOODS_EXPANSION += [
    # --- Sulu yemekler & baklagil ---
    {"name": "Kuru Fasulye", "category": "dish_tr", "kcal": 118, "p": 7.0, "c": 16.0, "f": 2.8, "portion": 250, "tags": "vegan,vegetarian,high_protein", "aliases": "fasulye yemeği"},
    {"name": "Nohut Yemeği", "category": "dish_tr", "kcal": 130, "p": 7.2, "c": 18.0, "f": 3.2, "portion": 250, "tags": "vegan,vegetarian,high_protein", "aliases": "nohut"},
    {"name": "Mercimekli Köfte", "category": "dish_tr", "kcal": 150, "p": 6.0, "c": 22.0, "f": 4.0, "portion": 120, "tags": "vegan,vegetarian", "aliases": "mercimek köfte"},
    {"name": "Kıymalı Bamya", "category": "dish_tr", "kcal": 95, "p": 6.5, "c": 7.0, "f": 4.5, "portion": 250, "tags": "", "aliases": "bamya"},
    {"name": "Patlıcan Musakka", "category": "dish_tr", "kcal": 110, "p": 5.0, "c": 9.0, "f": 6.0, "portion": 250, "tags": "vegetarian,gluten_free", "aliases": "musakka"},
    {"name": "Zeytinyağlı Taze Fasulye", "category": "dish_tr", "kcal": 78, "p": 2.2, "c": 9.5, "f": 3.5, "portion": 220, "tags": "vegan,vegetarian,gluten_free", "aliases": "taze fasulye"},
    {"name": "Zeytinyağlı Bezelye", "category": "dish_tr", "kcal": 90, "p": 4.0, "c": 11.0, "f": 3.0, "portion": 220, "tags": "vegan,vegetarian,gluten_free", "aliases": "bezelye yemeği"},
    {"name": "Ispanak (zeytinyağlı)", "category": "dish_tr", "kcal": 55, "p": 2.4, "c": 5.0, "f": 2.8, "portion": 220, "tags": "vegan,vegetarian,gluten_free", "aliases": "zeytinyağlı ıspanak"},

    # --- Dolma & sarma ---
    {"name": "Yaprak Sarma (zeytinyağlı)", "category": "dish_tr", "kcal": 145, "p": 3.0, "c": 20.0, "f": 6.0, "portion": 150, "tags": "vegan,vegetarian", "aliases": "sarma"},
    {"name": "Etli Dolma", "category": "dish_tr", "kcal": 130, "p": 7.5, "c": 13.0, "f": 5.0, "portion": 200, "tags": "", "aliases": "biber dolması"},
    {"name": "Kabak Dolması", "category": "dish_tr", "kcal": 85, "p": 3.2, "c": 10.0, "f": 3.5, "portion": 220, "tags": "vegetarian", "aliases": "kabak dolma"},

    # --- Pilav & bulgur ---
    {"name": "Bulgur Pilavı", "category": "grain", "kcal": 115, "p": 3.8, "c": 22.0, "f": 1.6, "portion": 180, "tags": "vegan,vegetarian", "aliases": "bulgur"},
    {"name": "Şehriyeli Pilav", "category": "grain", "kcal": 150, "p": 3.5, "c": 28.0, "f": 2.8, "portion": 180, "tags": "vegetarian", "aliases": "şehriyeli pirinç pilav"},
    {"name": "Mercimekli Bulgur Pilavı", "category": "grain", "kcal": 122, "p": 4.5, "c": 22.0, "f": 1.8, "portion": 180, "tags": "vegan,vegetarian", "aliases": "mercimekli bulgur"},
    {"name": "Kısır", "category": "dish_tr", "kcal": 160, "p": 4.2, "c": 24.0, "f": 5.0, "portion": 150, "tags": "vegan,vegetarian", "aliases": "kısır, çiğ köfte (kısır)"},
]

TURKISH_FOODS_EXPANSION += [
    # --- Börek & hamur işi ---
    {"name": "Su Böreği", "category": "dish_tr", "kcal": 235, "p": 8.0, "c": 26.0, "f": 11.0, "portion": 150, "tags": "vegetarian", "aliases": "su böreği"},
    {"name": "Ispanaklı Börek", "category": "dish_tr", "kcal": 210, "p": 6.0, "c": 24.0, "f": 10.0, "portion": 150, "tags": "vegetarian", "aliases": "ıspanaklı börek"},
    {"name": "Kıymalı Börek", "category": "dish_tr", "kcal": 245, "p": 9.0, "c": 25.0, "f": 12.0, "portion": 150, "tags": "", "aliases": "kıymalı börek"},
    {"name": "Pide (kıymalı)", "category": "dish_tr", "kcal": 230, "p": 10.0, "c": 28.0, "f": 8.5, "portion": 250, "tags": "", "aliases": "kıymalı pide"},
    {"name": "Lahmacun", "category": "dish_tr", "kcal": 225, "p": 9.5, "c": 27.0, "f": 8.5, "portion": 180, "tags": "", "aliases": "lahmacun"},

    # --- Kahvaltılık & meze ---
    {"name": "Menemen (yağsız)", "category": "dish_tr", "kcal": 95, "p": 6.5, "c": 4.5, "f": 5.5, "portion": 200, "tags": "vegetarian,gluten_free", "aliases": "menemen"},
    {"name": "Çılbır", "category": "dish_tr", "kcal": 135, "p": 7.5, "c": 4.0, "f": 9.5, "portion": 180, "tags": "vegetarian,gluten_free", "aliases": "çılbır"},
    {"name": "Humus", "category": "dish_tr", "kcal": 175, "p": 7.5, "c": 20.0, "f": 7.5, "portion": 60, "tags": "vegan,vegetarian", "aliases": "humus"},
    {"name": "Haydari", "category": "dish_tr", "kcal": 140, "p": 8.0, "c": 5.0, "f": 10.0, "portion": 60, "tags": "vegetarian,gluten_free", "aliases": "haydari"},
    {"name": "Acılı Ezme", "category": "dish_tr", "kcal": 60, "p": 1.5, "c": 7.0, "f": 3.2, "portion": 80, "tags": "vegan,vegetarian,gluten_free", "aliases": "ezme"},
    {"name": "Cacık", "category": "dish_tr", "kcal": 45, "p": 2.6, "c": 3.5, "f": 2.2, "portion": 200, "tags": "vegetarian,gluten_free", "aliases": "cacık"},

    # --- Kebap & ızgara ---
    {"name": "Adana Kebap", "category": "protein_source", "kcal": 250, "p": 19.0, "c": 3.0, "f": 17.5, "portion": 200, "tags": "high_protein", "aliases": "adana kebap"},
    {"name": "Şiş Kebap (kuşbaşı)", "category": "protein_source", "kcal": 195, "p": 23.0, "c": 1.0, "f": 10.5, "portion": 200, "tags": "high_protein,gluten_free", "aliases": "şiş kebap"},
    {"name": "Tavuk Döner", "category": "protein_source", "kcal": 180, "p": 18.0, "c": 8.0, "f": 8.5, "portion": 200, "tags": "high_protein", "aliases": "döner (tavuk)"},
    {"name": "Et Döner", "category": "protein_source", "kcal": 240, "p": 16.5, "c": 9.0, "f": 15.5, "portion": 200, "tags": "high_protein", "aliases": "döner (et)"},
]

TURKISH_FOODS_EXPANSION += [
    # --- Kahvaltı tablosu ekleri ---
    {"name": "Beyaz Peynir (tuzsuz)", "category": "dairy", "kcal": 265, "p": 17.5, "c": 2.0, "f": 21.0, "portion": 50, "tags": "vegetarian,gluten_free,high_protein", "aliases": "beyaz peynir"},
    {"name": "Kaşar Peyniri", "category": "dairy", "kcal": 390, "p": 25.0, "c": 2.2, "f": 32.0, "portion": 40, "tags": "vegetarian,gluten_free,high_protein", "aliases": "kaşar"},
    {"name": "Lor Peyniri", "category": "dairy", "kcal": 90, "p": 13.0, "c": 3.0, "f": 3.0, "portion": 80, "tags": "vegetarian,gluten_free,high_protein", "aliases": "lor"},
    {"name": "Kaymak", "category": "fat", "kcal": 680, "p": 1.0, "c": 1.5, "f": 75.0, "portion": 15, "tags": "keto,gluten_free", "aliases": "kaymak"},
    {"name": "Tahin", "category": "fat", "kcal": 595, "p": 17.0, "c": 21.0, "f": 50.0, "portion": 15, "tags": "vegan,vegetarian,gluten_free", "aliases": "tahin"},
    {"name": "Pekmez", "category": "other", "kcal": 290, "p": 1.0, "c": 71.0, "f": 0.3, "portion": 20, "tags": "vegan,vegetarian,gluten_free", "aliases": "üzüm pekmezi"},
    {"name": "Zeytin (yeşil)", "category": "fat", "kcal": 145, "p": 1.0, "c": 3.8, "f": 15.0, "portion": 30, "tags": "vegan,vegetarian,gluten_free,keto", "aliases": "yeşil zeytin"},
    {"name": "Zeytin (siyah)", "category": "fat", "kcal": 175, "p": 1.2, "c": 6.0, "f": 16.5, "portion": 30, "tags": "vegan,vegetarian,gluten_free,keto", "aliases": "siyah zeytin"},

    # --- Tatlılar & atıştırmalık ---
    {"name": "Künefe", "category": "other", "kcal": 380, "p": 7.0, "c": 42.0, "f": 20.0, "portion": 120, "tags": "vegetarian", "aliases": "künefe"},
    {"name": "Baklava", "category": "other", "kcal": 430, "p": 6.5, "c": 48.0, "f": 24.0, "portion": 60, "tags": "vegetarian", "aliases": "baklava"},
    {"name": "Sütlaç", "category": "other", "kcal": 130, "p": 3.5, "c": 21.0, "f": 3.2, "portion": 150, "tags": "vegetarian", "aliases": "sütlaç"},
    {"name": "Ayran", "category": "dairy", "kcal": 37, "p": 1.9, "c": 3.2, "f": 1.9, "portion": 250, "tags": "vegetarian,gluten_free", "aliases": "ayran"},
    {"name": "Kefir", "category": "dairy", "kcal": 45, "p": 3.2, "c": 4.5, "f": 1.0, "portion": 250, "tags": "vegetarian,gluten_free", "aliases": "kefir"},
    {"name": "Kuru Kayısı", "category": "fruit", "kcal": 240, "p": 3.4, "c": 63.0, "f": 0.5, "portion": 40, "tags": "vegan,vegetarian,gluten_free", "aliases": "kayısı"},
    {"name": "Ceviz", "category": "fat", "kcal": 654, "p": 15.0, "c": 14.0, "f": 65.0, "portion": 30, "tags": "vegan,vegetarian,gluten_free,keto", "aliases": "ceviz"},
    {"name": "Fındık", "category": "fat", "kcal": 628, "p": 15.0, "c": 17.0, "f": 60.0, "portion": 30, "tags": "vegan,vegetarian,gluten_free,keto", "aliases": "fındık"},
    {"name": "Badem", "category": "fat", "kcal": 579, "p": 21.0, "c": 22.0, "f": 50.0, "portion": 30, "tags": "vegan,vegetarian,gluten_free,keto", "aliases": "badem"},
    {"name": "Antep Fıstığı", "category": "fat", "kcal": 560, "p": 20.0, "c": 28.0, "f": 45.0, "portion": 30, "tags": "vegan,vegetarian,gluten_free,keto", "aliases": "fıstık"},
]
