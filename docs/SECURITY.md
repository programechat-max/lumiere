# Güvenlik Politikası & Uygulama Detayları

Bu belge LUMIERE platformunun kimlik doğrulama/yetkilendirme mimarisini ve
güvenlik sertleştirme kararlarını belgeler (PROMPT 2 & PROMPT 8).

## 1. Kimlik Doğrulama

- **Şifre hashleme:** Argon2 (`argon2-cffi`). Eski `bcrypt` hash'leri
  `passlib.CryptContext(schemes=["argon2", "bcrypt"], deprecated="auto")` ile
  hâlâ doğrulanabilir; kullanıcı doğru şifreyle giriş yaptığı anda hash
  otomatik olarak Argon2'ye yükseltilir (bkz. `backend/auth.py::needs_rehash`).
  Mevcut hesaplar bozulmaz, kademeli geçiş sağlanır.
- **Şifre politikası:** En az 12 karakter, büyük/küçük harf, rakam ve özel
  karakter zorunlu (`auth.validate_password_strength`).
- **JWT access token:** 15 dakika ömürlü, `sub` claim'inde kullanıcı ID.
- **Refresh token:** 7 gün ömürlü, veritabanında **SHA-256 hash'i** olarak
  saklanır (ham token asla DB'de tutulmaz), `HttpOnly` + `Secure` + `SameSite=Lax`
  cookie ile taşınır (`/api/v1/auth/*` path'i ile sınırlı).
- **CSRF koruması:** Refresh/cookie akışı "double-submit cookie" deseniyle
  korunur — `csrf_token` cookie'si (HttpOnly=False, JS okuyabilir) ile
  `X-CSRF-Token` header'ı eşleşmelidir.
- **Hesap kilitleme:** 5 başarısız girişten sonra 15 dakika kilit
  (`MAX_FAILED_LOGIN_ATTEMPTS`, `LOGIN_LOCKOUT_MINUTES`).
- **Eşzamanlı oturum limiti:** Kullanıcı başına en fazla 3 aktif refresh
  oturumu; limit aşıldığında en eski oturumlar otomatik iptal edilir.
- **Kullanıcı numaralandırma (enumeration) koruması:** Giriş hataları her
  zaman jenerik "E-posta veya şifre hatalı." mesajı döner.

## 2. Yetkilendirme (RBAC)

Roller: `SUPER_ADMIN`, `ADMIN`, `SUPPORT`, `FINANCE`, `COACH`, `USER`.
`backend/auth.py::require_roles(...)` bir FastAPI dependency factory'sidir;
`/api/v1/admin/*` uçları bu şekilde korunur. Satır bazlı erişim (row-level
security) her sorguda `user_id` filtresiyle uygulanır — kullanıcılar asla
başka bir kullanıcının verisine dolaylı olarak da ulaşamaz.

## 3. Denetim Kaydı (Audit Log)

`AuditLog` tablosu: `login_success`, `login_failed`, `logout`,
`password_change_*`, `register`, `admin.edit_user` gibi tüm hassas olayları
`user_id`, `actor_user_id` (admin impersonation/işlem yapan), IP, User-Agent,
sonuç ve zaman damgasıyla kalıcı olarak saklar. Audit log yazımı ana iş
akışını asla bozmaz (hata olursa yutulur, sadece loglanır).

## 4. Ağ / HTTP Güvenliği

- **CORS:** `allow_origins=["*"]` KALDIRILDI. `ALLOWED_ORIGINS` ortam
  değişkeninden okunan beyaz listeye göre kısıtlanır (bkz. `backend/config.py`).
- **Güvenlik başlıkları** (`backend/middleware.py::SecurityHeadersMiddleware`):
  `X-Content-Type-Options`, `X-Frame-Options: DENY`, `X-XSS-Protection`,
  `Content-Security-Policy`, üretimde `Strict-Transport-Security`.
- **Hız sınırlama:** IP bazlı genel limit (varsayılan 1000/dk) +
  login/register için 5/dk + plan bazlı AI endpoint limitleri
  (`backend/rate_limit.py`). Redis varsa dağıtık, yoksa süreç-içi bellek
  deposu kullanılır.
- **Hata formatı:** İstemciye asla stack trace sızdırılmaz; tüm hatalar
  `{"detail": ..., "error": {"code", "message", "details"}}` formatında
  standardize edilmiştir (`backend/error_handlers.py`).

## 5. Sırlar / Ortam Değişkenleri

Tüm gizli anahtarlar (`JWT_SECRET_KEY`, `STRIPE_SECRET_KEY`,
`AWS_SECRET_ACCESS_KEY`, `APNS_AUTH_KEY_PATH` vb.) `.env` üzerinden okunur,
koda gömülü DEĞİLDİR (bkz. `backend/.env.example`). Üretimde bir secrets
manager (AWS Secrets Manager / HashiCorp Vault / Doppler) kullanılması
önerilir — bu repo şu an dosya tabanlı `.env` kullanıyor, vault entegrasyonu
ayrı bir altyapı kararı gerektirir ve bu yükseltmenin kapsamı dışındadır.

## 6. Bilinen Sınırlamalar / Takip Edilmesi Gerekenler

- 2FA/MFA alanları (`User.mfa_secret`, `User.mfa_enabled`) şemada mevcut
  ancak `pyotp` ile TOTP akışı (QR kod üretimi + doğrulama uçları) henüz
  bağlanmadı — bu, hızlı bir takip görevi olarak eklenebilir.
- OAuth2 (Google/Apple Sign-In) eklenmedi.
- Legacy `/api/auth/*` uçları (JSON body access token, cookie yok) geriye
  dönük uyumluluk için korunmuştur; yeni istemciler `/api/v1/auth/*`
  akışına geçmelidir (bkz. `docs/API_VERSIONING.md`).
