"""
Bilgi katmanı TTL cache — Redis (REDIS_URL tanımlıysa) + süreç-içi fallback.

rate_limit.py'deki kalıbı izler: Redis mevcut değilse veya bağlanamazsa
süreç-içi sözlüğe düşer (tek süreçli geliştirme/test için yeterli). Aynı
besin/konu için USDA veya PubMed'e tekrar tekrar gidilmesini önler.
"""
import json
import threading
import time
import logging

from config import settings
from rate_limit import get_redis

logger = logging.getLogger(__name__)

# Süreç-içi fallback deposu {key: (expires_at, value)}
_memory_cache = {}
_memory_lock = threading.Lock()

# Varsayılan TTL'ler (saniye)
TTL_USDA_FOOD = 30 * 24 * 3600      # besin verisi nadiren değişir - 30 gün
TTL_PUBMED = 7 * 24 * 3600          # bilimsel sorgular - 7 gün
TTL_LIB_SEARCH = 6 * 3600           # kütüphane arama sonuçları - 6 saat


def _memory_get(key: str):
    with _memory_lock:
        entry = _memory_cache.get(key)
        if not entry:
            return None
        expires_at, value = entry
        if expires_at < time.time():
            _memory_cache.pop(key, None)
            return None
        return value


def _memory_set(key: str, value, ttl: int):
    with _memory_lock:
        # Basit boyut sınırı: en eski kayıtları bırak (2000 kayıt)
        if len(_memory_cache) > 2000:
            oldest = sorted(_memory_cache.items(), key=lambda kv: kv[1][0])[:500]
            for k, _ in oldest:
                _memory_cache.pop(k, None)
        _memory_cache[key] = (time.time() + ttl, value)


def cache_get(key: str):
    """Değer yoksa None döner. Değerler JSON-uyumlu olmalı."""
    redis_client = get_redis()
    if redis_client is not None:
        try:
            raw = redis_client.get(key)
            if raw is not None:
                return json.loads(raw)
        except Exception:
            pass  # Redis hatasında süreç-içi cache'e düş
    return _memory_get(key)


def cache_set(key: str, value, ttl: int = TTL_LIB_SEARCH):
    redis_client = get_redis()
    if redis_client is not None:
        try:
            redis_client.setex(key, ttl, json.dumps(value, ensure_ascii=False))
            return
        except Exception:
            pass
    _memory_set(key, value, ttl)


def cached(key: str, ttl: int = TTL_LIB_SEARCH, producer=None):
    """cache_get + cache_set sarmalayıcı: producer fonksiyonu yalnızca cache
    boşsa çağrılır. producer None dönerse sonuç cache'lenmez (hata durumu)."""
    value = cache_get(key)
    if value is not None:
        return value
    value = producer()
    if value is not None:
        cache_set(key, value, ttl)
    return value