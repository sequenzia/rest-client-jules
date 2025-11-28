from typing import Optional, Dict, Any, Tuple
from .config import CacheConfig
import time

class CacheBackend:
    def get(self, key: str) -> Optional[Any]:
        raise NotImplementedError

    def set(self, key: str, value: Any, ttl: float):
        raise NotImplementedError

    def delete(self, key: str):
        raise NotImplementedError

    def clear(self):
        raise NotImplementedError

class MemoryCache(CacheBackend):
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self._cache: Dict[str, Tuple[Any, float]] = {} # key -> (value, expiry_time)

    def get(self, key: str) -> Optional[Any]:
        if key in self._cache:
            value, expiry = self._cache[key]
            if time.time() < expiry:
                return value
            else:
                del self._cache[key]
        return None

    def set(self, key: str, value: Any, ttl: float):
        if len(self._cache) >= self.max_size:
            # Simple LRU eviction could be better, but for now just clear or random eviction?
            # Or just don't add. Let's do simple popitem (FIFO-ish if dict is ordered)
             self._cache.pop(next(iter(self._cache)))

        self._cache[key] = (value, time.time() + ttl)

    def delete(self, key: str):
        if key in self._cache:
            del self._cache[key]

    def clear(self):
        self._cache.clear()

class CacheManager:
    def __init__(self, config: CacheConfig):
        self.config = config
        self.backend = config.backend if config.backend else MemoryCache()

    def get(self, key: str) -> Optional[Any]:
        if not self.config.enabled:
            return None
        return self.backend.get(key)

    def set(self, key: str, value: Any, ttl: Optional[float] = None):
        if not self.config.enabled:
            return
        ttl = ttl if ttl is not None else self.config.default_ttl
        self.backend.set(key, value, ttl)

    def generate_key(self, method: str, url: str, params: Optional[Dict] = None) -> str:
        # Simple key generation
        return f"{method}:{url}:{str(params)}"
