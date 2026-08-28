"""
HTTP middleware katmanı (PROMPT 6 & 7):
  - Request-ID enjeksiyonu + yapılandırılmış (JSON) erişim logu
  - IP bazlı genel hız sınırlama (DDoS koruması)
  - Güvenlik header'ları (PROMPT 8 ile hizalı: CSP, X-Frame-Options, HSTS, ...)
"""
import json
import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from config import settings
from rate_limit import check_rate_limit

access_logger = logging.getLogger("lumiere.access")

SENSITIVE_PATHS = ("/api/auth/login", "/api/auth/register", "/api/v1/auth")


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Her isteğe X-Request-ID atar ve yapılandırılmış JSON erişim logu üretir."""

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        start = time.perf_counter()
        request.state.request_id = request_id
        try:
            response = await call_next(request)
        except Exception:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            access_logger.exception(json.dumps({
                "request_id": request_id, "method": request.method, "path": request.url.path,
                "status": 500, "duration_ms": duration_ms,
            }))
            raise
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        response.headers["X-Request-ID"] = request_id

        log_path = request.url.path
        is_sensitive = any(log_path.startswith(p) for p in SENSITIVE_PATHS)
        log_level = logging.ERROR if response.status_code >= 500 else (
            logging.WARNING if response.status_code >= 400 else logging.INFO
        )
        # Hassas yollarda (login/register) gövde/parametre loglanmaz, sadece meta bilgi.
        access_logger.log(log_level, json.dumps({
            "request_id": request_id,
            "method": request.method,
            "path": log_path,
            "status": response.status_code,
            "duration_ms": duration_ms,
            "query_params": None if is_sensitive else dict(request.query_params),
            "client_ip": request.client.host if request.client else None,
        }))
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """PROMPT 8: Tarayıcı tarafında XSS/clickjacking/karışık-içerik risklerini azaltan
    standart güvenlik başlıkları. API yanıtları için CSP script kaynaklarını kısıtlar."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("X-XSS-Protection", "1; mode=block")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; frame-ancestors 'none'; object-src 'none'",
        )
        if settings.ENVIRONMENT == "production":
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        return response


class IPRateLimitMiddleware(BaseHTTPMiddleware):
    """PROMPT 6: Tüm /api yollarına IP bazlı genel hız sınırı (DDoS koruması).
    Kullanıcı/plan bazlı ince taneli sınırlama, ilgili endpoint'lerde ayrıca uygulanır."""

    async def dispatch(self, request: Request, call_next):
        if not request.url.path.startswith("/api"):
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        result = check_rate_limit(f"ip:{client_ip}", settings.RATE_LIMIT_IP_PER_MINUTE, 60)
        if not result.allowed:
            return JSONResponse(
                status_code=429,
                content={"error": {"code": "RATE_LIMITED", "message": "Çok fazla istek gönderildi. Lütfen biraz sonra tekrar deneyin.", "details": {}}},
                headers={**result.headers, "Retry-After": str(result.reset_seconds)},
            )
        response = await call_next(request)
        for key, value in result.headers.items():
            response.headers.setdefault(key, value)
        return response
