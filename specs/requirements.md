# Python REST Client API - Requirements Specification

## 1. Overview

This document defines the requirements for a Python client library that interfaces with REST API endpoints. The client should provide a clean, Pythonic interface for consuming HTTP-based services with support for both synchronous and asynchronous operations.

This specification serves as the authoritative guideline for both human software engineers and AI coding agents implementing the library.

---

## 2. Technology Stack

| Component               | Tool                | Purpose                                                                                   |
| :---------------------- | :------------------ | :---------------------------------------------------------------------------------------- |
| **HTTP Client**         | `httpx`             | Native async support, HTTP/2, strictly typed, and broadly compatible with `requests` API |
| **Validation**          | `pydantic`          | Runtime data validation, automatic error parsing, and strict schema enforcement          |
| **Configuration**       | `pydantic-settings` | Type-safe configuration management (environment variables, `.env` files)                 |
| **Retries**             | `tenacity`          | Decorator-based retry logic with composable stop/wait conditions                         |
| **Testing**             | `respx`             | Specifically designed to mock `httpx` requests; superior to standard `unittest.mock`     |
| **Package Manager**     | `uv`                | Fast Python package installer and resolver                                               |
| **Formatter & Linter**  | `ruff`              | Extremely fast Python linter and formatter written in Rust                               |

---

## 3. Core HTTP Operations

### 3.1 Supported HTTP Methods

The client must support all standard HTTP methods:

- **GET**: Retrieve resources
- **POST**: Create new resources
- **PUT**: Replace existing resources
- **PATCH**: Partially update resources
- **DELETE**: Remove resources
- **HEAD**: Retrieve metadata without response body
- **OPTIONS**: Query supported methods (optional for MVP)

### 3.2 Request Construction

The client must provide intuitive methods for:

- Setting request headers (both default and per-request)
- Adding query parameters with automatic URL encoding
- Sending request bodies in multiple formats (JSON, form data, raw bytes)
- Setting custom User-Agent strings
- Configuring request timeouts per call

### 3.3 Response Handling

The client must:

- Automatically deserialize JSON responses to Python dictionaries or Pydantic models
- Provide access to raw response content when needed
- Expose response status codes, headers, and metadata
- Support response streaming for large payloads
- Detect and handle character encoding appropriately

### 3.4 Protocol Support

The client must support multiple HTTP protocol versions:

- HTTP/1.1 support (default)
- HTTP/2 support (opt-in via configuration, requires `h2` optional dependency)
- Automatic protocol negotiation when HTTP/2 is enabled
- Graceful fallback to HTTP/1.1 when HTTP/2 is unavailable or unsupported by server

### 3.5 Redirect Handling

The client must provide configurable redirect behavior:

- Automatic redirect following (enabled by default)
- Configurable maximum redirect limit (default: 20)
- Option to disable cross-origin redirects
- Access to redirect history in response object
- Configurable redirect behavior per HTTP method (e.g., whether POST follows redirects)
- Option to disable redirects entirely per-request or globally

---

## 4. Synchronous and Asynchronous Support

### 4.1 Dual Interface Requirement

The client must provide both synchronous and asynchronous versions of all operations to accommodate different use cases:

- Synchronous interface for scripts, simple applications, and REPL usage
- Asynchronous interface for high-concurrency applications using asyncio

### 4.2 Implementation Approach

- Use httpx as the underlying HTTP library (supports both sync and async natively)
- Provide separate client classes: `Client` (sync) and `AsyncClient` (async)
- All async methods must use async/await syntax
- Minimum supported Python version: 3.10 (see Section 18.2)

### 4.3 Context Manager Support

Both synchronous and asynchronous clients must support context manager protocols for proper resource management:

```python
# Synchronous
with Client(base_url="https://api.example.com") as client:
    response = client.get("/endpoint")

# Asynchronous
async with AsyncClient(base_url="https://api.example.com") as client:
    response = await client.get("/endpoint")
```

---

## 5. Streaming Capabilities

### 5.1 Response Streaming

The client must support streaming responses for:

- Large file downloads
- Server-sent events (SSE)
- Chunked transfer encoding
- Line-by-line processing of text responses

### 5.2 Streaming Interface

