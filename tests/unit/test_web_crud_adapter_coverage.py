"""
Comprehensive tests for web/crud_adapter.py module targeting 100% coverage.

This test suite provides exhaustive coverage for the async CRUD adapter including:
- CRUDBase class initialization and session management
- Instance CRUD operations with all code paths
- Task CRUD operations with comprehensive filtering and error handling
- Worktree CRUD operations and status management
- Configuration CRUD operations with scope handling
- Health check CRUD operations
- Alert and recovery attempt placeholder operations
- Database session error conditions
- Async operation verification and exception handling
- All conditional branches and edge cases

Target: 100% coverage (289 statements)
"""

from datetime import UTC, datetime
from unittest.mock import Mock, patch

import pytest

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


class TestPlaceholderModels:
    """Test placeholder model classes - Alert and RecoveryAttempt."""

    def test_alert_creation_with_kwargs(self):
        """Test Alert placeholder model creation with all attributes - lines 35-43."""
        alert_data = {
            "id": 1,
            "title": "Test Alert",
            "message": "Test message",
            "level": "error",
            "instance_id": 123,
        }

        alert = Alert(**alert_data)

        # Lines 36-37: Set attributes from kwargs
        assert alert.id == 1
        assert alert.title == "Test Alert"
        assert alert.message == "Test message"
        assert alert.level == "error"
        assert alert.instance_id == 123
        # Line 38: Created timestamp set
        assert hasattr(alert, "created_at")
        assert isinstance(alert.created_at, datetime)

    def test_alert_creation_with_default_attributes(self):
        """Test Alert model default attribute handling - lines 40-43."""
        alert_data = {"message": "Test without id or level"}
        alert = Alert(**alert_data)

        # Lines 40-43: Default attributes when not provided
        assert alert.id == 1  # Default from line 41
        assert alert.level == "info"  # Default from line 43
        assert hasattr(alert, "created_at")

    def test_alert_creation_with_id_provided(self):
        """Test Alert creation when id is provided in kwargs - covers line 40 condition."""
        alert_data = {"id": 42, "level": "warning"}
        alert = Alert(**alert_data)

        # Should use provided id, not default
        assert alert.id == 42
        assert alert.level == "warning"

    def test_alert_creation_with_level_provided(self):
        """Test Alert creation when level is provided in kwargs - covers line 42 condition."""
        alert_data = {"level": "critical"}
        alert = Alert(**alert_data)

        # Should use provided level, not default
        assert alert.level == "critical"
        assert alert.id == 1  # Still gets default id

    def test_recovery_attempt_creation_with_kwargs(self):
        """Test RecoveryAttempt placeholder model creation - lines 49-55."""
        attempt_data = {
            "id": 1,
            "strategy": "restart",
            "status": "completed",
            "instance_id": 456,
        }

        attempt = RecoveryAttempt(**attempt_data)

        # Lines 50-51: Set attributes from kwargs
        assert attempt.id == 1
        assert attempt.strategy == "restart"
        assert attempt.status == "completed"
        assert attempt.instance_id == 456
        # Line 52: Created timestamp set
        assert hasattr(attempt, "created_at")
        assert isinstance(attempt.created_at, datetime)

    def test_recovery_attempt_creation_with_default_id(self):
        """Test RecoveryAttempt with default id handling - lines 54-55."""
        attempt_data = {"strategy": "reconnect"}
        attempt = RecoveryAttempt(**attempt_data)

        # Lines 54-55: Default id when not provided
        assert attempt.id == 1
        assert attempt.strategy == "reconnect"


class TestCRUDBaseInit:
    """Test CRUDBase class initialization - line 63."""

    def test_crud_base_initialization(self):
        """Test CRUDBase initialization with session - line 63."""
        mock_session = Mock()
        crud = CRUDBase(mock_session)

        # Line 63: Session assignment
        assert crud.session == mock_session


