"""Comprehensive tests for src/cc_orchestrator/web/crud_adapter.py module.

This test suite provides comprehensive coverage for the async CRUD adapter including:
- Placeholder model classes (Alert, RecoveryAttempt)
- CRUDBase async operations for all entity types
- Instance CRUD operations with enum conversions
- Task CRUD operations with priority mapping
- Worktree CRUD operations with status handling
- Configuration CRUD operations with scope conversion
- Health check CRUD operations
- Alert operations (placeholder functionality)
- Error handling and async execution patterns

Target: 96%+ coverage (275/289 statements)
"""

import asyncio
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from sqlalchemy.orm import Session

from cc_orchestrator.web.crud_adapter import (
    Alert,
    RecoveryAttempt,
    CRUDBase,
)
from cc_orchestrator.database.models import (
    Configuration,
    ConfigScope,
    HealthCheck,
    HealthStatus,
    Instance,
    InstanceStatus,
    Task,
    TaskStatus,
    TaskPriority,
    Worktree,
    WorktreeStatus,
)


class TestAlert:
    """Test Alert placeholder model class."""

    def test_alert_creation_with_kwargs(self):
        """Test creating Alert with keyword arguments."""
        alert = Alert(
            instance_id=123,
            alert_id="alert-456",
            level="warning",
            message="Test alert message",
            details={"key": "value"},
            timestamp=datetime.now()
        )
        
        assert alert.instance_id == 123
        assert alert.alert_id == "alert-456"
        assert alert.level == "warning"
        assert alert.message == "Test alert message"
        assert alert.details == {"key": "value"}
        assert isinstance(alert.created_at, datetime)
        assert alert.id == 1  # Default id

    def test_alert_creation_minimal(self):
        """Test creating Alert with minimal arguments."""
        alert = Alert()
        
        assert alert.id == 1  # Default id
        assert alert.level == "info"  # Default level
        assert isinstance(alert.created_at, datetime)

    def test_alert_creation_with_custom_id(self):
        """Test creating Alert with custom id."""
        alert = Alert(id=999, level="error")
        
        assert alert.id == 999
        assert alert.level == "error"
        assert isinstance(alert.created_at, datetime)

    def test_alert_creation_without_level(self):
        """Test creating Alert without level gets default."""
        alert = Alert(message="test message")
        
        assert alert.level == "info"
        assert alert.message == "test message"
        assert hasattr(alert, "id")
        assert hasattr(alert, "created_at")

    def test_alert_arbitrary_attributes(self):
        """Test Alert accepts arbitrary attributes."""
        alert = Alert(
            custom_field="custom_value",
            another_field=42,
            nested_data={"nested": True}
        )
        
        assert alert.custom_field == "custom_value"
        assert alert.another_field == 42
        assert alert.nested_data == {"nested": True}


class TestRecoveryAttempt:
    """Test RecoveryAttempt placeholder model class."""

    def test_recovery_attempt_creation_with_kwargs(self):
        """Test creating RecoveryAttempt with keyword arguments."""
        recovery = RecoveryAttempt(
            instance_id=123,
            attempt_type="automatic",
            success=True,
            error_message=None,
            duration_ms=1500
        )
        
        assert recovery.instance_id == 123
        assert recovery.attempt_type == "automatic"
        assert recovery.success is True
        assert recovery.error_message is None
        assert recovery.duration_ms == 1500
        assert isinstance(recovery.created_at, datetime)
        assert recovery.id == 1  # Default id

    def test_recovery_attempt_creation_minimal(self):
        """Test creating RecoveryAttempt with minimal arguments."""
        recovery = RecoveryAttempt()
        
        assert recovery.id == 1  # Default id
        assert isinstance(recovery.created_at, datetime)

    def test_recovery_attempt_creation_with_custom_id(self):
        """Test creating RecoveryAttempt with custom id."""
        recovery = RecoveryAttempt(id=777, success=False)
        
        assert recovery.id == 777
        assert recovery.success is False
        assert isinstance(recovery.created_at, datetime)

    def test_recovery_attempt_arbitrary_attributes(self):
        """Test RecoveryAttempt accepts arbitrary attributes."""
        recovery = RecoveryAttempt(
            metadata={"key": "value"},
            recovery_data=[1, 2, 3],
            timestamp=datetime.now()
        )
        
        assert recovery.metadata == {"key": "value"}
        assert recovery.recovery_data == [1, 2, 3]
        assert hasattr(recovery, "timestamp")


class TestCRUDBaseInitialization:
    """Test CRUDBase initialization."""

    def test_crud_base_init(self):
        """Test CRUDBase initialization with session."""
        mock_session = Mock(spec=Session)
        crud = CRUDBase(mock_session)
        
        assert crud.session is mock_session