- Provide iterator/async iterator interface for consuming streamed data
- Support for reading responses in configurable chunk sizes
- Ability to process streams without loading entire response into memory
- Optional progress callbacks for monitoring download progress

### 5.3 Request Streaming

Support for streaming request bodies:

- File uploads without loading entire file into memory
- Generator-based request body streaming
- Multipart streaming for large file uploads

---

## 6. Authentication and Security

### 6.1 Authentication Methods

The client must support multiple authentication schemes:

- **API Key authentication**: Header-based or query parameter
- **Bearer token authentication**: OAuth2, JWT
- **Basic authentication**: Username/password
- **Custom authentication**: Pluggable authentication handlers via callable or class interface

### 6.2 Credential Management

- Accept credentials via client initialization parameters
- Support environment variable-based credential loading (via pydantic-settings)
- Allow per-request credential override
- Secure handling of sensitive data (no logging of credentials by default)
- Support for credential refresh callbacks (for expiring tokens)

### 6.3 SSL/TLS Configuration

- SSL certificate verification enabled by default
- Option to disable verification (with explicit warning logged)
- Support for custom CA bundles
- Client certificate authentication support (mTLS)
- Configurable minimum TLS version

### 6.4 Proxy Configuration

The client must support proxy configurations for enterprise environments:

- HTTP and HTTPS proxy support
- SOCKS proxy support (optional, via `httpx-socks` dependency)
- Environment variable proxy detection (`HTTP_PROXY`, `HTTPS_PROXY`, `NO_PROXY`)
- Per-request proxy override capability
- Proxy authentication support (Basic, Digest)
- Option to bypass proxy for specific hosts

---

## 7. Error Handling and Resilience

### 7.1 Exception Hierarchy

Define custom exceptions for different failure scenarios:

```
ClientError (base)
├── HTTPError
│   ├── ClientResponseError (4xx)
│   │   ├── AuthenticationError (401)
│   │   ├── ForbiddenError (403)
│   │   ├── NotFoundError (404)
│   │   └── RateLimitError (429)
│   └── ServerError (5xx)
├── ConnectionError
├── TimeoutError
│   ├── ConnectTimeoutError
│   ├── ReadTimeoutError
│   └── WriteTimeoutError
├── ValidationError
└── ConfigurationError
```

### 7.2 HTTP Error Handling

- Raise appropriate exceptions for HTTP error status codes by default
- Option to disable automatic exception raising globally or for specific status codes
- Include response details (status, headers, body) in exception objects
- Provide helper methods to check response success without exceptions
- Support for custom error response parsing (e.g., API-specific error formats)

### 7.3 Retry Logic

Implement configurable retry mechanism using tenacity:

- Automatic retry for transient failures (network errors, 5xx responses)
- Exponential backoff with configurable jitter
- Configurable maximum retry attempts (default: 3)
- Configurable retry status codes (default: 408, 429, 500, 502, 503, 504)
- Respect `Retry-After` headers when present
- Option to disable retries entirely
- Per-request retry override

#### Idempotency Considerations

- By default, only retry idempotent methods (GET, HEAD, OPTIONS, PUT, DELETE)
- POST and PATCH retry only when explicitly configured or when `Idempotency-Key` header is present
- Support for automatic `Idempotency-Key` header generation (opt-in)
- Clear documentation of retry safety expectations

### 7.4 Timeout Configuration

Support multiple timeout types with granular control:

- **Connection timeout**: Maximum time to establish connection (default: 5s)
- **Read timeout**: Maximum time between receiving bytes (default: 30s)
- **Write timeout**: Maximum time between sending bytes (default: 30s)
- **Pool timeout**: Maximum time waiting for connection from pool (default: 10s)
- **Total timeout**: Overall request deadline (default: None)
- Configurable defaults with per-request override
- Support for `httpx.Timeout` object for granular control

### 7.5 Circuit Breaker (Future Enhancement)

Consider implementing circuit breaker pattern for:

- Preventing cascading failures
- Automatic recovery testing
- Configurable failure thresholds
- Half-open state for gradual recovery

---

## 8. Configuration and Initialization

### 8.1 Client Initialization

The client constructor must accept:

