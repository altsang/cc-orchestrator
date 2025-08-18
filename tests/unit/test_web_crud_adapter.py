"""Comprehensive tests for web CRUD adapter module."""

import asyncio
from datetime import datetime
from unittest.mock import Mock, patch

import pytest
from sqlalchemy.orm import Session

from cc_orchestrator.database.models import (
    ConfigScope,
    Configuration,
    HealthCheck,
    HealthStatus,
    Instance,
    InstanceStatus,
    Task,
    TaskPriority,
    TaskStatus,
    Worktree,
    WorktreeStatus,
)
from cc_orchestrator.web.crud_adapter import Alert, CRUDBase, RecoveryAttempt


@pytest.fixture
def mock_session():
    """Create a mock database session."""
    session = Mock(spec=Session)
    session.is_active = True
    return session


@pytest.fixture
def crud_adapter(mock_session):
    """Create a CRUD adapter instance."""
    return CRUDBase(mock_session)


class TestPlaceholderModels:
    """Test placeholder model classes."""

    def test_alert_creation(self):
        """Test Alert model creation."""
        alert = Alert(
            instance_id=1,
            alert_id="test-alert",
            level="warning",
            message="Test message",
        )

        assert alert.instance_id == 1
        assert alert.alert_id == "test-alert"
        assert alert.level == "warning"
        assert alert.message == "Test message"
        assert hasattr(alert, "created_at")
        assert alert.id == 1

    def test_alert_default_attributes(self):
        """Test Alert model with minimal attributes."""
        alert = Alert()

        assert hasattr(alert, "created_at")
        assert alert.id == 1
        assert alert.level == "info"

    def test_recovery_attempt_creation(self):
        """Test RecoveryAttempt model creation."""
        attempt = RecoveryAttempt(
            instance_id=1, attempt_type="restart", status="completed"
        )

        assert attempt.instance_id == 1
        assert attempt.attempt_type == "restart"
        assert attempt.status == "completed"
        assert hasattr(attempt, "created_at")
        assert attempt.id == 1

    def test_recovery_attempt_default_attributes(self):
        """Test RecoveryAttempt model with minimal attributes."""
        attempt = RecoveryAttempt()

        assert hasattr(attempt, "created_at")
        assert attempt.id == 1


class TestCRUDBaseInitialization:
    """Test CRUD adapter initialization."""

    def test_initialization(self, mock_session):
        """Test CRUD adapter initialization."""
        adapter = CRUDBase(mock_session)
        assert adapter.session is mock_session


