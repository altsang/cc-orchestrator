"""Unit tests for Orchestrator class."""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from cc_orchestrator.core.instance import ClaudeInstance
from cc_orchestrator.core.orchestrator import Orchestrator
from cc_orchestrator.database.crud import NotFoundError


class TestOrchestrator:
    """Test suite for Orchestrator class."""

    def test_init_default(self):
        """Test orchestrator initialization with defaults."""
        orchestrator = Orchestrator()
        assert orchestrator.config_path is None
        assert orchestrator._db_session is None
        assert orchestrator._should_close_session is True
        assert orchestrator._initialized is False

    def test_init_with_config(self):
        """Test orchestrator initialization with config path."""
        config_path = "/path/to/config.yaml"
        orchestrator = Orchestrator(config_path=config_path)
        assert orchestrator.config_path == config_path
        assert orchestrator._db_session is None
        assert orchestrator._should_close_session is True
        assert orchestrator._initialized is False

    def test_init_with_session(self):
        """Test orchestrator initialization with provided session."""
        mock_session = Mock()
        orchestrator = Orchestrator(db_session=mock_session)
        assert orchestrator._db_session is mock_session
        assert orchestrator._should_close_session is False
        assert orchestrator._initialized is False

    @pytest.mark.asyncio
    async def test_initialize(self):
        """Test orchestrator initialization."""
        mock_health_monitor = Mock()
        mock_health_monitor.start = AsyncMock()

        with (
            patch(
                "cc_orchestrator.database.connection.get_database_manager"
            ) as mock_get_db_manager,
            patch(
                "cc_orchestrator.core.orchestrator.get_health_monitor",
                return_value=mock_health_monitor,
            ),
        ):
            mock_db_manager = Mock()
            mock_session = Mock()
            mock_db_manager.create_session.return_value = mock_session
            mock_get_db_manager.return_value = mock_db_manager

            orchestrator = Orchestrator()
            await orchestrator.initialize()

            assert orchestrator._initialized is True
            assert orchestrator._db_session is mock_session
            assert orchestrator._should_close_session is True
            mock_health_monitor.start.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialize_with_provided_session(self):
        """Test orchestrator initialization with provided session."""
        mock_session = Mock()
        mock_health_monitor = Mock()
        mock_health_monitor.start = AsyncMock()

        with patch(
            "cc_orchestrator.core.orchestrator.get_health_monitor",
            return_value=mock_health_monitor,
        ):
            orchestrator = Orchestrator(db_session=mock_session)
            await orchestrator.initialize()

        assert orchestrator._initialized is True
        assert orchestrator._db_session is mock_session
        assert orchestrator._should_close_session is False
        mock_health_monitor.start.assert_called_once()

    def test_get_instance_existing(self):
        """Test getting an existing instance."""
        mock_session = Mock()
        orchestrator = Orchestrator(db_session=mock_session)
        orchestrator._initialized = True

        mock_db_instance = Mock()
        mock_db_instance.issue_id = "test-123"
        mock_db_instance.workspace_path = "/test/workspace"
        mock_db_instance.branch_name = "main"
        mock_db_instance.tmux_session = "test-session"
        mock_db_instance.status = Mock()
        mock_db_instance.process_id = None
        mock_db_instance.created_at = Mock()
        mock_db_instance.last_activity = None
        mock_db_instance.updated_at = Mock()
        mock_db_instance.extra_metadata = {}

        with patch("cc_orchestrator.core.orchestrator.InstanceCRUD") as mock_crud:
            mock_crud.get_by_issue_id.return_value = mock_db_instance

            with patch.object(
                orchestrator, "_db_instance_to_claude_instance"
            ) as mock_convert:
                mock_instance = Mock(spec=ClaudeInstance)
                mock_convert.return_value = mock_instance

                result = orchestrator.get_instance("test-123")

                assert result == mock_instance
                mock_crud.get_by_issue_id.assert_called_once_with(
                    mock_session, "test-123"
                )
                mock_convert.assert_called_once_with(mock_db_instance)

    def test_get_instance_nonexistent(self):
        """Test getting a non-existent instance."""
        mock_session = Mock()
        orchestrator = Orchestrator(db_session=mock_session)
        orchestrator._initialized = True

        with patch("cc_orchestrator.core.orchestrator.InstanceCRUD") as mock_crud:
            mock_crud.get_by_issue_id.side_effect = NotFoundError("Not found")

            result = orchestrator.get_instance("nonexistent")
            assert result is None

    def test_get_instance_uninitialized(self):
        """Test getting instance when orchestrator not initialized."""
        orchestrator = Orchestrator()
        result = orchestrator.get_instance("test-123")
        assert result is None

    def test_list_instances_empty(self):
        """Test listing instances when none exist."""
        orchestrator = Orchestrator()
        result = orchestrator.list_instances()
        assert result == []

    def test_list_instances_with_data(self):
        """Test listing instances with data."""
        mock_session = Mock()
        orchestrator = Orchestrator(db_session=mock_session)
        orchestrator._initialized = True

        mock_db_instance1 = Mock()
        mock_db_instance2 = Mock()

        with patch("cc_orchestrator.core.orchestrator.InstanceCRUD") as mock_crud:
            mock_crud.list_all.return_value = [mock_db_instance1, mock_db_instance2]

            with patch.object(
                orchestrator, "_db_instance_to_claude_instance"
            ) as mock_convert:
                mock_instance1 = Mock(spec=ClaudeInstance)
                mock_instance2 = Mock(spec=ClaudeInstance)
                mock_convert.side_effect = [mock_instance1, mock_instance2]

                result = orchestrator.list_instances()

                assert len(result) == 2
                assert mock_instance1 in result
                assert mock_instance2 in result
                mock_crud.list_all.assert_called_once_with(mock_session)

    @pytest.mark.asyncio
    async def test_create_instance_success(self):
        """Test successful instance creation."""
        mock_session = Mock()
        orchestrator = Orchestrator(db_session=mock_session)
        orchestrator._initialized = True

        with patch.object(
            orchestrator, "get_instance", return_value=None
        ):  # No existing instance
            with patch(
                "cc_orchestrator.core.orchestrator.ClaudeInstance"
            ) as mock_claude_instance_class:
                mock_instance = AsyncMock()
                mock_instance.issue_id = "test-123"
                mock_instance.workspace_path = "/tmp/test"
                mock_instance.branch_name = "main"
                mock_instance.tmux_session = "test-session"
                mock_claude_instance_class.return_value = mock_instance

                mock_db_instance = Mock()
                mock_db_instance.id = 1

                with patch(
                    "cc_orchestrator.core.orchestrator.InstanceCRUD"
                ) as mock_crud:
                    mock_crud.create.return_value = mock_db_instance

                    result = await orchestrator.create_instance(
                        "test-123", workspace_path="/tmp/test"
                    )

                    assert result == mock_instance
                    mock_instance.initialize.assert_called_once()
                    mock_claude_instance_class.assert_called_once_with(
                        issue_id="test-123", workspace_path="/tmp/test"
                    )
                    mock_crud.create.assert_called_once()
                    mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_instance_already_exists(self):
        """Test creating instance that already exists."""
        mock_session = Mock()
        orchestrator = Orchestrator(db_session=mock_session)
        orchestrator._initialized = True

        mock_existing_instance = Mock(spec=ClaudeInstance)
        with patch.object(
            orchestrator, "get_instance", return_value=mock_existing_instance
        ):
            with pytest.raises(
                ValueError, match="Instance for issue test-123 already exists"
            ):
                await orchestrator.create_instance("test-123")

    @pytest.mark.asyncio
    async def test_create_instance_uninitialized(self):
        """Test creating instance when orchestrator not initialized."""
        orchestrator = Orchestrator()

        with pytest.raises(RuntimeError, match="not initialized"):
            await orchestrator.create_instance("test-123")

    @pytest.mark.asyncio
    async def test_destroy_instance_success(self):
        """Test successful instance destruction."""
        mock_session = Mock()
        orchestrator = Orchestrator(db_session=mock_session)
        orchestrator._initialized = True

        mock_db_instance = Mock()
        mock_db_instance.id = 1
        mock_instance = AsyncMock()

        with patch("cc_orchestrator.core.orchestrator.InstanceCRUD") as mock_crud:
            mock_crud.get_by_issue_id.return_value = mock_db_instance

            with patch.object(
                orchestrator,
                "_db_instance_to_claude_instance",
                return_value=mock_instance,
            ):
                result = await orchestrator.destroy_instance("test-123")

                assert result is True
                mock_instance.cleanup.assert_called_once()
                mock_crud.get_by_issue_id.assert_called_once_with(
                    mock_session, "test-123"
                )
                mock_crud.delete.assert_called_once_with(mock_session, 1)
                mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_destroy_instance_not_found(self):
        """Test destroying non-existent instance."""
        mock_session = Mock()
        orchestrator = Orchestrator(db_session=mock_session)
        orchestrator._initialized = True

        with patch("cc_orchestrator.core.orchestrator.InstanceCRUD") as mock_crud:
            mock_crud.get_by_issue_id.side_effect = NotFoundError("Not found")

            result = await orchestrator.destroy_instance("nonexistent")

            assert result is False

    @pytest.mark.asyncio
    async def test_destroy_instance_uninitialized(self):
        """Test destroying instance when orchestrator not initialized."""
        orchestrator = Orchestrator()

        with pytest.raises(RuntimeError, match="not initialized"):
            await orchestrator.destroy_instance("test-123")

    @pytest.mark.asyncio
    async def test_cleanup(self):
        """Test orchestrator cleanup."""
        mock_session = Mock()
        mock_health_monitor = Mock()
        mock_health_monitor.stop = AsyncMock()

        with patch(
            "cc_orchestrator.core.orchestrator.get_health_monitor",
            return_value=mock_health_monitor,
        ):
            orchestrator = Orchestrator(db_session=mock_session)
            orchestrator._initialized = True
            orchestrator._should_close_session = False  # We provided the session

        mock_instance1 = AsyncMock()
        mock_instance2 = AsyncMock()

        with patch.object(
            orchestrator,
            "list_instances",
            return_value=[mock_instance1, mock_instance2],
        ):
            # Mock cleanup functions to avoid affecting global state
            with (
                patch(
                    "cc_orchestrator.core.orchestrator.cleanup_process_manager",
                    new_callable=AsyncMock,
                ) as mock_cleanup_process,
                patch(
                    "cc_orchestrator.core.orchestrator.cleanup_health_monitor",
                    new_callable=AsyncMock,
                ) as mock_cleanup_health,
            ):
                await orchestrator.cleanup()

        mock_health_monitor.stop.assert_called_once()
        mock_instance1.cleanup.assert_called_once()
        mock_instance2.cleanup.assert_called_once()
        mock_cleanup_process.assert_called_once()
        mock_cleanup_health.assert_called_once()
        # Session should not be closed since we provided it
        mock_session.close.assert_not_called()

    @pytest.mark.asyncio
    async def test_cleanup_with_auto_session(self):
        """Test orchestrator cleanup with auto-managed session."""
        mock_session = Mock()
        mock_health_monitor = Mock()
        mock_health_monitor.stop = AsyncMock()

        with patch(
            "cc_orchestrator.core.orchestrator.get_health_monitor",
            return_value=mock_health_monitor,
        ):
            orchestrator = Orchestrator()
            orchestrator._initialized = True
            orchestrator._db_session = mock_session
            orchestrator._should_close_session = (
                True  # Orchestrator created the session
            )

        with patch.object(orchestrator, "list_instances", return_value=[]):
            with (
                patch(
                    "cc_orchestrator.core.orchestrator.cleanup_process_manager",
                    new_callable=AsyncMock,
                ),
                patch(
                    "cc_orchestrator.core.orchestrator.cleanup_health_monitor",
                    new_callable=AsyncMock,
                ),
            ):
                await orchestrator.cleanup()

        # Session should be closed since orchestrator created it
        mock_session.close.assert_called_once()
        assert orchestrator._db_session is None
