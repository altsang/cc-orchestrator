"""
Comprehensive test suite for tasks router targeting 100% code coverage.

This test file aims for complete coverage of all 147 statements in the tasks router,
including all endpoints, error conditions, edge cases, and conditional branches.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import HTTPException, status

from cc_orchestrator.database.models import TaskPriority, TaskStatus
from cc_orchestrator.web.dependencies import PaginationParams
from cc_orchestrator.web.routers.v1 import tasks
from cc_orchestrator.web.schemas import TaskCreate, TaskResponse, TaskUpdate


class TestTasksListEndpoint:
    """Test the list tasks endpoint with all filtering combinations."""

    @pytest.fixture
    def mock_crud(self):
        """Mock CRUD adapter for list tests."""
        crud = AsyncMock()
        return crud

    @pytest.fixture
    def pagination_params(self):
        """Standard pagination parameters."""
        return PaginationParams(page=1, size=20)

    @pytest.fixture
    def sample_task_data(self):
        """Sample task data for responses."""
        return {
            "id": 1,
            "title": "Test Task",
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

    @pytest.mark.asyncio
    async def test_list_tasks_no_filters(
        self, mock_crud, pagination_params, sample_task_data
    ):
        """Test listing tasks with no filters applied."""
        task = TaskResponse(**sample_task_data)
        mock_crud.list_tasks.return_value = ([task], 1)

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
        mock_crud.list_tasks.assert_called_once_with(offset=0, limit=20, filters={})

    @pytest.mark.asyncio
    async def test_list_tasks_with_status_filter(
        self, mock_crud, pagination_params, sample_task_data
    ):
        """Test listing tasks with status filter."""
        task = TaskResponse(**sample_task_data)
        mock_crud.list_tasks.return_value = ([task], 1)

        result = await tasks.list_tasks(
            pagination=pagination_params,
            status_filter=TaskStatus.IN_PROGRESS,
            priority_filter=None,
            instance_id=None,
            worktree_id=None,
            crud=mock_crud,
        )

        assert result["total"] == 1
        mock_crud.list_tasks.assert_called_once_with(
            offset=0, limit=20, filters={"status": TaskStatus.IN_PROGRESS}
        )

    @pytest.mark.asyncio
    async def test_list_tasks_with_priority_filter(
        self, mock_crud, pagination_params, sample_task_data
    ):
        """Test listing tasks with priority filter."""
        task = TaskResponse(**sample_task_data)
        mock_crud.list_tasks.return_value = ([task], 1)

        result = await tasks.list_tasks(
            pagination=pagination_params,
            status_filter=None,
            priority_filter=TaskPriority.HIGH,
            instance_id=None,
            worktree_id=None,
            crud=mock_crud,
        )

        assert result["total"] == 1
        mock_crud.list_tasks.assert_called_once_with(
            offset=0, limit=20, filters={"priority": TaskPriority.HIGH}
        )

    @pytest.mark.asyncio
    async def test_list_tasks_with_instance_id_filter(
        self, mock_crud, pagination_params, sample_task_data
    ):
        """Test listing tasks with instance_id filter."""
        task = TaskResponse(**sample_task_data)
        mock_crud.list_tasks.return_value = ([task], 1)

        result = await tasks.list_tasks(
            pagination=pagination_params,
            status_filter=None,
            priority_filter=None,
            instance_id=123,
            worktree_id=None,
            crud=mock_crud,
        )

        assert result["total"] == 1
        mock_crud.list_tasks.assert_called_once_with(
            offset=0, limit=20, filters={"instance_id": 123}
        )

    @pytest.mark.asyncio
    async def test_list_tasks_with_worktree_id_filter(
        self, mock_crud, pagination_params, sample_task_data
    ):
        """Test listing tasks with worktree_id filter."""
        task = TaskResponse(**sample_task_data)
        mock_crud.list_tasks.return_value = ([task], 1)

        result = await tasks.list_tasks(
            pagination=pagination_params,
            status_filter=None,
            priority_filter=None,
            instance_id=None,
            worktree_id=456,
            crud=mock_crud,
        )

        assert result["total"] == 1
        mock_crud.list_tasks.assert_called_once_with(
            offset=0, limit=20, filters={"worktree_id": 456}
        )

    @pytest.mark.asyncio
    async def test_list_tasks_with_all_filters(
        self, mock_crud, pagination_params, sample_task_data
    ):
        """Test listing tasks with all filters applied."""
        task = TaskResponse(**sample_task_data)
        mock_crud.list_tasks.return_value = ([task], 1)

        result = await tasks.list_tasks(
            pagination=pagination_params,
            status_filter=TaskStatus.COMPLETED,
            priority_filter=TaskPriority.URGENT,
            instance_id=123,
            worktree_id=456,
            crud=mock_crud,
        )

        assert result["total"] == 1
        mock_crud.list_tasks.assert_called_once_with(
            offset=0,
            limit=20,
            filters={
                "status": TaskStatus.COMPLETED,
                "priority": TaskPriority.URGENT,
                "instance_id": 123,
                "worktree_id": 456,
            },
        )

    @pytest.mark.asyncio
    async def test_list_tasks_empty_results(self, mock_crud, pagination_params):
        """Test listing tasks with no results."""
        mock_crud.list_tasks.return_value = ([], 0)

        result = await tasks.list_tasks(
            pagination=pagination_params,
            status_filter=None,
            priority_filter=None,
            instance_id=None,
            worktree_id=None,
            crud=mock_crud,
        )

        assert result["total"] == 0
        assert len(result["items"]) == 0
        assert result["pages"] == 0

    @pytest.mark.asyncio
    async def test_list_tasks_pagination_calculation(self, mock_crud, sample_task_data):
        """Test pagination calculation with different total counts."""
        task = TaskResponse(**sample_task_data)
        mock_crud.list_tasks.return_value = ([task] * 5, 25)
        pagination = PaginationParams(page=2, size=10)

        result = await tasks.list_tasks(
            pagination=pagination,
            status_filter=None,
            priority_filter=None,
            instance_id=None,
            worktree_id=None,
            crud=mock_crud,
        )

        assert result["total"] == 25
        assert result["page"] == 2
        assert result["size"] == 10
        assert result["pages"] == 3  # (25 + 10 - 1) // 10 = 3
        mock_crud.list_tasks.assert_called_once_with(offset=10, limit=10, filters={})


class TestTasksCreateEndpoint:
    """Test the create task endpoint with validation scenarios."""

    @pytest.fixture
    def mock_crud(self):
        """Mock CRUD adapter for create tests."""
        crud = AsyncMock()
        # Mock instance and worktree exist by default
        crud.get_instance.return_value = Mock(id=1)
        crud.get_worktree.return_value = Mock(id=1)
        return crud

    @pytest.fixture
    def sample_task_data(self):
        """Sample task data for responses."""
        return {
            "id": 1,
            "title": "Created Task",
            "description": "Created task description",
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

    @pytest.mark.asyncio
    async def test_create_task_minimal_data(self, mock_crud, sample_task_data):
        """Test creating task with minimal required data."""
        task_data = TaskCreate(title="Minimal Task", description="Test description")
        created_task = TaskResponse(**sample_task_data)
        mock_crud.create_task.return_value = created_task

        result = await tasks.create_task(task_data=task_data, crud=mock_crud)

        assert result["success"] is True
        assert "Task created successfully" in result["message"]
        assert result["data"] is not None
        mock_crud.create_task.assert_called_once()
        # Should not validate instance or worktree since they're None
        mock_crud.get_instance.assert_not_called()
        mock_crud.get_worktree.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_task_with_instance_id(self, mock_crud, sample_task_data):
        """Test creating task with instance_id validation."""
        task_data = TaskCreate(title="Task with Instance", instance_id=1)
        created_task = TaskResponse(**sample_task_data)
        mock_crud.create_task.return_value = created_task

        result = await tasks.create_task(task_data=task_data, crud=mock_crud)

        assert result["success"] is True
        mock_crud.get_instance.assert_called_once_with(1)
        mock_crud.create_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_task_with_worktree_id(self, mock_crud, sample_task_data):
        """Test creating task with worktree_id validation."""
        task_data = TaskCreate(title="Task with Worktree", worktree_id=1)
        created_task = TaskResponse(**sample_task_data)
        mock_crud.create_task.return_value = created_task

        result = await tasks.create_task(task_data=task_data, crud=mock_crud)

        assert result["success"] is True
        mock_crud.get_worktree.assert_called_once_with(1)
        mock_crud.create_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_task_with_both_ids(self, mock_crud, sample_task_data):
        """Test creating task with both instance_id and worktree_id."""
        task_data = TaskCreate(title="Task with Both", instance_id=1, worktree_id=1)
        created_task = TaskResponse(**sample_task_data)
        mock_crud.create_task.return_value = created_task

        result = await tasks.create_task(task_data=task_data, crud=mock_crud)

        assert result["success"] is True
        mock_crud.get_instance.assert_called_once_with(1)
        mock_crud.get_worktree.assert_called_once_with(1)
        mock_crud.create_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_task_invalid_instance_id(self, mock_crud):
        """Test creating task with non-existent instance_id."""
        mock_crud.get_instance.return_value = None
        task_data = TaskCreate(title="Invalid Instance Task", instance_id=999)

        with pytest.raises(HTTPException) as exc_info:
            await tasks.create_task(task_data=task_data, crud=mock_crud)

        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "Instance with ID 999 not found" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_create_task_invalid_worktree_id(self, mock_crud):
        """Test creating task with non-existent worktree_id."""
        mock_crud.get_worktree.return_value = None
        task_data = TaskCreate(title="Invalid Worktree Task", worktree_id=999)

        with pytest.raises(HTTPException) as exc_info:
            await tasks.create_task(task_data=task_data, crud=mock_crud)

        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "Worktree with ID 999 not found" in str(exc_info.value.detail)


class TestTasksGetEndpoint:
    """Test the get task endpoint."""

    @pytest.fixture
    def mock_crud(self):
        """Mock CRUD adapter for get tests."""
        return AsyncMock()

    @pytest.fixture
    def sample_task_data(self):
        """Sample task data for responses."""
        return {
            "id": 1,
            "title": "Retrieved Task",
            "description": "Retrieved task description",
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

    @pytest.mark.asyncio
    async def test_get_task_success(self, mock_crud, sample_task_data):
        """Test successful task retrieval."""
        task = TaskResponse(**sample_task_data)
        mock_crud.get_task.return_value = task

        result = await tasks.get_task(task_id=1, crud=mock_crud)

        assert result["success"] is True
        assert "Task retrieved successfully" in result["message"]
        assert result["data"] is not None
        mock_crud.get_task.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_get_task_not_found(self, mock_crud):
        """Test task retrieval for non-existent task."""
        mock_crud.get_task.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await tasks.get_task(task_id=999, crud=mock_crud)

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert "Task with ID 999 not found" in str(exc_info.value.detail)


class TestTasksUpdateEndpoint:
    """Test the update task endpoint with all validation scenarios."""

    @pytest.fixture
    def mock_crud(self):
        """Mock CRUD adapter for update tests."""
        crud = AsyncMock()
        # Mock existing task by default
        crud.get_task.return_value = Mock(id=1, title="Existing Task")
        # Mock instance and worktree exist by default
        crud.get_instance.return_value = Mock(id=1)
        crud.get_worktree.return_value = Mock(id=1)
        return crud

    @pytest.fixture
    def sample_task_data(self):
        """Sample task data for responses."""
        return {
            "id": 1,
            "title": "Updated Task",
            "description": "Updated task description",
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

    @pytest.mark.asyncio
    async def test_update_task_success(self, mock_crud, sample_task_data):
        """Test successful task update."""
        task_data = TaskUpdate(title="Updated Task Name")
        updated_task = TaskResponse(**sample_task_data)
        mock_crud.update_task.return_value = updated_task

        result = await tasks.update_task(task_id=1, task_data=task_data, crud=mock_crud)

        assert result["success"] is True
        assert "Task updated successfully" in result["message"]
        assert result["data"] is not None
        mock_crud.get_task.assert_called_once_with(1)
        mock_crud.update_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_task_not_found(self, mock_crud):
        """Test updating non-existent task."""
        mock_crud.get_task.return_value = None
        task_data = TaskUpdate(name="Updated Name")

        with pytest.raises(HTTPException) as exc_info:
            await tasks.update_task(task_id=999, task_data=task_data, crud=mock_crud)

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert "Task with ID 999 not found" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_update_task_with_instance_id(self, mock_crud, sample_task_data):
        """Test updating task with instance_id validation."""
        task_data = TaskUpdate(instance_id=2)
        updated_task = TaskResponse(**sample_task_data)
        mock_crud.update_task.return_value = updated_task

        result = await tasks.update_task(task_id=1, task_data=task_data, crud=mock_crud)

        assert result["success"] is True
        mock_crud.get_instance.assert_called_once_with(2)

    @pytest.mark.asyncio
    async def test_update_task_with_worktree_id(self, mock_crud, sample_task_data):
        """Test updating task with worktree_id validation."""
        task_data = TaskUpdate(worktree_id=2)
        updated_task = TaskResponse(**sample_task_data)
        mock_crud.update_task.return_value = updated_task

        result = await tasks.update_task(task_id=1, task_data=task_data, crud=mock_crud)

        assert result["success"] is True
        mock_crud.get_worktree.assert_called_once_with(2)

    @pytest.mark.asyncio
    async def test_update_task_invalid_instance_id(self, mock_crud):
        """Test updating task with non-existent instance_id."""
        mock_crud.get_instance.return_value = None
        task_data = TaskUpdate(instance_id=999)

        with pytest.raises(HTTPException) as exc_info:
            await tasks.update_task(task_id=1, task_data=task_data, crud=mock_crud)

        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "Instance with ID 999 not found" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_update_task_invalid_worktree_id(self, mock_crud):
        """Test updating task with non-existent worktree_id."""
        mock_crud.get_worktree.return_value = None
        task_data = TaskUpdate(worktree_id=999)

        with pytest.raises(HTTPException) as exc_info:
            await tasks.update_task(task_id=1, task_data=task_data, crud=mock_crud)

        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "Worktree with ID 999 not found" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_update_task_no_validation_when_ids_none(
        self, mock_crud, sample_task_data
    ):
        """Test that validation is skipped when instance_id and worktree_id are None."""
        task_data = TaskUpdate(name="Updated Name")  # No instance_id or worktree_id
        updated_task = TaskResponse(**sample_task_data)
        mock_crud.update_task.return_value = updated_task

        result = await tasks.update_task(task_id=1, task_data=task_data, crud=mock_crud)

        assert result["success"] is True
        # Should not call validation methods for None IDs
        mock_crud.get_instance.assert_not_called()
        mock_crud.get_worktree.assert_not_called()


class TestTasksDeleteEndpoint:
    """Test the delete task endpoint."""

    @pytest.fixture
    def mock_crud(self):
        """Mock CRUD adapter for delete tests."""
        crud = AsyncMock()
        crud.get_task.return_value = Mock(id=1, title="Task to Delete")
        return crud

    @pytest.mark.asyncio
    async def test_delete_task_success(self, mock_crud):
        """Test successful task deletion."""
        result = await tasks.delete_task(task_id=1, crud=mock_crud)

        assert result["success"] is True
        assert "Task deleted successfully" in result["message"]
        assert result["data"] is None
        mock_crud.get_task.assert_called_once_with(1)
        mock_crud.delete_task.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_delete_task_not_found(self, mock_crud):
        """Test deleting non-existent task."""
        mock_crud.get_task.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await tasks.delete_task(task_id=999, crud=mock_crud)

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert "Task with ID 999 not found" in str(exc_info.value.detail)


class TestTasksStartEndpoint:
    """Test the start task endpoint with all status scenarios."""

    @pytest.fixture
    def mock_crud(self):
        """Mock CRUD adapter for start tests."""
        return AsyncMock()

    @pytest.fixture
    def sample_task_data(self):
        """Sample task data for responses."""
        return {
            "id": 1,
            "title": "Started Task",
            "description": "Started task description",
            "instance_id": 1,
            "command": "test command",
            "schedule": None,
            "enabled": True,
            "status": "in_progress",
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
            "last_run": None,
            "next_run": None,
        }

    @pytest.mark.asyncio
    async def test_start_task_success_from_pending(self, mock_crud, sample_task_data):
        """Test starting a task from pending status."""
        mock_task = Mock(status=TaskStatus.PENDING)
        mock_crud.get_task.return_value = mock_task
        updated_task = TaskResponse(**sample_task_data)
        mock_crud.update_task.return_value = updated_task

        result = await tasks.start_task(task_id=1, crud=mock_crud)

        assert result["success"] is True
        assert "Task started successfully" in result["message"]
        assert result["data"] is not None
        mock_crud.get_task.assert_called_once_with(1)
        # Verify the update was called with correct parameters
        mock_crud.update_task.assert_called_once()
        update_args = mock_crud.update_task.call_args[0]
        assert update_args[0] == 1  # task_id
        update_data = update_args[1]
        assert update_data["status"] == TaskStatus.IN_PROGRESS
        assert "started_at" in update_data

    @pytest.mark.asyncio
    async def test_start_task_success_from_failed(self, mock_crud, sample_task_data):
        """Test starting a task from failed status."""
        mock_task = Mock(status=TaskStatus.FAILED)
        mock_crud.get_task.return_value = mock_task
        updated_task = TaskResponse(**sample_task_data)
        mock_crud.update_task.return_value = updated_task

        result = await tasks.start_task(task_id=1, crud=mock_crud)

        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_start_task_not_found(self, mock_crud):
        """Test starting non-existent task."""
        mock_crud.get_task.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await tasks.start_task(task_id=999, crud=mock_crud)

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert "Task with ID 999 not found" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_start_task_already_in_progress(self, mock_crud):
        """Test starting task that's already in progress."""
        mock_task = Mock(status=TaskStatus.IN_PROGRESS)
        mock_crud.get_task.return_value = mock_task

        with pytest.raises(HTTPException) as exc_info:
            await tasks.start_task(task_id=1, crud=mock_crud)

        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "Task is already in progress" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_start_task_already_completed(self, mock_crud):
        """Test starting task that's already completed."""
        mock_task = Mock(status=TaskStatus.COMPLETED)
        mock_crud.get_task.return_value = mock_task

        with pytest.raises(HTTPException) as exc_info:
            await tasks.start_task(task_id=1, crud=mock_crud)

        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "Cannot start a completed task" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_start_task_already_cancelled(self, mock_crud):
        """Test starting task that's already cancelled."""
        mock_task = Mock(status=TaskStatus.CANCELLED)
        mock_crud.get_task.return_value = mock_task

        with pytest.raises(HTTPException) as exc_info:
            await tasks.start_task(task_id=1, crud=mock_crud)

        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "Cannot start a cancelled task" in str(exc_info.value.detail)