class TestInstanceOperations:
    """Test instance CRUD operations."""

    @pytest.mark.asyncio
    async def test_list_instances_no_filters(self, crud_adapter, mock_session):
        """Test listing instances without filters."""
        mock_instances = [
            Mock(spec=Instance, id=1, issue_id="issue-1"),
            Mock(spec=Instance, id=2, issue_id="issue-2"),
        ]

        with patch("cc_orchestrator.web.crud_adapter.InstanceCRUD") as mock_crud:
            mock_crud.list_all.return_value = mock_instances

            instances, total = await crud_adapter.list_instances(offset=0, limit=20)

            assert instances == mock_instances
            assert total == 2
            # The actual implementation doesn't pass limit/offset to list_all
            mock_crud.list_all.assert_called_with(mock_session, status=None)

    @pytest.mark.asyncio
    async def test_list_instances_with_status_filter(self, crud_adapter, mock_session):
        """Test listing instances with status filter."""
        mock_instances = [Mock(spec=Instance, id=1, issue_id="issue-1")]

        with patch("cc_orchestrator.web.crud_adapter.InstanceCRUD") as mock_crud:
            mock_crud.list_all.return_value = mock_instances

            instances, total = await crud_adapter.list_instances(
                filters={"status": "running"}
            )

            assert instances == mock_instances
            assert total == 1
            # Should convert string status to enum
            assert mock_crud.list_all.call_args[1]["status"] == InstanceStatus.RUNNING

    @pytest.mark.asyncio
    async def test_list_instances_with_enum_status_filter(
        self, crud_adapter, mock_session
    ):
        """Test listing instances with enum status filter."""
        mock_instances = [Mock(spec=Instance, id=1, issue_id="issue-1")]

        with patch("cc_orchestrator.web.crud_adapter.InstanceCRUD") as mock_crud:
            mock_crud.list_all.return_value = mock_instances

            instances, total = await crud_adapter.list_instances(
                filters={"status": InstanceStatus.RUNNING}
            )

            assert instances == mock_instances
            assert total == 1
            mock_crud.list_all.assert_called_with(
                mock_session, status=InstanceStatus.RUNNING
            )

    @pytest.mark.asyncio
    async def test_create_instance_basic(self, crud_adapter, mock_session):
        """Test creating an instance with basic data."""
        mock_instance = Mock(spec=Instance, id=1, issue_id="issue-1")
        instance_data = {
            "issue_id": "issue-1",
            "workspace_path": "/path/to/workspace",
            "branch_name": "feature-branch",
        }

        with patch("cc_orchestrator.web.crud_adapter.InstanceCRUD") as mock_crud:
            mock_crud.create.return_value = mock_instance

            result = await crud_adapter.create_instance(instance_data)

            assert result == mock_instance
            mock_crud.create.assert_called_once_with(
                mock_session,
                issue_id="issue-1",
                workspace_path="/path/to/workspace",
                branch_name="feature-branch",
                tmux_session=None,
                extra_metadata={},
            )

    @pytest.mark.asyncio
    async def test_create_instance_with_status(self, crud_adapter, mock_session):
        """Test creating an instance with status."""
        mock_instance = Mock(spec=Instance, id=1, issue_id="issue-1")
        instance_data = {"issue_id": "issue-1", "status": "running"}

        with patch("cc_orchestrator.web.crud_adapter.InstanceCRUD") as mock_crud:
            mock_crud.create.return_value = mock_instance

            result = await crud_adapter.create_instance(instance_data)

            assert result == mock_instance
            assert mock_instance.status == InstanceStatus.RUNNING
            mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_instance_with_enum_status(self, crud_adapter, mock_session):
        """Test creating an instance with enum status."""
        mock_instance = Mock(spec=Instance, id=1, issue_id="issue-1")
        instance_data = {"issue_id": "issue-1", "status": InstanceStatus.STOPPED}

        with patch("cc_orchestrator.web.crud_adapter.InstanceCRUD") as mock_crud:
            mock_crud.create.return_value = mock_instance

            result = await crud_adapter.create_instance(instance_data)

            assert result == mock_instance
            assert mock_instance.status == InstanceStatus.STOPPED

    @pytest.mark.asyncio
    async def test_get_instance_success(self, crud_adapter, mock_session):
        """Test getting an instance by ID successfully."""
        mock_instance = Mock(spec=Instance, id=1, issue_id="issue-1")

        with patch("cc_orchestrator.web.crud_adapter.InstanceCRUD") as mock_crud:
            mock_crud.get_by_id.return_value = mock_instance

            result = await crud_adapter.get_instance(1)

            assert result == mock_instance
            mock_crud.get_by_id.assert_called_once_with(mock_session, 1)

    @pytest.mark.asyncio
    async def test_get_instance_not_found(self, crud_adapter, mock_session):
        """Test getting an instance that doesn't exist."""
        with patch("cc_orchestrator.web.crud_adapter.InstanceCRUD") as mock_crud:
            mock_crud.get_by_id.side_effect = Exception("Not found")

            result = await crud_adapter.get_instance(999)

            assert result is None

    @pytest.mark.asyncio
    async def test_get_instance_inactive_session(self, crud_adapter):
        """Test getting an instance with inactive session."""
        crud_adapter.session.is_active = False

        result = await crud_adapter.get_instance(1)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_instance_by_issue_id_success(self, crud_adapter, mock_session):
        """Test getting an instance by issue ID successfully."""
        mock_instance = Mock(spec=Instance, id=1, issue_id="issue-1")

        with patch("cc_orchestrator.web.crud_adapter.InstanceCRUD") as mock_crud:
            mock_crud.get_by_issue_id.return_value = mock_instance

            result = await crud_adapter.get_instance_by_issue_id("issue-1")

            assert result == mock_instance
            mock_crud.get_by_issue_id.assert_called_once_with(mock_session, "issue-1")

    @pytest.mark.asyncio
    async def test_get_instance_by_issue_id_not_found(self, crud_adapter, mock_session):
        """Test getting an instance by issue ID that doesn't exist."""
        with patch("cc_orchestrator.web.crud_adapter.InstanceCRUD") as mock_crud:
            mock_crud.get_by_issue_id.side_effect = Exception("Not found")

            result = await crud_adapter.get_instance_by_issue_id("nonexistent")

            assert result is None

    @pytest.mark.asyncio
    async def test_update_instance_with_string_status(self, crud_adapter, mock_session):
        """Test updating an instance with string status."""
        mock_instance = Mock(spec=Instance, id=1, issue_id="issue-1")
        update_data = {"status": "STOPPED"}

        with patch("cc_orchestrator.web.crud_adapter.InstanceCRUD") as mock_crud:
            mock_crud.update.return_value = mock_instance

            result = await crud_adapter.update_instance(1, update_data)

            assert result == mock_instance
            # Should convert to lowercase and then to enum
            expected_data = {"status": InstanceStatus.STOPPED}
            mock_crud.update.assert_called_once_with(mock_session, 1, **expected_data)

    @pytest.mark.asyncio
    async def test_update_instance_with_enum_status(self, crud_adapter, mock_session):
        """Test updating an instance with enum status."""
        mock_instance = Mock(spec=Instance, id=1, issue_id="issue-1")
        update_data = {"status": InstanceStatus.ERROR}

        with patch("cc_orchestrator.web.crud_adapter.InstanceCRUD") as mock_crud:
            mock_crud.update.return_value = mock_instance

            result = await crud_adapter.update_instance(1, update_data)

            assert result == mock_instance
            mock_crud.update.assert_called_once_with(mock_session, 1, **update_data)

    @pytest.mark.asyncio
    async def test_update_instance_other_fields(self, crud_adapter, mock_session):
        """Test updating an instance with non-status fields."""
        mock_instance = Mock(spec=Instance, id=1, issue_id="issue-1")
        update_data = {"workspace_path": "/new/path", "branch_name": "new-branch"}

        with patch("cc_orchestrator.web.crud_adapter.InstanceCRUD") as mock_crud:
            mock_crud.update.return_value = mock_instance

            result = await crud_adapter.update_instance(1, update_data)

            assert result == mock_instance
            mock_crud.update.assert_called_once_with(mock_session, 1, **update_data)

    @pytest.mark.asyncio
    async def test_delete_instance(self, crud_adapter, mock_session):
        """Test deleting an instance."""
        with patch("cc_orchestrator.web.crud_adapter.InstanceCRUD") as mock_crud:
            await crud_adapter.delete_instance(1)

            mock_crud.delete.assert_called_once_with(mock_session, 1)


