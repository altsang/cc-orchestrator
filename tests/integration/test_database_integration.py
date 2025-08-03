"""Integration tests for database functionality."""

import tempfile
from pathlib import Path

import pytest
from sqlalchemy import create_engine

from cc_orchestrator.database import (
    ConfigScope,
    ConfigurationCRUD,
    DatabaseManager,
    InstanceCRUD,
    TaskCRUD,
    TaskPriority,
    TaskStatus,
    WorktreeCRUD,
)
from cc_orchestrator.database.migrations import MigrationManager
from cc_orchestrator.database.schema import (
    create_sample_data,
    get_table_counts,
    validate_schema,
)


@pytest.fixture
def temp_db_path():
    """Create a temporary database file."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)

    yield db_path

    # Cleanup
    if db_path.exists():
        db_path.unlink()


@pytest.fixture
def db_manager(temp_db_path):
    """Create a database manager with a temporary database."""
    db_url = f"sqlite:///{temp_db_path}"
    manager = DatabaseManager(database_url=db_url)
    manager.create_tables()

    yield manager

    manager.close()


class TestDatabaseManager:
    """Test DatabaseManager functionality."""

    def test_create_database_manager(self, temp_db_path):
        """Test creating a database manager."""
        db_url = f"sqlite:///{temp_db_path}"
        manager = DatabaseManager(database_url=db_url)

        assert manager.database_url == db_url
        assert manager.engine is not None
        assert manager.session_factory is not None

        manager.close()

    def test_create_tables(self, db_manager):
        """Test creating database tables."""
        # Tables should already be created by fixture
        validation = validate_schema(db_manager.engine)

        expected_tables = {"instances", "tasks", "worktrees", "configurations"}
        actual_tables = {
            table
            for table, exists in validation.items()
            if exists and table in expected_tables
        }

        assert actual_tables == expected_tables

    def test_session_context_manager(self, db_manager):
        """Test using session context manager."""
        with db_manager.get_session() as session:
            # Create an instance
            instance = InstanceCRUD.create(session=session, issue_id="test-123")
            assert instance.id is not None

        # Verify data was committed
        with db_manager.get_session() as session:
            retrieved = InstanceCRUD.get_by_issue_id(
                session=session, issue_id="test-123"
            )
            assert retrieved.issue_id == "test-123"

    def test_session_rollback_on_error(self, db_manager):
        """Test session rollback on error."""
        try:
            with db_manager.get_session() as session:
                # Create an instance
                InstanceCRUD.create(session=session, issue_id="test-456")
                # Force an error
                raise ValueError("Test error")
        except ValueError:
            pass

        # Verify data was rolled back
        with db_manager.get_session() as session:
            from cc_orchestrator.database.crud import NotFoundError

            with pytest.raises(NotFoundError):
                InstanceCRUD.get_by_issue_id(session=session, issue_id="test-456")


class TestMigrationSystem:
    """Test migration system functionality."""

    def test_migration_manager_creation(self, temp_db_path):
        """Test creating a migration manager."""
        db_url = f"sqlite:///{temp_db_path}"
        engine = create_engine(db_url)

        migration_manager = MigrationManager(engine)
        assert migration_manager.engine == engine
        assert migration_manager.migrations_dir is not None

    def test_migration_table_creation(self, temp_db_path):
        """Test that migration tracking table is created."""
        db_url = f"sqlite:///{temp_db_path}"
        engine = create_engine(db_url)

        MigrationManager(engine)

        # Check that schema_migrations table exists
        from sqlalchemy import inspect

        inspector = inspect(engine)
        table_names = inspector.get_table_names()

        assert "schema_migrations" in table_names

    def test_initial_migration_discovery(self, temp_db_path):
        """Test discovering the initial migration."""
        db_url = f"sqlite:///{temp_db_path}"
        engine = create_engine(db_url)

        migration_manager = MigrationManager(engine)
        migrations = migration_manager.discover_migrations()

        # Should find at least the initial migration
        assert len(migrations) >= 1

        # Check the initial migration
        initial_migration = next((m for m in migrations if m.version == "001"), None)
        assert initial_migration is not None
        assert "initial schema" in initial_migration.description.lower()

    def test_migration_up(self, temp_db_path):
        """Test applying migrations."""
        db_url = f"sqlite:///{temp_db_path}"
        engine = create_engine(db_url)

        migration_manager = MigrationManager(engine)

        # Apply all migrations
        success = migration_manager.migrate_up()
        assert success is True

        # Check that tables were created
        validation = validate_schema(engine)
        expected_tables = {"instances", "tasks", "worktrees", "configurations"}
        actual_tables = {
            table
            for table, exists in validation.items()
            if exists and table in expected_tables
        }

        assert actual_tables == expected_tables

        # Check migration records
        applied = migration_manager.get_applied_migrations()
        assert len(applied) >= 1
        assert applied[0].version == "001"

    def test_migration_status(self, temp_db_path):
        """Test getting migration status."""
        db_url = f"sqlite:///{temp_db_path}"
        engine = create_engine(db_url)

        migration_manager = MigrationManager(engine)

        # Before migration
        status = migration_manager.get_migration_status()
        assert status["current_version"] is None
        assert status["applied_count"] == 0
        assert status["pending_count"] >= 1

        # After migration
        migration_manager.migrate_up()
        status = migration_manager.get_migration_status()
        assert status["current_version"] == "001"
        assert status["applied_count"] >= 1
        assert status["pending_count"] == 0


class TestCompleteWorkflow:
    """Test complete database workflows."""

    def test_instance_with_tasks_and_worktree(self, db_manager):
        """Test creating an instance with related tasks and worktree."""
        with db_manager.get_session() as session:
            # Create instance
            instance = InstanceCRUD.create(
                session=session,
                issue_id="workflow-test",
                workspace_path="/tmp/workflow-test",
                branch_name="feature/workflow-test",
            )

            # Create worktree
            worktree = WorktreeCRUD.create(
                session=session,
                name="workflow-worktree",
                path="/tmp/workflow-test",
                branch_name="feature/workflow-test",
                instance_id=instance.id,
            )

            # Create tasks
            TaskCRUD.create(
                session=session,
                title="Setup environment",
                priority=TaskPriority.HIGH,
                instance_id=instance.id,
                worktree_id=worktree.id,
            )

            TaskCRUD.create(
                session=session,
                title="Implement feature",
                priority=TaskPriority.MEDIUM,
                instance_id=instance.id,
                worktree_id=worktree.id,
            )

            TaskCRUD.create(
                session=session,
                title="Write tests",
                priority=TaskPriority.MEDIUM,
                instance_id=instance.id,
                worktree_id=worktree.id,
            )

        # Verify relationships
        with db_manager.get_session() as session:
            retrieved_instance = InstanceCRUD.get_by_issue_id(
                session=session, issue_id="workflow-test"
            )

            # Check instance has worktree
            assert retrieved_instance.worktree is not None
            assert retrieved_instance.worktree.name == "workflow-worktree"

            # Check instance has tasks
            assert len(retrieved_instance.tasks) == 3

            # Check tasks are properly ordered by priority
            instance_tasks = TaskCRUD.list_by_instance(
                session=session, instance_id=retrieved_instance.id
            )
            assert instance_tasks[0].priority == TaskPriority.HIGH
            assert instance_tasks[0].title == "Setup environment"

    def test_task_status_workflow(self, db_manager):
        """Test task status progression workflow."""
        with db_manager.get_session() as session:
            # Create instance and task
            instance = InstanceCRUD.create(session=session, issue_id="status-test")
            task = TaskCRUD.create(
                session=session,
                title="Status workflow test",
                instance_id=instance.id,
            )

            # Initially pending
            assert task.status == TaskStatus.PENDING
            assert task.started_at is None
            assert task.completed_at is None

            # Start task
            TaskCRUD.update_status(
                session=session, task_id=task.id, status=TaskStatus.IN_PROGRESS
            )
            assert task.status == TaskStatus.IN_PROGRESS
            assert task.started_at is not None

            # Complete task
            TaskCRUD.update_status(
                session=session, task_id=task.id, status=TaskStatus.COMPLETED
            )
            assert task.status == TaskStatus.COMPLETED
            assert task.completed_at is not None
            assert task.actual_duration is not None

    def test_configuration_hierarchy(self, db_manager):
        """Test configuration value hierarchy."""
        with db_manager.get_session() as session:
            # Create instance
            instance = InstanceCRUD.create(session=session, issue_id="config-test")

            # Create configurations at different scopes
            ConfigurationCRUD.create(
                session=session,
                key="test.timeout",
                value="3600",
                scope=ConfigScope.GLOBAL,
                description="Global timeout setting",
            )

            ConfigurationCRUD.create(
                session=session,
                key="test.timeout",
                value="1800",
                scope=ConfigScope.USER,
                description="User timeout setting",
            )

            ConfigurationCRUD.create(
                session=session,
                key="test.timeout",
                value="900",
                scope=ConfigScope.INSTANCE,
                instance_id=instance.id,
                description="Instance timeout setting",
            )

            # Test hierarchy
            global_value = ConfigurationCRUD.get_value(
                session=session,
                key="test.timeout",
                scope=ConfigScope.GLOBAL,
            )
            assert global_value == "3600"

            user_value = ConfigurationCRUD.get_value(
                session=session,
                key="test.timeout",
                scope=ConfigScope.USER,
            )
            assert user_value == "1800"  # User overrides global

            instance_value = ConfigurationCRUD.get_value(
                session=session,
                key="test.timeout",
                scope=ConfigScope.INSTANCE,
                instance_id=instance.id,
            )
            assert instance_value == "900"  # Instance overrides all

    def test_sample_data_creation(self, db_manager):
        """Test creating sample data."""
        # Create sample data
        create_sample_data(db_manager.engine)

        # Verify data was created
        counts = get_table_counts(db_manager.engine)

        assert counts["instances"] >= 1
        assert counts["tasks"] >= 1
        assert counts["worktrees"] >= 1
        assert counts["configurations"] >= 1

        # Verify relationships work
        with db_manager.get_session() as session:
            instances = InstanceCRUD.list_all(session=session)
            assert len(instances) >= 1

            # Check that instance has related data
            instance = instances[0]
            assert instance.worktree is not None
            assert len(instance.tasks) >= 1

    def test_cascade_deletion(self, db_manager):
        """Test that deleting an instance cascades to related entities."""
        with db_manager.get_session() as session:
            # Create instance with related data
            instance = InstanceCRUD.create(session=session, issue_id="cascade-test")

            worktree = WorktreeCRUD.create(
                session=session,
                name="cascade-worktree",
                path="/tmp/cascade-test",
                branch_name="main",
                instance_id=instance.id,
            )

            task1 = TaskCRUD.create(
                session=session,
                title="Task 1",
                instance_id=instance.id,
                worktree_id=worktree.id,
            )

            task2 = TaskCRUD.create(
                session=session,
                title="Task 2",
                instance_id=instance.id,
                worktree_id=worktree.id,
            )

            # Verify data exists
            assert (
                len(TaskCRUD.list_by_instance(session=session, instance_id=instance.id))
                == 2
            )

            # Capture IDs before deleting
            instance_id = instance.id
            task1_id = task1.id
            task2_id = task2.id
            worktree_id = worktree.id

            # Delete instance
            InstanceCRUD.delete(session=session, instance_id=instance.id)

        # Verify cascaded deletion
        with db_manager.get_session() as session:
            from cc_orchestrator.database.crud import NotFoundError

            # Instance should be gone
            with pytest.raises(NotFoundError):
                InstanceCRUD.get_by_id(session=session, instance_id=instance_id)

            # Tasks should be gone (cascade delete)
            with pytest.raises(NotFoundError):
                TaskCRUD.get_by_id(session=session, task_id=task1_id)

            with pytest.raises(NotFoundError):
                TaskCRUD.get_by_id(session=session, task_id=task2_id)

            # Worktree should still exist (not cascade deleted)
            retrieved_worktree = WorktreeCRUD.get_by_path(
                session=session, path="/tmp/cascade-test"
            )
            assert retrieved_worktree.id == worktree_id
            assert retrieved_worktree.instance_id is None  # Should be unlinked
