"""Focused tests for rate limiter to improve coverage."""

import time
from unittest.mock import Mock

import pytest
from fastapi import Request

from cc_orchestrator.web.exceptions import RateLimitExceededError
from cc_orchestrator.web.rate_limiter import (
    InMemoryRateLimiter,
    get_client_ip,
    rate_limit,
    websocket_rate_limit,
)


class TestInMemoryRateLimiter:
    """Test InMemoryRateLimiter functionality."""

    def test_init(self):
        """Test rate limiter initialization."""
        limiter = InMemoryRateLimiter()
        assert limiter.request_history == {}

    def test_check_rate_limit_within_limit(self):
        """Test rate limiting within allowed limit."""
        limiter = InMemoryRateLimiter()

        # Should not raise exception within limit
        limiter.check_rate_limit("192.168.1.1", "GET:/test", 5, 60)
        limiter.check_rate_limit("192.168.1.1", "GET:/test", 5, 60)
        limiter.check_rate_limit("192.168.1.1", "GET:/test", 5, 60)

        assert len(limiter.request_history["192.168.1.1"]["GET:/test"]) == 3

    def test_check_rate_limit_exceeded(self):
        """Test rate limiting when limit is exceeded."""
        limiter = InMemoryRateLimiter()

        # Fill up to limit
        for _ in range(3):
            limiter.check_rate_limit("192.168.1.1", "GET:/test", 3, 60)

        # Next request should raise exception
        with pytest.raises(RateLimitExceededError) as exc_info:
            limiter.check_rate_limit("192.168.1.1", "GET:/test", 3, 60)

        assert exc_info.value.limit == 3
        assert "60s" in str(exc_info.value.window)

    def test_check_rate_limit_different_endpoints(self):
        """Test rate limiting with different endpoints."""
        limiter = InMemoryRateLimiter()

        # Different endpoints should have separate limits
        for _ in range(3):
            limiter.check_rate_limit("192.168.1.1", "GET:/test1", 3, 60)
            limiter.check_rate_limit("192.168.1.1", "GET:/test2", 3, 60)

        # Both should be at limit but not exceeded
        assert len(limiter.request_history["192.168.1.1"]["GET:/test1"]) == 3
        assert len(limiter.request_history["192.168.1.1"]["GET:/test2"]) == 3

    def test_check_rate_limit_different_ips(self):
        """Test rate limiting with different IPs."""
        limiter = InMemoryRateLimiter()

        # Different IPs should have separate limits
        for _ in range(3):
            limiter.check_rate_limit("192.168.1.1", "GET:/test", 3, 60)
            limiter.check_rate_limit("192.168.1.2", "GET:/test", 3, 60)

        assert len(limiter.request_history["192.168.1.1"]["GET:/test"]) == 3
        assert len(limiter.request_history["192.168.1.2"]["GET:/test"]) == 3

    def test_cleanup_old_entries(self):
        """Test cleanup of old entries."""
        limiter = InMemoryRateLimiter()

        # Add some requests
        limiter.check_rate_limit("192.168.1.1", "GET:/test", 10, 60)
        limiter.check_rate_limit("192.168.1.2", "GET:/test", 10, 60)

        assert len(limiter.request_history) == 2

        # Clean up (with very short max_age to clean everything)
        limiter.cleanup_old_entries(max_age_seconds=0)

        # Should be cleaned up
        assert len(limiter.request_history) == 0

    def test_window_sliding(self):
        """Test that rate limiting window slides correctly."""
        limiter = InMemoryRateLimiter()

        # Mock time to control window sliding
        original_time = time.time
        current_time = 1000.0

        def mock_time():
            return current_time

        time.time = mock_time

        try:
            # Add requests at current time
            limiter.check_rate_limit("192.168.1.1", "GET:/test", 2, 10)
            limiter.check_rate_limit("192.168.1.1", "GET:/test", 2, 10)

            # Should be at limit
            with pytest.raises(RateLimitExceededError):
                limiter.check_rate_limit("192.168.1.1", "GET:/test", 2, 10)

            # Move time forward beyond window
            current_time = 1020.0

            # Should be allowed again
            limiter.check_rate_limit("192.168.1.1", "GET:/test", 2, 10)

        finally:
            time.time = original_time