class TestTaskOperations:
    """Test task CRUD operations."""

    @pytest.mark.asyncio
    async def test_list_tasks_by_instance(self, crud_adapter, mock_session):
        """Test listing tasks filtered by instance ID."""
        mock_tasks = [
            Mock(spec=Task, id=1, title="Task 1"),
            Mock(spec=Task, id=2, title="Task 2"),
        ]

        with patch("cc_orchestrator.web.crud_adapter.TaskCRUD") as mock_crud:
            mock_crud.list_by_instance.return_value = mock_tasks

            tasks, total = await crud_adapter.list_tasks(
                offset=0, limit=10, filters={"instance_id": 1}
            )

            assert tasks == mock_tasks
            assert total == 2
            mock_crud.list_by_instance.assert_called_once_with(
                mock_session, 1, status=None
            )

    @pytest.mark.asyncio
    async def test_list_tasks_by_instance_with_status(self, crud_adapter, mock_session):
        """Test listing tasks by instance with status filter."""
        mock_tasks = [Mock(spec=Task, id=1, title="Task 1")]

        with patch("cc_orchestrator.web.crud_adapter.TaskCRUD") as mock_crud:
            mock_crud.list_by_instance.return_value = mock_tasks

            tasks, total = await crud_adapter.list_tasks(
                filters={"instance_id": 1, "status": "pending"}
            )

            assert tasks == mock_tasks
            assert total == 1
            mock_crud.list_by_instance.assert_called_once_with(
                mock_session, 1, status=TaskStatus.PENDING
            )

    @pytest.mark.asyncio
    async def test_list_tasks_pending_only(self, crud_adapter, mock_session):
        """Test listing pending tasks without instance filter."""
        mock_tasks = [Mock(spec=Task, id=1, title="Task 1")]

        with patch("cc_orchestrator.web.crud_adapter.TaskCRUD") as mock_crud:
            mock_crud.list_pending.return_value = mock_tasks

            tasks, total = await crud_adapter.list_tasks(offset=0, limit=10)

            assert tasks == mock_tasks
            assert total == 1
            # The actual implementation doesn't pass limit to list_pending
            mock_crud.list_pending.assert_called_with(mock_session)

    @pytest.mark.asyncio
    async def test_list_tasks_pending_with_offset(self, crud_adapter, mock_session):
        """Test listing pending tasks with offset."""
        mock_tasks = [
            Mock(spec=Task, id=1, title="Task 1"),
            Mock(spec=Task, id=2, title="Task 2"),
            Mock(spec=Task, id=3, title="Task 3"),
        ]

        with patch("cc_orchestrator.web.crud_adapter.TaskCRUD") as mock_crud:
            mock_crud.list_pending.return_value = mock_tasks

            tasks, total = await crud_adapter.list_tasks(offset=1, limit=10)

            # Should skip first task due to offset
            assert len(tasks) == 2
            assert tasks[0].id == 2
            assert tasks[1].id == 3
            assert total == 3

    @pytest.mark.asyncio
    async def test_create_task_with_string_priority_bug(
        self, crud_adapter, mock_session
    ):
        """Test creating a task with string priority (should work correctly now)."""
        mock_task = Mock(spec=Task, id=1, title="Test Task")
        task_data = {
            "title": "Test Task",
            "priority": "HIGH",  # Should now convert to TaskPriority.HIGH
        }

        with patch("cc_orchestrator.web.crud_adapter.TaskCRUD") as mock_crud:
            mock_crud.create.return_value = mock_task

            result = await crud_adapter.create_task(task_data)

            assert result == mock_task
            # Should convert string to enum correctly
            assert mock_crud.create.call_args[1]["priority"] == TaskPriority.HIGH

    @pytest.mark.asyncio
    async def test_create_task_with_int_priority(self, crud_adapter, mock_session):
        """Test creating a task with integer priority."""
        mock_task = Mock(spec=Task, id=1, title="Test Task")
        task_data = {"title": "Test Task", "priority": 4}  # URGENT

        with patch("cc_orchestrator.web.crud_adapter.TaskCRUD") as mock_crud:
            mock_crud.create.return_value = mock_task

            result = await crud_adapter.create_task(task_data)

            assert result == mock_task
            # Should convert int to enum
            assert mock_crud.create.call_args[1]["priority"] == TaskPriority.URGENT

    @pytest.mark.asyncio
    async def test_create_task_with_invalid_int_priority(
        self, crud_adapter, mock_session
    ):
        """Test creating a task with invalid integer priority."""
        mock_task = Mock(spec=Task, id=1, title="Test Task")
        task_data = {"title": "Test Task", "priority": 99}  # Invalid

        with patch("cc_orchestrator.web.crud_adapter.TaskCRUD") as mock_crud:
            mock_crud.create.return_value = mock_task

            result = await crud_adapter.create_task(task_data)

            assert result == mock_task
            # Should default to MEDIUM
            assert mock_crud.create.call_args[1]["priority"] == TaskPriority.MEDIUM

    @pytest.mark.asyncio
    async def test_create_task_default_priority(self, crud_adapter, mock_session):
        """Test creating a task with default priority."""
        mock_task = Mock(spec=Task, id=1, title="Test Task")
        task_data = {"title": "Test Task"}

        with patch("cc_orchestrator.web.crud_adapter.TaskCRUD") as mock_crud:
            mock_crud.create.return_value = mock_task

            result = await crud_adapter.create_task(task_data)

            assert result == mock_task
            # Should use default priority (MEDIUM = 2)
            assert mock_crud.create.call_args[1]["priority"] == TaskPriority.MEDIUM

    @pytest.mark.asyncio
    async def test_get_task_success(self, crud_adapter, mock_session):
        """Test getting a task by ID successfully."""
        mock_task = Mock(spec=Task, id=1, title="Test Task")

        with patch("cc_orchestrator.web.crud_adapter.TaskCRUD") as mock_crud:
            mock_crud.get_by_id.return_value = mock_task

            result = await crud_adapter.get_task(1)

            assert result == mock_task
            mock_crud.get_by_id.assert_called_once_with(mock_session, 1)

    @pytest.mark.asyncio
    async def test_get_task_not_found(self, crud_adapter, mock_session):
        """Test getting a task that doesn't exist."""
        with patch("cc_orchestrator.web.crud_adapter.TaskCRUD") as mock_crud:
            mock_crud.get_by_id.side_effect = Exception("Not found")

            result = await crud_adapter.get_task(999)

            assert result is None

    @pytest.mark.asyncio
    async def test_update_task_with_status(self, crud_adapter, mock_session):
        """Test updating a task with status change using enum directly."""
        mock_task = Mock(spec=Task, id=1, title="Test Task")
        update_data = {"status": TaskStatus.COMPLETED}  # Use enum directly to avoid bug

        with patch("cc_orchestrator.web.crud_adapter.TaskCRUD") as mock_crud:
            mock_crud.update_status.return_value = mock_task

            result = await crud_adapter.update_task(1, update_data)

            assert result == mock_task
            mock_crud.update_status.assert_called_once_with(
                mock_session, 1, TaskStatus.COMPLETED
            )

    @pytest.mark.asyncio
    async def test_update_task_with_string_status_bug(self, crud_adapter, mock_session):
        """Test updating a task with string status (should work correctly now)."""
        mock_task = Mock(spec=Task, id=1, title="Test Task")
        update_data = {"status": "completed"}  # lowercase string - should work

        with patch("cc_orchestrator.web.crud_adapter.TaskCRUD") as mock_crud:
            mock_crud.update_status.return_value = mock_task

            result = await crud_adapter.update_task(1, update_data)

            assert result == mock_task
            # Should convert string to enum correctly
            mock_crud.update_status.assert_called_once_with(
                mock_session, 1, TaskStatus.COMPLETED
            )

    @pytest.mark.asyncio
    async def test_update_task_without_status(self, crud_adapter, mock_session):
        """Test updating a task without status change."""
        mock_task = Mock(spec=Task, id=1, title="Test Task")
        update_data = {"instance_id": 2, "description": "Updated"}

        with patch("cc_orchestrator.web.crud_adapter.TaskCRUD") as mock_crud:
            mock_crud.update.return_value = mock_task

            result = await crud_adapter.update_task(1, update_data)

            assert result == mock_task
            mock_crud.update.assert_called_once_with(mock_session, 1, **update_data)

    @pytest.mark.asyncio
    async def test_delete_task(self, crud_adapter, mock_session):
        """Test deleting a task (validation only)."""
        mock_task = Mock(spec=Task, id=1, title="Test Task")

        with patch("cc_orchestrator.web.crud_adapter.TaskCRUD") as mock_crud:
            mock_crud.get_by_id.return_value = mock_task

            await crud_adapter.delete_task(1)

            # Should validate task exists
            mock_crud.get_by_id.assert_called_once_with(mock_session, 1)


