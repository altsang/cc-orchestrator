"""Fixed tests for web API endpoints."""

from datetime import UTC, datetime
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from cc_orchestrator.database.connection import Base, get_db_session
from cc_orchestrator.database.models import InstanceStatus
from cc_orchestrator.web.app import create_app
from cc_orchestrator.web.auth import create_access_token


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


class TestAPIEndpointsFixed:
    """Test API endpoints with proper mocking."""

    @patch("cc_orchestrator.web.routers.api.InstanceCRUD")
    def test_get_instances_working(self, mock_crud, client, auth_headers):
        """Test getting instances with proper mocking."""
        # Mock the database response
        mock_instance = Mock()
        mock_instance.id = 1
        mock_instance.issue_id = "123"
        mock_instance.status = InstanceStatus.RUNNING
        mock_instance.created_at = datetime.now(UTC)
        mock_instance.updated_at = datetime.now(UTC)
        mock_instance.config = {}

        mock_crud.list_all.return_value = [mock_instance]

        response = client.get("/api/v1/instances", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "instances" in data
        assert data["total"] == 1
        assert data["instances"][0]["id"] == 1

    @patch("cc_orchestrator.web.routers.api.InstanceCRUD")
    def test_get_instance_by_id_working(self, mock_crud, client, auth_headers):
        """Test getting specific instance."""
        mock_instance = Mock()
        mock_instance.id = 1
        mock_instance.issue_id = "123"
        mock_instance.status = InstanceStatus.RUNNING
        mock_instance.created_at = datetime.now(UTC)
        mock_instance.updated_at = datetime.now(UTC)
        mock_instance.config = {}

        mock_crud.get_by_id.return_value = mock_instance

        response = client.get("/api/v1/instances/1", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 1

    @patch("cc_orchestrator.web.routers.api.InstanceCRUD")
    def test_create_instance_working(self, mock_crud, client, auth_headers):
        """Test creating instance."""
        mock_instance = Mock()
        mock_instance.id = 1
        mock_instance.issue_id = "123"
        mock_instance.status = InstanceStatus.INITIALIZING
        mock_instance.created_at = datetime.now(UTC)
        mock_instance.updated_at = datetime.now(UTC)
        mock_instance.config = {}

        mock_crud.create.return_value = mock_instance

        response = client.post(
            "/api/v1/instances", json={"issue_id": "123"}, headers=auth_headers
        )

        assert response.status_code == 201
        data = response.json()
        assert data["issue_id"] == "123"

    @patch("cc_orchestrator.web.routers.api.InstanceCRUD")
    def test_start_instance_working(self, mock_crud, client, auth_headers):
        """Test starting instance."""
        mock_crud.update.return_value = Mock()

        response = client.post("/api/v1/instances/1/start", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "instance_id" in data

    @patch("cc_orchestrator.web.routers.api.InstanceCRUD")
    def test_stop_instance_working(self, mock_crud, client, auth_headers):
        """Test stopping instance."""
        mock_crud.update.return_value = Mock()

        response = client.post("/api/v1/instances/1/stop", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "message" in data

    @patch("cc_orchestrator.web.routers.api.InstanceCRUD")
    def test_restart_instance_working(self, mock_crud, client, auth_headers):
        """Test restarting instance."""
        mock_crud.update.return_value = Mock()

        response = client.post("/api/v1/instances/1/restart", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "message" in data

    @patch("cc_orchestrator.web.routers.api.InstanceCRUD")
    def test_get_instance_health_working(self, mock_crud, client, auth_headers):
        """Test getting instance health."""
        mock_instance = Mock()
        mock_instance.status = InstanceStatus.RUNNING
        mock_instance.updated_at = datetime.now(UTC)

        mock_crud.get_by_id.return_value = mock_instance

        response = client.get("/api/v1/instances/1/health", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "instance_id" in data
        assert "health" in data

    @patch("cc_orchestrator.web.routers.api.InstanceCRUD")
    def test_get_instance_logs_working(self, mock_crud, client, auth_headers):
        """Test getting instance logs."""
        mock_crud.get_by_id.return_value = Mock()

        response = client.get("/api/v1/instances/1/logs", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "logs" in data
        assert "total" in data

    @patch("cc_orchestrator.web.routers.api.InstanceCRUD")
    def test_instance_not_found_error(self, mock_crud, client, auth_headers):
        """Test instance not found error."""
        mock_crud.get_by_id.side_effect = Exception("Not found")

        response = client.get("/api/v1/instances/99999", headers=auth_headers)

        assert response.status_code == 404
        error_data = response.json()
        assert "error" in error_data

    @patch("cc_orchestrator.web.routers.api.InstanceCRUD")
    def test_instance_operation_error(self, mock_crud, client, auth_headers):
        """Test instance operation error."""
        mock_crud.update.side_effect = Exception("Operation failed")

        response = client.post("/api/v1/instances/1/start", headers=auth_headers)

        assert response.status_code == 400
        error_data = response.json()
        assert "error" in error_data

    def test_update_instance_status(self, client, auth_headers):
        """Test updating instance status."""
        with patch("cc_orchestrator.web.routers.api.InstanceCRUD") as mock_crud:
            mock_instance = Mock()
            mock_instance.id = 1
            mock_instance.status = InstanceStatus.RUNNING
            mock_instance.created_at = datetime.now(UTC)
            mock_instance.updated_at = datetime.now(UTC)
            mock_instance.issue_id = "123"
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

    def test_rate_limiting_triggered(self, client, auth_headers):
        """Test rate limiting functionality."""
        with patch("cc_orchestrator.web.routers.api.InstanceCRUD") as mock_crud:
            mock_crud.list_all.return_value = []

            # Make many requests rapidly
            responses = []
            for _ in range(35):  # More than 30/min limit
                response = client.get("/api/v1/instances", headers=auth_headers)
                responses.append(response)

            # Should have some rate limited responses
            rate_limited = [r for r in responses if r.status_code == 429]
            assert len(rate_limited) > 0, "Rate limiting should be triggered"

    def test_get_instances_with_status_filter(self, client, auth_headers):
        """Test getting instances with status filter."""
        with patch("cc_orchestrator.web.routers.api.InstanceCRUD") as mock_crud:
            mock_crud.list_all.return_value = []

            response = client.get(
                "/api/v1/instances?status=RUNNING", headers=auth_headers
            )

            assert response.status_code == 200
            # Verify the filter was passed
            mock_crud.list_all.assert_called_with(
                mock_crud.list_all.call_args[0][0], status=InstanceStatus.RUNNING
            )

    def test_get_logs_with_parameters(self, client, auth_headers):
        """Test getting logs with query parameters."""
        with patch("cc_orchestrator.web.routers.api.InstanceCRUD") as mock_crud:
            mock_crud.get_by_id.return_value = Mock()

            response = client.get(
                "/api/v1/instances/1/logs?limit=50&search=error", headers=auth_headers
            )

            assert response.status_code == 200
            data = response.json()
            assert data["limit"] == 50
            assert data["search"] == "error"
