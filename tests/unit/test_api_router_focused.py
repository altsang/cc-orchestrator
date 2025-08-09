"""Focused tests for API router to improve coverage."""

import os
from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient


@pytest.fixture
def mock_auth():
    """Mock authentication for tests."""
    with patch("cc_orchestrator.web.routers.api.get_current_user") as mock:
        mock.return_value = {"sub": "testuser", "role": "admin"}
        yield mock


@pytest.fixture
def mock_db():
    """Mock database session."""
    with patch("cc_orchestrator.web.routers.api.get_db_session") as mock:
        session = Mock()
        mock.return_value = session
        yield session


@pytest.fixture
def mock_crud():
    """Mock CRUD operations."""
    with patch("cc_orchestrator.web.routers.api.InstanceCRUD") as mock:
        yield mock


@pytest.fixture
def client():
    """Test client with environment setup."""
    with patch.dict(
        os.environ,
        {
            "JWT_SECRET_KEY": "test-secret-key-for-testing",
            "ENABLE_DEMO_USERS": "true",
            "DEBUG": "true",
        },
    ):
        from cc_orchestrator.web.app import create_app

        app = create_app()
        with TestClient(app) as client:
            yield client


@pytest.fixture
def auth_headers():
    """Authentication headers for requests."""
    with patch.dict(
        os.environ,
        {"JWT_SECRET_KEY": "test-secret-key-for-testing", "ENABLE_DEMO_USERS": "true"},
    ):
        import importlib

        from cc_orchestrator.web import auth

        importlib.reload(auth)

        token = auth.create_access_token({"sub": "testuser", "role": "admin"})
        return {"Authorization": f"Bearer {token}"}


class TestInstanceListEndpoint:
    """Test the GET /instances endpoint."""

    def test_get_instances_success(
        self, client, mock_auth, mock_db, mock_crud, auth_headers
    ):
        """Test successful instances retrieval."""
        # Mock successful response
        mock_crud.list_all.return_value = []

        response = client.get("/api/v1/instances", headers=auth_headers)
        assert response.status_code == 200

        data = response.json()
        assert "instances" in data
        assert "total" in data
        assert data["total"] == 0

    def test_get_instances_with_filter(
        self, client, mock_auth, mock_db, mock_crud, auth_headers
    ):
        """Test instances retrieval with status filter."""
        mock_crud.list_by_status.return_value = []
        mock_crud.count_by_status.return_value = 0

        response = client.get(
            "/api/v1/instances?status_filter=running", headers=auth_headers
        )
        assert response.status_code == 200

        mock_crud.list_by_status.assert_called_once_with("running", skip=0, limit=100)

    def test_get_instances_pagination(
        self, client, mock_auth, mock_db, mock_crud, auth_headers
    ):
        """Test instances retrieval with pagination."""
        mock_crud.list_all.return_value = []
        mock_crud.count.return_value = 0

        response = client.get("/api/v1/instances?skip=10&limit=5", headers=auth_headers)
        assert response.status_code == 200

        mock_crud.list_all.assert_called_once_with(skip=10, limit=5)

    def test_get_instances_unauthorized(self, client):
        """Test instances retrieval without authentication."""
        response = client.get("/api/v1/instances")
        assert response.status_code == 403


class TestInstanceCreateEndpoint:
    """Test the POST /instances endpoint."""

    def test_create_instance_success(
        self, client, mock_auth, mock_db, mock_crud, auth_headers
    ):
        """Test successful instance creation."""
        # Mock successful creation
        mock_instance = Mock()
        mock_instance.id = 1
        mock_instance.issue_id = "123"
        mock_instance.status = "initializing"
        mock_crud.create.return_value = mock_instance

        data = {"issue_id": "123", "status": "initializing"}
        response = client.post("/api/v1/instances", json=data, headers=auth_headers)
        assert response.status_code == 201

        mock_crud.create.assert_called_once()

    def test_create_instance_validation_error(
        self, client, mock_auth, mock_db, mock_crud, auth_headers
    ):
        """Test instance creation with invalid data."""
        data = {}  # Missing required fields
        response = client.post("/api/v1/instances", json=data, headers=auth_headers)
        assert response.status_code == 422

    def test_create_instance_duplicate(
        self, client, mock_auth, mock_db, mock_crud, auth_headers
    ):
        """Test instance creation with duplicate issue_id."""
        mock_crud.create.side_effect = HTTPException(
            status_code=409, detail="Instance already exists"
        )

        data = {"issue_id": "123", "status": "initializing"}
        response = client.post("/api/v1/instances", json=data, headers=auth_headers)
        assert response.status_code == 409


