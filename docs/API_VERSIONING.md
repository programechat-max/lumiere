# API Versiyonlama, Sayfalama & Hız Sınırlama Tasarımı (PROMPT 6)

## Versiyonlama Stratejisi

- **Yeni tüm özellikler** `/api/v1/*` altında yayınlanır (auth, billing,
  files, notifications, privacy, jobs, admin, support).
- **Mevcut (legacy) uçlar** — `/api/auth/*`, `/api/profile`, `/api/nutrition*`,
  `/api/workout*`, `/api/chat`, `/api/mealplan*`, `/api/metrics`,
  `/api/insights*`, `/api/memory*`, `/api/onboarding/*` — **değiştirilmeden**
  `/api/*` altında kalır. Bu, mevcut web/iOS istemcilerini bozmadan yeni
  altyapıyı devreye almamızı sağladı.
- **Neden tam bir `/api/v1` taşıması yapılmadı:** ~40 mevcut endpoint'i
  path değiştirerek taşımak, frontend/iOS istemci güncellemesini AYNI ANDA
  gerektirir ve gerçek kullanıcı riski taşır. Bu, ayrı, planlı bir "v1 tam
  taşıma" görevi olarak ele alınmalı — istemci güncellemesiyle koordineli
  şekilde yapılmalıdır. Önerilen adımlar:
  1. Legacy uçları değiştirmeden `/api/v1/*` altında ALIAS olarak yeniden
     kaydet (ince bir `APIRouter` sarmalayıcıyla).
  2. Frontend/iOS'u `/api/v1/*`'e geçir.
  3. `Deprecation`/`Sunset` header'larıyla `/api/*`'i en az 6 ay canlı tut.
  4. Kullanım telemetrisi sıfırlanınca `/api/*`'i kaldır.
- Version negotiation header'ı (`API-Version`) şu an eklenmedi; path tabanlı
  versiyonlama yeterli görüldü (URL versiyonlama, Prompt 6'nın önerdiği
  birincil yöntem).

## Sayfalama

- **Limit/offset** (`backend/pagination.py::paginate_query`): varsayılan
  `limit=50`, maksimum `1000`. Yanıt formatı: `{data, total, limit, offset}`.
  Yeni uçlarda kullanılır: `/api/v1/files`, `/api/v1/admin/users`,
  `/api/v1/admin/support/tickets`.
- **Cursor tabanlı** (`cursor_paginate`): zaman serisi verileri için hazır,
  henüz bir üretim endpoint'ine bağlanmadı (ileri seviye optimizasyon).
- **Legacy liste uçları BİLİNÇLİ OLARAK sayfalanmadı** — bunlar zaten düz
  dizi (`list[...]`) döndürüyor ve frontend bu şekle bağımlı. Şekli
  `{data, total, ...}` olarak değiştirmek frontend'i kırardı. Bu uçlar
  zaten `days`/`limit` query parametreleriyle veri hacmini sınırlıyor.

## Hız Sınırlama

| Katman | Limit | Uygulama |
|---|---|---|
| IP (genel) | 1000 istek/dk | `IPRateLimitMiddleware` (tüm `/api/*`) |
| Login/Register | 5 istek/dk (IP) | `routes_auth_v1.py::login_v1` |
| AI endpoint'leri (chat, plan üretimi, onboarding analizi) | Plana göre: FREE 10/dk, PREMIUM 100/dk, COACHING sınırsız | `rate_limit.enforce_plan_rate_limit` |
| Veri dışa aktarma (GDPR export) | Ayda 1 | `routes_privacy.py::export_my_data` |

Depolama: `REDIS_URL` tanımlıysa Redis (dağıtık, çoklu süreç/instance
tutarlı); değilse süreç-içi bellek sözlüğü (tek instance geliştirme/test
için yeterli). Yanıt header'ları: `X-RateLimit-Limit`, `X-RateLimit-Remaining`,
`X-RateLimit-Reset`, aşımda `Retry-After` + HTTP 429.

## Hata Formatı

```json
{
  "detail": "İnsan tarafından okunabilir mesaj (geriye dönük uyumluluk)",
  "error": { "code": "RATE_LIMITED", "message": "...", "details": {} }
}
```

`detail` alanı mevcut frontend/testlerin beklediği eski formatla uyumludur;
`error.code` yeni istemcilerin makine tarafından işlenebilir hata kodlarına
göre dallanabilmesi için eklenmiştir.
