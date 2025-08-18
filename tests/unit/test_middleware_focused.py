"""Comprehensive tests for web middleware to achieve 100% coverage."""

from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import FastAPI, Request, Response
from fastapi.testclient import TestClient

from cc_orchestrator.web.middleware import (
    LoggingMiddleware,
    RateLimitMiddleware,
    RequestIDMiddleware,
    SecurityHeadersMiddleware,
)


@pytest.fixture
def mock_request():
    """Create a mock request for testing."""
    request = Mock(spec=Request)
    request.method = "GET"
    request.url.path = "/test"
    request.headers = {}
    request.state = Mock()
    request.client = Mock()
    request.client.host = "192.168.1.100"
    return request


@pytest.fixture
def mock_response():
    """Create a mock response for testing."""
    response = Mock(spec=Response)
    response.status_code = 200
    response.headers = {}
    return response


class TestRequestIDMiddleware:
    """Test RequestIDMiddleware functionality."""

    @pytest.fixture
    def middleware(self):
        """Create RequestIDMiddleware instance."""
        app = Mock()
        return RequestIDMiddleware(app)

    async def test_dispatch_adds_request_id(
        self, middleware, mock_request, mock_response
    ):
        """Test that dispatch adds request ID to request state and response headers."""
        call_next = AsyncMock(return_value=mock_response)

        result = await middleware.dispatch(mock_request, call_next)

        # Check request ID was added to request state
        assert hasattr(mock_request.state, "request_id")
        assert mock_request.state.request_id is not None
        assert len(mock_request.state.request_id) == 36  # UUID length

        # Check request ID was added to response headers
        assert "X-Request-ID" in mock_response.headers
        assert mock_response.headers["X-Request-ID"] == mock_request.state.request_id

        # Check call_next was called
        call_next.assert_called_once_with(mock_request)
        assert result == mock_response

    async def test_dispatch_generates_unique_ids(self, middleware, mock_response):
        """Test that each request gets a unique ID."""
        call_next = AsyncMock(return_value=mock_response)
        request1 = Mock(spec=Request)
        request1.state = Mock()
        request2 = Mock(spec=Request)
        request2.state = Mock()

        await middleware.dispatch(request1, call_next)
        await middleware.dispatch(request2, call_next)

        assert request1.state.request_id != request2.state.request_id


class TestLoggingMiddleware:
    """Test LoggingMiddleware functionality."""

    @pytest.fixture
    def middleware(self):
        """Create LoggingMiddleware instance."""
        app = Mock()
        return LoggingMiddleware(app)

    async def test_dispatch_logs_request_and_response(
        self, middleware, mock_request, mock_response
    ):
        """Test that dispatch logs both request and response."""
        mock_request.headers = {"user-agent": "test-agent"}
        mock_request.state.request_id = "test-request-id"
        call_next = AsyncMock(return_value=mock_response)

        with (
            patch("cc_orchestrator.web.middleware.log_api_request") as mock_log_req,
            patch("cc_orchestrator.web.middleware.log_api_response") as mock_log_resp,
            patch("time.time", side_effect=[1000.0, 1001.5]),
        ):

            result = await middleware.dispatch(mock_request, call_next)

            # Check request logging
            mock_log_req.assert_called_once_with(
                method="GET",
                path="/test",
                client_ip="192.168.1.100",
                user_agent="test-agent",
                request_id="test-request-id",
            )

            # Check response logging
            mock_log_resp.assert_called_once_with(
                method="GET",
                path="/test",
                status_code=200,
                response_time_ms=1500.0,  # 1.5 seconds * 1000
                request_id="test-request-id",
            )

            assert result == mock_response

    async def test_dispatch_handles_missing_request_id(
        self, middleware, mock_request, mock_response
    ):
        """Test that dispatch handles missing request ID gracefully."""
        call_next = AsyncMock(return_value=mock_response)
        # Create a fresh state object without request_id
        mock_request.state = Mock()
        # Ensure no request_id attribute exists
        if hasattr(mock_request.state, "request_id"):
            delattr(mock_request.state, "request_id")

        with (
            patch("cc_orchestrator.web.middleware.log_api_request") as mock_log_req,
            patch("cc_orchestrator.web.middleware.log_api_response") as mock_log_resp,
        ):

            await middleware.dispatch(mock_request, call_next)

            # Both should be called with None for request_id
            assert mock_log_req.call_args[1]["request_id"] is None
            assert mock_log_resp.call_args[1]["request_id"] is None

    def test_get_client_ip_forwarded_for(self, middleware):
        """Test client IP extraction from X-Forwarded-For header."""
        request = Mock()
        request.headers = {"x-forwarded-for": "203.0.113.195, 70.41.3.18, 192.168.1.1"}
        request.client = None

        ip = middleware._get_client_ip(request)
        assert ip == "203.0.113.195"

    def test_get_client_ip_forwarded(self, middleware):
        """Test client IP extraction from X-Forwarded header."""
        request = Mock()
        request.headers = {"x-forwarded": "203.0.113.195, proxy"}
        request.client = None

        ip = middleware._get_client_ip(request)
        assert ip == "203.0.113.195"

    def test_get_client_ip_real_ip(self, middleware):
        """Test client IP extraction from X-Real-IP header."""
        request = Mock()
        request.headers = {"x-real-ip": "203.0.113.195"}
        request.client = None

        ip = middleware._get_client_ip(request)
        assert ip == "203.0.113.195"

    def test_get_client_ip_direct_client(self, middleware):
        """Test client IP extraction from direct client."""
        request = Mock()
        request.headers = {}
        request.client = Mock()
        request.client.host = "192.168.1.100"

        ip = middleware._get_client_ip(request)
        assert ip == "192.168.1.100"

    def test_get_client_ip_no_client(self, middleware):
        """Test client IP extraction when no client available."""
        request = Mock()
        request.headers = {}
        request.client = None

        ip = middleware._get_client_ip(request)
        assert ip == "unknown"


