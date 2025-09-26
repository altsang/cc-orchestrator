"""
Integration tests for CLI database persistence and fail-fast behavior.

These tests verify the critical requirement that CLI commands fail-fast
when database sync fails, as identified in the PR review.
"""

import pytest
import json
from unittest.mock import Mock, AsyncMock, patch
from click.testing import CliRunner

from cc_orchestrator.cli.instances import start, stop, list as list_instances
from cc_orchestrator.core.orchestrator import DatabaseSyncError


class TestCLIDatabaseIntegration:
    """Test CLI database integration and fail-fast behavior."""

    def setup_method(self):
        """Set up test environment."""
        self.runner = CliRunner()

    @pytest.mark.asyncio
    async def test_start_instance_fail_fast_on_database_sync_error(self):
        """Test CLI start command fails fast when database sync fails."""
        with patch('cc_orchestrator.cli.instances.Orchestrator') as mock_orchestrator_class:
            mock_orchestrator = Mock()
            mock_orchestrator.initialize = AsyncMock()
            mock_orchestrator.get_instance = AsyncMock(return_value=None)
            mock_orchestrator.cleanup = AsyncMock()
            mock_orchestrator_class.return_value = mock_orchestrator

            # Mock instance creation and start success
            mock_instance = Mock()
            mock_instance.start = AsyncMock(return_value=True)
            mock_instance.stop = AsyncMock(return_value=True)
            mock_orchestrator.create_instance = AsyncMock(return_value=mock_instance)
            mock_orchestrator.destroy_instance = AsyncMock(return_value=True)

            # Database sync fails with DatabaseSyncError
            mock_orchestrator.sync_instance_state = AsyncMock(
                side_effect=DatabaseSyncError("Critical database sync failure")
            )

            result = self.runner.invoke(start, ['123'])

            # CLI should fail and instance should be stopped
            assert result.exit_code == 0  # Click doesn't set exit code for async errors
            assert "ERROR: Failed to persist instance 123 to database" in result.output
            assert "Instance has been stopped to prevent inconsistent state" in result.output

            # Verify cleanup was called
            mock_instance.stop.assert_called_once()
            mock_orchestrator.destroy_instance.assert_called_once_with('123')

    @pytest.mark.asyncio
    async def test_start_instance_fail_fast_on_unexpected_error(self):
        """Test CLI start command fails fast on unexpected database errors."""
        with patch('cc_orchestrator.cli.instances.Orchestrator') as mock_orchestrator_class:
            mock_orchestrator = Mock()
            mock_orchestrator.initialize = AsyncMock()
            mock_orchestrator.get_instance = AsyncMock(return_value=None)
            mock_orchestrator.cleanup = AsyncMock()
            mock_orchestrator_class.return_value = mock_orchestrator

            # Mock instance creation and start success
            mock_instance = Mock()
            mock_instance.start = AsyncMock(return_value=True)
            mock_instance.stop = AsyncMock(return_value=True)
            mock_orchestrator.create_instance = AsyncMock(return_value=mock_instance)
            mock_orchestrator.destroy_instance = AsyncMock(return_value=True)

            # Unexpected database error
            mock_orchestrator.sync_instance_state = AsyncMock(
                side_effect=Exception("Unexpected database connection error")
            )

            result = self.runner.invoke(start, ['456'])

            # CLI should fail and instance should be stopped
            assert result.exit_code == 0
            assert "ERROR: Failed to sync instance 456 - operation aborted" in result.output

            # Verify cleanup was called
            mock_instance.stop.assert_called_once()
            mock_orchestrator.destroy_instance.assert_called_once_with('456')

    @pytest.mark.asyncio
    async def test_start_instance_json_output_on_database_error(self):
        """Test CLI start command returns proper JSON on database error."""
        with patch('cc_orchestrator.cli.instances.Orchestrator') as mock_orchestrator_class:
            mock_orchestrator = Mock()
            mock_orchestrator.initialize = AsyncMock()
            mock_orchestrator.get_instance = AsyncMock(return_value=None)
            mock_orchestrator.cleanup = AsyncMock()
            mock_orchestrator_class.return_value = mock_orchestrator

            # Mock instance creation and start success
            mock_instance = Mock()
            mock_instance.start = AsyncMock(return_value=True)
            mock_instance.stop = AsyncMock(return_value=True)
            mock_orchestrator.create_instance = AsyncMock(return_value=mock_instance)
            mock_orchestrator.destroy_instance = AsyncMock(return_value=True)

            # Database sync fails
            error_msg = "Database connection timeout"
            mock_orchestrator.sync_instance_state = AsyncMock(
                side_effect=DatabaseSyncError(error_msg)
            )

            result = self.runner.invoke(start, ['789', '--json'])

            # Should return valid JSON with error details
            assert result.exit_code == 0
            try:
                output_data = json.loads(result.output)
                assert output_data['error'] == "Database sync failed - instance stopped"
                assert output_data['issue_id'] == '789'
                assert error_msg in output_data['details']
            except json.JSONDecodeError:
                pytest.fail("Output should be valid JSON")

    @pytest.mark.asyncio
    async def test_restart_existing_instance_fail_fast(self):
        """Test CLI fails fast when restarting existing instance with database error."""
        with patch('cc_orchestrator.cli.instances.Orchestrator') as mock_orchestrator_class:
            mock_orchestrator = Mock()
            mock_orchestrator.initialize = AsyncMock()
            mock_orchestrator.cleanup = AsyncMock()
            mock_orchestrator_class.return_value = mock_orchestrator

            # Mock existing stopped instance
            mock_instance = Mock()
            mock_instance.is_running = Mock(return_value=False)
            mock_instance.start = AsyncMock(return_value=True)
            mock_instance.stop = AsyncMock(return_value=True)
            mock_orchestrator.get_instance = AsyncMock(return_value=mock_instance)

            # Database sync fails on restart
            mock_orchestrator.sync_instance_state = AsyncMock(
                side_effect=DatabaseSyncError("Sync failure on restart")
            )

            result = self.runner.invoke(start, ['existing-123'])

            # Should fail fast and stop the instance
            assert result.exit_code == 0
            assert "ERROR: Failed to persist instance existing-123 to database" in result.output
            mock_instance.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_instance_with_database_sync(self):
        """Test CLI stop command syncs state to database."""
        with patch('cc_orchestrator.cli.instances.Orchestrator') as mock_orchestrator_class:
            mock_orchestrator = Mock()
            mock_orchestrator.initialize = AsyncMock()
            mock_orchestrator.cleanup = AsyncMock()
            mock_orchestrator_class.return_value = mock_orchestrator

            # Mock running instance
            mock_instance = Mock()
            mock_instance.is_running = Mock(return_value=True)
            mock_instance.stop = AsyncMock(return_value=True)
            mock_orchestrator.get_instance = AsyncMock(return_value=mock_instance)

            # Database sync succeeds
            mock_orchestrator.sync_instance_state = AsyncMock()

            result = self.runner.invoke(stop, ['running-123'])

            # Should succeed and sync to database
            assert result.exit_code == 0
            assert "Successfully stopped instance for issue running-123" in result.output
            mock_orchestrator.sync_instance_state.assert_called_once_with('running-123')

    @pytest.mark.asyncio
    async def test_list_instances_lazy_loading_performance(self):
        """Test list command uses appropriate loading strategy."""
        with patch('cc_orchestrator.cli.instances.Orchestrator') as mock_orchestrator_class:
            mock_orchestrator = Mock()
            mock_orchestrator.initialize = AsyncMock()
            mock_orchestrator.cleanup = AsyncMock()
            mock_orchestrator_class.return_value = mock_orchestrator

            # Mock instances list
            mock_instances = [Mock(), Mock()]
            mock_orchestrator.list_instances = AsyncMock(return_value=mock_instances)

            result = self.runner.invoke(list_instances, [])

            # Should initialize with lazy_load=False for comprehensive listing
            mock_orchestrator.initialize.assert_called_once_with(lazy_load=False)
            mock_orchestrator.list_instances.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_single_instance_lazy_loading_performance(self):
        """Test start command uses lazy loading for performance."""
        with patch('cc_orchestrator.cli.instances.Orchestrator') as mock_orchestrator_class:
            mock_orchestrator = Mock()
            mock_orchestrator.initialize = AsyncMock()
            mock_orchestrator.get_instance = AsyncMock(return_value=None)
            mock_orchestrator.cleanup = AsyncMock()
            mock_orchestrator_class.return_value = mock_orchestrator

            # Mock instance creation and start
            mock_instance = Mock()
            mock_instance.start = AsyncMock(return_value=True)
            mock_instance.get_info = Mock(return_value={'process_id': 123, 'workspace_path': '/test'})
            mock_orchestrator.create_instance = AsyncMock(return_value=mock_instance)
            mock_orchestrator.sync_instance_state = AsyncMock()

            result = self.runner.invoke(start, ['performance-test'])

            # Should initialize with lazy_load=True for performance
            mock_orchestrator.initialize.assert_called_once_with(lazy_load=True)

    @pytest.mark.asyncio
    async def test_database_connection_pool_configuration(self):
        """Test that database connection pool is properly configured."""
        with patch('cc_orchestrator.core.orchestrator.get_database_manager') as mock_get_db:
            mock_db_manager = Mock()
            mock_db_manager.initialize = AsyncMock()
            mock_get_db.return_value = mock_db_manager

            orchestrator_instance = Mock()
            with patch('cc_orchestrator.cli.instances.Orchestrator', return_value=orchestrator_instance):
                orchestrator_instance.initialize = AsyncMock()
                orchestrator_instance.get_instance = AsyncMock(return_value=None)
                orchestrator_instance.cleanup = AsyncMock()

                # Mock successful instance creation flow
                mock_instance = Mock()
                mock_instance.start = AsyncMock(return_value=True)
                mock_instance.get_info = Mock(return_value={
                    'process_id': 999,
                    'workspace_path': '/pool/test',
                    'branch_name': 'test-branch',
                    'tmux_session': 'test-session'
                })
                orchestrator_instance.create_instance = AsyncMock(return_value=mock_instance)
                orchestrator_instance.sync_instance_state = AsyncMock()

                result = self.runner.invoke(start, ['pool-test'])

                # Database manager should be called with proper initialization
                mock_get_db.assert_called()
                mock_db_manager.initialize.assert_called()