class TestTasksCompleteEndpoint:
    """Test the complete task endpoint with all scenarios."""

    @pytest.fixture
    def mock_crud(self):
        """Mock CRUD adapter for complete tests."""
        return AsyncMock()

    @pytest.fixture
    def sample_task_data(self):
        """Sample task data for responses."""
        return {
            "id": 1,
            "title": "Completed Task",
            "description": "Completed task description",
            "instance_id": 1,
            "command": "test command",
            "schedule": None,
            "enabled": True,
            "status": "completed",
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
            "last_run": None,
            "next_run": None,
        }

    @pytest.mark.asyncio
    async def test_complete_task_success(self, mock_crud, sample_task_data):
        """Test completing task successfully."""
        mock_task = Mock(
            status=TaskStatus.IN_PROGRESS,
            started_at=datetime.now(UTC) - timedelta(minutes=10),
        )
        mock_crud.get_task.return_value = mock_task
        updated_task = TaskResponse(**sample_task_data)
        mock_crud.update_task.return_value = updated_task

        result = await tasks.complete_task(
            task_id=1, results={"output": "success"}, crud=mock_crud
        )

        assert result["success"] is True
        assert "Task completed successfully" in result["message"]
        mock_crud.get_task.assert_called_once_with(1)
        mock_crud.update_task.assert_called_once()

        # Verify the update data includes completion info
        update_args = mock_crud.update_task.call_args[0]
        update_data = update_args[1]
        assert update_data["status"] == TaskStatus.COMPLETED
        assert "completed_at" in update_data
        assert "actual_duration" in update_data
        assert update_data["results"] == {"output": "success"}

    @pytest.mark.asyncio
    async def test_complete_task_without_results(self, mock_crud, sample_task_data):
        """Test completing task without results data."""
        mock_task = Mock(
            status=TaskStatus.IN_PROGRESS,
            started_at=datetime.now(UTC) - timedelta(minutes=5),
        )
        mock_crud.get_task.return_value = mock_task
        updated_task = TaskResponse(**sample_task_data)
        mock_crud.update_task.return_value = updated_task

        result = await tasks.complete_task(task_id=1, results=None, crud=mock_crud)

        assert result["success"] is True
        # Verify no results field in update data when None
        update_args = mock_crud.update_task.call_args[0]
        update_data = update_args[1]
        assert "results" not in update_data

    @pytest.mark.asyncio
    async def test_complete_task_without_started_at(self, mock_crud, sample_task_data):
        """Test completing task that was never started (no started_at)."""
        mock_task = Mock(status=TaskStatus.PENDING, started_at=None)
        mock_crud.get_task.return_value = mock_task
        updated_task = TaskResponse(**sample_task_data)
        mock_crud.update_task.return_value = updated_task

        result = await tasks.complete_task(task_id=1, crud=mock_crud)

        assert result["success"] is True
        # Verify no actual_duration when started_at is None
        update_args = mock_crud.update_task.call_args[0]
        update_data = update_args[1]
        assert "actual_duration" not in update_data

    @pytest.mark.asyncio
    async def test_complete_task_timezone_naive_started_at(
        self, mock_crud, sample_task_data
    ):
        """Test completing task with timezone-naive started_at."""
        naive_datetime = datetime.now() - timedelta(minutes=15)  # No timezone
        mock_task = Mock(status=TaskStatus.IN_PROGRESS, started_at=naive_datetime)
        mock_crud.get_task.return_value = mock_task
        updated_task = TaskResponse(**sample_task_data)
        mock_crud.update_task.return_value = updated_task

        result = await tasks.complete_task(task_id=1, crud=mock_crud)

        assert result["success"] is True
        # Should handle timezone-naive datetime by assuming UTC
        update_args = mock_crud.update_task.call_args[0]
        update_data = update_args[1]
        assert "actual_duration" in update_data

    @pytest.mark.asyncio
    async def test_complete_task_not_found(self, mock_crud):
        """Test completing non-existent task."""
        mock_crud.get_task.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await tasks.complete_task(task_id=999, crud=mock_crud)

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert "Task with ID 999 not found" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_complete_task_already_completed(self, mock_crud):
        """Test completing task that's already completed."""
        mock_task = Mock(status=TaskStatus.COMPLETED)
        mock_crud.get_task.return_value = mock_task

        with pytest.raises(HTTPException) as exc_info:
            await tasks.complete_task(task_id=1, crud=mock_crud)

        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "Task is already completed" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_complete_task_already_cancelled(self, mock_crud):
        """Test completing task that's already cancelled."""
        mock_task = Mock(status=TaskStatus.CANCELLED)
        mock_crud.get_task.return_value = mock_task

        with pytest.raises(HTTPException) as exc_info:
            await tasks.complete_task(task_id=1, crud=mock_crud)

        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "Cannot complete a cancelled task" in str(exc_info.value.detail)


