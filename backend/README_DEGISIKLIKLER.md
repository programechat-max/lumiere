# Bu düzenlemede neler değişti?

## Kritik düzeltmeler
- `main.py` artık gerçekten çalışıyor: eski hali `models.NutritionPlan.date` ve `target_fats`
  gibi VAR OLMAYAN kolonlara referans veriyordu, her istek 500 hatası veriyordu.
- Frontend'in beklediği `/api/status`, `/api/nutrition`, `/api/workout` endpoint'leri artık gerçekten var.
- Kırık/bağlanmamış `routers/` klasörü (var olmayan şema ve crud fonksiyonlarına referans veriyordu,
  hiçbir yerden import edilmiyordu) tamamen kaldırıldı.
- `ai_agent.py` (hiç kullanılmıyordu) ve `telegram_bot.py`'deki ayrı, senkron olmayan AI mantığı
  tek bir `ai_core.py` motorunda birleştirildi.
- `NutritionPlan` tablosu `date` kolonu olmadığı için "bugünün öğünleri" hiç doğru çekilemiyordu;
  yeni `NutritionLog` tablosu bunu düzeltiyor.

## Yeni eklenen (senin istediğin kişiselleştirme + gelişim takibi için)
- `UserProfile` genişletildi: hedef, aktivite seviyesi, beslenme/uyku/sakatlık notları, günlük makro hedefleri.
- Telegram'da `/profil` komutu ile onboarding sohbeti: yaş, boy, kilo, hedef, aktivite, beslenme, rutin sorup profili dolduruyor.
- `BodyMetric` tablosu: kilo/ölçüm geçmişi (gelişim grafiği için).
- `UserMemory` tablosu: AI'nin öğrendiği tercihler ve haftalık analizler kalıcı olarak saklanıyor,
  her mesajda system prompt'a otomatik ekleniyor (Jarvis gerçekten "seni tanıyor").
- `/analiz` komutu ve haftalık otomatik (Pazartesi 09:00) analiz: son 7 günün antrenman/beslenme/kilo
  verisini AI analiz edip somut öneriler veriyor - "gelişime yönelik hareket etme" isteğinin başlangıcı.
- `video_analyzer.py` artık analiz sonucunu bir .txt dosyasına değil, veritabanına yazıyor -
  eskiden telegram_bot.py bu dosyayı hiç okumadığı için video analizleri botu etkilemiyordu.

## Sırada ne var (senin onayınla devam edeceğim)
1. Frontend'i (`App.jsx`) yeni endpoint'lere göre güncellemek — özellikle sabit 2700kcal/140g
   hedeflerini profildeki gerçek `daily_calorie_target` değerlerine bağlamak.
2. Antrenman programının "progressive overload" mantığıyla otomatik ilerlemesi (örn. hedef tekrara
   ulaşıldıysa ağırlığı otomatik önerme).
3. Dashboard'a gelişim grafiği (kilo/ölçüm trendi) ve haftalık analiz kartı eklemek.
4. `.env` dosyasını `.env.example`'dan oluşturup gerçek anahtarları girmen gerekiyor.

## Bu turda eklenenler

### 1. Profesyonel kas ısı haritası
`src/App.jsx` içindeki `MuscleHeatmap` bileşeni sıfırdan yazıldı: gönderdiğin anatomi
referans görseline benzer şekilde, gölgeli/degrade dolgulu, kas ayrım çizgileriyle (sternum
hattı, linea alba, vastus ayrımı, lat/erector şeritleri vb.) daha gerçekçi bir ön+arka vücut
silueti. Çalışılmayan bölgeler nötr gri degrade, çalışılan kas grupları set hacmine göre
sarı→turuncu→kırmızı degrade + hafif "glow" ile öne çıkıyor. Veri kaynağı ve renk eşikleri
(`/api/workout/heatmap/day`, `getHeatColor`) değişmedi, sadece görsel katman yenilendi.

### 2. Video + sesli anlatımla onboarding
Artık web arayüzü sadece "Telegram'a git" demiyor: `!isSetupComplete` durumunda yeni
`OnboardingWizard` bileşeni açılıyor.
- **Adım 1:** temel bilgiler (yaş, boy, kilo, hedef, tecrübe, aktivite seviyesi, opsiyonel odak
  kas grubu / hedef fizik) formu.