class TestRateLimitMiddleware:
    """Test RateLimitMiddleware functionality."""

    @pytest.fixture
    def middleware(self):
        """Create RateLimitMiddleware instance."""
        app = Mock()
        return RateLimitMiddleware(app, requests_per_minute=3)

    async def test_dispatch_allows_requests_within_limit(
        self, middleware, mock_request, mock_response
    ):
        """Test that requests within limit are allowed."""
        call_next = AsyncMock(return_value=mock_response)

        with patch("cc_orchestrator.web.middleware.datetime") as mock_datetime:
            now = datetime(2023, 1, 1, 12, 0, 0)
            mock_datetime.now.return_value = now

            result = await middleware.dispatch(mock_request, call_next)

            assert result == mock_response
            call_next.assert_called_once_with(mock_request)

            # Check rate limit headers were added
            assert mock_response.headers["X-RateLimit-Limit"] == "3"
            assert mock_response.headers["X-RateLimit-Remaining"] == "2"
            assert "X-RateLimit-Reset" in mock_response.headers

    async def test_dispatch_blocks_requests_over_limit(self, middleware, mock_request):
        """Test that requests over limit are blocked."""
        call_next = AsyncMock()

        with patch("cc_orchestrator.web.middleware.datetime") as mock_datetime:
            now = datetime(2023, 1, 1, 12, 0, 0)
            mock_datetime.now.return_value = now

            # Make requests up to the limit
            for _ in range(3):
                await middleware.dispatch(mock_request, call_next)

            # Next request should be blocked
            result = await middleware.dispatch(mock_request, call_next)

            assert result.status_code == 429
            assert "Rate limit exceeded" in result.body.decode()
            assert result.headers["Retry-After"] == "60"
            assert result.media_type == "application/json"

            # Should not have called next handler for blocked request
            assert call_next.call_count == 3

    async def test_dispatch_cleans_old_requests(
        self, middleware, mock_request, mock_response
    ):
        """Test that old requests are cleaned up."""
        call_next = AsyncMock(return_value=mock_response)

        with patch("cc_orchestrator.web.middleware.datetime") as mock_datetime:
            # First request at time 0
            mock_datetime.now.return_value = datetime(2023, 1, 1, 12, 0, 0)
            await middleware.dispatch(mock_request, call_next)
            await middleware.dispatch(mock_request, call_next)
            await middleware.dispatch(mock_request, call_next)

            # Should be at limit now
            assert len(middleware.client_requests["192.168.1.100"]) == 3

            # Move time forward by 2 minutes (old requests should be cleaned)
            mock_datetime.now.return_value = datetime(2023, 1, 1, 12, 2, 0)
            result = await middleware.dispatch(mock_request, call_next)

            # Should be allowed again (old requests cleaned)
            assert result == mock_response
            assert len(middleware.client_requests["192.168.1.100"]) == 1

    async def test_dispatch_different_ips_separate_limits(
        self, middleware, mock_response
    ):
        """Test that different IPs have separate rate limits."""
        call_next = AsyncMock(return_value=mock_response)

        # Create two different requests with different IPs
        request1 = Mock(spec=Request)
        request1.client = Mock()
        request1.client.host = "192.168.1.100"
        request1.headers = {}

        request2 = Mock(spec=Request)
        request2.client = Mock()
        request2.client.host = "192.168.1.101"
        request2.headers = {}

        with patch("cc_orchestrator.web.middleware.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime(2023, 1, 1, 12, 0, 0)

            # Fill up limit for first IP
            for _ in range(3):
                await middleware.dispatch(request1, call_next)

            # Second IP should still be allowed
            result = await middleware.dispatch(request2, call_next)
            assert result == mock_response

    def test_get_client_ip_forwarded_for(self, middleware):
        """Test client IP extraction from X-Forwarded-For header."""
        request = Mock()
        request.headers = {"x-forwarded-for": "203.0.113.195, proxy"}
        request.client = None

        ip = middleware._get_client_ip(request)
        assert ip == "203.0.113.195"

    def test_get_client_ip_real_ip(self, middleware):
        """Test client IP extraction from X-Real-IP header."""
        request = Mock()
        request.headers = {"x-real-ip": "203.0.113.195"}
        request.client = None

        ip = middleware._get_client_ip(request)
        assert ip == "203.0.113.195"

    def test_get_client_ip_direct(self, middleware):
        """Test client IP extraction from direct client."""
        request = Mock()
        request.headers = {}
        request.client = Mock()
        request.client.host = "192.168.1.100"

        ip = middleware._get_client_ip(request)
        assert ip == "192.168.1.100"

    def test_get_client_ip_no_client(self, middleware):
        """Test client IP extraction when no client available."""
        request = Mock()
        request.headers = {}
        request.client = None

        ip = middleware._get_client_ip(request)
        assert ip == "unknown"

    def test_init_with_custom_rate_limit(self):
        """Test initialization with custom rate limit."""
        app = Mock()
        middleware = RateLimitMiddleware(app, requests_per_minute=100)

        assert middleware.requests_per_minute == 100
        assert isinstance(middleware.client_requests, dict)


class TestSecurityHeadersMiddleware:
    """Test SecurityHeadersMiddleware functionality."""

    @pytest.fixture
    def middleware(self):
        """Create SecurityHeadersMiddleware instance."""
        app = Mock()
        return SecurityHeadersMiddleware(app)

    async def test_dispatch_adds_security_headers(
        self, middleware, mock_request, mock_response
    ):
        """Test that dispatch adds all required security headers."""
        call_next = AsyncMock(return_value=mock_response)

        result = await middleware.dispatch(mock_request, call_next)

        # Check all security headers were added
        expected_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
        }

        for header, value in expected_headers.items():
            assert mock_response.headers[header] == value

        call_next.assert_called_once_with(mock_request)
        assert result == mock_response

    async def test_dispatch_preserves_existing_headers(self, middleware, mock_request):
        """Test that dispatch preserves existing response headers."""
        response = Mock(spec=Response)
        response.headers = {"Custom-Header": "custom-value"}
        call_next = AsyncMock(return_value=response)

        result = await middleware.dispatch(mock_request, call_next)

        # Check custom header is preserved
        assert response.headers["Custom-Header"] == "custom-value"
        # Check security headers were added
        assert "X-Content-Type-Options" in response.headers
        assert result == response