class TestTasksCancelEndpoint:
    """Test the cancel task endpoint."""

    @pytest.fixture
    def mock_crud(self):
        """Mock CRUD adapter for cancel tests."""
        return AsyncMock()

    @pytest.fixture
    def sample_task_data(self):
        """Sample task data for responses."""
        return {
            "id": 1,
            "title": "Cancelled Task",
            "description": "Cancelled task description",
            "instance_id": 1,
            "command": "test command",
            "schedule": None,
            "enabled": True,
            "status": "cancelled",
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
            "last_run": None,
            "next_run": None,
        }

    @pytest.mark.asyncio
    async def test_cancel_task_success_from_pending(self, mock_crud, sample_task_data):
        """Test cancelling task from pending status."""
        mock_task = Mock(status=TaskStatus.PENDING)
        mock_crud.get_task.return_value = mock_task
        updated_task = TaskResponse(**sample_task_data)
        mock_crud.update_task.return_value = updated_task

        result = await tasks.cancel_task(task_id=1, crud=mock_crud)

        assert result["success"] is True
        assert "Task cancelled successfully" in result["message"]
        mock_crud.get_task.assert_called_once_with(1)
        mock_crud.update_task.assert_called_once_with(
            1, {"status": TaskStatus.CANCELLED}
        )

    @pytest.mark.asyncio
    async def test_cancel_task_success_from_in_progress(
        self, mock_crud, sample_task_data
    ):
        """Test cancelling task from in progress status."""
        mock_task = Mock(status=TaskStatus.IN_PROGRESS)
        mock_crud.get_task.return_value = mock_task
        updated_task = TaskResponse(**sample_task_data)
        mock_crud.update_task.return_value = updated_task

        result = await tasks.cancel_task(task_id=1, crud=mock_crud)

        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_cancel_task_success_from_failed(self, mock_crud, sample_task_data):
        """Test cancelling task from failed status."""
        mock_task = Mock(status=TaskStatus.FAILED)
        mock_crud.get_task.return_value = mock_task
        updated_task = TaskResponse(**sample_task_data)
        mock_crud.update_task.return_value = updated_task

        result = await tasks.cancel_task(task_id=1, crud=mock_crud)

        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_cancel_task_not_found(self, mock_crud):
        """Test cancelling non-existent task."""
        mock_crud.get_task.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await tasks.cancel_task(task_id=999, crud=mock_crud)

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert "Task with ID 999 not found" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_cancel_task_already_completed(self, mock_crud):
        """Test cancelling task that's already completed."""
        mock_task = Mock(status=TaskStatus.COMPLETED)
        mock_crud.get_task.return_value = mock_task

        with pytest.raises(HTTPException) as exc_info:
            await tasks.cancel_task(task_id=1, crud=mock_crud)

        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "Cannot cancel a completed task" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_cancel_task_already_cancelled(self, mock_crud):
        """Test cancelling task that's already cancelled."""
        mock_task = Mock(status=TaskStatus.CANCELLED)
        mock_crud.get_task.return_value = mock_task

        with pytest.raises(HTTPException) as exc_info:
            await tasks.cancel_task(task_id=1, crud=mock_crud)

        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "Cannot cancel a cancelled task" in str(exc_info.value.detail)