- **base_url** (required): Root URL for all API requests
- **headers**: Default headers applied to all requests
- **timeout**: Default timeout configuration
- **auth**: Authentication configuration
- **retry**: Retry behavior configuration
- **verify_ssl**: Certificate verification settings
- **http2**: Enable HTTP/2 support (default: False)
- **follow_redirects**: Redirect following behavior (default: True)
- **max_redirects**: Maximum redirect count (default: 20)
- **proxy**: Proxy configuration
- **event_hooks**: Request/response event hooks

### 8.2 Configuration Precedence

Configuration follows this precedence (highest to lowest):

1. Per-request parameters
2. Client instance configuration
3. Environment variables (via pydantic-settings)
4. Library defaults

### 8.3 Immutability

Client instances should be effectively immutable after initialization:

- Configuration cannot be modified after client creation
- Create new client instances for different configurations
- This ensures thread safety and predictable behavior

### 8.4 Event Hooks

The client should support event hooks for common extension points:

- **request**: Called before sending each request, receives mutable request object
- **response**: Called after receiving each response, receives response object

Hooks enable cross-cutting concerns without modifying core logic:

- Request/response logging
- Metrics collection
- Header injection (correlation IDs, trace context)
- Response transformation

```python
def log_request(request):
    logger.info(f"Request: {request.method} {request.url}")

def log_response(response):
    logger.info(f"Response: {response.status_code}")

client = Client(
    base_url="https://api.example.com",
    event_hooks={"request": [log_request], "response": [log_response]}
)
```

---

## 9. Connection Management

### 9.1 Connection Pooling

Leverage httpx connection pooling:

- Reuse connections across requests
- Configurable pool size limits (max_connections, max_keepalive_connections)
- Automatic connection cleanup on client close
- Keepalive timeout configuration

### 9.2 Session Persistence

- Maintain session state across requests (cookies, connection pools)
- Automatic resource cleanup via context managers
- Explicit `close()` method for manual resource management
- Warning when client is garbage collected without being closed

---

## 10. Data Serialization and Validation

### 10.1 Request Serialization

- Automatic JSON serialization for Python objects using standard library json
- Optional high-performance serialization with orjson (when installed)
- Support for custom serializers
- Form-encoded data for POST/PUT requests (`application/x-www-form-urlencoded`)
- Multipart form data for file uploads (`multipart/form-data`)
- Automatic Content-Type header setting based on body type

### 10.2 Response Deserialization

- Automatic JSON deserialization based on Content-Type header
- Graceful handling of non-JSON responses
- Content-type detection and appropriate parsing
- Character encoding detection with UTF-8 fallback

### 10.3 Schema Validation

Integration with Pydantic for request/response models:

- Generic client methods accepting Pydantic model types for response parsing
- Automatic request body serialization from Pydantic models
- Validation error exceptions with detailed field-level errors
- Support for both strict and lax validation modes
- Optional response validation (disabled by default for performance)

```python
from pydantic import BaseModel

class User(BaseModel):
    id: int
    name: str
    email: str

# Response automatically validated and parsed
user = client.get("/users/123", response_model=User)
print(user.name)  # Fully typed, IDE autocomplete works

# Request body from model
new_user = User(id=0, name="Jane", email="jane@example.com")
client.post("/users", json=new_user)
```

### 10.4 Response Parsing Resilience

The client must handle malformed responses gracefully:

- Clear error messages for invalid JSON with context
- Content-Length mismatch detection and warning
- Truncated response detection
- Character encoding detection with fallback chain (UTF-8 default)
- Configurable maximum response size limits to prevent memory exhaustion (default: 100MB)
- Partial response recovery where possible

---

## 11. Developer Experience

### 11.1 Type Hints

- Complete type annotations for all public APIs
- Support for type checkers (mypy, pyright, pyrefly)
- Generic types for flexibility with Pydantic models
- Typed dictionaries for complex parameter objects
- `py.typed` marker file for PEP 561 compliance

### 11.2 Logging

- Integration with Python's standard logging module
- Optional structured logging support (JSON format) via configuration
- Log levels for different events:
  - **DEBUG**: Full request/response details (headers, body samples)
  - **INFO**: Request method, URL, and response status
  - **WARNING**: Retries, slow responses, deprecation notices
  - **ERROR**: Fatal errors, connection failures
