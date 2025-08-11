"""Comprehensive tests for database CRUD operations to maximize coverage.

This test suite focuses on uncovered areas and edge cases to improve test coverage
from the current 27% (68/250 lines) to maximize coverage impact.
"""

import json
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, Mock, patch
from typing import Any

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from cc_orchestrator.database import (
    Base,
    ConfigScope,
    Configuration,
    Instance,
    InstanceStatus,
    Task,
    TaskPriority,
    TaskStatus,
    Worktree,
    WorktreeStatus,
)
from cc_orchestrator.database.crud import (
    ConfigurationCRUD,
    CRUDError,
    HealthCheckCRUD,
    InstanceCRUD,
    NotFoundError,
    TaskCRUD,
    ValidationError,
    WorktreeCRUD,
)
from cc_orchestrator.database.models import HealthCheck, HealthStatus


@pytest.fixture
def mock_session():
    """Create a mock SQLAlchemy session."""
    session = Mock(spec=Session)
    session.add = Mock()
    session.delete = Mock()
    session.flush = Mock()
    session.commit = Mock()
    session.rollback = Mock()
    session.query = Mock()
    session.get = Mock()
    return session


@pytest.fixture
def memory_engine():
    """Create an in-memory SQLite engine for testing."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def db_session(memory_engine):
    """Create a database session for testing."""
    with Session(memory_engine) as session:
        yield session


class TestInstanceCRUDAdvanced:
    """Advanced tests for Instance CRUD operations focusing on uncovered areas."""

    def test_create_with_integrity_error_handling(self, mock_session):
        """Test IntegrityError handling during instance creation."""
        mock_session.add.side_effect = IntegrityError(
            statement="INSERT", params={}, orig=Exception("UNIQUE constraint failed")
        )
        
        with pytest.raises(ValidationError, match="Instance with issue_id 'duplicate' already exists"):
            InstanceCRUD.create(session=mock_session, issue_id="duplicate")

    def test_create_with_whitespace_trimming(self, db_session):
        """Test that issue_id whitespace is properly trimmed."""
        instance = InstanceCRUD.create(
            session=db_session,
            issue_id="  test-123  ",
            workspace_path="  /path/to/workspace  ",
            branch_name="  feature/branch  ",
            tmux_session="  session-name  "
        )
        
        assert instance.issue_id == "test-123"
        # Note: Other fields don't get trimmed, only issue_id

    def test_create_with_none_extra_metadata(self, db_session):
        """Test creation with None extra_metadata gets converted to empty dict."""
        instance = InstanceCRUD.create(
            session=db_session,
            issue_id="test-none",
            extra_metadata=None
        )
        
        assert instance.extra_metadata == {}

    def test_list_all_no_offset_condition(self, db_session):
        """Test list_all with offset=0 to cover the offset condition."""
        # Create test instances
        for i in range(3):
            InstanceCRUD.create(session=db_session, issue_id=f"test-{i}")
        db_session.commit()
        
        # Test with offset=0 (should not apply offset)
        instances = InstanceCRUD.list_all(session=db_session, offset=0, limit=2)
        assert len(instances) == 2

    def test_list_all_with_no_limit(self, db_session):
        """Test list_all without limit to cover the limit condition."""
        for i in range(3):
            InstanceCRUD.create(session=db_session, issue_id=f"test-{i}")
        db_session.commit()
        
        instances = InstanceCRUD.list_all(session=db_session, limit=None)
        assert len(instances) == 3

    def test_update_with_unallowed_fields(self, db_session):
        """Test that unallowed fields are ignored during update."""
        instance = InstanceCRUD.create(session=db_session, issue_id="test-update")
        db_session.commit()
        
        updated = InstanceCRUD.update(
            session=db_session,
            instance_id=instance.id,
            status=InstanceStatus.RUNNING,
            unallowed_field="should_be_ignored",
            issue_id="should_be_ignored"  # Not in allowed_fields
        )
        
        assert updated.status == InstanceStatus.RUNNING
        assert updated.issue_id == "test-update"  # Should remain unchanged

    def test_update_with_datetime_override(self, db_session):
        """Test that updated_at is properly set during updates."""
        instance = InstanceCRUD.create(session=db_session, issue_id="test-datetime")
        db_session.commit()
        
        original_updated_at = instance.updated_at
        
        with patch('cc_orchestrator.database.crud.datetime') as mock_datetime:
            mock_now = datetime(2023, 1, 1, 12, 0, 0)
            mock_datetime.now.return_value = mock_now
            
            InstanceCRUD.update(
                session=db_session,
                instance_id=instance.id,
                status=InstanceStatus.RUNNING
            )
            
            assert instance.updated_at == mock_now


class TestTaskCRUDAdvanced:
    """Advanced tests for Task CRUD operations focusing on uncovered areas."""

    def test_create_with_none_requirements_and_metadata(self, db_session):
        """Test task creation with None requirements and metadata."""
        task = TaskCRUD.create(
            session=db_session,
            title="Test Task",
            requirements=None,
            extra_metadata=None
        )
        
        assert task.requirements == {}
        assert task.extra_metadata == {}

    def test_create_with_whitespace_trimming(self, db_session):
        """Test that task title whitespace is properly trimmed."""
        task = TaskCRUD.create(
            session=db_session,
            title="  Test Task Title  "
        )
        
        assert task.title == "Test Task Title"

    def test_list_by_instance_priority_ordering_edge_cases(self, db_session):
        """Test priority ordering with all priority levels."""
        instance = InstanceCRUD.create(session=db_session, issue_id="test-priority")
        db_session.commit()
        
        # Create tasks with all priority levels
        priorities = [TaskPriority.LOW, TaskPriority.URGENT, TaskPriority.MEDIUM, TaskPriority.HIGH]
        tasks = []
        for i, priority in enumerate(priorities):
            task = TaskCRUD.create(
                session=db_session,
                title=f"Task {i}",
                instance_id=instance.id,
                priority=priority
            )
            tasks.append(task)
        db_session.commit()
        
        ordered_tasks = TaskCRUD.list_by_instance(session=db_session, instance_id=instance.id)
        
        # Should be ordered: URGENT(4), HIGH(3), MEDIUM(2), LOW(1)
        expected_order = [TaskPriority.URGENT, TaskPriority.HIGH, TaskPriority.MEDIUM, TaskPriority.LOW]
        actual_order = [task.priority for task in ordered_tasks]
        assert actual_order == expected_order

    def test_list_pending_priority_ordering_edge_cases(self, db_session):
        """Test priority ordering in list_pending with all priority levels."""
        # Create tasks with all priority levels
        priorities = [TaskPriority.LOW, TaskPriority.URGENT, TaskPriority.MEDIUM, TaskPriority.HIGH]
        for i, priority in enumerate(priorities):
            TaskCRUD.create(
                session=db_session,
                title=f"Task {i}",
                priority=priority
            )
        db_session.commit()
        
        pending_tasks = TaskCRUD.list_pending(session=db_session)
        
        # Should be ordered: URGENT(4), HIGH(3), MEDIUM(2), LOW(1)
        expected_order = [TaskPriority.URGENT, TaskPriority.HIGH, TaskPriority.MEDIUM, TaskPriority.LOW]
        actual_order = [task.priority for task in pending_tasks]
        assert actual_order == expected_order

    def test_update_status_timezone_aware_handling(self, db_session):
        """Test timezone-aware datetime handling in update_status."""
        task = TaskCRUD.create(session=db_session, title="Test Task")
        db_session.commit()
        
        # Set started_at to timezone-aware datetime
        with patch('cc_orchestrator.database.crud.datetime') as mock_datetime:
            start_time = datetime(2023, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
            end_time = datetime(2023, 1, 1, 11, 30, 0, tzinfo=timezone.utc)
            
            # Start the task
            mock_datetime.now.return_value = start_time
            TaskCRUD.update_status(session=db_session, task_id=task.id, status=TaskStatus.IN_PROGRESS)
            
            # Complete the task
            mock_datetime.now.return_value = end_time
            updated_task = TaskCRUD.update_status(session=db_session, task_id=task.id, status=TaskStatus.COMPLETED)
            
            # Should calculate duration: 90 minutes
            assert updated_task.actual_duration == 90

    def test_update_status_timezone_naive_handling(self, db_session):
        """Test timezone-naive datetime handling in update_status."""
        task = TaskCRUD.create(session=db_session, title="Test Task")
        db_session.commit()
        
        # Manually set started_at to timezone-naive datetime
        naive_start = datetime(2023, 1, 1, 10, 0, 0)  # No timezone info
        task.started_at = naive_start
        db_session.commit()
        
        with patch('cc_orchestrator.database.crud.datetime') as mock_datetime:
            end_time = datetime(2023, 1, 1, 11, 30, 0, tzinfo=timezone.utc)
            mock_datetime.now.return_value = end_time
            
            updated_task = TaskCRUD.update_status(session=db_session, task_id=task.id, status=TaskStatus.COMPLETED)
            
            # Should handle timezone-naive started_at by assuming UTC
            assert updated_task.actual_duration == 90

    def test_update_status_already_started_task(self, db_session):
        """Test updating status of already started task doesn't change started_at."""
        task = TaskCRUD.create(session=db_session, title="Test Task")
        db_session.commit()
        
        # First update to IN_PROGRESS
        TaskCRUD.update_status(session=db_session, task_id=task.id, status=TaskStatus.IN_PROGRESS)
        original_started_at = task.started_at
        
        # Update to IN_PROGRESS again
        TaskCRUD.update_status(session=db_session, task_id=task.id, status=TaskStatus.IN_PROGRESS)
        
        # started_at should not change
        assert task.started_at == original_started_at

    def test_update_status_already_completed_task(self, db_session):
        """Test updating already completed task doesn't change completed_at."""
        task = TaskCRUD.create(session=db_session, title="Test Task")
        db_session.commit()
        
        # Start and complete the task
        TaskCRUD.update_status(session=db_session, task_id=task.id, status=TaskStatus.IN_PROGRESS)
        TaskCRUD.update_status(session=db_session, task_id=task.id, status=TaskStatus.COMPLETED)
        original_completed_at = task.completed_at
        
        # Complete again
        TaskCRUD.update_status(session=db_session, task_id=task.id, status=TaskStatus.COMPLETED)
        
        # completed_at should not change
        assert task.completed_at == original_completed_at

    def test_update_status_failed_and_cancelled_statuses(self, db_session):
        """Test that FAILED and CANCELLED statuses set completed_at."""
        task1 = TaskCRUD.create(session=db_session, title="Failed Task")
        task2 = TaskCRUD.create(session=db_session, title="Cancelled Task")
        db_session.commit()
        
        # Start both tasks
        TaskCRUD.update_status(session=db_session, task_id=task1.id, status=TaskStatus.IN_PROGRESS)
        TaskCRUD.update_status(session=db_session, task_id=task2.id, status=TaskStatus.IN_PROGRESS)
        
        # Set to FAILED and CANCELLED
        failed_task = TaskCRUD.update_status(session=db_session, task_id=task1.id, status=TaskStatus.FAILED)
        cancelled_task = TaskCRUD.update_status(session=db_session, task_id=task2.id, status=TaskStatus.CANCELLED)
        
        assert failed_task.completed_at is not None
        assert cancelled_task.completed_at is not None
        assert failed_task.actual_duration is not None
        assert cancelled_task.actual_duration is not None

    def test_update_with_unallowed_fields(self, db_session):
        """Test that unallowed fields are ignored during update."""
        task = TaskCRUD.create(session=db_session, title="Test Task")
        db_session.commit()
        
        updated = TaskCRUD.update(
            session=db_session,
            task_id=task.id,
            title="Updated Title",
            status=TaskStatus.IN_PROGRESS,  # Not in allowed_fields
            unallowed_field="ignored"
        )
        
        assert updated.title == "Updated Title"
        assert updated.status == TaskStatus.PENDING  # Should remain unchanged

    def test_update_with_datetime_import_coverage(self, db_session):
        """Test the datetime import in TaskCRUD.update method."""
        task = TaskCRUD.create(session=db_session, title="Test Task")
        db_session.commit()
        
        # This covers the datetime import line in the update method
        updated = TaskCRUD.update(
            session=db_session,
            task_id=task.id,
            description="Updated description"
        )
        
        assert updated.description == "Updated description"
        assert updated.updated_at is not None