class TestInstanceOperations:
    """Test all instance-related CRUD operations."""

    @pytest.mark.asyncio
    async def test_list_instances_no_filters(self):
        """Test instance listing without filters - lines 71-93."""
        mock_session = Mock()
        crud = CRUDBase(mock_session)

        with patch("cc_orchestrator.web.crud_adapter.InstanceCRUD") as mock_crud:
            mock_instances = [Mock(spec=Instance), Mock(spec=Instance)]
            mock_crud.list_all.return_value = mock_instances

            instances, total = await crud.list_instances(offset=5, limit=10)

            # Lines 84-85: Call with status=None
            # Note: Based on actual implementation, list_all doesn't take limit/offset directly
            assert mock_crud.list_all.call_count == 2  # Called twice for data and count
            # Lines 88-89: Get total count
            assert len(instances) == 2
            assert total == 2

    @pytest.mark.asyncio
    async def test_list_instances_with_string_status_filter(self):
        """Test listing instances with string status filter - lines 74-82."""
        mock_session = Mock()
        crud = CRUDBase(mock_session)

        with patch("cc_orchestrator.web.crud_adapter.InstanceCRUD") as mock_crud:
            mock_instances = [Mock(spec=Instance)]
            mock_crud.list_all.return_value = mock_instances

            # Lines 74-82: String status conversion
            filters = {"status": "running"}
            instances, total = await crud.list_instances(filters=filters)

            # Should have converted string to enum
            mock_crud.list_all.assert_called()
            args = mock_crud.list_all.call_args[1]
            assert args["status"] == InstanceStatus.RUNNING

    @pytest.mark.asyncio
    async def test_list_instances_with_enum_status_filter(self):
        """Test listing instances with enum status filter - lines 81-82."""
        mock_session = Mock()
        crud = CRUDBase(mock_session)

        with patch("cc_orchestrator.web.crud_adapter.InstanceCRUD") as mock_crud:
            mock_instances = [Mock(spec=Instance)]
            mock_crud.list_all.return_value = mock_instances

            # Lines 81-82: Enum status direct use
            filters = {"status": InstanceStatus.ERROR}
            instances, total = await crud.list_instances(filters=filters)

            mock_crud.list_all.assert_called()
            args = mock_crud.list_all.call_args[1]
            assert args["status"] == InstanceStatus.ERROR

    @pytest.mark.asyncio
    async def test_create_instance_basic(self):
        """Test basic instance creation - lines 98-107."""
        mock_session = Mock()
        crud = CRUDBase(mock_session)

        instance_data = {
            "issue_id": "TEST-123",
            "workspace_path": "/workspace/test",
            "branch_name": "feature-branch",
            "tmux_session": "test-session",
        }

        with patch("cc_orchestrator.web.crud_adapter.InstanceCRUD") as mock_crud:
            mock_instance = Mock(spec=Instance)
            mock_crud.create.return_value = mock_instance

            result = await crud.create_instance(instance_data)

            # Lines 100-107: Create call with parameters
            mock_crud.create.assert_called_once_with(
                mock_session,
                issue_id="TEST-123",
                workspace_path="/workspace/test",
                branch_name="feature-branch",
                tmux_session="test-session",
                extra_metadata={},
            )
            assert result == mock_instance

    @pytest.mark.asyncio
    async def test_create_instance_with_status_string(self):
        """Test instance creation with string status - lines 110-121."""
        mock_session = Mock()
        mock_session.flush = Mock()
        crud = CRUDBase(mock_session)

        instance_data = {"issue_id": "TEST-123", "status": "running"}

        with patch("cc_orchestrator.web.crud_adapter.InstanceCRUD") as mock_crud:
            mock_instance = Mock(spec=Instance)
            mock_crud.create.return_value = mock_instance

            await crud.create_instance(instance_data)

            # Lines 112-115: String to enum conversion
            # Lines 119-120: Status assignment and flush
            assert mock_instance.status == InstanceStatus.RUNNING
            mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_instance_with_status_enum(self):
        """Test instance creation with enum status - lines 116-121."""
        mock_session = Mock()
        mock_session.flush = Mock()
        crud = CRUDBase(mock_session)

        instance_data = {"issue_id": "TEST-123", "status": InstanceStatus.ERROR}

        with patch("cc_orchestrator.web.crud_adapter.InstanceCRUD") as mock_crud:
            mock_instance = Mock(spec=Instance)
            mock_crud.create.return_value = mock_instance

            await crud.create_instance(instance_data)

            # Lines 116-117: Direct enum use
            # Lines 119-120: Status assignment and flush
            assert mock_instance.status == InstanceStatus.ERROR
            mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_instance_success(self):
        """Test successful instance retrieval - lines 129-137."""
        mock_session = Mock()
        mock_session.is_active = True
        crud = CRUDBase(mock_session)

        with patch("cc_orchestrator.web.crud_adapter.InstanceCRUD") as mock_crud:
            mock_instance = Mock(spec=Instance)
            mock_crud.get_by_id.return_value = mock_instance

            result = await crud.get_instance(1)

            # Lines 134: Successful retrieval
            assert result == mock_instance
            mock_crud.get_by_id.assert_called_with(mock_session, 1)

    @pytest.mark.asyncio
    async def test_get_instance_session_inactive(self):
        """Test instance retrieval with inactive session - lines 132-133."""
        mock_session = Mock()
        mock_session.is_active = False
        crud = CRUDBase(mock_session)

        result = await crud.get_instance(1)

        # Lines 132-133: Return None for inactive session
        assert result is None

    @pytest.mark.asyncio
    async def test_get_instance_no_is_active_attribute(self):
        """Test instance retrieval when session has no is_active - line 134."""
        mock_session = Mock()
        # Don't set is_active attribute
        del mock_session.is_active
        crud = CRUDBase(mock_session)

        with patch("cc_orchestrator.web.crud_adapter.InstanceCRUD") as mock_crud:
            mock_instance = Mock(spec=Instance)
            mock_crud.get_by_id.return_value = mock_instance

            result = await crud.get_instance(1)

            # Should proceed to CRUD call when no is_active attribute
            assert result == mock_instance

    @pytest.mark.asyncio
    async def test_get_instance_exception(self):
        """Test instance retrieval with exception - lines 135-137."""
        mock_session = Mock()
        crud = CRUDBase(mock_session)

        with patch("cc_orchestrator.web.crud_adapter.InstanceCRUD") as mock_crud:
            mock_crud.get_by_id.side_effect = Exception("Database error")

            result = await crud.get_instance(1)

            # Lines 135-137: Exception handling returns None
            assert result is None

    @pytest.mark.asyncio
    async def test_get_instance_by_issue_id_success(self):
        """Test successful instance retrieval by issue_id - lines 144-149."""
        mock_session = Mock()
        crud = CRUDBase(mock_session)

        with patch("cc_orchestrator.web.crud_adapter.InstanceCRUD") as mock_crud:
            mock_instance = Mock(spec=Instance)
            mock_crud.get_by_issue_id.return_value = mock_instance

            result = await crud.get_instance_by_issue_id("TEST-123")

            # Line 146: Successful retrieval
            assert result == mock_instance
            mock_crud.get_by_issue_id.assert_called_with(mock_session, "TEST-123")

    @pytest.mark.asyncio
    async def test_get_instance_by_issue_id_exception(self):
        """Test instance retrieval by issue_id with exception - lines 147-149."""
        mock_session = Mock()
        crud = CRUDBase(mock_session)

        with patch("cc_orchestrator.web.crud_adapter.InstanceCRUD") as mock_crud:
            mock_crud.get_by_issue_id.side_effect = Exception("Not found")

            result = await crud.get_instance_by_issue_id("NONEXISTENT")

            # Lines 147-149: Exception handling returns None
            assert result is None

    @pytest.mark.asyncio
    async def test_update_instance_with_string_status(self):
        """Test instance update with string status - lines 157-168."""
        mock_session = Mock()
        crud = CRUDBase(mock_session)

        update_data = {"status": "error"}

        with patch("cc_orchestrator.web.crud_adapter.InstanceCRUD") as mock_crud:
            mock_instance = Mock(spec=Instance)
            mock_crud.update.return_value = mock_instance

            result = await crud.update_instance(1, update_data)

            # Lines 159-166: Status conversion and update
            expected_data = {"status": InstanceStatus.ERROR}
            mock_crud.update.assert_called_with(mock_session, 1, **expected_data)
            assert result == mock_instance

    @pytest.mark.asyncio
    async def test_update_instance_without_status(self):
        """Test instance update without status field - line 168."""
        mock_session = Mock()
        crud = CRUDBase(mock_session)

        update_data = {"workspace_path": "/new/path"}

        with patch("cc_orchestrator.web.crud_adapter.InstanceCRUD") as mock_crud:
            mock_instance = Mock(spec=Instance)
            mock_crud.update.return_value = mock_instance

            result = await crud.update_instance(1, update_data)

            # Line 168: Direct update without status conversion
            mock_crud.update.assert_called_with(mock_session, 1, **update_data)
            assert result == mock_instance

    @pytest.mark.asyncio
    async def test_delete_instance(self):
        """Test instance deletion - lines 175-177."""
        mock_session = Mock()
        crud = CRUDBase(mock_session)

        with patch("cc_orchestrator.web.crud_adapter.InstanceCRUD") as mock_crud:
            await crud.delete_instance(1)

            # Line 176: Delete call
            mock_crud.delete.assert_called_with(mock_session, 1)


