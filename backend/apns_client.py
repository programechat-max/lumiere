"""
Apple Push Notification service (APNs) HTTP/2 istemcisi (PROMPT 9).

APNS_KEY_ID / APNS_TEAM_ID / APNS_AUTH_KEY_PATH / APNS_BUNDLE_ID ortam
değişkenleri tanımlı değilse `is_configured()` False döner ve gönderim
denemesi yerine sadece log/DB kaydı düşülür - Apple Developer hesabı/.p8
anahtarı olmadan da uygulama hatasız çalışır."""
import datetime
import logging
import time
from typing import Optional

import httpx
from jose import jwt

from config import settings

logger = logging.getLogger(__name__)

_PRODUCTION_HOST = "https://api.push.apple.com"
_SANDBOX_HOST = "https://api.sandbox.push.apple.com"

_cached_provider_token: Optional[str] = None
_cached_token_issued_at: float = 0
_TOKEN_TTL_SECONDS = 55 * 60  # Apple: aynı token en fazla 1 saat yeniden kullanılabilir


class APNsError(Exception):
    def __init__(self, status_code: int, reason: str):
        self.status_code = status_code
        self.reason = reason
        super().__init__(f"APNs hatası ({status_code}): {reason}")


def is_configured() -> bool:
    return settings.apns_configured


def _get_provider_token() -> str:
    """ES256 imzalı JWT provider token üretir/yeniden kullanır (Apple Token-based auth)."""
    global _cached_provider_token, _cached_token_issued_at
    now = time.time()
    if _cached_provider_token and (now - _cached_token_issued_at) < _TOKEN_TTL_SECONDS:
        return _cached_provider_token

    with open(settings.APNS_AUTH_KEY_PATH, "r") as f:
        private_key = f.read()

    token = jwt.encode(
        {"iss": settings.APNS_TEAM_ID, "iat": int(now)},
        private_key,
        algorithm="ES256",
        headers={"kid": settings.APNS_KEY_ID},
    )
    _cached_provider_token = token
    _cached_token_issued_at = now
    return token


def send_push(
    device_token: str,
    title: str,
    body: str,
    badge: Optional[int] = None,
    sound: str = "default",
    category: Optional[str] = None,
    thread_id: Optional[str] = None,
    deep_link: Optional[str] = None,
    custom_data: Optional[dict] = None,
) -> dict:
    """Tek bir cihaza push bildirimi gönderir. Yapılandırma yoksa APNsError fırlatır
    (çağıran taraf bunu yakalayıp PushNotificationLog'a 'failed' olarak yazar)."""
    if not is_configured():
        raise APNsError(0, "APNs yapılandırılmamış (APNS_* ortam değişkenleri eksik).")

    host = _SANDBOX_HOST if settings.APNS_USE_SANDBOX else _PRODUCTION_HOST
    url = f"{host}/3/device/{device_token}"

    aps_payload = {"alert": {"title": title, "body": body}, "sound": sound}
    if badge is not None:
        aps_payload["badge"] = badge
    if category:
        aps_payload["category"] = category
    if thread_id:
        aps_payload["thread-id"] = thread_id

    payload = {"aps": aps_payload}
    # Hassas PII (sağlık metrikleri vb.) APNs payload'una asla ham metin olarak konmaz;
    # sadece uygulama içi yönlendirme için gerekli minimal veri taşınır.
    if deep_link:
        payload["deep_link"] = deep_link
    if custom_data:
        payload["data"] = {k: v for k, v in custom_data.items() if k not in ("weight", "calories", "notes")}

    headers = {
        "authorization": f"bearer {_get_provider_token()}",
        "apns-topic": settings.APNS_BUNDLE_ID,
        "apns-push-type": "alert",
        "apns-priority": "10",
        "apns-expiration": str(int(time.time()) + 3600),
    }

    with httpx.Client(http2=True, timeout=10.0) as client:
        response = client.post(url, headers=headers, json=payload)

    if response.status_code == 200:
        return {"status": "sent"}

    try:
        reason = response.json().get("reason", "Unknown")
    except Exception:
        reason = response.text
    logger.warning("APNs gönderim hatası: %s (token=%s...)", reason, device_token[:8])
    raise APNsError(response.status_code, reason)


# Apple'ın "bu token artık geçersiz" diye işaretlediği durumlar - bu durumlarda
# token veritabanından otomatik silinmelidir (bkz. notification_service.prune_invalid_token).
INVALID_TOKEN_REASONS = {"BadDeviceToken", "Unregistered", "DeviceTokenNotForTopic"}
