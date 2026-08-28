# Gizlilik Politikası (Şablon) — v1.0

> ⚠️ **Yasal uyarı:** Bu belge bir mühendislik şablonudur, **hukuki
> danışmanlık değildir**. Yayına almadan önce bir avukat/KVKK-GDPR uzmanına
> gösterilmelidir. `policy_version` alanı (bkz. `Consent` tablosu) bu
> belgenin versiyonuyla senkron tutulmalıdır.

**Son güncelleme:** _(yayın tarihi buraya yazılır)_ · **Versiyon:** 1.0

## 1. Kim Olduğumuz

LUMIERE ("biz", "platform"), kullanıcılarına yapay zeka destekli
fitness/beslenme koçluğu hizmeti sunan bir SaaS platformudur.

## 2. Topladığımız Veriler

| Kategori | Örnek | Amaç | Yasal Dayanak |
|---|---|---|---|
| Hesap bilgileri | Ad, e-posta, şifre (hash) | Kimlik doğrulama | Sözleşmenin ifası |
| Sağlık/fitness verisi | Kilo, antrenman, beslenme kayıtları | Koçluk hizmeti | Sözleşmenin ifası + açık onay (özel nitelikli veri) |
| Medya | Onboarding video/ses, yemek fotoğrafları | AI analizi | Açık onay |
| Ödeme verisi | Fatura, plan durumu (kart numarası biz de tutulmaz, Stripe'ta) | Faturalandırma | Sözleşmenin ifası |
| Kullanım/teknik veri | IP, user-agent, oturum kayıtları | Güvenlik, dolandırıcılık önleme | Meşru menfaat |
| Push token | APNs cihaz token'ı | Bildirim gönderimi | Açık onay |

## 3. Verilerinizle Ne Yapıyoruz

- AI koçluk önerileri üretmek (Gemini API'ye gönderilen veri **anonimleştirilir/minimize edilir**;
  isim/e-posta gibi doğrudan tanımlayıcılar AI sağlayıcısına gönderilmez).
- Faturalandırma ve abonelik yönetimi (Stripe aracılığıyla).
- Push bildirimleri (Apple APNs aracılığıyla, sadece cihaz token'ı paylaşılır).
- Ürünü iyileştirmek için anonimleştirilmiş/toplu analiz (opt-in).

## 4. Kiminle Paylaşıyoruz (Alt İşleyiciler)

| Taraf | Amaç | Veri |
|---|---|---|
| Stripe, Inc. | Ödeme işleme | Ad, e-posta, ödeme bilgisi |
| Google (Gemini API) | AI analiz | Anonimleştirilmiş sağlık/fitness metni, medya |
| Apple (APNs) | Push bildirim | Cihaz token'ı |
| AWS (S3) | Dosya depolama | Video/ses/fotoğraf dosyaları (şifreli) |
| Sentry | Hata izleme | Teknik hata bilgisi (PII filtrelenir) |

## 5. Haklarınız (GDPR/KVKK)

- **Erişim/taşınabilirlik:** `GET /api/v1/privacy/export` ile tüm verinizi
  JSON formatında indirebilirsiniz (ayda 1 kez).
- **Silme ("unutulma hakkı"):** `POST /api/v1/privacy/delete-account` ile
  hesap silme talebi oluşturabilirsiniz. **30 günlük bekleme süresi** vardır,
  bu sürede `POST /api/v1/privacy/cancel-deletion` ile iptal edebilirsiniz.
  Fatura kayıtları yasal saklama süresi (7 yıl) nedeniyle bu silme kapsamı
  dışındadır.
- **Düzeltme:** Profilinizi uygulama içinden istediğiniz zaman güncelleyebilirsiniz.
- **Onay yönetimi:** `POST/GET /api/v1/privacy/consent` ile pazarlama
  e-postaları, analitik gibi izinlerinizi yönetebilirsiniz.

## 6. Veri Saklama

Bkz. `docs/privacy/DATA_RETENTION_POLICY.md`.

## 7. Güvenlik

Bkz. `docs/SECURITY.md`.

## 8. Çocukların Gizliliği

Bu hizmet 16 yaş altı bireylere yönelik değildir.

## 9. Politika Değişiklikleri

Önemli değişikliklerde kullanıcılar e-posta + uygulama içi bildirimle
bilgilendirilir; eski versiyonlar arşivlenir (kullanıcı hangi versiyonu
onayladığını görebilir).

## 10. İletişim

Gizlilik talepleri için: _(destek e-postası buraya yazılır)_