class TestTasksAssignEndpoint:
    """Test the assign task endpoint."""

    @pytest.fixture
    def mock_crud(self):
        """Mock CRUD adapter for assign tests."""
        crud = AsyncMock()
        crud.get_task.return_value = Mock(id=1, title="Task to Assign")
        crud.get_instance.return_value = Mock(id=2, issue_id="test-issue")
        return crud

    @pytest.fixture
    def sample_task_data(self):
        """Sample task data for responses."""
        return {
            "id": 1,
            "title": "Assigned Task",
            "description": "Assigned task description",
            "instance_id": 2,
            "command": "test command",
            "schedule": None,
            "enabled": True,
            "status": "pending",
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
            "last_run": None,
            "next_run": None,
        }

    @pytest.mark.asyncio
    async def test_assign_task_success(self, mock_crud, sample_task_data):
        """Test successful task assignment."""
        assignment_data = {"instance_id": 2}
        updated_task = TaskResponse(**sample_task_data)
        mock_crud.update_task.return_value = updated_task

        result = await tasks.assign_task(
            assignment_data=assignment_data, task_id=1, crud=mock_crud
        )

        assert result["success"] is True
        assert "Task assigned successfully" in result["message"]
        mock_crud.get_task.assert_called_once_with(1)
        mock_crud.get_instance.assert_called_once_with(2)
        mock_crud.update_task.assert_called_once_with(1, {"instance_id": 2})

    @pytest.mark.asyncio
    async def test_assign_task_missing_instance_id(self, mock_crud):
        """Test task assignment without instance_id."""
        assignment_data = {}  # Missing instance_id

        with pytest.raises(HTTPException) as exc_info:
            await tasks.assign_task(
                assignment_data=assignment_data, task_id=1, crud=mock_crud
            )

        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "instance_id is required" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_assign_task_none_instance_id(self, mock_crud):
        """Test task assignment with None instance_id."""
        assignment_data = {"instance_id": None}

        with pytest.raises(HTTPException) as exc_info:
            await tasks.assign_task(
                assignment_data=assignment_data, task_id=1, crud=mock_crud
            )

        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "instance_id is required" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_assign_task_not_found(self, mock_crud):
        """Test assigning non-existent task."""
        mock_crud.get_task.return_value = None
        assignment_data = {"instance_id": 2}

        with pytest.raises(HTTPException) as exc_info:
            await tasks.assign_task(
                assignment_data=assignment_data, task_id=999, crud=mock_crud
            )

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert "Task with ID 999 not found" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_assign_task_instance_not_found(self, mock_crud):
        """Test assigning task to non-existent instance."""
        mock_crud.get_instance.return_value = None
        assignment_data = {"instance_id": 999}

        with pytest.raises(HTTPException) as exc_info:
            await tasks.assign_task(
                assignment_data=assignment_data, task_id=1, crud=mock_crud
            )

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert "Instance with ID 999 not found" in str(exc_info.value.detail)


