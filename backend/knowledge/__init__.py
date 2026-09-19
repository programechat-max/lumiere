"""
Bilgi Katmanı (Knowledge Layer) — Lumiere'in somut veri havuzları.

Modüller:
- cache:            Redis (varsa) + süreç-içi TTL cache yardımcısı
- usda_client:      USDA FoodData Central API istemcisi (public domain veri)
- food_db:          FoodItem kütüphanesi + aday besin seçimi + makro doğrulama
- exercise_library: Kanonik egzersiz kütüphanesi (kaçış vanalı)
- exercise_selector: Geniş kütüphaneden kas grubu/hedef/ekipmana göre EN İYİ
                     hipertrofi hareketlerini rankleyen seçici (Faz 6)
- split_planner:     Gün sayısı+hedefe göre bilimsel split iskeleti (Faz 6)
- science:          Küratörlü araştırma notları + PubMed canlı sorgu (cache'li)
- weak_areas:       Eksik/gelişmeyen kas bölgesi tespiti
- seed_data:        Başlangıç verisi (besinler, egzersizler, araştırma notları)
- seed_knowledge:   Idempotent seed çalıştırıcı (python seed_knowledge.py)
- import_parquet:   0000.parquet -> exercise_library_items toplu import (Faz 6)
- evidence_exercises: Kanıta dayalı hipertrofi egzersiz çekirdeği (Faz 7):
                     kas başları + stimulus_rating + ROM profili + lengthened önceliği
- evidence_topics:  'Neden X yerine Y?' kanıt konu bankası (Jarvis cite motoru)
- volume_landmarks: Kanıta dayalı per-kas MEV/MAV/MRV hacim tablosu (seviye+hedef ölçekli)
- usda_client:      Mikro besin (Na, K, Ca, Fe, Mg, Zn, D, B12, C) dahil FDC verisi

Tasarım ilkeleri:
1. HİBRİT VERİ: Lokal tablo her zaman yeterli; harici API sadece tabloda olmayan
   besin/konularda devreye girer, sonucu kalıcı tabloya yazar.
2. GRACEFUL FALLBACK: USDA/PubMed erişilemezse uygulama asla bozulmaz - sadece
   küratörlü lokal çekirdek kullanılır.
3. TUTARLILIK: AI hareketleri kütüphaneden seçer -> WorkoutLog eşleşmeleri ve
   progression.py string eşleştirmeleri güvenilir çalışır.
4. AKILLI SEÇİM (Faz 6): 600 satırı prompt'a basmak yerine exercise_selector
   kas grubu başına en iyi 8-10 hareketi rankler; split_planner bilimsel iskeletin
   kendisini kurar - AI şablondan çıkamaz.
"""
