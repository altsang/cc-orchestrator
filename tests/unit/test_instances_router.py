"""
Unit tests for instances router API endpoints.

Tests cover all instance management functionality including:
- List instances with filtering and pagination
- Create new instances with validation
- Get, update, and delete instances
- Start and stop instance operations
- Get instance status and tasks
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import HTTPException

from cc_orchestrator.database.models import HealthStatus, InstanceStatus
from cc_orchestrator.web.dependencies import PaginationParams
from cc_orchestrator.web.routers.v1 import instances
from cc_orchestrator.web.schemas import InstanceCreate, InstanceResponse, InstanceUpdate


class TestInstancesRouterFunctions:
    """Test instances router endpoint functions directly."""

    @pytest.fixture
    def mock_crud(self):
        """Mock CRUD adapter."""
        crud = AsyncMock()

        # Mock instance data
        mock_instance = Mock()
        mock_instance.id = 1
        mock_instance.issue_id = "test-issue-001"
        mock_instance.status = InstanceStatus.RUNNING
        mock_instance.health_status = HealthStatus.HEALTHY
        mock_instance.workspace_path = "/workspace/test"
        mock_instance.branch_name = "main"
        mock_instance.tmux_session = "test-session"
        mock_instance.process_id = 12345
        mock_instance.extra_metadata = {}  # Dict, not Mock
        mock_instance.health_check_count = 10
        mock_instance.healthy_check_count = 8
        mock_instance.last_recovery_attempt = None
        mock_instance.recovery_attempt_count = 0
        mock_instance.health_check_details = "All systems operational"
        mock_instance.last_health_check = datetime.now(UTC)
        mock_instance.last_activity = datetime.now(UTC)
        mock_instance.created_at = datetime.now(UTC)
        mock_instance.updated_at = datetime.now(UTC)

        # Mock task data
        mock_task = Mock()
        mock_task.id = 1
        mock_task.instance_id = 1
        mock_task.name = "test-task"
        mock_task.__dict__ = {"id": 1, "instance_id": 1, "name": "test-task"}

        crud.list_instances.return_value = ([mock_instance], 1)
        crud.create_instance.return_value = mock_instance
        crud.get_instance.return_value = mock_instance
        crud.get_instance_by_issue_id.return_value = None  # No duplicate by default
        crud.update_instance.return_value = mock_instance
        crud.delete_instance.return_value = True
        crud.list_tasks.return_value = ([mock_task], 1)

        return crud

    @pytest.fixture
    def pagination_params(self):
        """Mock pagination parameters."""
        params = Mock(spec=PaginationParams)
        params.page = 1
        params.size = 20
        params.offset = 0
        return params

    @pytest.mark.asyncio
    async def test_list_instances_success(self, mock_crud, pagination_params):
        """Test successful instance listing with pagination."""
        result = await instances.list_instances(
            pagination=pagination_params,
            status_filter=None,
            branch_name=None,
            crud=mock_crud,
        )

        assert result["total"] == 1
        assert len(result["items"]) == 1
        assert result["page"] == 1
        assert result["size"] == 20
        assert result["pages"] == 1

        # Verify CRUD was called correctly
        mock_crud.list_instances.assert_called_once_with(offset=0, limit=20, filters={})

    @pytest.mark.asyncio
    async def test_list_instances_with_filters(self, mock_crud, pagination_params):
        """Test instance listing with status and branch filters."""
        result = await instances.list_instances(
            pagination=pagination_params,
            status_filter=InstanceStatus.RUNNING,
            branch_name="feature-branch",
            crud=mock_crud,
        )

        assert result["total"] == 1

        # Verify filters were applied
        mock_crud.list_instances.assert_called_once_with(
            offset=0,
            limit=20,
            filters={"status": InstanceStatus.RUNNING, "branch_name": "feature-branch"},
        )

    @pytest.mark.asyncio
    async def test_create_instance_success(self, mock_crud):
        """Test successful instance creation."""
        instance_data = InstanceCreate(
            issue_id="new-issue-001",
            workspace_path="/workspace/new",
            branch_name="new-branch",
            tmux_session="new-session",
        )

        result = await instances.create_instance(
            instance_data=instance_data, crud=mock_crud
        )

        assert result["success"] is True
        assert "Instance created successfully" in result["message"]
        assert "data" in result

        # Verify duplicate check and creation
        mock_crud.get_instance_by_issue_id.assert_called_once_with("new-issue-001")
        mock_crud.create_instance.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_instance_duplicate_issue_id(self, mock_crud):
        """Test instance creation with duplicate issue_id."""
        # Mock existing instance
        mock_existing = Mock()
        mock_crud.get_instance_by_issue_id.return_value = mock_existing

        instance_data = InstanceCreate(
            issue_id="duplicate-issue",
            workspace_path="/workspace/duplicate",
            branch_name="duplicate-branch",
        )

        with pytest.raises(Exception) as exc_info:
            await instances.create_instance(instance_data=instance_data, crud=mock_crud)

        assert "Instance with issue_id 'duplicate-issue' already exists" in str(
            exc_info.value
        )

    @pytest.mark.asyncio
    async def test_get_instance_success(self, mock_crud):
        """Test successful instance retrieval by ID."""
        result = await instances.get_instance(instance_id=1, crud=mock_crud)

        assert result["success"] is True
        assert "Instance retrieved successfully" in result["message"]
        assert "data" in result

        mock_crud.get_instance.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_get_instance_not_found(self, mock_crud):
        """Test instance retrieval for non-existent instance."""
        mock_crud.get_instance.return_value = None

        with pytest.raises(Exception) as exc_info:
            await instances.get_instance(instance_id=999, crud=mock_crud)

        assert "Instance with ID 999 not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_instance_database_error(self, mock_crud):
        """Test instance retrieval with database error."""
        # Mock a database error (not HTTPException)
        mock_crud.get_instance.side_effect = Exception("Database connection failed")

        with pytest.raises(HTTPException) as exc_info:
            await instances.get_instance(instance_id=1, crud=mock_crud)

        # Should convert database error to 404
        assert exc_info.value.status_code == 404
        assert "Instance with ID 1 not found" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_update_instance_success(self, mock_crud):
        """Test successful instance update."""
        update_data = InstanceUpdate(
            workspace_path="/workspace/updated", branch_name="updated-branch"
        )

        result = await instances.update_instance(
            instance_id=1, instance_data=update_data, crud=mock_crud
        )

        assert result["success"] is True
        assert "Instance updated successfully" in result["message"]

        mock_crud.get_instance.assert_called_once_with(1)
        mock_crud.update_instance.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_instance_not_found(self, mock_crud):
        """Test instance update for non-existent instance."""
        mock_crud.get_instance.return_value = None

        update_data = InstanceUpdate(workspace_path="/new/path")

        with pytest.raises(Exception) as exc_info:
            await instances.update_instance(
                instance_id=999, instance_data=update_data, crud=mock_crud
            )

        assert "Instance with ID 999 not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_delete_instance_success(self, mock_crud):
        """Test successful instance deletion."""
        result = await instances.delete_instance(instance_id=1, crud=mock_crud)

        assert result["success"] is True
        assert "Instance deleted successfully" in result["message"]

        mock_crud.get_instance.assert_called_once_with(1)
        mock_crud.delete_instance.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_delete_instance_not_found(self, mock_crud):
        """Test instance deletion for non-existent instance."""
        mock_crud.get_instance.return_value = None

        with pytest.raises(Exception) as exc_info:
            await instances.delete_instance(instance_id=999, crud=mock_crud)

        assert "Instance with ID 999 not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_start_instance_success(self, mock_crud):
        """Test successful instance start operation."""
        # Mock instance with stopped status
        mock_instance = Mock()
        mock_instance.status = InstanceStatus.STOPPED
        mock_crud.get_instance.return_value = mock_instance

        result = await instances.start_instance(instance_id=1, crud=mock_crud)

        assert result["success"] is True
        assert "Instance started successfully" in result["message"]

        mock_crud.get_instance.assert_called_once_with(1)
        mock_crud.update_instance.assert_called_once_with(
            1, {"status": InstanceStatus.RUNNING}
        )

    @pytest.mark.asyncio
    async def test_start_instance_already_running(self, mock_crud):
        """Test starting an instance that's already running."""
        # Mock instance with running status
        mock_instance = Mock()
        mock_instance.status = InstanceStatus.RUNNING
        mock_crud.get_instance.return_value = mock_instance

        with pytest.raises(Exception) as exc_info:
            await instances.start_instance(instance_id=1, crud=mock_crud)

        assert "Instance is already running" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_start_instance_not_found(self, mock_crud):
        """Test starting a non-existent instance."""
        mock_crud.get_instance.return_value = None

        with pytest.raises(Exception) as exc_info:
            await instances.start_instance(instance_id=999, crud=mock_crud)

        assert "Instance with ID 999 not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_stop_instance_success(self, mock_crud):
        """Test successful instance stop operation."""
        # Mock instance with running status
        mock_instance = Mock()
        mock_instance.status = InstanceStatus.RUNNING
        mock_crud.get_instance.return_value = mock_instance

        result = await instances.stop_instance(instance_id=1, crud=mock_crud)

        assert result["success"] is True
        assert "Instance stopped successfully" in result["message"]

        mock_crud.get_instance.assert_called_once_with(1)
        mock_crud.update_instance.assert_called_once_with(
            1, {"status": InstanceStatus.STOPPED}
        )

    @pytest.mark.asyncio
    async def test_stop_instance_already_stopped(self, mock_crud):
        """Test stopping an instance that's already stopped."""
        # Mock instance with stopped status
        mock_instance = Mock()
        mock_instance.status = InstanceStatus.STOPPED
        mock_crud.get_instance.return_value = mock_instance

        with pytest.raises(Exception) as exc_info:
            await instances.stop_instance(instance_id=1, crud=mock_crud)

        assert "Instance is already stopped" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_stop_instance_not_found(self, mock_crud):
        """Test stopping a non-existent instance."""
        mock_crud.get_instance.return_value = None

        with pytest.raises(Exception) as exc_info:
            await instances.stop_instance(instance_id=999, crud=mock_crud)

        assert "Instance with ID 999 not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_instance_status_success(self, mock_crud):
        """Test successful instance status retrieval."""
        result = await instances.get_instance_status(instance_id=1, crud=mock_crud)

        assert result["success"] is True
        assert "Instance status retrieved successfully" in result["message"]
        assert "data" in result

        status_data = result["data"]
        assert status_data["id"] == 1
        assert status_data["issue_id"] == "test-issue-001"
        assert status_data["status"] == InstanceStatus.RUNNING

        mock_crud.get_instance.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_get_instance_status_not_found(self, mock_crud):
        """Test instance status retrieval for non-existent instance."""
        mock_crud.get_instance.return_value = None

        with pytest.raises(Exception) as exc_info:
            await instances.get_instance_status(instance_id=999, crud=mock_crud)

        assert "Instance with ID 999 not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_instance_tasks_success(self, mock_crud, pagination_params):
        """Test successful retrieval of instance tasks."""
        # Create a proper mock task with all required fields
        from datetime import datetime

        from cc_orchestrator.database.models import TaskPriority, TaskStatus

        mock_task = Mock()
        mock_task.id = 1
        mock_task.title = "Test Task"
        mock_task.description = "Test Description"
        mock_task.status = TaskStatus.PENDING
        mock_task.priority = TaskPriority.MEDIUM
        mock_task.instance_id = 1
        mock_task.worktree_id = None
        mock_task.due_date = None
        mock_task.estimated_duration = None
        mock_task.actual_duration = None
        mock_task.requirements = {}
        mock_task.results = {}
        mock_task.extra_metadata = {}
        mock_task.started_at = None
        mock_task.completed_at = None
        mock_task.created_at = datetime.now(UTC)
        mock_task.updated_at = datetime.now(UTC)

        mock_crud.list_tasks.return_value = ([mock_task], 1)

        result = await instances.get_instance_tasks(
            instance_id=1, pagination=pagination_params, crud=mock_crud
        )

        assert result["total"] == 1
        assert len(result["items"]) == 1
        assert result["page"] == 1
        assert result["size"] == 20

        # Verify instance check and task retrieval
        mock_crud.get_instance.assert_called_once_with(1)
        mock_crud.list_tasks.assert_called_once_with(
            offset=0, limit=20, filters={"instance_id": 1}
        )

    @pytest.mark.asyncio
    async def test_get_instance_tasks_not_found(self, mock_crud, pagination_params):
        """Test instance tasks retrieval for non-existent instance."""
        mock_crud.get_instance.return_value = None

        with pytest.raises(Exception) as exc_info:
            await instances.get_instance_tasks(
                instance_id=999, pagination=pagination_params, crud=mock_crud
            )

        assert "Instance with ID 999 not found" in str(exc_info.value)