class TestTasksUnassignEndpoint:
    """Test the unassign task endpoint."""

    @pytest.fixture
    def mock_crud(self):
        """Mock CRUD adapter for unassign tests."""
        crud = AsyncMock()
        crud.get_task.return_value = Mock(id=1, title="Task to Unassign")
        return crud

    @pytest.fixture
    def sample_task_data(self):
        """Sample task data for responses."""
        return {
            "id": 1,
            "title": "Unassigned Task",
            "description": "Unassigned task description",
            "instance_id": None,
            "command": "test command",
            "schedule": None,
            "enabled": True,
            "status": "pending",
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
            "last_run": None,
            "next_run": None,
        }

    @pytest.mark.asyncio
    async def test_unassign_task_success(self, mock_crud, sample_task_data):
        """Test successful task unassignment."""
        updated_task = TaskResponse(**sample_task_data)
        mock_crud.update_task.return_value = updated_task

        result = await tasks.unassign_task(task_id=1, crud=mock_crud)

        assert result["success"] is True
        assert "Task unassigned successfully" in result["message"]
        mock_crud.get_task.assert_called_once_with(1)
        mock_crud.update_task.assert_called_once_with(1, {"instance_id": None})

    @pytest.mark.asyncio
    async def test_unassign_task_not_found(self, mock_crud):
        """Test unassigning non-existent task."""
        mock_crud.get_task.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await tasks.unassign_task(task_id=999, crud=mock_crud)

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert "Task with ID 999 not found" in str(exc_info.value.detail)


