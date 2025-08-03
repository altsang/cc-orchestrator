"""Unit tests for tmux service functionality."""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cc_orchestrator.tmux import (
    LayoutTemplate,
    SessionConfig,
    SessionInfo,
    SessionStatus,
    TmuxError,
    TmuxService,
)


class TestSessionConfig:
    """Test SessionConfig dataclass."""

    def test_session_config_creation(self):
        """Test SessionConfig creation with required fields."""
        config = SessionConfig(
            session_name="test-session",
            working_directory=Path("/tmp/test"),
            instance_id="test-instance",
        )
        assert config.session_name == "test-session"
        assert config.working_directory == Path("/tmp/test")
        assert config.instance_id == "test-instance"
        assert config.layout_template == "default"
        assert config.environment is None
        assert config.auto_attach is False
        assert config.persist_after_exit is True

    def test_session_config_with_optional_fields(self):
        """Test SessionConfig with optional fields."""
        config = SessionConfig(
            session_name="test-session",
            working_directory=Path("/tmp/test"),
            instance_id="test-instance",
            layout_template="development",
            environment={"TEST_VAR": "value"},
            auto_attach=True,
            persist_after_exit=False,
        )
        assert config.layout_template == "development"
        assert config.environment == {"TEST_VAR": "value"}
        assert config.auto_attach is True
        assert config.persist_after_exit is False


class TestSessionInfo:
    """Test SessionInfo dataclass."""

    def test_session_info_creation(self):
        """Test SessionInfo creation."""
        info = SessionInfo(
            session_name="cc-orchestrator-test",
            instance_id="test-instance",
            status=SessionStatus.ACTIVE,
            working_directory=Path("/tmp/test"),
            layout_template="default",
            created_at=1234567890.0,
            windows=["main", "terminal"],
        )
        assert info.session_name == "cc-orchestrator-test"
        assert info.instance_id == "test-instance"
        assert info.status == SessionStatus.ACTIVE
        assert info.working_directory == Path("/tmp/test")
        assert info.layout_template == "default"
        assert info.created_at == 1234567890.0
        assert info.windows == ["main", "terminal"]
        assert info.current_window is None
        assert info.last_activity is None
        assert info.attached_clients == 0


class TestLayoutTemplate:
    """Test LayoutTemplate class."""

    def test_layout_template_creation(self):
        """Test LayoutTemplate creation."""
        windows = [
            {
                "name": "main",
                "command": "bash",
                "panes": [{"command": "bash"}],
            }
        ]
        template = LayoutTemplate(
            name="test-template",
            description="Test template",
            windows=windows,
        )
        assert template.name == "test-template"
        assert template.description == "Test template"
        assert template.windows == windows
        assert template.default_pane_command == "bash"

    def test_layout_template_with_custom_pane_command(self):
        """Test LayoutTemplate with custom default pane command."""
        template = LayoutTemplate(
            name="test-template",
            description="Test template",
            windows=[],
            default_pane_command="zsh",
        )
        assert template.default_pane_command == "zsh"


