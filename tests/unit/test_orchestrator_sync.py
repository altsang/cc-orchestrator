"""Unit tests for Orchestrator sync functionality (Issue #59)."""

from unittest.mock import MagicMock, Mock, patch

import pytest
from sqlalchemy.exc import SQLAlchemyError

from cc_orchestrator.core.enums import InstanceStatus
from cc_orchestrator.core.instance import ClaudeInstance
from cc_orchestrator.core.orchestrator import Orchestrator
from cc_orchestrator.database.models import Instance as DBInstance


class TestOrchestratorSync:
    """Test the sync_instance_to_database functionality."""

    @pytest.fixture
    def mock_orchestrator(self):
        """Create a mock orchestrator with initialized state."""
        orchestrator = Orchestrator()
        orchestrator._initialized = True
        orchestrator._db_session = Mock()
        return orchestrator

    @pytest.fixture
    def mock_instance(self):
        """Create a mock Claude instance."""
        instance = Mock(spec=ClaudeInstance)
        instance.issue_id = "test-issue-123"
        instance.status = InstanceStatus.RUNNING
        instance.process_id = 12345
        instance.last_activity = "2025-09-21T00:00:00"
        return instance

    @pytest.fixture
    def mock_db_instance(self):
        """Create a mock database instance."""
        db_instance = Mock(spec=DBInstance)
        db_instance.id = 1
        db_instance.issue_id = "test-issue-123"
        db_instance.status = InstanceStatus.STOPPED
        db_instance.process_id = None
        return db_instance

    def test_sync_instance_to_database_success(
        self, mock_orchestrator, mock_instance, mock_db_instance
    ):
        """Test successful instance sync to database."""
        # Setup mocks
        with patch("cc_orchestrator.core.orchestrator.InstanceCRUD") as mock_crud:
            mock_crud.get_by_issue_id.return_value = mock_db_instance
            mock_crud.update.return_value = mock_db_instance

            # Mock the transaction context
            mock_orchestrator._db_session.begin.return_value.__enter__ = Mock()
            mock_orchestrator._db_session.begin.return_value.__exit__ = Mock(
                return_value=False
            )

            # Mock the authorization validation to return True
            with patch.object(
                mock_orchestrator, "_validate_instance_ownership", return_value=True
            ):
                # Execute
                result = mock_orchestrator.sync_instance_to_database(mock_instance)

                # Verify
                assert result is True
                mock_crud.get_by_issue_id.assert_called_once_with(
                    mock_orchestrator._db_session, "test-issue-123"
                )
                mock_crud.update.assert_called_once_with(
                    session=mock_orchestrator._db_session,
                    instance_id=1,
                    status=InstanceStatus.RUNNING,
                    process_id=12345,
                    last_activity="2025-09-21T00:00:00",
                )

    def test_sync_instance_to_database_invalid_instance(self, mock_orchestrator):
        """Test sync with invalid instance."""
        # Test with None instance
        result = mock_orchestrator.sync_instance_to_database(None)
        assert result is False

        # Test with instance without issue_id
        invalid_instance = Mock()
        invalid_instance.issue_id = None
        result = mock_orchestrator.sync_instance_to_database(invalid_instance)
        assert result is False

        # Test with instance with empty issue_id
        invalid_instance.issue_id = ""
        result = mock_orchestrator.sync_instance_to_database(invalid_instance)
        assert result is False

    def test_sync_instance_to_database_not_initialized(self, mock_instance):
        """Test sync when orchestrator is not initialized."""
        orchestrator = Orchestrator()

        # Test with _initialized = False
        orchestrator._initialized = False
        orchestrator._db_session = Mock()
        result = orchestrator.sync_instance_to_database(mock_instance)
        assert result is False

        # Test with no _db_session
        orchestrator._initialized = True
        orchestrator._db_session = None
        result = orchestrator.sync_instance_to_database(mock_instance)
        assert result is False

    def test_sync_instance_to_database_instance_not_found(
        self, mock_orchestrator, mock_instance
    ):
        """Test sync when instance is not found in database."""
        with patch("cc_orchestrator.core.orchestrator.InstanceCRUD") as mock_crud:
            mock_crud.get_by_issue_id.return_value = None

            # Mock the transaction context
            mock_orchestrator._db_session.begin.return_value.__enter__ = Mock()
            mock_orchestrator._db_session.begin.return_value.__exit__ = Mock(
                return_value=False
            )

            result = mock_orchestrator.sync_instance_to_database(mock_instance)

            assert result is False
            mock_crud.get_by_issue_id.assert_called_once()
            mock_crud.update.assert_not_called()

    def test_sync_instance_to_database_database_error(
        self, mock_orchestrator, mock_instance
    ):
        """Test sync when database operation fails."""
        with patch("cc_orchestrator.core.orchestrator.InstanceCRUD") as mock_crud:
            mock_crud.get_by_issue_id.side_effect = SQLAlchemyError(
                "Database connection failed"
            )

            # Mock the transaction context
            mock_orchestrator._db_session.begin.return_value.__enter__ = Mock()
            mock_orchestrator._db_session.begin.return_value.__exit__ = Mock(
                return_value=False
            )

            result = mock_orchestrator.sync_instance_to_database(mock_instance)

            assert result is False
            mock_crud.get_by_issue_id.assert_called_once()

    def test_sync_instance_to_database_update_error(
        self, mock_orchestrator, mock_instance, mock_db_instance
    ):
        """Test sync when update operation fails."""
        with patch("cc_orchestrator.core.orchestrator.InstanceCRUD") as mock_crud:
            mock_crud.get_by_issue_id.return_value = mock_db_instance
            mock_crud.update.side_effect = SQLAlchemyError("Update failed")

            # Mock the transaction context
            mock_orchestrator._db_session.begin.return_value.__enter__ = Mock()
            mock_orchestrator._db_session.begin.return_value.__exit__ = Mock(
                return_value=False
            )

            # Mock the authorization validation to return True
            with patch.object(
                mock_orchestrator, "_validate_instance_ownership", return_value=True
            ):
                result = mock_orchestrator.sync_instance_to_database(mock_instance)

                assert result is False
                # Note: get_by_issue_id is called twice - once for auth validation, once for sync
                assert mock_crud.get_by_issue_id.call_count == 2
                mock_crud.update.assert_called_once()

    def test_sync_instance_to_database_transaction_isolation(
        self, mock_orchestrator, mock_instance, mock_db_instance
    ):
        """Test that sync operations are properly isolated in transactions."""
        with patch("cc_orchestrator.core.orchestrator.InstanceCRUD") as mock_crud:
            mock_crud.get_by_issue_id.return_value = mock_db_instance
            mock_crud.update.return_value = mock_db_instance

            # Mock transaction context manager
            mock_context = MagicMock()
            mock_orchestrator._db_session.begin.return_value = mock_context

            # Mock the authorization validation to return True
            with patch.object(
                mock_orchestrator, "_validate_instance_ownership", return_value=True
            ):
                result = mock_orchestrator.sync_instance_to_database(mock_instance)

                # Verify transaction was used
                assert result is True
                mock_orchestrator._db_session.begin.assert_called_once()
                mock_context.__enter__.assert_called_once()
                mock_context.__exit__.assert_called_once()

    @patch("cc_orchestrator.core.orchestrator.logger")
    def test_sync_instance_to_database_logging(
        self, mock_logger, mock_orchestrator, mock_instance, mock_db_instance
    ):
        """Test that appropriate logging occurs during sync operations."""
        with patch("cc_orchestrator.core.orchestrator.InstanceCRUD") as mock_crud:
            mock_crud.get_by_issue_id.return_value = mock_db_instance
            mock_crud.update.return_value = mock_db_instance

            # Mock the transaction context
            mock_orchestrator._db_session.begin.return_value.__enter__ = Mock()
            mock_orchestrator._db_session.begin.return_value.__exit__ = Mock(
                return_value=False
            )

            # Mock the authorization validation to return True
            with patch.object(
                mock_orchestrator, "_validate_instance_ownership", return_value=True
            ):
                result = mock_orchestrator.sync_instance_to_database(mock_instance)

                assert result is True

                # Verify logging calls
                assert mock_logger.info.call_count >= 2  # Start and success logs
                mock_logger.info.assert_any_call(
                    "Syncing instance to database",
                    issue_id="test-issue-123",
                    memory_status="running",
                    db_status="stopped",
                    # Removed process_id from logging for security
                )
                mock_logger.info.assert_any_call(
                    "Instance state synced to database successfully",
                    issue_id="test-issue-123",
                    final_status="stopped",
                    # Removed process_id from logging for security
                )

    @patch("cc_orchestrator.core.orchestrator.logger")
    def test_sync_instance_to_database_error_logging(
        self, mock_logger, mock_orchestrator, mock_instance
    ):
        """Test error logging when sync fails."""
        with patch("cc_orchestrator.core.orchestrator.InstanceCRUD") as mock_crud:
            # Set up mock to succeed for authorization but fail for actual sync
            db_instance_mock = Mock()
            db_instance_mock.id = 1
            error_msg = "Database connection lost"

            # First call (for authorization) succeeds, second call (for sync) fails
            mock_crud.get_by_issue_id.side_effect = [
                db_instance_mock,
                SQLAlchemyError(error_msg),
            ]

            # Mock the transaction context
            mock_orchestrator._db_session.begin.return_value.__enter__ = Mock()
            mock_orchestrator._db_session.begin.return_value.__exit__ = Mock(
                return_value=False
            )

            result = mock_orchestrator.sync_instance_to_database(mock_instance)

            assert result is False
            mock_logger.error.assert_called_with(
                "Failed to sync instance state to database",
                issue_id="test-issue-123",
                error=error_msg,
            )


class TestSyncFailureScenarios:
    """Test various failure scenarios for sync functionality."""

    def test_concurrent_modification_handling(self):
        """Test handling of concurrent modifications to instance state."""
        # This test would verify that the atomic transaction prevents
        # race conditions between multiple processes modifying the same instance
        pass  # Implementation would require database integration test

    def test_sync_failure_recovery(self):
        """Test system behavior when sync consistently fails."""
        # This test would verify that repeated sync failures don't
        # accumulate and cause system instability
        pass  # Implementation would require integration testing

    def test_partial_sync_failure(self):
        """Test behavior when only some fields fail to sync."""
        # This test would verify proper handling of partial update failures
        pass  # Implementation would require more granular error handling
