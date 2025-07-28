"""Unit tests for database models."""

import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from cc_orchestrator.database import (
    Base,
    Instance,
    InstanceStatus,
    Task,
    TaskStatus,
    TaskPriority,
    Worktree,
    WorktreeStatus,
    Configuration,
    ConfigScope,
)


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


class TestInstanceModel:
    """Test Instance model."""
    
    def test_create_instance(self, db_session):
        """Test creating an instance."""
        instance = Instance(
            issue_id="123",
            workspace_path="/tmp/workspace",
            branch_name="feature/test",
            tmux_session="test-session",
            extra_metadata={"test": "data"},
        )
        
        db_session.add(instance)
        db_session.commit()
        
        assert instance.id is not None
        assert instance.issue_id == "123"
        assert instance.status == InstanceStatus.INITIALIZING
        assert instance.workspace_path == "/tmp/workspace"
        assert instance.branch_name == "feature/test"
        assert instance.tmux_session == "test-session"
        assert instance.extra_metadata == {"test": "data"}
        assert instance.created_at is not None
        assert instance.updated_at is not None
    
    def test_instance_unique_issue_id(self, db_session):
        """Test that issue_id must be unique."""
        instance1 = Instance(issue_id="123")
        instance2 = Instance(issue_id="123")
        
        db_session.add(instance1)
        db_session.commit()
        
        db_session.add(instance2)
        with pytest.raises(Exception):  # IntegrityError
            db_session.commit()
    
    def test_instance_repr(self, db_session):
        """Test instance string representation."""
        instance = Instance(issue_id="123", status=InstanceStatus.RUNNING)
        db_session.add(instance)
        db_session.commit()
        
        repr_str = repr(instance)
        assert "Instance" in repr_str
        assert "123" in repr_str
        assert "running" in repr_str


class TestTaskModel:
    """Test Task model."""
    
    def test_create_task(self, db_session):
        """Test creating a task."""
        task = Task(
            title="Test Task",
            description="A test task",
            priority=TaskPriority.HIGH,
            estimated_duration=60,
            requirements={"lang": "python"},
            extra_metadata={"category": "testing"},
        )
        
        db_session.add(task)
        db_session.commit()
        
        assert task.id is not None
        assert task.title == "Test Task"
        assert task.description == "A test task"
        assert task.status == TaskStatus.PENDING
        assert task.priority == TaskPriority.HIGH
        assert task.estimated_duration == 60
        assert task.requirements == {"lang": "python"}
        assert task.extra_metadata == {"category": "testing"}
        assert task.created_at is not None
    
    def test_task_instance_relationship(self, db_session):
        """Test task-instance relationship."""
        instance = Instance(issue_id="123")
        task = Task(title="Test Task", instance=instance)
        
        db_session.add(instance)
        db_session.add(task)
        db_session.commit()
        
        assert task.instance_id == instance.id
        assert task.instance == instance
        assert task in instance.tasks
    
    def test_task_worktree_relationship(self, db_session):
        """Test task-worktree relationship."""
        worktree = Worktree(
            name="test-worktree",
            path="/tmp/test",
            branch_name="main"
        )
        task = Task(title="Test Task", worktree=worktree)
        
        db_session.add(worktree)
        db_session.add(task)
        db_session.commit()
        
        assert task.worktree_id == worktree.id
        assert task.worktree == worktree
        assert task in worktree.tasks