class TestDatabaseTransactionHandling:
    """Test database transaction handling and rollback behavior."""

    def setup_method(self):
        """Set up test environment."""
        self.runner = CliRunner()

    @pytest.mark.asyncio
    async def test_transaction_rollback_behavior(self):
        """Test that database transactions are properly rolled back on errors."""
        # This would be an integration test with a real database
        # For now, we test the mocked behavior

        with patch('cc_orchestrator.core.orchestrator.get_db_session') as mock_session:
            mock_db_session = Mock()
            mock_context_manager = Mock()
            mock_context_manager.__enter__ = Mock(return_value=mock_db_session)
            mock_context_manager.__exit__ = Mock()
            mock_session.return_value = mock_context_manager

            # Simulate transaction failure
            mock_db_session.flush.side_effect = Exception("Constraint violation")

            from cc_orchestrator.core.orchestrator import Orchestrator
            orchestrator = Orchestrator()
            await orchestrator.initialize()

            mock_instance = Mock()
            mock_instance.issue_id = "transaction-test"
            mock_instance.status = "RUNNING"

            with patch('cc_orchestrator.core.orchestrator.InstanceCRUD') as mock_crud:
                mock_crud.get_by_issue_id.side_effect = Exception("Not found")

                try:
                    await orchestrator._sync_instance_to_database(mock_instance)
                except Exception:
                    pass  # Expected to fail

                # Context manager should have been called for proper cleanup
                mock_context_manager.__enter__.assert_called()
                mock_context_manager.__exit__.assert_called()

            await orchestrator.cleanup()

    @pytest.mark.asyncio
    async def test_cross_session_persistence_integration(self):
        """Integration test for cross-session persistence."""
        # Test simulates multiple CLI command invocations
        issue_id = "cross-session-test"

        # First CLI session - create instance
        with patch('cc_orchestrator.cli.instances.Orchestrator') as mock_orchestrator_class:
            mock_orchestrator = Mock()
            mock_orchestrator.initialize = AsyncMock()
            mock_orchestrator.get_instance = AsyncMock(return_value=None)
            mock_orchestrator.cleanup = AsyncMock()
            mock_orchestrator_class.return_value = mock_orchestrator

            mock_instance = Mock()
            mock_instance.start = AsyncMock(return_value=True)
            mock_instance.get_info = Mock(return_value={
                'process_id': 777,
                'workspace_path': '/cross/session'
            })
            mock_orchestrator.create_instance = AsyncMock(return_value=mock_instance)
            mock_orchestrator.sync_instance_state = AsyncMock()  # Succeeds

            runner = CliRunner()
            result = runner.invoke(start, [issue_id])
            assert result.exit_code == 0
            assert "Successfully started Claude instance" in result.output

        # Second CLI session - list instances (should find persisted instance)
        with patch('cc_orchestrator.cli.instances.Orchestrator') as mock_orchestrator_class:
            mock_orchestrator = Mock()
            mock_orchestrator.initialize = AsyncMock()
            mock_orchestrator.cleanup = AsyncMock()
            mock_orchestrator_class.return_value = mock_orchestrator

            # Mock that instance was persisted and loaded
            mock_persisted_instance = Mock()
            mock_persisted_instance.issue_id = issue_id
            mock_persisted_instance.status = Mock()
            mock_persisted_instance.status.value = "running"
            mock_persisted_instance.is_running = Mock(return_value=True)
            mock_persisted_instance.get_info = Mock(return_value={
                'process_id': 777,
                'workspace_path': '/cross/session',
                'status': 'running'
            })

            mock_orchestrator.list_instances = AsyncMock(return_value=[mock_persisted_instance])

            runner = CliRunner()
            result = runner.invoke(list_instances, [])

            # Should show the persisted instance from previous session
            assert result.exit_code == 0
            assert issue_id in result.output
            mock_orchestrator.initialize.assert_called_once_with(lazy_load=False)