class TestInstanceOperations:
    """Test CRUDBase instance operations."""

    def setUp(self):
        self.mock_session = Mock(spec=Session)
        self.crud = CRUDBase(self.mock_session)

    @pytest.mark.asyncio
    async def test_list_instances_no_filters(self):
        """Test listing instances without filters."""
        mock_instances = [Mock(spec=Instance), Mock(spec=Instance)]
        
        with patch('cc_orchestrator.web.crud_adapter.InstanceCRUD') as mock_crud:
            mock_crud.list_all.return_value = mock_instances
            
            crud = CRUDBase(Mock(spec=Session))
            instances, total = await crud.list_instances()
            
            assert instances == mock_instances
            assert total == 2
            mock_crud.list_all.assert_called()

    @pytest.mark.asyncio
    async def test_list_instances_with_status_filter_string(self):
        """Test listing instances with string status filter."""
        mock_instances = [Mock(spec=Instance)]
        
        with patch('cc_orchestrator.web.crud_adapter.InstanceCRUD') as mock_crud:
            mock_crud.list_all.return_value = mock_instances
            
            crud = CRUDBase(Mock(spec=Session))
            instances, total = await crud.list_instances(
                filters={"status": "active"}
            )
            
            assert instances == mock_instances
            assert total == 1
            # Should convert string to InstanceStatus enum
            mock_crud.list_all.assert_called()

    @pytest.mark.asyncio
    async def test_list_instances_with_status_filter_enum(self):
        """Test listing instances with enum status filter."""
        mock_instances = [Mock(spec=Instance)]
        
        with patch('cc_orchestrator.web.crud_adapter.InstanceCRUD') as mock_crud:
            mock_crud.list_all.return_value = mock_instances
            
            crud = CRUDBase(Mock(spec=Session))
            instances, total = await crud.list_instances(
                filters={"status": InstanceStatus.ACTIVE}
            )
            
            assert instances == mock_instances
            assert total == 1

    @pytest.mark.asyncio
    async def test_list_instances_with_pagination(self):
        """Test listing instances with pagination."""
        mock_instances = [Mock(spec=Instance) for _ in range(5)]
        
        with patch('cc_orchestrator.web.crud_adapter.InstanceCRUD') as mock_crud:
            mock_crud.list_all.return_value = mock_instances
            
            crud = CRUDBase(Mock(spec=Session))
            instances, total = await crud.list_instances(offset=10, limit=5)
            
            assert instances == mock_instances
            assert total == 5

    @pytest.mark.asyncio
    async def test_create_instance_basic(self):
        """Test creating instance with basic data."""
        mock_instance = Mock(spec=Instance)
        instance_data = {
            "issue_id": "ISSUE-123",
            "workspace_path": "/path/to/workspace",
            "branch_name": "feature/test"
        }
        
        with patch('cc_orchestrator.web.crud_adapter.InstanceCRUD') as mock_crud:
            mock_crud.create.return_value = mock_instance
            
            crud = CRUDBase(Mock(spec=Session))
            result = await crud.create_instance(instance_data)
            
            assert result is mock_instance
            mock_crud.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_instance_with_status_string(self):
        """Test creating instance with string status."""
        mock_instance = Mock(spec=Instance)
        mock_session = Mock(spec=Session)
        instance_data = {
            "issue_id": "ISSUE-123",
            "status": "active"
        }
        
        with patch('cc_orchestrator.web.crud_adapter.InstanceCRUD') as mock_crud:
            mock_crud.create.return_value = mock_instance
            
            crud = CRUDBase(mock_session)
            result = await crud.create_instance(instance_data)
            
            assert result is mock_instance
            # Should set status on instance and flush session
            mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_instance_with_status_enum(self):
        """Test creating instance with enum status."""
        mock_instance = Mock(spec=Instance)
        mock_session = Mock(spec=Session)
        instance_data = {
            "issue_id": "ISSUE-123",
            "status": InstanceStatus.ACTIVE
        }
        
        with patch('cc_orchestrator.web.crud_adapter.InstanceCRUD') as mock_crud:
            mock_crud.create.return_value = mock_instance
            
            crud = CRUDBase(mock_session)
            result = await crud.create_instance(instance_data)
            
            assert result is mock_instance
            mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_instance_success(self):
        """Test getting instance by ID successfully."""
        mock_instance = Mock(spec=Instance)
        
        with patch('cc_orchestrator.web.crud_adapter.InstanceCRUD') as mock_crud:
            mock_crud.get_by_id.return_value = mock_instance
            
            crud = CRUDBase(Mock(spec=Session))
            result = await crud.get_instance(123)
            
            assert result is mock_instance
            mock_crud.get_by_id.assert_called_once_with(crud.session, 123)

    @pytest.mark.asyncio
    async def test_get_instance_not_found(self):
        """Test getting instance by ID when not found."""
        with patch('cc_orchestrator.web.crud_adapter.InstanceCRUD') as mock_crud:
            mock_crud.get_by_id.side_effect = Exception("Not found")
            
            crud = CRUDBase(Mock(spec=Session))
            result = await crud.get_instance(999)
            
            assert result is None

    @pytest.mark.asyncio
    async def test_get_instance_inactive_session(self):
        """Test getting instance with inactive session."""
        mock_session = Mock(spec=Session)
        mock_session.is_active = False
        
        crud = CRUDBase(mock_session)
        result = await crud.get_instance(123)
        
        assert result is None

    @pytest.mark.asyncio
    async def test_get_instance_by_issue_id_success(self):
        """Test getting instance by issue ID successfully."""
        mock_instance = Mock(spec=Instance)
        
        with patch('cc_orchestrator.web.crud_adapter.InstanceCRUD') as mock_crud:
            mock_crud.get_by_issue_id.return_value = mock_instance
            
            crud = CRUDBase(Mock(spec=Session))
            result = await crud.get_instance_by_issue_id("ISSUE-123")
            
            assert result is mock_instance
            mock_crud.get_by_issue_id.assert_called_once_with(crud.session, "ISSUE-123")

    @pytest.mark.asyncio
    async def test_get_instance_by_issue_id_not_found(self):
        """Test getting instance by issue ID when not found."""
        with patch('cc_orchestrator.web.crud_adapter.InstanceCRUD') as mock_crud:
            mock_crud.get_by_issue_id.side_effect = Exception("Not found")
            
            crud = CRUDBase(Mock(spec=Session))
            result = await crud.get_instance_by_issue_id("NONEXISTENT")
            
            assert result is None

    @pytest.mark.asyncio
    async def test_update_instance_basic(self):
        """Test updating instance with basic data."""
        mock_instance = Mock(spec=Instance)
        update_data = {"workspace_path": "/new/path"}
        
        with patch('cc_orchestrator.web.crud_adapter.InstanceCRUD') as mock_crud:
            mock_crud.update.return_value = mock_instance
            
            crud = CRUDBase(Mock(spec=Session))
            result = await crud.update_instance(123, update_data)
            
            assert result is mock_instance
            mock_crud.update.assert_called_once_with(crud.session, 123, **update_data)

    @pytest.mark.asyncio
    async def test_update_instance_with_status_string(self):
        """Test updating instance with string status."""
        mock_instance = Mock(spec=Instance)
        update_data = {"status": "completed"}
        
        with patch('cc_orchestrator.web.crud_adapter.InstanceCRUD') as mock_crud:
            mock_crud.update.return_value = mock_instance
            
            crud = CRUDBase(Mock(spec=Session))
            result = await crud.update_instance(123, update_data)
            
            assert result is mock_instance
            # Should convert string to enum
            call_args = mock_crud.update.call_args
            assert call_args[1]["status"] == InstanceStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_update_instance_with_status_enum(self):
        """Test updating instance with enum status."""
        mock_instance = Mock(spec=Instance)
        update_data = {"status": InstanceStatus.FAILED}
        
        with patch('cc_orchestrator.web.crud_adapter.InstanceCRUD') as mock_crud:
            mock_crud.update.return_value = mock_instance
            
            crud = CRUDBase(Mock(spec=Session))
            result = await crud.update_instance(123, update_data)
            
            assert result is mock_instance

    @pytest.mark.asyncio
    async def test_delete_instance(self):
        """Test deleting instance."""
        with patch('cc_orchestrator.web.crud_adapter.InstanceCRUD') as mock_crud:
            crud = CRUDBase(Mock(spec=Session))
            await crud.delete_instance(123)
            
            mock_crud.delete.assert_called_once_with(crud.session, 123)


