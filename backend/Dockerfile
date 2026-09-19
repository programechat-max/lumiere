# LUMIERE backend - üretim/geliştirme container görüntüsü (PROMPT 1/5/10).
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev curl ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chmod +x docker-entrypoint.sh

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Uygulamadan once Alembic migration'larini uygula (bkz. docker-entrypoint.sh).
# Aksi halde model yeni kolonlari beklerken production semasi eski kalir ve
# sorgular 'column does not exist' -> InFailedSqlTransaction ile patlar.
CMD ["./docker-entrypoint.sh"]
