# GDPR/KVKK Uyum Kontrol Listesi (PROMPT 11)

| Gereklilik | Durum | Uygulama |
|---|---|---|
| Yasal dayanak belirlenmiş açık onay akışı | ✅ | `Consent` tablosu, `/api/v1/privacy/consent` |
| Erişim hakkı (veri indirme) | ✅ | `/api/v1/privacy/export` (gzip JSON, ayda 1) |
| Silme hakkı (unutulma) | ✅ | `/api/v1/privacy/delete-account` (30 gün ödül süresi) |
| Silme iptali | ✅ | `/api/v1/privacy/cancel-deletion` |
| Veri taşınabilirliği (makine okunabilir format) | ✅ | JSON export |
| Düzeltme hakkı | ✅ | `PUT /api/profile` (mevcut) |
| Veri minimizasyonu (AI sağlayıcısına PII sızıntısı yok) | ⚠️ Kısmi | `ai_core.py` promptlarının PII sızdırmadığı manuel olarak gözden geçirilmeli (otomatik test eklenmedi — takip görevi) |
| Şifreleme (aktarımda) | ✅ (altyapı bağımlı) | HTTPS zorunluluğu `COOKIE_SECURE`/HSTS ile prod'da uygulanır — TLS sertifikası deploy altyapısında (reverse proxy/load balancer) sağlanmalı |
| Şifreleme (beklemede) | ⚠️ Kısmi | S3 SSE-S3/KMS destekleniyor (`storage.py`); veritabanı düzeyinde alan bazlı şifreleme (örn. `injury_notes`) eklenmedi — hassasiyetine göre takip görevi |
| Audit log / erişim izleme | ✅ | `AuditLog` tablosu |
| Veri ihlali bildirim planı | ✅ (doküman) | `docs/privacy/INCIDENT_RESPONSE_PLAN.md` |
| Alt işleyici (sub-processor) listesi | ✅ (doküman) | `docs/privacy/PRIVACY_POLICY.md` §4 |
| Saklama süresi politikası | ✅ (doküman) | `docs/privacy/DATA_RETENTION_POLICY.md` |
| Veri Koruma Sorumlusu (DPO) ataması | ❌ Yapılmadı | Şirket büyüklüğüne/yasal zorunluluğa göre değerlendirilmeli |
| Veri Etki Değerlendirmesi (DPIA) şablonu | ❌ Yapılmadı | Yeni özellik eklerken (özellikle sağlık verisi işleyen) şablon oluşturulmalı |
| Çerez politikası / banner | ⚠️ Kısmi | Sadece fonksiyonel (session) cookie kullanılıyor, 3. parti izleme çerezi yok — ayrı bir "cookie banner" UI'ı henüz eklenmedi |
| CCPA/CASL/LGPD ayrımı (ülkeye göre) | ❌ Yapılmadı | `Consent.consent_type` alanı bunun için genişletilebilir; ülke bazlı otomatik mevzuat seçimi ayrı bir görev |

## Öncelikli Takip Görevleri

1. Alan bazlı şifreleme: `UserProfile.injury_notes`, `UserProfile.dietary_notes`
   gibi hassas serbest metin alanları için uygulama seviyesi şifreleme
   (örn. `cryptography.Fernet`) değerlendirilmeli.
2. `ai_core.py` promptlarının Gemini'ye gönderdiği veride e-posta/ad gibi
   doğrudan tanımlayıcı sızdırmadığını doğrulayan bir birim test eklenmeli.
3. DPO ataması ve DPIA şablonu — hukuk/uyum ekibiyle birlikte.
