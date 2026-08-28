"""
Dağıtık hız sınırlama (rate limiting) - PROMPT 6.

Redis yapılandırılmışsa (REDIS_URL) sabit pencere sayaçları Redis'te tutulur,
böylece birden fazla API süreci arasında tutarlı çalışır. Redis yoksa süreç-içi
bellek sözlüğüne düşer (tek süreçli geliştirme/test ortamı için yeterlidir).
"""
import threading
import time
from typing import Optional, Tuple

from config import settings

try:
    import redis as redis_lib
except ImportError:  # pragma: no cover
    redis_lib = None

_redis_client = None
_redis_lock = threading.Lock()


def get_redis():
    global _redis_client
    if not settings.REDIS_URL or redis_lib is None:
        return None
    if _redis_client is None:
        with _redis_lock:
            if _redis_client is None:
                try:
                    _redis_client = redis_lib.from_url(settings.REDIS_URL, decode_responses=True)
                    _redis_client.ping()
                except Exception:
                    _redis_client = False  # bağlanamadı, tekrar denemeyi bırak
    return _redis_client or None


class _InMemoryStore:
    """Redis mevcut olmadığında kullanılan basit sabit-pencere sayaç deposu."""

    def __init__(self):
        self._data = {}
        self._lock = threading.Lock()

    def incr(self, key: str, window_seconds: int) -> Tuple[int, int]:
        now = int(time.time())
        window_start = now - (now % window_seconds)
        with self._lock:
            entry = self._data.get(key)
            if not entry or entry[0] != window_start:
                entry = [window_start, 0]
            entry[1] += 1
            self._data[key] = entry
            reset_in = window_start + window_seconds - now
            return entry[1], max(reset_in, 1)


_memory_store = _InMemoryStore()


class RateLimitResult:
    def __init__(self, allowed: bool, limit: int, remaining: int, reset_seconds: int):
        self.allowed = allowed
        self.limit = limit
        self.remaining = remaining
        self.reset_seconds = reset_seconds

    @property
    def headers(self) -> dict:
        return {
            "X-RateLimit-Limit": str(self.limit),
            "X-RateLimit-Remaining": str(max(self.remaining, 0)),
            "X-RateLimit-Reset": str(self.reset_seconds),
        }


def check_rate_limit(key: str, limit: int, window_seconds: int = 60) -> RateLimitResult:
    """Sabit pencere sayaç algoritması. `key` bazında `window_seconds` içinde
    en fazla `limit` istek olmasını sağlar."""
    client = get_redis()
    if client is not None:
        try:
            now = int(time.time())
            window_start = now - (now % window_seconds)
            redis_key = f"ratelimit:{key}:{window_start}"
            count = client.incr(redis_key)
            if count == 1:
                client.expire(redis_key, window_seconds)
            reset_in = window_start + window_seconds - now
            return RateLimitResult(count <= limit, limit, limit - count, max(reset_in, 1))
        except Exception:
            pass  # Redis çökerse bellek deposuna düş - kullanıcıyı asla kilitlemeyelim.

    count, reset_in = _memory_store.incr(key, window_seconds)
    return RateLimitResult(count <= limit, limit, limit - count, reset_in)


def plan_limit_per_minute(plan_type: Optional[str]) -> int:
    plan = (plan_type or "FREE").upper()
    if plan in ("PREMIUM_MONTHLY", "PREMIUM_ANNUAL"):
        return settings.RATE_LIMIT_PREMIUM_PER_MINUTE
    if plan == "COACHING":
        return 10_000  # sınırsıza yakın
    return settings.RATE_LIMIT_FREE_PER_MINUTE


def enforce_plan_rate_limit(feature: str):
    """PROMPT 6: AI-yoğun endpoint'ler (chat, plan üretimi, onboarding analizleri) için
    abonelik planına göre dakikalık hız sınırı dependency'si. `Depends(enforce_plan_rate_limit("ai"))`
    şeklinde mevcut endpoint imzasına EK bir parametre olarak eklenir - davranışı bozmaz,
    sadece limit aşıldığında 429 döner."""
    from fastapi import Depends, HTTPException, Request
    from sqlalchemy.orm import Session

    import auth
    import billing_service
    import models
    from database import get_db

    def dependency(
        request: Request,
        current_user: "models.User" = Depends(auth.get_current_user),
        db: Session = Depends(get_db),
    ):
        sub = billing_service.get_or_create_subscription(db, current_user.id)
        limit = plan_limit_per_minute(sub.plan_type)
        result = check_rate_limit(f"plan:{feature}:{current_user.id}", limit, 60)
        if not result.allowed:
            raise HTTPException(
                status_code=429,
                detail="Bu özellik için dakikalık kullanım limitine ulaştınız. Premium'a geçerek limiti kaldırabilirsiniz.",
                headers=result.headers,
            )
        return True

    return dependency