class TestWorktreeOperations:
    """Test worktree CRUD operations."""

    @pytest.mark.asyncio
    async def test_list_worktrees_no_filters(self, crud_adapter, mock_session):
        """Test listing worktrees without filters."""
        mock_worktrees = [
            Mock(spec=Worktree, id=1, name="worktree-1"),
            Mock(spec=Worktree, id=2, name="worktree-2"),
        ]

        with patch("cc_orchestrator.web.crud_adapter.WorktreeCRUD") as mock_crud:
            mock_crud.list_all.return_value = mock_worktrees

            worktrees, total = await crud_adapter.list_worktrees()

            assert worktrees == mock_worktrees
            assert total == 2
            mock_crud.list_all.assert_called_once_with(mock_session)

    @pytest.mark.asyncio
    async def test_list_worktrees_with_status_filter(self, crud_adapter, mock_session):
        """Test listing worktrees with status filter."""
        mock_worktrees = [Mock(spec=Worktree, id=1, name="worktree-1")]

        with patch("cc_orchestrator.web.crud_adapter.WorktreeCRUD") as mock_crud:
            mock_crud.list_by_status.return_value = mock_worktrees

            worktrees, total = await crud_adapter.list_worktrees(
                filters={"status": "active"}
            )

            assert worktrees == mock_worktrees
            assert total == 1
            mock_crud.list_by_status.assert_called_once_with(
                mock_session, WorktreeStatus.ACTIVE
            )

    @pytest.mark.asyncio
    async def test_list_worktrees_pagination(self, crud_adapter, mock_session):
        """Test listing worktrees with pagination."""
        mock_worktrees = [
            Mock(spec=Worktree, id=1, name="worktree-1"),
            Mock(spec=Worktree, id=2, name="worktree-2"),
            Mock(spec=Worktree, id=3, name="worktree-3"),
        ]

        with patch("cc_orchestrator.web.crud_adapter.WorktreeCRUD") as mock_crud:
            mock_crud.list_all.return_value = mock_worktrees

            worktrees, total = await crud_adapter.list_worktrees(offset=1, limit=1)

            assert len(worktrees) == 1
            assert worktrees[0].id == 2  # Second item due to offset
            assert total == 3

    @pytest.mark.asyncio
    async def test_create_worktree(self, crud_adapter, mock_session):
        """Test creating a worktree."""
        mock_worktree = Mock(spec=Worktree, id=1, name="test-worktree")
        worktree_data = {
            "name": "test-worktree",
            "path": "/path/to/worktree",
            "branch_name": "feature-branch",
            "repository_url": "https://github.com/user/repo.git",
        }

        with patch("cc_orchestrator.web.crud_adapter.WorktreeCRUD") as mock_crud:
            mock_crud.create.return_value = mock_worktree

            result = await crud_adapter.create_worktree(worktree_data)

            assert result == mock_worktree
            mock_crud.create.assert_called_once_with(
                mock_session,
                name="test-worktree",
                path="/path/to/worktree",
                branch_name="feature-branch",
                repository_url="https://github.com/user/repo.git",
                instance_id=None,
                git_config={},
                extra_metadata={},
            )

    @pytest.mark.asyncio
    async def test_get_worktree_success(self, crud_adapter, mock_session):
        """Test getting a worktree by ID successfully."""
        mock_worktree = Mock(spec=Worktree, id=1, name="test-worktree")

        with patch("cc_orchestrator.web.crud_adapter.WorktreeCRUD") as mock_crud:
            mock_crud.get_by_id.return_value = mock_worktree

            result = await crud_adapter.get_worktree(1)

            assert result == mock_worktree
            mock_crud.get_by_id.assert_called_once_with(mock_session, 1)

    @pytest.mark.asyncio
    async def test_get_worktree_not_found(self, crud_adapter, mock_session):
        """Test getting a worktree that doesn't exist."""
        with patch("cc_orchestrator.web.crud_adapter.WorktreeCRUD") as mock_crud:
            mock_crud.get_by_id.side_effect = Exception("Not found")

            result = await crud_adapter.get_worktree(999)

            assert result is None

    @pytest.mark.asyncio
    async def test_get_worktree_by_path_success(self, crud_adapter, mock_session):
        """Test getting a worktree by path successfully."""
        mock_worktree = Mock(spec=Worktree, id=1, path="/path/to/worktree")

        with patch("cc_orchestrator.web.crud_adapter.WorktreeCRUD") as mock_crud:
            mock_crud.get_by_path.return_value = mock_worktree

            result = await crud_adapter.get_worktree_by_path("/path/to/worktree")

            assert result == mock_worktree
            mock_crud.get_by_path.assert_called_once_with(
                mock_session, "/path/to/worktree"
            )

    @pytest.mark.asyncio
    async def test_get_worktree_by_path_not_found(self, crud_adapter, mock_session):
        """Test getting a worktree by path that doesn't exist."""
        with patch("cc_orchestrator.web.crud_adapter.WorktreeCRUD") as mock_crud:
            mock_crud.get_by_path.side_effect = Exception("Not found")

            result = await crud_adapter.get_worktree_by_path("/nonexistent/path")

            assert result is None

    @pytest.mark.asyncio
    async def test_update_worktree_status_only(self, crud_adapter, mock_session):
        """Test updating a worktree status only."""
        mock_existing = Mock(spec=Worktree, id=1, status=WorktreeStatus.ACTIVE)
        mock_updated = Mock(spec=Worktree, id=1, status=WorktreeStatus.INACTIVE)
        update_data = {"status": "inactive"}

        with patch("cc_orchestrator.web.crud_adapter.WorktreeCRUD") as mock_crud:
            mock_crud.get_by_id.return_value = mock_existing
            mock_crud.update_status.return_value = mock_updated

            result = await crud_adapter.update_worktree(1, update_data)

            assert result == mock_updated
            mock_crud.update_status.assert_called_once_with(
                mock_session,
                1,
                WorktreeStatus.INACTIVE,
                current_commit=None,
                has_uncommitted_changes=None,
            )

    @pytest.mark.asyncio
    async def test_update_worktree_git_info(self, crud_adapter, mock_session):
        """Test updating worktree git information."""
        mock_existing = Mock(spec=Worktree, id=1, status=WorktreeStatus.ACTIVE)
        mock_updated = Mock(spec=Worktree, id=1, status=WorktreeStatus.ACTIVE)
        update_data = {"current_commit": "abc123", "has_uncommitted_changes": True}

        with patch("cc_orchestrator.web.crud_adapter.WorktreeCRUD") as mock_crud:
            mock_crud.get_by_id.return_value = mock_existing
            mock_crud.update_status.return_value = mock_updated

            result = await crud_adapter.update_worktree(1, update_data)

            assert result == mock_updated
            mock_crud.update_status.assert_called_once_with(
                mock_session,
                1,
                WorktreeStatus.ACTIVE,
                current_commit="abc123",
                has_uncommitted_changes=True,
            )

    @pytest.mark.asyncio
    async def test_update_worktree_other_fields(self, crud_adapter, mock_session):
        """Test updating worktree with non-status fields."""
        mock_existing = Mock(spec=Worktree, id=1, name="test-worktree")
        update_data = {"name": "new-name"}

        with patch("cc_orchestrator.web.crud_adapter.WorktreeCRUD") as mock_crud:
            mock_crud.get_by_id.return_value = mock_existing

            result = await crud_adapter.update_worktree(1, update_data)

            # Should return existing worktree as general update not implemented
            assert result == mock_existing
            mock_crud.get_by_id.assert_called_with(mock_session, 1)

    @pytest.mark.asyncio
    async def test_delete_worktree(self, crud_adapter, mock_session):
        """Test deleting a worktree."""
        with patch("cc_orchestrator.web.crud_adapter.WorktreeCRUD") as mock_crud:
            await crud_adapter.delete_worktree(1)

            mock_crud.delete.assert_called_once_with(mock_session, 1)