class TestWorktreeCRUDAdvanced:
    """Advanced tests for Worktree CRUD operations focusing on uncovered areas."""

    def test_create_with_integrity_error(self, mock_session):
        """Test IntegrityError handling during worktree creation."""
        mock_session.add.side_effect = IntegrityError(
            statement="INSERT", params={}, orig=Exception("UNIQUE constraint failed")
        )
        
        with pytest.raises(ValidationError, match="Worktree with path '/duplicate' already exists"):
            WorktreeCRUD.create(
                session=mock_session,
                name="test",
                path="/duplicate",
                branch_name="main"
            )

    def test_create_with_whitespace_trimming(self, db_session):
        """Test that worktree fields are properly trimmed."""
        worktree = WorktreeCRUD.create(
            session=db_session,
            name="  test-worktree  ",
            path="  /path/to/worktree  ",
            branch_name="  feature/branch  "
        )
        
        assert worktree.name == "test-worktree"
        assert worktree.path == "/path/to/worktree"
        assert worktree.branch_name == "feature/branch"

    def test_create_with_none_metadata_and_config(self, db_session):
        """Test creation with None git_config and extra_metadata."""
        worktree = WorktreeCRUD.create(
            session=db_session,
            name="test",
            path="/test/path",
            branch_name="main",
            git_config=None,
            extra_metadata=None
        )
        
        assert worktree.git_config == {}
        assert worktree.extra_metadata == {}

    def test_list_all_ordering(self, db_session):
        """Test that list_all returns worktrees ordered by created_at."""
        # Create worktrees with slight time differences
        worktree1 = WorktreeCRUD.create(
            session=db_session,
            name="first",
            path="/first",
            branch_name="main"
        )
        worktree2 = WorktreeCRUD.create(
            session=db_session,
            name="second",
            path="/second",
            branch_name="main"
        )
        db_session.commit()
        
        all_worktrees = WorktreeCRUD.list_all(session=db_session)
        assert len(all_worktrees) == 2
        # Should be ordered by created_at (oldest first)
        assert all_worktrees[0].created_at <= all_worktrees[1].created_at

    def test_list_by_status(self, db_session):
        """Test listing worktrees by status."""
        active_wt = WorktreeCRUD.create(
            session=db_session,
            name="active",
            path="/active",
            branch_name="main"
        )
        inactive_wt = WorktreeCRUD.create(
            session=db_session,
            name="inactive",
            path="/inactive",
            branch_name="main"
        )
        
        # Update one to inactive status
        WorktreeCRUD.update_status(
            session=db_session,
            worktree_id=inactive_wt.id,
            status=WorktreeStatus.INACTIVE
        )
        db_session.commit()
        
        active_worktrees = WorktreeCRUD.list_by_status(session=db_session, status=WorktreeStatus.ACTIVE)
        inactive_worktrees = WorktreeCRUD.list_by_status(session=db_session, status=WorktreeStatus.INACTIVE)
        
        assert len(active_worktrees) == 1
        assert len(inactive_worktrees) == 1
        assert active_worktrees[0].id == active_wt.id
        assert inactive_worktrees[0].id == inactive_wt.id

    def test_update_status_with_optional_params(self, db_session):
        """Test update_status with optional current_commit and has_uncommitted_changes."""
        worktree = WorktreeCRUD.create(
            session=db_session,
            name="test",
            path="/test",
            branch_name="main"
        )
        db_session.commit()
        
        # Test with all parameters
        updated = WorktreeCRUD.update_status(
            session=db_session,
            worktree_id=worktree.id,
            status=WorktreeStatus.DIRTY,
            current_commit="abc123",
            has_uncommitted_changes=True
        )
        
        assert updated.status == WorktreeStatus.DIRTY
        assert updated.current_commit == "abc123"
        assert updated.has_uncommitted_changes is True
        assert updated.last_sync is not None

    def test_update_status_with_none_optional_params(self, db_session):
        """Test update_status with None optional parameters."""
        worktree = WorktreeCRUD.create(
            session=db_session,
            name="test",
            path="/test",
            branch_name="main"
        )
        db_session.commit()
        
        # Set initial values
        worktree.current_commit = "old_commit"
        worktree.has_uncommitted_changes = False
        db_session.commit()
        
        # Update with None values (should not change existing values)
        updated = WorktreeCRUD.update_status(
            session=db_session,
            worktree_id=worktree.id,
            status=WorktreeStatus.ERROR,
            current_commit=None,
            has_uncommitted_changes=None
        )
        
        assert updated.status == WorktreeStatus.ERROR
        assert updated.current_commit == "old_commit"  # Should remain unchanged
        assert updated.has_uncommitted_changes is False  # Should remain unchanged

    def test_update_status_datetime_import_coverage(self, db_session):
        """Test the datetime import in update_status method."""
        worktree = WorktreeCRUD.create(
            session=db_session,
            name="test",
            path="/test",
            branch_name="main"
        )
        db_session.commit()
        
        # This test covers the datetime import line in update_status method
        original_last_sync = worktree.last_sync
        
        updated = WorktreeCRUD.update_status(
            session=db_session,
            worktree_id=worktree.id,
            status=WorktreeStatus.ACTIVE
        )
        
        # Verify that last_sync was updated
        assert updated.last_sync is not None
        assert updated.last_sync != original_last_sync

    def test_get_by_id_not_found(self, db_session):
        """Test WorktreeCRUD.get_by_id with non-existent ID."""
        with pytest.raises(NotFoundError, match="Worktree with ID 999 not found"):
            WorktreeCRUD.get_by_id(session=db_session, worktree_id=999)

    def test_delete_worktree(self, db_session):
        """Test WorktreeCRUD.delete operation."""
        worktree = WorktreeCRUD.create(
            session=db_session,
            name="deletable",
            path="/deletable",
            branch_name="main"
        )
        db_session.commit()
        
        result = WorktreeCRUD.delete(session=db_session, worktree_id=worktree.id)
        assert result is True
        
        # Verify it's deleted
        with pytest.raises(NotFoundError):
            WorktreeCRUD.get_by_id(session=db_session, worktree_id=worktree.id)