- Configurable log redaction for sensitive data:
  - Authorization headers (redacted by default)
  - API keys in query parameters
  - Configurable sensitive field patterns via regex
- Request/response body logging (opt-in, with configurable size limits)
- Correlation ID inclusion in all log messages when available

### 11.3 Observability

- Automatic request ID generation (configurable format: UUID4, ULID)
- Propagation of trace context headers (`traceparent`, `tracestate`, `X-Request-ID`)
- OpenTelemetry-compatible instrumentation hooks (optional dependency)
- Structured logging support with correlation IDs
- Request duration metrics exposure via hooks
- Support for custom metrics collectors

### 11.4 API Design Principles

- Intuitive, Pythonic interface following established conventions
- Consistent naming conventions aligned with httpx where applicable
- Sensible defaults requiring minimal configuration for common use cases
- Progressive disclosure: simple things simple, complex things possible
- Method chaining where appropriate
- Clear separation between configuration and runtime behavior

### 11.5 Documentation

- Comprehensive docstrings for all public APIs following Google style
- Type hints integrated with documentation
- Code examples in docstrings
- Sphinx-compatible documentation with autodoc support
- Dedicated documentation site with tutorials and guides
- Migration guide from requests library

---

## 12. Testing and Quality

### 12.1 Testability

- Design for easy mocking and testing
- Provide test utilities for common scenarios (mock server, fixtures)
- Support for request/response recording and playback
- Integration with respx for httpx mocking
- Example test patterns in documentation

### 12.2 Code Quality

- PEP 8 compliance enforced via ruff
- Type checking with mypy (strict mode)
- Linting and formatting with ruff
- Minimum code coverage target: 90%
- All public APIs must have tests
- Integration tests against real HTTP servers

---

## 13. Advanced Features

### 13.1 Rate Limiting (Future Enhancement)

Client-side rate limiting:

- Respect server rate limits automatically via response headers
- Configurable client-side rate limit strategies (token bucket, sliding window)
- Queue requests when rate limited
- Per-endpoint rate limit configuration
- Rate limit status exposure for monitoring

### 13.2 Response Caching (Future Enhancement)

HTTP-compliant caching:

- Cache responses based on Cache-Control headers
- Configurable cache backends (memory, disk, Redis)
- Cache invalidation support
- Conditional requests (If-None-Match, If-Modified-Since)
- Cache statistics exposure

### 13.3 Middleware System (Future Enhancement)

Extensibility architecture:

- Request preprocessing pipeline
- Response postprocessing pipeline
- Custom authentication handlers
- Logging and monitoring integrations
- Composable middleware stack

### 13.4 API Versioning

Support for API version negotiation:

- Version specification via headers (`Accept-Version`, custom headers)
- Version specification via URL path prefix
- Multiple API version support in single client instance
- Version-specific behavior configuration

### 13.5 Pagination Support (Future Enhancement)

Built-in pagination helpers:

- Iterator interface for paginated endpoints (sync and async)
- Support for common pagination patterns:
  - Offset/limit pagination
  - Cursor-based pagination
  - Link header pagination (RFC 5988)
  - Page number pagination
- Configurable page size
- Automatic next-page fetching with async generator support
- Early termination support
- Total count extraction where available

---

## 14. Performance Requirements

### 14.1 Efficiency

- Minimal memory overhead for normal operations
- Efficient streaming without buffering large responses
- Connection reuse to minimize latency
- Optional high-performance JSON with orjson
- Lazy evaluation where appropriate

### 14.2 Scalability

- Support for high-concurrency async operations (thousands of concurrent requests)
- No global state that prevents concurrent usage
- Thread-safe synchronous client
- Efficient connection pool management under load

### 14.3 Thread and Concurrency Safety

- Synchronous client instances are thread-safe for concurrent use from multiple threads
- Asynchronous client instances are safe for concurrent coroutine use within a single event loop
- Client configuration is immutable after initialization
- No global mutable state in the library
- Document any operations requiring external synchronization
- Connection pools are shared safely across threads/coroutines

---

## 15. Dependencies

### 15.1 Core Dependencies

Required for basic functionality:

- **httpx** (>=0.27.0): HTTP client library
- **pydantic** (>=2.0): Data validation and serialization
- **pydantic-settings** (>=2.0): Configuration management
- **tenacity** (>=8.0): Retry logic

