"""
Rate limiting middleware for API endpoints and WebSocket connections.

Implements token bucket algorithm with IP-based and user-based rate limiting.
"""

import asyncio
import time
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from ...utils.logging import LogContext, get_logger

logger = get_logger(__name__, LogContext.WEB)


@dataclass
class RateLimitRule:
    """Rate limiting rule configuration."""

    requests_per_minute: int
    burst_allowance: int = 0  # Additional requests allowed in burst
    block_duration_seconds: int = 60  # How long to block after limit exceeded


class TokenBucket:
    """Token bucket implementation for rate limiting."""

    def __init__(self, capacity: int, refill_rate: float):
        """
        Initialize token bucket.

        Args:
            capacity: Maximum number of tokens
            refill_rate: Tokens per second refill rate
        """
        self.capacity = capacity
        self.tokens = capacity
        self.refill_rate = refill_rate
        self.last_refill = time.time()
        self.blocked_until = 0.0

    def consume(self, tokens: int = 1) -> bool:
        """
        Try to consume tokens from bucket.

        Args:
            tokens: Number of tokens to consume

        Returns:
            True if tokens were consumed, False if rate limited
        """
        now = time.time()

        # Check if still blocked
        if now < self.blocked_until:
            return False

        # Refill tokens
        time_passed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + (time_passed * self.refill_rate))
        self.last_refill = now

        # Try to consume tokens
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        else:
            # Block for the configured duration
            self.blocked_until = now + 60  # 1 minute block
            logger.warning("Rate limit exceeded, blocking access", blocked_until=self.blocked_until)
            return False


