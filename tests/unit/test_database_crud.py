"""Unit tests for database CRUD operations."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from cc_orchestrator.database import (
    Base,
    ConfigScope,
    InstanceStatus,
    TaskPriority,
    TaskStatus,
    WorktreeStatus,
)
from cc_orchestrator.database.crud import (
    ConfigurationCRUD,
    HealthCheckCRUD,
    InstanceCRUD,
    NotFoundError,
    TaskCRUD,
    ValidationError,
    WorktreeCRUD,
)
from cc_orchestrator.database.models import HealthStatus, Worktree


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


class TestInstanceCRUD:
    """Test Instance CRUD operations."""

    def test_create_instance(self, db_session):
        """Test creating an instance."""
        instance = InstanceCRUD.create(
            session=db_session,
            issue_id="123",
            workspace_path="/tmp/workspace",
            branch_name="feature/test",
            tmux_session="test-session",
            extra_metadata={"test": "data"},
        )

        assert instance.id is not None
        assert instance.issue_id == "123"
        assert instance.workspace_path == "/tmp/workspace"
        assert instance.branch_name == "feature/test"
        assert instance.tmux_session == "test-session"
        assert instance.extra_metadata == {"test": "data"}
        assert instance.status == InstanceStatus.INITIALIZING

    def test_create_instance_validation(self, db_session):
        """Test instance creation validation."""
        # Empty issue_id should raise ValidationError
        with pytest.raises(ValidationError, match="Issue ID is required"):
            InstanceCRUD.create(session=db_session, issue_id="")

        # Whitespace-only issue_id should raise ValidationError
        with pytest.raises(ValidationError, match="Issue ID is required"):
            InstanceCRUD.create(session=db_session, issue_id="   ")

    def test_create_duplicate_issue_id(self, db_session):
        """Test creating instances with duplicate issue_id."""
        InstanceCRUD.create(session=db_session, issue_id="123")
        db_session.commit()

        with pytest.raises(ValidationError, match="already exists"):
            InstanceCRUD.create(session=db_session, issue_id="123")

    def test_get_by_id(self, db_session):
        """Test getting instance by ID."""
        instance = InstanceCRUD.create(session=db_session, issue_id="123")
        db_session.commit()

        retrieved = InstanceCRUD.get_by_id(session=db_session, instance_id=instance.id)
        assert retrieved.id == instance.id
        assert retrieved.issue_id == "123"

    def test_get_by_id_not_found(self, db_session):
        """Test getting non-existent instance by ID."""
        with pytest.raises(NotFoundError, match="Instance with ID 999 not found"):
            InstanceCRUD.get_by_id(session=db_session, instance_id=999)

    def test_get_by_issue_id(self, db_session):
        """Test getting instance by issue_id."""
        instance = InstanceCRUD.create(session=db_session, issue_id="123")
        db_session.commit()

        retrieved = InstanceCRUD.get_by_issue_id(session=db_session, issue_id="123")
        assert retrieved.id == instance.id
        assert retrieved.issue_id == "123"

    def test_get_by_issue_id_not_found(self, db_session):
        """Test getting non-existent instance by issue_id."""
        with pytest.raises(
            NotFoundError, match="Instance with issue_id 'nonexistent' not found"
        ):
            InstanceCRUD.get_by_issue_id(session=db_session, issue_id="nonexistent")

    def test_list_all(self, db_session):
        """Test listing all instances."""
        InstanceCRUD.create(session=db_session, issue_id="123")
        InstanceCRUD.create(session=db_session, issue_id="456")
        db_session.commit()

        instances = InstanceCRUD.list_all(session=db_session)
        assert len(instances) == 2

        # Should be ordered by created_at desc (newest first)
        assert instances[0].created_at >= instances[1].created_at

    def test_list_all_with_status_filter(self, db_session):
        """Test listing instances with status filter."""
        instance1 = InstanceCRUD.create(session=db_session, issue_id="123")
        instance2 = InstanceCRUD.create(session=db_session, issue_id="456")

        # Update one instance status
        InstanceCRUD.update(
            session=db_session, instance_id=instance1.id, status=InstanceStatus.RUNNING
        )
        db_session.commit()

        running_instances = InstanceCRUD.list_all(
            session=db_session, status=InstanceStatus.RUNNING
        )
        assert len(running_instances) == 1
        assert running_instances[0].id == instance1.id

        initializing_instances = InstanceCRUD.list_all(
            session=db_session, status=InstanceStatus.INITIALIZING
        )
        assert len(initializing_instances) == 1
        assert initializing_instances[0].id == instance2.id

    def test_list_all_with_pagination(self, db_session):
        """Test listing instances with pagination."""
        for i in range(5):
            InstanceCRUD.create(session=db_session, issue_id=str(i))
        db_session.commit()

        # Test limit
        instances = InstanceCRUD.list_all(session=db_session, limit=2)
        assert len(instances) == 2

        # Test offset
        instances_page2 = InstanceCRUD.list_all(session=db_session, limit=2, offset=2)
        assert len(instances_page2) == 2

        # Ensure different instances
        page1_ids = {inst.id for inst in instances}
        page2_ids = {inst.id for inst in instances_page2}
        assert page1_ids.isdisjoint(page2_ids)

    def test_update_instance(self, db_session):
        """Test updating an instance."""
        instance = InstanceCRUD.create(session=db_session, issue_id="123")
        db_session.commit()

        original_updated_at = instance.updated_at

        updated = InstanceCRUD.update(
            session=db_session,
            instance_id=instance.id,
            status=InstanceStatus.RUNNING,
            process_id=12345,
            extra_metadata={"updated": True},
        )
        db_session.commit()

        assert updated.id == instance.id
        assert updated.status == InstanceStatus.RUNNING
        assert updated.process_id == 12345
        assert updated.extra_metadata == {"updated": True}
        assert updated.updated_at > original_updated_at

    def test_update_instance_not_found(self, db_session):
        """Test updating non-existent instance."""
        with pytest.raises(NotFoundError):
            InstanceCRUD.update(
                session=db_session, instance_id=999, status=InstanceStatus.RUNNING
            )

    def test_delete_instance(self, db_session):
        """Test deleting an instance."""
        instance = InstanceCRUD.create(session=db_session, issue_id="123")
        db_session.commit()

        result = InstanceCRUD.delete(session=db_session, instance_id=instance.id)
        db_session.commit()

        assert result is True

        with pytest.raises(NotFoundError):
            InstanceCRUD.get_by_id(session=db_session, instance_id=instance.id)


class TestTaskCRUD:
    """Test Task CRUD operations."""

    def test_create_task(self, db_session):
        """Test creating a task."""
        task = TaskCRUD.create(
            session=db_session,
            title="Test Task",
            description="A test task",
            priority=TaskPriority.HIGH,
            estimated_duration=60,
            requirements={"lang": "python"},
            extra_metadata={"category": "testing"},
        )

        assert task.id is not None
        assert task.title == "Test Task"
        assert task.description == "A test task"
        assert task.status == TaskStatus.PENDING
        assert task.priority == TaskPriority.HIGH
        assert task.estimated_duration == 60
        assert task.requirements == {"lang": "python"}
        assert task.extra_metadata == {"category": "testing"}

    def test_create_task_validation(self, db_session):
        """Test task creation validation."""
        with pytest.raises(ValidationError, match="Task title is required"):
            TaskCRUD.create(session=db_session, title="")

        with pytest.raises(ValidationError, match="Task title is required"):
            TaskCRUD.create(session=db_session, title="   ")

    def test_get_by_id(self, db_session):
        """Test getting task by ID."""
        task = TaskCRUD.create(session=db_session, title="Test Task")
        db_session.commit()

        retrieved = TaskCRUD.get_by_id(session=db_session, task_id=task.id)
        assert retrieved.id == task.id
        assert retrieved.title == "Test Task"

    def test_get_by_id_not_found(self, db_session):
        """Test getting non-existent task by ID."""
        with pytest.raises(NotFoundError, match="Task with ID 999 not found"):
            TaskCRUD.get_by_id(session=db_session, task_id=999)

    def test_list_by_instance(self, db_session):
        """Test listing tasks by instance."""
        instance = InstanceCRUD.create(session=db_session, issue_id="123")
        db_session.commit()

        TaskCRUD.create(
            session=db_session,
            title="Task 1",
            instance_id=instance.id,
            priority=TaskPriority.HIGH,
        )
        TaskCRUD.create(
            session=db_session,
            title="Task 2",
            instance_id=instance.id,
            priority=TaskPriority.LOW,
        )
        TaskCRUD.create(session=db_session, title="Task 3")  # Different instance
        db_session.commit()

        tasks = TaskCRUD.list_by_instance(session=db_session, instance_id=instance.id)
        assert len(tasks) == 2

        # Should be ordered by priority desc, created_at asc
        assert tasks[0].priority == TaskPriority.HIGH
        assert tasks[1].priority == TaskPriority.LOW

    def test_list_by_instance_with_status_filter(self, db_session):
        """Test listing tasks by instance with status filter."""
        instance = InstanceCRUD.create(session=db_session, issue_id="123")
        db_session.commit()

        task1 = TaskCRUD.create(
            session=db_session, title="Task 1", instance_id=instance.id
        )
        task2 = TaskCRUD.create(
            session=db_session, title="Task 2", instance_id=instance.id
        )

        # Update one task status
        TaskCRUD.update_status(
            session=db_session, task_id=task1.id, status=TaskStatus.IN_PROGRESS
        )
        db_session.commit()

        pending_tasks = TaskCRUD.list_by_instance(
            session=db_session, instance_id=instance.id, status=TaskStatus.PENDING
        )
        assert len(pending_tasks) == 1
        assert pending_tasks[0].id == task2.id

        in_progress_tasks = TaskCRUD.list_by_instance(
            session=db_session, instance_id=instance.id, status=TaskStatus.IN_PROGRESS
        )
        assert len(in_progress_tasks) == 1
        assert in_progress_tasks[0].id == task1.id

    def test_list_pending(self, db_session):
        """Test listing pending tasks across all instances."""
        instance1 = InstanceCRUD.create(session=db_session, issue_id="123")
        instance2 = InstanceCRUD.create(session=db_session, issue_id="456")
        db_session.commit()

        TaskCRUD.create(
            session=db_session,
            title="Task 1",
            instance_id=instance1.id,
            priority=TaskPriority.HIGH,
        )
        task2 = TaskCRUD.create(
            session=db_session,
            title="Task 2",
            instance_id=instance2.id,
            priority=TaskPriority.MEDIUM,
        )
        TaskCRUD.create(
            session=db_session,
            title="Task 3",
            instance_id=instance1.id,
            priority=TaskPriority.LOW,
        )

        # Update one task to non-pending status
        TaskCRUD.update_status(
            session=db_session, task_id=task2.id, status=TaskStatus.COMPLETED
        )
        db_session.commit()

        pending_tasks = TaskCRUD.list_pending(session=db_session)
        assert len(pending_tasks) == 2

        # Should be ordered by priority desc, created_at asc
        assert pending_tasks[0].priority == TaskPriority.HIGH
        assert pending_tasks[1].priority == TaskPriority.LOW

    def test_list_pending_with_limit(self, db_session):
        """Test listing pending tasks with limit."""
        for i in range(5):
            TaskCRUD.create(session=db_session, title=f"Task {i}")
        db_session.commit()

        pending_tasks = TaskCRUD.list_pending(session=db_session, limit=2)
        assert len(pending_tasks) == 2

    def test_update_status(self, db_session):
        """Test updating task status."""
        task = TaskCRUD.create(session=db_session, title="Test Task")
        db_session.commit()

        # Update to in_progress
        updated = TaskCRUD.update_status(
            session=db_session, task_id=task.id, status=TaskStatus.IN_PROGRESS
        )
        db_session.commit()

        assert updated.status == TaskStatus.IN_PROGRESS
        assert updated.started_at is not None

        # Update to completed
        updated = TaskCRUD.update_status(
            session=db_session, task_id=task.id, status=TaskStatus.COMPLETED
        )
        db_session.commit()

        assert updated.status == TaskStatus.COMPLETED
        assert updated.completed_at is not None
        assert updated.actual_duration is not None


class TestWorktreeCRUD:
    """Test Worktree CRUD operations."""

    def test_create_worktree(self, db_session):
        """Test creating a worktree."""
        worktree = WorktreeCRUD.create(
            session=db_session,
            name="test-worktree",
            path="/tmp/test-worktree",
            branch_name="feature/test",
            repository_url="https://github.com/test/repo.git",
            git_config={"remote.origin.url": "https://github.com/test/repo.git"},
            extra_metadata={"purpose": "testing"},
        )

        assert worktree.id is not None
        assert worktree.name == "test-worktree"
        assert worktree.path == "/tmp/test-worktree"
        assert worktree.branch_name == "feature/test"
        assert worktree.repository_url == "https://github.com/test/repo.git"
        assert worktree.git_config == {
            "remote.origin.url": "https://github.com/test/repo.git"
        }
        assert worktree.extra_metadata == {"purpose": "testing"}
        assert worktree.status == WorktreeStatus.ACTIVE

    def test_create_worktree_validation(self, db_session):
        """Test worktree creation validation."""
        with pytest.raises(ValidationError, match="Worktree name is required"):
            WorktreeCRUD.create(
                session=db_session, name="", path="/tmp/test", branch_name="main"
            )

        with pytest.raises(ValidationError, match="Worktree path is required"):
            WorktreeCRUD.create(
                session=db_session, name="test", path="", branch_name="main"
            )

        with pytest.raises(ValidationError, match="Branch name is required"):
            WorktreeCRUD.create(
                session=db_session, name="test", path="/tmp/test", branch_name=""
            )

    def test_get_worktree_not_found(self, db_session):
        """Test getting worktree that doesn't exist raises NotFoundError."""
        with pytest.raises(NotFoundError, match="Worktree with ID 999 not found"):
            WorktreeCRUD.get_by_id(session=db_session, worktree_id=999)

    def test_list_worktrees_by_status(self, db_session):
        """Test listing worktrees filtered by status."""
        # Create worktrees with different statuses
        w1 = WorktreeCRUD.create(
            session=db_session, name="active", path="/tmp/active", branch_name="main"
        )
        w1.status = WorktreeStatus.ACTIVE

        w2 = WorktreeCRUD.create(
            session=db_session,
            name="inactive",
            path="/tmp/inactive",
            branch_name="main",
        )
        w2.status = WorktreeStatus.INACTIVE
        db_session.commit()

        # Test filtering by status
        active_worktrees = WorktreeCRUD.list_by_status(
            session=db_session, status=WorktreeStatus.ACTIVE
        )
        assert len(active_worktrees) == 1
        assert active_worktrees[0].name == "active"

    def test_create_duplicate_path(self, db_session):
        """Test creating worktrees with duplicate paths."""
        WorktreeCRUD.create(
            session=db_session, name="test1", path="/tmp/test", branch_name="main"
        )
        db_session.commit()

        with pytest.raises(ValidationError, match="already exists"):
            WorktreeCRUD.create(
                session=db_session,
                name="test2",
                path="/tmp/test",
                branch_name="feature",
            )

    def test_get_by_path(self, db_session):
        """Test getting worktree by path."""
        worktree = WorktreeCRUD.create(
            session=db_session,
            name="test-worktree",
            path="/tmp/test-worktree",
            branch_name="main",
        )
        db_session.commit()

        retrieved = WorktreeCRUD.get_by_path(
            session=db_session, path="/tmp/test-worktree"
        )
        assert retrieved.id == worktree.id
        assert retrieved.name == "test-worktree"

    def test_get_by_path_not_found(self, db_session):
        """Test getting non-existent worktree by path."""
        with pytest.raises(
            NotFoundError, match="Worktree with path '/nonexistent' not found"
        ):
            WorktreeCRUD.get_by_path(session=db_session, path="/nonexistent")

    def test_worktree_delete(self, db_session):
        """Test WorktreeCRUD.delete method (lines 621-624)."""
        # Create an instance first
        InstanceCRUD.create(
            session=db_session,
            issue_id="test-123",
            workspace_path="/tmp/test-workspace",
            branch_name="feature/delete-test",
            tmux_session="test-session",
        )

        # Create a worktree
        worktree = WorktreeCRUD.create(
            session=db_session,
            name="test-worktree",
            path="/tmp/test-worktree",
            branch_name="feature-branch",
            repository_url="https://github.com/test/repo.git",
            git_config={"remote.origin.url": "https://github.com/test/repo.git"},
            extra_metadata={"purpose": "testing"},
        )
        worktree_id = worktree.id

        # Delete the worktree (this covers lines 621-624)
        result = WorktreeCRUD.delete(session=db_session, worktree_id=worktree_id)

        # Should return True
        assert result is True

        # Worktree should be deleted
        db_session.commit()
        deleted_worktree = (
            db_session.query(Worktree).filter(Worktree.id == worktree_id).first()
        )
        assert deleted_worktree is None