class TestTaskOperations:
    """Test CRUDBase task operations."""

    @pytest.mark.asyncio
    async def test_list_tasks_no_filters(self):
        """Test listing tasks without filters."""
        mock_tasks = [Mock(spec=Task), Mock(spec=Task)]
        
        with patch('cc_orchestrator.web.crud_adapter.TaskCRUD') as mock_crud:
            mock_crud.list_pending.return_value = mock_tasks
            
            crud = CRUDBase(Mock(spec=Session))
            tasks, total = await crud.list_tasks()
            
            assert tasks == mock_tasks
            assert total == 2

    @pytest.mark.asyncio
    async def test_list_tasks_with_instance_id_filter(self):
        """Test listing tasks with instance_id filter."""
        mock_tasks = [Mock(spec=Task)]
        
        with patch('cc_orchestrator.web.crud_adapter.TaskCRUD') as mock_crud:
            mock_crud.list_by_instance.return_value = mock_tasks
            
            crud = CRUDBase(Mock(spec=Session))
            tasks, total = await crud.list_tasks(
                filters={"instance_id": 123}
            )
            
            assert tasks == mock_tasks
            assert total == 1
            mock_crud.list_by_instance.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_tasks_with_instance_and_status_filters(self):
        """Test listing tasks with instance_id and status filters."""
        mock_tasks = [Mock(spec=Task)]
        
        with patch('cc_orchestrator.web.crud_adapter.TaskCRUD') as mock_crud:
            mock_crud.list_by_instance.return_value = mock_tasks
            
            crud = CRUDBase(Mock(spec=Session))
            tasks, total = await crud.list_tasks(
                filters={"instance_id": 123, "status": "pending"}
            )
            
            assert tasks == mock_tasks
            assert total == 1
            # Should convert string status to enum
            call_args = mock_crud.list_by_instance.call_args
            assert call_args[1]["status"] == TaskStatus.PENDING

    @pytest.mark.asyncio
    async def test_list_tasks_with_pagination_general(self):
        """Test listing tasks with pagination for general listing."""
        mock_tasks = [Mock(spec=Task) for _ in range(10)]
        
        with patch('cc_orchestrator.web.crud_adapter.TaskCRUD') as mock_crud:
            mock_crud.list_pending.return_value = mock_tasks
            
            crud = CRUDBase(Mock(spec=Session))
            tasks, total = await crud.list_tasks(offset=5, limit=3)
            
            # Should apply offset manually
            assert len(tasks) == 5  # Remaining tasks after offset
            assert total == 10

    @pytest.mark.asyncio
    async def test_list_tasks_with_pagination_instance_filter(self):
        """Test listing tasks with pagination and instance filter."""
        mock_tasks = [Mock(spec=Task) for _ in range(8)]
        
        with patch('cc_orchestrator.web.crud_adapter.TaskCRUD') as mock_crud:
            mock_crud.list_by_instance.return_value = mock_tasks
            
            crud = CRUDBase(Mock(spec=Session))
            tasks, total = await crud.list_tasks(
                offset=2, limit=3, filters={"instance_id": 123}
            )
            
            assert len(tasks) == 3  # Should be paginated slice
            assert total == 8

    @pytest.mark.asyncio
    async def test_create_task_basic(self):
        """Test creating task with basic data."""
        mock_task = Mock(spec=Task)
        task_data = {
            "title": "Test Task",
            "description": "Test description"
        }
        
        with patch('cc_orchestrator.web.crud_adapter.TaskCRUD') as mock_crud:
            mock_crud.create.return_value = mock_task
            
            crud = CRUDBase(Mock(spec=Session))
            result = await crud.create_task(task_data)
            
            assert result is mock_task
            mock_crud.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_task_with_string_priority(self):
        """Test creating task with string priority."""
        mock_task = Mock(spec=Task)
        task_data = {
            "title": "Test Task",
            "priority": "high"
        }
        
        with patch('cc_orchestrator.web.crud_adapter.TaskCRUD') as mock_crud:
            mock_crud.create.return_value = mock_task
            
            crud = CRUDBase(Mock(spec=Session))
            result = await crud.create_task(task_data)
            
            assert result is mock_task
            # Should convert string to enum
            call_args = mock_crud.create.call_args
            assert call_args[1]["priority"] == TaskPriority.HIGH

    @pytest.mark.asyncio
    async def test_create_task_with_integer_priority(self):
        """Test creating task with integer priority."""
        mock_task = Mock(spec=Task)
        task_data = {
            "title": "Test Task",
            "priority": 4  # Should map to URGENT
        }
        
        with patch('cc_orchestrator.web.crud_adapter.TaskCRUD') as mock_crud:
            mock_crud.create.return_value = mock_task
            
            crud = CRUDBase(Mock(spec=Session))
            result = await crud.create_task(task_data)
            
            assert result is mock_task
            # Should convert integer to enum
            call_args = mock_crud.create.call_args
            assert call_args[1]["priority"] == TaskPriority.URGENT

    @pytest.mark.asyncio
    async def test_create_task_with_invalid_integer_priority(self):
        """Test creating task with invalid integer priority defaults to MEDIUM."""
        mock_task = Mock(spec=Task)
        task_data = {
            "title": "Test Task",
            "priority": 99  # Invalid, should default to MEDIUM
        }
        
        with patch('cc_orchestrator.web.crud_adapter.TaskCRUD') as mock_crud:
            mock_crud.create.return_value = mock_task
            
            crud = CRUDBase(Mock(spec=Session))
            result = await crud.create_task(task_data)
            
            assert result is mock_task
            # Should default to MEDIUM for invalid integer
            call_args = mock_crud.create.call_args
            assert call_args[1]["priority"] == TaskPriority.MEDIUM

    @pytest.mark.asyncio
    async def test_create_task_with_all_fields(self):
        """Test creating task with all possible fields."""
        mock_task = Mock(spec=Task)
        due_date = datetime.now() + timedelta(days=7)
        task_data = {
            "title": "Complete Task",
            "description": "Full description",
            "priority": TaskPriority.LOW,
            "instance_id": 123,
            "worktree_id": 456,
            "due_date": due_date,
            "estimated_duration": 3600,
            "requirements": {"python": "3.9+"},
            "extra_metadata": {"source": "api"}
        }
        
        with patch('cc_orchestrator.web.crud_adapter.TaskCRUD') as mock_crud:
            mock_crud.create.return_value = mock_task
            
            crud = CRUDBase(Mock(spec=Session))
            result = await crud.create_task(task_data)
            
            assert result is mock_task
            call_args = mock_crud.create.call_args
            assert call_args[1]["title"] == "Complete Task"
            assert call_args[1]["instance_id"] == 123
            assert call_args[1]["worktree_id"] == 456

    @pytest.mark.asyncio
    async def test_get_task_success(self):
        """Test getting task by ID successfully."""
        mock_task = Mock(spec=Task)
        
        with patch('cc_orchestrator.web.crud_adapter.TaskCRUD') as mock_crud:
            mock_crud.get_by_id.return_value = mock_task
            
            crud = CRUDBase(Mock(spec=Session))
            result = await crud.get_task(123)
            
            assert result is mock_task
            mock_crud.get_by_id.assert_called_once_with(crud.session, 123)

    @pytest.mark.asyncio
    async def test_get_task_not_found(self):
        """Test getting task by ID when not found."""
        with patch('cc_orchestrator.web.crud_adapter.TaskCRUD') as mock_crud:
            mock_crud.get_by_id.side_effect = Exception("Not found")
            
            crud = CRUDBase(Mock(spec=Session))
            result = await crud.get_task(999)
            
            assert result is None

    @pytest.mark.asyncio
    async def test_update_task_with_status(self):
        """Test updating task with status change."""
        mock_task = Mock(spec=Task)
        update_data = {"status": "completed"}
        
        with patch('cc_orchestrator.web.crud_adapter.TaskCRUD') as mock_crud:
            mock_crud.update_status.return_value = mock_task
            
            crud = CRUDBase(Mock(spec=Session))
            result = await crud.update_task(123, update_data)
            
            assert result is mock_task
            # Should use update_status for status changes
            mock_crud.update_status.assert_called_once()
            call_args = mock_crud.update_status.call_args
            assert call_args[0][2] == TaskStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_update_task_without_status(self):
        """Test updating task without status change."""
        mock_task = Mock(spec=Task)
        update_data = {"instance_id": 456}
        
        with patch('cc_orchestrator.web.crud_adapter.TaskCRUD') as mock_crud:
            mock_crud.update.return_value = mock_task
            
            crud = CRUDBase(Mock(spec=Session))
            result = await crud.update_task(123, update_data)
            
            assert result is mock_task
            # Should use general update for non-status changes
            mock_crud.update.assert_called_once_with(crud.session, 123, **update_data)

    @pytest.mark.asyncio
    async def test_update_task_with_status_enum(self):
        """Test updating task with status enum."""
        mock_task = Mock(spec=Task)
        update_data = {"status": TaskStatus.IN_PROGRESS}
        
        with patch('cc_orchestrator.web.crud_adapter.TaskCRUD') as mock_crud:
            mock_crud.update_status.return_value = mock_task
            
            crud = CRUDBase(Mock(spec=Session))
            result = await crud.update_task(123, update_data)
            
            assert result is mock_task

    @pytest.mark.asyncio
    async def test_delete_task(self):
        """Test deleting task (validates existence)."""
        mock_task = Mock(spec=Task)
        
        with patch('cc_orchestrator.web.crud_adapter.TaskCRUD') as mock_crud:
            mock_crud.get_by_id.return_value = mock_task
            
            crud = CRUDBase(Mock(spec=Session))
            await crud.delete_task(123)
            
            # Should validate task exists
            mock_crud.get_by_id.assert_called_once_with(crud.session, 123)


