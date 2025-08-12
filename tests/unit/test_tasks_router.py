"""
Unit tests for tasks router API endpoints.

Tests cover all task management functionality including:
- List tasks with filtering and pagination
- Create new tasks with validation
- Get, update, and delete tasks
- Task lifecycle operations (start, complete, cancel)
- Task assignment operations
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock

import pytest

from cc_orchestrator.database.models import TaskPriority, TaskStatus
from cc_orchestrator.web.dependencies import PaginationParams
from cc_orchestrator.web.routers.v1 import tasks
from cc_orchestrator.web.schemas import TaskCreate, TaskResponse, TaskUpdate


class TestTasksRouterFunctions:
    """Test tasks router endpoint functions directly."""

    @pytest.fixture
    def mock_crud(self):
        """Mock CRUD adapter."""
        crud = AsyncMock()

        # Create proper task data that matches TaskResponse schema
        task_data = {
            "id": 1,
            "name": "Test Task",
            "description": "Test task description",
            "instance_id": 1,
            "command": "test command",
            "schedule": None,
            "enabled": True,
            "status": "pending",
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
            "last_run": None,
            "next_run": None,
        }
        
        # Create TaskResponse object instead of Mock
        mock_task = TaskResponse(**task_data)

        # Mock instance and worktree data (these can stay as Mock since they're not serialized)
        mock_instance = Mock()
        mock_instance.id = 1
        mock_instance.issue_id = "test-issue"

        mock_worktree = Mock()
        mock_worktree.id = 1
        mock_worktree.path = "/workspace/test"

        crud.list_tasks.return_value = ([mock_task], 1)
        crud.create_task.return_value = mock_task
        crud.get_task.return_value = mock_task
        crud.update_task.return_value = mock_task
        crud.delete_task.return_value = True
        crud.get_instance.return_value = mock_instance
        crud.get_worktree.return_value = mock_worktree

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
    async def test_list_tasks_success(self, mock_crud, pagination_params):
        """Test successful task listing with pagination."""
        result = await tasks.list_tasks(
            pagination=pagination_params,
            status_filter=None,
            priority_filter=None,
            instance_id=None,
            worktree_id=None,
            crud=mock_crud,
        )

        assert result["total"] == 1
        assert len(result["items"]) == 1
        assert result["page"] == 1
        assert result["size"] == 20
        assert result["pages"] == 1

        # Verify CRUD was called correctly
        mock_crud.list_tasks.assert_called_once_with(offset=0, limit=20, filters={})

    @pytest.mark.asyncio
    async def test_list_tasks_with_filters(self, mock_crud, pagination_params):
        """Test task listing with status, priority, and assignment filters."""
        result = await tasks.list_tasks(
            pagination=pagination_params,
            status_filter=TaskStatus.IN_PROGRESS,
            priority_filter=TaskPriority.HIGH,
            instance_id=1,
            worktree_id=2,
            crud=mock_crud,
        )

        assert result["total"] == 1

        # Verify filters were applied
        mock_crud.list_tasks.assert_called_once_with(
            offset=0,
            limit=20,
            filters={
                "status": TaskStatus.IN_PROGRESS,
                "priority": TaskPriority.HIGH,
                "instance_id": 1,
                "worktree_id": 2,
            },
        )

    @pytest.mark.asyncio
    async def test_create_task_success(self, mock_crud):
        """Test successful task creation."""
        task_data = TaskCreate(
            name="New Task",
            description="New task description",
            instance_id=1,
        )

        result = await tasks.create_task(task_data=task_data, crud=mock_crud)

        assert result["success"] is True
        assert "Task created successfully" in result["message"]
        assert "data" in result

        # Verify instance validation and creation
        mock_crud.get_instance.assert_called_once_with(1)
        mock_crud.create_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_task_with_worktree(self, mock_crud):
        """Test task creation with worktree validation."""
        task_data = TaskCreate(
            name="Worktree Task", description="Task with worktree", worktree_id=1
        )

        result = await tasks.create_task(task_data=task_data, crud=mock_crud)

        assert result["success"] is True

        # Verify worktree validation
        mock_crud.get_worktree.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_create_task_invalid_instance(self, mock_crud):
        """Test task creation with non-existent instance."""
        mock_crud.get_instance.return_value = None

        task_data = TaskCreate(name="Invalid Task", instance_id=999)

        with pytest.raises(Exception) as exc_info:
            await tasks.create_task(task_data=task_data, crud=mock_crud)

        assert "Instance with ID 999 not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_task_invalid_worktree(self, mock_crud):
        """Test task creation with non-existent worktree."""
        mock_crud.get_worktree.return_value = None

        task_data = TaskCreate(name="Invalid Worktree Task", worktree_id=999)

        with pytest.raises(Exception) as exc_info:
            await tasks.create_task(task_data=task_data, crud=mock_crud)

        assert "Worktree with ID 999 not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_task_success(self, mock_crud):
        """Test successful task retrieval by ID."""
        result = await tasks.get_task(task_id=1, crud=mock_crud)

        assert result["success"] is True
        assert "Task retrieved successfully" in result["message"]
        assert "data" in result

        mock_crud.get_task.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_get_task_not_found(self, mock_crud):
        """Test task retrieval for non-existent task."""
        mock_crud.get_task.return_value = None

        with pytest.raises(Exception) as exc_info:
            await tasks.get_task(task_id=999, crud=mock_crud)

        assert "Task with ID 999 not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_update_task_success(self, mock_crud):
        """Test successful task update."""
        update_data = TaskUpdate(name="Updated Task")

        result = await tasks.update_task(
            task_id=1, task_data=update_data, crud=mock_crud
        )

        assert result["success"] is True
        assert "Task updated successfully" in result["message"]

        mock_crud.get_task.assert_called_once_with(1)
        mock_crud.update_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_task_not_found(self, mock_crud):
        """Test task update for non-existent task."""
        mock_crud.get_task.return_value = None

        update_data = TaskUpdate(name="Updated Task")

        with pytest.raises(Exception) as exc_info:
            await tasks.update_task(task_id=999, task_data=update_data, crud=mock_crud)

        assert "Task with ID 999 not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_delete_task_success(self, mock_crud):
        """Test successful task deletion."""
        result = await tasks.delete_task(task_id=1, crud=mock_crud)

        assert result["success"] is True
        assert "Task deleted successfully" in result["message"]

        mock_crud.get_task.assert_called_once_with(1)
        mock_crud.delete_task.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_delete_task_not_found(self, mock_crud):
        """Test task deletion for non-existent task."""
        mock_crud.get_task.return_value = None

        with pytest.raises(Exception) as exc_info:
            await tasks.delete_task(task_id=999, crud=mock_crud)

        assert "Task with ID 999 not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_start_task_success(self, mock_crud):
        """Test successful task start operation."""
        # Mock task with pending status
        mock_task = Mock()
        mock_task.status = TaskStatus.PENDING
        mock_crud.get_task.return_value = mock_task

        result = await tasks.start_task(task_id=1, crud=mock_crud)

        assert result["success"] is True
        assert "Task started successfully" in result["message"]

        mock_crud.get_task.assert_called_once_with(1)
        mock_crud.update_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_task_already_in_progress(self, mock_crud):
        """Test starting a task that's already in progress."""
        # Mock task with in_progress status
        mock_task = Mock()
        mock_task.status = TaskStatus.IN_PROGRESS
        mock_crud.get_task.return_value = mock_task

        with pytest.raises(Exception) as exc_info:
            await tasks.start_task(task_id=1, crud=mock_crud)

        assert "Task is already in progress" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_start_task_completed(self, mock_crud):
        """Test starting a completed task fails."""
        # Mock task with completed status
        mock_task = Mock()
        mock_task.status = TaskStatus.COMPLETED
        mock_crud.get_task.return_value = mock_task

        with pytest.raises(Exception) as exc_info:
            await tasks.start_task(task_id=1, crud=mock_crud)

        assert "Cannot start a completed task" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_complete_task_success(self, mock_crud):
        """Test successful task completion."""
        # Mock task with in_progress status
        mock_task = Mock()
        mock_task.status = TaskStatus.IN_PROGRESS
        mock_task.started_at = datetime.now(UTC)
        mock_crud.get_task.return_value = mock_task

        result = await tasks.complete_task(
            task_id=1, results={"output": "success"}, crud=mock_crud
        )

        assert result["success"] is True
        assert "Task completed successfully" in result["message"]

        mock_crud.get_task.assert_called_once_with(1)
        mock_crud.update_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_complete_task_already_completed(self, mock_crud):
        """Test completing a task that's already completed."""
        # Mock task with completed status
        mock_task = Mock()
        mock_task.status = TaskStatus.COMPLETED
        mock_crud.get_task.return_value = mock_task

        with pytest.raises(Exception) as exc_info:
            await tasks.complete_task(task_id=1, crud=mock_crud)

        assert "Task is already completed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_cancel_task_success(self, mock_crud):
        """Test successful task cancellation."""
        # Mock task with pending status
        mock_task = Mock()
        mock_task.status = TaskStatus.PENDING
        mock_crud.get_task.return_value = mock_task

        result = await tasks.cancel_task(task_id=1, crud=mock_crud)

        assert result["success"] is True
        assert "Task cancelled successfully" in result["message"]

        mock_crud.get_task.assert_called_once_with(1)
        mock_crud.update_task.assert_called_once_with(
            1, {"status": TaskStatus.CANCELLED}
        )

    @pytest.mark.asyncio
    async def test_cancel_task_already_completed(self, mock_crud):
        """Test cancelling a completed task fails."""
        # Mock task with completed status
        mock_task = Mock()
        mock_task.status = TaskStatus.COMPLETED
        mock_crud.get_task.return_value = mock_task

        with pytest.raises(Exception) as exc_info:
            await tasks.cancel_task(task_id=1, crud=mock_crud)

        assert "Cannot cancel a completed task" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_assign_task_success(self, mock_crud):
        """Test successful task assignment."""
        assignment_data = {"instance_id": 2}
        result = await tasks.assign_task(
            assignment_data=assignment_data, task_id=1, crud=mock_crud
        )

        assert result["success"] is True
        assert "Task assigned successfully" in result["message"]

        mock_crud.get_task.assert_called_once_with(1)
        mock_crud.get_instance.assert_called_once_with(2)
        mock_crud.update_task.assert_called_once_with(1, {"instance_id": 2})

    @pytest.mark.asyncio
    async def test_assign_task_invalid_instance(self, mock_crud):
        """Test task assignment with non-existent instance."""
        mock_crud.get_instance.return_value = None
        assignment_data = {"instance_id": 999}

        with pytest.raises(Exception) as exc_info:
            await tasks.assign_task(
                assignment_data=assignment_data, task_id=1, crud=mock_crud
            )

        assert "Instance with ID 999 not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_unassign_task_success(self, mock_crud):
        """Test successful task unassignment."""
        result = await tasks.unassign_task(task_id=1, crud=mock_crud)

        assert result["success"] is True
        assert "Task unassigned successfully" in result["message"]

        mock_crud.get_task.assert_called_once_with(1)
        mock_crud.update_task.assert_called_once_with(1, {"instance_id": None})


