"""
Web middleware modules.

Provides middleware for rate limiting, authentication, and other cross-cutting concerns.
"""

# Import new advanced rate limiter
from .rate_limiter import RateLimitMiddleware, rate_limiter

__all__ = [
    "RateLimitMiddleware",
    "rate_limiter"
]