class TestWorktreeOperations:
    """Test CRUDBase worktree operations."""

    @pytest.mark.asyncio
    async def test_list_worktrees_no_filters(self):
        """Test listing worktrees without filters."""
        mock_worktrees = [Mock(spec=Worktree), Mock(spec=Worktree)]
        
        with patch('cc_orchestrator.web.crud_adapter.WorktreeCRUD') as mock_crud:
            mock_crud.list_all.return_value = mock_worktrees
            
            crud = CRUDBase(Mock(spec=Session))
            worktrees, total = await crud.list_worktrees()
            
            assert worktrees == mock_worktrees
            assert total == 2

    @pytest.mark.asyncio
    async def test_list_worktrees_with_status_filter_string(self):
        """Test listing worktrees with string status filter."""
        mock_worktrees = [Mock(spec=Worktree)]
        
        with patch('cc_orchestrator.web.crud_adapter.WorktreeCRUD') as mock_crud:
            mock_crud.list_by_status.return_value = mock_worktrees
            
            crud = CRUDBase(Mock(spec=Session))
            worktrees, total = await crud.list_worktrees(
                filters={"status": "active"}
            )
            
            assert worktrees == mock_worktrees
            assert total == 1
            # Should convert string to enum and use list_by_status
            mock_crud.list_by_status.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_worktrees_with_status_filter_enum(self):
        """Test listing worktrees with enum status filter."""
        mock_worktrees = [Mock(spec=Worktree)]
        
        with patch('cc_orchestrator.web.crud_adapter.WorktreeCRUD') as mock_crud:
            mock_crud.list_by_status.return_value = mock_worktrees
            
            crud = CRUDBase(Mock(spec=Session))
            worktrees, total = await crud.list_worktrees(
                filters={"status": WorktreeStatus.ACTIVE}
            )
            
            assert worktrees == mock_worktrees
            assert total == 1

    @pytest.mark.asyncio
    async def test_list_worktrees_with_pagination(self):
        """Test listing worktrees with pagination."""
        mock_worktrees = [Mock(spec=Worktree) for _ in range(10)]
        
        with patch('cc_orchestrator.web.crud_adapter.WorktreeCRUD') as mock_crud:
            mock_crud.list_all.return_value = mock_worktrees
            
            crud = CRUDBase(Mock(spec=Session))
            worktrees, total = await crud.list_worktrees(offset=3, limit=4)
            
            assert len(worktrees) == 4  # Should be paginated slice
            assert total == 10

    @pytest.mark.asyncio
    async def test_create_worktree_basic(self):
        """Test creating worktree with basic data."""
        mock_worktree = Mock(spec=Worktree)
        worktree_data = {
            "name": "test-worktree",
            "path": "/path/to/worktree",
            "branch_name": "feature/test"
        }
        
        with patch('cc_orchestrator.web.crud_adapter.WorktreeCRUD') as mock_crud:
            mock_crud.create.return_value = mock_worktree
            
            crud = CRUDBase(Mock(spec=Session))
            result = await crud.create_worktree(worktree_data)
            
            assert result is mock_worktree
            mock_crud.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_worktree_with_all_fields(self):
        """Test creating worktree with all fields."""
        mock_worktree = Mock(spec=Worktree)
        worktree_data = {
            "name": "full-worktree",
            "path": "/full/path",
            "branch_name": "main",
            "repository_url": "https://github.com/user/repo.git",
            "instance_id": 123,
            "git_config": {"user.email": "test@example.com"},
            "extra_metadata": {"project": "test"}
        }
        
        with patch('cc_orchestrator.web.crud_adapter.WorktreeCRUD') as mock_crud:
            mock_crud.create.return_value = mock_worktree
            
            crud = CRUDBase(Mock(spec=Session))
            result = await crud.create_worktree(worktree_data)
            
            assert result is mock_worktree
            call_args = mock_crud.create.call_args
            assert call_args[1]["repository_url"] == "https://github.com/user/repo.git"
            assert call_args[1]["instance_id"] == 123

    @pytest.mark.asyncio
    async def test_get_worktree_success(self):
        """Test getting worktree by ID successfully."""
        mock_worktree = Mock(spec=Worktree)
        
        with patch('cc_orchestrator.web.crud_adapter.WorktreeCRUD') as mock_crud:
            mock_crud.get_by_id.return_value = mock_worktree
            
            crud = CRUDBase(Mock(spec=Session))
            result = await crud.get_worktree(123)
            
            assert result is mock_worktree
            mock_crud.get_by_id.assert_called_once_with(crud.session, 123)

    @pytest.mark.asyncio
    async def test_get_worktree_not_found(self):
        """Test getting worktree by ID when not found."""
        with patch('cc_orchestrator.web.crud_adapter.WorktreeCRUD') as mock_crud:
            mock_crud.get_by_id.side_effect = Exception("Not found")
            
            crud = CRUDBase(Mock(spec=Session))
            result = await crud.get_worktree(999)
            
            assert result is None

    @pytest.mark.asyncio
    async def test_get_worktree_by_path_success(self):
        """Test getting worktree by path successfully."""
        mock_worktree = Mock(spec=Worktree)
        
        with patch('cc_orchestrator.web.crud_adapter.WorktreeCRUD') as mock_crud:
            mock_crud.get_by_path.return_value = mock_worktree
            
            crud = CRUDBase(Mock(spec=Session))
            result = await crud.get_worktree_by_path("/path/to/worktree")
            
            assert result is mock_worktree
            mock_crud.get_by_path.assert_called_once_with(crud.session, "/path/to/worktree")

    @pytest.mark.asyncio
    async def test_get_worktree_by_path_not_found(self):
        """Test getting worktree by path when not found."""
        with patch('cc_orchestrator.web.crud_adapter.WorktreeCRUD') as mock_crud:
            mock_crud.get_by_path.side_effect = Exception("Not found")
            
            crud = CRUDBase(Mock(spec=Session))
            result = await crud.get_worktree_by_path("/nonexistent/path")
            
            assert result is None

    @pytest.mark.asyncio
    async def test_update_worktree_status_only(self):
        """Test updating worktree status only."""
        mock_worktree = Mock(spec=Worktree)
        mock_worktree.status = WorktreeStatus.ACTIVE
        update_data = {"status": "inactive"}
        
        with patch('cc_orchestrator.web.crud_adapter.WorktreeCRUD') as mock_crud:
            mock_crud.get_by_id.return_value = mock_worktree
            mock_crud.update_status.return_value = mock_worktree
            
            crud = CRUDBase(Mock(spec=Session))
            result = await crud.update_worktree(123, update_data)
            
            assert result is mock_worktree
            mock_crud.update_status.assert_called_once()
            call_args = mock_crud.update_status.call_args
            assert call_args[0][2] == WorktreeStatus.INACTIVE

    @pytest.mark.asyncio
    async def test_update_worktree_with_git_info(self):
        """Test updating worktree with git information."""
        mock_worktree = Mock(spec=Worktree)
        mock_worktree.status = WorktreeStatus.ACTIVE
        update_data = {
            "current_commit": "abc123",
            "has_uncommitted_changes": True
        }
        
        with patch('cc_orchestrator.web.crud_adapter.WorktreeCRUD') as mock_crud:
            mock_crud.get_by_id.return_value = mock_worktree
            mock_crud.update_status.return_value = mock_worktree
            
            crud = CRUDBase(Mock(spec=Session))
            result = await crud.update_worktree(123, update_data)
            
            assert result is mock_worktree
            mock_crud.update_status.assert_called_once()
            call_args = mock_crud.update_status.call_args
            assert call_args[1]["current_commit"] == "abc123"
            assert call_args[1]["has_uncommitted_changes"] is True

    @pytest.mark.asyncio
    async def test_update_worktree_status_and_git_info(self):
        """Test updating worktree with status and git information."""
        mock_worktree = Mock(spec=Worktree)
        mock_worktree.status = WorktreeStatus.ACTIVE
        update_data = {
            "status": WorktreeStatus.SYNCHRONIZING,
            "current_commit": "def456",
            "has_uncommitted_changes": False
        }
        
        with patch('cc_orchestrator.web.crud_adapter.WorktreeCRUD') as mock_crud:
            mock_crud.get_by_id.return_value = mock_worktree
            mock_crud.update_status.return_value = mock_worktree
            
            crud = CRUDBase(Mock(spec=Session))
            result = await crud.update_worktree(123, update_data)
            
            assert result is mock_worktree

    @pytest.mark.asyncio
    async def test_update_worktree_other_fields(self):
        """Test updating worktree with other fields (falls back to get_by_id)."""
        mock_worktree = Mock(spec=Worktree)
        update_data = {"description": "Updated description"}
        
        with patch('cc_orchestrator.web.crud_adapter.WorktreeCRUD') as mock_crud:
            mock_crud.get_by_id.return_value = mock_worktree
            
            crud = CRUDBase(Mock(spec=Session))
            result = await crud.update_worktree(123, update_data)
            
            assert result is mock_worktree
            # Should fall back to get_by_id since no general update method exists
            mock_crud.get_by_id.assert_called_once_with(crud.session, 123)

    @pytest.mark.asyncio
    async def test_delete_worktree(self):
        """Test deleting worktree."""
        with patch('cc_orchestrator.web.crud_adapter.WorktreeCRUD') as mock_crud:
            crud = CRUDBase(Mock(spec=Session))
            await crud.delete_worktree(123)
            
            mock_crud.delete.assert_called_once_with(crud.session, 123)


