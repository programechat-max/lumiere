# LUMIERE Coaching

React + Vite (web/iOS via Capacitor) frontend + FastAPI backend olarak yapılandırılmış
yapay zeka destekli fitness/beslenme koçluğu platformu.

> 📋 Bu projenin tek-kullanıcıdan çok-kullanıcılı kurumsal SaaS'a yükseltilmesi için
> yapılan çalışmanın tam özeti: **[PLATFORM_UPGRADE_SUMMARY.md](./PLATFORM_UPGRADE_SUMMARY.md)**

## Hızlı Başlangıç (Yerel Geliştirme)

### Backend
```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # zaten .venv varsa atla
pip install -r requirements.txt
cp .env.example .env   # JWT_SECRET_KEY vb. doldurun
uvicorn main:app --reload
```
Varsayılan olarak SQLite kullanır (`backend/sql_app.db`), Redis/PostgreSQL/Stripe/AWS/APNs
**olmadan** çalışır — bu servisler yapılandırılmadığında ilgili özellikler güvenli şekilde
devre dışı kalır (bkz. `docs/` altındaki ilgili kılavuzlar).

### Frontend
```bash
npm install
npm run dev
```

### Testler
```bash
cd backend
CELERY_TASK_ALWAYS_EAGER=true pytest -q
```

## Üretim Altyapısını Devreye Alma (opsiyonel)

```bash
docker compose up -d postgres pgadmin redis      # PostgreSQL + Redis + pgAdmin
docker compose --profile worker up -d            # + Celery worker/beat + Flower
cd backend && alembic upgrade head               # şema migrasyonu
```

Ardından `backend/.env` içine `DATABASE_URL`, `REDIS_URL` vb. tanımlayın (bkz.
`backend/.env.example`).

## Mac Yerel Sunucu + Operasyon Paneli

Docker Desktop açıkken proje kökünde:

```bash
export GEMINI_API_KEY="..."
export JWT_SECRET_KEY="openssl rand -hex 32 çıktısı"
docker compose up -d --build api postgres redis
docker compose --profile worker up -d --build
cd backend && alembic upgrade head
```

- API: `http://localhost:8000/health` ve bağımlılık kontrolü: `http://localhost:8000/ready`
- pgAdmin: `http://localhost:5050` (`admin@lumiere.local` / `admin` — ilk çalıştırmada değiştirin)
- Flower: `http://localhost:5555` (worker profili açıkken)
- Frontend: `npm run dev`

Admin rolündeki kullanıcılar uygulama başlığındaki **Admin** panelinden KPI, PostgreSQL/Redis durumu ve kullanıcı listesini görebilir. Video analizleri `/api/v1/jobs/onboarding/video` üzerinden kuyruğa alınır; mobil istemci sonucu job durumundan takip eder. Dış erişim için modem portu açmak yerine Tailscale veya Cloudflare Tunnel kullanın.

## Dokümantasyon Haritası

| Konu | Belge |
|---|---|
| Genel yükseltme özeti (12 prompt → durum) | `PLATFORM_UPGRADE_SUMMARY.md` |
| Güvenlik mimarisi (auth, RBAC, CORS, rate limit) | `docs/SECURITY.md` |
| API versiyonlama/sayfalama/hız sınırlama tasarımı | `docs/API_VERSIONING.md` |
| Operasyon runbook'u (alarm → aksiyon) | `docs/RUNBOOK.md` |
| iOS APNs push kurulumu | `docs/IOS_PUSH_GUIDE.md` |
| AWS S3 kurulumu (Terraform) | `docs/AWS_SETUP.md` |
| Gizlilik politikası / KVKK-GDPR | `docs/privacy/` |
| Backend değişiklik günlüğü (eski) | `backend/README_DEGISIKLIKLER.md` |

## Proje Yapısı

```
backend/          FastAPI uygulaması (bkz. PLATFORM_UPGRADE_SUMMARY.md için modül haritası)
src/               React dashboard (web + Capacitor iOS)
docs/              Mimari/güvenlik/gizlilik dokümantasyonu
docker-compose.yml PostgreSQL + Redis + Celery + Flower (yerel/prod altyapı)
.github/workflows  CI pipeline
```

---

## React + Vite Şablon Notları

Bu proje React + Vite ile HMR ve bazı ESLint kurallarıyla başlatıldı.

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) (Oxc)
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) (SWC)

TypeScript + tip farkındalıklı lint kuralları için [TS şablonuna](https://github.com/vitejs/vite/tree/main/packages/create-vite/template-react-ts) bakın.