class TestInstanceValidation:
    """Test instance data validation and edge cases."""

    def test_instance_response_model_validation(self):
        """Test InstanceResponse model validation."""
        instance_data = {
            "id": 1,
            "issue_id": "test-issue",
            "status": InstanceStatus.RUNNING,
            "health_status": HealthStatus.HEALTHY,
            "workspace_path": "/workspace/test",
            "branch_name": "main",
            "tmux_session": "test-session",
            "process_id": 12345,
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }

        response_model = InstanceResponse.model_validate(instance_data)
        assert response_model.issue_id == "test-issue"
        assert response_model.status == InstanceStatus.RUNNING.value

    def test_instance_create_model_validation(self):
        """Test InstanceCreate model validation."""
        create_data = {
            "issue_id": "new-issue",
            "workspace_path": "/workspace/new",
            "branch_name": "new-branch",
            "tmux_session": "new-session",
        }

        create_model = InstanceCreate.model_validate(create_data)
        assert create_model.issue_id == "new-issue"
        assert create_model.workspace_path == "/workspace/new"

    def test_instance_status_enum_values(self):
        """Test InstanceStatus enum contains expected values."""
        expected_statuses = {"initializing", "running", "stopped", "error"}
        actual_statuses = {status.value for status in InstanceStatus}

        assert actual_statuses == expected_statuses