- **Adım 2:** `getUserMedia` + `MediaRecorder` ile tarayıcıdan doğrudan **vücut videosu**
  kaydı ("iyi ışıkta, önden/yandan dön") → `POST /api/onboarding/video` → mevcut
  `ai_core.analyze_physique_media` (Gemini vision) ile analiz edilip kullanıcıya rapor
  gösteriliyor, kalıcı özet `UserMemory`'e yazılıyor.
- **Adım 3:** yine tarayıcıdan **sesli kayıt** ("güncel beslenmeni, antrenmanını, günlük
  rutinini ve gerçek hedefini anlat") → `POST /api/onboarding/voice` → önce
  `ai_core.transcribe_audio` ile metne çevriliyor, sonra YENİ `ai_core.extract_profile_from_transcript`
  fonksiyonu bu metni yapılandırılmış profil alanlarına (`dietary_notes`, `schedule_notes`,
  `injury_notes`, `goal`, `activity_level` vb.) ve bir `UserMemory` özetine dönüştürüyor.
- **Adım 4 ("Bitir"):** `POST /api/onboarding/complete` formdaki temel bilgileri profile
  yazar, `onboarding_completed=True` yapar, ardından `ai_core.generate_workout_program` ve
  `ai_core.generate_meal_plan`'ı hiçbir ekstra talimat vermeden çağırır — çünkü video/ses
  analizinden biriken `UserMemory` kayıtları zaten `build_system_prompt` üzerinden otomatik
  olarak devreye giriyor. Yani AI, kullanıcıyı gerçekten "tanıyarak" ilk programını kuruyor.

Video/ses dosyaları `backend/user_videos/` ve `backend/user_audio/` altına da kaydediliyor
(mevcut `video_analyzer.py` betiğiyle aynı klasör kalıbı). Yeni endpoint'ler dosya yükleme
kullandığı için `requirements.txt`'ye `python-multipart` eklendi — kurulumu güncellemeyi unutma:
`pip install -r requirements.txt`.

Ayrıca fark edilen küçük bir hata da düzeltildi: `ai_core.py` modül seviyesinde `schemas`'ı
import etmiyordu, bu yüzden fotoğraf analizindeki (`analyze_photo`) yemek kaydı satırı
`NameError` ile patlıyordu; artık dosya başında `import schemas` var.

## "Load failed" hatası düzeltmesi (video onboarding)

Profil oluşturmada vücut videosu yüklerken alınan "Load failed" hatasının kök nedeni:
video Gemini'ye **inline** (istek gövdesine doğrudan base64 gömülü) gönderiliyordu. Bu yöntem
sadece birkaç MB'a kadar güvenilir çalışıyor; 15-20 saniyelik bir kamera videosu bunu kolayca
aşıyor ve ya Gemini isteği reddediyor ya da FastAPI süreci base64'e çevirirken (boyut ~%33
büyür) uzun süre tıkanıp tarayıcıda bağlantı koptuğu için "Load failed" görünüyordu.

Yapılan düzeltmeler:
- `ai_core.py`: yeni `_upload_video_to_gemini()` fonksiyonu videoyu Gemini'nin **Files API**'sine
  yüklüyor (`genai.upload_file`) ve işlenip `ACTIVE` duruma geçmesini bekliyor. `analyze_physique_media`
  artık video veya 15MB'ı aşan her medya için bunu kullanıyor; fotoğraflar küçük olduğu için
  gereksiz gecikme olmasın diye inline kalmaya devam ediyor. Analiz bitince yüklenen dosya
  Gemini tarafında da temizleniyor (`genai.delete_file`).
- `main.py`: `/api/onboarding/video` ve `/api/onboarding/voice` artık 300MB üstü dosyaları
  net bir hata mesajıyla (413) reddediyor, ve beklenmeyen hatalarda bağlantıyı koparmak yerine
  anlamlı bir JSON hata (`detail`) dönüyor.
- `App.jsx` (OnboardingWizard): video kaydı artık **20 saniyede otomatik duruyor** ve bitrate
  ~1.2 Mbps ile sınırlanıyor (20sn ~3MB civarı) - böylece dosya baştan makul boyutta kalıyor.
  Ayrıca backend'den dönen gerçek hata mesajı (`detail`) artık jenerik bir metin yerine
  doğrudan kullanıcıya gösteriliyor.

## "API key not valid" hatası (sadece video analizinde, Telegram çalışırken)

