import time
import threading
from typing import Dict, Optional, Any
from .config import RateLimitConfig

class RateLimitStrategy:
    def acquire(self) -> bool:
        raise NotImplementedError

class TokenBucket(RateLimitStrategy):
    def __init__(self, rate: float, capacity: int):
        self._rate = rate
        self._capacity = float(capacity)
        self._tokens = float(capacity)
        self._last_refill = time.time()
        self._lock = threading.RLock()

    def acquire(self) -> bool:
        with self._lock:
            now = time.time()
            elapsed = now - self._last_refill
            self._tokens = min(self._capacity, self._tokens + elapsed * self._rate)
            self._last_refill = now

            if self._tokens >= 1:
                self._tokens -= 1
                return True
            return False

class RateLimiter:
    def __init__(self, config: RateLimitConfig):
        self.config = config
        self._limiters: Dict[str, RateLimitStrategy] = {}
        self._lock = threading.RLock()

        # Global limiter
        if config.strategy == "token_bucket":
            rate = config.max_requests / config.time_window
            self.global_limiter = TokenBucket(rate, config.max_requests)
        else:
            # Fallback to token bucket for now as it's the most common
            rate = config.max_requests / config.time_window
            self.global_limiter = TokenBucket(rate, config.max_requests)

    def acquire(self, key: Optional[str] = None) -> bool:
        # Check global limit first
        if not self.global_limiter.acquire():
             return False

        # If per-host or per-endpoint limiting is implemented, check here using 'key'
        return True

    def get_status(self) -> Any:
        # TODO: Return structured status
        pass
