"""Integration tests for instance persistence across CLI commands (Issue #59)."""

import os
import tempfile

import pytest
from sqlalchemy import create_engine

from cc_orchestrator.core.orchestrator import Orchestrator
from cc_orchestrator.database.connection import DatabaseManager
from cc_orchestrator.database.models import Base


@pytest.fixture
def temp_db():
    """Create a temporary test database."""
    temp_db_file = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    temp_db_file.close()

    database_url = f"sqlite:///{temp_db_file.name}"

    # Create database with tables
    engine = create_engine(database_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)

    yield database_url, temp_db_file.name

    # Cleanup
    try:
        os.unlink(temp_db_file.name)
    except OSError:
        pass


@pytest.fixture
def db_manager(temp_db):
    """Create a database manager for testing."""
    database_url, _ = temp_db
    # Reset any global database manager first
    from cc_orchestrator.database.connection import close_database

    close_database()

    manager = DatabaseManager(database_url=database_url)
    yield manager
    manager.close()


class TestInstancePersistenceIntegration:
    """Test instance persistence across separate CLI invocations."""

    async def test_complete_user_workflow_cross_process_persistence(self, temp_db):
        """Test the complete Issue #59 workflow: create → list → stop → verify.

        This test simulates separate CLI invocations by creating fresh Orchestrator
        instances for each command, verifying state persists across process boundaries.
        """
        database_url, _ = temp_db
        issue_id = "test-issue-123"

        # Step 1: Create instance (simulate: cc-orchestrator instances start issue-123)

        # Reset the global database manager to use our test database
        from cc_orchestrator.database.connection import close_database

        close_database()

        # Force use of our test database URL
        manager1 = DatabaseManager(database_url=database_url)
        orchestrator1 = Orchestrator(db_session=manager1.create_session())
        await orchestrator1.initialize()

        instance = await orchestrator1.create_instance(
            issue_id=issue_id,
            workspace_path="/test/workspace",
            branch_name="feature/test",
            tmux_session="test-session",
        )

        assert instance.issue_id == issue_id
        assert str(instance.workspace_path) == "/test/workspace"

        await orchestrator1.cleanup()
        manager1.close()

        # Step 2: List instances (simulate: cc-orchestrator instances list - separate process)
        manager2 = DatabaseManager(database_url=database_url)
        orchestrator2 = Orchestrator(db_session=manager2.create_session())
        await orchestrator2.initialize()

        instances = orchestrator2.list_instances()
        assert len(instances) == 1
        assert instances[0].issue_id == issue_id
        assert str(instances[0].workspace_path) == "/test/workspace"
        assert instances[0].branch_name == "feature/test"
        assert instances[0].tmux_session == "test-session"

        await orchestrator2.cleanup()
        manager2.close()

        # Step 3: Get specific instance (simulate: cc-orchestrator instances status issue-123)
        manager3 = DatabaseManager(database_url=database_url)
        orchestrator3 = Orchestrator(db_session=manager3.create_session())
        await orchestrator3.initialize()

        retrieved_instance = orchestrator3.get_instance(issue_id)
        assert retrieved_instance is not None
        assert retrieved_instance.issue_id == issue_id

        await orchestrator3.cleanup()
        manager3.close()

        # Step 4: Stop instance (simulate: cc-orchestrator instances stop issue-123)
        manager4 = DatabaseManager(database_url=database_url)
        orchestrator4 = Orchestrator(db_session=manager4.create_session())
        await orchestrator4.initialize()

        success = await orchestrator4.destroy_instance(issue_id)
        assert success is True

        await orchestrator4.cleanup()
        manager4.close()

        # Step 5: Verify instance removed (simulate: cc-orchestrator instances list - separate process)
        manager5 = DatabaseManager(database_url=database_url)
        orchestrator5 = Orchestrator(db_session=manager5.create_session())
        await orchestrator5.initialize()

        final_instances = orchestrator5.list_instances()
        assert len(final_instances) == 0

        # Verify instance is also gone from get_instance
        removed_instance = orchestrator5.get_instance(issue_id)
        assert removed_instance is None

        await orchestrator5.cleanup()
        manager5.close()

    async def test_multiple_instances_cross_process_persistence(self, db_manager):
        """Test multiple instances persist across process boundaries."""

        # Create multiple instances in one "process"
        orchestrator1 = Orchestrator(db_session=db_manager.create_session())
        await orchestrator1.initialize()

        instances_to_create = ["issue-1", "issue-2", "issue-3"]
        created_instances = []

        for issue_id in instances_to_create:
            instance = await orchestrator1.create_instance(issue_id=issue_id)
            created_instances.append(instance)

        assert len(created_instances) == 3
        await orchestrator1.cleanup()

        # List instances in another "process"
        orchestrator2 = Orchestrator(db_session=db_manager.create_session())
        await orchestrator2.initialize()

        persisted_instances = orchestrator2.list_instances()
        assert len(persisted_instances) == 3

        persisted_issue_ids = {inst.issue_id for inst in persisted_instances}
        expected_issue_ids = set(instances_to_create)
        assert persisted_issue_ids == expected_issue_ids

        await orchestrator2.cleanup()

        # Remove one instance in a third "process"
        orchestrator3 = Orchestrator(db_session=db_manager.create_session())
        await orchestrator3.initialize()

        success = await orchestrator3.destroy_instance("issue-2")
        assert success is True

        await orchestrator3.cleanup()

        # Verify remaining instances in fourth "process"
        orchestrator4 = Orchestrator(db_session=db_manager.create_session())
        await orchestrator4.initialize()

        remaining_instances = orchestrator4.list_instances()
        assert len(remaining_instances) == 2

        remaining_issue_ids = {inst.issue_id for inst in remaining_instances}
        assert remaining_issue_ids == {"issue-1", "issue-3"}

        await orchestrator4.cleanup()

    async def test_instance_not_found_cross_process(self, db_manager):
        """Test handling of non-existent instances across processes."""

        # Try to get non-existent instance
        orchestrator1 = Orchestrator(db_session=db_manager.create_session())
        await orchestrator1.initialize()

        non_existent = orchestrator1.get_instance("non-existent-issue")
        assert non_existent is None

        await orchestrator1.cleanup()

        # Try to destroy non-existent instance
        orchestrator2 = Orchestrator(db_session=db_manager.create_session())
        await orchestrator2.initialize()

        success = await orchestrator2.destroy_instance("non-existent-issue")
        assert success is False

        await orchestrator2.cleanup()

    async def test_database_session_management(self, db_manager):
        """Test that database sessions are properly managed across orchestrator lifecycles."""

        # Create instance with explicit session
        session1 = db_manager.create_session()
        orchestrator1 = Orchestrator(db_session=session1)
        await orchestrator1.initialize()

        await orchestrator1.create_instance("session-test")

        # Session should be managed properly
        assert orchestrator1._db_session is session1
        assert orchestrator1._should_close_session is False  # We provided session

        await orchestrator1.cleanup()
        # Session should remain open since we provided it
        session1.close()

        # Create instance with auto-managed session
        # Set up global database manager to use test database
        from cc_orchestrator.database.connection import get_database_manager

        # Set up global database manager to use test database
        get_database_manager(database_url=db_manager.database_url, reset=True)

        orchestrator2 = Orchestrator()  # No session provided
        await orchestrator2.initialize()

        assert orchestrator2._db_session is not None
        assert (
            orchestrator2._should_close_session is True
        )  # Orchestrator created session

        instances = orchestrator2.list_instances()
        assert len(instances) == 1
        assert instances[0].issue_id == "session-test"

        await orchestrator2.cleanup()
        # Session should be closed by orchestrator

    async def test_orchestrator_initialization_states(self, db_manager):
        """Test orchestrator initialization and error states."""

        # Test uninitialized orchestrator
        orchestrator = Orchestrator(db_session=db_manager.create_session())

        # Should handle uninitialized state gracefully
        instance = orchestrator.get_instance("test")
        assert instance is None

        instances = orchestrator.list_instances()
        assert instances == []

        # Should raise error for operations requiring initialization
        with pytest.raises(RuntimeError, match="not initialized"):
            await orchestrator.create_instance("test")

        with pytest.raises(RuntimeError, match="not initialized"):
            await orchestrator.destroy_instance("test")

        # Initialize and test normal operation
        await orchestrator.initialize()

        # Now operations should work
        created_instance = await orchestrator.create_instance("init-test")
        assert created_instance.issue_id == "init-test"

        await orchestrator.cleanup()

    async def test_instance_data_integrity_across_processes(self, db_manager):
        """Test that instance data maintains integrity across process boundaries."""

        # Create instance with specific data
        orchestrator1 = Orchestrator(db_session=db_manager.create_session())
        await orchestrator1.initialize()

        original_instance = await orchestrator1.create_instance(
            issue_id="data-integrity-test",
            workspace_path="/specific/workspace/path",
            branch_name="feature/data-integrity",
            tmux_session="tmux-data-test",
            custom_field="custom_value",
        )

        original_created_at = original_instance.created_at
        await orchestrator1.cleanup()

        # Retrieve instance in different process and verify all data
        orchestrator2 = Orchestrator(db_session=db_manager.create_session())
        await orchestrator2.initialize()

        retrieved_instance = orchestrator2.get_instance("data-integrity-test")
        assert retrieved_instance is not None

        # Verify all core fields
        assert retrieved_instance.issue_id == "data-integrity-test"
        assert str(retrieved_instance.workspace_path) == "/specific/workspace/path"
        assert retrieved_instance.branch_name == "feature/data-integrity"
        assert retrieved_instance.tmux_session == "tmux-data-test"
        # Verify timestamps are close (within 1 second to handle slight timing differences)
        time_diff = abs(
            (retrieved_instance.created_at - original_created_at).total_seconds()
        )
        assert time_diff < 1.0, f"Timestamp difference too large: {time_diff}s"

        # Verify metadata is preserved
        # Note: Custom fields from kwargs go into extra_metadata in the database

        await orchestrator2.cleanup()

    async def test_concurrent_orchestrator_access(self, db_manager):
        """Test multiple orchestrators accessing the same database simultaneously."""

        # Create two orchestrators with separate sessions
        session1 = db_manager.create_session()
        session2 = db_manager.create_session()

        orchestrator1 = Orchestrator(db_session=session1)
        orchestrator2 = Orchestrator(db_session=session2)

        await orchestrator1.initialize()
        await orchestrator2.initialize()

        # Create instance in orchestrator1
        await orchestrator1.create_instance("concurrent-test-1")

        # Create instance in orchestrator2
        await orchestrator2.create_instance("concurrent-test-2")

        # Both should see both instances
        instances1 = orchestrator1.list_instances()
        instances2 = orchestrator2.list_instances()

        assert len(instances1) == 2
        assert len(instances2) == 2

        issue_ids1 = {inst.issue_id for inst in instances1}
        issue_ids2 = {inst.issue_id for inst in instances2}

        expected_ids = {"concurrent-test-1", "concurrent-test-2"}
        assert issue_ids1 == expected_ids
        assert issue_ids2 == expected_ids

        # Clean up
        await orchestrator1.cleanup()
        await orchestrator2.cleanup()

        session1.close()
        session2.close()
