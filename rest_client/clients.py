from typing import Optional, Dict, Any, Union, List
import httpx
from .config import ClientConfig, TimeoutConfig, RetryConfig, CircuitBreakerConfig
from .exceptions import (
    HTTPError, ClientResponseError, AuthenticationError, ForbiddenError,
    NotFoundError, RateLimitError, ServerError, ConnectionError,
    TimeoutError, ConnectTimeoutError, ReadTimeoutError, WriteTimeoutError,
    CircuitBreakerOpenError
)
from .retry import create_retry_strategy, create_async_retry_strategy
from .circuit_breaker import CircuitBreaker, AsyncCircuitBreaker
from .rate_limit import RateLimiter, RateLimitConfig
from .cache import CacheManager, CacheConfig
from .pagination import Paginator, AsyncPaginator, PaginationStrategy, OffsetLimitPagination
from .middleware import Middleware, SyncMiddleware

class Client:
    def __init__(
        self,
        base_url: str,
        headers: Optional[Dict[str, str]] = None,
        timeout: Union[float, TimeoutConfig, None] = None,
        auth: Optional[Any] = None,
        retry: Optional[RetryConfig] = None,
        circuit_breaker: Optional[CircuitBreakerConfig] = None,
        rate_limit: Optional[RateLimitConfig] = None,
        cache: Optional[CacheConfig] = None,
        middleware: Optional[List[SyncMiddleware]] = None,
        **kwargs
    ):
        self.config = ClientConfig(
            base_url=base_url,
            headers=headers or {},
            **kwargs
        )
        self.middleware = middleware or []
        if timeout is not None:
             if isinstance(timeout, (int, float)):
                  self.config.timeout = TimeoutConfig(connect=timeout, read=timeout, write=timeout, pool=timeout)
             else:
                  self.config.timeout = timeout

        if retry is not None:
            self.config.retry = retry

        if circuit_breaker is not None:
            self.config.circuit_breaker = circuit_breaker

        if rate_limit is not None:
            self.config.rate_limit = rate_limit

        if cache is not None:
            self.config.cache = cache

        self._client = httpx.Client(
            base_url=self.config.base_url,
            headers=self.config.headers,
            timeout=self._build_httpx_timeout(self.config.timeout),
            auth=auth,
            verify=self.config.verify_ssl,
            http2=self.config.http2,
            follow_redirects=self.config.follow_redirects,
            max_redirects=self.config.max_redirects,
        )
        self.circuit_breaker = CircuitBreaker(self.config.circuit_breaker)
        self._retry_strategy = create_retry_strategy(self.config.retry)
        self.rate_limiter = RateLimiter(self.config.rate_limit)
        self.cache = CacheManager(self.config.cache)

    def _build_httpx_timeout(self, timeout_config: Union[float, TimeoutConfig]) -> httpx.Timeout:
        if isinstance(timeout_config, (int, float)):
             return httpx.Timeout(timeout_config)
        return httpx.Timeout(
            connect=timeout_config.connect,
            read=timeout_config.read,
            write=timeout_config.write,
            pool=timeout_config.pool
        )

    def request(self, method: str, url: str, **kwargs) -> httpx.Response:
        # 1. Check Rate Limit
        if not self.rate_limiter.acquire():
             # For MVP, raise an error if client-side rate limit is exceeded.
             # In a more advanced implementation, we might queue or sleep.
             raise RateLimitError("Client-side rate limit exceeded")

        # 2. Check Cache
        cache_key = self.cache.generate_key(method, url, kwargs.get("params"))
        if method.upper() in ["GET", "HEAD"]:
            cached_response = self.cache.get(cache_key)
            if cached_response:
                return cached_response

        # Core request logic (with Retry & Circuit Breaker)
        def _core_request(req_obj: httpx.Request) -> httpx.Response:
            def _request_attempt():
                if not self.circuit_breaker.allow_request():
                    raise CircuitBreakerOpenError("Circuit breaker is open")

                try:
                    # Use send() instead of request() since we have a request object
                    response = self._client.send(req_obj)
                    response.raise_for_status()
                    self.circuit_breaker.record_success()

                    # Cache successful response if eligible
                    if method.upper() in ["GET", "HEAD"] and response.status_code in self.config.cache.cacheable_status_codes:
                        self.cache.set(cache_key, response)

                    return response
                except httpx.HTTPStatusError as e:
                    # Check if this status code should trip the circuit breaker
                    if e.response.status_code in self.config.circuit_breaker.included_status_codes:
                        self.circuit_breaker.record_failure(e)
                    else:
                        self.circuit_breaker.record_success()

                    self._handle_http_error(e)
                except (httpx.ConnectTimeout, httpx.ReadTimeout, httpx.WriteTimeout, httpx.TimeoutException) as e:
                    self.circuit_breaker.record_failure(e)
                    if isinstance(e, httpx.ConnectTimeout):
                        raise ConnectTimeoutError(str(e)) from e
                    elif isinstance(e, httpx.ReadTimeout):
                        raise ReadTimeoutError(str(e)) from e
                    elif isinstance(e, httpx.WriteTimeout):
                        raise WriteTimeoutError(str(e)) from e
                    else:
                        raise TimeoutError(str(e)) from e
                except httpx.NetworkError as e:
                    self.circuit_breaker.record_failure(e)
                    raise ConnectionError(str(e)) from e
                except Exception as e:
                    if isinstance(e, HTTPError): # Already handled
                        raise e
                    # Check if unknown exceptions should trip CB? Configurable via excluded_exceptions
                    self.circuit_breaker.record_failure(e)
                    raise

            return self._retry_strategy(_request_attempt)

        # Build request object
        request = self._client.build_request(method, url, **kwargs)

        # Apply middleware
        def call_next(req: httpx.Request, index: int = 0) -> httpx.Response:
            if index < len(self.middleware):
                middleware = self.middleware[index]
                return middleware(req, lambda r: call_next(r, index + 1))
            else:
                return _core_request(req)

        return call_next(request)

    def paginate(
        self,
        url: str,
        strategy: Optional[PaginationStrategy] = None,
        **kwargs
    ) -> Paginator:
        if strategy is None:
            strategy = OffsetLimitPagination() # Default
        return Paginator(self, url, strategy, **kwargs)

    def _handle_http_error(self, e: httpx.HTTPStatusError):
        status_code = e.response.status_code
        message = str(e)
        response = e.response

        if status_code == 401:
            raise AuthenticationError(message, response)
        elif status_code == 403:
            raise ForbiddenError(message, response)
        elif status_code == 404:
            raise NotFoundError(message, response)
        elif status_code == 429:
             retry_after = response.headers.get("Retry-After")
             retry_after_seconds = None
             if retry_after:
                 try:
                     retry_after_seconds = float(retry_after)
                 except ValueError:
                     pass # Handle date format later
             raise RateLimitError(message, response, retry_after=retry_after_seconds)
        elif 400 <= status_code < 500:
            raise ClientResponseError(message, response)
        elif 500 <= status_code < 600:
            raise ServerError(message, response)
        else:
            raise HTTPError(message, response)


    def get(self, url: str, **kwargs) -> httpx.Response:
        return self.request("GET", url, **kwargs)

    def post(self, url: str, **kwargs) -> httpx.Response:
        return self.request("POST", url, **kwargs)

    def put(self, url: str, **kwargs) -> httpx.Response:
        return self.request("PUT", url, **kwargs)

    def patch(self, url: str, **kwargs) -> httpx.Response:
        return self.request("PATCH", url, **kwargs)

    def delete(self, url: str, **kwargs) -> httpx.Response:
        return self.request("DELETE", url, **kwargs)

    def head(self, url: str, **kwargs) -> httpx.Response:
        return self.request("HEAD", url, **kwargs)

    def options(self, url: str, **kwargs) -> httpx.Response:
        return self.request("OPTIONS", url, **kwargs)

    def close(self):
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