class TestHealthCheckCRUD:
    """Tests for HealthCheck CRUD operations (currently has minimal coverage)."""

    def test_create_health_check(self, db_session):
        """Test creating a health check record."""
        instance = InstanceCRUD.create(session=db_session, issue_id="health-test")
        db_session.commit()
        
        check_timestamp = datetime.now(timezone.utc)
        health_check = HealthCheckCRUD.create(
            session=db_session,
            instance_id=instance.id,
            overall_status=HealthStatus.HEALTHY,
            check_results='{"status": "ok", "checks": []}',
            duration_ms=150.5,
            check_timestamp=check_timestamp
        )
        
        assert health_check.id is not None
        assert health_check.instance_id == instance.id
        assert health_check.overall_status == HealthStatus.HEALTHY
        assert health_check.check_results == '{"status": "ok", "checks": []}'
        assert health_check.duration_ms == 150.5
        assert health_check.check_timestamp == check_timestamp

    def test_list_by_instance(self, db_session):
        """Test listing health checks by instance."""
        instance = InstanceCRUD.create(session=db_session, issue_id="health-test")
        db_session.commit()
        
        # Create multiple health checks
        timestamps = [
            datetime.now(timezone.utc) - timedelta(hours=2),
            datetime.now(timezone.utc) - timedelta(hours=1),
            datetime.now(timezone.utc)
        ]
        
        for i, timestamp in enumerate(timestamps):
            HealthCheckCRUD.create(
                session=db_session,
                instance_id=instance.id,
                overall_status=HealthStatus.HEALTHY,
                check_results=f'{{"check": {i}}}',
                duration_ms=100.0 + i,
                check_timestamp=timestamp
            )
        db_session.commit()
        
        checks = HealthCheckCRUD.list_by_instance(session=db_session, instance_id=instance.id)
        assert len(checks) == 3
        
        # Should be ordered by check_timestamp desc (newest first)
        assert checks[0].check_timestamp >= checks[1].check_timestamp >= checks[2].check_timestamp

    def test_list_by_instance_with_pagination(self, db_session):
        """Test listing health checks with pagination."""
        instance = InstanceCRUD.create(session=db_session, issue_id="health-pagination")
        db_session.commit()
        
        # Create 5 health checks
        for i in range(5):
            HealthCheckCRUD.create(
                session=db_session,
                instance_id=instance.id,
                overall_status=HealthStatus.HEALTHY,
                check_results=f'{{"check": {i}}}',
                duration_ms=100.0,
                check_timestamp=datetime.now(timezone.utc)
            )
        db_session.commit()
        
        # Test limit
        checks = HealthCheckCRUD.list_by_instance(session=db_session, instance_id=instance.id, limit=2)
        assert len(checks) == 2
        
        # Test offset and limit
        checks_page2 = HealthCheckCRUD.list_by_instance(
            session=db_session, 
            instance_id=instance.id, 
            limit=2, 
            offset=2
        )
        assert len(checks_page2) == 2

    def test_list_by_instance_with_no_offset(self, db_session):
        """Test list_by_instance with offset=0 to cover the offset condition."""
        instance = InstanceCRUD.create(session=db_session, issue_id="health-no-offset")
        db_session.commit()
        
        HealthCheckCRUD.create(
            session=db_session,
            instance_id=instance.id,
            overall_status=HealthStatus.HEALTHY,
            check_results='{"test": true}',
            duration_ms=100.0,
            check_timestamp=datetime.now(timezone.utc)
        )
        db_session.commit()
        
        # Test with offset=0 (should not apply offset)
        checks = HealthCheckCRUD.list_by_instance(
            session=db_session, 
            instance_id=instance.id, 
            offset=0
        )
        assert len(checks) == 1

    def test_count_by_instance(self, db_session):
        """Test counting health checks for an instance."""
        instance1 = InstanceCRUD.create(session=db_session, issue_id="count-test-1")
        instance2 = InstanceCRUD.create(session=db_session, issue_id="count-test-2")
        db_session.commit()
        
        # Create checks for instance1
        for i in range(3):
            HealthCheckCRUD.create(
                session=db_session,
                instance_id=instance1.id,
                overall_status=HealthStatus.HEALTHY,
                check_results='{"test": true}',
                duration_ms=100.0,
                check_timestamp=datetime.now(timezone.utc)
            )
        
        # Create checks for instance2
        for i in range(2):
            HealthCheckCRUD.create(
                session=db_session,
                instance_id=instance2.id,
                overall_status=HealthStatus.DEGRADED,
                check_results='{"test": false}',
                duration_ms=200.0,
                check_timestamp=datetime.now(timezone.utc)
            )
        db_session.commit()
        
        count1 = HealthCheckCRUD.count_by_instance(session=db_session, instance_id=instance1.id)
        count2 = HealthCheckCRUD.count_by_instance(session=db_session, instance_id=instance2.id)
        
        assert count1 == 3
        assert count2 == 2


