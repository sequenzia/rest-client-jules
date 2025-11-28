# ... existing imports
from rest_client import RateLimitConfig, RateLimitError
from rest_client.middleware import Middleware, SyncMiddleware
import pytest
import respx
import httpx
from rest_client import Client, AsyncClient

# ... existing tests

@respx.mock
def test_rate_limiting():
    # Mocking rate limiter behavior is tricky without time.sleep, but we can test logic
    # The TokenBucket starts full.
    client = Client(
        base_url="https://api.example.com",
        rate_limit=RateLimitConfig(strategy="token_bucket", max_requests=1, time_window=60)
    )
    respx.get("https://api.example.com/test").mock(return_value=httpx.Response(200))

    # 1st request should succeed
    client.get("/test")

    # 2nd request should fail immediately
    with pytest.raises(RateLimitError, match="Client-side rate limit exceeded"):
        client.get("/test")

@respx.mock
def test_sync_middleware():
    class TestMiddleware(SyncMiddleware):
        def __call__(self, request, call_next):
            request.headers["X-Test"] = "true"
            response = call_next(request)
            response.headers["X-Response-Test"] = "true"
            return response

    client = Client(
        base_url="https://api.example.com",
        middleware=[TestMiddleware()]
    )

    respx.get("https://api.example.com/test").mock(return_value=httpx.Response(200))

    response = client.get("/test")

    assert respx.calls.last.request.headers["X-Test"] == "true"
    assert response.headers["X-Response-Test"] == "true"

@pytest.mark.asyncio
@respx.mock
async def test_async_middleware():
    class TestAsyncMiddleware(Middleware):
        async def __call__(self, request, call_next):
            request.headers["X-Test"] = "true"
            response = await call_next(request)
            response.headers["X-Response-Test"] = "true"
            return response

    client = AsyncClient(
        base_url="https://api.example.com",
        middleware=[TestAsyncMiddleware()]
    )

    respx.get("https://api.example.com/test").mock(return_value=httpx.Response(200))

    response = await client.get("/test")

    assert respx.calls.last.request.headers["X-Test"] == "true"
    assert response.headers["X-Response-Test"] == "true"
