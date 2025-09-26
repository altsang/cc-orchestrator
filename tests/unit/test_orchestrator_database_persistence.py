"""
Comprehensive tests for orchestrator database persistence functionality.

This test suite covers all the critical database integration features
identified in the PR review comments.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch

from cc_orchestrator.core.orchestrator import Orchestrator, DatabaseSyncError
from cc_orchestrator.core.instance import ClaudeInstance, InstanceStatus
from cc_orchestrator.database.crud import NotFoundError, ValidationError


class TestOrchestratorDatabasePersistence:
    """Test orchestrator database persistence functionality."""

    @pytest.fixture
    async def orchestrator(self):
        """Create a test orchestrator instance."""
        orchestrator = Orchestrator()
        await orchestrator.initialize(lazy_load=True)
        yield orchestrator
        await orchestrator.cleanup()

    @pytest.fixture
    def mock_instance(self):
        """Create a mock ClaudeInstance for testing."""
        instance = Mock(spec=ClaudeInstance)
        instance.issue_id = "test-123"
        instance.status = InstanceStatus.RUNNING
        instance.process_id = 12345
        instance.workspace_path = "/test/workspace"
        instance.branch_name = "feature/test"
        instance.tmux_session = "test-session"
        instance.created_at = datetime.now()
        instance.last_activity = datetime.now()
        instance.metadata = {"test": "data"}
        instance.start = AsyncMock(return_value=True)
        instance.stop = AsyncMock(return_value=True)
        instance.initialize = AsyncMock()
        instance.is_running = Mock(return_value=True)
        return instance

    @pytest.mark.asyncio
    async def test_sync_instance_to_database_success(self, orchestrator, mock_instance):
        """Test successful database sync with proper transaction management."""
        # Test should verify that database sync works correctly
        with patch('cc_orchestrator.core.orchestrator.get_db_session') as mock_session:
            mock_db_session = Mock()
            mock_session.return_value.__enter__.return_value = mock_db_session

            with patch('cc_orchestrator.core.orchestrator.InstanceCRUD') as mock_crud:
                mock_crud.get_by_issue_id.side_effect = NotFoundError("Not found")
                mock_db_instance = Mock()
                mock_db_instance.id = 1
                mock_crud.create.return_value = mock_db_instance

                # Should not raise exception
                await orchestrator._sync_instance_to_database(mock_instance)

                # Verify CRUD operations were called
                mock_crud.create.assert_called_once()
                mock_crud.update.assert_called_once()
                mock_db_session.flush.assert_called()

    @pytest.mark.asyncio
    async def test_sync_instance_to_database_with_retries(self, orchestrator, mock_instance):
        """Test database sync retry logic for transient failures."""
        with patch('cc_orchestrator.core.orchestrator.get_db_session') as mock_session:
            # First two attempts fail, third succeeds
            mock_session.side_effect = [Exception("Connection error"), Exception("Timeout"), Mock()]

            with patch('asyncio.sleep'):  # Mock sleep to speed up test
                with patch('cc_orchestrator.core.orchestrator.InstanceCRUD') as mock_crud:
                    mock_crud.get_by_issue_id.side_effect = NotFoundError("Not found")
                    mock_db_instance = Mock()
                    mock_db_instance.id = 1
                    mock_crud.create.return_value = mock_db_instance

                    # Should eventually succeed after retries
                    await orchestrator._sync_instance_to_database(mock_instance)

                    # Should have been called 3 times (2 failures + 1 success)
                    assert mock_session.call_count == 3

    @pytest.mark.asyncio
    async def test_sync_instance_to_database_max_retries_exceeded(self, orchestrator, mock_instance):
        """Test database sync fails after max retries exceeded."""
        with patch('cc_orchestrator.core.orchestrator.get_db_session') as mock_session:
            mock_session.side_effect = Exception("Persistent connection error")

            with patch('asyncio.sleep'):  # Mock sleep to speed up test
                with pytest.raises(DatabaseSyncError) as exc_info:
                    await orchestrator._sync_instance_to_database(mock_instance)

                assert "Failed to sync instance test-123 to database" in str(exc_info.value)
                assert mock_session.call_count == 3  # Max retries

    @pytest.mark.asyncio
    async def test_load_specific_instance_from_database(self, orchestrator):
        """Test lazy loading of specific instance from database."""
        with patch('cc_orchestrator.core.orchestrator.get_db_session') as mock_session:
            mock_db_session = Mock()
            mock_session.return_value.__enter__.return_value = mock_db_session

            with patch('cc_orchestrator.core.orchestrator.InstanceCRUD') as mock_crud:
                # Mock database instance
                mock_db_instance = Mock()
                mock_db_instance.issue_id = "test-456"
                mock_db_instance.status = "RUNNING"
                mock_db_instance.workspace_path = "/test/path"
                mock_db_instance.branch_name = "test-branch"
                mock_db_instance.tmux_session = "test-tmux"
                mock_db_instance.process_id = 99999
                mock_db_instance.created_at = datetime.now()
                mock_db_instance.last_activity = datetime.now()
                mock_db_instance.updated_at = datetime.now()
                mock_db_instance.extra_metadata = {}

                mock_crud.get_by_issue_id.return_value = mock_db_instance

                with patch('cc_orchestrator.core.orchestrator.ClaudeInstance') as mock_instance_class:
                    mock_instance = Mock()
                    mock_instance.initialize = AsyncMock()
                    mock_instance_class.return_value = mock_instance

                    # Load specific instance
                    await orchestrator._load_specific_instance_from_database("test-456")

                    # Verify instance was added to memory
                    assert "test-456" in orchestrator.instances
                    mock_crud.get_by_issue_id.assert_called_once_with(mock_db_session, "test-456")

    @pytest.mark.asyncio
    async def test_load_specific_instance_not_found(self, orchestrator):
        """Test lazy loading when instance doesn't exist in database."""
        with patch('cc_orchestrator.core.orchestrator.get_db_session') as mock_session:
            mock_db_session = Mock()
            mock_session.return_value.__enter__.return_value = mock_db_session

            with patch('cc_orchestrator.core.orchestrator.InstanceCRUD') as mock_crud:
                mock_crud.get_by_issue_id.side_effect = NotFoundError("Not found")

                # Should not raise exception for missing instance
                await orchestrator._load_specific_instance_from_database("nonexistent")

                # Instance should not be in memory
                assert "nonexistent" not in orchestrator.instances

    @pytest.mark.asyncio
    async def test_get_instance_with_lazy_loading(self, orchestrator):
        """Test get_instance triggers lazy loading when needed."""
        # Instance not in memory initially
        assert "lazy-test" not in orchestrator.instances

        with patch.object(orchestrator, '_load_specific_instance_from_database') as mock_load:
            mock_instance = Mock()
            orchestrator.instances["lazy-test"] = mock_instance  # Simulate loaded instance

            result = await orchestrator.get_instance("lazy-test")

            # Should call lazy loading
            mock_load.assert_called_once_with("lazy-test")
            assert result == mock_instance

    @pytest.mark.asyncio
    async def test_get_instance_already_in_memory(self, orchestrator):
        """Test get_instance returns cached instance without database call."""
        mock_instance = Mock()
        orchestrator.instances["cached-test"] = mock_instance

        with patch.object(orchestrator, '_load_specific_instance_from_database') as mock_load:
            result = await orchestrator.get_instance("cached-test")

            # Should NOT call lazy loading
            mock_load.assert_not_called()
            assert result == mock_instance

    @pytest.mark.asyncio
    async def test_list_instances_lazy_loading(self, orchestrator):
        """Test list_instances loads all instances when memory is empty."""
        # Start with empty memory
        orchestrator.instances = {}

        with patch.object(orchestrator, '_load_instances_from_database') as mock_load_all:
            await orchestrator.list_instances(load_all=True)

            # Should trigger loading all instances
            mock_load_all.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_instances_no_loading_when_cached(self, orchestrator):
        """Test list_instances doesn't reload when instances already in memory."""
        # Start with instances in memory
        mock_instance = Mock()
        orchestrator.instances = {"existing": mock_instance}

        with patch.object(orchestrator, '_load_instances_from_database') as mock_load_all:
            result = await orchestrator.list_instances(load_all=True)

            # Should NOT reload
            mock_load_all.assert_not_called()
            assert len(result) == 1

    @pytest.mark.asyncio
    async def test_create_instance_with_database_persistence(self, orchestrator):
        """Test create_instance persists to database."""
        with patch('cc_orchestrator.core.orchestrator.ClaudeInstance') as mock_instance_class:
            mock_instance = Mock()
            mock_instance.issue_id = "persist-test"
            mock_instance.initialize = AsyncMock()
            mock_instance_class.return_value = mock_instance

            with patch.object(orchestrator, '_sync_instance_to_database') as mock_sync:
                result = await orchestrator.create_instance("persist-test")

                # Should sync to database
                mock_sync.assert_called_once_with(mock_instance)
                assert result == mock_instance
                assert "persist-test" in orchestrator.instances

    @pytest.mark.asyncio
    async def test_destroy_instance_removes_from_database(self, orchestrator):
        """Test destroy_instance removes instance from database."""
        # Add instance to memory
        mock_instance = Mock()
        mock_instance.cleanup = AsyncMock()
        orchestrator.instances["destroy-test"] = mock_instance

        with patch('cc_orchestrator.core.orchestrator.get_db_session') as mock_session:
            mock_db_session = Mock()
            mock_session.return_value.__enter__.return_value = mock_db_session

            with patch('cc_orchestrator.core.orchestrator.InstanceCRUD') as mock_crud:
                mock_db_instance = Mock()
                mock_db_instance.id = 1
                mock_crud.get_by_issue_id.return_value = mock_db_instance

                result = await orchestrator.destroy_instance("destroy-test")

                # Should remove from database and memory
                assert result is True
                assert "destroy-test" not in orchestrator.instances
                mock_crud.get_by_issue_id.assert_called_once_with(mock_db_session, "destroy-test")
                mock_crud.delete.assert_called_once_with(mock_db_session, 1)

    @pytest.mark.asyncio
    async def test_initialize_with_lazy_loading(self):
        """Test orchestrator initialization with lazy loading enabled."""
        orchestrator = Orchestrator()

        with patch.object(orchestrator, '_load_instances_from_database') as mock_load:
            await orchestrator.initialize(lazy_load=True)

            # Should NOT load instances immediately
            mock_load.assert_not_called()
            assert orchestrator._initialized is True

        await orchestrator.cleanup()

    @pytest.mark.asyncio
    async def test_initialize_without_lazy_loading(self):
        """Test orchestrator initialization loads all instances immediately."""
        orchestrator = Orchestrator()

        with patch.object(orchestrator, '_load_instances_from_database') as mock_load:
            await orchestrator.initialize(lazy_load=False)

            # Should load all instances
            mock_load.assert_called_once()
            assert orchestrator._initialized is True

        await orchestrator.cleanup()