Bu hata Telegram sohbeti çalışırken SADECE onboarding video analizinde çıkıyorsa, anahtarın
kendisi geçersiz DEĞİL — Telegram ve video analizi aynı `GEMINI_API_KEY`'i kullanıyor, o yüzden
anahtar gerçekten geçersiz olsaydı ikisi de patlardı. Hatadaki URL'e dikkat et:
`.../$discovery/rest?version=v1beta&key=...` — bu, normal `generateContent` çağrılarının
kullandığı yoldan FARKLI, sadece Files API'nin (`genai.upload_file`, video yüklemede kullanılan
fonksiyon) bazı `google-generativeai` sürümlerinde kullandığı discovery-tabanlı bir alt istemci.
Bu, kurulu SDK sürümüyle sade bir API key arasında bir uyumsuzluk.

İki katmanlı çözüm uygulandı:
1. `requirements.txt`'de `google-generativeai>=0.8.3` alt sınırı verildi. Eğer daha eski bir
   sürüm kuruluysa: `pip install -r requirements.txt --upgrade` çalıştırıp backend'i yeniden
   başlat.
2. `ai_core.py`'de Files API yüklemesi artık kendi içinde try/except ile korunuyor: başarısız
   olursa (bu discovery hatası dahil) otomatik olarak eski **inline** gönderime düşüyor. Video
   zaten kayıt sırasında küçük tutulduğu için (20sn/~1.2Mbps, birkaç MB) inline gönderim
   güvenli. Yani SDK güncellenmese bile video analizi artık tamamen durmuyor, sadece Files
   API'nin büyük dosya avantajından yararlanamıyor.

## Bu turda eklenenler (2)

### 1. "Tüm öğünlerimi tamamladım" artık gerçekten çalışıyor
Eskiden Telegram'da sadece plandaki TEK bir öğüne atıfla ("kahvaltımı yedim") çalışan eşleme
mantığı vardı; kullanıcı "tüm öğünlerimi tamamladım" gibi günün TAMAMINA atıfla bir şey
söylediğinde AI bunu tek bir öğün ismiyle eşleştirmeye çalışıp bulamıyor ve "bu isimde bir
öğün yok" diyordu. Yeni `complete_all_meals` intent'i: plandaki tüm öğünleri (bugün zaten tek
tek kaydedilmiş olanları atlayarak) gerçek plan verisiyle kaydediyor ve toplam kalori/proteinle
özet dönüyor.

### 2. Antrenman programı artık kanıta dayalı hipertrofi mantığıyla hareket seçiyor
`generate_workout_program` prompt'u eskiden sadece "4-6 hareket, kas grubunu belirt" diyordu -
bu da modelin en "klasik/akla gelen" hareketleri (örn. sadece ayakta barbell curl) yazmasına
yol açıyordu. Artık prompt açıkça istiyor: her kas grubu için gerilmiş pozisyonda yükleyen bir
hareket (stretch-mediated hypertrophy), gün içinde bileşik→izolasyon sıralaması, kas/hareket
tipine göre değişen tekrar aralıkları (ağır bileşik 5-10, ana hipertrofi 8-12, izolasyon/uzun
kas 10-20), gereksiz hareket tekrarından kaçınma ve deneyim seviyesine göre serbest ağırlık/
makine dengesi.

### 3. Hafıza sistemi belirgin şekilde güçlendirildi
- **Tekrar önleme:** Aynı tercih/not farklı sohbetlerde tekrar söylenirse artık hafızada
  onlarca neredeyse aynı satır birikmiyor - mevcut kayıt güncelleniyor.
- **Haftalık analiz raporları artık hafızayı boğmuyor:** Eskiden her haftalık analiz ayrı bir
  hafıza kaydıydı ve uzun metinler oldukları için birkaç hafta sonra son 10 kayıt tamamen
  analizlerle doluyor, kullanıcının "balık yemem" gibi kalıcı tercihleri sistem prompt'undan
  düşüyordu. Artık en fazla son 2 analiz tutuluyor, kalıcı tercih/not/içgörüler ayrı ve çok
  daha yüksek bir sınırla (40) besleniyor.
- **Yeni `forget` intent'i:** Kullanıcı "bunu unut" / "artık öyle değil" derse, en yakın
  eşleşen hafıza kaydı bulunup siliniyor - eskiden hafızadan bir şeyi çıkarmanın hiçbir yolu
  yoktu, yanlış/eskimiş bilgi sonsuza kadar system prompt'ta kalıyordu.
- System prompt'taki hafıza bölümü artık "kalıcı tercihler" ve "en son haftalık analiz" olarak
  ayrı başlıklarda sunuluyor, modelin hangisinin güncel hangisinin uzun vadeli olduğunu
  ayırt etmesi kolaylaşıyor.