class TestConfigurationOperations:
    """Test configuration CRUD operations."""

    @pytest.mark.asyncio
    async def test_list_configurations(self, crud_adapter, mock_session):
        """Test listing configurations (not implemented)."""
        configs, total = await crud_adapter.list_configurations()

        assert configs == []
        assert total == 0

    @pytest.mark.asyncio
    async def test_create_configuration_with_string_scope(
        self, crud_adapter, mock_session
    ):
        """Test creating a configuration with string scope."""
        mock_config = Mock(spec=Configuration, id=1, key="test.key")
        config_data = {"key": "test.key", "value": "test_value", "scope": "global"}

        with patch("cc_orchestrator.web.crud_adapter.ConfigurationCRUD") as mock_crud:
            mock_crud.create.return_value = mock_config

            result = await crud_adapter.create_configuration(config_data)

            assert result == mock_config
            # Should convert string to enum
            assert mock_crud.create.call_args[1]["scope"] == ConfigScope.GLOBAL

    @pytest.mark.asyncio
    async def test_create_configuration_scope_mapping(self, crud_adapter, mock_session):
        """Test configuration scope string to enum mapping."""
        mock_config = Mock(spec=Configuration, id=1, key="test.key")

        scope_mappings = [
            ("user", ConfigScope.USER),
            ("project", ConfigScope.PROJECT),
            ("instance", ConfigScope.INSTANCE),
            ("invalid", ConfigScope.GLOBAL),  # Should default to GLOBAL
        ]

        with patch("cc_orchestrator.web.crud_adapter.ConfigurationCRUD") as mock_crud:
            mock_crud.create.return_value = mock_config

            for scope_str, expected_enum in scope_mappings:
                config_data = {
                    "key": "test.key",
                    "value": "test_value",
                    "scope": scope_str,
                }

                await crud_adapter.create_configuration(config_data)
                assert mock_crud.create.call_args[1]["scope"] == expected_enum

    @pytest.mark.asyncio
    async def test_get_configuration(self, crud_adapter, mock_session):
        """Test getting configuration by ID (not implemented)."""
        result = await crud_adapter.get_configuration(1)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_configuration_by_key_scope_string(
        self, crud_adapter, mock_session
    ):
        """Test getting configuration by key and string scope."""
        mock_config = Mock(spec=Configuration, id=1, key="test.key")

        with patch("cc_orchestrator.web.crud_adapter.ConfigurationCRUD") as mock_crud:
            mock_crud.get_by_key_scope.return_value = mock_config

            result = await crud_adapter.get_configuration_by_key_scope(
                "test.key", "global", instance_id=None
            )

            assert result == mock_config
            mock_crud.get_by_key_scope.assert_called_once_with(
                mock_session, "test.key", ConfigScope.GLOBAL, None
            )

    @pytest.mark.asyncio
    async def test_get_configuration_by_key_scope_enum(
        self, crud_adapter, mock_session
    ):
        """Test getting configuration by key and enum scope."""
        mock_config = Mock(spec=Configuration, id=1, key="test.key")

        with patch("cc_orchestrator.web.crud_adapter.ConfigurationCRUD") as mock_crud:
            mock_crud.get_by_key_scope.return_value = mock_config

            result = await crud_adapter.get_configuration_by_key_scope(
                "test.key", ConfigScope.USER, instance_id=1
            )

            assert result == mock_config
            mock_crud.get_by_key_scope.assert_called_once_with(
                mock_session, "test.key", ConfigScope.USER, 1
            )

    @pytest.mark.asyncio
    async def test_get_configuration_by_key_scope_not_found(
        self, crud_adapter, mock_session
    ):
        """Test getting configuration by key and scope that doesn't exist."""
        with patch("cc_orchestrator.web.crud_adapter.ConfigurationCRUD") as mock_crud:
            mock_crud.get_by_key_scope.side_effect = Exception("Not found")

            result = await crud_adapter.get_configuration_by_key_scope(
                "nonexistent.key", "global"
            )

            assert result is None

    @pytest.mark.asyncio
    async def test_get_exact_configuration_by_key_scope(
        self, crud_adapter, mock_session
    ):
        """Test getting exact configuration by key and scope."""
        mock_config = Mock(spec=Configuration, id=1, key="test.key")

        with patch("cc_orchestrator.web.crud_adapter.ConfigurationCRUD") as mock_crud:
            mock_crud.get_exact_by_key_scope.return_value = mock_config

            result = await crud_adapter.get_exact_configuration_by_key_scope(
                "test.key", "instance", instance_id=1
            )

            assert result == mock_config
            mock_crud.get_exact_by_key_scope.assert_called_once_with(
                mock_session, "test.key", ConfigScope.INSTANCE, 1
            )

    @pytest.mark.asyncio
    async def test_update_configuration(self, crud_adapter, mock_session):
        """Test updating configuration (creates dummy object)."""
        update_data = {"value": "new_value", "description": "Updated"}

        result = await crud_adapter.update_configuration(1, update_data)

        assert result.id == 1
        assert result.value == "new_value"
        assert result.description == "Updated"
        assert result.scope == ConfigScope.GLOBAL

    @pytest.mark.asyncio
    async def test_delete_configuration(self, crud_adapter, mock_session):
        """Test deleting configuration (placeholder)."""
        # Should not raise any exception
        await crud_adapter.delete_configuration(1)