class TestTaskOperations:
    """Test all task-related CRUD operations."""

    @pytest.mark.asyncio
    async def test_list_tasks_with_instance_id_filter(self):
        """Test task listing with instance_id filter - lines 186-210."""
        mock_session = Mock()
        crud = CRUDBase(mock_session)

        filters = {"instance_id": 1}

        with patch("cc_orchestrator.web.crud_adapter.TaskCRUD") as mock_crud:
            mock_tasks = [Mock(spec=Task), Mock(spec=Task), Mock(spec=Task)]
            mock_crud.list_by_instance.return_value = mock_tasks

            tasks, total = await crud.list_tasks(offset=1, limit=2, filters=filters)

            # Lines 188-202: Instance filter path
            mock_crud.list_by_instance.assert_called_with(mock_session, 1, status=None)
            # Lines 204-209: Pagination logic
            assert len(tasks) == 2  # Limited by pagination
            assert total == 3  # Total count

    @pytest.mark.asyncio
    async def test_list_tasks_with_instance_id_and_status_filter(self):
        """Test task listing with instance_id and status filters - lines 190-202."""
        mock_session = Mock()
        crud = CRUDBase(mock_session)

        filters = {"instance_id": 1, "status": "pending"}

        with patch("cc_orchestrator.web.crud_adapter.TaskCRUD") as mock_crud:
            mock_tasks = [Mock(spec=Task)]
            mock_crud.list_by_instance.return_value = mock_tasks

            tasks, total = await crud.list_tasks(filters=filters)

            # Lines 190-199: Status filter conversion
            mock_crud.list_by_instance.assert_called_with(
                mock_session, 1, status=TaskStatus.PENDING
            )

    @pytest.mark.asyncio
    async def test_list_tasks_with_instance_id_and_enum_status_filter(self):
        """Test task listing with enum status filter - lines 196-199."""
        mock_session = Mock()
        crud = CRUDBase(mock_session)

        filters = {"instance_id": 1, "status": TaskStatus.COMPLETED}

        with patch("cc_orchestrator.web.crud_adapter.TaskCRUD") as mock_crud:
            mock_tasks = [Mock(spec=Task)]
            mock_crud.list_by_instance.return_value = mock_tasks

            tasks, total = await crud.list_tasks(filters=filters)

            # Lines 197-199: Direct enum use
            mock_crud.list_by_instance.assert_called_with(
                mock_session, 1, status=TaskStatus.COMPLETED
            )

    @pytest.mark.asyncio
    async def test_list_tasks_general_listing(self):
        """Test general task listing without instance_id - lines 211-218."""
        mock_session = Mock()
        crud = CRUDBase(mock_session)

        with patch("cc_orchestrator.web.crud_adapter.TaskCRUD") as mock_crud:
            mock_tasks = [Mock(spec=Task), Mock(spec=Task)]
            mock_crud.list_pending.return_value = mock_tasks

            tasks, total = await crud.list_tasks(limit=5)

            # Lines 213-217: General listing path
            # Note: list_pending may not take limit parameter
            mock_crud.list_pending.assert_called()
            assert len(tasks) == 2
            assert total == 2

    @pytest.mark.asyncio
    async def test_list_tasks_general_with_offset(self):
        """Test general task listing with offset - lines 215-217."""
        mock_session = Mock()
        crud = CRUDBase(mock_session)

        with patch("cc_orchestrator.web.crud_adapter.TaskCRUD") as mock_crud:
            mock_tasks = [Mock(spec=Task), Mock(spec=Task), Mock(spec=Task)]
            mock_crud.list_pending.return_value = mock_tasks

            tasks, total = await crud.list_tasks(offset=1, limit=10)

            # Lines 215-217: Offset handling
            expected_tasks = mock_tasks[1:]  # Skip first task due to offset
            assert len(tasks) == len(expected_tasks)

    @pytest.mark.asyncio
    async def test_create_task_with_string_priority(self):
        """Test task creation with string priority - lines 225-242."""
        mock_session = Mock()
        crud = CRUDBase(mock_session)

        task_data = {
            "title": "Test Task",
            "priority": "HIGH",  # String should work correctly now
            "instance_id": 1,
        }

        with patch("cc_orchestrator.web.crud_adapter.TaskCRUD") as mock_crud:
            mock_task = Mock(spec=Task)
            mock_crud.create.return_value = mock_task

            result = await crud.create_task(task_data)

            # Lines 228-238: String priority conversion - should work correctly now
            # TaskPriority enum values are integers, and code maps strings to enums
            assert result == mock_task
            call_kwargs = mock_crud.create.call_args[1]
            assert call_kwargs["priority"] == TaskPriority.HIGH

    @pytest.mark.asyncio
    async def test_create_task_with_integer_priority(self):
        """Test task creation with integer priority - lines 232-242."""
        mock_session = Mock()
        crud = CRUDBase(mock_session)

        task_data = {
            "title": "Test Task",
            "priority": 3,  # Should map to HIGH
            "description": "Test description",
        }

        with patch("cc_orchestrator.web.crud_adapter.TaskCRUD") as mock_crud:
            mock_task = Mock(spec=Task)
            mock_crud.create.return_value = mock_task

            await crud.create_task(task_data)

            # Lines 232-242: Integer priority mapping
            call_kwargs = mock_crud.create.call_args[1]
            assert call_kwargs["priority"] == TaskPriority.HIGH

    @pytest.mark.asyncio
    async def test_create_task_with_invalid_integer_priority(self):
        """Test task creation with invalid integer priority - line 242."""
        mock_session = Mock()
        crud = CRUDBase(mock_session)

        task_data = {
            "title": "Test Task",
            "priority": 99,  # Invalid, should default to MEDIUM
        }

        with patch("cc_orchestrator.web.crud_adapter.TaskCRUD") as mock_crud:
            mock_task = Mock(spec=Task)
            mock_crud.create.return_value = mock_task

            await crud.create_task(task_data)

            # Line 242: Default to MEDIUM for invalid priority
            call_kwargs = mock_crud.create.call_args[1]
            assert call_kwargs["priority"] == TaskPriority.MEDIUM

    @pytest.mark.asyncio
    async def test_create_task_with_all_parameters(self):
        """Test task creation with all parameters - lines 244-255."""
        mock_session = Mock()
        crud = CRUDBase(mock_session)

        task_data = {
            "title": "Complete Task",
            "description": "Full description",
            "priority": 1,
            "instance_id": 1,
            "worktree_id": 2,
            "due_date": "2024-01-01",
            "estimated_duration": 3600,
            "requirements": {"cpu": "high"},
            "extra_metadata": {"tags": ["urgent"]},
        }

        with patch("cc_orchestrator.web.crud_adapter.TaskCRUD") as mock_crud:
            mock_task = Mock(spec=Task)
            mock_crud.create.return_value = mock_task

            await crud.create_task(task_data)

            # Lines 244-255: All parameters passed
            mock_crud.create.assert_called_once_with(
                mock_session,
                title="Complete Task",
                description="Full description",
                priority=TaskPriority.LOW,
                instance_id=1,
                worktree_id=2,
                due_date="2024-01-01",
                estimated_duration=3600,
                requirements={"cpu": "high"},
                extra_metadata={"tags": ["urgent"]},
            )

    @pytest.mark.asyncio
    async def test_get_task_success(self):
        """Test successful task retrieval - lines 262-266."""
        mock_session = Mock()
        crud = CRUDBase(mock_session)

        with patch("cc_orchestrator.web.crud_adapter.TaskCRUD") as mock_crud:
            mock_task = Mock(spec=Task)
            mock_crud.get_by_id.return_value = mock_task

            result = await crud.get_task(1)

            # Line 264: Successful retrieval
            assert result == mock_task
            mock_crud.get_by_id.assert_called_with(mock_session, 1)

    @pytest.mark.asyncio
    async def test_get_task_exception(self):
        """Test task retrieval with exception - lines 265-267."""
        mock_session = Mock()
        crud = CRUDBase(mock_session)

        with patch("cc_orchestrator.web.crud_adapter.TaskCRUD") as mock_crud:
            mock_crud.get_by_id.side_effect = Exception("Database error")

            result = await crud.get_task(1)

            # Lines 265-267: Exception handling returns None
            assert result is None

    @pytest.mark.asyncio
    async def test_update_task_with_status(self):
        """Test task update with status - lines 273-284."""
        mock_session = Mock()
        crud = CRUDBase(mock_session)

        update_data = {"status": "completed"}

        with patch("cc_orchestrator.web.crud_adapter.TaskCRUD") as mock_crud:
            mock_task = Mock(spec=Task)
            mock_crud.update_status.return_value = mock_task

            result = await crud.update_task(1, update_data)

            # Lines 275-284: Status update path - should work correctly now
            # TaskStatus values are lowercase and code calls .lower() before creating enum
            assert result == mock_task
            mock_crud.update_status.assert_called_with(
                mock_session, 1, TaskStatus.COMPLETED
            )

    @pytest.mark.asyncio
    async def test_update_task_with_enum_status(self):
        """Test task update with enum status - lines 281-284."""
        mock_session = Mock()
        crud = CRUDBase(mock_session)

        update_data = {"status": TaskStatus.FAILED}

        with patch("cc_orchestrator.web.crud_adapter.TaskCRUD") as mock_crud:
            mock_task = Mock(spec=Task)
            mock_crud.update_status.return_value = mock_task

            await crud.update_task(1, update_data)

            # Lines 281-284: Direct enum status update
            mock_crud.update_status.assert_called_with(
                mock_session, 1, TaskStatus.FAILED
            )

    @pytest.mark.asyncio
    async def test_update_task_without_status(self):
        """Test task update without status - lines 286-287."""
        mock_session = Mock()
        crud = CRUDBase(mock_session)

        update_data = {"instance_id": 2}

        with patch("cc_orchestrator.web.crud_adapter.TaskCRUD") as mock_crud:
            mock_task = Mock(spec=Task)
            mock_crud.update.return_value = mock_task

            await crud.update_task(1, update_data)

            # Lines 286-287: General update path
            mock_crud.update.assert_called_with(mock_session, 1, **update_data)

    @pytest.mark.asyncio
    async def test_delete_task(self):
        """Test task deletion - lines 294-299."""
        mock_session = Mock()
        crud = CRUDBase(mock_session)

        with patch("cc_orchestrator.web.crud_adapter.TaskCRUD") as mock_crud:
            await crud.delete_task(1)

            # Lines 297-298: Validation that task exists
            mock_crud.get_by_id.assert_called_with(mock_session, 1)