class TestConfigurationOperations:
    """Test CRUDBase configuration operations."""

    @pytest.mark.asyncio
    async def test_list_configurations(self):
        """Test listing configurations (returns empty for now)."""
        crud = CRUDBase(Mock(spec=Session))
        configs, total = await crud.list_configurations()
        
        assert configs == []
        assert total == 0

    @pytest.mark.asyncio
    async def test_create_configuration_basic(self):
        """Test creating configuration with basic data."""
        mock_config = Mock(spec=Configuration)
        config_data = {
            "key": "test.setting",
            "value": "test_value"
        }
        
        with patch('cc_orchestrator.web.crud_adapter.ConfigurationCRUD') as mock_crud:
            mock_crud.create.return_value = mock_config
            
            crud = CRUDBase(Mock(spec=Session))
            result = await crud.create_configuration(config_data)
            
            assert result is mock_config
            mock_crud.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_configuration_with_string_scopes(self):
        """Test creating configuration with various string scopes."""
        mock_config = Mock(spec=Configuration)
        
        scopes_to_test = [
            ("global", ConfigScope.GLOBAL),
            ("user", ConfigScope.USER),
            ("project", ConfigScope.PROJECT),
            ("instance", ConfigScope.INSTANCE),
            ("unknown", ConfigScope.GLOBAL)  # Should default to GLOBAL
        ]
        
        with patch('cc_orchestrator.web.crud_adapter.ConfigurationCRUD') as mock_crud:
            mock_crud.create.return_value = mock_config
            
            for scope_str, expected_enum in scopes_to_test:
                config_data = {
                    "key": f"test.{scope_str}",
                    "value": "test_value",
                    "scope": scope_str
                }
                
                crud = CRUDBase(Mock(spec=Session))
                result = await crud.create_configuration(config_data)
                
                assert result is mock_config
                call_args = mock_crud.create.call_args
                assert call_args[1]["scope"] == expected_enum

    @pytest.mark.asyncio
    async def test_create_configuration_with_all_fields(self):
        """Test creating configuration with all fields."""
        mock_config = Mock(spec=Configuration)
        config_data = {
            "key": "complex.setting",
            "value": {"nested": "value"},
            "scope": ConfigScope.INSTANCE,
            "instance_id": 123,
            "description": "Test configuration",
            "is_secret": True,
            "extra_metadata": {"source": "api"}
        }
        
        with patch('cc_orchestrator.web.crud_adapter.ConfigurationCRUD') as mock_crud:
            mock_crud.create.return_value = mock_config
            
            crud = CRUDBase(Mock(spec=Session))
            result = await crud.create_configuration(config_data)
            
            assert result is mock_config
            call_args = mock_crud.create.call_args
            assert call_args[1]["instance_id"] == 123
            assert call_args[1]["is_secret"] is True

    @pytest.mark.asyncio
    async def test_get_configuration(self):
        """Test getting configuration by ID (returns None for now)."""
        crud = CRUDBase(Mock(spec=Session))
        result = await crud.get_configuration(123)
        
        assert result is None

    @pytest.mark.asyncio
    async def test_get_configuration_by_key_scope_success(self):
        """Test getting configuration by key and scope successfully."""
        mock_config = Mock(spec=Configuration)
        
        with patch('cc_orchestrator.web.crud_adapter.ConfigurationCRUD') as mock_crud:
            mock_crud.get_by_key_scope.return_value = mock_config
            
            crud = CRUDBase(Mock(spec=Session))
            result = await crud.get_configuration_by_key_scope(
                "test.key", "global", instance_id=None
            )
            
            assert result is mock_config
            mock_crud.get_by_key_scope.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_configuration_by_key_scope_with_string_scope(self):
        """Test getting configuration by key with string scope conversion."""
        mock_config = Mock(spec=Configuration)
        
        with patch('cc_orchestrator.web.crud_adapter.ConfigurationCRUD') as mock_crud:
            mock_crud.get_by_key_scope.return_value = mock_config
            
            crud = CRUDBase(Mock(spec=Session))
            result = await crud.get_configuration_by_key_scope(
                "test.key", "instance", instance_id=456
            )
            
            assert result is mock_config
            call_args = mock_crud.get_by_key_scope.call_args
            assert call_args[0][2] == ConfigScope.INSTANCE
            assert call_args[0][3] == 456

    @pytest.mark.asyncio
    async def test_get_configuration_by_key_scope_not_found(self):
        """Test getting configuration by key and scope when not found."""
        with patch('cc_orchestrator.web.crud_adapter.ConfigurationCRUD') as mock_crud:
            mock_crud.get_by_key_scope.side_effect = Exception("Not found")
            
            crud = CRUDBase(Mock(spec=Session))
            result = await crud.get_configuration_by_key_scope(
                "nonexistent.key", ConfigScope.GLOBAL
            )
            
            assert result is None

    @pytest.mark.asyncio
    async def test_get_exact_configuration_by_key_scope_success(self):
        """Test getting exact configuration by key and scope successfully."""
        mock_config = Mock(spec=Configuration)
        
        with patch('cc_orchestrator.web.crud_adapter.ConfigurationCRUD') as mock_crud:
            mock_crud.get_exact_by_key_scope.return_value = mock_config
            
            crud = CRUDBase(Mock(spec=Session))
            result = await crud.get_exact_configuration_by_key_scope(
                "exact.key", "user", instance_id=None
            )
            
            assert result is mock_config
            mock_crud.get_exact_by_key_scope.assert_called_once()
            call_args = mock_crud.get_exact_by_key_scope.call_args
            assert call_args[0][2] == ConfigScope.USER

    @pytest.mark.asyncio
    async def test_get_exact_configuration_by_key_scope_with_enum(self):
        """Test getting exact configuration with enum scope."""
        mock_config = Mock(spec=Configuration)
        
        with patch('cc_orchestrator.web.crud_adapter.ConfigurationCRUD') as mock_crud:
            mock_crud.get_exact_by_key_scope.return_value = mock_config
            
            crud = CRUDBase(Mock(spec=Session))
            result = await crud.get_exact_configuration_by_key_scope(
                "exact.key", ConfigScope.PROJECT
            )
            
            assert result is mock_config

    @pytest.mark.asyncio
    async def test_get_exact_configuration_by_key_scope_not_found(self):
        """Test getting exact configuration when not found."""
        with patch('cc_orchestrator.web.crud_adapter.ConfigurationCRUD') as mock_crud:
            mock_crud.get_exact_by_key_scope.side_effect = Exception("Not found")
            
            crud = CRUDBase(Mock(spec=Session))
            result = await crud.get_exact_configuration_by_key_scope(
                "nonexistent.key", "global"
            )
            
            assert result is None

    @pytest.mark.asyncio
    async def test_update_configuration(self):
        """Test updating configuration (creates dummy config)."""
        update_data = {"value": "new_value", "description": "Updated"}
        
        crud = CRUDBase(Mock(spec=Session))
        result = await crud.update_configuration(123, update_data)
        
        assert isinstance(result, Configuration)
        assert result.id == 123
        assert result.value == "new_value"
        assert result.description == "Updated"

    @pytest.mark.asyncio
    async def test_delete_configuration(self):
        """Test deleting configuration (no-op for now)."""
        crud = CRUDBase(Mock(spec=Session))
        # Should not raise any exception
        await crud.delete_configuration(123)