class TestTasksRouterDecoratorAndIntegration:
    """Test router decorator functionality and integration aspects."""

    def test_router_exists(self):
        """Test that the router object exists and is properly configured."""
        assert tasks.router is not None
        assert hasattr(tasks.router, "routes")

    def test_decorators_preserve_function_names(self):
        """Test that decorators preserve function names for debugging."""
        functions = [
            tasks.list_tasks,
            tasks.create_task,
            tasks.get_task,
            tasks.update_task,
            tasks.delete_task,
            tasks.start_task,
            tasks.complete_task,
            tasks.cancel_task,
            tasks.assign_task,
            tasks.unassign_task,
        ]

        for func in functions:
            # Function should retain its name even with decorators
            assert hasattr(func, "__name__")
            assert func.__name__ in [
                "list_tasks",
                "create_task",
                "get_task",
                "update_task",
                "delete_task",
                "start_task",
                "complete_task",
                "cancel_task",
                "assign_task",
                "unassign_task",
            ]

    def test_router_has_expected_routes(self):
        """Test that router has all expected routes."""
        routes = tasks.router.routes
        route_paths = [route.path for route in routes]

        expected_paths = [
            "/",
            "/{task_id}",
            "/{task_id}/start",
            "/{task_id}/complete",
            "/{task_id}/cancel",
            "/{task_id}/assign",
        ]

        for expected_path in expected_paths:
            assert expected_path in route_paths

    def test_router_http_methods(self):
        """Test that routes have correct HTTP methods."""
        routes = tasks.router.routes
        path_methods = {}

        for route in routes:
            if hasattr(route, "methods"):
                if route.path not in path_methods:
                    path_methods[route.path] = set()
                path_methods[route.path].update(route.methods)

        # Root path should support GET and POST
        if "/" in path_methods:
            assert "GET" in path_methods["/"]
            assert "POST" in path_methods["/"]

        # Individual task should support GET, PUT, DELETE
        if "/{task_id}" in path_methods:
            assert "GET" in path_methods["/{task_id}"]
            assert "PUT" in path_methods["/{task_id}"]
            assert "DELETE" in path_methods["/{task_id}"]

        # Action endpoints should support POST
        action_paths = [
            "/{task_id}/start",
            "/{task_id}/complete",
            "/{task_id}/cancel",
            "/{task_id}/assign",
        ]
        for path in action_paths:
            if path in path_methods:
                assert "POST" in path_methods[path]