class AsyncClient:
    def __init__(
        self,
        base_url: str,
        headers: Optional[Dict[str, str]] = None,
        timeout: Union[float, TimeoutConfig, None] = None,
        auth: Optional[Any] = None,
        retry: Optional[RetryConfig] = None,
        circuit_breaker: Optional[CircuitBreakerConfig] = None,
        rate_limit: Optional[RateLimitConfig] = None,
        cache: Optional[CacheConfig] = None,
        middleware: Optional[List[Middleware]] = None,
        **kwargs
    ):
        self.config = ClientConfig(
            base_url=base_url,
            headers=headers or {},
            **kwargs
        )
        self.middleware = middleware or []
        if timeout is not None:
             if isinstance(timeout, (int, float)):
                  self.config.timeout = TimeoutConfig(connect=timeout, read=timeout, write=timeout, pool=timeout)
             else:
                  self.config.timeout = timeout

        if retry is not None:
            self.config.retry = retry

        if circuit_breaker is not None:
            self.config.circuit_breaker = circuit_breaker

        if rate_limit is not None:
            self.config.rate_limit = rate_limit

        if cache is not None:
            self.config.cache = cache

        self._client = httpx.AsyncClient(
            base_url=self.config.base_url,
            headers=self.config.headers,
            timeout=self._build_httpx_timeout(self.config.timeout),
            auth=auth,
            verify=self.config.verify_ssl,
            http2=self.config.http2,
            follow_redirects=self.config.follow_redirects,
            max_redirects=self.config.max_redirects,
        )
        self.circuit_breaker = AsyncCircuitBreaker(self.config.circuit_breaker)
        self._retry_strategy = create_async_retry_strategy(self.config.retry)
        self.rate_limiter = RateLimiter(self.config.rate_limit)
        self.cache = CacheManager(self.config.cache)

    def _build_httpx_timeout(self, timeout_config: Union[float, TimeoutConfig]) -> httpx.Timeout:
        if isinstance(timeout_config, (int, float)):
             return httpx.Timeout(timeout_config)
        return httpx.Timeout(
            connect=timeout_config.connect,
            read=timeout_config.read,
            write=timeout_config.write,
            pool=timeout_config.pool
        )

    async def request(self, method: str, url: str, **kwargs) -> httpx.Response:
        # 1. Check Rate Limit
        if not self.rate_limiter.acquire():
             raise RateLimitError("Client-side rate limit exceeded")

        # 2. Check Cache
        cache_key = self.cache.generate_key(method, url, kwargs.get("params"))
        if method.upper() in ["GET", "HEAD"]:
            cached_response = self.cache.get(cache_key)
            if cached_response:
                return cached_response

        # Core request logic (with Retry & Circuit Breaker)
        async def _core_request(req_obj: httpx.Request) -> httpx.Response:
            async def _request_attempt():
                if not self.circuit_breaker.allow_request():
                    raise CircuitBreakerOpenError("Circuit breaker is open")

                try:
                    response = await self._client.send(req_obj)
                    response.raise_for_status()
                    self.circuit_breaker.record_success()

                    # Cache successful response
                    if method.upper() in ["GET", "HEAD"] and response.status_code in self.config.cache.cacheable_status_codes:
                        self.cache.set(cache_key, response)

                    return response
                except httpx.HTTPStatusError as e:
                    # Check if this status code should trip the circuit breaker
                    if e.response.status_code in self.config.circuit_breaker.included_status_codes:
                        self.circuit_breaker.record_failure(e)
                    else:
                        self.circuit_breaker.record_success()

                    self._handle_http_error(e)
                except (httpx.ConnectTimeout, httpx.ReadTimeout, httpx.WriteTimeout, httpx.TimeoutException) as e:
                    self.circuit_breaker.record_failure(e)
                    if isinstance(e, httpx.ConnectTimeout):
                        raise ConnectTimeoutError(str(e)) from e
                    elif isinstance(e, httpx.ReadTimeout):
                        raise ReadTimeoutError(str(e)) from e
                    elif isinstance(e, httpx.WriteTimeout):
                        raise WriteTimeoutError(str(e)) from e
                    else:
                        raise TimeoutError(str(e)) from e
                except httpx.NetworkError as e:
                    self.circuit_breaker.record_failure(e)
                    raise ConnectionError(str(e)) from e
                except Exception as e:
                    if isinstance(e, HTTPError):
                        raise e
                    self.circuit_breaker.record_failure(e)
                    raise

            return await self._retry_strategy(_request_attempt)

        # Build request object
        request = self._client.build_request(method, url, **kwargs)

        # Apply middleware
        async def call_next(req: httpx.Request, index: int = 0) -> httpx.Response:
            if index < len(self.middleware):
                middleware = self.middleware[index]
                return await middleware(req, lambda r: call_next(r, index + 1))
            else:
                return await _core_request(req)

        return await call_next(request)

    def paginate(
        self,
        url: str,
        strategy: Optional[PaginationStrategy] = None,
        **kwargs
    ) -> AsyncPaginator:
        if strategy is None:
            strategy = OffsetLimitPagination() # Default
        return AsyncPaginator(self, url, strategy, **kwargs)

    def _handle_http_error(self, e: httpx.HTTPStatusError):
        status_code = e.response.status_code
        message = str(e)
        response = e.response

        if status_code == 401:
            raise AuthenticationError(message, response)
        elif status_code == 403:
            raise ForbiddenError(message, response)
        elif status_code == 404:
            raise NotFoundError(message, response)
        elif status_code == 429:
             retry_after = response.headers.get("Retry-After")
             retry_after_seconds = None
             if retry_after:
                 try:
                     retry_after_seconds = float(retry_after)
                 except ValueError:
                     pass # Handle date format later
             raise RateLimitError(message, response, retry_after=retry_after_seconds)
        elif 400 <= status_code < 500:
            raise ClientResponseError(message, response)
        elif 500 <= status_code < 600:
            raise ServerError(message, response)
        else:
            raise HTTPError(message, response)

    async def get(self, url: str, **kwargs) -> httpx.Response:
        return await self.request("GET", url, **kwargs)

    async def post(self, url: str, **kwargs) -> httpx.Response:
        return await self.request("POST", url, **kwargs)

    async def put(self, url: str, **kwargs) -> httpx.Response:
        return await self.request("PUT", url, **kwargs)

    async def patch(self, url: str, **kwargs) -> httpx.Response:
        return await self.request("PATCH", url, **kwargs)

    async def delete(self, url: str, **kwargs) -> httpx.Response:
        return await self.request("DELETE", url, **kwargs)

    async def head(self, url: str, **kwargs) -> httpx.Response:
        return await self.request("HEAD", url, **kwargs)

    async def options(self, url: str, **kwargs) -> httpx.Response:
        return await self.request("OPTIONS", url, **kwargs)

    async def close(self):
        await self._client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        await self.close()