class RateLimiter:
    """
    Rate limiter with multiple rules and backends.

    Features:
    - IP-based rate limiting
    - User-based rate limiting
    - WebSocket connection rate limiting
    - Different rules for different endpoint patterns
    """

    def __init__(self):
        # IP-based rate limiting
        self.ip_buckets: dict[str, TokenBucket] = defaultdict(
            lambda: TokenBucket(capacity=100, refill_rate=100/60)  # 100 requests per minute
        )

        # WebSocket connection rate limiting
        self.websocket_ip_buckets: dict[str, TokenBucket] = defaultdict(
            lambda: TokenBucket(capacity=5, refill_rate=5/60)  # 5 connections per minute
        )

        # API endpoint specific limits
        self.endpoint_rules = {
            "/api/v1/logs/search": RateLimitRule(requests_per_minute=20, burst_allowance=5),
            "/api/v1/logs/export": RateLimitRule(requests_per_minute=5, burst_allowance=2),
            "/api/v1/logs/stream/start": RateLimitRule(requests_per_minute=10, burst_allowance=3),
        }

        # Cleanup task
        self.cleanup_task: asyncio.Task[None] | None = None

    async def initialize(self) -> None:
        """Initialize the rate limiter."""
        self.cleanup_task = asyncio.create_task(self._cleanup_old_buckets())

    async def cleanup(self) -> None:
        """Cleanup rate limiter resources."""
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass

    def check_api_rate_limit(self, request: Request, client_ip: str) -> bool:
        """
        Check rate limit for API requests.

        Args:
            request: FastAPI request object
            client_ip: Client IP address

        Returns:
            True if request is allowed, False if rate limited
        """
        # Get the appropriate bucket for this IP
        bucket = self.ip_buckets[client_ip]

        # Check endpoint-specific limits
        path = request.url.path
        if path in self.endpoint_rules:
            rule = self.endpoint_rules[path]
            # Create or get specific bucket for this endpoint
            endpoint_key = f"{client_ip}:{path}"
            if endpoint_key not in self.ip_buckets:
                capacity = rule.requests_per_minute + rule.burst_allowance
                refill_rate = rule.requests_per_minute / 60
                self.ip_buckets[endpoint_key] = TokenBucket(capacity, refill_rate)

            return self.ip_buckets[endpoint_key].consume()

        # Use general rate limiting
        return bucket.consume()

    def check_websocket_rate_limit(self, client_ip: str) -> bool:
        """
        Check rate limit for WebSocket connections.

        Args:
            client_ip: Client IP address

        Returns:
            True if connection is allowed, False if rate limited
        """
        bucket = self.websocket_ip_buckets[client_ip]
        return bucket.consume()

    def get_rate_limit_info(self, client_ip: str, endpoint: str | None = None) -> dict[str, Any]:
        """
        Get current rate limit information.

        Args:
            client_ip: Client IP address
            endpoint: Optional specific endpoint

        Returns:
            Dict with rate limit information
        """
        key = f"{client_ip}:{endpoint}" if endpoint and endpoint in self.endpoint_rules else client_ip
        bucket = self.ip_buckets.get(key, self.ip_buckets[client_ip])

        return {
            "remaining_tokens": int(bucket.tokens),
            "capacity": bucket.capacity,
            "reset_time": bucket.last_refill + 60,  # Next minute boundary
            "blocked_until": bucket.blocked_until if bucket.blocked_until > time.time() else None,
        }

    async def _cleanup_old_buckets(self) -> None:
        """Cleanup old unused token buckets periodically."""
        while True:
            try:
                await asyncio.sleep(300)  # Cleanup every 5 minutes

                current_time = time.time()
                cutoff_time = current_time - 600  # Remove buckets unused for 10 minutes

                # Cleanup IP buckets
                old_keys = [
                    key for key, bucket in self.ip_buckets.items()
                    if bucket.last_refill < cutoff_time
                ]
                for key in old_keys:
                    del self.ip_buckets[key]

                # Cleanup WebSocket buckets
                old_ws_keys = [
                    key for key, bucket in self.websocket_ip_buckets.items()
                    if bucket.last_refill < cutoff_time
                ]
                for key in old_ws_keys:
                    del self.websocket_ip_buckets[key]

                if old_keys or old_ws_keys:
                    logger.info(
                        "Cleaned up old rate limit buckets",
                        ip_buckets_removed=len(old_keys),
                        websocket_buckets_removed=len(old_ws_keys),
                    )

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Rate limiter cleanup failed", exception=e)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for rate limiting."""

    def __init__(self, app, rate_limiter: RateLimiter):
        super().__init__(app)
        self.rate_limiter = rate_limiter

    async def dispatch(self, request: Request, call_next) -> Response:
        """Apply rate limiting to HTTP requests."""
        # Get client IP
        client_ip = self._get_client_ip(request)

        # Skip rate limiting for health checks and metrics
        if request.url.path in ["/health", "/metrics", "/api/status"]:
            return await call_next(request)

        # Check rate limit
        if not self.rate_limiter.check_api_rate_limit(request, client_ip):
            logger.warning(
                "Rate limit exceeded for API request",
                client_ip=client_ip,
                path=request.url.path,
                method=request.method,
            )

            # Get rate limit info for headers
            rate_info = self.rate_limiter.get_rate_limit_info(client_ip, request.url.path)

            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please try again later.",
                headers={
                    "Retry-After": "60",
                    "X-RateLimit-Limit": str(rate_info["capacity"]),
                    "X-RateLimit-Remaining": str(max(0, rate_info["remaining_tokens"])),
                    "X-RateLimit-Reset": str(int(rate_info["reset_time"])),
                }
            )

        # Continue with request
        response = await call_next(request)

        # Add rate limit headers to response
        rate_info = self.rate_limiter.get_rate_limit_info(client_ip, request.url.path)
        response.headers["X-RateLimit-Limit"] = str(rate_info["capacity"])
        response.headers["X-RateLimit-Remaining"] = str(max(0, rate_info["remaining_tokens"]))
        response.headers["X-RateLimit-Reset"] = str(int(rate_info["reset_time"]))

        return response

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request."""
        # Check for forwarded headers (load balancer/proxy)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip

        # Fall back to direct client IP
        return request.client.host if request.client else "unknown"


# Global rate limiter instance
rate_limiter = RateLimiter()
