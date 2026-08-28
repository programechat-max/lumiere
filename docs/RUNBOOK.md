# Operasyon Runbook'u (PROMPT 7)

Bu belge, izleme/alarm sistemleri devreye alındığında (Sentry/Prometheus/
Grafana) bir uyarı geldiğinde izlenecek adımları özetler.

## Health Check Uçları

- `GET /health` — Canlılık (liveness). Sadece süreç ayaktaysa 200 döner.
  Load balancer/orchestrator bunu "yeniden başlat" kararı için kullanır.
- `GET /ready` — Hazırlık (readiness). DB + Redis bağlantısını kontrol eder.
  `checks.database.status != "ok"` ise trafik bu instance'a yönlendirilmemeli.
- `GET /metrics` — Prometheus formatında istek sayacı, p50/p95/p99 gecikme.

## Alarm → Aksiyon Eşlemesi

| Alarm | Olası Kök Neden | İlk Aksiyon |
|---|---|---|
| Hata oranı > %1 (5dk) | Kötü deploy, bozuk bağımlılık | Son deploy'u kontrol et → gerekirse rollback |
| p95 gecikme > 2s | DB yavaş sorgu, harici API (Gemini) yavaş | `/ready` çıktısına bak, slow query log kontrol et |
| DB pool tükendi | Sızıntı yapan sorgu / trafik artışı | `DB_POOL_SIZE`/`DB_MAX_OVERFLOW` artır, aktif bağlantıları incele |
| Celery kuyruk derinliği > 1000 | Worker düşük/çökmüş | `docker compose --profile worker ps`, worker sayısını artır |
| Stripe webhook 3+ kez başarısız | İmza uyuşmazlığı / endpoint erişilemez | `STRIPE_WEBHOOK_SECRET` doğrula, Stripe Dashboard'dan yeniden gönder |
| Başarısız login > 10/IP/saat | Brute-force denemesi | IP'yi WAF/firewall'da geçici engelle, `AuditLog` incele |

## Sık Kullanılan Komutlar

```bash
# Servis sağlığı
curl -s http://localhost:8000/ready | jq

# Celery worker durumu (Flower UI)
open http://localhost:5555

# Son 50 audit log kaydı (SQL)
sqlite3 backend/sql_app.db "SELECT action, user_id, ip_address, created_at FROM audit_logs ORDER BY created_at DESC LIMIT 50;"

# Alembic migration durumu
cd backend && alembic current && alembic history
```

## Kod Sürümü / Sürüm Takibi

`APP_VERSION` ortam değişkeni `/health` yanıtında görünür ve Sentry
release etiketiyle eşleştirilir — bir hata raporunun hangi deploy'da
oluştuğunu anında görebilmek için her deploy'da bu değeri güncelleyin
(CI/CD pipeline'a `git describe --tags` ile otomatik enjekte edilmesi
önerilir).

## Graceful Shutdown

- FastAPI `shutdown` event'i APScheduler'ı düzgünce durdurur
  (`scheduler.shutdown_scheduler`).
- Celery worker'lar `acks_late=True` ile yapılandırıldığından, `SIGTERM`
  alındığında devam eden görevi bitirmeye çalışır (bkz. `celery_app.py`).
  Kubernetes/ECS'de `terminationGracePeriodSeconds >= 30` önerilir.