class TestHealthCheckOperations:
    """Test CRUDBase health check operations."""

    @pytest.mark.asyncio
    async def test_list_health_checks_with_instance_filter(self):
        """Test listing health checks with instance_id filter."""
        mock_checks = [Mock(spec=HealthCheck)]
        
        with patch('cc_orchestrator.web.crud_adapter.HealthCheckCRUD') as mock_crud:
            mock_crud.list_by_instance.return_value = mock_checks
            mock_crud.count_by_instance.return_value = 1
            
            crud = CRUDBase(Mock(spec=Session))
            checks, total = await crud.list_health_checks(
                filters={"instance_id": 123}
            )
            
            assert checks == mock_checks
            assert total == 1
            mock_crud.list_by_instance.assert_called_once_with(
                crud.session, 123, limit=20, offset=0
            )

    @pytest.mark.asyncio
    async def test_list_health_checks_no_instance_filter(self):
        """Test listing health checks without instance filter."""
        crud = CRUDBase(Mock(spec=Session))
        checks, total = await crud.list_health_checks()
        
        assert checks == []
        assert total == 0

    @pytest.mark.asyncio
    async def test_list_health_checks_with_pagination(self):
        """Test listing health checks with pagination."""
        mock_checks = [Mock(spec=HealthCheck)]
        
        with patch('cc_orchestrator.web.crud_adapter.HealthCheckCRUD') as mock_crud:
            mock_crud.list_by_instance.return_value = mock_checks
            mock_crud.count_by_instance.return_value = 1
            
            crud = CRUDBase(Mock(spec=Session))
            checks, total = await crud.list_health_checks(
                offset=10, limit=5, filters={"instance_id": 456}
            )
            
            assert checks == mock_checks
            assert total == 1
            mock_crud.list_by_instance.assert_called_once_with(
                crud.session, 456, limit=5, offset=10
            )

    @pytest.mark.asyncio
    async def test_create_health_check_with_string_status(self):
        """Test creating health check with string status."""
        mock_check = Mock(spec=HealthCheck)
        check_data = {
            "instance_id": 123,
            "overall_status": "healthy",
            "check_results": {"cpu": "ok", "memory": "ok"},
            "duration_ms": 250,
            "check_timestamp": datetime.now()
        }
        
        with patch('cc_orchestrator.web.crud_adapter.HealthCheckCRUD') as mock_crud:
            mock_crud.create.return_value = mock_check
            
            crud = CRUDBase(Mock(spec=Session))
            result = await crud.create_health_check(check_data)
            
            assert result is mock_check
            call_args = mock_crud.create.call_args
            assert call_args[1]["overall_status"] == HealthStatus.HEALTHY

    @pytest.mark.asyncio
    async def test_create_health_check_with_enum_status(self):
        """Test creating health check with enum status."""
        mock_check = Mock(spec=HealthCheck)
        check_data = {
            "instance_id": 456,
            "overall_status": HealthStatus.DEGRADED,
            "check_results": {"cpu": "warning"},
            "duration_ms": 500,
            "check_timestamp": datetime.now()
        }
        
        with patch('cc_orchestrator.web.crud_adapter.HealthCheckCRUD') as mock_crud:
            mock_crud.create.return_value = mock_check
            
            crud = CRUDBase(Mock(spec=Session))
            result = await crud.create_health_check(check_data)
            
            assert result is mock_check