class TestClientIPExtraction:
    """Test client IP extraction functionality."""

    def test_get_client_ip_forwarded_for(self):
        """Test IP extraction from X-Forwarded-For header."""
        mock_request = Mock(spec=Request)
        mock_request.headers = {"X-Forwarded-For": "203.0.113.195, 70.41.3.18"}
        mock_request.client = None

        ip = get_client_ip(mock_request)
        assert ip == "203.0.113.195"

    def test_get_client_ip_forwarded_host(self):
        """Test IP extraction from X-Forwarded-Host header."""
        mock_request = Mock(spec=Request)
        mock_request.headers = {"X-Forwarded-Host": "example.com"}
        mock_request.client = None

        ip = get_client_ip(mock_request)
        assert ip == "example.com"

    def test_get_client_ip_real_ip(self):
        """Test IP extraction from X-Real-IP header."""
        mock_request = Mock(spec=Request)
        mock_request.headers = {"X-Real-IP": "203.0.113.195"}
        mock_request.client = None

        ip = get_client_ip(mock_request)
        assert ip == "203.0.113.195"

    def test_get_client_ip_direct(self):
        """Test IP extraction from direct client connection."""
        mock_client = Mock()
        mock_client.host = "192.168.1.100"

        mock_request = Mock(spec=Request)
        mock_request.headers = {}
        mock_request.client = mock_client

        ip = get_client_ip(mock_request)
        assert ip == "192.168.1.100"

    def test_get_client_ip_unknown(self):
        """Test fallback when no IP can be determined."""
        mock_request = Mock(spec=Request)
        mock_request.headers = {}
        mock_request.client = None

        ip = get_client_ip(mock_request)
        assert ip == "unknown"


class TestWebSocketRateLimit:
    """Test WebSocket rate limiting functionality."""

    def test_websocket_rate_limit_functions(self):
        """Test WebSocket rate limit function creation."""
        check_limit, add_connection, remove_connection = websocket_rate_limit(2)

        # Should not raise initially
        check_limit("192.168.1.1")

        # Add connections
        add_connection("192.168.1.1")
        add_connection("192.168.1.1")

        # Should be at limit
        with pytest.raises(RateLimitExceededError):
            check_limit("192.168.1.1")

        # Remove connection
        remove_connection("192.168.1.1")

        # Should be allowed again
        check_limit("192.168.1.1")

    def test_websocket_rate_limit_different_ips(self):
        """Test WebSocket rate limiting with different IPs."""
        check_limit, add_connection, remove_connection = websocket_rate_limit(1)

        # Different IPs should have separate limits
        add_connection("192.168.1.1")
        add_connection("192.168.1.2")

        # Both should be at their individual limits
        with pytest.raises(RateLimitExceededError):
            check_limit("192.168.1.1")

        with pytest.raises(RateLimitExceededError):
            check_limit("192.168.1.2")

    def test_websocket_rate_limit_cleanup(self):
        """Test WebSocket connection cleanup."""
        check_limit, add_connection, remove_connection = websocket_rate_limit(2)

        # Add and remove connections
        add_connection("192.168.1.1")
        remove_connection("192.168.1.1")
        remove_connection("192.168.1.1")  # Extra removal should be safe

        # Should be allowed
        check_limit("192.168.1.1")


class TestRateLimitDecorator:
    """Test rate limit decorator functionality."""

    @pytest.fixture
    def mock_request(self):
        """Create a mock request for testing."""
        mock_client = Mock()
        mock_client.host = "192.168.1.1"

        mock_url = Mock()
        mock_url.path = "/test"

        request = Mock(spec=Request)
        request.client = mock_client
        request.method = "GET"
        request.url = mock_url
        request.headers = {}

        return request

    async def test_rate_limit_decorator_success(self, mock_request):
        """Test rate limit decorator with successful request."""

        @rate_limit(requests_per_minute=60)
        async def test_endpoint():
            return "success"

        # Should pass without request
        result = await test_endpoint()
        assert result == "success"

        # Should pass with request
        result = await test_endpoint(request=mock_request)
        assert result == "success"

    async def test_rate_limit_decorator_no_request(self):
        """Test rate limit decorator without request parameter."""

        @rate_limit(requests_per_minute=60)
        async def test_endpoint(data: str = "test"):
            return f"result: {data}"

        result = await test_endpoint(data="hello")
        assert result == "result: hello"
