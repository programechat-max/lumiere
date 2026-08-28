# Kullanım Şartları (Şablon) — v1.0

> ⚠️ **Yasal uyarı:** Bu belge bir mühendislik şablonudur, hukuki
> danışmanlık değildir. Yayına almadan önce hukuki inceleme gereklidir.

**Versiyon:** 1.0

## 1. Hizmetin Tanımı

LUMIERE, yapay zeka destekli fitness/beslenme koçluğu sağlayan bir mobil/web
uygulamasıdır. Sağlanan öneriler tıbbi tavsiye niteliğinde DEĞİLDİR.

## 2. Sağlık Feragatnamesi

Uygulama içeriği bir doktor, diyetisyen veya fizyoterapistin yerini tutmaz.
Herhangi bir antrenman/beslenme programına başlamadan önce bir sağlık
uzmanına danışmanız önerilir. Sakatlık/sağlık durumu bildiren kullanıcı
notları (`injury_notes`) AI'ya bilgi vermek içindir, tıbbi teşhis değildir.

## 3. Hesap Sorumluluğu

Kullanıcı, hesap kimlik bilgilerinin gizliliğinden sorumludur. Şüpheli
erişim fark edildiğinde `/api/v1/auth/sessions` üzerinden tüm oturumlar
sonlandırılabilir.

## 4. Abonelik & Faturalandırma

- Planlar: FREE, PREMIUM_MONTHLY, PREMIUM_ANNUAL, COACHING.
- 7 günlük ücretsiz deneme (kullanıcı başına bir kez).
- İptal, mevcut faturalandırma döneminin sonunda yürürlüğe girer
  (`POST /api/v1/billing/cancel`).
- Ücret iadeleri Stripe politikaları ve yürürlükteki tüketici hukukuna
  tabidir.

## 5. Kabul Edilebilir Kullanım

Kullanıcılar platformu şu amaçlarla kullanamaz: başka kullanıcıların
verilerine yetkisiz erişim denemesi, zararlı dosya yüklemesi, API'yi
otomatik/kötüye kullanım amaçlı istismar etme (bkz. hız sınırlama kuralları).

## 6. Fesih

Şartların ihlali durumunda hesap askıya alınabilir
(`User.is_suspended`, admin tarafından). Kullanıcı istediği zaman
`/api/v1/privacy/delete-account` ile hesabını kapatabilir.

## 7. Sorumluluk Sınırlaması

Hizmet "olduğu gibi" sağlanır. Platform, AI önerilerinin kullanımından
kaynaklanan doğrudan/dolaylı zararlardan sorumlu tutulamaz (yürürlükteki
tüketici mevzuatının izin verdiği ölçüde).

## 8. Değişiklikler

Bu şartlar güncellenebilir; önemli değişikliklerde kullanıcılar bilgilendirilir.