class TestWorktreeOperations:
    """Test all worktree-related CRUD operations."""

    @pytest.mark.asyncio
    async def test_list_worktrees_with_status_filter(self):
        """Test worktree listing with status filter - lines 308-318."""
        mock_session = Mock()
        crud = CRUDBase(mock_session)

        filters = {"status": "active"}

        with patch("cc_orchestrator.web.crud_adapter.WorktreeCRUD") as mock_crud:
            mock_worktrees = [Mock(spec=Worktree)]
            mock_crud.list_by_status.return_value = mock_worktrees

            worktrees, total = await crud.list_worktrees(filters=filters)

            # Lines 310-318: Status filter path
            mock_crud.list_by_status.assert_called_with(
                mock_session, WorktreeStatus.ACTIVE
            )

    @pytest.mark.asyncio
    async def test_list_worktrees_with_enum_status_filter(self):
        """Test worktree listing with enum status filter - lines 315-318."""
        mock_session = Mock()
        crud = CRUDBase(mock_session)

        filters = {"status": WorktreeStatus.DIRTY}

        with patch("cc_orchestrator.web.crud_adapter.WorktreeCRUD") as mock_crud:
            mock_worktrees = [Mock(spec=Worktree)]
            mock_crud.list_by_status.return_value = mock_worktrees

            worktrees, total = await crud.list_worktrees(filters=filters)

            # Lines 316-318: Direct enum use
            mock_crud.list_by_status.assert_called_with(
                mock_session, WorktreeStatus.DIRTY
            )

    @pytest.mark.asyncio
    async def test_list_worktrees_without_filters(self):
        """Test worktree listing without filters - lines 319-328."""
        mock_session = Mock()
        crud = CRUDBase(mock_session)

        with patch("cc_orchestrator.web.crud_adapter.WorktreeCRUD") as mock_crud:
            mock_worktrees = [
                Mock(spec=Worktree),
                Mock(spec=Worktree),
                Mock(spec=Worktree),
            ]
            mock_crud.list_all.return_value = mock_worktrees

            worktrees, total = await crud.list_worktrees(offset=1, limit=2)

            # Lines 320: No filter path
            mock_crud.list_all.assert_called_with(mock_session)
            # Lines 322-327: Pagination logic
            assert len(worktrees) == 2  # Limited by pagination
            assert total == 3

    @pytest.mark.asyncio
    async def test_create_worktree(self):
        """Test worktree creation - lines 335-345."""
        mock_session = Mock()
        crud = CRUDBase(mock_session)

        worktree_data = {
            "name": "test-worktree",
            "path": "/workspace/test",
            "branch_name": "feature-branch",
            "repository_url": "https://github.com/test/repo.git",
            "instance_id": 1,
            "git_config": {"user.name": "Test User"},
            "extra_metadata": {"project": "test"},
        }

        with patch("cc_orchestrator.web.crud_adapter.WorktreeCRUD") as mock_crud:
            mock_worktree = Mock(spec=Worktree)
            mock_crud.create.return_value = mock_worktree

            await crud.create_worktree(worktree_data)

            # Lines 336-345: All parameters passed
            mock_crud.create.assert_called_once_with(
                mock_session,
                name="test-worktree",
                path="/workspace/test",
                branch_name="feature-branch",
                repository_url="https://github.com/test/repo.git",
                instance_id=1,
                git_config={"user.name": "Test User"},
                extra_metadata={"project": "test"},
            )

    @pytest.mark.asyncio
    async def test_get_worktree_success(self):
        """Test successful worktree retrieval - lines 352-356."""
        mock_session = Mock()
        crud = CRUDBase(mock_session)

        with patch("cc_orchestrator.web.crud_adapter.WorktreeCRUD") as mock_crud:
            mock_worktree = Mock(spec=Worktree)
            mock_crud.get_by_id.return_value = mock_worktree

            result = await crud.get_worktree(1)

            # Line 354: Successful retrieval
            assert result == mock_worktree
            mock_crud.get_by_id.assert_called_with(mock_session, 1)

    @pytest.mark.asyncio
    async def test_get_worktree_exception(self):
        """Test worktree retrieval with exception - lines 355-357."""
        mock_session = Mock()
        crud = CRUDBase(mock_session)

        with patch("cc_orchestrator.web.crud_adapter.WorktreeCRUD") as mock_crud:
            mock_crud.get_by_id.side_effect = Exception("Database error")

            result = await crud.get_worktree(1)

            # Lines 355-357: Exception handling returns None
            assert result is None

    @pytest.mark.asyncio
    async def test_get_worktree_by_path_success(self):
        """Test successful worktree retrieval by path - lines 363-367."""
        mock_session = Mock()
        crud = CRUDBase(mock_session)

        with patch("cc_orchestrator.web.crud_adapter.WorktreeCRUD") as mock_crud:
            mock_worktree = Mock(spec=Worktree)
            mock_crud.get_by_path.return_value = mock_worktree

            result = await crud.get_worktree_by_path("/workspace/test")

            # Line 365: Successful retrieval
            assert result == mock_worktree
            mock_crud.get_by_path.assert_called_with(mock_session, "/workspace/test")

    @pytest.mark.asyncio
    async def test_get_worktree_by_path_exception(self):
        """Test worktree retrieval by path with exception - lines 366-368."""
        mock_session = Mock()
        crud = CRUDBase(mock_session)

        with patch("cc_orchestrator.web.crud_adapter.WorktreeCRUD") as mock_crud:
            mock_crud.get_by_path.side_effect = Exception("Not found")

            result = await crud.get_worktree_by_path("/nonexistent")

            # Lines 366-368: Exception handling returns None
            assert result is None

    @pytest.mark.asyncio
    async def test_update_worktree_with_status_and_git_info(self):
        """Test worktree update with status and git info - lines 376-403."""
        mock_session = Mock()
        crud = CRUDBase(mock_session)

        # Mock current worktree for status preservation
        current_worktree = Mock()
        current_worktree.status = WorktreeStatus.ACTIVE

        update_data = {
            "status": "dirty",
            "current_commit": "abc123",
            "has_uncommitted_changes": True,
        }

        with patch("cc_orchestrator.web.crud_adapter.WorktreeCRUD") as mock_crud:
            mock_crud.get_by_id.return_value = current_worktree
            mock_updated_worktree = Mock(spec=Worktree)
            mock_crud.update_status.return_value = mock_updated_worktree

            await crud.update_worktree(1, update_data)

            # Lines 383-384: Get current worktree
            mock_crud.get_by_id.assert_called_with(mock_session, 1)
            # Lines 388-395: Status conversion and update
            mock_crud.update_status.assert_called_with(
                mock_session,
                1,
                WorktreeStatus.DIRTY,
                current_commit="abc123",
                has_uncommitted_changes=True,
            )

    @pytest.mark.asyncio
    async def test_update_worktree_with_enum_status(self):
        """Test worktree update with enum status - lines 393-403."""
        mock_session = Mock()
        crud = CRUDBase(mock_session)

        current_worktree = Mock()
        current_worktree.status = WorktreeStatus.ACTIVE

        update_data = {"status": WorktreeStatus.ERROR, "current_commit": "def456"}

        with patch("cc_orchestrator.web.crud_adapter.WorktreeCRUD") as mock_crud:
            mock_crud.get_by_id.return_value = current_worktree
            mock_updated_worktree = Mock(spec=Worktree)
            mock_crud.update_status.return_value = mock_updated_worktree

            await crud.update_worktree(1, update_data)

            # Lines 394-403: Direct enum use
            mock_crud.update_status.assert_called_with(
                mock_session,
                1,
                WorktreeStatus.ERROR,
                current_commit="def456",
                has_uncommitted_changes=None,
            )

    @pytest.mark.asyncio
    async def test_update_worktree_git_info_only(self):
        """Test worktree update with git info only - lines 378-403."""
        mock_session = Mock()
        crud = CRUDBase(mock_session)

        current_worktree = Mock()
        current_worktree.status = WorktreeStatus.DIRTY

        update_data = {"current_commit": "xyz789", "has_uncommitted_changes": False}

        with patch("cc_orchestrator.web.crud_adapter.WorktreeCRUD") as mock_crud:
            mock_crud.get_by_id.return_value = current_worktree
            mock_updated_worktree = Mock(spec=Worktree)
            mock_crud.update_status.return_value = mock_updated_worktree

            await crud.update_worktree(1, update_data)

            # Lines 383-403: Use existing status with git info
            mock_crud.update_status.assert_called_with(
                mock_session,
                1,
                WorktreeStatus.DIRTY,  # Preserved from current worktree
                current_commit="xyz789",
                has_uncommitted_changes=False,
            )

    @pytest.mark.asyncio
    async def test_update_worktree_other_fields(self):
        """Test worktree update with other fields - lines 404-407."""
        mock_session = Mock()
        crud = CRUDBase(mock_session)

        update_data = {"name": "updated-name"}

        with patch("cc_orchestrator.web.crud_adapter.WorktreeCRUD") as mock_crud:
            mock_worktree = Mock(spec=Worktree)
            mock_crud.get_by_id.return_value = mock_worktree

            result = await crud.update_worktree(1, update_data)

            # Lines 405-407: Return existing worktree for non-status updates
            assert result == mock_worktree
            mock_crud.get_by_id.assert_called_with(mock_session, 1)

    @pytest.mark.asyncio
    async def test_delete_worktree(self):
        """Test worktree deletion - lines 414-416."""
        mock_session = Mock()
        crud = CRUDBase(mock_session)

        with patch("cc_orchestrator.web.crud_adapter.WorktreeCRUD") as mock_crud:
            await crud.delete_worktree(1)

            # Line 415: Delete call
            mock_crud.delete.assert_called_with(mock_session, 1)