class TestWorktreeModel:
    """Test Worktree model."""
    
    def test_create_worktree(self, db_session):
        """Test creating a worktree."""
        worktree = Worktree(
            name="test-worktree",
            path="/tmp/test-worktree",
            branch_name="feature/test",
            repository_url="https://github.com/test/repo.git",
            current_commit="abc123",
            has_uncommitted_changes=True,
            git_config={"remote.origin.url": "https://github.com/test/repo.git"},
            extra_metadata={"purpose": "testing"},
        )
        
        db_session.add(worktree)
        db_session.commit()
        
        assert worktree.id is not None
        assert worktree.name == "test-worktree"
        assert worktree.path == "/tmp/test-worktree"
        assert worktree.branch_name == "feature/test"
        assert worktree.repository_url == "https://github.com/test/repo.git"
        assert worktree.status == WorktreeStatus.ACTIVE
        assert worktree.current_commit == "abc123"
        assert worktree.has_uncommitted_changes is True
        assert worktree.git_config == {"remote.origin.url": "https://github.com/test/repo.git"}
        assert worktree.extra_metadata == {"purpose": "testing"}
    
    def test_worktree_unique_path(self, db_session):
        """Test that worktree path must be unique."""
        worktree1 = Worktree(name="test1", path="/tmp/test", branch_name="main")
        worktree2 = Worktree(name="test2", path="/tmp/test", branch_name="feature")
        
        db_session.add(worktree1)
        db_session.commit()
        
        db_session.add(worktree2)
        with pytest.raises(Exception):  # IntegrityError
            db_session.commit()
    
    def test_worktree_instance_relationship(self, db_session):
        """Test worktree-instance relationship."""
        instance = Instance(issue_id="123")
        worktree = Worktree(
            name="test-worktree",
            path="/tmp/test",
            branch_name="main",
            instance=instance
        )
        
        db_session.add(instance)
        db_session.add(worktree)
        db_session.commit()
        
        assert worktree.instance_id == instance.id
        assert worktree.instance == instance
        assert instance.worktree == worktree


class TestConfigurationModel:
    """Test Configuration model."""
    
    def test_create_configuration(self, db_session):
        """Test creating a configuration."""
        config = Configuration(
            key="test.setting",
            value="test_value",
            scope=ConfigScope.GLOBAL,
            description="A test configuration",
            is_secret=False,
            extra_metadata={"source": "test"},
        )
        
        db_session.add(config)
        db_session.commit()
        
        assert config.id is not None
        assert config.key == "test.setting"
        assert config.value == "test_value"
        assert config.scope == ConfigScope.GLOBAL
        assert config.description == "A test configuration"
        assert config.is_secret is False
        assert config.extra_metadata == {"source": "test"}
        assert config.created_at is not None
    
    def test_configuration_instance_scoped(self, db_session):
        """Test instance-scoped configuration."""
        instance = Instance(issue_id="123")
        config = Configuration(
            key="instance.setting",
            value="instance_value",
            scope=ConfigScope.INSTANCE,
            instance=instance,
        )
        
        db_session.add(instance)
        db_session.add(config)
        db_session.commit()
        
        assert config.instance_id == instance.id
        assert config.scope == ConfigScope.INSTANCE
    
    def test_configuration_repr(self, db_session):
        """Test configuration string representation."""
        config = Configuration(
            key="test.key",
            value="test_value",
            scope=ConfigScope.USER
        )
        db_session.add(config)
        db_session.commit()
        
        repr_str = repr(config)
        assert "Configuration" in repr_str
        assert "test.key" in repr_str
        assert "user" in repr_str


class TestModelRelationships:
    """Test model relationships and cascades."""
    
    def test_instance_deletion_cascades_to_tasks(self, db_session):
        """Test that deleting an instance deletes its tasks."""
        instance = Instance(issue_id="123")
        task1 = Task(title="Task 1", instance=instance)
        task2 = Task(title="Task 2", instance=instance)
        
        db_session.add_all([instance, task1, task2])
        db_session.commit()
        
        # Verify tasks exist
        assert db_session.query(Task).count() == 2
        
        # Delete instance
        db_session.delete(instance)
        db_session.commit()
        
        # Verify tasks are deleted
        assert db_session.query(Task).count() == 0
    
    def test_worktree_tasks_relationship(self, db_session):
        """Test worktree can have multiple tasks."""
        worktree = Worktree(name="test", path="/tmp/test", branch_name="main")
        task1 = Task(title="Task 1", worktree=worktree)
        task2 = Task(title="Task 2", worktree=worktree)
        
        db_session.add_all([worktree, task1, task2])
        db_session.commit()
        
        assert len(worktree.tasks) == 2
        assert task1 in worktree.tasks
        assert task2 in worktree.tasks