class TestInstanceDetailEndpoint:
    """Test the GET /instances/{instance_id} endpoint."""

    def test_get_instance_success(
        self, client, mock_auth, mock_db, mock_crud, auth_headers
    ):
        """Test successful instance retrieval."""
        mock_instance = Mock()
        mock_instance.id = 1
        mock_instance.issue_id = "123"
        mock_instance.status = "running"
        mock_crud.get_by_id.return_value = mock_instance

        response = client.get("/api/v1/instances/1", headers=auth_headers)
        assert response.status_code == 200

        mock_crud.get_by_id.assert_called_once_with(1)

    def test_get_instance_not_found(
        self, client, mock_auth, mock_db, mock_crud, auth_headers
    ):
        """Test instance retrieval when not found."""
        mock_crud.get_by_id.return_value = None

        response = client.get("/api/v1/instances/999", headers=auth_headers)
        assert response.status_code == 404

    def test_get_instance_by_issue_id(
        self, client, mock_auth, mock_db, mock_crud, auth_headers
    ):
        """Test instance retrieval by issue ID."""
        mock_instance = Mock()
        mock_instance.issue_id = "123"
        mock_crud.get_by_issue_id.return_value = mock_instance

        response = client.get("/api/v1/instances/issue-123", headers=auth_headers)
        assert response.status_code == 200

        mock_crud.get_by_issue_id.assert_called_once_with("123")


class TestInstanceUpdateEndpoint:
    """Test the PATCH /instances/{instance_id} endpoint."""

    def test_update_instance_success(
        self, client, mock_auth, mock_db, mock_crud, auth_headers
    ):
        """Test successful instance update."""
        mock_instance = Mock()
        mock_instance.id = 1
        mock_instance.status = "stopped"
        mock_crud.get_by_id.return_value = mock_instance
        mock_crud.update.return_value = mock_instance

        data = {"status": "stopped"}
        response = client.patch(
            "/api/v1/instances/1/status", json=data, headers=auth_headers
        )
        assert response.status_code == 200

        mock_crud.update.assert_called()

    def test_update_instance_not_found(
        self, client, mock_auth, mock_db, mock_crud, auth_headers
    ):
        """Test instance update when not found."""
        mock_crud.get_by_id.return_value = None

        data = {"status": "stopped"}
        response = client.patch(
            "/api/v1/instances/999/status", json=data, headers=auth_headers
        )
        assert response.status_code == 404

    def test_update_instance_invalid_status(
        self, client, mock_auth, mock_db, mock_crud, auth_headers
    ):
        """Test instance update with invalid status."""
        data = {"status": "invalid-status"}
        response = client.patch(
            "/api/v1/instances/1/status", json=data, headers=auth_headers
        )
        assert response.status_code == 422


class TestInstanceDeleteEndpoint:
    """Test the DELETE /instances/{instance_id} endpoint."""

    def test_delete_instance_success(
        self, client, mock_auth, mock_db, mock_crud, auth_headers
    ):
        """Test successful instance deletion."""
        mock_instance = Mock()
        mock_instance.id = 1
        mock_crud.get_by_id.return_value = mock_instance
        mock_crud.delete.return_value = True

        response = client.delete("/api/v1/instances/1", headers=auth_headers)
        assert response.status_code == 204

        mock_crud.delete.assert_called_once_with(1)

    def test_delete_instance_not_found(
        self, client, mock_auth, mock_db, mock_crud, auth_headers
    ):
        """Test instance deletion when not found."""
        mock_crud.get_by_id.return_value = None

        response = client.delete("/api/v1/instances/999", headers=auth_headers)
        assert response.status_code == 404


