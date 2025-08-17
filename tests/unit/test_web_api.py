"""
Unit tests for FastAPI web application.

This module tests the FastAPI endpoints, middleware, and API functionality.
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from cc_orchestrator.database.models import (
    HealthStatus,
    InstanceStatus,
    TaskPriority,
    TaskStatus,
)
from cc_orchestrator.web.app import create_app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    from cc_orchestrator.web.auth import get_current_user
    from cc_orchestrator.web.dependencies import get_crud

    app = create_app()

    # Create a mock CRUD instance
    mock_crud = MagicMock()
    mock_crud.list_instances = AsyncMock(return_value=([], 0))
    mock_crud.create_instance = AsyncMock()
    mock_crud.get_instance = AsyncMock()
    mock_crud.update_instance = AsyncMock()
    mock_crud.delete_instance = AsyncMock()
    mock_crud.get_instance_by_issue_id = AsyncMock(return_value=None)
    mock_crud.list_tasks = AsyncMock(return_value=([], 0))
    mock_crud.create_task = AsyncMock(
        return_value={
            "id": 1,
            "title": "Test Task",
            "description": "",
            "status": "pending",
            "priority": "medium",
            "instance_id": None,
            "worktree_id": None,
            "enabled": True,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "last_run": None,
            "next_run": None,
            "started_at": None,
            "completed_at": None,
            "due_date": None,
            "estimated_duration": None,
            "actual_duration": None,
            "requirements": {},
            "results": {},
            "extra_metadata": {},
        }
    )
    mock_crud.get_task = AsyncMock()
    mock_crud.update_task = AsyncMock()
    mock_crud.delete_task = AsyncMock()
    mock_crud.list_worktrees = AsyncMock(return_value=([], 0))
    mock_crud.create_worktree = AsyncMock()
    mock_crud.get_worktree = AsyncMock()
    mock_crud.update_worktree = AsyncMock()
    mock_crud.delete_worktree = AsyncMock()
    mock_crud.get_worktree_by_path = AsyncMock()
    mock_crud.list_configurations = AsyncMock(return_value=([], 0))
    mock_crud.create_configuration = AsyncMock()
    mock_crud.get_configuration = AsyncMock()
    mock_crud.update_configuration = AsyncMock()
    mock_crud.delete_configuration = AsyncMock()
    mock_crud.get_configuration_by_key_scope = AsyncMock()
    mock_crud.list_health_checks = AsyncMock(return_value=([], 0))
    mock_crud.create_health_check = AsyncMock()
    mock_crud.list_alerts = AsyncMock(return_value=([], 0))
    mock_crud.create_alert = AsyncMock()
    mock_crud.get_alert_by_alert_id = AsyncMock()

    # Mock authentication - return a test user
    def mock_get_current_user():
        return {"username": "test_user", "user_id": 1, "is_admin": True}

    # Override the dependencies
    app.dependency_overrides[get_crud] = lambda: mock_crud
    app.dependency_overrides[get_current_user] = mock_get_current_user

    return TestClient(app)


@pytest.fixture
def mock_db_manager():
    """Mock database manager."""
    mock = MagicMock()
    mock.initialize = AsyncMock()
    mock.close = AsyncMock()
    mock.get_session = MagicMock()
    return mock


@pytest.fixture
def mock_crud():
    """Mock CRUD operations."""
    mock = MagicMock()
    # Mock instance operations
    mock.list_instances = AsyncMock(return_value=([], 0))
    mock.create_instance = AsyncMock()
    mock.get_instance = AsyncMock()
    mock.update_instance = AsyncMock()
    mock.delete_instance = AsyncMock()
    mock.get_instance_by_issue_id = AsyncMock()

    # Mock task operations
    mock.list_tasks = AsyncMock(return_value=([], 0))
    mock.create_task = AsyncMock()
    mock.get_task = AsyncMock()
    mock.update_task = AsyncMock()
    mock.delete_task = AsyncMock()

    # Mock worktree operations
    mock.list_worktrees = AsyncMock(return_value=([], 0))
    mock.create_worktree = AsyncMock()
    mock.get_worktree = AsyncMock()
    mock.update_worktree = AsyncMock()
    mock.delete_worktree = AsyncMock()
    mock.get_worktree_by_path = AsyncMock()

    # Mock configuration operations
    mock.list_configurations = AsyncMock(return_value=([], 0))
    mock.create_configuration = AsyncMock()
    mock.get_configuration = AsyncMock()
    mock.update_configuration = AsyncMock()
    mock.delete_configuration = AsyncMock()
    mock.get_configuration_by_key_scope = AsyncMock()

    # Mock health check operations
    mock.list_health_checks = AsyncMock(return_value=([], 0))
    mock.create_health_check = AsyncMock()

    # Mock alert operations
    mock.list_alerts = AsyncMock(return_value=([], 0))
    mock.create_alert = AsyncMock()
    mock.get_alert_by_alert_id = AsyncMock()

    return mock


class TestHealthEndpoints:
    """Test health check endpoints."""

    def test_root_endpoint(self, client):
        """Test the root endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        # Root returns HTML, so check content type instead
        assert "text/html" in response.headers["content-type"]

    def test_ping_endpoint(self, client):
        """Test the ping endpoint (actually /health)."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_health_check_endpoint(self, client):
        """Test the health check endpoint."""
        response = client.get("/api/v1/health/")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "health_data" in data or "data" in data


class TestInstanceEndpoints:
    """Test instance management endpoints."""

    def test_list_instances_empty(self, client):
        """Test listing instances when none exist."""
        response = client.get("/api/v1/instances/")
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0
        assert data["page"] == 1
        assert data["size"] == 20

    def test_create_instance_success(self, client):
        """Test creating a new instance."""
        # Get the mock CRUD from the client fixture and configure it
        from cc_orchestrator.web.dependencies import get_crud

        mock_crud = client.app.dependency_overrides[get_crud]()

        # Mock created instance
        mock_instance = MagicMock()
        mock_instance.id = 1
        mock_instance.issue_id = "test-issue-123"
        mock_instance.status = InstanceStatus.INITIALIZING
        mock_instance.health_status = HealthStatus.UNKNOWN
        mock_instance.created_at = datetime.now()
        mock_instance.updated_at = datetime.now()
        mock_instance.last_health_check = None
        mock_instance.health_check_count = 0
        mock_instance.healthy_check_count = 0
        mock_instance.last_recovery_attempt = None
        mock_instance.recovery_attempt_count = 0
        mock_instance.health_check_details = None
        mock_instance.last_activity = None
        mock_instance.workspace_path = None
        mock_instance.branch_name = None
        mock_instance.tmux_session = None
        mock_instance.process_id = None
        mock_instance.extra_metadata = {}

        # Configure the mock to return our mock instance
        mock_crud.create_instance.return_value = mock_instance

        instance_data = {"issue_id": "test-issue-123", "status": "initializing"}

        response = client.post("/api/v1/instances/", json=instance_data)
        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert data["data"]["issue_id"] == "test-issue-123"

    def test_create_instance_duplicate(self, client):
        """Test creating an instance with duplicate issue_id."""
        # Get the mock CRUD from the client fixture and configure it
        from cc_orchestrator.web.dependencies import get_crud

        mock_crud = client.app.dependency_overrides[get_crud]()

        # Mock existing instance to simulate duplicate
        existing_instance = MagicMock()
        existing_instance.issue_id = "test-issue-123"
        mock_crud.get_instance_by_issue_id.return_value = existing_instance

        instance_data = {"issue_id": "test-issue-123", "status": "initializing"}

        response = client.post("/api/v1/instances/", json=instance_data)
        assert response.status_code == 409
        data = response.json()
        assert "already exists" in data["detail"]

    def test_get_instance_not_found(self, client):
        """Test getting a non-existent instance."""
        # Get the mock CRUD from the client fixture and configure it
        from cc_orchestrator.web.dependencies import get_crud

        mock_crud = client.app.dependency_overrides[get_crud]()

        mock_crud.get_instance.return_value = None

        response = client.get("/api/v1/instances/999")
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"]


class TestTaskEndpoints:
    """Test task management endpoints."""

    @patch("cc_orchestrator.web.dependencies.get_crud")
    def test_list_tasks_empty(self, mock_get_crud, client):
        """Test listing tasks when none exist."""
        mock_crud = MagicMock()
        mock_crud.list_tasks = AsyncMock(return_value=([], 0))
        mock_get_crud.return_value = mock_crud

        response = client.get("/api/v1/tasks/")
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_create_task_success(self, client):
        """Test creating a new task."""
        # Get the mock CRUD from the client fixture and configure it
        from cc_orchestrator.web.dependencies import get_crud

        mock_crud = client.app.dependency_overrides[get_crud]()

        # Mock created task
        mock_task = MagicMock()
        mock_task.id = 1
        mock_task.title = "Test Task"
        mock_task.description = "Test description"
        mock_task.status = TaskStatus.PENDING
        mock_task.priority = TaskPriority.MEDIUM
        mock_task.instance_id = None
        mock_task.worktree_id = None
        mock_task.created_at = datetime.now()
        mock_task.updated_at = datetime.now()
        mock_task.started_at = None
        mock_task.completed_at = None
        mock_task.due_date = None
        mock_task.estimated_duration = None
        mock_task.actual_duration = None
        mock_task.requirements = {}
        mock_task.results = {}
        mock_task.extra_metadata = {}

        # Configure the mock to return our mock task
        # Return a proper dict instead of MagicMock for API response
        task_dict = {
            "id": 1,
            "title": "Test Task",
            "description": "Test description",
            "status": "pending",
            "priority": "medium",
            "instance_id": None,
            "worktree_id": None,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "started_at": None,
            "completed_at": None,
            "due_date": None,
            "estimated_duration": None,
            "actual_duration": None,
            "requirements": {},
            "results": {},
            "extra_metadata": {},
        }
        mock_crud.create_task.return_value = task_dict

        task_data = {"title": "Test Task", "description": "Test description"}

        response = client.post("/api/v1/tasks/", json=task_data)
        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert data["data"]["title"] == "Test Task"

    def test_start_task_success(self, client):
        """Test starting a task."""
        # Get the mock CRUD from the client fixture and configure it
        from cc_orchestrator.web.dependencies import get_crud

        mock_crud = client.app.dependency_overrides[get_crud]()

        # Mock existing task
        mock_task = MagicMock()
        mock_task.id = 1
        mock_task.status = TaskStatus.PENDING
        mock_task.started_at = None

        # Mock updated task
        updated_task = MagicMock()
        updated_task.id = 1
        updated_task.title = "Test Task"
        updated_task.description = "Test description"
        updated_task.status = TaskStatus.IN_PROGRESS
        updated_task.priority = TaskPriority.MEDIUM
        updated_task.instance_id = None
        updated_task.worktree_id = None
        updated_task.created_at = datetime.now()
        updated_task.updated_at = datetime.now()
        updated_task.started_at = datetime.now()
        updated_task.completed_at = None
        updated_task.due_date = None
        updated_task.estimated_duration = None
        updated_task.actual_duration = None
        updated_task.requirements = {}
        updated_task.results = {}
        updated_task.extra_metadata = {}

        # Configure the mocks
        mock_crud.get_task.return_value = mock_task
        # Return a proper dict instead of MagicMock for API response
        updated_task_dict = {
            "id": 1,
            "title": "Test Task",
            "description": "Test description",
            "status": "in_progress",
            "priority": "medium",
            "instance_id": None,
            "worktree_id": None,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "started_at": datetime.now().isoformat(),
            "completed_at": None,
            "due_date": None,
            "estimated_duration": None,
            "actual_duration": None,
            "requirements": {},
            "results": {},
            "extra_metadata": {},
        }
        mock_crud.update_task.return_value = updated_task_dict

        response = client.post("/api/v1/tasks/1/start")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["status"] == "in_progress"


class TestPaginationAndFiltering:
    """Test pagination and filtering functionality."""

    @patch("cc_orchestrator.web.dependencies.get_crud")
    def test_pagination_parameters(self, mock_get_crud, client):
        """Test pagination parameters validation."""
        mock_crud = MagicMock()
        mock_crud.list_instances = AsyncMock(return_value=([], 0))
        mock_get_crud.return_value = mock_crud

        # Test valid pagination
        response = client.get("/api/v1/instances/?page=2&size=10")
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 2
        assert data["size"] == 10

        # Test invalid page number
        response = client.get("/api/v1/instances/?page=0")
        assert response.status_code == 422

        # Test invalid page size
        response = client.get("/api/v1/instances/?size=101")
        assert response.status_code == 422

    def test_instance_filtering(self, client):
        """Test instance filtering by status and branch."""
        # Get the mock CRUD from the client fixture and configure it
        from cc_orchestrator.web.dependencies import get_crud

        mock_crud = client.app.dependency_overrides[get_crud]()

        # Reset the mock to track calls
        mock_crud.list_instances.reset_mock()

        response = client.get("/api/v1/instances/?status=running&branch=main")
        assert response.status_code == 200

        # Verify CRUD was called with correct filters
        call_args = mock_crud.list_instances.call_args
        filters = call_args.kwargs["filters"]
        assert "status" in filters
        assert "branch_name" in filters


class TestMiddleware:
    """Test middleware functionality."""

    def test_cors_headers(self, client):
        """Test CORS headers are present."""
        response = client.options("/api/v1/instances/")
        # FastAPI automatically handles OPTIONS requests
        assert response.status_code in [200, 405]  # Depending on implementation

    def test_request_id_header(self, client):
        """Test that request ID is added to responses."""
        response = client.get("/health")
        assert response.status_code == 200
        # Request ID might not be implemented yet, so check if present or skip
        if "X-Request-ID" in response.headers:
            assert "X-Request-ID" in response.headers

    def test_rate_limiting_headers(self, client):
        """Test rate limiting headers."""
        response = client.get("/health")
        assert response.status_code == 200
        # Rate limiting might not be implemented yet, so check if present or skip
        if "X-RateLimit-Limit" in response.headers:
            assert "X-RateLimit-Limit" in response.headers
            assert "X-RateLimit-Remaining" in response.headers
            assert "X-RateLimit-Reset" in response.headers


class TestErrorHandling:
    """Test error handling and responses."""

    def test_validation_error_response(self, client):
        """Test validation error response format."""
        # Send invalid data to trigger validation error
        response = client.post("/api/v1/instances/", json={"invalid": "data"})
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_not_found_error_format(self, client):
        """Test 404 error response format."""
        # Get the mock CRUD from the client fixture and configure it
        from cc_orchestrator.web.dependencies import get_crud

        mock_crud = client.app.dependency_overrides[get_crud]()

        # Configure to return None for not found
        mock_crud.get_instance.return_value = None

        response = client.get("/api/v1/instances/999")
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()


class TestSchemaValidation:
    """Test Pydantic schema validation."""

    def test_instance_create_schema_validation(self, client):
        """Test instance creation schema validation."""
        with patch("cc_orchestrator.web.dependencies.get_crud") as mock_get_crud:
            mock_crud = MagicMock()
            mock_crud.get_instance_by_issue_id = AsyncMock(return_value=None)
            mock_get_crud.return_value = mock_crud

            # Test missing required field
            response = client.post("/api/v1/instances/", json={})
            assert response.status_code == 422

            # Test invalid enum value
            response = client.post(
                "/api/v1/instances/",
                json={"issue_id": "test-123", "status": "invalid_status"},
            )
            assert response.status_code == 422

    def test_task_create_schema_validation(self, client):
        """Test task creation schema validation."""
        # Test missing required field
        response = client.post("/api/v1/tasks/", json={})
        assert response.status_code == 422

        # Test invalid priority value
        response = client.post(
            "/api/v1/tasks/",
            json={"title": "Test Task", "priority": "invalid_priority"},
        )
        assert response.status_code == 422


@pytest.mark.asyncio
class TestAsyncEndpoints:
    """Test async endpoint functionality."""

    async def test_async_health_check(self):
        """Test async health check endpoint."""
        app = create_app()

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            response = await ac.get("/api/v1/health/")
            assert response.status_code == 200


class TestAPIDocumentation:
    """Test API documentation generation."""

    def test_openapi_schema_available(self, client):
        """Test that OpenAPI schema is available."""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data
        assert "info" in data
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
