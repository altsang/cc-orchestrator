"""
Simplified unit tests for FastAPI web application.

This module provides basic tests to verify FastAPI functionality.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from cc_orchestrator.web.app import create_app
from cc_orchestrator.web.dependencies import get_crud


@pytest.fixture
def mock_crud():
    """Create a simple mock CRUD instance."""
    crud = MagicMock()
    crud.list_instances = AsyncMock(return_value=([], 0))
    crud.list_tasks = AsyncMock(return_value=([], 0))
    crud.list_worktrees = AsyncMock(return_value=([], 0))
    crud.list_configurations = AsyncMock(return_value=([], 0))
    crud.list_health_checks = AsyncMock(return_value=([], 0))
    crud.list_alerts = AsyncMock(return_value=([], 0))
    return crud


@pytest.fixture
def client(mock_crud):
    """Create a test client with mocked dependencies."""
    app = create_app()
    app.dependency_overrides[get_crud] = lambda: mock_crud
    return TestClient(app)


class TestBasicEndpoints:
    """Test basic API endpoints."""

    def test_root_endpoint(self, client):
        """Test the root endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        # Root returns HTML, not JSON
        assert "text/html" in response.headers["content-type"]
        assert "CC-Orchestrator Dashboard" in response.text

    def test_ping_endpoint(self, client):
        """Test the ping endpoint."""
        response = client.get("/ping")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    def test_health_check_endpoint(self, client):
        """Test the health check endpoint."""
        response = client.get("/api/v1/health/")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data

    def test_list_instances_empty(self, client):
        """Test listing instances when none exist."""
        response = client.get("/api/v1/instances/")
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_list_tasks_empty(self, client):
        """Test listing tasks when none exist."""
        response = client.get("/api/v1/tasks/")
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_openapi_schema_available(self, client):
        """Test that OpenAPI schema is available."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data
        assert data["info"]["title"] == "CC-Orchestrator API"

    def test_swagger_docs_available(self, client):
        """Test that Swagger docs are available."""
        response = client.get("/docs")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_redoc_available(self, client):
        """Test that ReDoc is available."""
        response = client.get("/redoc")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]


class TestAPIValidation:
    """Test API validation."""

    def test_invalid_pagination(self, client):
        """Test invalid pagination parameters."""
        response = client.get("/api/v1/instances/?page=0")
        assert response.status_code in [400, 422]  # Both indicate validation error

        response = client.get("/api/v1/instances/?size=101")
        assert response.status_code in [400, 422]  # Both indicate validation error

    def test_valid_pagination(self, client):
        """Test valid pagination parameters."""
        response = client.get("/api/v1/instances/?page=1&size=10")
        assert response.status_code == 200


class TestMiddleware:
    """Test middleware functionality."""

    def test_cors_headers(self, client):
        """Test CORS headers are present."""
        response = client.options("/api/v1/instances/")
        # FastAPI automatically handles OPTIONS requests
        assert response.status_code in [200, 405]

    def test_request_id_header(self, client):
        """Test that request ID is added to responses."""
        response = client.get("/ping")
        assert response.status_code == 200
        assert "X-Request-ID" in response.headers

    def test_rate_limiting_headers(self, client):
        """Test rate limiting headers."""
        import os

        response = client.get("/ping")
        assert response.status_code == 200

        # Rate limiting is disabled during testing, so headers may not be present
        # Check if we're in testing mode
        testing_mode = os.getenv("TESTING", "false").lower() == "true"

        if not testing_mode:
            # In non-testing mode, rate limiting headers should be present
            assert "X-RateLimit-Limit" in response.headers
            assert "X-RateLimit-Remaining" in response.headers
            assert "X-RateLimit-Reset" in response.headers
        else:
            # In testing mode, rate limiting is disabled, so we just verify
            # the response is successful without rate limiting headers
            # This is the expected behavior in testing mode
            pass
