import time
import asyncio
import logging
from typing import Any, Optional, Dict, Tuple

logger = logging.getLogger("cache_service")

class MemoryCache:
    def __init__(self):
        self._cache: Dict[str, Tuple[float, Any]] = {}

    def get(self, key: str) -> Optional[Any]:
        if key in self._cache:
            expires_at, val = self._cache[key]
            if time.time() < expires_at:
                return val
            else:
                del self._cache[key]
        return None

    def set(self, key: str, value: Any, ttl_seconds: int = 300):
        self._cache[key] = (time.time() + ttl_seconds, value)

    def invalidate(self, key_prefix: str = ""):
        if not key_prefix:
            self._cache.clear()
            return
        keys_to_del = [k for k in self._cache if k.startswith(key_prefix)]
        for k in keys_to_del:
            del self._cache[k]

cache = MemoryCache()
