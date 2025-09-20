"""Tests for error recovery fixes in orchestrator (addressing PR #60 review comments)."""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from cc_orchestrator.core.enums import InstanceStatus
from cc_orchestrator.core.instance import ClaudeInstance
from cc_orchestrator.core.orchestrator import Orchestrator
from cc_orchestrator.database.crud import InstanceCRUD


class TestCreateInstanceErrorRecovery:
    """Test error recovery in create_instance method."""

    async def test_create_instance_database_failure_cleanup(self, temp_db):
        """Test that resources are cleaned up when database persistence fails."""
        database_url, _ = temp_db

        # Reset any global database manager first
        from cc_orchestrator.database.connection import close_database
        close_database()

        from cc_orchestrator.database.connection import DatabaseManager
        manager = DatabaseManager(database_url=database_url)
        orchestrator = Orchestrator(db_session=manager.create_session())
        await orchestrator.initialize()

        # Mock database failure after instance initialization
        with patch.object(InstanceCRUD, 'create') as mock_create:
            mock_create.side_effect = Exception("Database connection lost")

            # Mock instance to verify cleanup is called
            with patch('cc_orchestrator.core.instance.ClaudeInstance') as mock_instance_class:
                mock_instance = Mock()
                mock_instance.initialize = AsyncMock()
                mock_instance.cleanup = AsyncMock()
                mock_instance.issue_id = "test-issue"
                mock_instance_class.return_value = mock_instance

                # Should raise exception and call cleanup
                with pytest.raises(Exception, match="Database connection lost"):
                    await orchestrator.create_instance("test-issue")

                # Verify cleanup was called after database failure
                mock_instance.cleanup.assert_called_once()

        await orchestrator.cleanup()
        manager.close()

    async def test_create_instance_cleanup_failure_logged(self, temp_db):
        """Test that cleanup failures during error recovery are properly logged."""
        database_url, _ = temp_db

        from cc_orchestrator.database.connection import close_database
        close_database()

        from cc_orchestrator.database.connection import DatabaseManager
        manager = DatabaseManager(database_url=database_url)
        orchestrator = Orchestrator(db_session=manager.create_session())
        await orchestrator.initialize()

        # Mock both database failure and cleanup failure
        with patch.object(InstanceCRUD, 'create') as mock_create, \
             patch('cc_orchestrator.core.instance.ClaudeInstance') as mock_instance_class:

            mock_create.side_effect = Exception("Database connection lost")

            mock_instance = Mock()
            mock_instance.initialize = AsyncMock()
            mock_instance.cleanup = AsyncMock(side_effect=Exception("Cleanup failed"))
            mock_instance.issue_id = "test-issue"
            mock_instance_class.return_value = mock_instance

            # Should still raise the original database exception
            with pytest.raises(Exception, match="Database connection lost"):
                await orchestrator.create_instance("test-issue")

            # Verify cleanup was attempted despite failure
            mock_instance.cleanup.assert_called_once()

        await orchestrator.cleanup()
        manager.close()


class TestDestroyInstanceErrorRecovery:
    """Test error recovery in destroy_instance method."""

    async def test_destroy_instance_database_first_order(self, temp_db):
        """Test that database deletion happens before resource cleanup (correct order)."""
        database_url, _ = temp_db

        from cc_orchestrator.database.connection import close_database
        close_database()

        from cc_orchestrator.database.connection import DatabaseManager
        manager = DatabaseManager(database_url=database_url)
        orchestrator = Orchestrator(db_session=manager.create_session())
        await orchestrator.initialize()

        # Create instance first
        await orchestrator.create_instance("test-issue")

        # Track order of operations
        call_order = []

        with patch.object(InstanceCRUD, 'delete') as mock_delete, \
             patch.object(ClaudeInstance, 'cleanup') as mock_cleanup:

            def track_delete(*args, **kwargs):
                call_order.append("database_delete")

            def track_cleanup(*args, **kwargs):
                call_order.append("resource_cleanup")
                return AsyncMock()()

            mock_delete.side_effect = track_delete
            mock_cleanup.side_effect = track_cleanup

            # Destroy instance
            result = await orchestrator.destroy_instance("test-issue")

            # Verify correct order: database deletion BEFORE resource cleanup
            assert result is True
            assert call_order == ["database_delete", "resource_cleanup"]

        await orchestrator.cleanup()
        manager.close()

    async def test_destroy_instance_database_consistency_on_cleanup_failure(self, temp_db):
        """Test database consistency when resource cleanup fails."""
        database_url, _ = temp_db

        from cc_orchestrator.database.connection import close_database
        close_database()

        from cc_orchestrator.database.connection import DatabaseManager
        manager = DatabaseManager(database_url=database_url)
        orchestrator = Orchestrator(db_session=manager.create_session())
        await orchestrator.initialize()

        # Create instance first
        await orchestrator.create_instance("test-issue")

        # Mock cleanup failure (but database deletion succeeds)
        with patch.object(ClaudeInstance, 'cleanup') as mock_cleanup:
            mock_cleanup.side_effect = Exception("Cleanup failed")

            # Destroy should still succeed (database consistency prioritized)
            result = await orchestrator.destroy_instance("test-issue")

            # Database should be consistent (instance removed)
            remaining = orchestrator.list_instances()
            assert len(remaining) == 0
            assert result is True  # Destruction succeeded despite cleanup failure

        await orchestrator.cleanup()
        manager.close()

    async def test_destroy_instance_database_failure_rollback(self, temp_db):
        """Test that database rollback works when deletion fails."""
        database_url, _ = temp_db

        from cc_orchestrator.database.connection import close_database
        close_database()

        from cc_orchestrator.database.connection import DatabaseManager
        manager = DatabaseManager(database_url=database_url)
        orchestrator = Orchestrator(db_session=manager.create_session())
        await orchestrator.initialize()

        # Create instance first
        await orchestrator.create_instance("test-issue")

        # Mock database deletion failure
        with patch.object(InstanceCRUD, 'delete') as mock_delete:
            mock_delete.side_effect = Exception("Database deletion failed")

            # Destroy should fail
            result = await orchestrator.destroy_instance("test-issue")

            # Database should still contain the instance (rollback successful)
            remaining = orchestrator.list_instances()
            assert len(remaining) == 1
            assert remaining[0].issue_id == "test-issue"
            assert result is False  # Destruction failed

        await orchestrator.cleanup()
        manager.close()


