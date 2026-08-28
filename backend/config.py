"""
Merkezi uygulama ayarları (PROMPT 1/2/3/4/5/6/7/9/11).

Tüm gizli anahtarlar/servis kimlik bilgileri ortam değişkenlerinden okunur,
hiçbiri koda gömülü değildir. Bir servis için gerekli değişkenler tanımlı
değilse ilgili özellik "yapılandırılmamış" kabul edilir ve o alt sistem
sessizce devre dışı / mock modda çalışır — böylece bulut hesapları
(AWS, Stripe, Sentry, APNs) olmadan da uygulama hatasız açılır.

.env dosyası backend/ dizininde okunur (bkz. .env.example).
"""
import os
from functools import lru_cache
from typing import List, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


def _split_csv(value: str) -> List[str]:
    return [v.strip() for v in value.split(",") if v.strip()]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- Genel ---
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")  # development|staging|production
    APP_VERSION: str = os.getenv("APP_VERSION", "1.0.0")
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"

    # --- Veritabanı (PROMPT 1) ---
    # Boşsa SQLite'a düşer (sıfır konfigürasyonla yerel geliştirme).
    # PostgreSQL örneği: postgresql+psycopg://user:pass@localhost:5432/lumiere
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./sql_app.db")
    DB_POOL_SIZE: int = int(os.getenv("DB_POOL_SIZE", "20"))
    DB_MAX_OVERFLOW: int = int(os.getenv("DB_MAX_OVERFLOW", "40"))
    DB_POOL_TIMEOUT: int = int(os.getenv("DB_POOL_TIMEOUT", "30"))
    DB_POOL_RECYCLE: int = int(os.getenv("DB_POOL_RECYCLE", "1800"))

    # --- JWT / Auth (PROMPT 2) ---
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "GELISTIRME-ICIN-GECICI-ANAHTAR-DEGISTIR")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
    MAX_FAILED_LOGIN_ATTEMPTS: int = int(os.getenv("MAX_FAILED_LOGIN_ATTEMPTS", "5"))
    LOGIN_LOCKOUT_MINUTES: int = int(os.getenv("LOGIN_LOCKOUT_MINUTES", "15"))
    MAX_CONCURRENT_SESSIONS: int = int(os.getenv("MAX_CONCURRENT_SESSIONS", "3"))
    SESSION_INACTIVITY_DAYS: int = int(os.getenv("SESSION_INACTIVITY_DAYS", "30"))
    # NOT: Varsayılan False - yerel geliştirme/test https olmadan (http://localhost) çalışır.
    # ÜRETİMDE (ENVIRONMENT=production) BU DEğİŞKEN MUTLAKA "true" YAPıLMALI (bkz. .env.example).
    COOKIE_SECURE: bool = os.getenv("COOKIE_SECURE", "true" if os.getenv("ENVIRONMENT") == "production" else "false").lower() == "true"
    COOKIE_DOMAIN: Optional[str] = os.getenv("COOKIE_DOMAIN") or None

    # --- CORS (PROMPT 8 / kritik güvenlik açığı) ---
    # Virgülle ayrılmış izinli origin listesi. Boş/"*"=geliştirme modunda tüm origin'lere izin verir.
    ALLOWED_ORIGINS: str = os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:5173,http://localhost:3000,capacitor://localhost,http://localhost",
    )

    @property
    def allowed_origins_list(self) -> List[str]:
        raw = self.ALLOWED_ORIGINS.strip()
        if raw == "*":
            return ["*"]
        return _split_csv(raw)

    # --- Redis / Celery (PROMPT 5) ---
    REDIS_URL: Optional[str] = os.getenv("REDIS_URL") or None
    CELERY_TASK_ALWAYS_EAGER: bool = os.getenv("CELERY_TASK_ALWAYS_EAGER", "").lower() == "true"

    # --- AWS S3 (PROMPT 4) ---
    AWS_ACCESS_KEY_ID: Optional[str] = os.getenv("AWS_ACCESS_KEY_ID") or None
    AWS_SECRET_ACCESS_KEY: Optional[str] = os.getenv("AWS_SECRET_ACCESS_KEY") or None
    AWS_REGION: str = os.getenv("AWS_REGION", "eu-central-1")
    S3_BUCKET_NAME: Optional[str] = os.getenv("S3_BUCKET_NAME") or None
    S3_KMS_KEY_ID: Optional[str] = os.getenv("S3_KMS_KEY_ID") or None
    CLOUDFRONT_DOMAIN: Optional[str] = os.getenv("CLOUDFRONT_DOMAIN") or None

    @property
    def s3_configured(self) -> bool:
        return bool(self.AWS_ACCESS_KEY_ID and self.AWS_SECRET_ACCESS_KEY and self.S3_BUCKET_NAME)

    # --- Stripe (PROMPT 3) ---
    STRIPE_SECRET_KEY: Optional[str] = os.getenv("STRIPE_SECRET_KEY") or None
    STRIPE_WEBHOOK_SECRET: Optional[str] = os.getenv("STRIPE_WEBHOOK_SECRET") or None
    STRIPE_PRICE_PREMIUM_MONTHLY: Optional[str] = os.getenv("STRIPE_PRICE_PREMIUM_MONTHLY") or None
    STRIPE_PRICE_PREMIUM_ANNUAL: Optional[str] = os.getenv("STRIPE_PRICE_PREMIUM_ANNUAL") or None
    STRIPE_PRICE_COACHING: Optional[str] = os.getenv("STRIPE_PRICE_COACHING") or None
    TRIAL_PERIOD_DAYS: int = int(os.getenv("TRIAL_PERIOD_DAYS", "7"))

    @property
    def stripe_configured(self) -> bool:
        return bool(self.STRIPE_SECRET_KEY)

    # --- Sentry / gözlemlenebilirlik (PROMPT 7) ---
    SENTRY_DSN: Optional[str] = os.getenv("SENTRY_DSN") or None
    SENTRY_TRACES_SAMPLE_RATE: float = float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.05"))

    # --- APNs / iOS Push (PROMPT 9) ---
    APNS_KEY_ID: Optional[str] = os.getenv("APNS_KEY_ID") or None
    APNS_TEAM_ID: Optional[str] = os.getenv("APNS_TEAM_ID") or None
    APNS_AUTH_KEY_PATH: Optional[str] = os.getenv("APNS_AUTH_KEY_PATH") or None
    APNS_BUNDLE_ID: Optional[str] = os.getenv("APNS_BUNDLE_ID") or None
    APNS_USE_SANDBOX: bool = os.getenv("APNS_USE_SANDBOX", "true").lower() == "true"

    @property
    def apns_configured(self) -> bool:
        return bool(self.APNS_KEY_ID and self.APNS_TEAM_ID and self.APNS_AUTH_KEY_PATH and self.APNS_BUNDLE_ID)

    # --- Rate limiting (PROMPT 6) ---
    RATE_LIMIT_FREE_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_FREE_PER_MINUTE", "10"))
    RATE_LIMIT_PREMIUM_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_PREMIUM_PER_MINUTE", "100"))
    RATE_LIMIT_IP_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_IP_PER_MINUTE", "1000"))
    RATE_LIMIT_LOGIN_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_LOGIN_PER_MINUTE", "5"))

    # --- Admin bootstrap ---
    ADMIN_BOOTSTRAP_EMAILS: str = os.getenv("ADMIN_BOOTSTRAP_EMAILS", "")

    @property
    def admin_bootstrap_emails_list(self) -> List[str]:
        return [e.strip().lower() for e in self.ADMIN_BOOTSTRAP_EMAILS.split(",") if e.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