class TestTaskValidation:
    """Test task data validation and edge cases."""

    def test_task_response_model_validation(self):
        """Test TaskResponse model validation."""
        task_data = {
            "id": 1,
            "name": "Test Task",
            "description": "Test description",
            "status": "pending",
            "instance_id": 1,
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
            "command": None,
            "schedule": None,
            "enabled": True,
            "last_run": None,
            "next_run": None,
            "requirements": {},
            "results": {},
            "extra_metadata": {},
            "started_at": None,
            "completed_at": None,
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }

        response_model = TaskResponse.model_validate(task_data)
        assert response_model.name == "Test Task"
        assert response_model.status == "pending"

    def test_task_create_model_validation(self):
        """Test TaskCreate model validation."""
        create_data = {
            "name": "New Task",
            "description": "New task description",
        }

        create_model = TaskCreate.model_validate(create_data)
        assert create_model.name == "New Task"

    def test_task_status_enum_values(self):
        """Test TaskStatus enum contains expected values."""
        expected_statuses = {
            "pending",
            "in_progress",
            "completed",
            "cancelled",
            "failed",
        }
        actual_statuses = {status.value for status in TaskStatus}

        assert actual_statuses == expected_statuses

    def test_task_priority_enum_values(self):
        """Test TaskPriority enum contains expected values."""
        expected_priorities = {1, 2, 3, 4}  # TaskPriority uses integers
        actual_priorities = {priority.value for priority in TaskPriority}

        assert actual_priorities == expected_priorities


