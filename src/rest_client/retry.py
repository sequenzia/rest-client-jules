from tenacity import (
    Retrying,
    AsyncRetrying,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception
)
from .config import RetryConfig
from .exceptions import HTTPError, ConnectionError, TimeoutError

def _should_retry_exception(exception: BaseException, retry_statuses: list[int]) -> bool:
    if isinstance(exception, (ConnectionError, TimeoutError)):
        return True
    if isinstance(exception, HTTPError):
        # Retry if status code is in configured retry_statuses
        if exception.status_code and exception.status_code in retry_statuses:
            return True
    return False

def create_retry_strategy(config: RetryConfig) -> Retrying:
    return Retrying(
        stop=stop_after_attempt(config.max_attempts),
        wait=wait_exponential(multiplier=config.backoff_factor, max=config.backoff_max),
        retry=retry_if_exception(lambda e: _should_retry_exception(e, config.retry_statuses)),
        reraise=True
    )

def create_async_retry_strategy(config: RetryConfig) -> AsyncRetrying:
    return AsyncRetrying(
        stop=stop_after_attempt(config.max_attempts),
        wait=wait_exponential(multiplier=config.backoff_factor, max=config.backoff_max),
        retry=retry_if_exception(lambda e: _should_retry_exception(e, config.retry_statuses)),
        reraise=True
    )
