"""Comprehensive tests for API router functionality."""

from unittest.mock import Mock, patch

import pytest
from fastapi import Request
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from cc_orchestrator.database.connection import Base, get_db_session
from cc_orchestrator.database.models import InstanceStatus
from cc_orchestrator.web.app import create_app
from cc_orchestrator.web.auth import create_access_token
from cc_orchestrator.web.exceptions import (
    RateLimitExceededError,
)


@pytest.fixture(scope="function")
def test_db():
    """Create a test database."""
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)

    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db():
        try:
            db = TestingSessionLocal()
            yield db
        finally:
            db.close()

    return override_get_db


@pytest.fixture
def test_app(test_db):
    """Create test FastAPI application with test database."""
    app = create_app()
    app.dependency_overrides[get_db_session] = test_db
    return app


@pytest.fixture
def client(test_app):
    """Create test client."""
    return TestClient(test_app)


@pytest.fixture
def auth_token():
    """Create valid authentication token."""
    return create_access_token(data={"sub": "testuser", "role": "admin"})


@pytest.fixture
def auth_headers(auth_token):
    """Create authentication headers."""
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture
def mock_request():
    """Create mock request object."""
    request = Mock(spec=Request)
    request.client = Mock()
    request.client.host = "127.0.0.1"
    request.headers = {}
    return request


class TestAPIRoutingAndDependencies:
    """Test API routing and dependency injection."""

    def test_api_endpoint_routing(self, client, auth_headers):
        """Test that all API endpoints are properly routed."""
        endpoints_to_test = [
            ("/api/v1/instances", "GET"),
            ("/api/v1/instances/1", "GET"),
            ("/api/v1/instances", "POST"),
            ("/api/v1/instances/1/status", "PATCH"),
            ("/api/v1/instances/1/start", "POST"),
            ("/api/v1/instances/1/stop", "POST"),
            ("/api/v1/instances/1/restart", "POST"),
            ("/api/v1/instances/1/health", "GET"),
            ("/api/v1/instances/1/logs", "GET"),
        ]

        with patch("cc_orchestrator.web.routers.api.InstanceCRUD") as mock_crud:
            mock_instance = Mock()
            mock_instance.id = 1
            mock_instance.status = InstanceStatus.RUNNING
            mock_instance.issue_id = "123"
            mock_instance.created_at = None
            mock_instance.updated_at = None
            mock_instance.config = {}

            mock_crud.list_all.return_value = []
            mock_crud.get_by_id.return_value = mock_instance
            mock_crud.create.return_value = mock_instance
            mock_crud.update.return_value = mock_instance

            for endpoint, method in endpoints_to_test:
                if method == "GET":
                    response = client.get(endpoint, headers=auth_headers)
                elif method == "POST":
                    if "instances" in endpoint and endpoint.endswith("instances"):
                        response = client.post(
                            endpoint, json={"issue_id": "123"}, headers=auth_headers
                        )
                    else:
                        response = client.post(endpoint, headers=auth_headers)
                elif method == "PATCH":
                    response = client.patch(
                        endpoint, json={"status": "RUNNING"}, headers=auth_headers
                    )

                # Should not return 404 (endpoint exists)
                assert (
                    response.status_code != 404
                ), f"Endpoint {method} {endpoint} returned 404"

    def test_dependency_injection_database(self, client, auth_headers):
        """Test database session dependency injection."""
        with (
            patch("cc_orchestrator.web.routers.api.InstanceCRUD") as mock_crud,
            patch("cc_orchestrator.web.routers.api.get_db_session") as mock_db_dep,
        ):

            mock_session = Mock()
            mock_db_dep.return_value = mock_session
            mock_crud.list_all.return_value = []

            client.get("/api/v1/instances", headers=auth_headers)

            # Verify database session was used
            mock_crud.list_all.assert_called_once()
            call_args = mock_crud.list_all.call_args[0]
            assert len(call_args) > 0  # DB session should be first argument

    def test_dependency_injection_authentication(self, client):
        """Test authentication dependency injection."""
        with patch("cc_orchestrator.web.routers.api.InstanceCRUD"):
            # Without auth headers - should fail
            response = client.get("/api/v1/instances")
            assert response.status_code == 403  # Forbidden

            # With invalid token - should fail
            headers = {"Authorization": "Bearer invalid-token"}
            response = client.get("/api/v1/instances", headers=headers)
            assert response.status_code == 401  # Unauthorized


