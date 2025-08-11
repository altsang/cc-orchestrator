"""Unit tests for tmux service functionality."""

from pathlib import Path
from unittest.mock import MagicMock, PropertyMock, patch

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
    async def test_create_session_already_exists(
        self, tmux_service, mock_server, tmp_path
    ):
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
    async def test_create_session_with_environment(
        self, tmux_service, mock_server, tmp_path
    ):
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
    async def test_create_session_with_auto_attach(
        self, tmux_service, mock_server, tmp_path
    ):
        """Test session creation with auto-attach enabled."""
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
            auto_attach=True,
        )

        with patch("asyncio.get_event_loop") as mock_loop:
            mock_loop.return_value.time.return_value = 1234567890.0
            with patch.object(tmux_service, "attach_session") as mock_attach:
                mock_attach.return_value = True

                result = await tmux_service.create_session(config)

        # Verify auto-attach was called
        mock_attach.assert_called_once_with("cc-orchestrator-test-session")
        assert result.session_name == "cc-orchestrator-test-session"

    @pytest.mark.asyncio
    async def test_create_session_exception_handling(
        self, tmux_service, mock_server, tmp_path
    ):
        """Test session creation exception handling."""
        mock_server.sessions.get.return_value = None
        mock_server.new_session.side_effect = Exception("Tmux server error")

        config = SessionConfig(
            session_name="test-session",
            working_directory=tmp_path,
            instance_id="test-instance",
        )

        with pytest.raises(TmuxError, match="Failed to create session"):
            await tmux_service.create_session(config)

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
        mock_session.kill.assert_called_once()  # destroy_session should still use kill()
        assert "cc-orchestrator-test-session" not in tmux_service._sessions

    @pytest.mark.asyncio
    async def test_destroy_session_with_attached_clients(
        self, tmux_service, mock_server
    ):
        """Test session destruction with attached clients."""
        mock_session = MagicMock()
        mock_session.session_attached = True
        mock_server.sessions.get.return_value = mock_session

        with pytest.raises(TmuxError, match="has attached clients"):
            await tmux_service.destroy_session("test-session", force=False)

    @pytest.mark.asyncio
    async def test_destroy_session_force_with_attached_clients(
        self, tmux_service, mock_server
    ):
        """Test forced session destruction with attached clients."""
        mock_session = MagicMock()
        mock_session.session_attached = True
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
    async def test_destroy_session_session_none_from_server(
        self, tmux_service, mock_server
    ):
        """Test destroying session when server returns None."""
        mock_server.sessions.get.return_value = None

        # Mock session_exists to return True but sessions.get returns None
        with patch.object(tmux_service, "session_exists", return_value=True):
            result = await tmux_service.destroy_session("test-session")
            assert result is False

    @pytest.mark.asyncio
    async def test_destroy_session_exception_handling(self, tmux_service, mock_server):
        """Test destroy_session exception handling."""
        mock_session = MagicMock()
        mock_session.attached = False
        mock_session.kill.side_effect = Exception("Kill failed")
        mock_server.sessions.get.return_value = mock_session

        with patch.object(tmux_service, "session_exists", return_value=True):
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
    async def test_attach_session_server_returns_none(self, tmux_service, mock_server):
        """Test attach when server returns None session."""
        mock_server.sessions.get.return_value = None

        with patch.object(tmux_service, "session_exists", return_value=True):
            result = await tmux_service.attach_session("test-session")
            assert result is False

    @pytest.mark.asyncio
    async def test_attach_session_exception_handling(self, tmux_service, mock_server):
        """Test attach_session exception handling."""
        mock_server.sessions.get.side_effect = Exception("Server error")

        with patch.object(tmux_service, "session_exists", return_value=True):
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
        mock_session.cmd.assert_called_once_with("detach-client", "-a")
        assert session_info.status == SessionStatus.DETACHED
        assert session_info.last_activity == 1234567900.0

    @pytest.mark.asyncio
    async def test_detach_session_server_returns_none(self, tmux_service, mock_server):
        """Test detach when server returns None session."""
        mock_server.sessions.get.return_value = None

        result = await tmux_service.detach_session("test-session")
        assert result is False

    @pytest.mark.asyncio
    async def test_detach_session_exception_handling(self, tmux_service, mock_server):
        """Test detach_session exception handling."""
        mock_session = MagicMock()
        mock_session.cmd.side_effect = Exception("Detach failed")
        mock_server.sessions.get.return_value = mock_session

        result = await tmux_service.detach_session("test-session")
        assert result is False

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
    async def test_list_sessions_with_orphaned(self, tmux_service, mock_server):
        """Test listing sessions with orphaned detection."""
        # Create mock sessions - one managed, one orphaned
        mock_session1 = MagicMock()
        mock_session1.name = "cc-orchestrator-session1"
        mock_session1.attached = True
        mock_session1.start_directory = "/tmp/session1"
        mock_window1 = MagicMock()
        mock_window1.name = "main"
        mock_session1.windows = [mock_window1]
        mock_session1.active_window = mock_window1
        mock_session1.clients = []

        # Orphaned session (not in _sessions tracking)
        mock_orphaned = MagicMock()
        mock_orphaned.name = "cc-orchestrator-orphaned"
        mock_orphaned.session_attached = False
        mock_orphaned.start_directory = "/tmp/orphaned"
        mock_window_orphaned = MagicMock()
        mock_window_orphaned.name = "main"
        mock_orphaned.windows = [mock_window_orphaned]
        mock_orphaned.active_window = mock_window_orphaned
        mock_orphaned.clients = []

        mock_server.sessions = [mock_session1, mock_orphaned]

        sessions = await tmux_service.list_sessions(include_orphaned=True)

        assert len(sessions) == 2
        assert sessions[0].session_name == "cc-orchestrator-session1"
        assert sessions[1].session_name == "cc-orchestrator-orphaned"

    @pytest.mark.asyncio
    async def test_list_sessions_exception_handling(self, tmux_service, mock_server):
        """Test list_sessions exception handling."""
        mock_server.sessions = MagicMock()
        mock_server.sessions.__iter__.side_effect = Exception("Server error")

        sessions = await tmux_service.list_sessions()

        assert sessions == []

    @pytest.mark.asyncio
    async def test_get_session_info_from_tracking(self, tmux_service, tmp_path):
        """Test get_session_info when session exists in tracking."""
        session_info = SessionInfo(
            session_name="cc-orchestrator-test-session",
            instance_id="test-instance",
            status=SessionStatus.ACTIVE,
            working_directory=tmp_path,
            layout_template="default",
            created_at=1234567890.0,
            windows=["main"],
        )
        tmux_service._sessions["cc-orchestrator-test-session"] = session_info

        result = await tmux_service.get_session_info("test-session")

        assert result is session_info
        assert result.session_name == "cc-orchestrator-test-session"

    @pytest.mark.asyncio
    async def test_get_session_info_from_tmux_direct(self, tmux_service, mock_server):
        """Test get_session_info from tmux directly."""
        mock_session = MagicMock()
        mock_session.name = "cc-orchestrator-test-session"
        mock_session.session_attached = True
        mock_session.start_directory = "/tmp/test"
        mock_window = MagicMock()
        mock_window.name = "main"
        mock_session.windows = [mock_window]
        mock_session.active_window = mock_window
        mock_session.clients = []

        mock_server.sessions.get.return_value = mock_session

        result = await tmux_service.get_session_info("test-session")

        assert result is not None
        assert result.session_name == "cc-orchestrator-test-session"
        assert result.instance_id == "test-session"

    @pytest.mark.asyncio
    async def test_get_session_info_exception_handling(self, tmux_service, mock_server):
        """Test get_session_info exception handling."""
        mock_server.sessions.get.side_effect = Exception("Server error")

        result = await tmux_service.get_session_info("test-session")

        assert result is None

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
        with patch.object(
            tmux_service, "destroy_session", return_value=True
        ) as mock_destroy:
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
        with patch.object(
            tmux_service, "destroy_session", return_value=True
        ) as mock_destroy:
            result = await tmux_service.cleanup_sessions(instance_id="instance1")

        assert result == 1
        mock_destroy.assert_called_once_with("cc-orchestrator-session1", force=False)

    @pytest.mark.asyncio
    async def test_cleanup_sessions_exception_handling(self, tmux_service, mock_server):
        """Test cleanup_sessions exception handling."""
        # Add a session to tracking to trigger cleanup
        session_info = SessionInfo(
            session_name="cc-orchestrator-session1",
            instance_id="instance1",
            status=SessionStatus.ACTIVE,
            working_directory=Path("/tmp"),
            layout_template="default",
            created_at=1234567890.0,
            windows=["main"],
        )
        tmux_service._sessions = {"cc-orchestrator-session1": session_info}

        # Mock destroy_session to raise an exception
        with patch.object(
            tmux_service, "destroy_session", side_effect=Exception("Cleanup failed")
        ) as mock_destroy:
            result = await tmux_service.cleanup_sessions()

        # Should return 0 due to exception, but not crash
        assert result == 0
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

    @pytest.mark.asyncio
    async def test_apply_layout_template_exception_handling(self, tmux_service):
        """Test _apply_layout_template exception handling."""
        mock_session = MagicMock()
        mock_session.name = "test-session"
        mock_session.windows = []
        mock_session.new_window.side_effect = Exception("Window creation failed")

        template = LayoutTemplate(
            name="test-template",
            description="Test template",
            windows=[
                {
                    "name": "test-window",
                    "command": "bash",
                    "panes": [{"command": "bash"}],
                }
            ],
        )

        with pytest.raises(TmuxError, match="Failed to apply layout template"):
            await tmux_service._apply_layout_template(mock_session, template)

    @pytest.mark.asyncio
    async def test_apply_layout_template_with_vertical_split(self, tmux_service):
        """Test _apply_layout_template with vertical pane splitting."""
        mock_session = MagicMock()
        mock_session.name = "test-session"
        mock_session.windows = []

        # Mock window creation
        mock_window = MagicMock()
        mock_window.name = "test-window"
        mock_session.new_window.return_value = mock_window

        # Mock pane splitting
        mock_pane = MagicMock()
        mock_window.split_window.return_value = mock_pane

        template = LayoutTemplate(
            name="vertical-template",
            description="Template with vertical split",
            windows=[
                {
                    "name": "test-window",
                    "command": "bash",
                    "panes": [
                        {"command": "bash"},
                        {
                            "command": "htop",
                            "split": "vertical",
                        },  # This should trigger vertical split
                    ],
                }
            ],
        )

        await tmux_service._apply_layout_template(mock_session, template)

        # Verify vertical split was used (vertical=True)
        mock_window.split_window.assert_called_with(vertical=True, attach=False)
        mock_pane.send_keys.assert_called_with("htop")

    @pytest.mark.asyncio
    async def test_get_session_info_with_no_name(self, tmux_service):
        """Test _get_session_info with session that has no name."""
        mock_session = MagicMock()
        mock_session.name = None  # Session with no name

        result = await tmux_service._get_session_info(mock_session)

        # Should return None for sessions with no name
        assert result is None

    @pytest.mark.asyncio
    async def test_list_sessions_orphaned_detection_exception(
        self, tmux_service, mock_server
    ):
        """Test list_sessions with exception during orphaned session detection."""
        # Create a mock session that will cause an exception
        mock_session = MagicMock()
        mock_session.name = "cc-orchestrator-test"

        # Mock sessions list to raise exception during iteration
        def mock_sessions_iter():
            yield mock_session
            raise Exception("Server error during iteration")

        mock_server.sessions.__iter__ = mock_sessions_iter

        # Should not crash, just return empty list
        sessions = await tmux_service.list_sessions(include_orphaned=True)

        # Should handle exception gracefully and return empty list
        assert sessions == []

    @pytest.mark.asyncio
    async def test_detect_orphaned_sessions_exception(self, tmux_service, mock_server):
        """Test _detect_orphaned_sessions with exception during iteration."""
        # Mock server sessions to raise an exception during iteration
        mock_server.sessions.__iter__.side_effect = Exception(
            "Session detection failed"
        )

        # Should handle exception gracefully and return empty list
        result = await tmux_service._detect_orphaned_sessions()

        # Should return empty list on exception
        assert result == []

    @pytest.mark.asyncio
    async def test_get_session_info_from_tracking_with_update(self, tmux_service):
        """Test _get_session_info when session exists in tracking with updates."""
        # Set up existing session in tracking
        session_info = SessionInfo(
            session_name="test-session",
            instance_id="test-instance",
            status=SessionStatus.ACTIVE,
            working_directory=Path("/tmp"),
            layout_template="default",
            created_at=1234567890.0,
            windows=["old-window"],
        )
        tmux_service._sessions["test-session"] = session_info

        # Create mock session with updated info
        mock_session = MagicMock()
        mock_session.name = "test-session"
        mock_window1 = MagicMock()
        mock_window1.name = "new-window"
        mock_session.windows = [mock_window1]
        mock_session.active_window = mock_window1
        mock_session.clients = ["client1"]

        result = await tmux_service._get_session_info(mock_session)

        assert result is session_info
        assert result.windows == ["new-window"]
        assert result.current_window == "new-window"
        assert result.attached_clients == 1

    @pytest.mark.asyncio
    async def test_get_session_info_exception_handling_internal(self, tmux_service):
        """Test _get_session_info exception handling."""
        mock_session = MagicMock()
        mock_session.name = "test-session"
        # Make accessing windows property raise an exception
        type(mock_session).windows = PropertyMock(
            side_effect=Exception("Session error")
        )

        result = await tmux_service._get_session_info(mock_session)

        assert result is None


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
