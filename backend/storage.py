"""
Dosya depolama katmanı (PROMPT 4). AWS kimlik bilgileri (AWS_ACCESS_KEY_ID,
AWS_SECRET_ACCESS_KEY, S3_BUCKET_NAME) yapılandırılmışsa S3 kullanılır; değilse
mevcut yerel disk davranışına (backend/user_videos, backend/user_audio, ...)
sorunsuzca düşer - bulut hesabı olmadan da onboarding akışı çalışmaya devam eder."""
import logging
import mimetypes
import os
import secrets
import uuid
from typing import Optional

from config import settings

logger = logging.getLogger(__name__)

ALLOWED_MIME_PREFIXES = ("video/", "audio/", "image/")
MAX_FILE_SIZE_BYTES = 300 * 1024 * 1024  # 300MB - PROMPT 4 gerekliliği

_s3_client = None


def _get_s3_client():
    global _s3_client
    if not settings.s3_configured:
        return None
    if _s3_client is None:
        import boto3
        _s3_client = boto3.client(
            "s3",
            region_name=settings.AWS_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        )
    return _s3_client


def validate_upload(mime_type: str, size_bytes: int) -> Optional[str]:
    """Dosya doğrulama: boyut + MIME tipi. Hata varsa açıklama metni, yoksa None döner."""
    if size_bytes <= 0:
        return "Boş dosya."
    if size_bytes > MAX_FILE_SIZE_BYTES:
        return f"Dosya çok büyük ({MAX_FILE_SIZE_BYTES // (1024*1024)}MB üzeri)."
    if not any(mime_type.startswith(p) for p in ALLOWED_MIME_PREFIXES):
        return f"Desteklenmeyen dosya tipi: {mime_type}"
    return None


def build_object_key(user_id: int, category: str, filename: str) -> str:
    """Tahmin edilemez (36 karakter rastgele) S3 anahtarı üretir - presigned URL
    guessing riskine karşı (PROMPT 4 kısıtı)."""
    ext = os.path.splitext(filename)[1] or mimetypes.guess_extension("application/octet-stream") or ""
    random_suffix = secrets.token_hex(18)  # 36 hex karakter
    return f"users/{user_id}/{category}/{uuid.uuid4().hex}-{random_suffix}{ext}"


def generate_presigned_upload_url(object_key: str, mime_type: str, expires_in: int = 900) -> Optional[dict]:
    """Tarayıcı/uygulamanın backend'i atlayıp doğrudan S3'e yükleyebilmesi için presigned URL."""
    client = _get_s3_client()
    if client is None:
        return None
    extra_args = {"ContentType": mime_type}
    if settings.S3_KMS_KEY_ID:
        extra_args["ServerSideEncryption"] = "aws:kms"
        extra_args["SSEKMSKeyId"] = settings.S3_KMS_KEY_ID
    else:
        extra_args["ServerSideEncryption"] = "AES256"
    url = client.generate_presigned_url(
        "put_object",
        Params={"Bucket": settings.S3_BUCKET_NAME, "Key": object_key, **extra_args},
        ExpiresIn=expires_in,
    )
    return {"upload_url": url, "object_key": object_key, "expires_in": expires_in}


def generate_presigned_download_url(object_key: str, expires_in: int = 3600) -> Optional[str]:
    client = _get_s3_client()
    if client is None:
        return None
    return client.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.S3_BUCKET_NAME, "Key": object_key},
        ExpiresIn=expires_in,
    )


def delete_object(object_key: str) -> bool:
    client = _get_s3_client()
    if client is None:
        # Yerel disk fallback - dosya zaten backend/user_videos vb. altında; en iyi çaba ile sil.
        for base in ("user_videos", "user_audio"):
            local_path = os.path.join(base, os.path.basename(object_key))
            if os.path.exists(local_path):
                os.remove(local_path)
                return True
        return False
    client.delete_object(Bucket=settings.S3_BUCKET_NAME, Key=object_key)
    return True


def save_local_fallback(directory: str, filename: str, content: bytes) -> str:
    os.makedirs(directory, exist_ok=True)
    path = os.path.join(directory, filename)
    with open(path, "wb") as f:
        f.write(content)
    return path