class TestConfigurationCRUDAdvanced:
    """Advanced tests for Configuration CRUD operations focusing on uncovered areas."""

    def test_create_with_whitespace_trimming(self, db_session):
        """Test that configuration key is properly trimmed."""
        config = ConfigurationCRUD.create(
            session=db_session,
            key="  test.key  ",
            value="test_value"
        )
        
        assert config.key == "test.key"

    def test_create_with_none_metadata(self, db_session):
        """Test creation with None extra_metadata."""
        config = ConfigurationCRUD.create(
            session=db_session,
            key="test.key",
            value="test_value",
            extra_metadata=None
        )
        
        assert config.extra_metadata == {}

    def test_get_value_scope_hierarchy_instance_without_instance_id(self, db_session):
        """Test get_value with INSTANCE scope but no instance_id."""
        ConfigurationCRUD.create(
            session=db_session,
            key="test.setting",
            value="global_value",
            scope=ConfigScope.GLOBAL
        )
        db_session.commit()
        
        # Request INSTANCE scope but don't provide instance_id
        value = ConfigurationCRUD.get_value(
            session=db_session,
            key="test.setting",
            scope=ConfigScope.INSTANCE,
            instance_id=None
        )
        
        # Should fall back to lower priority scopes and return global value
        assert value == "global_value"

    def test_get_value_scope_hierarchy_all_scopes(self, db_session):
        """Test complete scope hierarchy with all scope levels."""
        instance = InstanceCRUD.create(session=db_session, issue_id="config-test")
        db_session.commit()
        
        # Create configurations at all scopes
        ConfigurationCRUD.create(
            session=db_session,
            key="test.setting",
            value="global_value",
            scope=ConfigScope.GLOBAL
        )
        ConfigurationCRUD.create(
            session=db_session,
            key="test.setting",
            value="user_value",
            scope=ConfigScope.USER
        )
        ConfigurationCRUD.create(
            session=db_session,
            key="test.setting",
            value="project_value",
            scope=ConfigScope.PROJECT
        )
        ConfigurationCRUD.create(
            session=db_session,
            key="test.setting",
            value="instance_value",
            scope=ConfigScope.INSTANCE,
            instance_id=instance.id
        )
        db_session.commit()
        
        # Test PROJECT scope (should return project value)
        value = ConfigurationCRUD.get_value(
            session=db_session,
            key="test.setting",
            scope=ConfigScope.PROJECT
        )
        assert value == "project_value"

    def test_get_by_key_scope_hierarchy_coverage(self, db_session):
        """Test get_by_key_scope with complete hierarchy coverage."""
        instance = InstanceCRUD.create(session=db_session, issue_id="scope-test")
        db_session.commit()
        
        # Create configurations at all scopes
        global_config = ConfigurationCRUD.create(
            session=db_session,
            key="test.setting",
            value="global_value",
            scope=ConfigScope.GLOBAL
        )
        user_config = ConfigurationCRUD.create(
            session=db_session,
            key="test.setting",
            value="user_value",
            scope=ConfigScope.USER
        )
        project_config = ConfigurationCRUD.create(
            session=db_session,
            key="test.setting",
            value="project_value",
            scope=ConfigScope.PROJECT
        )
        instance_config = ConfigurationCRUD.create(
            session=db_session,
            key="test.setting",
            value="instance_value",
            scope=ConfigScope.INSTANCE,
            instance_id=instance.id
        )
        db_session.commit()
        
        # Test each scope returns the right config object
        config = ConfigurationCRUD.get_by_key_scope(
            session=db_session,
            key="test.setting",
            scope=ConfigScope.GLOBAL
        )
        assert config.id == global_config.id
        
        config = ConfigurationCRUD.get_by_key_scope(
            session=db_session,
            key="test.setting",
            scope=ConfigScope.USER
        )
        assert config.id == user_config.id
        
        config = ConfigurationCRUD.get_by_key_scope(
            session=db_session,
            key="test.setting",
            scope=ConfigScope.PROJECT
        )
        assert config.id == project_config.id
        
        config = ConfigurationCRUD.get_by_key_scope(
            session=db_session,
            key="test.setting",
            scope=ConfigScope.INSTANCE,
            instance_id=instance.id
        )
        assert config.id == instance_config.id

    def test_get_exact_by_key_scope_instance_with_instance_id(self, db_session):
        """Test get_exact_by_key_scope for INSTANCE scope with instance_id."""
        instance = InstanceCRUD.create(session=db_session, issue_id="exact-test")
        db_session.commit()
        
        config = ConfigurationCRUD.create(
            session=db_session,
            key="instance.setting",
            value="instance_value",
            scope=ConfigScope.INSTANCE,
            instance_id=instance.id
        )
        db_session.commit()
        
        found_config = ConfigurationCRUD.get_exact_by_key_scope(
            session=db_session,
            key="instance.setting",
            scope=ConfigScope.INSTANCE,
            instance_id=instance.id
        )
        
        assert found_config is not None
        assert found_config.id == config.id
        assert found_config.value == "instance_value"

    def test_get_exact_by_key_scope_non_instance_scope(self, db_session):
        """Test get_exact_by_key_scope for non-INSTANCE scopes."""
        config = ConfigurationCRUD.create(
            session=db_session,
            key="global.setting",
            value="global_value",
            scope=ConfigScope.GLOBAL
        )
        db_session.commit()
        
        found_config = ConfigurationCRUD.get_exact_by_key_scope(
            session=db_session,
            key="global.setting",
            scope=ConfigScope.GLOBAL
        )
        
        assert found_config is not None
        assert found_config.id == config.id

    def test_get_exact_by_key_scope_not_found(self, db_session):
        """Test get_exact_by_key_scope when configuration is not found."""
        result = ConfigurationCRUD.get_exact_by_key_scope(
            session=db_session,
            key="nonexistent.key",
            scope=ConfigScope.GLOBAL
        )
        
        assert result is None

    def test_get_by_key_scope_not_found(self, db_session):
        """Test get_by_key_scope when no configuration exists."""
        result = ConfigurationCRUD.get_by_key_scope(
            session=db_session,
            key="nonexistent.key",
            scope=ConfigScope.GLOBAL
        )
        
        assert result is None