class TestAlertOperations:
    """Test CRUDBase alert operations (placeholder functionality)."""

    @pytest.mark.asyncio
    async def test_list_alerts(self):
        """Test listing alerts returns empty list."""
        crud = CRUDBase(Mock(spec=Session))
        alerts, total = await crud.list_alerts()
        
        assert alerts == []
        assert total == 0

    @pytest.mark.asyncio
    async def test_list_alerts_with_filters(self):
        """Test listing alerts with filters still returns empty."""
        crud = CRUDBase(Mock(spec=Session))
        alerts, total = await crud.list_alerts(
            offset=5, limit=10, filters={"level": "error"}
        )
        
        assert alerts == []
        assert total == 0

    @pytest.mark.asyncio
    async def test_create_alert(self):
        """Test creating alert with placeholder implementation."""
        alert_data = {
            "instance_id": 123,
            "alert_id": "ALERT-456",
            "level": "error",
            "message": "System error occurred",
            "details": {"error_code": "E001"},
            "timestamp": datetime.now()
        }
        
        crud = CRUDBase(Mock(spec=Session))
        result = await crud.create_alert(alert_data)
        
        assert isinstance(result, Alert)
        assert result.instance_id == 123
        assert result.alert_id == "ALERT-456"
        assert result.level == "error"
        assert result.message == "System error occurred"
        assert result.details == {"error_code": "E001"}
        assert result.id == 1  # Simulated assigned ID

    @pytest.mark.asyncio
    async def test_create_alert_minimal(self):
        """Test creating alert with minimal data."""
        alert_data = {
            "instance_id": 999,
            "alert_id": "MIN-001",
            "level": "info",
            "message": "Info message",
            "timestamp": datetime.now()
        }
        
        crud = CRUDBase(Mock(spec=Session))
        result = await crud.create_alert(alert_data)
        
        assert isinstance(result, Alert)
        assert result.instance_id == 999
        assert result.alert_id == "MIN-001"
        assert hasattr(result, "details")

    @pytest.mark.asyncio
    async def test_get_alert_by_alert_id(self):
        """Test getting alert by alert ID returns None."""
        crud = CRUDBase(Mock(spec=Session))
        result = await crud.get_alert_by_alert_id("ALERT-123")
        
        assert result is None


class TestAsyncExecution:
    """Test async execution patterns and threading."""

    @pytest.mark.asyncio
    async def test_async_to_thread_execution(self):
        """Test that operations are properly executed in threads."""
        mock_session = Mock(spec=Session)
        
        # Mock the asyncio.to_thread to capture the function being called
        with patch('asyncio.to_thread') as mock_to_thread:
            mock_to_thread.return_value = Mock(spec=Instance)
            
            crud = CRUDBase(mock_session)
            await crud.get_instance(123)
            
            # Verify asyncio.to_thread was called
            mock_to_thread.assert_called_once()
            # The first argument should be a callable
            assert callable(mock_to_thread.call_args[0][0])

    @pytest.mark.asyncio
    async def test_multiple_concurrent_operations(self):
        """Test multiple concurrent async operations."""
        mock_session = Mock(spec=Session)
        crud = CRUDBase(mock_session)
        
        with patch('cc_orchestrator.web.crud_adapter.InstanceCRUD') as mock_instance_crud, \
             patch('cc_orchestrator.web.crud_adapter.TaskCRUD') as mock_task_crud:
            
            mock_instance_crud.get_by_id.return_value = Mock(spec=Instance)
            mock_task_crud.get_by_id.return_value = Mock(spec=Task)
            
            # Run multiple operations concurrently
            results = await asyncio.gather(
                crud.get_instance(123),
                crud.get_task(456),
                crud.get_instance(789)
            )
            
            assert len(results) == 3
            assert all(result is not None for result in results)

    @pytest.mark.asyncio
    async def test_exception_handling_in_async_context(self):
        """Test exception handling in async context."""
        with patch('cc_orchestrator.web.crud_adapter.InstanceCRUD') as mock_crud:
            mock_crud.get_by_id.side_effect = RuntimeError("Database error")
            
            crud = CRUDBase(Mock(spec=Session))
            result = await crud.get_instance(123)
            
            # Should handle exception and return None
            assert result is None