class TestHealthMonitorIntegration:
    """Test health monitor integration for database-loaded instances."""

    async def test_health_monitor_registration_for_running_instances(self, temp_db):
        """Test that RUNNING instances loaded from database are registered with health monitor."""
        database_url, _ = temp_db

        from cc_orchestrator.database.connection import close_database
        close_database()

        from cc_orchestrator.database.connection import DatabaseManager
        manager = DatabaseManager(database_url=database_url)
        orchestrator = Orchestrator(db_session=manager.create_session())
        await orchestrator.initialize()

        # Create an instance and manually set it to RUNNING in database
        await orchestrator.create_instance("test-issue")

        # Update database to mark instance as RUNNING
        from cc_orchestrator.database.models import Instance
        db_instance = orchestrator._db_session.query(Instance).filter_by(issue_id="test-issue").first()
        db_instance.status = InstanceStatus.RUNNING
        db_instance.process_id = 12345
        orchestrator._db_session.commit()

        # Mock health monitor
        with patch.object(orchestrator.health_monitor, 'register_instance') as mock_register:
            # Load instance from database (should trigger health monitor registration)
            orchestrator.get_instance("test-issue")

            # Verify health monitor registration was called
            mock_register.assert_called_once()
            call_args = mock_register.call_args[0]
            assert call_args[0].issue_id == "test-issue"
            assert call_args[0].status == InstanceStatus.RUNNING

        await orchestrator.cleanup()
        manager.close()

    async def test_health_monitor_registration_skipped_for_stopped_instances(self, temp_db):
        """Test that STOPPED instances are not registered with health monitor."""
        database_url, _ = temp_db

        from cc_orchestrator.database.connection import close_database
        close_database()

        from cc_orchestrator.database.connection import DatabaseManager
        manager = DatabaseManager(database_url=database_url)
        orchestrator = Orchestrator(db_session=manager.create_session())
        await orchestrator.initialize()

        # Create instance (defaults to STOPPED after initialization)
        await orchestrator.create_instance("test-issue")

        # Mock health monitor
        with patch.object(orchestrator.health_monitor, 'register_instance') as mock_register:
            # Load instance from database
            orchestrator.get_instance("test-issue")

            # Verify health monitor registration was NOT called for STOPPED instance
            mock_register.assert_not_called()

        await orchestrator.cleanup()
        manager.close()

    async def test_health_monitor_registration_failure_handled(self, temp_db):
        """Test that health monitor registration failures are handled gracefully."""
        database_url, _ = temp_db

        from cc_orchestrator.database.connection import close_database
        close_database()

        from cc_orchestrator.database.connection import DatabaseManager
        manager = DatabaseManager(database_url=database_url)
        orchestrator = Orchestrator(db_session=manager.create_session())
        await orchestrator.initialize()

        # Create a RUNNING instance
        await orchestrator.create_instance("test-issue")

        # Update database to mark instance as RUNNING
        from cc_orchestrator.database.models import Instance
        db_instance = orchestrator._db_session.query(Instance).filter_by(issue_id="test-issue").first()
        db_instance.status = InstanceStatus.RUNNING
        orchestrator._db_session.commit()

        # Mock health monitor to fail
        with patch.object(orchestrator.health_monitor, 'register_instance') as mock_register:
            mock_register.side_effect = Exception("Health monitor failure")

            # Load instance should succeed despite health monitor failure
            loaded_instance = orchestrator.get_instance("test-issue")

            # Verify instance was still loaded successfully
            assert loaded_instance is not None
            assert loaded_instance.issue_id == "test-issue"
            assert loaded_instance.status == InstanceStatus.RUNNING

        await orchestrator.cleanup()
        manager.close()


class TestEnumSynchronizationValidation:
    """Test that enum synchronization is maintained."""

    def test_instance_status_enum_consistency(self):
        """Test that InstanceStatus enum is consistent across modules."""
        from cc_orchestrator.core.enums import InstanceStatus as CoreInstanceStatus
        from cc_orchestrator.database.models import InstanceStatus as DBInstanceStatus

        # They should be the same object (imported from core)
        assert CoreInstanceStatus is DBInstanceStatus

        # Verify all expected status values exist
        expected_statuses = {"INITIALIZING", "RUNNING", "STOPPED", "ERROR"}
        actual_statuses = set(CoreInstanceStatus.__members__.keys())
        assert actual_statuses == expected_statuses

    def test_instance_state_backward_compatibility(self):
        """Test that InstanceState alias works for backward compatibility."""
        from cc_orchestrator.core.enums import InstanceState, InstanceStatus

        # InstanceState should be an alias for InstanceStatus
        assert InstanceState is InstanceStatus
        assert InstanceState.RUNNING == InstanceStatus.RUNNING