class TestConfigurationCRUD:
    """Test Configuration CRUD operations."""

    def test_create_configuration(self, db_session):
        """Test creating a configuration."""
        config = ConfigurationCRUD.create(
            session=db_session,
            key="test.setting",
            value="test_value",
            scope=ConfigScope.GLOBAL,
            description="A test configuration",
            is_secret=False,
            extra_metadata={"source": "test"},
        )

        assert config.id is not None
        assert config.key == "test.setting"
        assert config.value == "test_value"
        assert config.scope == ConfigScope.GLOBAL
        assert config.description == "A test configuration"
        assert config.is_secret is False
        assert config.extra_metadata == {"source": "test"}

    def test_create_configuration_validation(self, db_session):
        """Test configuration creation validation."""
        with pytest.raises(ValidationError, match="Configuration key is required"):
            ConfigurationCRUD.create(session=db_session, key="", value="test")

        with pytest.raises(ValidationError, match="Configuration key is required"):
            ConfigurationCRUD.create(session=db_session, key="   ", value="test")

    def test_get_value_global(self, db_session):
        """Test getting global configuration value."""
        ConfigurationCRUD.create(
            session=db_session,
            key="test.setting",
            value="global_value",
            scope=ConfigScope.GLOBAL,
        )
        db_session.commit()

        value = ConfigurationCRUD.get_value(session=db_session, key="test.setting")
        assert value == "global_value"

    def test_get_value_hierarchy(self, db_session):
        """Test configuration value hierarchy (instance > project > user > global)."""
        instance = InstanceCRUD.create(session=db_session, issue_id="123")
        db_session.commit()

        # Create configs at different scopes
        ConfigurationCRUD.create(
            session=db_session,
            key="test.setting",
            value="global_value",
            scope=ConfigScope.GLOBAL,
        )
        ConfigurationCRUD.create(
            session=db_session,
            key="test.setting",
            value="user_value",
            scope=ConfigScope.USER,
        )
        ConfigurationCRUD.create(
            session=db_session,
            key="test.setting",
            value="instance_value",
            scope=ConfigScope.INSTANCE,
            instance_id=instance.id,
        )
        db_session.commit()

        # Global scope should return global value
        value = ConfigurationCRUD.get_value(
            session=db_session, key="test.setting", scope=ConfigScope.GLOBAL
        )
        assert value == "global_value"

        # User scope should return user value (higher precedence than global)
        value = ConfigurationCRUD.get_value(
            session=db_session, key="test.setting", scope=ConfigScope.USER
        )
        assert value == "user_value"

        # Instance scope should return instance value (highest precedence)
        value = ConfigurationCRUD.get_value(
            session=db_session,
            key="test.setting",
            scope=ConfigScope.INSTANCE,
            instance_id=instance.id,
        )
        assert value == "instance_value"

    def test_get_value_not_found(self, db_session):
        """Test getting non-existent configuration value."""
        value = ConfigurationCRUD.get_value(
            session=db_session, key="nonexistent.setting"
        )
        assert value is None

    def test_configuration_get_by_key_not_found(self, db_session):
        """Test ConfigurationCRUD.get_by_key when no config found (line 766)."""
        # Create an instance first
        instance = InstanceCRUD.create(
            session=db_session,
            issue_id="test-456",
            workspace_path="/tmp/test-config",
            branch_name="feature/config-test",
            tmux_session="config-session",
        )

        # Try to get a non-existent configuration key
        # This should trigger the fallback return None at line 766
        config = ConfigurationCRUD.get_by_key_scope(
            session=db_session,
            key="nonexistent.key",
            scope=ConfigScope.INSTANCE,
            instance_id=instance.id,
        )

        # Should return None (line 766)
        assert config is None


class TestHealthCheckCRUD:
    """Test HealthCheck CRUD operations."""

    def test_health_check_list_with_offset(self, db_session):
        """Test HealthCheckCRUD.list_by_instance with offset (line 860)."""
        from datetime import datetime

        from cc_orchestrator.database.models import HealthCheck

        # Create an instance first
        instance = InstanceCRUD.create(
            session=db_session,
            issue_id="test-789",
            workspace_path="/tmp/test-health",
            branch_name="feature/health-test",
            tmux_session="health-session",
        )

        # Create multiple health checks
        health_checks = []
        for i in range(5):
            health_check = HealthCheck(
                instance_id=instance.id,
                overall_status=HealthStatus.HEALTHY,
                check_results=f"{{'message': 'Check {i}'}}",
                duration_ms=100,
                check_timestamp=datetime.now(),
            )
            db_session.add(health_check)
            health_checks.append(health_check)

        db_session.commit()

        # Test with offset (this covers line 860)
        result = HealthCheckCRUD.list_by_instance(
            session=db_session,
            instance_id=instance.id,
            offset=2,  # This triggers the offset condition at line 860
            limit=2,
        )

        # Should return 2 health checks starting from offset 2
        assert len(result) == 2