class TestConfigurationOperations:
    """Test all configuration-related CRUD operations."""

    @pytest.mark.asyncio
    async def test_list_configurations(self):
        """Test configuration listing - lines 425-429."""
        mock_session = Mock()
        crud = CRUDBase(mock_session)

        configs, total = await crud.list_configurations()

        # Lines 426-428: Return empty list (TODO implementation)
        assert configs == []
        assert total == 0

    @pytest.mark.asyncio
    async def test_create_configuration_with_global_scope(self):
        """Test configuration creation with global scope - lines 435-461."""
        mock_session = Mock()
        crud = CRUDBase(mock_session)

        config_data = {
            "key": "test.config",
            "value": "test_value",
            "scope": "global",
            "description": "Test config",
            "is_secret": True,
            "extra_metadata": {"category": "test"},
        }

        with patch("cc_orchestrator.web.crud_adapter.ConfigurationCRUD") as mock_crud:
            mock_config = Mock(spec=Configuration)
            mock_crud.create.return_value = mock_config

            await crud.create_configuration(config_data)

            # Lines 441-461: Scope conversion and creation
            mock_crud.create.assert_called_once_with(
                mock_session,
                key="test.config",
                value="test_value",
                scope=ConfigScope.GLOBAL,
                instance_id=None,
                description="Test config",
                is_secret=True,
                extra_metadata={"category": "test"},
            )

    @pytest.mark.asyncio
    async def test_create_configuration_with_all_scopes(self):
        """Test configuration creation with different scopes - lines 441-450."""
        mock_session = Mock()
        crud = CRUDBase(mock_session)

        # Test all scope conversions
        scope_mappings = [
            ("user", ConfigScope.USER),
            ("project", ConfigScope.PROJECT),
            ("instance", ConfigScope.INSTANCE),
            ("invalid", ConfigScope.GLOBAL),  # Default fallback
        ]

        with patch("cc_orchestrator.web.crud_adapter.ConfigurationCRUD") as mock_crud:
            mock_config = Mock(spec=Configuration)
            mock_crud.create.return_value = mock_config

            for scope_str, expected_enum in scope_mappings:
                config_data = {
                    "key": f"test.{scope_str}",
                    "value": "test_value",
                    "scope": scope_str,
                }

                await crud.create_configuration(config_data)

                # Verify correct scope enum used
                call_args = mock_crud.create.call_args[1]
                assert call_args["scope"] == expected_enum

    @pytest.mark.asyncio
    async def test_get_configuration(self):
        """Test configuration retrieval - lines 468-472."""
        mock_session = Mock()
        crud = CRUDBase(mock_session)

        result = await crud.get_configuration(1)

        # Lines 469-471: Return None (TODO implementation)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_configuration_by_key_scope_string(self):
        """Test configuration retrieval by key/scope with string - lines 480-504."""
        mock_session = Mock()
        crud = CRUDBase(mock_session)

        with patch("cc_orchestrator.web.crud_adapter.ConfigurationCRUD") as mock_crud:
            mock_config = Mock(spec=Configuration)
            mock_crud.get_by_key_scope.return_value = mock_config

            result = await crud.get_configuration_by_key_scope(
                "test.key", "global", instance_id=1
            )

            # Lines 482-501: String scope conversion and retrieval
            mock_crud.get_by_key_scope.assert_called_with(
                mock_session, "test.key", ConfigScope.GLOBAL, 1
            )
            assert result == mock_config

    @pytest.mark.asyncio
    async def test_get_configuration_by_key_scope_all_string_scopes(self):
        """Test configuration retrieval with all scope strings - lines 488-492."""
        mock_session = Mock()
        crud = CRUDBase(mock_session)

        # Test all scope string conversions to cover missing lines
        scope_tests = [
            ("user", ConfigScope.USER),  # Line 488
            ("project", ConfigScope.PROJECT),  # Line 490
            ("instance", ConfigScope.INSTANCE),  # Line 492
        ]

        with patch("cc_orchestrator.web.crud_adapter.ConfigurationCRUD") as mock_crud:
            mock_config = Mock(spec=Configuration)
            mock_crud.get_by_key_scope.return_value = mock_config

            for scope_str, expected_enum in scope_tests:
                await crud.get_configuration_by_key_scope("test.key", scope_str)

                # Verify correct enum conversion
                mock_crud.get_by_key_scope.assert_called_with(
                    mock_session, "test.key", expected_enum, None
                )

    @pytest.mark.asyncio
    async def test_get_configuration_by_key_scope_enum(self):
        """Test configuration retrieval by key/scope with enum - lines 495-504."""
        mock_session = Mock()
        crud = CRUDBase(mock_session)

        with patch("cc_orchestrator.web.crud_adapter.ConfigurationCRUD") as mock_crud:
            mock_config = Mock(spec=Configuration)
            mock_crud.get_by_key_scope.return_value = mock_config

            await crud.get_configuration_by_key_scope("test.key", ConfigScope.USER)

            # Lines 495-504: Direct enum use
            mock_crud.get_by_key_scope.assert_called_with(
                mock_session, "test.key", ConfigScope.USER, None
            )

    @pytest.mark.asyncio
    async def test_get_configuration_by_key_scope_exception(self):
        """Test configuration retrieval exception handling - lines 503-505."""
        mock_session = Mock()
        crud = CRUDBase(mock_session)

        with patch("cc_orchestrator.web.crud_adapter.ConfigurationCRUD") as mock_crud:
            mock_crud.get_by_key_scope.side_effect = Exception("Database error")

            result = await crud.get_configuration_by_key_scope("test.key", "global")

            # Lines 503-505: Exception handling returns None
            assert result is None

    @pytest.mark.asyncio
    async def test_get_exact_configuration_by_key_scope_all_scopes(self):
        """Test exact configuration retrieval with all scope strings - lines 519-529."""
        mock_session = Mock()
        crud = CRUDBase(mock_session)

        # Test all scope string conversions to cover missing lines
        scope_tests = [
            ("global", ConfigScope.GLOBAL),  # Line 519
            ("user", ConfigScope.USER),  # Line 521
            ("project", ConfigScope.PROJECT),  # Line 523
            ("instance", ConfigScope.INSTANCE),  # Line 525
            # Test else case for line 527-529
            ("invalid_scope", ConfigScope.GLOBAL),  # Lines 527-528 (else case)
        ]

        with patch("cc_orchestrator.web.crud_adapter.ConfigurationCRUD") as mock_crud:
            mock_config = Mock(spec=Configuration)
            mock_crud.get_exact_by_key_scope.return_value = mock_config

            for scope_str, expected_enum in scope_tests:
                result = await crud.get_exact_configuration_by_key_scope(
                    "test.key", scope_str, instance_id=2
                )

                # Verify correct enum conversion
                mock_crud.get_exact_by_key_scope.assert_called_with(
                    mock_session, "test.key", expected_enum, 2
                )
                assert result == mock_config

    @pytest.mark.asyncio
    async def test_get_exact_configuration_by_key_scope_enum_direct(self):
        """Test exact configuration retrieval with enum directly - line 529."""
        mock_session = Mock()
        crud = CRUDBase(mock_session)

        with patch("cc_orchestrator.web.crud_adapter.ConfigurationCRUD") as mock_crud:
            mock_config = Mock(spec=Configuration)
            mock_crud.get_exact_by_key_scope.return_value = mock_config

            # Test with enum directly (line 529: else clause)
            result = await crud.get_exact_configuration_by_key_scope(
                "test.key", ConfigScope.PROJECT, instance_id=2
            )

            # Line 529: Direct enum use (else branch)
            mock_crud.get_exact_by_key_scope.assert_called_with(
                mock_session, "test.key", ConfigScope.PROJECT, 2
            )
            assert result == mock_config

    @pytest.mark.asyncio
    async def test_get_exact_configuration_by_key_scope_exception(self):
        """Test exact configuration retrieval exception - lines 536-539."""
        mock_session = Mock()
        crud = CRUDBase(mock_session)

        with patch("cc_orchestrator.web.crud_adapter.ConfigurationCRUD") as mock_crud:
            mock_crud.get_exact_by_key_scope.side_effect = Exception("Not found")

            result = await crud.get_exact_configuration_by_key_scope(
                "test.key", "instance"
            )

            # Lines 536-539: Exception handling returns None
            assert result is None

    @pytest.mark.asyncio
    async def test_update_configuration(self):
        """Test configuration update - lines 546-566."""
        mock_session = Mock()
        crud = CRUDBase(mock_session)

        update_data = {"value": "updated_value", "is_secret": True}

        result = await crud.update_configuration(1, update_data)

        # Lines 552-566: Create dummy config with updates applied
        assert result.id == 1
        assert result.key == "updated-config-1"
        assert result.value == "updated_value"
        assert result.is_secret is True
        assert result.scope == ConfigScope.GLOBAL

    @pytest.mark.asyncio
    async def test_delete_configuration(self):
        """Test configuration deletion - lines 572-576."""
        mock_session = Mock()
        crud = CRUDBase(mock_session)

        await crud.delete_configuration(1)

        # Lines 574-575: No-op implementation (TODO)
        # Should complete without error