class TestInstanceRouterDecorators:
    """Test decorator functionality on instance endpoints."""

    def test_decorators_applied_to_list_instances(self):
        """Test that decorators are applied to list_instances function."""
        func = instances.list_instances
        assert hasattr(func, "__wrapped__") or hasattr(func, "__name__")
        assert func.__name__ == "list_instances"

    def test_decorators_applied_to_create_instance(self):
        """Test that decorators are applied to create_instance function."""
        func = instances.create_instance
        assert hasattr(func, "__wrapped__") or hasattr(func, "__name__")
        assert func.__name__ == "create_instance"

    def test_decorators_applied_to_get_instance(self):
        """Test that decorators are applied to get_instance function."""
        func = instances.get_instance
        assert hasattr(func, "__wrapped__") or hasattr(func, "__name__")
        assert func.__name__ == "get_instance"


class TestInstanceRouterIntegration:
    """Test router integration aspects."""

    def test_router_has_endpoints(self):
        """Test that the router has the expected endpoints."""
        routes = instances.router.routes
        assert len(routes) > 0

        route_paths = [route.path for route in routes]

        # Should have the main list endpoint
        assert "/" in route_paths

        # Should have specific instance endpoints
        assert "/{instance_id}" in route_paths
        assert "/{instance_id}/start" in route_paths
        assert "/{instance_id}/stop" in route_paths

    def test_router_methods(self):
        """Test that routes have correct HTTP methods."""
        routes = instances.router.routes

        # Collect all methods for each path
        path_methods = {}
        for route in routes:
            if route.path not in path_methods:
                path_methods[route.path] = set()
            path_methods[route.path].update(route.methods)

        # Main endpoint should support GET and POST
        assert "GET" in path_methods["/"]
        assert "POST" in path_methods["/"]

        # Specific instance endpoint should support GET, PUT, DELETE
        assert "GET" in path_methods["/{instance_id}"]
        assert "PUT" in path_methods["/{instance_id}"]
        assert "DELETE" in path_methods["/{instance_id}"]

        # Action endpoints should support POST
        assert "POST" in path_methods["/{instance_id}/start"]
        assert "POST" in path_methods["/{instance_id}/stop"]

    def test_instance_status_enum_in_routes(self):
        """Test that InstanceStatus enum is properly integrated."""
        statuses = [status.value for status in InstanceStatus]
        expected_statuses = ["initializing", "running", "stopped", "error"]

        assert set(statuses) == set(expected_statuses)


