import time
import enum
import threading
from typing import Optional
from .config import CircuitBreakerConfig

class CircuitState(enum.Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

class CircuitBreakerMetrics:
    def __init__(self):
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[float] = None
        self.total_calls = 0
        self.total_failures = 0

class CircuitBreaker:
    def __init__(self, config: CircuitBreakerConfig):
        self.config = config
        self.state = CircuitState.CLOSED
        self.metrics = CircuitBreakerMetrics()
        self._lock = threading.RLock()
        self.opened_at: Optional[float] = None

    def allow_request(self) -> bool:
        with self._lock:
            if self.state == CircuitState.OPEN:
                if time.time() - self.opened_at > self.config.reset_timeout:
                    self._transition_to_half_open()
                    return True
                return False
            elif self.state == CircuitState.HALF_OPEN:
                # In half-open state, we limit concurrent calls (simple implementation: just allow one by one or up to limit)
                # For simplicity here, we rely on the caller to manage concurrency or we check if we've exceeded half_open_max_calls
                # But since we don't track active calls easily without more state, let's just allow it and count the result.
                # A more robust implementation would track active calls.
                return True
            return True

    def record_success(self):
        with self._lock:
            if self.state == CircuitState.HALF_OPEN:
                self.metrics.success_count += 1
                if self.metrics.success_count >= self.config.success_threshold:
                    self._transition_to_closed()
            elif self.state == CircuitState.CLOSED:
                self.metrics.failure_count = 0

    def record_failure(self, exception: Exception):
        # Check if exception should be excluded
        for excluded in self.config.excluded_exceptions:
            if isinstance(exception, excluded):
                return

        with self._lock:
            self.metrics.last_failure_time = time.time()
            self.metrics.total_failures += 1

            if self.state == CircuitState.CLOSED:
                self.metrics.failure_count += 1
                if self.metrics.failure_count >= self.config.failure_threshold:
                    self._transition_to_open()
            elif self.state == CircuitState.HALF_OPEN:
                self._transition_to_open()

    def _transition_to_open(self):
        self.state = CircuitState.OPEN
        self.opened_at = time.time()
        self.metrics.failure_count = 0
        self.metrics.success_count = 0

    def _transition_to_half_open(self):
        self.state = CircuitState.HALF_OPEN
        self.metrics.success_count = 0
        self.metrics.failure_count = 0

    def _transition_to_closed(self):
        self.state = CircuitState.CLOSED
        self.metrics.failure_count = 0
        self.metrics.success_count = 0
        self.opened_at = None

    def force_open(self):
        with self._lock:
            self._transition_to_open()

    def force_close(self):
        with self._lock:
            self._transition_to_closed()

    def reset(self):
        with self._lock:
            self._transition_to_closed()
            self.metrics = CircuitBreakerMetrics()


class AsyncCircuitBreaker(CircuitBreaker):
    """
    Async aware circuit breaker?
    The logic is mostly time and counter based, so the sync version works for async too if we use thread-safe locks.
    However, for high concurrency async, we might want to avoid blocking locks.
    But for MVP, the RLock is fine as critical sections are very short.
    """
    pass