class TestHealthCheckOperations:
    """Test all health check-related CRUD operations."""

    @pytest.mark.asyncio
    async def test_list_health_checks_with_instance_filter(self):
        """Test health check listing with instance filter - lines 585-598."""
        mock_session = Mock()
        crud = CRUDBase(mock_session)

        filters = {"instance_id": 1}

        with patch("cc_orchestrator.web.crud_adapter.HealthCheckCRUD") as mock_crud:
            mock_checks = [Mock(spec=HealthCheck)]
            mock_crud.list_by_instance.return_value = mock_checks
            mock_crud.count_by_instance.return_value = 5

            checks, total = await crud.list_health_checks(
                offset=2, limit=10, filters=filters
            )

            # Lines 588-594: Instance filter path
            mock_crud.list_by_instance.assert_called_with(
                mock_session, 1, limit=10, offset=2
            )
            mock_crud.count_by_instance.assert_called_with(mock_session, 1)
            assert checks == mock_checks
            assert total == 5

    @pytest.mark.asyncio
    async def test_list_health_checks_without_filter(self):
        """Test health check listing without instance filter - lines 596-599."""
        mock_session = Mock()
        crud = CRUDBase(mock_session)

        checks, total = await crud.list_health_checks()

        # Lines 597-598: Return empty when no instance filter
        assert checks == []
        assert total == 0

    @pytest.mark.asyncio
    async def test_create_health_check_with_string_status(self):
        """Test health check creation with string status - lines 605-618."""
        mock_session = Mock()
        crud = CRUDBase(mock_session)

        check_data = {
            "instance_id": 1,
            "overall_status": "healthy",
            "check_results": {"cpu": "ok"},
            "duration_ms": 150,
            "check_timestamp": datetime.now(UTC),
        }

        with patch("cc_orchestrator.web.crud_adapter.HealthCheckCRUD") as mock_crud:
            mock_check = Mock(spec=HealthCheck)
            mock_crud.create.return_value = mock_check

            await crud.create_health_check(check_data)

            # Lines 607-618: String to enum conversion and creation
            mock_crud.create.assert_called_once_with(
                mock_session,
                instance_id=1,
                overall_status=HealthStatus.HEALTHY,
                check_results={"cpu": "ok"},
                duration_ms=150,
                check_timestamp=check_data["check_timestamp"],
            )

    @pytest.mark.asyncio
    async def test_create_health_check_with_enum_status(self):
        """Test health check creation with enum status - lines 611-618."""
        mock_session = Mock()
        crud = CRUDBase(mock_session)

        check_data = {
            "instance_id": 2,
            "overall_status": HealthStatus.CRITICAL,
            "check_results": {"status": "failed"},
            "duration_ms": 5000,
            "check_timestamp": datetime.now(UTC),
        }

        with patch("cc_orchestrator.web.crud_adapter.HealthCheckCRUD") as mock_crud:
            mock_check = Mock(spec=HealthCheck)
            mock_crud.create.return_value = mock_check

            await crud.create_health_check(check_data)

            # Lines 611-618: Direct enum use
            mock_crud.create.assert_called_once_with(
                mock_session,
                instance_id=2,
                overall_status=HealthStatus.CRITICAL,
                check_results={"status": "failed"},
                duration_ms=5000,
                check_timestamp=check_data["check_timestamp"],
            )


