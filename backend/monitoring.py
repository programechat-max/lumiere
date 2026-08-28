"""
Gözlemlenebilirlik: hata takibi (Sentry), metrikler (Prometheus) ve health check'ler
(PROMPT 7). SENTRY_DSN tanımlı değilse Sentry devre dışı kalır - kod hiçbir zaman
üçüncü parti bir hesap olmadan çökmez."""
import datetime
import logging

from fastapi import APIRouter, Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session

from config import settings
from database import get_db, engine

logger = logging.getLogger(__name__)

APP_START_TIME = datetime.datetime.utcnow()

router = APIRouter(tags=["monitoring"])


def init_sentry() -> None:
    if not settings.SENTRY_DSN:
        logger.info("SENTRY_DSN tanımlı değil - hata takibi devre dışı (yerel geliştirme modu).")
        return
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration

        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            environment=settings.ENVIRONMENT,
            release=settings.APP_VERSION,
            traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
            integrations=[FastApiIntegration()],
            # 404/beklenen istemci hatalarını gürültü olarak eleriz.
            before_send=lambda event, hint: None if event.get("level") == "info" else event,
        )
        logger.info("Sentry hata takibi etkinleştirildi (environment=%s).", settings.ENVIRONMENT)
    except Exception as exc:  # pragma: no cover
        logger.warning("Sentry başlatılamadı: %s", exc)


def init_metrics(app: FastAPI) -> None:
    """Prometheus /metrics endpoint'i - p50/p95/p99 gecikme, istek sayacı vb."""
    try:
        from prometheus_fastapi_instrumentator import Instrumentator
        Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)
        logger.info("Prometheus /metrics endpoint'i etkinleştirildi.")
    except Exception as exc:  # pragma: no cover
        logger.warning("Prometheus instrumentator başlatılamadı: %s", exc)


def _check_database() -> dict:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok"}
    except Exception as exc:
        return {"status": "error", "detail": str(exc)}


def _check_redis() -> dict:
    if not settings.REDIS_URL:
        return {"status": "not_configured"}
    try:
        from rate_limit import get_redis
        client = get_redis()
        if client is None:
            return {"status": "error", "detail": "bağlantı kurulamadı"}
        client.ping()
        return {"status": "ok"}
    except Exception as exc:
        return {"status": "error", "detail": str(exc)}


@router.get("/health")
def liveness():
    """Canlılık kontrolü — süreç ayakta mı? Load balancer bunu kullanır."""
    return {
        "status": "ok",
        "version": settings.APP_VERSION,
        "uptime_seconds": int((datetime.datetime.utcnow() - APP_START_TIME).total_seconds()),
    }


@router.get("/ready")
def readiness():
    """Hazırlık kontrolü — bağımlılıklar (DB, Redis) sağlıklı mı?"""
    checks = {
        "database": _check_database(),
        "redis": _check_redis(),
        "gemini_api_key_configured": bool(__import__("os").getenv("GEMINI_API_KEY") or __import__("os").getenv("GOOGLE_API_KEY")),
    }
    is_ready = checks["database"]["status"] == "ok"
    return {
        "status": "ok" if is_ready else "degraded",
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "checks": checks,
    }
