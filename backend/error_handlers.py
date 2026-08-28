"""
Tutarlı hata formatı (PROMPT 6): { error: { code, message, details } }.
Stack trace'ler istemciye asla sızdırılmaz, sadece sunucu loglarına yazılır.
"""
import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from starlette.responses import JSONResponse

logger = logging.getLogger("lumiere.errors")

_CODE_BY_STATUS = {
    400: "BAD_REQUEST", 401: "UNAUTHORIZED", 403: "FORBIDDEN", 404: "NOT_FOUND",
    409: "CONFLICT", 413: "PAYLOAD_TOO_LARGE", 422: "UNPROCESSABLE_ENTITY",
    429: "RATE_LIMITED", 500: "INTERNAL_ERROR", 503: "SERVICE_UNAVAILABLE",
}


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(HTTPException)
    async def handle_http_exception(request: Request, exc: HTTPException):
        code = _CODE_BY_STATUS.get(exc.status_code, "ERROR")
        # NOT: Geriye dönük uyumluluk için `detail` alanı KORUNUR (mevcut frontend/testler
        # `err.detail`/`response.json()["detail"]` bekliyor). Yeni standart `error.{code,message,details}`
        # yapısı EK olarak sağlanır - istemciler kademeli olarak yeni forma geçebilir.
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail, "error": {"code": code, "message": exc.detail, "details": {}}},
            headers=exc.headers or {},
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, exc: RequestValidationError):
        errors = jsonable_encoder(exc.errors())
        return JSONResponse(
            status_code=422,
            content={
                "detail": errors,
                "error": {"code": "VALIDATION_ERROR", "message": "Geçersiz istek verisi.", "details": {"errors": errors}},
            },
        )

    @app.exception_handler(Exception)
    async def handle_unhandled_exception(request: Request, exc: Exception):
        request_id = getattr(request.state, "request_id", None)
        logger.exception("Beklenmeyen sunucu hatası [request_id=%s]", request_id)
        try:
            import sentry_sdk
            sentry_sdk.capture_exception(exc)
        except Exception:
            pass
        return JSONResponse(
            status_code=500,
            content={"error": {"code": "INTERNAL_ERROR", "message": "Sunucuda beklenmeyen bir hata oluştu.", "details": {}}},
        )
