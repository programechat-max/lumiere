# Veri İhlali / Olay Müdahale Planı (PROMPT 11)

## 1. Tespit

- Sentry/güvenlik izleme uyarıları (bkz. `docs/SECURITY.md` §4,
  `docs/RUNBOOK.md`), anormal `AuditLog` desenleri (çok sayıda başarısız
  giriş, olağandışı veri erişimi), 3. parti bildirimi (örn. Stripe, AWS).

## 2. Sınıflandırma (İlk 1 saat)

| Seviye | Tanım | Örnek |
|---|---|---|
| P0 - Kritik | Kişisel/sağlık verisi sızdırıldı veya yetkisiz erişildi | DB dump'ı sızdırıldı, S3 bucket public oldu |
| P1 - Yüksek | Sistemsel güvenlik açığı, henüz veri sızıntısı kanıtı yok | Auth bypass keşfedildi |
| P2 - Orta | Sınırlı etkili, tek kullanıcı | Bir hesabın ele geçirilmesi |

## 3. Müdahale Adımları

1. **Durdur:** Etkilenen sistemi/anahtarı izole et (API anahtarı rotasyonu,
   şüpheli oturumları `UserSession.revoked_at` ile toplu iptal et).
2. **Kapsam belirle:** Hangi tablolar/kullanıcılar etkilendi?
   `AuditLog` üzerinden erişim izini çıkar.
3. **Sızıntıyı kapat:** Güvenlik açığını yama, yeni deploy.
4. **Delil koru:** İlgili logları/audit kayıtlarını arşivle (soruşturma için).

## 4. Bildirim

- **Düzenleyici kuruma (KVKK/GDPR yetkilisi):** İhlalin öğrenilmesinden
  itibaren **72 saat içinde** (GDPR Md. 33).
- **Etkilenen kullanıcılara:** Yüksek risk varsa **gecikmeden** (GDPR Md. 34) —
  e-posta + uygulama içi bildirim (push, `billing_alerts_enabled` kanalından
  bağımsız olarak kritik güvenlik bildirimleri her zaman gönderilir).
- Bildirim içeriği: ne oldu, hangi veri etkilendi, alınan önlemler,
  kullanıcının yapması gerekenler (örn. şifre değişikliği).

## 5. Kayıt Tutma

Her olay için: tespit zamanı, sınıflandırma, kapsam, alınan aksiyonlar,
bildirim zamanları, kök neden analizi — ayrı bir "olay kaydı" belgesinde
(bu repo'da otomasyona bağlı değildir, manuel prosedürdür).

## 6. Olay Sonrası

- Kök neden analizi (blameless postmortem).
- Aynı hatanın tekrarını önleyecek test/monitoring eklenmesi.
- Bu planın güncellenmesi (öğrenilen dersler).
