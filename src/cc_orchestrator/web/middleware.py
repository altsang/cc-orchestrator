"""
Middleware for FastAPI application.

This module provides custom middleware for logging, rate limiting,
request tracking, and other cross-cutting concerns.
"""

import time
import uuid
from collections import defaultdict
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from .logging_utils import log_api_request, log_api_response


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Add unique request ID to each request for tracking."""

    async def dispatch(
        self, request: Request, call_next: Callable[..., Any]
    ) -> Response:
        """Add request ID header and make it available in request state."""
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id

        return response


class LoggingMiddleware(BaseHTTPMiddleware):
    """Log API requests and responses with timing information."""

    async def dispatch(
        self, request: Request, call_next: Callable[..., Any]
    ) -> Response:
        """Log request details and response timing."""
        start_time = time.time()

        # Extract request information
        client_ip = self._get_client_ip(request)
        user_agent = request.headers.get("user-agent")
        request_id = getattr(request.state, "request_id", None)

        # Log incoming request
        log_api_request(
            method=request.method,
            path=str(request.url.path),
            client_ip=client_ip,
            user_agent=user_agent,
            request_id=request_id,
        )

        # Process request
        response = await call_next(request)

        # Calculate response time
        end_time = time.time()
        response_time_ms = (end_time - start_time) * 1000

        # Log response
        log_api_response(
            method=request.method,
            path=str(request.url.path),
            status_code=response.status_code,
            response_time_ms=response_time_ms,
            request_id=request_id,
        )

        return response

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request headers."""
        # Check for forwarded headers (load balancer/proxy)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            # Take the first IP in the chain
            return forwarded_for.split(",")[0].strip()

        forwarded = request.headers.get("x-forwarded")
        if forwarded:
            return forwarded.split(",")[0].strip()

        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip

        # Fall back to direct client IP
        return request.client.host if request.client else "unknown"


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple rate limiting middleware based on client IP."""

    def __init__(self, app: Any, requests_per_minute: int = 60):
        """Initialize rate limiter with requests per minute limit."""
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.client_requests: dict[str, list[datetime]] = defaultdict(list)

    async def dispatch(
        self, request: Request, call_next: Callable[..., Any]
    ) -> Response:
        """Check rate limit and process request if allowed."""
        client_ip = self._get_client_ip(request)

        # Clean old requests (older than 1 minute)
        now = datetime.now()
        cutoff = now - timedelta(minutes=1)
        self.client_requests[client_ip] = [
            req_time
            for req_time in self.client_requests[client_ip]
            if req_time > cutoff
        ]

        # Check if rate limit exceeded
        if len(self.client_requests[client_ip]) >= self.requests_per_minute:
            return Response(
                content='{"error": "Rate limit exceeded", "message": "Too many requests"}',
                status_code=429,
                media_type="application/json",
                headers={"Retry-After": "60"},
            )

        # Record this request
        self.client_requests[client_ip].append(now)

        # Process request
        response = await call_next(request)

        # Add rate limit headers
        remaining = max(
            0, self.requests_per_minute - len(self.client_requests[client_ip])
        )
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(
            int((now + timedelta(minutes=1)).timestamp())
        )

        return response

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request headers."""
        # Check for forwarded headers (load balancer/proxy)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip

        # Fall back to direct client IP
        return request.client.host if request.client else "unknown"


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""

    async def dispatch(
        self, request: Request, call_next: Callable[..., Any]
    ) -> Response:
        """Add security headers to response."""
        response = await call_next(request)

        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "camera=(), microphone=(), geolocation=()"
        )

        # HSTS header for HTTPS (only add in production)
        # response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        return response
