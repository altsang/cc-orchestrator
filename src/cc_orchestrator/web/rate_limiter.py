"""Rate limiting functionality for API endpoints."""

import time
from collections import defaultdict
from collections.abc import Callable
from typing import Any

from fastapi import Request

from .exceptions import RateLimitExceededError


class InMemoryRateLimiter:
    """Simple in-memory rate limiter implementation."""

    def __init__(self) -> None:
        # Store request counts per client IP
        # Format: {ip: {endpoint: [timestamp, ...]}}
        self.request_history: dict[str, dict[str, list[float]]] = defaultdict(
            lambda: defaultdict(list)
        )

    def check_rate_limit(
        self, client_ip: str, endpoint: str, limit: int, window_seconds: int
    ) -> None:
        """Check if request is within rate limit."""
        current_time = time.time()
        window_start = current_time - window_seconds

        # Clean old requests outside the window
        client_history = self.request_history[client_ip][endpoint]
        self.request_history[client_ip][endpoint] = [
            req for req in client_history if req > window_start
        ]

        # Count requests in current window
        current_requests = len(self.request_history[client_ip][endpoint])

        if current_requests >= limit:
            raise RateLimitExceededError(limit, f"{window_seconds}s")

        # Record this request
        self.request_history[client_ip][endpoint].append(current_time)

    def cleanup_old_entries(self, max_age_seconds: int = 3600) -> None:
        """Clean up old entries to prevent memory bloat."""
        cutoff_time = time.time() - max_age_seconds

        for client_ip in list(self.request_history.keys()):
            for endpoint in list(self.request_history[client_ip].keys()):
                self.request_history[client_ip][endpoint] = [
                    req
                    for req in self.request_history[client_ip][endpoint]
                    if req > cutoff_time
                ]

                # Remove empty endpoint entries
                if not self.request_history[client_ip][endpoint]:
                    del self.request_history[client_ip][endpoint]

            # Remove empty client entries
            if not self.request_history[client_ip]:
                del self.request_history[client_ip]


# Global rate limiter instance
rate_limiter = InMemoryRateLimiter()


def get_client_ip(request: Request) -> str:
    """Extract client IP from request."""
    # Check for forwarded headers (when behind proxy)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()

    forwarded = request.headers.get("X-Forwarded-Host")
    if forwarded:
        return forwarded

    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip

    # Fall back to direct client IP
    if request.client:
        return request.client.host

    return "unknown"


def rate_limit(
    requests_per_minute: int = 60,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator for rate limiting endpoints."""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        async def wrapper(
            request: Request | None = None, *args: Any, **kwargs: Any
        ) -> Any:
            if request:
                import os

                # Use test rate limit if set, otherwise use default
                effective_limit = int(
                    os.getenv("TEST_RATE_LIMIT_PER_MINUTE", str(requests_per_minute))
                )

                client_ip = get_client_ip(request)
                endpoint = f"{request.method}:{request.url.path}"

                rate_limiter.check_rate_limit(
                    client_ip=client_ip,
                    endpoint=endpoint,
                    limit=effective_limit,
                    window_seconds=60,
                )

            return await func(*args, **kwargs)

        return wrapper

    return decorator


def websocket_rate_limit(
    connections_per_ip: int = 5,
) -> tuple[Callable[[str], None], Callable[[str], None], Callable[[str], None]]:
    """Rate limiter for WebSocket connections."""
    connection_counts: dict[str, int] = defaultdict(int)

    def check_limit(client_ip: str) -> None:
        import os

        # Use higher limit for tests if set
        effective_limit = int(
            os.getenv("TEST_WEBSOCKET_CONNECTIONS_PER_IP", str(connections_per_ip))
        )

        if connection_counts[client_ip] >= effective_limit:
            raise RateLimitExceededError(effective_limit, "concurrent connections")

    def add_connection(client_ip: str) -> None:
        connection_counts[client_ip] += 1

    def remove_connection(client_ip: str) -> None:
        if connection_counts[client_ip] > 0:
            connection_counts[client_ip] -= 1
        if connection_counts[client_ip] == 0:
            del connection_counts[client_ip]

    return check_limit, add_connection, remove_connection


# WebSocket connection limiter
ws_check_limit, ws_add_connection, ws_remove_connection = websocket_rate_limit()


class RateLimiter:
    """Simple rate limiter class for general use."""

    def __init__(self, rate: int, window: int):
        """Initialize rate limiter.

        Args:
            rate: Maximum number of requests per window
            window: Time window in seconds
        """
        self.rate = rate
        self.window = window
        self._limiter = InMemoryRateLimiter()

    def check_limit(self, identifier: str, endpoint: str = "default") -> None:
        """Check if request is within rate limit.

        Args:
            identifier: Unique identifier (e.g. IP, user ID)
            endpoint: Endpoint identifier

        Raises:
            RateLimitExceededError: If rate limit exceeded
        """
        self._limiter.check_rate_limit(identifier, endpoint, self.rate, self.window)
