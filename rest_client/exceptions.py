from typing import Any, Optional, List, Dict
import httpx

class ClientError(Exception):
    """Base exception for all client errors."""
    pass

class HTTPError(ClientError):
    """Exception for HTTP errors."""
    def __init__(self, message: str, response: Optional[httpx.Response] = None):
        super().__init__(message)
        self.response = response
        self.status_code = response.status_code if response else None

class ClientResponseError(HTTPError):
    """Exception for 4xx client errors."""
    pass

class AuthenticationError(ClientResponseError):
    """Exception for 401 Authentication errors."""
    pass

class ForbiddenError(ClientResponseError):
    """Exception for 403 Forbidden errors."""
    pass

class NotFoundError(ClientResponseError):
    """Exception for 404 Not Found errors."""
    pass

class RateLimitError(ClientResponseError):
    """Exception for 429 Rate Limit errors."""
    def __init__(self, message: str, response: Optional[httpx.Response] = None, retry_after: Optional[float] = None):
        super().__init__(message, response)
        self.retry_after = retry_after

class ServerError(HTTPError):
    """Exception for 5xx server errors."""
    pass

class ConnectionError(ClientError):
    """Exception for connection errors."""
    pass

class TimeoutError(ClientError):
    """Exception for timeout errors."""
    pass

class ConnectTimeoutError(TimeoutError):
    """Exception for connection timeouts."""
    pass

class ReadTimeoutError(TimeoutError):
    """Exception for read timeouts."""
    pass

class WriteTimeoutError(TimeoutError):
    """Exception for write timeouts."""
    pass

class CircuitBreakerError(ClientError):
    """Base exception for circuit breaker errors."""
    pass

class CircuitBreakerOpenError(CircuitBreakerError):
    """Exception raised when circuit breaker is open."""
    pass

class ValidationError(ClientError):
    """Exception for validation errors."""
    def __init__(self, message: str, errors: Optional[List[Dict[str, Any]]] = None):
        super().__init__(message)
        self.errors = errors

class ConfigurationError(ClientError):
    """Exception for configuration errors."""
    pass