class TestAlertOperations:
    """Test alert-related operations."""

    @pytest.mark.asyncio
    async def test_list_alerts(self):
        """Test alert listing - line 627."""
        mock_session = Mock()
        crud = CRUDBase(mock_session)

        alerts, total = await crud.list_alerts()

        # Line 627: Return empty list
        assert alerts == []
        assert total == 0

    @pytest.mark.asyncio
    async def test_create_alert(self):
        """Test alert creation - lines 631-640."""
        mock_session = Mock()
        crud = CRUDBase(mock_session)

        alert_data = {
            "instance_id": 1,
            "alert_id": "ALERT-123",
            "level": "warning",
            "message": "Test alert message",
            "details": {"source": "system"},
            "timestamp": datetime.now(UTC),
        }

        alert = await crud.create_alert(alert_data)

        # Lines 631-640: Alert creation and ID assignment
        assert alert.instance_id == 1
        assert alert.alert_id == "ALERT-123"
        assert alert.level == "warning"
        assert alert.message == "Test alert message"
        assert alert.details == {"source": "system"}
        assert alert.timestamp == alert_data["timestamp"]
        assert alert.id == 1  # Line 639: Simulated assigned ID

    @pytest.mark.asyncio
    async def test_get_alert_by_alert_id(self):
        """Test alert retrieval by alert ID - line 644."""
        mock_session = Mock()
        crud = CRUDBase(mock_session)

        result = await crud.get_alert_by_alert_id("ALERT-123")

        # Line 644: Return None (placeholder implementation)
        assert result is None


