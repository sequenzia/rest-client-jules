import pytest
import respx
import httpx
from rest_client import Client, AsyncClient, NotFoundError, RetryConfig, CircuitBreakerOpenError

@pytest.fixture
def client():
    return Client(base_url="https://api.example.com")

@pytest.fixture
def async_client():
    return AsyncClient(base_url="https://api.example.com")

@respx.mock
def test_sync_client_get(client):
    respx.get("https://api.example.com/users/123").mock(return_value=httpx.Response(200, json={"id": 123, "name": "John"}))

    response = client.get("/users/123")
    assert response.status_code == 200
    assert response.json()["name"] == "John"

@pytest.mark.asyncio
@respx.mock
async def test_async_client_get(async_client):
    respx.get("https://api.example.com/users/123").mock(return_value=httpx.Response(200, json={"id": 123, "name": "John"}))

    response = await async_client.get("/users/123")
    assert response.status_code == 200
    assert response.json()["name"] == "John"

@respx.mock
def test_client_error_handling(client):
    respx.get("https://api.example.com/notfound").mock(return_value=httpx.Response(404))

    with pytest.raises(NotFoundError):
        client.get("/notfound")

@respx.mock
def test_retry_logic():
    # Fail 2 times then succeed
    route = respx.get("https://api.example.com/flaky").mock(
        side_effect=[
            httpx.Response(500),
            httpx.Response(500),
            httpx.Response(200, json={"status": "ok"})
        ]
    )

    client = Client(
        base_url="https://api.example.com",
        retry=RetryConfig(max_attempts=3, backoff_factor=0.1) # Fast retry for test
    )

    response = client.get("/flaky")
    assert response.status_code == 200
    assert route.call_count == 3

@respx.mock
def test_no_retry_404():
    # 404 should not retry by default
    route = respx.get("https://api.example.com/missing").mock(return_value=httpx.Response(404))

    client = Client(
        base_url="https://api.example.com",
        retry=RetryConfig(max_attempts=3)
    )

    with pytest.raises(NotFoundError):
        client.get("/missing")

    assert route.call_count == 1

@respx.mock
def test_circuit_breaker():
    # Fail enough times to open circuit
    route = respx.get("https://api.example.com/fail").mock(return_value=httpx.Response(500))

    client = Client(
        base_url="https://api.example.com",
        retry=RetryConfig(max_attempts=1), # No retry to trigger CB faster
    )
    # Default CB threshold is 5 failures

    # Trigger failures
    for _ in range(5):
        try:
            client.get("/fail")
        except Exception:
            pass

    assert client.circuit_breaker.state.value == "open"

    # Next call should raise CircuitBreakerOpenError immediately without network call
    with pytest.raises(CircuitBreakerOpenError):
        client.get("/fail")

    # Ensure network call count is still 5 (no 6th call made)
    assert route.call_count == 5
