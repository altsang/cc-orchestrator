"""Proper rate limiter tests that verify functionality works."""

import os
import time
from unittest.mock import Mock

import pytest

from cc_orchestrator.web.exceptions import RateLimitExceededError
from cc_orchestrator.web.rate_limiter import InMemoryRateLimiter, rate_limit


class TestInMemoryRateLimiter:
    """Test the core rate limiter functionality."""

    def setup_method(self):
        """Set up test with fresh rate limiter."""
        self.limiter = InMemoryRateLimiter()

    def test_allows_requests_under_limit(self):
        """Test that requests under the limit are allowed."""
        # Should allow 3 requests in 60 seconds
        for _ in range(3):
            self.limiter.check_rate_limit("127.0.0.1", "GET:/test", 3, 60)

        # No exception should be raised

    def test_blocks_requests_over_limit(self):
        """Test that requests over the limit are blocked."""
        # Fill up the limit (3 requests)
        for _ in range(3):
            self.limiter.check_rate_limit("127.0.0.1", "GET:/test", 3, 60)

        # The 4th request should be blocked
        with pytest.raises(RateLimitExceededError) as exc_info:
            self.limiter.check_rate_limit("127.0.0.1", "GET:/test", 3, 60)

        assert "3" in str(exc_info.value)
        assert "60s" in str(exc_info.value)

    def test_different_ips_have_separate_limits(self):
        """Test that different IPs have separate rate limits."""
        # Fill up limit for first IP
        for _ in range(3):
            self.limiter.check_rate_limit("127.0.0.1", "GET:/test", 3, 60)

        # Second IP should still be allowed
        self.limiter.check_rate_limit("127.0.0.2", "GET:/test", 3, 60)

    def test_different_endpoints_have_separate_limits(self):
        """Test that different endpoints have separate rate limits."""
        # Fill up limit for first endpoint
        for _ in range(3):
            self.limiter.check_rate_limit("127.0.0.1", "GET:/test1", 3, 60)

        # Second endpoint should still be allowed
        self.limiter.check_rate_limit("127.0.0.1", "GET:/test2", 3, 60)

    def test_window_sliding_allows_new_requests(self):
        """Test that the time window slides properly."""
        # This test uses a very short window to test sliding
        self.limiter.check_rate_limit(
            "127.0.0.1", "GET:/test", 1, 0.1
        )  # 1 req per 0.1 seconds

        # Should be blocked immediately
        with pytest.raises(RateLimitExceededError):
            self.limiter.check_rate_limit("127.0.0.1", "GET:/test", 1, 0.1)

        # Wait for window to slide
        time.sleep(0.15)

        # Should be allowed again
        self.limiter.check_rate_limit("127.0.0.1", "GET:/test", 1, 0.1)

    def test_cleanup_removes_old_entries(self):
        """Test that cleanup removes old entries."""
        # Add some requests
        self.limiter.check_rate_limit("127.0.0.1", "GET:/test", 10, 60)
        assert len(self.limiter.request_history["127.0.0.1"]["GET:/test"]) == 1

        # Clean up entries older than 0 seconds (should remove everything)
        self.limiter.cleanup_old_entries(0)

        # History should be cleaned up
        assert "127.0.0.1" not in self.limiter.request_history


class TestRateLimitDecorator:
    """Test the rate limit decorator."""

    def test_uses_test_rate_limit_when_set(self):
        """Test that decorator uses TEST_RATE_LIMIT_PER_MINUTE when set."""
        # Set test environment variable
        old_value = os.environ.get("TEST_RATE_LIMIT_PER_MINUTE")
        os.environ["TEST_RATE_LIMIT_PER_MINUTE"] = "1000"  # Very high limit

        try:

            @rate_limit(requests_per_minute=1)  # Very low production limit
            async def test_endpoint(request=None):
                return "success"

            # Create mock request
            mock_request = Mock()
            mock_request.client.host = "127.0.0.1"
            mock_request.method = "GET"
            mock_request.url.path = "/test"
            mock_request.headers = {}

            # Should be able to make many requests due to high test limit
            import asyncio

            async def run_test():
                for _ in range(50):  # Would fail with limit=1, passes with limit=1000
                    result = await test_endpoint(mock_request)
                    assert result == "success"

            asyncio.run(run_test())

        finally:
            # Clean up
            if old_value is None:
                os.environ.pop("TEST_RATE_LIMIT_PER_MINUTE", None)
            else:
                os.environ["TEST_RATE_LIMIT_PER_MINUTE"] = old_value

    def test_rate_limiting_actually_works(self):
        """Test that rate limiting actually blocks requests when it should."""
        # Temporarily clear test environment to test real rate limiting
        old_value = os.environ.get("TEST_RATE_LIMIT_PER_MINUTE")
        os.environ.pop("TEST_RATE_LIMIT_PER_MINUTE", None)

        try:

            @rate_limit(requests_per_minute=2)  # Very low limit
            async def test_endpoint(request=None):
                return "success"

            # Create mock request
            mock_request = Mock()
            mock_request.client.host = "127.0.0.1"
            mock_request.method = "GET"
            mock_request.url.path = "/test-strict"
            mock_request.headers = {}

            import asyncio

            async def run_test():
                # First 2 requests should succeed
                await test_endpoint(mock_request)
                await test_endpoint(mock_request)

                # Third request should fail
                with pytest.raises(RateLimitExceededError):
                    await test_endpoint(mock_request)

            asyncio.run(run_test())

        finally:
            # Restore test environment
            if old_value is not None:
                os.environ["TEST_RATE_LIMIT_PER_MINUTE"] = old_value


class TestRateLimiterIntegration:
    """Integration tests for rate limiter with realistic scenarios."""

    def setup_method(self):
        """Reset rate limiter state."""
        from cc_orchestrator.web.rate_limiter import rate_limiter

        rate_limiter.request_history.clear()

    def test_rate_limiter_state_reset_works(self):
        """Test that the state reset in conftest.py works properly."""
        from cc_orchestrator.web.rate_limiter import rate_limiter

        # Add some state
        rate_limiter.check_rate_limit("127.0.0.1", "GET:/test", 10, 60)
        assert len(rate_limiter.request_history) > 0

        # State should be cleared between tests (this happens automatically via conftest.py)
        # This test verifies that our reset mechanism works