class TestAsyncOperationPatterns:
    """Test async operation patterns and comprehensive edge cases."""

    @pytest.mark.asyncio
    async def test_asyncio_to_thread_called_for_all_operations(self):
        """Verify asyncio.to_thread is used consistently."""
        mock_session = Mock()
        crud = CRUDBase(mock_session)

        operations_to_test = [
            ("list_instances", []),
            ("create_instance", [{"issue_id": "TEST"}]),
            ("get_instance", [1]),
            ("get_instance_by_issue_id", ["TEST"]),
            ("update_instance", [1, {"status": "running"}]),
            ("delete_instance", [1]),
            ("list_tasks", []),
            ("create_task", [{"title": "Test"}]),
            ("get_task", [1]),
            ("update_task", [1, {"title": "Updated"}]),
            ("delete_task", [1]),
            ("list_worktrees", []),
            (
                "create_worktree",
                [{"name": "test", "path": "/test", "branch_name": "main"}],
            ),
            ("get_worktree", [1]),
            ("get_worktree_by_path", ["/test"]),
            ("update_worktree", [1, {"name": "updated"}]),
            ("delete_worktree", [1]),
            ("list_configurations", []),
            ("create_configuration", [{"key": "test", "value": "val"}]),
            ("get_configuration", [1]),
            ("get_configuration_by_key_scope", ["key", "global"]),
            ("get_exact_configuration_by_key_scope", ["key", "global"]),
            ("update_configuration", [1, {"value": "new"}]),
            ("delete_configuration", [1]),
            ("list_health_checks", []),
            (
                "create_health_check",
                [
                    {
                        "instance_id": 1,
                        "overall_status": "healthy",
                        "check_results": {},
                        "duration_ms": 100,
                        "check_timestamp": datetime.now(),
                    }
                ],
            ),
        ]

        with patch("asyncio.to_thread") as mock_to_thread:
            mock_to_thread.return_value = Mock()  # Generic return value

            # Mock all CRUD classes to prevent actual calls
            with (
                patch("cc_orchestrator.web.crud_adapter.InstanceCRUD"),
                patch("cc_orchestrator.web.crud_adapter.TaskCRUD"),
                patch("cc_orchestrator.web.crud_adapter.WorktreeCRUD"),
                patch("cc_orchestrator.web.crud_adapter.ConfigurationCRUD"),
                patch("cc_orchestrator.web.crud_adapter.HealthCheckCRUD"),
            ):

                for operation_name, args in operations_to_test:
                    mock_to_thread.reset_mock()
                    operation = getattr(crud, operation_name)

                    try:
                        await operation(*args)
                        # Verify asyncio.to_thread was called for each operation
                        mock_to_thread.assert_called_once()
                    except Exception:
                        # Some operations might fail due to mocking limitations
                        # but they should still call asyncio.to_thread
                        mock_to_thread.assert_called_once()

    @pytest.mark.asyncio
    async def test_comprehensive_error_scenarios(self):
        """Test comprehensive error handling across all operations."""
        mock_session = Mock()
        crud = CRUDBase(mock_session)

        # Test database connection errors
        mock_session.is_active = False
        result = await crud.get_instance(1)
        assert result is None

        # Test various exception types in different operations
        with patch("cc_orchestrator.web.crud_adapter.InstanceCRUD") as mock_crud:
            mock_crud.get_by_issue_id.side_effect = ValueError("Invalid ID")
            result = await crud.get_instance_by_issue_id("INVALID")
            assert result is None

            mock_crud.list_all.side_effect = RuntimeError("Connection lost")
            with pytest.raises(RuntimeError):
                await crud.list_instances()

        # Test task operation exceptions
        with patch("cc_orchestrator.web.crud_adapter.TaskCRUD") as mock_crud:
            mock_crud.get_by_id.side_effect = KeyError("Task not found")
            result = await crud.get_task(999)
            assert result is None

        # Test worktree operation exceptions
        with patch("cc_orchestrator.web.crud_adapter.WorktreeCRUD") as mock_crud:
            mock_crud.get_by_path.side_effect = OSError("Path not accessible")
            result = await crud.get_worktree_by_path("/invalid")
            assert result is None

        # Test configuration operation exceptions
        with patch("cc_orchestrator.web.crud_adapter.ConfigurationCRUD") as mock_crud:
            mock_crud.get_by_key_scope.side_effect = TimeoutError("Query timeout")
            result = await crud.get_configuration_by_key_scope("key", "scope")
            assert result is None

    @pytest.mark.asyncio
    async def test_pagination_edge_cases(self):
        """Test pagination with edge cases."""
        mock_session = Mock()
        crud = CRUDBase(mock_session)

        # Test empty results with pagination
        with patch("cc_orchestrator.web.crud_adapter.InstanceCRUD") as mock_crud:
            mock_crud.list_all.return_value = []

            instances, total = await crud.list_instances(offset=100, limit=10)
            assert instances == []
            assert total == 0

        # Test large offset with task pagination
        with patch("cc_orchestrator.web.crud_adapter.TaskCRUD") as mock_crud:
            mock_tasks = [Mock(spec=Task) for _ in range(5)]
            mock_crud.list_by_instance.return_value = mock_tasks

            filters = {"instance_id": 1}
            tasks, total = await crud.list_tasks(offset=10, limit=5, filters=filters)

            # Should return empty slice when offset exceeds available items
            assert len(tasks) == 0
            assert total == 5  # Total count unchanged

        # Test zero limit
        with patch("cc_orchestrator.web.crud_adapter.WorktreeCRUD") as mock_crud:
            mock_worktrees = [Mock(spec=Worktree) for _ in range(10)]
            mock_crud.list_all.return_value = mock_worktrees

            worktrees, total = await crud.list_worktrees(limit=0)
            assert len(worktrees) == 0
            assert total == 10

    @pytest.mark.asyncio
    async def test_enum_conversion_edge_cases(self):
        """Test enum conversion edge cases and error handling."""
        mock_session = Mock()
        crud = CRUDBase(mock_session)

        # Test invalid task priority string (should default to MEDIUM)
        with patch("cc_orchestrator.web.crud_adapter.TaskCRUD") as mock_crud:
            mock_crud.create.return_value = Mock(spec=Task)

            task_data = {"title": "Test", "priority": "INVALID_PRIORITY"}

            # The code now properly maps string priorities and defaults to MEDIUM for invalid strings
            await crud.create_task(task_data)

            # Should default to MEDIUM for invalid priority strings
            call_kwargs = mock_crud.create.call_args[1]
            assert call_kwargs["priority"] == TaskPriority.MEDIUM

        # Test case sensitivity in status conversions
        with patch("cc_orchestrator.web.crud_adapter.InstanceCRUD") as mock_crud:
            mock_instance = Mock(spec=Instance)
            mock_crud.create.return_value = mock_instance
            mock_session.flush = Mock()

            # Test lowercase conversion
            instance_data = {"issue_id": "TEST", "status": "RUNNING"}
            await crud.create_instance(instance_data)

            # Should convert to lowercase for enum
            assert mock_instance.status == InstanceStatus.RUNNING