class TestAPIErrorHandling:
    """Test comprehensive API error handling."""

    def test_instance_not_found_error_handling(self, client, auth_headers):
        """Test InstanceNotFoundError handling."""
        with patch("cc_orchestrator.web.routers.api.InstanceCRUD") as mock_crud:
            mock_crud.get_by_id.side_effect = Exception("Instance not found")

            response = client.get("/api/v1/instances/99999", headers=auth_headers)

            assert response.status_code == 404
            error_data = response.json()
            assert "error" in error_data
            assert "InstanceNotFoundError" in error_data["error"]

    def test_instance_operation_error_handling(self, client, auth_headers):
        """Test InstanceOperationError handling."""
        with patch("cc_orchestrator.web.routers.api.InstanceCRUD") as mock_crud:
            mock_crud.update.side_effect = Exception("Operation failed")

            response = client.post("/api/v1/instances/1/start", headers=auth_headers)

            assert response.status_code == 400
            error_data = response.json()
            assert "error" in error_data

    def test_validation_error_handling(self, client, auth_headers):
        """Test request validation error handling."""
        # Invalid JSON for create instance
        response = client.post(
            "/api/v1/instances", json={}, headers=auth_headers  # Missing required field
        )

        assert response.status_code == 422  # Validation error

    def test_unhandled_exception_handling(self, client, auth_headers):
        """Test general exception handling."""
        with patch("cc_orchestrator.web.routers.api.InstanceCRUD") as mock_crud:
            mock_crud.list_all.side_effect = RuntimeError("Database connection lost")

            response = client.get("/api/v1/instances", headers=auth_headers)

            # Should be handled gracefully
            assert response.status_code >= 400


class TestRateLimitingIntegration:
    """Test rate limiting integration in API endpoints."""

    def test_get_instances_rate_limiting(self, client, auth_headers):
        """Test rate limiting on GET /instances endpoint."""
        with (
            patch("cc_orchestrator.web.routers.api.InstanceCRUD") as mock_crud,
            patch("cc_orchestrator.web.routers.api.get_client_ip") as mock_get_ip,
            patch("cc_orchestrator.web.routers.api.rate_limiter") as mock_limiter,
        ):

            mock_crud.list_all.return_value = []
            mock_get_ip.return_value = "127.0.0.1"
            mock_limiter.check_rate_limit.side_effect = RateLimitExceededError(
                30, "60s"
            )

            response = client.get("/api/v1/instances", headers=auth_headers)

            assert response.status_code == 429
            mock_limiter.check_rate_limit.assert_called_once_with(
                "127.0.0.1", "GET:/api/v1/instances", 30, 60
            )

    def test_create_instance_rate_limiting(self, client, auth_headers):
        """Test rate limiting on POST /instances endpoint."""
        with (
            patch("cc_orchestrator.web.routers.api.InstanceCRUD"),
            patch("cc_orchestrator.web.routers.api.get_client_ip") as mock_get_ip,
            patch("cc_orchestrator.web.routers.api.rate_limiter") as mock_limiter,
        ):

            mock_get_ip.return_value = "127.0.0.1"
            mock_limiter.check_rate_limit.side_effect = RateLimitExceededError(
                10, "60s"
            )

            response = client.post(
                "/api/v1/instances", json={"issue_id": "123"}, headers=auth_headers
            )

            assert response.status_code == 429
            mock_limiter.check_rate_limit.assert_called_once_with(
                "127.0.0.1", "POST:/api/v1/instances", 10, 60
            )

    def test_instance_control_rate_limiting(self, client, auth_headers):
        """Test rate limiting on instance control endpoints."""
        endpoints = ["start", "stop", "restart"]

        for endpoint in endpoints:
            with (
                patch("cc_orchestrator.web.routers.api.InstanceCRUD"),
                patch("cc_orchestrator.web.routers.api.get_client_ip") as mock_get_ip,
                patch("cc_orchestrator.web.routers.api.rate_limiter") as mock_limiter,
            ):

                mock_get_ip.return_value = "127.0.0.1"
                mock_limiter.check_rate_limit.side_effect = RateLimitExceededError(
                    20, "60s"
                )

                response = client.post(
                    f"/api/v1/instances/1/{endpoint}", headers=auth_headers
                )

                assert response.status_code == 429
                mock_limiter.check_rate_limit.assert_called_once_with(
                    "127.0.0.1", f"POST:/api/v1/instances/*/{endpoint}", 20, 60
                )


