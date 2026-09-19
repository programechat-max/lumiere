# Yeni Kullanıcı Akış Diyagramları (Arkplan Gerçek Kod Karşılıkları)

Bu dosyadaki diyagramlar **Mermaid** formatındadır; GitHub, VS Code (Mermaid eklentisi),
Notion ve mermaid.live adresinde doğrudan render edilir. Diyagramlardaki her adım
koddaki gerçek fonksiyon/endpoint karşılığıyla etiketlenmiştir.

---

## 1. Genel Yolculuk: Kayıttan Programlara

```mermaid
flowchart TD
    A["📱 Kayıt / Giriş<br/>POST /api/register → JWT"] --> B["📋 Onboarding Formu (9 adım)<br/>hedef, kilo, yaş/boy, seviye,<br/>gün sayısı, beslenme tercihi"]
    B --> C["🎥 Adım 7: Vücut Videosu (10-15 sn)<br/>POST /api/onboarding/video"]
    C --> C1["(ops.) 🎤 Sesli Anlatım<br/>POST /api/onboarding/voice"]
    C1 --> D["✅ Adım 9: Tamamla<br/>PUT /api/profile + POST /api/onboarding/complete<br/>→ video analizi kalıcı hafızaya (UserMemory)"]
    D --> E["📝 Program Oluşturucu Anketleri"]
    E --> F["🏋️ Antrenman Anketi bitti<br/>POST /api/program-builder/workout"]
    F --> F1["🤖 generate_workout_program()<br/>AI + split planlayıcı + egzersiz havuzu"]
    E --> G["🥗 Beslenme Anketi bitti<br/>POST /api/program-builder/nutrition"]
    G --> G1["🤖 generate_meal_plan()<br/>AI + doğrulanmış besin havuzu + makro doğrulama"]
    F1 --> H["📊 Uygulama: günlük antrenman + öğün planı,<br/>koç sohbeti (canlı PubMed), progress takibi"]
    G1 --> H
```

---

## 2. Video Analizi Arkaplanı (Ne Oluyor?)

```mermaid
flowchart TD
    A["🎥 Video yükleme (webm/mp4, ≤300MB)<br/>Auth: JWT → rate limit ai_media"] --> B["💾 Disk: user_videos/onboarding_TS.webm"]
    B --> C{"🎬 Video karelere ayrılabilir mi?<br/>_extract_video_frames()"}
    C -- "evet (tercih edilen)" --> D1["🖼️ Kare tabanlı analiz<br/>(iOS codec güvenli)"]
    C -- "hayır" --> E{"📤 Files API yüklemesi<br/>_upload_video_to_gemini()"}
    E -- "başarılı" --> D2["☁️ Dosya referansıyla analiz"]
    E -- "başarısız / ≤15MB" --> D3["📦 Inline base64 gönderim"]
    D1 --> F["🧠 Gemini VISION modeli<br/>system prompt = profil + UserMemory<br/>(build_system_prompt)"]
    D2 --> F
    D3 --> F
    F --> G["📋 Yapılandırılmış JSON çıktı:<br/>• report → kullanıcıya gösterilen koç raporu<br/>• memory_summary → kalıcı özet<br/>• training_instruction / nutrition_instruction"]
    G --> H["🧠 UserMemory: category=physique_analysis<br/>(sonraki tüm program üretiminde bağlam)"]
    G --> I["📱 Frontend state → onboarding/complete ile<br/>UserMemory: onboarding_video_analysis (importance=9)"]
```

---

## 3. Antrenman Programı Üretimi (AI Öncesi Hazırlık + AI + Sonrası)

```mermaid
flowchart TD
    A["📝 Anket cevapları<br/>WorkoutQuestionnaire"] --> B["💾 Profil serbest alanlarına yazılır<br/>_persist_questionnaire_to_profile"]
    B --> C["👤 Profil okunur: deneyim, hedef,<br/>odak, sakatlık, aktivite"]
    C --> D["🧮 Bilimsel parametreler:<br/>level → sıklık + MEV/MAV/MRV + periodizasyon + RPE<br/>goal → set çarpanı + tekrar aralığı"]
    D --> E["📅 ADIM 0: Split Planlayıcı<br/>build_split_from_instruction / build_split<br/>(PPL / Upper-Lower / Full Body / Arnold)"]
    E --> F["🏋️ ADIM 1: Akıllı Egzersiz Seçici<br/>format_selected_pool — split gün kas grupları<br/>ekipman + sakatlık filtresi, grup başı 8 hareket"]
    F --> G["🔬 ADIM 2: Küratörlü Bilimsel Bağlam<br/>get_research_context (PMID'li, deterministik)"]
    G --> H["📉 ADIM 3: Zayıf Bölge Tespiti<br/>detect_weak_areas (hacim + stagnasyon)"]
    H --> I["📄 ADIM 4: Odak Grup PubMed Canlı Blok<br/>get_focus_evidence_block (cache'li, hata→küratörlü)"]
    I --> J["🧠 GEMINI: dev bilimsel prompt<br/>profil + split şablonu + kilitli hareket havuzu<br/>+ kanıtlar + MAV kuralları → JSON program"]
    J --> K["🔗 Kütüphane Uzlaştırma<br/>reconcile_program_with_library:<br/>kanonik isim eşleştirme; bilinmeyen → pending_review"]
    K --> L["💾 DB: WorkoutProgram + hareket satırları<br/>→ frontend'e program listesi"]
```

---

## 4. Beslenme Planı Üretimi

```mermaid
flowchart TD
    A["📝 Anket cevapları<br/>NutritionQuestionnaire"] --> B["💾 Profil serbest alanlarına yazılır<br/>_persist_questionnaire_to_profile"]
    B --> C["👤 Profil: günlük kalori/makro hedefleri,<br/>dietary_notes, hedef"]
    C --> D["🥗 Doğrulanmış Besin Havuzu<br/>format_candidate_pool:<br/>42 temel seed + 59 TR kürasyon + USDA"]
    D --> E["🍽️ Öğün sayısı: anket meals_per_day<br/>(yoksa 3-5 öğün kılavuzu)"]
    E --> F["🧠 GEMINI: Türk mutfağı + makro hedefi prompt'u<br/>%5 sapma kuralı + protein dağılım kuralları"]
    F --> G["🔍 Makro Doğrulama<br/>verify_and_fix_meal_plan:<br/>her besin tablodan yeniden hesaplanır;<br/>%5+ sapan öğün porsiyonu düzeltilir"]
    G --> H{"💾 save=True?"}
    H -- "evet" --> I["DB: replace_meal_plan<br/>→ günlük öğün planı"]
    H -- "hayır" --> J["Taslak pydantic liste<br/>(onay akışı)"]
```

---

## 5. Sesli Anlatım (opsiyonel kol)

```mermaid
flowchart TD
    A["🎤 Ses kaydı (webm/ogg)"] --> B["💾 user_audio/"]
    B --> C["📝 transcribe_audio → metin"]
    C --> D["🧠 extract_profile_from_transcript:<br/>profile_updates + summary + memory_summary"]
    D --> E["👤 UserProfile alanları + UserMemory"]
```