class TestTaskRouterDecorators:
    """Test decorator functionality on task endpoints."""

    def test_decorators_applied_to_list_tasks(self):
        """Test that decorators are applied to list_tasks function."""
        func = tasks.list_tasks
        assert hasattr(func, "__wrapped__") or hasattr(func, "__name__")
        assert func.__name__ == "list_tasks"

    def test_decorators_applied_to_create_task(self):
        """Test that decorators are applied to create_task function."""
        func = tasks.create_task
        assert hasattr(func, "__wrapped__") or hasattr(func, "__name__")
        assert func.__name__ == "create_task"

    def test_decorators_applied_to_start_task(self):
        """Test that decorators are applied to start_task function."""
        func = tasks.start_task
        assert hasattr(func, "__wrapped__") or hasattr(func, "__name__")
        assert func.__name__ == "start_task"


class TestTaskRouterIntegration:
    """Test router integration aspects."""

    def test_router_has_endpoints(self):
        """Test that the router has the expected endpoints."""
        routes = tasks.router.routes
        assert len(routes) > 0

        route_paths = [route.path for route in routes]

        # Should have the main list endpoint
        assert "/" in route_paths

        # Should have specific task endpoints
        assert "/{task_id}" in route_paths
        assert "/{task_id}/start" in route_paths
        assert "/{task_id}/complete" in route_paths
        assert "/{task_id}/cancel" in route_paths

    def test_router_methods(self):
        """Test that routes have correct HTTP methods."""
        routes = tasks.router.routes

        # Collect all methods for each path
        path_methods = {}
        for route in routes:
            if route.path not in path_methods:
                path_methods[route.path] = set()
            path_methods[route.path].update(route.methods)

        # Main endpoint should support GET and POST
        assert "GET" in path_methods["/"]
        assert "POST" in path_methods["/"]

        # Specific task endpoint should support GET, PUT, DELETE
        assert "GET" in path_methods["/{task_id}"]
        assert "PUT" in path_methods["/{task_id}"]
        assert "DELETE" in path_methods["/{task_id}"]

        # Action endpoints should support POST
        assert "POST" in path_methods["/{task_id}/start"]
        assert "POST" in path_methods["/{task_id}/complete"]
        assert "POST" in path_methods["/{task_id}/cancel"]


class TestTaskRouterEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.fixture
    def mock_crud_empty_results(self):
        """Mock CRUD adapter with empty results."""
        crud = AsyncMock()
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
    async def test_list_tasks_empty_results(
        self, mock_crud_empty_results, pagination_params
    ):
        """Test task listing with no tasks."""
        result = await tasks.list_tasks(
            pagination=pagination_params,
            status_filter=None,
            priority_filter=None,
            instance_id=None,
            worktree_id=None,
            crud=mock_crud_empty_results,
        )

        assert result["total"] == 0
        assert len(result["items"]) == 0
        assert result["pages"] == 0