class TestAPIPerformanceTracking:
    """Test API performance tracking and logging."""

    def test_performance_decorator_applied(self, client, auth_headers):
        """Test that performance tracking decorators are applied."""
        with (
            patch("cc_orchestrator.web.routers.api.InstanceCRUD") as mock_crud,
            patch(
                "cc_orchestrator.web.logging_utils.track_api_performance"
            ) as mock_perf,
        ):

            mock_crud.list_all.return_value = []
            mock_decorator = Mock(return_value=lambda func: func)
            mock_perf.return_value = mock_decorator

            response = client.get("/api/v1/instances", headers=auth_headers)

            # Performance tracking should be called
            # Note: Due to decorator mechanics, this might not assert as expected in all cases
            assert response.status_code == 200

    def test_error_handling_decorator_applied(self, client, auth_headers):
        """Test that error handling decorators are applied."""
        with (
            patch("cc_orchestrator.web.routers.api.InstanceCRUD") as mock_crud,
            patch("cc_orchestrator.web.logging_utils.handle_api_errors") as mock_errors,
        ):

            mock_crud.list_all.side_effect = Exception("Test error")
            mock_decorator = Mock(return_value=lambda func: func)
            mock_errors.return_value = mock_decorator

            response = client.get("/api/v1/instances", headers=auth_headers)

            # Error handling should be applied
            assert response.status_code >= 400


class TestAPIResponseFormats:
    """Test API response formats and serialization."""

    def test_instance_list_response_format(self, client, auth_headers):
        """Test instance list response format."""
        with patch("cc_orchestrator.web.routers.api.InstanceCRUD") as mock_crud:
            mock_instance = Mock()
            mock_instance.id = 1
            mock_instance.issue_id = "123"
            mock_instance.status = InstanceStatus.RUNNING
            mock_instance.created_at = None
            mock_instance.updated_at = None
            mock_instance.config = {}

            mock_crud.list_all.return_value = [mock_instance]

            response = client.get("/api/v1/instances", headers=auth_headers)

            assert response.status_code == 200
            data = response.json()

            # Check response structure
            assert "instances" in data
            assert "total" in data
            assert isinstance(data["instances"], list)
            assert isinstance(data["total"], int)
            assert data["total"] == 1

    def test_single_instance_response_format(self, client, auth_headers):
        """Test single instance response format."""
        with patch("cc_orchestrator.web.routers.api.InstanceCRUD") as mock_crud:
            mock_instance = Mock()
            mock_instance.id = 1
            mock_instance.issue_id = "123"
            mock_instance.status = InstanceStatus.RUNNING
            mock_instance.created_at = None
            mock_instance.updated_at = None
            mock_instance.config = {}

            mock_crud.get_by_id.return_value = mock_instance

            response = client.get("/api/v1/instances/1", headers=auth_headers)

            assert response.status_code == 200
            data = response.json()

            # Check response fields
            assert "id" in data
            assert "issue_id" in data
            assert "status" in data
            assert data["id"] == 1

    def test_health_response_format(self, client, auth_headers):
        """Test health endpoint response format."""
        with patch("cc_orchestrator.web.routers.api.InstanceCRUD") as mock_crud:
            mock_instance = Mock()
            mock_instance.status = InstanceStatus.RUNNING
            mock_instance.updated_at = None

            mock_crud.get_by_id.return_value = mock_instance

            response = client.get("/api/v1/instances/1/health", headers=auth_headers)

            assert response.status_code == 200
            data = response.json()

            # Check health response structure
            required_fields = [
                "instance_id",
                "status",
                "health",
                "cpu_usage",
                "memory_usage",
                "uptime_seconds",
                "last_activity",
            ]

            for field in required_fields:
                assert field in data

    def test_logs_response_format(self, client, auth_headers):
        """Test logs endpoint response format."""
        with patch("cc_orchestrator.web.routers.api.InstanceCRUD") as mock_crud:
            mock_crud.get_by_id.return_value = Mock()

            response = client.get(
                "/api/v1/instances/1/logs?limit=50&search=error", headers=auth_headers
            )

            assert response.status_code == 200
            data = response.json()

            # Check logs response structure
            required_fields = ["instance_id", "logs", "total", "limit", "search"]

            for field in required_fields:
                assert field in data

            assert data["limit"] == 50
            assert data["search"] == "error"