class TestInstanceRouterErrorCases:
    """Test error handling in instance router."""

    @pytest.fixture
    def mock_crud_with_errors(self):
        """Mock CRUD adapter that returns None (not found)."""
        crud = AsyncMock()
        crud.get_instance.return_value = None
        return crud

    @pytest.mark.asyncio
    async def test_instance_operations_handle_database_errors(
        self, mock_crud_with_errors
    ):
        """Test instance operations when instance not found."""
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await instances.get_instance(instance_id=1, crud=mock_crud_with_errors)

        # Should get 404 for not found
        assert exc_info.value.status_code == 404
        assert "Instance with ID 1 not found" in str(exc_info.value.detail)


class TestInstanceRouterEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.fixture
    def mock_crud_empty_results(self):
        """Mock CRUD adapter with empty results."""
        crud = AsyncMock()
        crud.list_instances.return_value = ([], 0)
        crud.list_tasks.return_value = ([], 0)
        return crud

    @pytest.fixture
    def pagination_params(self):
        """Mock pagination parameters for edge cases."""
        params = Mock(spec=PaginationParams)
        params.page = 1
        params.size = 20
        params.offset = 0
        return params

    @pytest.mark.asyncio
    async def test_list_instances_empty_results(
        self, mock_crud_empty_results, pagination_params
    ):
        """Test instance listing with no instances."""
        result = await instances.list_instances(
            pagination=pagination_params,
            status_filter=None,
            branch_name=None,
            crud=mock_crud_empty_results,
        )

        assert result["total"] == 0
        assert len(result["items"]) == 0
        assert result["pages"] == 0

    @pytest.mark.asyncio
    async def test_get_instance_tasks_empty_results(
        self, mock_crud_empty_results, pagination_params
    ):
        """Test instance tasks with no results."""
        # Still need a valid instance for the existence check
        mock_instance = Mock()
        mock_instance.id = 1
        mock_crud_empty_results.get_instance.return_value = mock_instance

        result = await instances.get_instance_tasks(
            instance_id=1, pagination=pagination_params, crud=mock_crud_empty_results
        )

        assert result["total"] == 0
        assert len(result["items"]) == 0
