"""Comprehensive tests for rate limiter."""

import time
from unittest.mock import Mock

import pytest

from cc_orchestrator.web.exceptions import RateLimitExceededError
from cc_orchestrator.web.rate_limiter import (
    InMemoryRateLimiter,
    get_client_ip,
    rate_limit,
    ws_add_connection,
    ws_check_limit,
    ws_remove_connection,
)


class TestInMemoryRateLimiter:
    """Test in-memory rate limiter functionality."""

    def test_rate_limiter_init(self):
        """Test rate limiter initialization."""
        limiter = InMemoryRateLimiter()
        assert len(limiter.request_history) == 0

    def test_rate_limit_under_limit(self):
        """Test requests under rate limit."""
        limiter = InMemoryRateLimiter()

        # Should not raise exception
        limiter.check_rate_limit("192.168.1.1", "GET:/api/test", 10, 60)
        limiter.check_rate_limit("192.168.1.1", "GET:/api/test", 10, 60)
        limiter.check_rate_limit("192.168.1.1", "GET:/api/test", 10, 60)

    def test_rate_limit_exceeded(self):
        """Test rate limit exceeded."""
        limiter = InMemoryRateLimiter()
        client_ip = "192.168.1.1"
        endpoint = "GET:/api/test"
        limit = 3
        window = 60

        # Make requests up to limit
        for _ in range(limit):
            limiter.check_rate_limit(client_ip, endpoint, limit, window)

        # Next request should raise exception
        with pytest.raises(RateLimitExceededError) as exc_info:
            limiter.check_rate_limit(client_ip, endpoint, limit, window)

        assert exc_info.value.limit == limit
        assert "60s" in exc_info.value.message

    def test_rate_limit_different_clients(self):
        """Test rate limiting for different clients."""
        limiter = InMemoryRateLimiter()
        endpoint = "GET:/api/test"
        limit = 2
        window = 60

        # Client 1 makes requests
        limiter.check_rate_limit("192.168.1.1", endpoint, limit, window)
        limiter.check_rate_limit("192.168.1.1", endpoint, limit, window)

        # Client 1 should be at limit
        with pytest.raises(RateLimitExceededError):
            limiter.check_rate_limit("192.168.1.1", endpoint, limit, window)

        # Client 2 should still be able to make requests
        limiter.check_rate_limit("192.168.1.2", endpoint, limit, window)
        limiter.check_rate_limit("192.168.1.2", endpoint, limit, window)

    def test_rate_limit_different_endpoints(self):
        """Test rate limiting for different endpoints."""
        limiter = InMemoryRateLimiter()
        client_ip = "192.168.1.1"
        limit = 2
        window = 60

        # Make requests to endpoint1
        limiter.check_rate_limit(client_ip, "GET:/api/endpoint1", limit, window)
        limiter.check_rate_limit(client_ip, "GET:/api/endpoint1", limit, window)

        # endpoint1 should be at limit
        with pytest.raises(RateLimitExceededError):
            limiter.check_rate_limit(client_ip, "GET:/api/endpoint1", limit, window)

        # endpoint2 should still be available
        limiter.check_rate_limit(client_ip, "GET:/api/endpoint2", limit, window)
        limiter.check_rate_limit(client_ip, "GET:/api/endpoint2", limit, window)

    def test_rate_limit_window_expiration(self):
        """Test that rate limit window expires."""
        limiter = InMemoryRateLimiter()
        client_ip = "192.168.1.1"
        endpoint = "GET:/api/test"
        limit = 2
        window = 1  # 1 second window

        # Fill up the limit
        limiter.check_rate_limit(client_ip, endpoint, limit, window)
        limiter.check_rate_limit(client_ip, endpoint, limit, window)

        # Should be at limit
        with pytest.raises(RateLimitExceededError):
            limiter.check_rate_limit(client_ip, endpoint, limit, window)

        # Fast-forward time by mocking the current time
        with patch('time.time', return_value=time.time() + 1.1):
            # Should be able to make requests again
            limiter.check_rate_limit(client_ip, endpoint, limit, window)

    def test_cleanup_old_entries(self):
        """Test cleanup of old entries."""
        limiter = InMemoryRateLimiter()
        client_ip = "192.168.1.1"
        endpoint = "GET:/api/test"

        # Add some requests
        limiter.check_rate_limit(client_ip, endpoint, 10, 60)
        assert len(limiter.request_history[client_ip][endpoint]) == 1

        # Cleanup with very short age should remove them
        limiter.cleanup_old_entries(max_age_seconds=0)

        # Should be cleaned up
        assert (
            client_ip not in limiter.request_history
            or endpoint not in limiter.request_history[client_ip]
            or len(limiter.request_history[client_ip][endpoint]) == 0
        )

    def test_cleanup_preserves_recent_entries(self):
        """Test cleanup preserves recent entries."""
        limiter = InMemoryRateLimiter()
        client_ip = "192.168.1.1"
        endpoint = "GET:/api/test"

        # Add some requests
        limiter.check_rate_limit(client_ip, endpoint, 10, 60)

        # Cleanup with long age should preserve them
        limiter.cleanup_old_entries(max_age_seconds=3600)

        # Should still be there
        assert len(limiter.request_history[client_ip][endpoint]) == 1

    def test_cleanup_removes_empty_entries(self):
        """Test cleanup removes empty client/endpoint entries."""
        limiter = InMemoryRateLimiter()

        # Manually add old entries
        old_time = time.time() - 7200  # 2 hours ago
        limiter.request_history["192.168.1.1"]["GET:/api/test"] = [old_time]

        # Cleanup
        limiter.cleanup_old_entries(max_age_seconds=3600)

        # Should remove empty entries
        assert "192.168.1.1" not in limiter.request_history

    def test_rate_limit_with_zero_limit(self):
        """Test rate limiting with zero limit."""
        limiter = InMemoryRateLimiter()

        # First request with limit 0 should immediately fail
        with pytest.raises(RateLimitExceededError):
            limiter.check_rate_limit("192.168.1.1", "GET:/api/test", 0, 60)

    def test_rate_limit_records_timestamp(self):
        """Test that requests are recorded with timestamps."""
        limiter = InMemoryRateLimiter()
        client_ip = "192.168.1.1"
        endpoint = "GET:/api/test"

        before = time.time()
        limiter.check_rate_limit(client_ip, endpoint, 10, 60)
        after = time.time()

        # Should have recorded a timestamp
        timestamps = limiter.request_history[client_ip][endpoint]
        assert len(timestamps) == 1
        assert before <= timestamps[0] <= after