class TestTransactionHandlingAndEdgeCases:
    """Tests for transaction handling, error scenarios, and edge cases."""

    def test_session_rollback_on_integrity_error(self, mock_session):
        """Test that session operations handle IntegrityErrors properly."""
        # Setup mock to raise IntegrityError on flush
        mock_session.flush.side_effect = IntegrityError(
            statement="INSERT", params={}, orig=Exception("Constraint violation")
        )
        
        with pytest.raises(ValidationError):
            InstanceCRUD.create(session=mock_session, issue_id="test")
        
        # Verify session operations were called
        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()

    def test_task_status_update_without_started_at(self, db_session):
        """Test task completion without started_at (no duration calculation)."""
        task = TaskCRUD.create(session=db_session, title="No Start Task")
        db_session.commit()
        
        # Complete task without starting it
        updated = TaskCRUD.update_status(
            session=db_session,
            task_id=task.id,
            status=TaskStatus.COMPLETED
        )
        
        assert updated.status == TaskStatus.COMPLETED
        assert updated.completed_at is not None
        assert updated.actual_duration is None  # No duration since no start time

    def test_complex_json_metadata_handling(self, db_session):
        """Test handling of complex JSON metadata structures."""
        complex_metadata = {
            "nested": {
                "array": [1, 2, 3],
                "object": {"key": "value"},
                "null_value": None,
                "boolean": True
            },
            "unicode": "测试数据",
            "special_chars": "!@#$%^&*()"
        }
        
        instance = InstanceCRUD.create(
            session=db_session,
            issue_id="json-test",
            extra_metadata=complex_metadata
        )
        db_session.commit()
        
        retrieved = InstanceCRUD.get_by_id(session=db_session, instance_id=instance.id)
        assert retrieved.extra_metadata == complex_metadata

    def test_empty_string_vs_none_handling(self, db_session):
        """Test handling of empty strings vs None values."""
        # Test with empty strings
        instance = InstanceCRUD.create(
            session=db_session,
            issue_id="empty-test",
            workspace_path="",
            branch_name="",
            tmux_session=""
        )
        
        assert instance.workspace_path == ""
        assert instance.branch_name == ""
        assert instance.tmux_session == ""

    def test_large_text_field_handling(self, db_session):
        """Test handling of large text fields."""
        large_description = "A" * 10000  # 10KB description
        large_results = {"data": "B" * 5000}  # 5KB in results
        
        task = TaskCRUD.create(
            session=db_session,
            title="Large Text Task",
            description=large_description,
            requirements=large_results
        )
        db_session.commit()
        
        retrieved = TaskCRUD.get_by_id(session=db_session, task_id=task.id)
        assert retrieved.description == large_description
        assert retrieved.requirements == large_results