### 15.2 Optional Dependencies

Enhanced functionality via extras:

- **orjson**: Faster JSON serialization/deserialization (2-10x speedup)
- **httpx-socks**: SOCKS proxy support
- **h2**: HTTP/2 support (required when HTTP/2 is enabled)
- **opentelemetry-api** + **opentelemetry-instrumentation-httpx**: Distributed tracing

### 15.3 Dependency Installation

Optional dependencies installable via extras:

```bash
pip install mypackage              # Core only
pip install mypackage[fast]        # Includes orjson
pip install mypackage[http2]       # Includes h2
pip install mypackage[socks]       # Includes httpx-socks
pip install mypackage[tracing]     # Includes opentelemetry packages
pip install mypackage[all]         # All optional dependencies
```

### 15.4 Dependency Management

- Minimal dependency footprint for core functionality
- No unnecessary transitive dependencies
- Pin minimum versions, allow flexibility for patches
- Clear documentation of optional dependencies and their purposes
- Regular dependency updates and security audits

---

## 16. Package Distribution

### 16.1 Packaging

- Distribute via PyPI
- Support for pip and uv installation
- Semantic versioning (SemVer 2.0)
- Changelog maintenance (Keep a Changelog format)
- Source distribution and wheel packages
- Signed releases (optional)

### 16.2 Python Version Support

- Minimum Python version: 3.10
- Test against Python versions: 3.10, 3.11, 3.12, 3.13
- Document end-of-life policy aligned with Python release cycle
- Provide clear upgrade guidance when dropping version support

---

## 17. MVP vs Future Enhancements

### 17.1 Minimum Viable Product (MVP)

Essential features for initial release:

- Core HTTP methods (GET, POST, PUT, PATCH, DELETE, HEAD)
- Synchronous and asynchronous clients
- Basic authentication (API key, bearer token, basic auth)
- JSON serialization/deserialization
- Pydantic model support for responses
- Error handling with custom exception hierarchy
- Retry logic with exponential backoff and jitter
- Timeout configuration (all timeout types)
- Response streaming
- Request streaming for file uploads
- Context manager support
- Event hooks (request/response)
- Redirect handling
- Proxy support (HTTP/HTTPS)
- Complete type hints
- Structured logging with redaction
- Request ID generation and propagation
- Comprehensive documentation
- Test utilities for consumers

### 17.2 Post-MVP Enhancements

Features for future releases:

- Circuit breaker pattern
- Response caching
- Client-side rate limiting
- Full middleware/plugin system
- Advanced authentication (OAuth2 flows with refresh)
- Request/response recording for testing
- Metrics and monitoring hooks
- Pagination helpers
- SOCKS proxy support
- OpenTelemetry integration
- GraphQL support (optional module)

---

## 18. Example Usage

### 18.1 Simple Synchronous Usage

```python
from mypackage import Client

client = Client(
    base_url="https://api.example.com",
    auth=("api_key", "your-api-key"),
    timeout=30.0
)

# GET request
response = client.get("/users/123")
user = response.json()

# POST request with JSON body
new_user = client.post("/users", json={"name": "John Doe", "email": "john@example.com"})

# Always close the client when done (or use context manager)
client.close()
```

### 18.2 Asynchronous Usage

```python
from mypackage import AsyncClient

async def main():
    async with AsyncClient(base_url="https://api.example.com") as client:
        # Concurrent requests
        users, posts = await asyncio.gather(
            client.get("/users"),
            client.get("/posts")
        )
        
        user_data = users.json()
        post_data = posts.json()
```

### 18.3 Streaming Usage

```python
# Download large file with progress
with client.stream("GET", "/large-file.zip") as response:
    total = int(response.headers.get("content-length", 0))
    downloaded = 0
    
    with open("large-file.zip", "wb") as f:
        for chunk in response.iter_bytes(chunk_size=8192):
            f.write(chunk)
            downloaded += len(chunk)
            print(f"Progress: {downloaded}/{total} bytes")
```

### 18.4 Error Handling

