#!/usr/bin/env bash
# Backend container giris noktasi.
#
# KOK NEDEN (InFailedSqlTransaction / 'Program olusturulamadi'):
# Render'daki production Postgres tablolari ilk deploy'da SQLAlchemy create_all
# ile olusturulmustu; Alembic HIC calistirilmadigi icin alembic_version tablosu
# YOK. Bu yuzden 'alembic upgrade head' ilk migration'i (eb95af9d1758 initial
# schema) kosturup 'relation "users" already exists' (DuplicateTable) ile
# patliyordu. Modelin bekledigi Faz 6/7 kolonlari da DB'de olmadigi icin
# selector sorgusu 'column does not exist' -> InFailedSqlTransaction veriyordu.
#
# Cozum (idempotent, her baslatmada guvenle kosar):
#  1) 'users' tablosu VAR ama 'alembic_version' YOKsa -> sema create_all ile
#     kurulmus demektir; Alembic'e baslangic noktasini 'stamp eb95af9d1758'
#     ile bildir (tablolari YENIDEN OLUSTURMAZ, sadece revision isaretler).
#  2) Arindan 'upgrade head' -> yalnizca eksik sonraki migration'lari uygular
#     (Faz 6/7 kolonlari vb. eklenebilir hale gelir).
set -euo pipefail

cd /app

echo "[entrypoint] Veritabani sema durumu denetleniyor..."

NEED_STAMP=$(python - <<'PY'
# 'users' var ama alembic_version yoksa -> 'true' yazdir.
try:
    from sqlalchemy import create_engine, inspect
    from config import settings
    eng = create_engine(settings.DATABASE_URL)
    insp = inspect(eng)
    tables = set(insp.get_table_names())
    print("true" if ("users" in tables and "alembic_version" not in tables) else "false")
except Exception:
    # DB'ye henuz ulasilamiyorsa stamp'e kalkismayalim; upgrade head kendi
    # basarisini/hatasini yonetsin.
    print("false")
PY
)

if [ "$NEED_STAMP" = "true" ]; then
  echo "[entrypoint] Mevcut sema create_all ile kurulmus (alembic_version yok)."
  echo "[entrypoint] Baslangic revision'i isaretleniyor: stamp eb95af9d1758"
  python -m alembic stamp eb95af9d1758
fi

echo "[entrypoint] Alembic migration'lari uygulaniyor (head)..."
# head'e cekemezse container hizli ve gorunur sekilde dussun ki eksik sema ile
# sessizce calisip kullaniciya 'sunucu hatasi' dondurmesin.
python -m alembic upgrade head

echo "[entrypoint] Migration tamam. Uygulama baslatiliyor."
exec uvicorn main:app --host 0.0.0.0 --port "${PORT:-8000}"