class TestGetClientIP:
    """Test client IP extraction."""

    def test_get_client_ip_from_x_forwarded_for(self):
        """Test extracting IP from X-Forwarded-For header."""
        request = Mock()
        request.headers = {"X-Forwarded-For": "192.168.1.1, 10.0.0.1"}
        request.client = None

        ip = get_client_ip(request)
        assert ip == "192.168.1.1"

    def test_get_client_ip_from_x_forwarded_host(self):
        """Test extracting IP from X-Forwarded-Host header."""
        request = Mock()
        request.headers = {"X-Forwarded-Host": "192.168.1.2"}
        request.client = None

        ip = get_client_ip(request)
        assert ip == "192.168.1.2"

    def test_get_client_ip_from_x_real_ip(self):
        """Test extracting IP from X-Real-IP header."""
        request = Mock()
        request.headers = {"X-Real-IP": "192.168.1.3"}
        request.client = None

        ip = get_client_ip(request)
        assert ip == "192.168.1.3"

    def test_get_client_ip_from_client_direct(self):
        """Test extracting IP from client directly."""
        request = Mock()
        request.headers = {}
        request.client = Mock()
        request.client.host = "192.168.1.4"

        ip = get_client_ip(request)
        assert ip == "192.168.1.4"

    def test_get_client_ip_no_client(self):
        """Test when no client information available."""
        request = Mock()
        request.headers = {}
        request.client = None

        ip = get_client_ip(request)
        assert ip == "unknown"

    def test_get_client_ip_priority_order(self):
        """Test that headers are checked in priority order."""
        request = Mock()
        request.headers = {
            "X-Forwarded-For": "192.168.1.1",
            "X-Forwarded-Host": "192.168.1.2",
            "X-Real-IP": "192.168.1.3",
        }
        request.client = Mock()
        request.client.host = "192.168.1.4"

        # Should use X-Forwarded-For first
        ip = get_client_ip(request)
        assert ip == "192.168.1.1"


class TestRateLimitDecorator:
    """Test rate limit decorator functionality."""

    def test_rate_limit_decorator_creation(self):
        """Test rate limit decorator can be created."""
        decorator = rate_limit(requests_per_minute=30)
        assert callable(decorator)

    def test_rate_limit_decorator_default_params(self):
        """Test rate limit decorator with default parameters."""
        decorator = rate_limit()
        assert callable(decorator)