class TestBulkOperationsAndBatchProcessing:
    """Tests for bulk operations and batch processing scenarios."""

    def test_bulk_instance_creation(self, db_session):
        """Test creating multiple instances in a batch."""
        instances = []
        for i in range(10):
            instance = InstanceCRUD.create(
                session=db_session,
                issue_id=f"bulk-{i:03d}",
                extra_metadata={"batch": i}
            )
            instances.append(instance)
        
        # Commit all at once
        db_session.commit()
        
        # Verify all were created
        all_instances = InstanceCRUD.list_all(session=db_session)
        assert len(all_instances) == 10

    def test_bulk_task_status_updates(self, db_session):
        """Test updating multiple task statuses."""
        instance = InstanceCRUD.create(session=db_session, issue_id="bulk-tasks")
        db_session.commit()
        
        # Create multiple tasks
        tasks = []
        for i in range(5):
            task = TaskCRUD.create(
                session=db_session,
                title=f"Bulk Task {i}",
                instance_id=instance.id
            )
            tasks.append(task)
        db_session.commit()
        
        # Update all to in_progress
        for task in tasks:
            TaskCRUD.update_status(
                session=db_session,
                task_id=task.id,
                status=TaskStatus.IN_PROGRESS
            )
        db_session.commit()
        
        # Verify all updates
        updated_tasks = TaskCRUD.list_by_instance(
            session=db_session,
            instance_id=instance.id,
            status=TaskStatus.IN_PROGRESS
        )
        assert len(updated_tasks) == 5

    def test_cascading_deletes_with_relationships(self, db_session):
        """Test cascading behavior when deleting instances with related data."""
        # Enable foreign key constraints in SQLite for this test
        db_session.execute(text("PRAGMA foreign_keys = ON"))
        
        instance = InstanceCRUD.create(session=db_session, issue_id="cascade-test")
        db_session.commit()
        
        # Create related tasks
        task1 = TaskCRUD.create(
            session=db_session,
            title="Related Task 1",
            instance_id=instance.id
        )
        task2 = TaskCRUD.create(
            session=db_session,
            title="Related Task 2",
            instance_id=instance.id
        )
        db_session.commit()
        
        # Delete the instance
        InstanceCRUD.delete(session=db_session, instance_id=instance.id)
        db_session.commit()
        
        # Verify tasks still exist but with null instance_id (due to SET NULL)
        retrieved_task1 = TaskCRUD.get_by_id(session=db_session, task_id=task1.id)
        retrieved_task2 = TaskCRUD.get_by_id(session=db_session, task_id=task2.id)
        
        assert retrieved_task1.instance_id is None
        assert retrieved_task2.instance_id is None