```python
from mypackage import Client, HTTPError, RateLimitError, TimeoutError

client = Client(base_url="https://api.example.com", auth=("bearer", "token"))

try:
    response = client.get("/users/123")
    user = response.json()
except RateLimitError as e:
    retry_after = e.retry_after  # Extracted from Retry-After header
    logger.warning(f"Rate limited, retry after {retry_after}s")
except TimeoutError as e:
    logger.error(f"Request timed out: {e}")
except HTTPError as e:
    logger.error(f"Request failed: {e.status_code} - {e.response.text}")
finally:
    client.close()
```

### 18.5 Pydantic Model Integration

```python
from pydantic import BaseModel, EmailStr
from mypackage import AsyncClient

class User(BaseModel):
    id: int
    name: str
    email: EmailStr

class CreateUserRequest(BaseModel):
    name: str
    email: EmailStr

async with AsyncClient(base_url="https://api.example.com") as client:
    # Response automatically validated and parsed to User model
    user = await client.get("/users/123", response_model=User)
    print(user.name)  # Fully typed, IDE autocomplete works
    
    # Request body from Pydantic model
    new_user_request = CreateUserRequest(name="Jane", email="jane@example.com")
    created_user = await client.post(
        "/users", 
        json=new_user_request,
        response_model=User
    )
```

### 18.6 Custom Configuration

```python
from mypackage import Client, RetryConfig, TimeoutConfig

client = Client(
    base_url="https://api.example.com",
    auth=("bearer", "your-token"),
    timeout=TimeoutConfig(
        connect=5.0,
        read=30.0,
        write=30.0,
        pool=10.0
    ),
    retry=RetryConfig(
        max_attempts=5,
        retry_statuses=[429, 500, 502, 503, 504],
        backoff_factor=0.5,
        backoff_max=60.0
    ),
    headers={"X-Custom-Header": "value"},
    http2=True,
    follow_redirects=True,
    max_redirects=10
)
```

### 18.7 Event Hooks for Observability

```python
import logging
import uuid

logger = logging.getLogger(__name__)

def add_correlation_id(request):
    """Add correlation ID to all requests."""
    if "X-Correlation-ID" not in request.headers:
        request.headers["X-Correlation-ID"] = str(uuid.uuid4())

def log_request(request):
    """Log outgoing requests."""
    logger.info(
        "HTTP Request",
        extra={
            "method": request.method,
            "url": str(request.url),
            "correlation_id": request.headers.get("X-Correlation-ID")
        }
    )

def log_response(response):
    """Log incoming responses."""
    logger.info(
        "HTTP Response",
        extra={
            "status_code": response.status_code,
            "url": str(response.url),
            "duration_ms": response.elapsed.total_seconds() * 1000,
            "correlation_id": response.request.headers.get("X-Correlation-ID")
        }
    )

client = Client(
    base_url="https://api.example.com",
    event_hooks={
        "request": [add_correlation_id, log_request],
        "response": [log_response]
    }
)
```

---

## 19. Success Criteria

The client library will be considered successful when it:

1. **Provides a clean, intuitive API** that reduces boilerplate compared to raw httpx usage
2. **Handles common failure scenarios gracefully** with informative error messages
3. **Performs efficiently** under normal and high-load conditions with minimal overhead
4. **Is well-documented** with clear examples, tutorials, and API reference
5. **Achieves high test coverage** (>90%) with comprehensive unit and integration tests
6. **Receives positive feedback** from early adopters and internal teams
7. **Integrates seamlessly** with existing Python tooling (type checkers, linters, IDEs)
8. **Maintains backward compatibility** following semantic versioning principles

---
## Appendix A: Glossary

- **Circuit Breaker**: Pattern that prevents cascading failures by stopping requests to failing services
- **Idempotent**: Operation that produces the same result regardless of how many times it's executed
- **mTLS**: Mutual TLS, where both client and server authenticate each other
- **SSE**: Server-Sent Events, a standard for servers to push updates to clients
- **ULID**: Universally Unique Lexicographically Sortable Identifier

## Appendix B: References

- [httpx Documentation](https://www.python-httpx.org/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [Tenacity Documentation](https://tenacity.readthedocs.io/)
- [HTTP/2 Specification (RFC 7540)](https://datatracker.ietf.org/doc/html/rfc7540)
- [OpenTelemetry Python](https://opentelemetry.io/docs/instrumentation/python/)