class TestWebSocketRateLimiting:
    """Test WebSocket connection rate limiting."""

    def test_websocket_rate_limit_under_limit(self):
        """Test WebSocket connections under limit."""
        # Should not raise exception
        ws_check_limit("192.168.1.1")
        ws_add_connection("192.168.1.1")

        # Should be able to add more
        ws_check_limit("192.168.1.1")
        ws_add_connection("192.168.1.1")

    def test_websocket_rate_limit_exceeded(self):
        """Test WebSocket connections exceeding limit."""
        client_ip = "192.168.1.100"  # Use unique IP to avoid conflicts

        # Add connections up to limit (default 5)
        for _i in range(5):
            ws_check_limit(client_ip)
            ws_add_connection(client_ip)

        # Next connection should fail
        with pytest.raises(RateLimitExceededError) as exc_info:
            ws_check_limit(client_ip)

        assert "concurrent connections" in exc_info.value.message

    def test_websocket_connection_removal(self):
        """Test WebSocket connection removal."""
        client_ip = "192.168.1.101"  # Use unique IP

        # Add a connection
        ws_check_limit(client_ip)
        ws_add_connection(client_ip)

        # Remove it
        ws_remove_connection(client_ip)

        # Should be able to add again
        ws_check_limit(client_ip)

    def test_websocket_different_ips(self):
        """Test WebSocket connections from different IPs."""
        # Fill up limit for one IP
        for _i in range(5):
            ws_add_connection("192.168.1.200")

        # Should fail for same IP
        with pytest.raises(RateLimitExceededError):
            ws_check_limit("192.168.1.200")

        # Should succeed for different IP
        ws_check_limit("192.168.1.201")

    def test_websocket_connection_tracking_accuracy(self):
        """Test accurate WebSocket connection tracking."""
        client_ip = "192.168.1.202"

        # Add multiple connections
        ws_add_connection(client_ip)
        ws_add_connection(client_ip)
        ws_add_connection(client_ip)

        # Remove some
        ws_remove_connection(client_ip)
        ws_remove_connection(client_ip)

        # Should still be able to add more
        ws_check_limit(client_ip)
        ws_add_connection(client_ip)
        ws_add_connection(client_ip)

    def test_websocket_remove_connection_when_zero(self):
        """Test removing connection when count is already zero."""
        client_ip = "192.168.1.203"

        # Remove connection when none exist (should not error)
        ws_remove_connection(client_ip)

        # Should still be able to add connections
        ws_check_limit(client_ip)
        ws_add_connection(client_ip)


class TestRateLimiterEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_client_ip(self):
        """Test rate limiting with empty client IP."""
        limiter = InMemoryRateLimiter()

        # Should handle empty string
        limiter.check_rate_limit("", "GET:/api/test", 10, 60)

        # Should be tracked under empty string
        assert "" in limiter.request_history

    def test_empty_endpoint(self):
        """Test rate limiting with empty endpoint."""
        limiter = InMemoryRateLimiter()

        # Should handle empty endpoint
        limiter.check_rate_limit("192.168.1.1", "", 10, 60)

        # Should be tracked
        assert "" in limiter.request_history["192.168.1.1"]

    def test_very_small_window(self):
        """Test rate limiting with very small time window."""
        limiter = InMemoryRateLimiter()

        # Should work with small window
        limiter.check_rate_limit("192.168.1.1", "GET:/api/test", 1, 0.1)

        # Should immediately be at limit due to small window
        with pytest.raises(RateLimitExceededError):
            limiter.check_rate_limit("192.168.1.1", "GET:/api/test", 1, 0.1)

    def test_large_numbers(self):
        """Test rate limiting with large numbers."""
        limiter = InMemoryRateLimiter()

        # Should handle large limits
        limiter.check_rate_limit("192.168.1.1", "GET:/api/test", 1000000, 3600)

        # Should not hit limit
        for _ in range(100):
            limiter.check_rate_limit("192.168.1.1", "GET:/api/test", 1000000, 3600)

    def test_concurrent_access_simulation(self):
        """Test simulated concurrent access to rate limiter."""
        limiter = InMemoryRateLimiter()
        client_ip = "192.168.1.1"
        endpoint = "GET:/api/test"
        limit = 10
        window = 60

        # Simulate rapid requests (would be concurrent in real scenario)
        requests_made = 0
        rate_limited = 0

        for _ in range(15):  # More than limit
            try:
                limiter.check_rate_limit(client_ip, endpoint, limit, window)
                requests_made += 1
            except RateLimitExceededError:
                rate_limited += 1

        assert requests_made == limit
        assert rate_limited == 5  # 15 - 10