class TestHealthCheckOperations:
    """Test health check CRUD operations."""

    @pytest.mark.asyncio
    async def test_list_health_checks_by_instance(self, crud_adapter, mock_session):
        """Test listing health checks by instance ID."""
        mock_checks = [
            Mock(spec=HealthCheck, id=1, overall_status=HealthStatus.HEALTHY),
            Mock(spec=HealthCheck, id=2, overall_status=HealthStatus.DEGRADED),
        ]

        with patch("cc_orchestrator.web.crud_adapter.HealthCheckCRUD") as mock_crud:
            mock_crud.list_by_instance.return_value = mock_checks
            mock_crud.count_by_instance.return_value = 2

            checks, total = await crud_adapter.list_health_checks(
                offset=0, limit=10, filters={"instance_id": 1}
            )

            assert checks == mock_checks
            assert total == 2
            mock_crud.list_by_instance.assert_called_once_with(
                mock_session, 1, limit=10, offset=0
            )
            mock_crud.count_by_instance.assert_called_once_with(mock_session, 1)

    @pytest.mark.asyncio
    async def test_list_health_checks_no_instance_filter(
        self, crud_adapter, mock_session
    ):
        """Test listing health checks without instance filter."""
        checks, total = await crud_adapter.list_health_checks()

        assert checks == []
        assert total == 0

    @pytest.mark.asyncio
    async def test_create_health_check_string_status(self, crud_adapter, mock_session):
        """Test creating health check with string status."""
        mock_check = Mock(spec=HealthCheck, id=1, overall_status=HealthStatus.HEALTHY)
        check_data = {
            "instance_id": 1,
            "overall_status": "healthy",
            "check_results": {"cpu": "ok", "memory": "ok"},
            "duration_ms": 150,
            "check_timestamp": datetime.now(),
        }

        with patch("cc_orchestrator.web.crud_adapter.HealthCheckCRUD") as mock_crud:
            mock_crud.create.return_value = mock_check

            result = await crud_adapter.create_health_check(check_data)

            assert result == mock_check
            # Should convert string to enum
            assert (
                mock_crud.create.call_args[1]["overall_status"] == HealthStatus.HEALTHY
            )

    @pytest.mark.asyncio
    async def test_create_health_check_enum_status(self, crud_adapter, mock_session):
        """Test creating health check with enum status."""
        mock_check = Mock(spec=HealthCheck, id=1, overall_status=HealthStatus.UNHEALTHY)
        check_data = {
            "instance_id": 1,
            "overall_status": HealthStatus.UNHEALTHY,
            "check_results": {"error": "service down"},
            "duration_ms": 5000,
            "check_timestamp": datetime.now(),
        }

        with patch("cc_orchestrator.web.crud_adapter.HealthCheckCRUD") as mock_crud:
            mock_crud.create.return_value = mock_check

            result = await crud_adapter.create_health_check(check_data)

            assert result == mock_check
            mock_crud.create.assert_called_once()