class TestInstanceActionEndpoints:
    """Test instance action endpoints (start, stop, restart)."""

    def test_start_instance_success(
        self, client, mock_auth, mock_db, mock_crud, auth_headers
    ):
        """Test successful instance start."""
        mock_instance = Mock()
        mock_instance.id = 1
        mock_instance.status = "stopped"
        mock_crud.get_by_id.return_value = mock_instance
        mock_crud.update.return_value = mock_instance

        response = client.post("/api/v1/instances/1/start", headers=auth_headers)
        assert response.status_code == 200

        mock_crud.update.assert_called()

    def test_stop_instance_success(
        self, client, mock_auth, mock_db, mock_crud, auth_headers
    ):
        """Test successful instance stop."""
        mock_instance = Mock()
        mock_instance.id = 1
        mock_instance.status = "running"
        mock_crud.get_by_id.return_value = mock_instance
        mock_crud.update.return_value = mock_instance

        response = client.post("/api/v1/instances/1/stop", headers=auth_headers)
        assert response.status_code == 200

        mock_crud.update.assert_called()

    def test_restart_instance_success(
        self, client, mock_auth, mock_db, mock_crud, auth_headers
    ):
        """Test successful instance restart."""
        mock_instance = Mock()
        mock_instance.id = 1
        mock_crud.get_by_id.return_value = mock_instance
        mock_crud.update.return_value = mock_instance

        response = client.post("/api/v1/instances/1/restart", headers=auth_headers)
        assert response.status_code == 200


class TestInstanceMetricsEndpoint:
    """Test instance metrics and logs endpoints."""

    def test_get_instance_logs_success(
        self, client, mock_auth, mock_db, mock_crud, auth_headers
    ):
        """Test successful instance logs retrieval."""
        mock_instance = Mock()
        mock_instance.id = 1
        mock_crud.get_by_id.return_value = mock_instance

        with patch("cc_orchestrator.web.routers.api.get_instance_logs") as mock_logs:
            mock_logs.return_value = ([], 0)  # logs, total

            response = client.get("/api/v1/instances/1/logs", headers=auth_headers)
            assert response.status_code == 200

            data = response.json()
            assert "logs" in data
            assert "total" in data

    def test_get_instance_logs_with_search(
        self, client, mock_auth, mock_db, mock_crud, auth_headers
    ):
        """Test instance logs retrieval with search."""
        mock_instance = Mock()
        mock_instance.id = 1
        mock_crud.get_by_id.return_value = mock_instance

        with patch("cc_orchestrator.web.routers.api.get_instance_logs") as mock_logs:
            mock_logs.return_value = ([], 0)

            response = client.get(
                "/api/v1/instances/1/logs?search=error", headers=auth_headers
            )
            assert response.status_code == 200

            mock_logs.assert_called_once_with(1, limit=100, search="error")

    def test_get_instance_metrics_success(
        self, client, mock_auth, mock_db, mock_crud, auth_headers
    ):
        """Test successful instance metrics retrieval."""
        mock_instance = Mock()
        mock_instance.id = 1
        mock_crud.get_by_id.return_value = mock_instance

        with patch(
            "cc_orchestrator.web.routers.api.get_instance_metrics"
        ) as mock_metrics:
            mock_metrics.return_value = {
                "cpu_usage": 45.5,
                "memory_usage": 67.2,
                "disk_usage": 80.1,
            }

            response = client.get("/api/v1/instances/1/metrics", headers=auth_headers)
            assert response.status_code == 200

            data = response.json()
            assert "cpu_usage" in data
            assert "memory_usage" in data


class TestErrorHandling:
    """Test error handling in API endpoints."""

    def test_database_error_handling(
        self, client, mock_auth, mock_db, mock_crud, auth_headers
    ):
        """Test database error handling."""
        mock_crud.list_all.side_effect = Exception("Database connection error")

        response = client.get("/api/v1/instances", headers=auth_headers)
        # Should return 500 error due to unhandled exception
        assert response.status_code == 500

    def test_validation_error_handling(
        self, client, mock_auth, mock_db, mock_crud, auth_headers
    ):
        """Test validation error handling."""
        # Send invalid JSON
        response = client.post(
            "/api/v1/instances",
            data="invalid json",
            headers={**auth_headers, "Content-Type": "application/json"},
        )
        assert response.status_code == 422

    def test_rate_limiting_behavior(
        self, client, mock_auth, mock_db, mock_crud, auth_headers
    ):
        """Test that endpoints work under normal load."""
        mock_crud.list_all.return_value = []
        mock_crud.count.return_value = 0

        # Make several requests
        for _ in range(5):
            response = client.get("/api/v1/instances", headers=auth_headers)
            assert response.status_code == 200
