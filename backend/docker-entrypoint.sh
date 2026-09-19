#!/usr/bin/env bash
# Backend container giris noktasi.
#
# KOK NEDEN (InFailedSqlTransaction / 'Program olusturulamadi'):
# Uygulama kodu exercise_library_items tablosundan yeni kolonlari (difficulty,
# force_type, muscle_head, rom_profile, evidence_level, evidence_scope,
# reviewed_by, ...) bekliyor ama production Postgres'e bu kolonlar hic
# eklenmemisti. Cunku startup yalnizca `uvicorn` calistiriyor, Alembic
# migration'lari HIC uygulanmiyordu. database.migrate_schema() da Postgres'te
# kasitli olarak no-op oldugu icin sema eski kaldi ve selector sorgusu
# 'column does not exist' ile patladi -> transaction abort.
#
# Cozum: uygulama baslamadan ONCE semayi en son revision'a cek.
set -euo pipefail

cd /app

echo "[entrypoint] Alembic migration'lari uygulaniyor (head)..."
# head'e cekemezse container hizli ve gorunur sekilde dussun ki eksik sema ile
# sessizce calisip kullaniciya 'sunucu hatasi' dondurmesin.
python -m alembic upgrade head

echo "[entrypoint] Migration tamam. Uygulama baslatiliyor."
exec uvicorn main:app --host 0.0.0.0 --port "${PORT:-8000}"