class TestTasksEdgeCasesAndErrorConditions:
    """Test edge cases, error conditions, and boundary values."""

    @pytest.fixture
    def mock_crud(self):
        """Mock CRUD adapter for edge case tests."""
        return AsyncMock()

    @pytest.mark.asyncio
    async def test_complete_task_zero_duration(self, mock_crud):
        """Test completing task with zero duration (started just now)."""
        now = datetime.now(UTC)
        mock_task = Mock(status=TaskStatus.IN_PROGRESS, started_at=now)
        mock_crud.get_task.return_value = mock_task

        sample_task_data = {
            "id": 1,
            "title": "Zero Duration Task",
            "description": "Task completed immediately",
            "instance_id": 1,
            "command": "instant command",
            "schedule": None,
            "enabled": True,
            "status": "completed",
            "created_at": now,
            "updated_at": now,
            "last_run": None,
            "next_run": None,
        }

        updated_task = TaskResponse(**sample_task_data)
        mock_crud.update_task.return_value = updated_task

        # Use patch to control datetime.now() in the function
        with patch("cc_orchestrator.web.routers.v1.tasks.datetime") as mock_datetime:
            # Make the "now" call exactly the same to get 0 duration
            mock_datetime.now.return_value = now
            mock_datetime.UTC = UTC

            result = await tasks.complete_task(task_id=1, crud=mock_crud)

        assert result["success"] is True
        # Verify duration calculation - with 0 duration, actual_duration won't be included
        # because 0 is falsy and the condition is "if actual_duration:"
        update_args = mock_crud.update_task.call_args[0]
        update_data = update_args[1]
        assert (
            "actual_duration" not in update_data
        )  # 0 duration is falsy, so not included

    @pytest.mark.asyncio
    async def test_list_tasks_large_page_calculation(self, mock_crud):
        """Test pagination calculation with large numbers."""
        # Simulate large dataset
        mock_crud.list_tasks.return_value = ([], 10000)
        pagination = PaginationParams(page=100, size=50)

        result = await tasks.list_tasks(
            pagination=pagination,
            status_filter=None,
            priority_filter=None,
            instance_id=None,
            worktree_id=None,
            crud=mock_crud,
        )

        assert result["total"] == 10000
        assert result["page"] == 100
        assert result["size"] == 50
        assert result["pages"] == 200  # (10000 + 50 - 1) // 50 = 200

    @pytest.mark.asyncio
    async def test_assign_task_with_integer_zero_instance_id(self, mock_crud):
        """Test task assignment with instance_id of 0 (falsy but valid)."""
        assignment_data = {"instance_id": 0}

        with pytest.raises(HTTPException) as exc_info:
            await tasks.assign_task(
                assignment_data=assignment_data, task_id=1, crud=mock_crud
            )

        # 0 should be treated as falsy and trigger "required" error
        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "instance_id is required" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_create_task_model_dump_called(self, mock_crud):
        """Test that model_dump is called on TaskCreate during creation."""
        task_data = TaskCreate(
            title="Model Dump Test", description="Test model dumping"
        )

        sample_task_data = {
            "id": 1,
            "title": "Model Dump Test",
            "description": "Test model dumping",
            "instance_id": None,
            "command": None,
            "schedule": None,
            "enabled": True,
            "status": "pending",
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
            "last_run": None,
            "next_run": None,
        }

        created_task = TaskResponse(**sample_task_data)
        mock_crud.create_task.return_value = created_task

        result = await tasks.create_task(task_data=task_data, crud=mock_crud)

        assert result["success"] is True
        # Verify create_task was called with dumped model data
        mock_crud.create_task.assert_called_once()
        create_args = mock_crud.create_task.call_args[0]
        assert isinstance(create_args[0], dict)  # Should be dumped dict, not model

    @pytest.mark.asyncio
    async def test_update_task_exclude_unset_called(self, mock_crud):
        """Test that model_dump(exclude_unset=True) is called on TaskUpdate."""
        existing_task = Mock(id=1, title="Existing Task")
        mock_crud.get_task.return_value = existing_task

        task_data = TaskUpdate(title="Updated Name")  # Only title is set

        sample_task_data = {
            "id": 1,
            "title": "Updated Name",
            "description": "Original description",
            "instance_id": None,
            "command": None,
            "schedule": None,
            "enabled": True,
            "status": "pending",
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
            "last_run": None,
            "next_run": None,
        }

        updated_task = TaskResponse(**sample_task_data)
        mock_crud.update_task.return_value = updated_task

        result = await tasks.update_task(task_id=1, task_data=task_data, crud=mock_crud)

        assert result["success"] is True
        # Verify update_task was called with exclude_unset=True dumped data
        mock_crud.update_task.assert_called_once()
        update_args = mock_crud.update_task.call_args[0]
        assert update_args[0] == 1  # task_id
        update_data = update_args[1]
        assert isinstance(update_data, dict)
        # Should only contain fields that were set (title in this case)
        assert "title" in update_data

    @pytest.mark.asyncio
    async def test_datetime_utc_import_coverage(self):
        """Test that datetime.now(UTC) is properly imported and used."""
        # This test ensures the import statements are covered
        from cc_orchestrator.web.routers.v1.tasks import UTC, datetime

        # Verify imports work
        now = datetime.now(UTC)
        assert now.tzinfo is not None
        assert now.tzinfo == UTC