class TestMiddlewareIntegration:
    """Test middleware integration with FastAPI."""

    def test_middleware_with_fastapi_app(self):
        """Test that middleware works with actual FastAPI app."""
        app = FastAPI()

        # Add all middleware
        app.add_middleware(SecurityHeadersMiddleware)
        app.add_middleware(RateLimitMiddleware, requests_per_minute=10)
        app.add_middleware(LoggingMiddleware)
        app.add_middleware(RequestIDMiddleware)

        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}

        client = TestClient(app)
        response = client.get("/test")

        # Check response is successful
        assert response.status_code == 200

        # Check security headers are present
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["X-Frame-Options"] == "DENY"

        # Check request ID header is present
        assert "X-Request-ID" in response.headers

        # Check rate limit headers are present
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers

    def test_rate_limit_middleware_integration(self):
        """Test rate limit middleware blocks excessive requests."""
        app = FastAPI()
        app.add_middleware(RateLimitMiddleware, requests_per_minute=2)

        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}

        client = TestClient(app)

        # First two requests should succeed
        response1 = client.get("/test")
        response2 = client.get("/test")
        assert response1.status_code == 200
        assert response2.status_code == 200

        # Third request should be rate limited
        response3 = client.get("/test")
        assert response3.status_code == 429
        assert "Rate limit exceeded" in response3.text
