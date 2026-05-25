"""Tiny cache abstraction.

Uses Redis when ``REDIS_URL`` is configured (production), otherwise a process
-local TTL dict. The dashboard's "sub-100ms reads" requirement is satisfied by
either backend; the interface is deliberately minimal.
"""

from __future__ import annotations

import json
import time
from typing import Any

from app.config import settings


class _MemoryCache:
    def __init__(self) -> None:
        self._store: dict[str, tuple[float, str]] = {}

    def get(self, key: str) -> Any | None:
        item = self._store.get(key)
        if item is None:
            return None
        expires_at, payload = item
        if expires_at < time.time():
            self._store.pop(key, None)
            return None
        return json.loads(payload)

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        ttl = ttl if ttl is not None else settings.cache_ttl_seconds
        self._store[key] = (time.time() + ttl, json.dumps(value, default=str))


class _RedisCache:
    def __init__(self, url: str) -> None:
        import redis  # imported lazily so local mode never needs the package

        self._client = redis.Redis.from_url(url, decode_responses=True)

    def get(self, key: str) -> Any | None:
        raw = self._client.get(key)
        return json.loads(raw) if raw is not None else None

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        ttl = ttl if ttl is not None else settings.cache_ttl_seconds
        self._client.set(key, json.dumps(value, default=str), ex=ttl)


def _build_cache():
    if settings.redis_url:
        return _RedisCache(settings.redis_url)
    return _MemoryCache()


cache = _build_cache()
