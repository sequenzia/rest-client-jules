from typing import List, Optional, Union, Dict, Any, Callable
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class RetryConfig(BaseSettings):
    max_attempts: int = 3
    retry_statuses: List[int] = Field(default_factory=lambda: [408, 429, 500, 502, 503, 504])
    backoff_factor: float = 0.5
    backoff_max: float = 60.0

    model_config = SettingsConfigDict(env_prefix="REST_CLIENT_RETRY_")

class TimeoutConfig(BaseSettings):
    connect: float = 5.0
    read: float = 30.0
    write: float = 30.0
    pool: float = 10.0
    total: Optional[float] = None

    model_config = SettingsConfigDict(env_prefix="REST_CLIENT_TIMEOUT_")

class CircuitBreakerConfig(BaseSettings):
    failure_threshold: int = 5
    success_threshold: int = 2
    reset_timeout: float = 30.0
    half_open_max_calls: int = 3
    failure_rate_threshold: float = 0.5
    sampling_duration: float = 60.0
    excluded_exceptions: List[Any] = Field(default_factory=list)
    included_status_codes: List[int] = Field(default_factory=lambda: [500, 502, 503, 504])
    per_host: bool = False
    fallback: Optional[Callable] = None

    model_config = SettingsConfigDict(env_prefix="REST_CLIENT_CB_")

class RateLimitConfig(BaseSettings):
    strategy: str = "token_bucket"
    max_requests: int = 100
    time_window: float = 60.0
    burst_size: int = 10
    queue_size: int = 50
    queue_timeout: float = 30.0
    respect_retry_after: bool = True

    model_config = SettingsConfigDict(env_prefix="REST_CLIENT_RATELIMIT_")

class CacheConfig(BaseSettings):
    enabled: bool = False
    backend: Any = None # Placeholder for cache backend
    default_ttl: float = 300.0
    cacheable_status_codes: List[int] = Field(default_factory=lambda: [200, 203, 204, 206, 300, 301, 308])

    model_config = SettingsConfigDict(env_prefix="REST_CLIENT_CACHE_")

class ClientConfig(BaseSettings):
    base_url: str
    headers: Dict[str, str] = Field(default_factory=dict)
    timeout: Union[float, TimeoutConfig] = Field(default_factory=TimeoutConfig)
    retry: RetryConfig = Field(default_factory=RetryConfig)
    verify_ssl: bool = True
    http2: bool = False
    follow_redirects: bool = True
    max_redirects: int = 20
    circuit_breaker: CircuitBreakerConfig = Field(default_factory=CircuitBreakerConfig)
    rate_limit: RateLimitConfig = Field(default_factory=RateLimitConfig)
    cache: CacheConfig = Field(default_factory=CacheConfig)

    model_config = SettingsConfigDict(env_prefix="REST_CLIENT_")
