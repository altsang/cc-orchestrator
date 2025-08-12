"""Comprehensive tests for src/cc_orchestrator/database/models.py module.

This test suite provides comprehensive coverage for all database models including:
- Base declarative class
- All enum classes (InstanceStatus, HealthStatus, TaskStatus, TaskPriority, WorktreeStatus, ConfigScope)
- All model classes (Instance, Task, Worktree, HealthCheck, Configuration)
- Model relationships and foreign keys
- Model field defaults and constraints
- Model __repr__ methods
- Database indexes
- SQLAlchemy integration

Target: 100% coverage (142/142 statements)
"""

from datetime import datetime, timedelta

from sqlalchemy import Index

from cc_orchestrator.database.models import (
    Base,
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


class TestBase:
    """Test Base declarative class."""

    def test_base_class_exists(self):
        """Test Base declarative class is properly defined."""
        assert Base is not None
        assert hasattr(Base, '__table_args__')
        assert hasattr(Base, 'registry')

    def test_base_inheritance(self):
        """Test Base can be used as parent class."""
        class TestModel(Base):
            __tablename__ = "test_model"

        assert issubclass(TestModel, Base)


class TestInstanceStatus:
    """Test InstanceStatus enumeration."""

    def test_instance_status_values(self):
        """Test all instance status enum values."""
        assert InstanceStatus.INITIALIZING.value == "initializing"
        assert InstanceStatus.RUNNING.value == "running"
        assert InstanceStatus.STOPPED.value == "stopped"
        assert InstanceStatus.ERROR.value == "error"

    def test_instance_status_count(self):
        """Test expected number of instance statuses."""
        statuses = list(InstanceStatus)
        assert len(statuses) == 4

    def test_instance_status_comparison(self):
        """Test instance status enum comparison."""
        assert InstanceStatus.INITIALIZING != InstanceStatus.RUNNING
        assert InstanceStatus.STOPPED == InstanceStatus.STOPPED

    def test_instance_status_string_conversion(self):
        """Test instance status string conversion."""
        assert str(InstanceStatus.INITIALIZING) == "InstanceStatus.INITIALIZING"
        assert InstanceStatus.RUNNING.value == "running"

    def test_instance_status_iteration(self):
        """Test iteration over instance status values."""
        expected_values = {"initializing", "running", "stopped", "error"}
        actual_values = {status.value for status in InstanceStatus}
        assert actual_values == expected_values


class TestHealthStatus:
    """Test HealthStatus enumeration."""

    def test_health_status_values(self):
        """Test all health status enum values."""
        assert HealthStatus.HEALTHY.value == "healthy"
        assert HealthStatus.DEGRADED.value == "degraded"
        assert HealthStatus.UNHEALTHY.value == "unhealthy"
        assert HealthStatus.CRITICAL.value == "critical"
        assert HealthStatus.UNKNOWN.value == "unknown"

    def test_health_status_count(self):
        """Test expected number of health statuses."""
        statuses = list(HealthStatus)
        assert len(statuses) == 5

    def test_health_status_comparison(self):
        """Test health status enum comparison."""
        assert HealthStatus.HEALTHY != HealthStatus.DEGRADED
        assert HealthStatus.UNKNOWN == HealthStatus.UNKNOWN

    def test_health_status_iteration(self):
        """Test iteration over health status values."""
        expected_values = {"healthy", "degraded", "unhealthy", "critical", "unknown"}
        actual_values = {status.value for status in HealthStatus}
        assert actual_values == expected_values


class TestTaskStatus:
    """Test TaskStatus enumeration."""

    def test_task_status_values(self):
        """Test all task status enum values."""
        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.IN_PROGRESS.value == "in_progress"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.FAILED.value == "failed"
        assert TaskStatus.CANCELLED.value == "cancelled"

    def test_task_status_count(self):
        """Test expected number of task statuses."""
        statuses = list(TaskStatus)
        assert len(statuses) == 5

    def test_task_status_iteration(self):
        """Test iteration over task status values."""
        expected_values = {"pending", "in_progress", "completed", "failed", "cancelled"}
        actual_values = {status.value for status in TaskStatus}
        assert actual_values == expected_values


class TestTaskPriority:
    """Test TaskPriority enumeration."""

    def test_task_priority_values(self):
        """Test all task priority enum values."""
        assert TaskPriority.LOW.value == 1
        assert TaskPriority.MEDIUM.value == 2
        assert TaskPriority.HIGH.value == 3
        assert TaskPriority.URGENT.value == 4

    def test_task_priority_count(self):
        """Test expected number of task priorities."""
        priorities = list(TaskPriority)
        assert len(priorities) == 4

    def test_task_priority_ordering(self):
        """Test task priority numeric ordering."""
        assert TaskPriority.LOW.value < TaskPriority.MEDIUM.value
        assert TaskPriority.MEDIUM.value < TaskPriority.HIGH.value
        assert TaskPriority.HIGH.value < TaskPriority.URGENT.value

    def test_task_priority_comparison(self):
        """Test task priority comparison."""
        assert TaskPriority.LOW != TaskPriority.HIGH
        assert TaskPriority.URGENT == TaskPriority.URGENT


class TestWorktreeStatus:
    """Test WorktreeStatus enumeration."""

    def test_worktree_status_values(self):
        """Test all worktree status enum values."""
        assert WorktreeStatus.ACTIVE.value == "active"
        assert WorktreeStatus.INACTIVE.value == "inactive"
        assert WorktreeStatus.DIRTY.value == "dirty"
        assert WorktreeStatus.ERROR.value == "error"

    def test_worktree_status_count(self):
        """Test expected number of worktree statuses."""
        statuses = list(WorktreeStatus)
        assert len(statuses) == 4

    def test_worktree_status_iteration(self):
        """Test iteration over worktree status values."""
        expected_values = {"active", "inactive", "dirty", "error"}
        actual_values = {status.value for status in WorktreeStatus}
        assert actual_values == expected_values


class TestConfigScope:
    """Test ConfigScope enumeration."""

    def test_config_scope_values(self):
        """Test all config scope enum values."""
        assert ConfigScope.GLOBAL.value == "global"
        assert ConfigScope.USER.value == "user"
        assert ConfigScope.PROJECT.value == "project"
        assert ConfigScope.INSTANCE.value == "instance"

    def test_config_scope_count(self):
        """Test expected number of config scopes."""
        scopes = list(ConfigScope)
        assert len(scopes) == 4

    def test_config_scope_iteration(self):
        """Test iteration over config scope values."""
        expected_values = {"global", "user", "project", "instance"}
        actual_values = {scope.value for scope in ConfigScope}
        assert actual_values == expected_values


class TestInstanceModel:
    """Test Instance model class."""

    def test_instance_creation_minimal(self):
        """Test creating instance with minimal required fields."""
        instance = Instance(issue_id="ISSUE-123")

        assert instance.issue_id == "ISSUE-123"
        assert instance.status == InstanceStatus.INITIALIZING  # Default
        assert instance.health_status == HealthStatus.UNKNOWN  # Default
        assert instance.health_check_count == 0  # Default
        assert instance.healthy_check_count == 0  # Default
        assert instance.recovery_attempt_count == 0  # Default
        assert instance.extra_metadata == {}  # Default

    def test_instance_creation_with_all_fields(self):
        """Test creating instance with all fields."""
        now = datetime.now()
        instance = Instance(
            issue_id="ISSUE-456",
            status=InstanceStatus.RUNNING,
            workspace_path="/path/to/workspace",
            branch_name="feature/test",
            tmux_session="test-session",
            process_id=12345,
            health_status=HealthStatus.HEALTHY,
            last_health_check=now,
            health_check_count=5,
            healthy_check_count=4,
            last_recovery_attempt=now,
            recovery_attempt_count=1,
            health_check_details="All systems nominal",
            created_at=now,
            updated_at=now,
            last_activity=now,
            extra_metadata={"custom": "data"}
        )

        assert instance.issue_id == "ISSUE-456"
        assert instance.status == InstanceStatus.RUNNING
        assert instance.workspace_path == "/path/to/workspace"
        assert instance.branch_name == "feature/test"
        assert instance.tmux_session == "test-session"
        assert instance.process_id == 12345
        assert instance.health_status == HealthStatus.HEALTHY
        assert instance.last_health_check == now
        assert instance.health_check_count == 5
        assert instance.healthy_check_count == 4
        assert instance.last_recovery_attempt == now
        assert instance.recovery_attempt_count == 1
        assert instance.health_check_details == "All systems nominal"
        assert instance.extra_metadata == {"custom": "data"}

    def test_instance_default_values(self):
        """Test instance model default values."""
        instance = Instance(issue_id="DEFAULT-TEST")

        assert instance.status == InstanceStatus.INITIALIZING
        assert instance.health_status == HealthStatus.UNKNOWN
        assert instance.health_check_count == 0
        assert instance.healthy_check_count == 0
        assert instance.recovery_attempt_count == 0
        assert instance.extra_metadata == {}
        assert instance.workspace_path is None
        assert instance.branch_name is None
        assert instance.tmux_session is None
        assert instance.process_id is None

    def test_instance_repr(self):
        """Test instance __repr__ method."""
        instance = Instance(
            id=123,
            issue_id="REPR-TEST",
            status=InstanceStatus.RUNNING
        )

        repr_str = repr(instance)
        assert "Instance" in repr_str
        assert "id=123" in repr_str
        assert "issue_id='REPR-TEST'" in repr_str
        assert "status='running'" in repr_str

    def test_instance_tablename(self):
        """Test instance table name."""
        assert Instance.__tablename__ == "instances"

    def test_instance_nullable_fields(self):
        """Test instance nullable field behavior."""
        instance = Instance(issue_id="NULL-TEST")

        # These fields should accept None values
        instance.workspace_path = None
        instance.branch_name = None
        instance.tmux_session = None
        instance.process_id = None
        instance.last_health_check = None
        instance.last_recovery_attempt = None
        instance.last_activity = None
        instance.health_check_details = None

        # Should not raise any exceptions
        assert instance.workspace_path is None
        assert instance.process_id is None


class TestTaskModel:
    """Test Task model class."""

    def test_task_creation_minimal(self):
        """Test creating task with minimal required fields."""
        task = Task(title="Test Task")

        assert task.title == "Test Task"
        assert task.status == TaskStatus.PENDING  # Default
        assert task.priority == TaskPriority.MEDIUM  # Default
        assert task.requirements == {}  # Default
        assert task.results == {}  # Default
        assert task.extra_metadata == {}  # Default

    def test_task_creation_with_all_fields(self):
        """Test creating task with all fields."""
        now = datetime.now()
        due_date = now + timedelta(days=7)

        task = Task(
            title="Complete Task",
            description="Full task description",
            status=TaskStatus.IN_PROGRESS,
            priority=TaskPriority.HIGH,
            instance_id=123,
            worktree_id=456,
            created_at=now,
            updated_at=now,
            started_at=now,
            completed_at=None,
            due_date=due_date,
            estimated_duration=120,
            actual_duration=90,
            requirements={"python": "3.9+"},
            results={"output": "success"},
            extra_metadata={"source": "api"}
        )

        assert task.title == "Complete Task"
        assert task.description == "Full task description"
        assert task.status == TaskStatus.IN_PROGRESS
        assert task.priority == TaskPriority.HIGH
        assert task.instance_id == 123
        assert task.worktree_id == 456
        assert task.due_date == due_date
        assert task.estimated_duration == 120
        assert task.actual_duration == 90
        assert task.requirements == {"python": "3.9+"}
        assert task.results == {"output": "success"}
        assert task.extra_metadata == {"source": "api"}

    def test_task_default_values(self):
        """Test task model default values."""
        task = Task(title="Default Test")

        assert task.status == TaskStatus.PENDING
        assert task.priority == TaskPriority.MEDIUM
        assert task.requirements == {}
        assert task.results == {}
        assert task.extra_metadata == {}
        assert task.description is None
        assert task.instance_id is None
        assert task.worktree_id is None

    def test_task_repr(self):
        """Test task __repr__ method."""
        task = Task(
            id=456,
            title="Repr Task",
            status=TaskStatus.COMPLETED
        )

        repr_str = repr(task)
        assert "Task" in repr_str
        assert "id=456" in repr_str
        assert "title='Repr Task'" in repr_str
        assert "status='completed'" in repr_str

    def test_task_tablename(self):
        """Test task table name."""
        assert Task.__tablename__ == "tasks"

    def test_task_nullable_fields(self):
        """Test task nullable field behavior."""
        task = Task(title="Nullable Test")

        # These fields should accept None values
        task.description = None
        task.instance_id = None
        task.worktree_id = None
        task.started_at = None
        task.completed_at = None
        task.due_date = None
        task.estimated_duration = None
        task.actual_duration = None

        # Should not raise any exceptions
        assert task.description is None
        assert task.estimated_duration is None


class TestWorktreeModel:
    """Test Worktree model class."""

    def test_worktree_creation_minimal(self):
        """Test creating worktree with minimal required fields."""
        worktree = Worktree(
            name="test-worktree",
            path="/path/to/worktree",
            branch_name="main"
        )

        assert worktree.name == "test-worktree"
        assert worktree.path == "/path/to/worktree"
        assert worktree.branch_name == "main"
        assert worktree.status == WorktreeStatus.ACTIVE  # Default
        assert worktree.has_uncommitted_changes is False  # Default
        assert worktree.git_config == {}  # Default
        assert worktree.extra_metadata == {}  # Default

    def test_worktree_creation_with_all_fields(self):
        """Test creating worktree with all fields."""
        now = datetime.now()

        worktree = Worktree(
            name="full-worktree",
            path="/full/path/to/worktree",
            branch_name="feature/complete",
            repository_url="https://github.com/user/repo.git",
            status=WorktreeStatus.DIRTY,
            instance_id=789,
            current_commit="abc123def456",
            has_uncommitted_changes=True,
            created_at=now,
            updated_at=now,
            last_sync=now,
            git_config={"user.email": "test@example.com"},
            extra_metadata={"project": "test"}
        )

        assert worktree.name == "full-worktree"
        assert worktree.path == "/full/path/to/worktree"
        assert worktree.branch_name == "feature/complete"
        assert worktree.repository_url == "https://github.com/user/repo.git"
        assert worktree.status == WorktreeStatus.DIRTY
        assert worktree.instance_id == 789
        assert worktree.current_commit == "abc123def456"
        assert worktree.has_uncommitted_changes is True
        assert worktree.git_config == {"user.email": "test@example.com"}
        assert worktree.extra_metadata == {"project": "test"}

    def test_worktree_default_values(self):
        """Test worktree model default values."""
        worktree = Worktree(
            name="default-test",
            path="/default/path",
            branch_name="default"
        )

        assert worktree.status == WorktreeStatus.ACTIVE
        assert worktree.has_uncommitted_changes is False
        assert worktree.git_config == {}
        assert worktree.extra_metadata == {}
        assert worktree.repository_url is None
        assert worktree.instance_id is None
        assert worktree.current_commit is None

    def test_worktree_repr(self):
        """Test worktree __repr__ method."""
        worktree = Worktree(
            id=789,
            name="repr-worktree",
            path="/repr/path",
            branch_name="repr-branch"
        )

        repr_str = repr(worktree)
        assert "Worktree" in repr_str
        assert "id=789" in repr_str
        assert "name='repr-worktree'" in repr_str
        assert "branch='repr-branch'" in repr_str

    def test_worktree_tablename(self):
        """Test worktree table name."""
        assert Worktree.__tablename__ == "worktrees"

    def test_worktree_nullable_fields(self):
        """Test worktree nullable field behavior."""
        worktree = Worktree(
            name="nullable-test",
            path="/nullable/path",
            branch_name="nullable"
        )

        # These fields should accept None values
        worktree.repository_url = None
        worktree.instance_id = None
        worktree.current_commit = None
        worktree.last_sync = None

        # Should not raise any exceptions
        assert worktree.repository_url is None
        assert worktree.current_commit is None


class TestHealthCheckModel:
    """Test HealthCheck model class."""

    def test_health_check_creation(self):
        """Test creating health check with all required fields."""
        now = datetime.now()

        health_check = HealthCheck(
            instance_id=123,
            overall_status=HealthStatus.HEALTHY,
            check_results='{"cpu": "ok", "memory": "ok"}',
            duration_ms=250.5,
            check_timestamp=now
        )

        assert health_check.instance_id == 123
        assert health_check.overall_status == HealthStatus.HEALTHY
        assert health_check.check_results == '{"cpu": "ok", "memory": "ok"}'
        assert health_check.duration_ms == 250.5
        assert health_check.check_timestamp == now

    def test_health_check_with_different_statuses(self):
        """Test health check with different health statuses."""
        now = datetime.now()

        statuses_to_test = [
            HealthStatus.HEALTHY,
            HealthStatus.DEGRADED,
            HealthStatus.UNHEALTHY,
            HealthStatus.CRITICAL,
            HealthStatus.UNKNOWN
        ]

        for status in statuses_to_test:
            health_check = HealthCheck(
                instance_id=456,
                overall_status=status,
                check_results=f'{{"status": "{status.value}"}}',
                duration_ms=100,
                check_timestamp=now
            )

            assert health_check.overall_status == status

    def test_health_check_repr(self):
        """Test health check __repr__ method."""
        health_check = HealthCheck(
            id=999,
            instance_id=123,
            overall_status=HealthStatus.DEGRADED,
            check_results='{"test": "data"}',
            duration_ms=300,
            check_timestamp=datetime.now()
        )

        repr_str = repr(health_check)
        assert "HealthCheck" in repr_str
        assert "id=999" in repr_str
        assert "instance_id=123" in repr_str
        assert "status='degraded'" in repr_str

    def test_health_check_tablename(self):
        """Test health check table name."""
        assert HealthCheck.__tablename__ == "health_checks"

    def test_health_check_required_fields(self):
        """Test health check requires all necessary fields."""
        now = datetime.now()

        # All these fields are required (non-nullable)
        health_check = HealthCheck(
            instance_id=789,
            overall_status=HealthStatus.CRITICAL,
            check_results='{"error": "system failure"}',
            duration_ms=500,
            check_timestamp=now
        )

        assert health_check.instance_id is not None
        assert health_check.overall_status is not None
        assert health_check.check_results is not None
        assert health_check.duration_ms is not None
        assert health_check.check_timestamp is not None


class TestConfigurationModel:
    """Test Configuration model class."""

    def test_configuration_creation_minimal(self):
        """Test creating configuration with minimal required fields."""
        config = Configuration(
            key="test.setting",
            value="test_value"
        )

        assert config.key == "test.setting"
        assert config.value == "test_value"
        assert config.scope == ConfigScope.GLOBAL  # Default
        assert config.is_secret is False  # Default
        assert config.is_readonly is False  # Default
        assert config.extra_metadata == {}  # Default

    def test_configuration_creation_with_all_fields(self):
        """Test creating configuration with all fields."""
        now = datetime.now()

        config = Configuration(
            key="complex.setting",
            value="complex_value",
            scope=ConfigScope.INSTANCE,
            instance_id=123,
            description="Test configuration setting",
            is_secret=True,
            is_readonly=True,
            created_at=now,
            updated_at=now,
            extra_metadata={"source": "api", "category": "database"}
        )

        assert config.key == "complex.setting"
        assert config.value == "complex_value"
        assert config.scope == ConfigScope.INSTANCE
        assert config.instance_id == 123
        assert config.description == "Test configuration setting"
        assert config.is_secret is True
        assert config.is_readonly is True
        assert config.extra_metadata == {"source": "api", "category": "database"}

    def test_configuration_default_values(self):
        """Test configuration model default values."""
        config = Configuration(
            key="default.test",
            value="default_value"
        )

        assert config.scope == ConfigScope.GLOBAL
        assert config.is_secret is False
        assert config.is_readonly is False
        assert config.extra_metadata == {}
        assert config.instance_id is None
        assert config.description is None

    def test_configuration_with_different_scopes(self):
        """Test configuration with different scope values."""
        scopes_to_test = [
            ConfigScope.GLOBAL,
            ConfigScope.USER,
            ConfigScope.PROJECT,
            ConfigScope.INSTANCE
        ]

        for scope in scopes_to_test:
            config = Configuration(
                key=f"test.{scope.value}",
                value="test_value",
                scope=scope
            )

            assert config.scope == scope

    def test_configuration_repr(self):
        """Test configuration __repr__ method."""
        config = Configuration(
            id=555,
            key="repr.test",
            value="repr_value",
            scope=ConfigScope.PROJECT
        )

        repr_str = repr(config)
        assert "Configuration" in repr_str
        assert "id=555" in repr_str
        assert "key='repr.test'" in repr_str
        assert "scope='project'" in repr_str

    def test_configuration_tablename(self):
        """Test configuration table name."""
        assert Configuration.__tablename__ == "configurations"

    def test_configuration_nullable_fields(self):
        """Test configuration nullable field behavior."""
        config = Configuration(
            key="nullable.test",
            value="nullable_value"
        )

        # These fields should accept None values
        config.instance_id = None
        config.description = None

        # Should not raise any exceptions
        assert config.instance_id is None
        assert config.description is None

    def test_configuration_boolean_fields(self):
        """Test configuration boolean field behavior."""
        config = Configuration(
            key="boolean.test",
            value="boolean_value"
        )

        # Test setting boolean values
        config.is_secret = True
        config.is_readonly = False

        assert config.is_secret is True
        assert config.is_readonly is False

        config.is_secret = False
        config.is_readonly = True

        assert config.is_secret is False
        assert config.is_readonly is True


class TestModelRelationships:
    """Test relationships between models."""

    def test_instance_task_relationship(self):
        """Test Instance-Task relationship."""
        instance = Instance(issue_id="REL-123")

        # Test relationship attributes exist
        assert hasattr(instance, 'tasks')

        # Test Task has instance relationship
        task = Task(title="Related Task")
        assert hasattr(task, 'instance')

    def test_instance_worktree_relationship(self):
        """Test Instance-Worktree relationship."""
        instance = Instance(issue_id="REL-456")

        # Test relationship attributes exist
        assert hasattr(instance, 'worktree')

        # Test Worktree has instance relationship
        worktree = Worktree(name="test", path="/test", branch_name="main")
        assert hasattr(worktree, 'instance')

    def test_instance_configuration_relationship(self):
        """Test Instance-Configuration relationship."""
        instance = Instance(issue_id="REL-789")

        # Test relationship attributes exist
        assert hasattr(instance, 'configurations')

        # Test Configuration has instance relationship
        config = Configuration(key="test.key", value="test_value")
        assert hasattr(config, 'instance')

    def test_worktree_task_relationship(self):
        """Test Worktree-Task relationship."""
        worktree = Worktree(name="test", path="/test", branch_name="main")
        task = Task(title="Test Task")

        # Test relationship attributes exist
        assert hasattr(worktree, 'tasks')
        assert hasattr(task, 'worktree')

    def test_health_check_instance_relationship(self):
        """Test HealthCheck-Instance relationship."""
        health_check = HealthCheck(
            instance_id=123,
            overall_status=HealthStatus.HEALTHY,
            check_results='{"status": "ok"}',
            duration_ms=100,
            check_timestamp=datetime.now()
        )

        # Test relationship attributes exist
        assert hasattr(health_check, 'instance')


class TestModelIndexes:
    """Test database indexes are properly defined."""

    def test_instance_indexes_exist(self):
        """Test Instance model indexes are defined."""
        # These indexes should be defined in the module
        # We test by checking the module level variables
        import cc_orchestrator.database.models as models_module
        from cc_orchestrator.database.models import Index

        # Look for index definitions
        index_names = []
        for attr_name in dir(models_module):
            attr = getattr(models_module, attr_name)
            if isinstance(attr, Index):
                index_names.append(attr.name)

        # Expected instance indexes
        expected_instance_indexes = [
            "idx_instances_issue_id",
            "idx_instances_status",
            "idx_instances_created_at"
        ]

        for expected_index in expected_instance_indexes:
            assert expected_index in index_names

    def test_task_indexes_exist(self):
        """Test Task model indexes are defined."""
        import cc_orchestrator.database.models as models_module

        index_names = []
        for attr_name in dir(models_module):
            attr = getattr(models_module, attr_name)
            if isinstance(attr, Index):
                index_names.append(attr.name)

        expected_task_indexes = [
            "idx_tasks_status",
            "idx_tasks_priority",
            "idx_tasks_instance_id",
            "idx_tasks_created_at",
            "idx_tasks_due_date"
        ]

        for expected_index in expected_task_indexes:
            assert expected_index in index_names

    def test_worktree_indexes_exist(self):
        """Test Worktree model indexes are defined."""
        import cc_orchestrator.database.models as models_module

        index_names = []
        for attr_name in dir(models_module):
            attr = getattr(models_module, attr_name)
            if isinstance(attr, Index):
                index_names.append(attr.name)

        expected_worktree_indexes = [
            "idx_worktrees_path",
            "idx_worktrees_branch",
            "idx_worktrees_status"
        ]

        for expected_index in expected_worktree_indexes:
            assert expected_index in index_names

    def test_configuration_indexes_exist(self):
        """Test Configuration model indexes are defined."""
        import cc_orchestrator.database.models as models_module

        index_names = []
        for attr_name in dir(models_module):
            attr = getattr(models_module, attr_name)
            if isinstance(attr, Index):
                index_names.append(attr.name)

        expected_config_indexes = [
            "idx_configurations_key_scope",
            "idx_configurations_instance_id"
        ]

        for expected_index in expected_config_indexes:
            assert expected_index in index_names

    def test_health_check_indexes_exist(self):
        """Test HealthCheck model indexes are defined."""
        import cc_orchestrator.database.models as models_module

        index_names = []
        for attr_name in dir(models_module):
            attr = getattr(models_module, attr_name)
            if isinstance(attr, Index):
                index_names.append(attr.name)

        expected_health_indexes = [
            "idx_health_checks_instance_id",
            "idx_health_checks_timestamp"
        ]

        for expected_index in expected_health_indexes:
            assert expected_index in index_names

    def test_total_index_count(self):
        """Test total number of indexes defined."""
        import cc_orchestrator.database.models as models_module

        index_count = 0
        for attr_name in dir(models_module):
            attr = getattr(models_module, attr_name)
            if isinstance(attr, Index):
                index_count += 1

        # Total expected indexes: 3 + 5 + 3 + 2 + 2 = 15
        assert index_count == 15


class TestModelFieldTypes:
    """Test model field types and constraints."""

    def test_instance_field_types(self):
        """Test Instance model field types."""
        instance = Instance(issue_id="TYPE-TEST")

        # Test that required fields have correct types
        assert isinstance(instance.issue_id, str)
        assert isinstance(instance.status, InstanceStatus)
        assert isinstance(instance.health_status, HealthStatus)
        assert isinstance(instance.health_check_count, int)
        assert isinstance(instance.healthy_check_count, int)
        assert isinstance(instance.recovery_attempt_count, int)
        assert isinstance(instance.extra_metadata, dict)

    def test_task_field_types(self):
        """Test Task model field types."""
        task = Task(title="Type Test")

        # Test that required fields have correct types
        assert isinstance(task.title, str)
        assert isinstance(task.status, TaskStatus)
        assert isinstance(task.priority, TaskPriority)
        assert isinstance(task.requirements, dict)
        assert isinstance(task.results, dict)
        assert isinstance(task.extra_metadata, dict)

    def test_worktree_field_types(self):
        """Test Worktree model field types."""
        worktree = Worktree(
            name="type-test",
            path="/type/test",
            branch_name="type-branch"
        )

        # Test that required fields have correct types
        assert isinstance(worktree.name, str)
        assert isinstance(worktree.path, str)
        assert isinstance(worktree.branch_name, str)
        assert isinstance(worktree.status, WorktreeStatus)
        assert isinstance(worktree.has_uncommitted_changes, bool)
        assert isinstance(worktree.git_config, dict)
        assert isinstance(worktree.extra_metadata, dict)

    def test_health_check_field_types(self):
        """Test HealthCheck model field types."""
        health_check = HealthCheck(
            instance_id=123,
            overall_status=HealthStatus.HEALTHY,
            check_results='{"type": "test"}',
            duration_ms=100,
            check_timestamp=datetime.now()
        )

        # Test that required fields have correct types
        assert isinstance(health_check.instance_id, int)
        assert isinstance(health_check.overall_status, HealthStatus)
        assert isinstance(health_check.check_results, str)
        assert isinstance(health_check.duration_ms, int | float)
        assert isinstance(health_check.check_timestamp, datetime)

    def test_configuration_field_types(self):
        """Test Configuration model field types."""
        config = Configuration(key="type.test", value="test_value")

        # Test that required fields have correct types
        assert isinstance(config.key, str)
        assert isinstance(config.value, str)
        assert isinstance(config.scope, ConfigScope)
        assert isinstance(config.is_secret, bool)
        assert isinstance(config.is_readonly, bool)
        assert isinstance(config.extra_metadata, dict)


class TestModelTimestamps:
    """Test model timestamp behavior."""

    def test_instance_timestamps(self):
        """Test Instance model timestamp fields."""
        instance = Instance(issue_id="TIME-TEST")

        # Test that timestamp fields exist
        assert hasattr(instance, 'created_at')
        assert hasattr(instance, 'updated_at')
        assert hasattr(instance, 'last_activity')
        assert hasattr(instance, 'last_health_check')
        assert hasattr(instance, 'last_recovery_attempt')

    def test_task_timestamps(self):
        """Test Task model timestamp fields."""
        task = Task(title="Time Test")

        # Test that timestamp fields exist
        assert hasattr(task, 'created_at')
        assert hasattr(task, 'updated_at')
        assert hasattr(task, 'started_at')
        assert hasattr(task, 'completed_at')
        assert hasattr(task, 'due_date')

    def test_worktree_timestamps(self):
        """Test Worktree model timestamp fields."""
        worktree = Worktree(
            name="time-test",
            path="/time/test",
            branch_name="time"
        )

        # Test that timestamp fields exist
        assert hasattr(worktree, 'created_at')
        assert hasattr(worktree, 'updated_at')
        assert hasattr(worktree, 'last_sync')

    def test_health_check_timestamps(self):
        """Test HealthCheck model timestamp fields."""
        health_check = HealthCheck(
            instance_id=123,
            overall_status=HealthStatus.HEALTHY,
            check_results='{"time": "test"}',
            duration_ms=100,
            check_timestamp=datetime.now()
        )

        # Test that timestamp fields exist
        assert hasattr(health_check, 'created_at')
        assert hasattr(health_check, 'updated_at')
        assert hasattr(health_check, 'check_timestamp')

    def test_configuration_timestamps(self):
        """Test Configuration model timestamp fields."""
        config = Configuration(key="time.test", value="test_value")

        # Test that timestamp fields exist
        assert hasattr(config, 'created_at')
        assert hasattr(config, 'updated_at')


class TestModelJSONFields:
    """Test model JSON field behavior."""

    def test_instance_json_fields(self):
        """Test Instance model JSON fields."""
        metadata = {"custom": "data", "numbers": [1, 2, 3]}
        instance = Instance(
            issue_id="JSON-TEST",
            extra_metadata=metadata
        )

        assert instance.extra_metadata == metadata
        assert isinstance(instance.extra_metadata, dict)

    def test_task_json_fields(self):
        """Test Task model JSON fields."""
        requirements = {"python": "3.9+", "memory": "4GB"}
        results = {"status": "success", "output_lines": 100}
        metadata = {"priority_reason": "critical bug"}

        task = Task(
            title="JSON Test",
            requirements=requirements,
            results=results,
            extra_metadata=metadata
        )

        assert task.requirements == requirements
        assert task.results == results
        assert task.extra_metadata == metadata

    def test_worktree_json_fields(self):
        """Test Worktree model JSON fields."""
        git_config = {"user.name": "Test User", "user.email": "test@example.com"}
        metadata = {"project_type": "python", "framework": "fastapi"}

        worktree = Worktree(
            name="json-test",
            path="/json/test",
            branch_name="json",
            git_config=git_config,
            extra_metadata=metadata
        )

        assert worktree.git_config == git_config
        assert worktree.extra_metadata == metadata

    def test_configuration_json_fields(self):
        """Test Configuration model JSON fields."""
        metadata = {"category": "database", "sensitive": False, "tags": ["api", "config"]}

        config = Configuration(
            key="json.test",
            value="json_value",
            extra_metadata=metadata
        )

        assert config.extra_metadata == metadata


class TestEnumIntegration:
    """Test enum integration with models."""

    def test_all_instance_statuses_work(self):
        """Test all instance statuses work with model."""
        for status in InstanceStatus:
            instance = Instance(issue_id=f"STATUS-{status.value.upper()}")
            instance.status = status
            assert instance.status == status

    def test_all_health_statuses_work(self):
        """Test all health statuses work with model."""
        for health_status in HealthStatus:
            instance = Instance(issue_id=f"HEALTH-{health_status.value.upper()}")
            instance.health_status = health_status
            assert instance.health_status == health_status

    def test_all_task_statuses_work(self):
        """Test all task statuses work with model."""
        for status in TaskStatus:
            task = Task(title=f"Task {status.value}")
            task.status = status
            assert task.status == status

    def test_all_task_priorities_work(self):
        """Test all task priorities work with model."""
        for priority in TaskPriority:
            task = Task(title=f"Task Priority {priority.value}")
            task.priority = priority
            assert task.priority == priority

    def test_all_worktree_statuses_work(self):
        """Test all worktree statuses work with model."""
        for status in WorktreeStatus:
            worktree = Worktree(
                name=f"worktree-{status.value}",
                path=f"/path/{status.value}",
                branch_name="test"
            )
            worktree.status = status
            assert worktree.status == status

    def test_all_config_scopes_work(self):
        """Test all config scopes work with model."""
        for scope in ConfigScope:
            config = Configuration(
                key=f"test.{scope.value}",
                value="test_value"
            )
            config.scope = scope
            assert config.scope == scope


class TestModelIntegration:
    """Test comprehensive model integration scenarios."""

    def test_full_instance_workflow(self):
        """Test complete instance workflow with related models."""
        # Create instance
        instance = Instance(issue_id="WORKFLOW-123")

        # Add tasks
        task1 = Task(title="Setup Environment", instance_id=1)
        task2 = Task(title="Run Tests", instance_id=1, priority=TaskPriority.HIGH)

        # Add worktree
        worktree = Worktree(
            name="workflow-worktree",
            path="/workflow/path",
            branch_name="feature/workflow",
            instance_id=1
        )

        # Add configuration
        config = Configuration(
            key="workflow.setting",
            value="enabled",
            scope=ConfigScope.INSTANCE,
            instance_id=1
        )

        # Add health check
        health_check = HealthCheck(
            instance_id=1,
            overall_status=HealthStatus.HEALTHY,
            check_results='{"all": "good"}',
            duration_ms=150,
            check_timestamp=datetime.now()
        )

        # Verify all models are properly configured
        assert instance.issue_id == "WORKFLOW-123"
        assert task1.title == "Setup Environment"
        assert task2.priority == TaskPriority.HIGH
        assert worktree.name == "workflow-worktree"
        assert config.scope == ConfigScope.INSTANCE
        assert health_check.overall_status == HealthStatus.HEALTHY

    def test_model_field_edge_cases(self):
        """Test edge cases for model fields."""
        # Very long strings (within limits)
        instance = Instance(issue_id="A" * 50)  # Max length for issue_id
        assert len(instance.issue_id) == 50

        # Empty but valid JSON
        task = Task(title="Edge Case", requirements={}, results={})
        assert task.requirements == {}
        assert task.results == {}

        # Boundary values for numeric fields
        task.estimated_duration = 0
        task.actual_duration = 999999
        assert task.estimated_duration == 0
        assert task.actual_duration == 999999

        # Boolean edge cases
        config = Configuration(key="edge.test", value="test")
        config.is_secret = True
        config.is_readonly = False
        assert config.is_secret is True
        assert config.is_readonly is False

    def test_all_model_repr_methods(self):
        """Test all model __repr__ methods work correctly."""
        # Instance
        instance = Instance(id=1, issue_id="REPR-TEST", status=InstanceStatus.RUNNING)
        instance_repr = repr(instance)
        assert "Instance" in instance_repr and "REPR-TEST" in instance_repr

        # Task
        task = Task(id=2, title="Test Task", status=TaskStatus.PENDING)
        task_repr = repr(task)
        assert "Task" in task_repr and "Test Task" in task_repr

        # Worktree
        worktree = Worktree(id=3, name="test-wt", path="/test", branch_name="main")
        worktree_repr = repr(worktree)
        assert "Worktree" in worktree_repr and "test-wt" in worktree_repr

        # HealthCheck
        health_check = HealthCheck(
            id=4, instance_id=1, overall_status=HealthStatus.HEALTHY,
            check_results='{}', duration_ms=100, check_timestamp=datetime.now()
        )
        health_check_repr = repr(health_check)
        assert "HealthCheck" in health_check_repr and "healthy" in health_check_repr

        # Configuration
        config = Configuration(id=5, key="test.key", value="test", scope=ConfigScope.GLOBAL)
        config_repr = repr(config)
        assert "Configuration" in config_repr and "test.key" in config_repr