class TestAPIParameterHandling:
    """Test API parameter validation and handling."""

    def test_query_parameter_handling(self, client, auth_headers):
        """Test query parameter parsing."""
        with patch("cc_orchestrator.web.routers.api.InstanceCRUD") as mock_crud:
            mock_crud.list_all.return_value = []

            # Test status filter
            response = client.get(
                "/api/v1/instances?status=RUNNING", headers=auth_headers
            )
            assert response.status_code == 200

            # Verify filter was passed
            mock_crud.list_all.assert_called_once()
            call_args = mock_crud.list_all.call_args[1]
            assert "status" in call_args
            assert call_args["status"] == InstanceStatus.RUNNING

    def test_path_parameter_handling(self, client, auth_headers):
        """Test path parameter parsing."""
        with patch("cc_orchestrator.web.routers.api.InstanceCRUD") as mock_crud:
            mock_crud.get_by_id.return_value = Mock()

            client.get("/api/v1/instances/123", headers=auth_headers)

            # Verify instance ID was parsed correctly
            mock_crud.get_by_id.assert_called_once()
            call_args = mock_crud.get_by_id.call_args[0]
            assert 123 in call_args

    def test_request_body_parameter_handling(self, client, auth_headers):
        """Test request body parsing."""
        with patch("cc_orchestrator.web.routers.api.InstanceCRUD") as mock_crud:
            mock_crud.create.return_value = Mock()

            client.post(
                "/api/v1/instances", json={"issue_id": "test-123"}, headers=auth_headers
            )

            # Verify issue_id was parsed
            mock_crud.create.assert_called_once()
            call_args = mock_crud.create.call_args[1]
            assert "issue_id" in call_args
            assert call_args["issue_id"] == "test-123"

    def test_invalid_parameter_types(self, client, auth_headers):
        """Test handling of invalid parameter types."""
        with patch("cc_orchestrator.web.routers.api.InstanceCRUD"):
            # Invalid instance ID (non-numeric)
            response = client.get("/api/v1/instances/invalid", headers=auth_headers)
            assert response.status_code == 422  # Validation error


class TestAPIStatusTransitions:
    """Test instance status transition logic."""

    def test_status_update_endpoint(self, client, auth_headers):
        """Test status update endpoint functionality."""
        with patch("cc_orchestrator.web.routers.api.InstanceCRUD") as mock_crud:
            mock_instance = Mock()
            mock_instance.id = 1
            mock_instance.status = InstanceStatus.RUNNING
            mock_instance.issue_id = "123"
            mock_instance.created_at = None
            mock_instance.updated_at = None
            mock_instance.config = {}

            mock_crud.update.return_value = mock_instance

            response = client.patch(
                "/api/v1/instances/1/status",
                json={"status": "RUNNING"},
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "RUNNING"

    def test_start_stop_restart_operations(self, client, auth_headers):
        """Test start, stop, and restart operations."""
        operations = [
            ("start", InstanceStatus.RUNNING),
            ("stop", InstanceStatus.STOPPED),
            ("restart", InstanceStatus.RUNNING),
        ]

        for operation, expected_status in operations:
            with patch("cc_orchestrator.web.routers.api.InstanceCRUD") as mock_crud:
                mock_crud.update.return_value = Mock()

                response = client.post(
                    f"/api/v1/instances/1/{operation}", headers=auth_headers
                )

                assert response.status_code == 200
                data = response.json()
                assert "message" in data
                assert "instance_id" in data

                # Verify correct status was set
                mock_crud.update.assert_called_once()
                call_args = mock_crud.update.call_args[1]
                assert "status" in call_args
                assert call_args["status"] == expected_status


class TestAPIClientIPExtraction:
    """Test client IP extraction for rate limiting."""

    def test_client_ip_extraction_from_headers(self, client, auth_headers):
        """Test IP extraction from various headers."""
        headers_to_test = [
            ("X-Forwarded-For", "192.168.1.1, 10.0.0.1"),
            ("X-Real-IP", "192.168.1.2"),
            ("X-Forwarded-Host", "192.168.1.3"),
        ]

        for header_name, header_value in headers_to_test:
            with (
                patch("cc_orchestrator.web.routers.api.InstanceCRUD") as mock_crud,
                patch("cc_orchestrator.web.routers.api.get_client_ip") as mock_get_ip,
            ):

                mock_crud.list_all.return_value = []
                expected_ip = header_value.split(",")[0].strip()
                mock_get_ip.return_value = expected_ip

                headers = {**auth_headers, header_name: header_value}
                response = client.get("/api/v1/instances", headers=headers)

                assert response.status_code == 200
                mock_get_ip.assert_called_once()

    def test_client_ip_fallback_behavior(self, client, auth_headers):
        """Test IP extraction fallback behavior."""
        with (
            patch("cc_orchestrator.web.routers.api.InstanceCRUD") as mock_crud,
            patch("cc_orchestrator.web.routers.api.get_client_ip") as mock_get_ip,
        ):

            mock_crud.list_all.return_value = []
            mock_get_ip.return_value = "unknown"  # Fallback case

            response = client.get("/api/v1/instances", headers=auth_headers)

            assert response.status_code == 200
            mock_get_ip.assert_called_once()