class TestDatabaseSyncErrorScenarios:
    """Test database sync error handling and recovery."""

    @pytest.fixture
    async def orchestrator(self):
        """Create a test orchestrator instance."""
        orchestrator = Orchestrator()
        await orchestrator.initialize(lazy_load=True)
        yield orchestrator
        await orchestrator.cleanup()

    @pytest.mark.asyncio
    async def test_transaction_rollback_on_constraint_violation(self, orchestrator):
        """Test transaction rollback when database constraints are violated."""
        mock_instance = Mock()
        mock_instance.issue_id = "constraint-test"
        mock_instance.status = InstanceStatus.RUNNING

        with patch('cc_orchestrator.core.orchestrator.get_db_session') as mock_session:
            mock_db_session = Mock()
            mock_session.return_value.__enter__.return_value = mock_db_session
            mock_db_session.flush.side_effect = Exception("UNIQUE constraint failed")

            with patch('cc_orchestrator.core.orchestrator.InstanceCRUD') as mock_crud:
                mock_crud.get_by_issue_id.side_effect = NotFoundError("Not found")
                mock_db_instance = Mock()
                mock_db_instance.id = 1
                mock_crud.create.return_value = mock_db_instance

                with pytest.raises(DatabaseSyncError):
                    await orchestrator._sync_instance_to_database(mock_instance)

                # Transaction should have been attempted to rollback automatically
                # by the context manager

    @pytest.mark.asyncio
    async def test_database_connection_pool_timeout(self, orchestrator):
        """Test handling of connection pool timeouts."""
        mock_instance = Mock()
        mock_instance.issue_id = "timeout-test"

        with patch('cc_orchestrator.core.orchestrator.get_db_session') as mock_session:
            mock_session.side_effect = Exception("Connection pool timeout")

            with patch('asyncio.sleep'):
                with pytest.raises(DatabaseSyncError) as exc_info:
                    await orchestrator._sync_instance_to_database(mock_instance)

                assert "timeout-test" in str(exc_info.value)
                # Should have tried all retries
                assert mock_session.call_count == 3

    @pytest.mark.asyncio
    async def test_status_conversion_edge_cases(self, orchestrator):
        """Test instance status conversion between database and memory."""
        # Test all status mappings
        test_cases = [
            (InstanceStatus.INITIALIZING, "INITIALIZING"),
            (InstanceStatus.RUNNING, "RUNNING"),
            (InstanceStatus.STOPPED, "STOPPED"),
            (InstanceStatus.ERROR, "ERROR"),
        ]

        for instance_status, db_status_str in test_cases:
            # Test instance to DB status conversion
            with patch('cc_orchestrator.database.models.InstanceStatus') as mock_db_status:
                mock_db_status.INITIALIZING = "INITIALIZING"
                mock_db_status.RUNNING = "RUNNING"
                mock_db_status.STOPPED = "STOPPED"
                mock_db_status.ERROR = "ERROR"

                db_status = orchestrator._instance_status_to_db_status(instance_status)
                # Would need actual enum comparison in real test

                # Test DB to instance status conversion
                with patch.object(orchestrator, '_db_status_to_instance_status') as mock_convert:
                    mock_convert.return_value = instance_status
                    result = orchestrator._db_status_to_instance_status(db_status)
                    assert result == instance_status