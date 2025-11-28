from typing import Callable, Awaitable
import httpx

Request = httpx.Request
Response = httpx.Response

class Middleware:
    """Base class for middleware."""
    async def __call__(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        raise NotImplementedError

class SyncMiddleware:
    def __call__(
        self,
        request: Request,
        call_next: Callable[[Request], Response]
    ) -> Response:
        raise NotImplementedError