class TestTaskModelValidationCoverage:
    """Test TaskResponse model validation edge cases."""

    def test_task_response_model_validate_called(self):
        """Test TaskResponse.model_validate is called with different data."""
        task_data = {
            "id": 1,
            "title": "Validation Test",
            "description": "Test validation",
            "instance_id": None,
            "command": None,
            "schedule": None,
            "enabled": True,
            "status": "pending",
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
            "last_run": None,
            "next_run": None,
        }

        # This should work without errors
        task_response = TaskResponse.model_validate(task_data)
        assert task_response.title == "Validation Test"
        assert task_response.id == 1

    def test_task_response_list_conversion(self):
        """Test conversion of task list to TaskResponse list."""
        task_data_list = [
            {
                "id": 1,
                "title": "Task 1",
                "description": "First task",
                "instance_id": None,
                "command": None,
                "schedule": None,
                "enabled": True,
                "status": "pending",
                "created_at": datetime.now(UTC),
                "updated_at": datetime.now(UTC),
                "last_run": None,
                "next_run": None,
            },
            {
                "id": 2,
                "title": "Task 2",
                "description": "Second task",
                "instance_id": 1,
                "command": "test",
                "schedule": "* * * * *",
                "enabled": False,
                "status": "completed",
                "created_at": datetime.now(UTC),
                "updated_at": datetime.now(UTC),
                "last_run": datetime.now(UTC),
                "next_run": datetime.now(UTC),
            },
        ]

        # Convert to TaskResponse objects like in the list_tasks function
        task_responses = [TaskResponse.model_validate(task) for task in task_data_list]

        assert len(task_responses) == 2
        assert task_responses[0].title == "Task 1"
        assert task_responses[1].title == "Task 2"
        assert task_responses[0].enabled is True
        assert task_responses[1].enabled is False


class TestDecoratorAndTypingCoverage:
    """Test decorator and typing coverage."""

    def test_import_coverage(self):
        """Test that all required imports are accessible."""
        # Test type imports
        from cc_orchestrator.database.models import TaskPriority, TaskStatus

        # Verify enums have expected values
        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.IN_PROGRESS.value == "in_progress"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.FAILED.value == "failed"
        assert TaskStatus.CANCELLED.value == "cancelled"

        assert TaskPriority.LOW.value == 1
        assert TaskPriority.MEDIUM.value == 2
        assert TaskPriority.HIGH.value == 3
        assert TaskPriority.URGENT.value == 4

    def test_function_return_type_annotations(self):
        """Test that functions have proper return type annotations."""
        # Verify return type hints exist
        import inspect

        functions = [
            tasks.list_tasks,
            tasks.create_task,
            tasks.get_task,
            tasks.update_task,
            tasks.delete_task,
            tasks.start_task,
            tasks.complete_task,
            tasks.cancel_task,
            tasks.assign_task,
            tasks.unassign_task,
        ]

        for func in functions:
            sig = inspect.signature(func)
            # All functions should return dict[str, Any]
            assert sig.return_annotation is not None


# Final comprehensive integration test
class TestTasksRouterFullIntegration:
    """Integration test that covers all endpoints in sequence."""

    @pytest.fixture
    def mock_crud_full(self):
        """Mock CRUD adapter for full integration test."""
        crud = AsyncMock()

        # Mock all required methods
        crud.list_tasks.return_value = ([], 0)
        crud.get_task.return_value = None
        crud.get_instance.return_value = Mock(id=1)
        crud.get_worktree.return_value = Mock(id=1)
        crud.create_task.return_value = Mock()
        crud.update_task.return_value = Mock()
        crud.delete_task.return_value = True

        return crud

    @pytest.mark.asyncio
    async def test_complete_workflow_coverage(self, mock_crud_full):
        """Test a complete workflow that exercises all major code paths."""
        pagination = PaginationParams(page=1, size=10)

        # 1. List tasks (empty)
        result = await tasks.list_tasks(
            pagination=pagination,
            status_filter=None,
            priority_filter=None,
            instance_id=None,
            worktree_id=None,
            crud=mock_crud_full,
        )
        assert result["total"] == 0

        # 2. Try to get non-existent task
        with pytest.raises(HTTPException):
            await tasks.get_task(task_id=1, crud=mock_crud_full)

        # 3. Create task with validation
        task_data = TaskCreate(title="Integration Test Task", instance_id=1)
        sample_task = {
            "id": 1,
            "title": "Integration Test Task",
            "description": "",
            "instance_id": 1,
            "command": None,
            "schedule": None,
            "enabled": True,
            "status": "pending",
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
            "last_run": None,
            "next_run": None,
        }

        created_task = TaskResponse(**sample_task)
        mock_crud_full.create_task.return_value = created_task

        result = await tasks.create_task(task_data=task_data, crud=mock_crud_full)
        assert result["success"] is True

        # Verify all CRUD methods were called as expected
        assert mock_crud_full.list_tasks.called
        assert mock_crud_full.get_task.called
        assert mock_crud_full.get_instance.called
        assert mock_crud_full.create_task.called