class TestEdgeCasesAndErrorHandling:
    """Test edge cases and error handling scenarios."""

    @pytest.mark.asyncio
    async def test_create_instance_with_empty_data(self):
        """Test creating instance with minimal required data."""
        with patch('cc_orchestrator.web.crud_adapter.InstanceCRUD') as mock_crud:
            mock_crud.create.return_value = Mock(spec=Instance)
            
            crud = CRUDBase(Mock(spec=Session))
            # Should handle missing optional fields gracefully
            result = await crud.create_instance({"issue_id": "REQUIRED-123"})
            
            assert result is not None

    @pytest.mark.asyncio
    async def test_list_tasks_empty_result(self):
        """Test listing tasks when no tasks exist."""
        with patch('cc_orchestrator.web.crud_adapter.TaskCRUD') as mock_crud:
            mock_crud.list_pending.return_value = []
            
            crud = CRUDBase(Mock(spec=Session))
            tasks, total = await crud.list_tasks()
            
            assert tasks == []
            assert total == 0

    @pytest.mark.asyncio
    async def test_create_task_with_default_priority(self):
        """Test creating task without explicit priority uses default."""
        mock_task = Mock(spec=Task)
        task_data = {"title": "Task without priority"}
        
        with patch('cc_orchestrator.web.crud_adapter.TaskCRUD') as mock_crud:
            mock_crud.create.return_value = mock_task
            
            crud = CRUDBase(Mock(spec=Session))
            result = await crud.create_task(task_data)
            
            assert result is mock_task
            call_args = mock_crud.create.call_args
            # Should use default priority (2 -> MEDIUM)
            assert call_args[1]["priority"] == TaskPriority.MEDIUM

    @pytest.mark.asyncio
    async def test_update_worktree_with_string_status_conversion(self):
        """Test worktree status string conversion handles all cases."""
        mock_worktree = Mock(spec=Worktree)
        mock_worktree.status = WorktreeStatus.ACTIVE
        
        test_cases = [
            ("active", WorktreeStatus.ACTIVE),
            ("inactive", WorktreeStatus.INACTIVE),
            ("synchronizing", WorktreeStatus.SYNCHRONIZING),
            ("error", WorktreeStatus.ERROR)
        ]
        
        with patch('cc_orchestrator.web.crud_adapter.WorktreeCRUD') as mock_crud:
            mock_crud.get_by_id.return_value = mock_worktree
            mock_crud.update_status.return_value = mock_worktree
            
            for status_str, expected_enum in test_cases:
                crud = CRUDBase(Mock(spec=Session))
                await crud.update_worktree(123, {"status": status_str})
                
                call_args = mock_crud.update_status.call_args
                assert call_args[0][2] == expected_enum

    @pytest.mark.asyncio
    async def test_configuration_scope_conversion_edge_cases(self):
        """Test configuration scope conversion handles all valid cases."""
        mock_config = Mock(spec=Configuration)
        
        test_cases = [
            ("GLOBAL", ConfigScope.GLOBAL),
            ("Global", ConfigScope.GLOBAL),
            ("USER", ConfigScope.USER),
            ("Project", ConfigScope.PROJECT),
            ("INSTANCE", ConfigScope.INSTANCE),
            ("invalid_scope", ConfigScope.GLOBAL)  # Should default
        ]
        
        with patch('cc_orchestrator.web.crud_adapter.ConfigurationCRUD') as mock_crud:
            mock_crud.create.return_value = mock_config
            
            for scope_str, expected_enum in test_cases:
                config_data = {
                    "key": f"test.{scope_str.lower()}",
                    "value": "test_value",
                    "scope": scope_str
                }
                
                crud = CRUDBase(Mock(spec=Session))
                await crud.create_configuration(config_data)
                
                call_args = mock_crud.create.call_args
                assert call_args[1]["scope"] == expected_enum

    @pytest.mark.asyncio
    async def test_task_priority_integer_mapping_complete(self):
        """Test complete task priority integer to enum mapping."""
        mock_task = Mock(spec=Task)
        
        priority_mappings = [
            (1, TaskPriority.LOW),
            (2, TaskPriority.MEDIUM),
            (3, TaskPriority.HIGH),
            (4, TaskPriority.URGENT)
        ]
        
        with patch('cc_orchestrator.web.crud_adapter.TaskCRUD') as mock_crud:
            mock_crud.create.return_value = mock_task
            
            for priority_int, expected_enum in priority_mappings:
                task_data = {
                    "title": f"Task with priority {priority_int}",
                    "priority": priority_int
                }
                
                crud = CRUDBase(Mock(spec=Session))
                await crud.create_task(task_data)
                
                call_args = mock_crud.create.call_args
                assert call_args[1]["priority"] == expected_enum


class TestIntegrationScenarios:
    """Test realistic integration scenarios combining multiple operations."""

    @pytest.mark.asyncio
    async def test_instance_creation_and_task_assignment_workflow(self):
        """Test creating instance and assigning tasks workflow."""
        mock_instance = Mock(spec=Instance)
        mock_instance.id = 123
        mock_task = Mock(spec=Task)
        
        with patch('cc_orchestrator.web.crud_adapter.InstanceCRUD') as mock_instance_crud, \
             patch('cc_orchestrator.web.crud_adapter.TaskCRUD') as mock_task_crud:
            
            mock_instance_crud.create.return_value = mock_instance
            mock_task_crud.create.return_value = mock_task
            
            crud = CRUDBase(Mock(spec=Session))
            
            # Create instance
            instance = await crud.create_instance({
                "issue_id": "ISSUE-123",
                "status": "active"
            })
            
            # Create task for the instance
            task = await crud.create_task({
                "title": "Setup worktree",
                "instance_id": instance.id,
                "priority": "high"
            })
            
            assert instance is mock_instance
            assert task is mock_task

    @pytest.mark.asyncio
    async def test_worktree_lifecycle_workflow(self):
        """Test complete worktree lifecycle workflow."""
        mock_worktree = Mock(spec=Worktree)
        mock_worktree.id = 456
        mock_worktree.status = WorktreeStatus.ACTIVE
        
        with patch('cc_orchestrator.web.crud_adapter.WorktreeCRUD') as mock_crud:
            mock_crud.create.return_value = mock_worktree
            mock_crud.get_by_id.return_value = mock_worktree
            mock_crud.update_status.return_value = mock_worktree
            
            crud = CRUDBase(Mock(spec=Session))
            
            # Create worktree
            worktree = await crud.create_worktree({
                "name": "test-worktree",
                "path": "/path/to/worktree",
                "branch_name": "feature/test"
            })
            
            # Update with git status
            updated_worktree = await crud.update_worktree(worktree.id, {
                "status": "synchronizing",
                "current_commit": "abc123",
                "has_uncommitted_changes": False
            })
            
            # Delete worktree
            await crud.delete_worktree(worktree.id)
            
            assert worktree is mock_worktree
            assert updated_worktree is mock_worktree

    @pytest.mark.asyncio
    async def test_configuration_hierarchy_access(self):
        """Test configuration hierarchy access patterns."""
        mock_global_config = Mock(spec=Configuration)
        mock_instance_config = Mock(spec=Configuration)
        
        with patch('cc_orchestrator.web.crud_adapter.ConfigurationCRUD') as mock_crud:
            mock_crud.create.return_value = mock_global_config
            mock_crud.get_by_key_scope.return_value = mock_instance_config
            mock_crud.get_exact_by_key_scope.return_value = mock_global_config
            
            crud = CRUDBase(Mock(spec=Session))
            
            # Create global configuration
            global_config = await crud.create_configuration({
                "key": "api.timeout",
                "value": "30",
                "scope": "global"
            })
            
            # Get hierarchical configuration (may resolve to instance-specific)
            resolved_config = await crud.get_configuration_by_key_scope(
                "api.timeout", "instance", instance_id=123
            )
            
            # Get exact configuration at global scope
            exact_config = await crud.get_exact_configuration_by_key_scope(
                "api.timeout", "global"
            )
            
            assert global_config is mock_global_config
            assert resolved_config is mock_instance_config
            assert exact_config is mock_global_config