class TestTmuxService:
    """Test cases for TmuxService class."""

    @pytest.fixture
    def mock_server(self):
        """Mock libtmux server."""
        with patch("cc_orchestrator.tmux.service.libtmux.Server") as mock:
            server_instance = MagicMock()
            mock.return_value = server_instance
            yield server_instance

    @pytest.fixture
    def tmux_service(self, mock_server):
        """Create TmuxService instance with mocked server."""
        return TmuxService()

    def test_tmux_service_initialization(self, tmux_service, mock_server):
        """Test TmuxService initialization."""
        assert tmux_service._server is mock_server
        assert tmux_service._sessions == {}
        assert tmux_service._session_prefix == "cc-orchestrator"
        assert "default" in tmux_service._layout_templates
        assert "development" in tmux_service._layout_templates
        assert "claude" in tmux_service._layout_templates

    def test_normalize_session_name(self, tmux_service):
        """Test session name normalization."""
        # Test adding prefix
        result = tmux_service._normalize_session_name("test-session")
        assert result == "cc-orchestrator-test-session"

        # Test keeping existing prefix
        result = tmux_service._normalize_session_name("cc-orchestrator-test")
        assert result == "cc-orchestrator-test"

    def test_extract_instance_id(self, tmux_service):
        """Test instance ID extraction from session name."""
        # Test with prefix
        result = tmux_service._extract_instance_id("cc-orchestrator-test-instance")
        assert result == "test-instance"

        # Test without prefix
        result = tmux_service._extract_instance_id("test-instance")
        assert result == "test-instance"

    @pytest.mark.asyncio
    async def test_session_exists_true(self, tmux_service, mock_server):
        """Test session_exists returns True when session exists."""
        mock_session = MagicMock()
        mock_server.sessions.get.return_value = mock_session

        result = await tmux_service.session_exists("test-session")
        assert result is True
        mock_server.sessions.get.assert_called_once_with(
            session_name="cc-orchestrator-test-session"
        )

    @pytest.mark.asyncio
    async def test_session_exists_false(self, tmux_service, mock_server):
        """Test session_exists returns False when session doesn't exist."""
        mock_server.sessions.get.return_value = None

        result = await tmux_service.session_exists("test-session")
        assert result is False

    @pytest.mark.asyncio
    async def test_session_exists_exception(self, tmux_service, mock_server):
        """Test session_exists handles exceptions gracefully."""
        mock_server.sessions.get.side_effect = Exception("Connection error")

        result = await tmux_service.session_exists("test-session")
        assert result is False

    @pytest.mark.asyncio
    async def test_create_session_success(self, tmux_service, mock_server, tmp_path):
        """Test successful session creation."""
        # Setup mocks
        mock_session = MagicMock()
        mock_window = MagicMock()
        mock_window.name = "main"
        mock_session.windows = [mock_window]
        mock_server.new_session.return_value = mock_session
        mock_server.sessions.get.return_value = None  # Session doesn't exist

        config = SessionConfig(
            session_name="test-session",
            working_directory=tmp_path,
            instance_id="test-instance",
        )

        with patch("asyncio.get_event_loop") as mock_loop:
            mock_loop.return_value.time.return_value = 1234567890.0

            result = await tmux_service.create_session(config)

        assert isinstance(result, SessionInfo)
        assert result.session_name == "cc-orchestrator-test-session"
        assert result.instance_id == "test-instance"
        assert result.status == SessionStatus.ACTIVE
        assert result.working_directory == tmp_path
        assert result.layout_template == "default"
        assert result.windows == ["main"]
        assert result.current_window == "main"

        # Verify session was created with correct parameters
        mock_server.new_session.assert_called_once_with(
            session_name="cc-orchestrator-test-session",
            start_directory=str(tmp_path),
            detach=True,
        )

    @pytest.mark.asyncio
    async def test_create_session_already_exists(self, tmux_service, mock_server, tmp_path):
        """Test session creation when session already exists."""
        mock_session = MagicMock()
        mock_server.sessions.get.return_value = mock_session

        config = SessionConfig(
            session_name="test-session",
            working_directory=tmp_path,
            instance_id="test-instance",
        )

        with pytest.raises(TmuxError, match="Session .* already exists"):
            await tmux_service.create_session(config)

    @pytest.mark.asyncio
    async def test_create_session_with_environment(self, tmux_service, mock_server, tmp_path):
        """Test session creation with environment variables."""
        mock_session = MagicMock()
        mock_window = MagicMock()
        mock_window.name = "main"
        mock_session.windows = [mock_window]
        mock_server.new_session.return_value = mock_session
        mock_server.sessions.get.return_value = None

        config = SessionConfig(
            session_name="test-session",
            working_directory=tmp_path,
            instance_id="test-instance",
            environment={"TEST_VAR": "test_value", "ANOTHER_VAR": "another_value"},
        )

        with patch("asyncio.get_event_loop") as mock_loop:
            mock_loop.return_value.time.return_value = 1234567890.0

            await tmux_service.create_session(config)

        # Verify environment variables were set
        mock_session.set_environment.assert_any_call("TEST_VAR", "test_value")
        mock_session.set_environment.assert_any_call("ANOTHER_VAR", "another_value")

    @pytest.mark.asyncio
    async def test_destroy_session_success(self, tmux_service, mock_server):
        """Test successful session destruction."""
        mock_session = MagicMock()
        mock_session.attached = False
        mock_server.sessions.get.return_value = mock_session

        # Add session to tracking
        tmux_service._sessions["cc-orchestrator-test-session"] = SessionInfo(
            session_name="cc-orchestrator-test-session",
            instance_id="test-instance",
            status=SessionStatus.ACTIVE,
            working_directory=Path("/tmp"),
            layout_template="default",
            created_at=1234567890.0,
            windows=["main"],
        )

        result = await tmux_service.destroy_session("test-session")
        assert result is True
        mock_session.kill.assert_called_once()
        assert "cc-orchestrator-test-session" not in tmux_service._sessions

    @pytest.mark.asyncio
    async def test_destroy_session_with_attached_clients(self, tmux_service, mock_server):
        """Test session destruction with attached clients."""
        mock_session = MagicMock()
        mock_session.attached = True
        mock_server.sessions.get.return_value = mock_session

        with pytest.raises(TmuxError, match="has attached clients"):
            await tmux_service.destroy_session("test-session", force=False)

    @pytest.mark.asyncio
    async def test_destroy_session_force_with_attached_clients(self, tmux_service, mock_server):
        """Test forced session destruction with attached clients."""
        mock_session = MagicMock()
        mock_session.attached = True
        mock_server.sessions.get.return_value = mock_session

        result = await tmux_service.destroy_session("test-session", force=True)
        assert result is True
        mock_session.kill.assert_called_once()

    @pytest.mark.asyncio
    async def test_destroy_session_not_exists(self, tmux_service, mock_server):
        """Test destroying non-existent session."""
        mock_server.sessions.get.return_value = None

        result = await tmux_service.destroy_session("test-session")
        assert result is False

    @pytest.mark.asyncio
    async def test_attach_session_success(self, tmux_service, mock_server):
        """Test successful session attachment."""
        mock_session = MagicMock()
        mock_server.sessions.get.return_value = mock_session

        # Add session to tracking
        session_info = SessionInfo(
            session_name="cc-orchestrator-test-session",
            instance_id="test-instance",
            status=SessionStatus.DETACHED,
            working_directory=Path("/tmp"),
            layout_template="default",
            created_at=1234567890.0,
            windows=["main"],
        )
        tmux_service._sessions["cc-orchestrator-test-session"] = session_info

        with patch("asyncio.get_event_loop") as mock_loop:
            mock_loop.return_value.time.return_value = 1234567900.0

            result = await tmux_service.attach_session("test-session")

        assert result is True
        assert session_info.status == SessionStatus.ACTIVE
        assert session_info.last_activity == 1234567900.0

    @pytest.mark.asyncio
    async def test_attach_session_not_exists(self, tmux_service, mock_server):
        """Test attaching to non-existent session."""
        mock_server.sessions.get.return_value = None

        result = await tmux_service.attach_session("test-session")
        assert result is False

    @pytest.mark.asyncio
    async def test_detach_session_success(self, tmux_service, mock_server):
        """Test successful session detachment."""
        mock_session = MagicMock()
        mock_server.sessions.get.return_value = mock_session

        # Add session to tracking
        session_info = SessionInfo(
            session_name="cc-orchestrator-test-session",
            instance_id="test-instance",
            status=SessionStatus.ACTIVE,
            working_directory=Path("/tmp"),
            layout_template="default",
            created_at=1234567890.0,
            windows=["main"],
        )
        tmux_service._sessions["cc-orchestrator-test-session"] = session_info

        with patch("asyncio.get_event_loop") as mock_loop:
            mock_loop.return_value.time.return_value = 1234567900.0

            result = await tmux_service.detach_session("test-session")

        assert result is True
        mock_session.detach.assert_called_once()
        assert session_info.status == SessionStatus.DETACHED
        assert session_info.last_activity == 1234567900.0

    @pytest.mark.asyncio
    async def test_list_sessions(self, tmux_service, mock_server):
        """Test listing sessions."""
        # Create mock sessions
        mock_session1 = MagicMock()
        mock_session1.name = "cc-orchestrator-session1"
        mock_session1.attached = True
        mock_session1.start_directory = "/tmp/session1"
        mock_window1 = MagicMock()
        mock_window1.name = "main"
        mock_session1.windows = [mock_window1]
        mock_session1.active_window = mock_window1
        mock_session1.clients = []

        mock_session2 = MagicMock()
        mock_session2.name = "cc-orchestrator-session2"
        mock_session2.attached = False
        mock_session2.start_directory = "/tmp/session2"
        mock_window2 = MagicMock()
        mock_window2.name = "terminal"
        mock_session2.windows = [mock_window2]
        mock_session2.active_window = mock_window2
        mock_session2.clients = []

        mock_server.sessions = [mock_session1, mock_session2]

        sessions = await tmux_service.list_sessions()

        assert len(sessions) == 2
        assert sessions[0].session_name == "cc-orchestrator-session1"
        assert sessions[0].status == SessionStatus.ACTIVE
        assert sessions[1].session_name == "cc-orchestrator-session2"
        assert sessions[1].status == SessionStatus.DETACHED

    @pytest.mark.asyncio
    async def test_cleanup_sessions_all(self, tmux_service, mock_server):
        """Test cleaning up all sessions."""
        # Add sessions to tracking
        session1 = SessionInfo(
            session_name="cc-orchestrator-session1",
            instance_id="instance1",
            status=SessionStatus.ACTIVE,
            working_directory=Path("/tmp"),
            layout_template="default",
            created_at=1234567890.0,
            windows=["main"],
        )
        session2 = SessionInfo(
            session_name="cc-orchestrator-session2",
            instance_id="instance2",
            status=SessionStatus.DETACHED,
            working_directory=Path("/tmp"),
            layout_template="default",
            created_at=1234567890.0,
            windows=["main"],
        )
        tmux_service._sessions = {
            "cc-orchestrator-session1": session1,
            "cc-orchestrator-session2": session2,
        }

        # Mock destroy_session to return True
        with patch.object(tmux_service, "destroy_session", return_value=True) as mock_destroy:
            result = await tmux_service.cleanup_sessions()

        assert result == 2
        assert mock_destroy.call_count == 2

    @pytest.mark.asyncio
    async def test_cleanup_sessions_by_instance(self, tmux_service, mock_server):
        """Test cleaning up sessions for specific instance."""
        # Add sessions to tracking
        session1 = SessionInfo(
            session_name="cc-orchestrator-session1",
            instance_id="instance1",
            status=SessionStatus.ACTIVE,
            working_directory=Path("/tmp"),
            layout_template="default",
            created_at=1234567890.0,
            windows=["main"],
        )
        session2 = SessionInfo(
            session_name="cc-orchestrator-session2",
            instance_id="instance2",
            status=SessionStatus.DETACHED,
            working_directory=Path("/tmp"),
            layout_template="default",
            created_at=1234567890.0,
            windows=["main"],
        )
        tmux_service._sessions = {
            "cc-orchestrator-session1": session1,
            "cc-orchestrator-session2": session2,
        }

        # Mock destroy_session to return True
        with patch.object(tmux_service, "destroy_session", return_value=True) as mock_destroy:
            result = await tmux_service.cleanup_sessions(instance_id="instance1")

        assert result == 1
        mock_destroy.assert_called_once_with("cc-orchestrator-session1", force=False)

    def test_add_layout_template(self, tmux_service):
        """Test adding custom layout template."""
        template = LayoutTemplate(
            name="custom",
            description="Custom template",
            windows=[
                {
                    "name": "custom-window",
                    "command": "zsh",
                    "panes": [{"command": "zsh"}],
                }
            ],
        )

        tmux_service.add_layout_template(template)
        assert "custom" in tmux_service._layout_templates
        assert tmux_service._layout_templates["custom"] == template

    def test_get_layout_templates(self, tmux_service):
        """Test getting layout templates."""
        templates = tmux_service.get_layout_templates()
        assert "default" in templates
        assert "development" in templates
        assert "claude" in templates
        assert isinstance(templates, dict)

        # Verify it's a copy
        templates["test"] = "modified"
        original_templates = tmux_service.get_layout_templates()
        assert "test" not in original_templates


class TestTmuxError:
    """Test TmuxError exception."""

    def test_tmux_error_creation(self):
        """Test TmuxError creation."""
        error = TmuxError("Test error message")
        assert str(error) == "Test error message"
        assert error.session_name is None

    def test_tmux_error_with_session_name(self):
        """Test TmuxError with session name."""
        error = TmuxError("Test error message", session_name="test-session")
        assert str(error) == "Test error message"
        assert error.session_name == "test-session"