class TestExceptionHandlingAndErrorPaths:
    """Tests for exception handling and error paths."""

    def test_sqlalchemy_error_handling(self, mock_session):
        """Test handling of general SQLAlchemy errors."""
        mock_session.flush.side_effect = SQLAlchemyError("Database connection lost")
        
        with pytest.raises(SQLAlchemyError):
            InstanceCRUD.create(session=mock_session, issue_id="error-test")

    def test_task_priority_edge_values(self, db_session):
        """Test task priority handling with edge values."""
        # Test with all priority enum values
        for priority in TaskPriority:
            task = TaskCRUD.create(
                session=db_session,
                title=f"Priority {priority.name} Task",
                priority=priority
            )
            assert task.priority == priority

    def test_configuration_scope_edge_cases(self, db_session):
        """Test configuration scope handling with edge cases."""
        instance = InstanceCRUD.create(session=db_session, issue_id="scope-edge")
        db_session.commit()
        
        # Test all scope enum values
        for scope in ConfigScope:
            config = ConfigurationCRUD.create(
                session=db_session,
                key=f"{scope.value}.setting",
                value=f"{scope.value}_value",
                scope=scope,
                instance_id=instance.id if scope == ConfigScope.INSTANCE else None
            )
            assert config.scope == scope

    def test_health_status_all_values(self, db_session):
        """Test health check creation with all health status values."""
        instance = InstanceCRUD.create(session=db_session, issue_id="health-all")
        db_session.commit()
        
        for status in HealthStatus:
            health_check = HealthCheckCRUD.create(
                session=db_session,
                instance_id=instance.id,
                overall_status=status,
                check_results=f'{{"status": "{status.value}"}}',
                duration_ms=100.0,
                check_timestamp=datetime.now(timezone.utc)
            )
            assert health_check.overall_status == status

    def test_worktree_status_all_values(self, db_session):
        """Test worktree creation and updates with all status values."""
        for i, status in enumerate(WorktreeStatus):
            worktree = WorktreeCRUD.create(
                session=db_session,
                name=f"test-{status.value}",
                path=f"/test/{status.value}",
                branch_name=f"{status.value}-branch"
            )
            
            # Update to the status
            WorktreeCRUD.update_status(
                session=db_session,
                worktree_id=worktree.id,
                status=status
            )
            
            assert worktree.status == status