class TestAlertOperations:
    """Test alert operations (placeholder implementation)."""

    @pytest.mark.asyncio
    async def test_list_alerts(self, crud_adapter):
        """Test listing alerts (placeholder)."""
        alerts, total = await crud_adapter.list_alerts()

        assert alerts == []
        assert total == 0

    @pytest.mark.asyncio
    async def test_create_alert(self, crud_adapter):
        """Test creating an alert (placeholder)."""
        alert_data = {
            "instance_id": 1,
            "alert_id": "test-alert",
            "level": "warning",
            "message": "Test alert message",
            "timestamp": datetime.now(),
        }

        result = await crud_adapter.create_alert(alert_data)

        assert isinstance(result, Alert)
        assert result.instance_id == 1
        assert result.alert_id == "test-alert"
        assert result.level == "warning"
        assert result.message == "Test alert message"
        assert result.id == 1

    @pytest.mark.asyncio
    async def test_get_alert_by_alert_id(self, crud_adapter):
        """Test getting alert by alert ID (placeholder)."""
        result = await crud_adapter.get_alert_by_alert_id("test-alert")

        assert result is None


class TestAsyncIntegration:
    """Test async integration and edge cases."""

    @pytest.mark.asyncio
    async def test_asyncio_to_thread_integration(self, crud_adapter, mock_session):
        """Test that asyncio.to_thread is properly used."""
        mock_instance = Mock(spec=Instance, id=1, issue_id="issue-1")

        with (
            patch("cc_orchestrator.web.crud_adapter.InstanceCRUD") as mock_crud,
            patch("asyncio.to_thread", wraps=asyncio.to_thread) as mock_to_thread,
        ):

            mock_crud.get_by_id.return_value = mock_instance

            result = await crud_adapter.get_instance(1)

            assert result == mock_instance
            # Should have called asyncio.to_thread
            mock_to_thread.assert_called_once()

    @pytest.mark.asyncio
    async def test_session_validation_edge_case(self, crud_adapter):
        """Test session validation with missing is_active attribute."""
        # Remove is_active attribute to test edge case
        if hasattr(crud_adapter.session, "is_active"):
            delattr(crud_adapter.session, "is_active")

        with patch("cc_orchestrator.web.crud_adapter.InstanceCRUD") as mock_crud:
            mock_crud.get_by_id.return_value = Mock(spec=Instance, id=1)

            # Should not fail if is_active doesn't exist
            result = await crud_adapter.get_instance(1)

            assert result is not None

    @pytest.mark.asyncio
    async def test_enum_conversion_edge_cases(self, crud_adapter, mock_session):
        """Test enum conversions with edge cases."""
        mock_instance = Mock(spec=Instance, id=1)

        with patch("cc_orchestrator.web.crud_adapter.InstanceCRUD") as mock_crud:
            mock_crud.create.return_value = mock_instance

            # Test with mixed case status
            instance_data = {"issue_id": "issue-1", "status": "Running"}  # Mixed case

            result = await crud_adapter.create_instance(instance_data)

            assert result == mock_instance
            # Should convert to lowercase then to enum
            assert mock_instance.status == InstanceStatus.RUNNING
