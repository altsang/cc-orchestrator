"""
Comprehensive test coverage for tmux service functionality.

This test file aims for 100% statement coverage of src/cc_orchestrator/tmux/service.py
covering all classes, methods, error conditions, and edge cases.
"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, PropertyMock, call, patch

import pytest

from cc_orchestrator.tmux.service import (
    LayoutTemplate,
    SessionConfig,
    SessionInfo,
    SessionStatus,
    TmuxError,
    TmuxService,
    cleanup_tmux_service,
    get_tmux_service,
)


class TestSessionStatus:
    """Test SessionStatus enum."""

    def test_session_status_values(self):
        """Test all SessionStatus enum values."""
        assert SessionStatus.CREATING.value == "creating"
        assert SessionStatus.ACTIVE.value == "active"
        assert SessionStatus.DETACHED.value == "detached"
        assert SessionStatus.STOPPING.value == "stopping"
        assert SessionStatus.STOPPED.value == "stopped"
        assert SessionStatus.ERROR.value == "error"


class TestSessionConfig:
    """Test SessionConfig dataclass with comprehensive edge cases."""

    def test_session_config_minimal(self):
        """Test SessionConfig with minimal required fields."""
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
        assert config.window_configs is None
        assert config.auto_attach is False
        assert config.persist_after_exit is True

    def test_session_config_all_fields(self):
        """Test SessionConfig with all fields."""
        config = SessionConfig(
            session_name="test-session",
            working_directory=Path("/tmp/test"),
            instance_id="test-instance",
            layout_template="development",
            environment={"TEST_VAR": "value"},
            window_configs=[{"name": "test-window", "command": "bash"}],
            auto_attach=True,
            persist_after_exit=False,
        )
        assert config.layout_template == "development"
        assert config.environment == {"TEST_VAR": "value"}
        assert config.window_configs == [{"name": "test-window", "command": "bash"}]
        assert config.auto_attach is True
        assert config.persist_after_exit is False


class TestSessionInfo:
    """Test SessionInfo dataclass with all field combinations."""

    def test_session_info_minimal(self):
        """Test SessionInfo with minimal required fields."""
        info = SessionInfo(
            session_name="cc-orchestrator-test",
            instance_id="test-instance",
            status=SessionStatus.ACTIVE,
            working_directory=Path("/tmp/test"),
            layout_template="default",
            created_at=1234567890.0,
            windows=["main"],
        )
        assert info.session_name == "cc-orchestrator-test"
        assert info.instance_id == "test-instance"
        assert info.status == SessionStatus.ACTIVE
        assert info.working_directory == Path("/tmp/test")
        assert info.layout_template == "default"
        assert info.created_at == 1234567890.0
        assert info.windows == ["main"]
        assert info.current_window is None
        assert info.last_activity is None
        assert info.attached_clients == 0
        assert info.environment is None

    def test_session_info_all_fields(self):
        """Test SessionInfo with all fields populated."""
        info = SessionInfo(
            session_name="cc-orchestrator-test",
            instance_id="test-instance",
            status=SessionStatus.ACTIVE,
            working_directory=Path("/tmp/test"),
            layout_template="default",
            created_at=1234567890.0,
            windows=["main", "secondary"],
            current_window="main",
            last_activity=1234567900.0,
            attached_clients=2,
            environment={"VAR": "value"},
        )
        assert info.current_window == "main"
        assert info.last_activity == 1234567900.0
        assert info.attached_clients == 2
        assert info.environment == {"VAR": "value"}


class TestLayoutTemplate:
    """Test LayoutTemplate class with various configurations."""

    def test_layout_template_default_pane_command(self):
        """Test LayoutTemplate with default pane command."""
        template = LayoutTemplate(
            name="test",
            description="Test template",
            windows=[],
        )
        assert template.name == "test"
        assert template.description == "Test template"
        assert template.windows == []
        assert template.default_pane_command == "bash"

    def test_layout_template_custom_pane_command(self):
        """Test LayoutTemplate with custom pane command."""
        template = LayoutTemplate(
            name="test",
            description="Test template",
            windows=[],
            default_pane_command="zsh",
        )
        assert template.default_pane_command == "zsh"

    def test_layout_template_complex_windows(self):
        """Test LayoutTemplate with complex window configurations."""
        windows = [
            {
                "name": "editor",
                "command": "vim",
                "panes": [
                    {"command": "vim"},
                    {"command": "bash", "split": "horizontal"},
                ],
            },
            {
                "name": "server",
                "command": "python -m http.server",
                "panes": [{"command": "python -m http.server"}],
            },
        ]
        template = LayoutTemplate(
            name="complex",
            description="Complex template",
            windows=windows,
            default_pane_command="fish",
        )
        assert template.windows == windows
        assert template.default_pane_command == "fish"


class TestTmuxServiceComprehensive:
    """Comprehensive test cases for TmuxService class covering all methods and edge cases."""

    @pytest.fixture
    def mock_server(self):
        """Mock libtmux server."""
        with patch("cc_orchestrator.tmux.service.libtmux.Server") as mock:
            server_instance = MagicMock()
            mock.return_value = server_instance
            yield server_instance

    @pytest.fixture
    def mock_logging(self):
        """Mock all logging functions."""
        with (
            patch("cc_orchestrator.tmux.service.log_session_operation") as log_op,
            patch("cc_orchestrator.tmux.service.log_session_attach") as log_attach,
            patch("cc_orchestrator.tmux.service.log_session_detach") as log_detach,
            patch("cc_orchestrator.tmux.service.log_session_cleanup") as log_cleanup,
            patch("cc_orchestrator.tmux.service.log_session_list") as log_list,
            patch("cc_orchestrator.tmux.service.log_orphaned_sessions") as log_orphaned,
            patch("cc_orchestrator.tmux.service.log_layout_setup") as log_layout,
            patch("cc_orchestrator.tmux.service.tmux_logger") as logger,
        ):
            yield {
                "operation": log_op,
                "attach": log_attach,
                "detach": log_detach,
                "cleanup": log_cleanup,
                "list": log_list,
                "orphaned": log_orphaned,
                "layout": log_layout,
                "logger": logger,
            }

    @pytest.fixture
    def tmux_service(self, mock_server, mock_logging):
        """Create TmuxService instance with mocked dependencies."""
        return TmuxService()

    def test_tmux_service_initialization_complete(
        self, tmux_service, mock_server, mock_logging
    ):
        """Test complete TmuxService initialization."""
        assert tmux_service._server is mock_server
        assert tmux_service._sessions == {}
        assert tmux_service._session_prefix == "cc-orchestrator"

        # Test all default templates are initialized
        templates = tmux_service._layout_templates
        assert "default" in templates
        assert "development" in templates
        assert "claude" in templates

        # Verify template contents
        default_template = templates["default"]
        assert default_template.name == "default"
        assert default_template.description == "Single window with default shell"
        assert len(default_template.windows) == 1

        dev_template = templates["development"]
        assert dev_template.name == "development"
        assert len(dev_template.windows) == 3

        claude_template = templates["claude"]
        assert claude_template.name == "claude"
        assert len(claude_template.windows) == 2

        # Verify logging was called
        mock_logging["logger"].info.assert_called_with("Tmux service initialized")

    def test_normalize_session_name_edge_cases(self, tmux_service):
        """Test session name normalization with edge cases."""
        # Empty string
        result = tmux_service._normalize_session_name("")
        assert result == "cc-orchestrator-"

        # Already has prefix
        result = tmux_service._normalize_session_name("cc-orchestrator-test")
        assert result == "cc-orchestrator-test"

        # Partial prefix match (shouldn't be treated as full prefix)
        result = tmux_service._normalize_session_name("cc-test")
        assert result == "cc-orchestrator-cc-test"

        # Long session name
        long_name = "a" * 100
        result = tmux_service._normalize_session_name(long_name)
        assert result == f"cc-orchestrator-{long_name}"

    def test_extract_instance_id_edge_cases(self, tmux_service):
        """Test instance ID extraction with edge cases."""
        # With exact prefix
        result = tmux_service._extract_instance_id("cc-orchestrator-test")
        assert result == "test"

        # Without prefix
        result = tmux_service._extract_instance_id("simple-name")
        assert result == "simple-name"

        # Empty string after prefix
        result = tmux_service._extract_instance_id("cc-orchestrator-")
        assert result == ""

        # Just the prefix (no hyphen after prefix, returns slice from after assumed hyphen)
        result = tmux_service._extract_instance_id("cc-orchestrator")
        assert (
            result == ""
        )  # Returns empty string because slice is beyond string length

    @pytest.mark.asyncio
    async def test_session_exists_edge_cases(self, tmux_service, mock_server):
        """Test session_exists with various edge cases."""
        # Session exists
        mock_session = MagicMock()
        mock_server.sessions.get.return_value = mock_session
        result = await tmux_service.session_exists("test")
        assert result is True

        # Session doesn't exist (returns None)
        mock_server.sessions.get.return_value = None
        result = await tmux_service.session_exists("nonexistent")
        assert result is False

        # Various exception types
        mock_server.sessions.get.side_effect = AttributeError("No sessions")
        result = await tmux_service.session_exists("error")
        assert result is False

        mock_server.sessions.get.side_effect = ConnectionError("Connection failed")
        result = await tmux_service.session_exists("error")
        assert result is False

    @pytest.mark.asyncio
    async def test_create_session_working_directory_creation(
        self, tmux_service, mock_server, tmp_path, mock_logging
    ):
        """Test session creation with working directory creation."""
        # Directory doesn't exist
        new_dir = tmp_path / "nonexistent" / "nested"
        config = SessionConfig(
            session_name="test",
            working_directory=new_dir,
            instance_id="test-instance",
        )

        mock_session = MagicMock()
        mock_window = MagicMock()
        mock_window.name = "main"
        mock_session.windows = [mock_window]
        mock_server.new_session.return_value = mock_session
        mock_server.sessions.get.return_value = None

        with patch("asyncio.get_event_loop") as mock_loop:
            mock_loop.return_value.time.return_value = 1234567890.0
            result = await tmux_service.create_session(config)

        # Directory should be created
        assert new_dir.exists()
        assert isinstance(result, SessionInfo)

    @pytest.mark.asyncio
    async def test_create_session_with_layout_template_fallback(
        self, tmux_service, mock_server, tmp_path, mock_logging
    ):
        """Test session creation with non-existent layout template falls back to default."""
        config = SessionConfig(
            session_name="test",
            working_directory=tmp_path,
            instance_id="test-instance",
            layout_template="nonexistent",
        )

        mock_session = MagicMock()
        mock_window = MagicMock()
        mock_window.name = "main"
        mock_session.windows = [mock_window]
        mock_server.new_session.return_value = mock_session
        mock_server.sessions.get.return_value = None

        with (
            patch("asyncio.get_event_loop") as mock_loop,
            patch.object(tmux_service, "_apply_layout_template") as mock_apply,
        ):
            mock_loop.return_value.time.return_value = 1234567890.0
            await tmux_service.create_session(config)

        # Should apply default template since nonexistent template doesn't exist
        mock_apply.assert_called_once()
        applied_template = mock_apply.call_args[0][1]
        assert applied_template.name == "default"

    @pytest.mark.asyncio
    async def test_create_session_empty_windows(
        self, tmux_service, mock_server, tmp_path, mock_logging
    ):
        """Test session creation when session has no windows."""
        config = SessionConfig(
            session_name="test",
            working_directory=tmp_path,
            instance_id="test-instance",
        )

        mock_session = MagicMock()
        mock_session.windows = []  # No windows
        mock_server.new_session.return_value = mock_session
        mock_server.sessions.get.return_value = None

        with patch("asyncio.get_event_loop") as mock_loop:
            mock_loop.return_value.time.return_value = 1234567890.0
            result = await tmux_service.create_session(config)

        assert result.windows == []
        assert result.current_window is None

    @pytest.mark.asyncio
    async def test_create_session_windows_with_none_name(
        self, tmux_service, mock_server, tmp_path, mock_logging
    ):
        """Test session creation when windows have None names."""
        config = SessionConfig(
            session_name="test",
            working_directory=tmp_path,
            instance_id="test-instance",
        )

        mock_session = MagicMock()
        mock_window1 = MagicMock()
        mock_window1.name = "main"
        mock_window2 = MagicMock()
        mock_window2.name = None  # Window with no name
        mock_session.windows = [mock_window1, mock_window2]
        mock_server.new_session.return_value = mock_session
        mock_server.sessions.get.return_value = None

        with patch("asyncio.get_event_loop") as mock_loop:
            mock_loop.return_value.time.return_value = 1234567890.0
            result = await tmux_service.create_session(config)

        # Should only include windows with names
        assert result.windows == ["main"]
        assert result.current_window == "main"

    @pytest.mark.asyncio
    async def test_destroy_session_with_attached_property(
        self, tmux_service, mock_server, mock_logging
    ):
        """Test destroy_session checking attached property correctly."""
        mock_session = MagicMock()
        # Use property mock to properly handle 'attached' attribute access
        type(mock_session).attached = PropertyMock(return_value=True)
        mock_server.sessions.get.return_value = mock_session

        with patch.object(tmux_service, "session_exists", return_value=True):
            with pytest.raises(TmuxError, match="has attached clients"):
                await tmux_service.destroy_session("test", force=False)

    @pytest.mark.asyncio
    async def test_destroy_session_force_with_attached(
        self, tmux_service, mock_server, mock_logging
    ):
        """Test force destroying session with attached clients."""
        mock_session = MagicMock()
        type(mock_session).attached = PropertyMock(return_value=True)
        mock_server.sessions.get.return_value = mock_session

        with patch.object(tmux_service, "session_exists", return_value=True):
            result = await tmux_service.destroy_session("test", force=True)
            assert result is True
            mock_session.kill.assert_called_once()

    @pytest.mark.asyncio
    async def test_destroy_session_tmux_error_reraise(
        self, tmux_service, mock_server, mock_logging
    ):
        """Test that TmuxError is re-raised properly."""
        mock_session = MagicMock()
        type(mock_session).attached = PropertyMock(return_value=True)
        mock_server.sessions.get.return_value = mock_session

        with patch.object(tmux_service, "session_exists", return_value=True):
            # Should re-raise TmuxError
            with pytest.raises(TmuxError):
                await tmux_service.destroy_session("test", force=False)

    @pytest.mark.asyncio
    async def test_attach_session_without_tracking(
        self, tmux_service, mock_server, mock_logging
    ):
        """Test attaching to session not in tracking."""
        mock_session = MagicMock()
        mock_server.sessions.get.return_value = mock_session

        with patch.object(tmux_service, "session_exists", return_value=True):
            with patch("asyncio.get_event_loop") as mock_loop:
                mock_loop.return_value.time.return_value = 1234567900.0
                result = await tmux_service.attach_session("test")

        assert result is True
        # Session not in tracking, so no status update

    @pytest.mark.asyncio
    async def test_detach_session_without_tracking(
        self, tmux_service, mock_server, mock_logging
    ):
        """Test detaching from session not in tracking."""
        mock_session = MagicMock()
        mock_server.sessions.get.return_value = mock_session

        with patch("asyncio.get_event_loop") as mock_loop:
            mock_loop.return_value.time.return_value = 1234567900.0
            result = await tmux_service.detach_session("test")

        assert result is True
        mock_session.cmd.assert_called_once_with("detach-client", "-a")

    @pytest.mark.asyncio
    async def test_list_sessions_filter_non_prefixed(
        self, tmux_service, mock_server, mock_logging
    ):
        """Test list_sessions filters out sessions without prefix."""
        mock_session1 = MagicMock()
        mock_session1.name = "cc-orchestrator-test1"
        mock_session1.attached = False
        mock_session1.start_directory = "/tmp"
        mock_window = MagicMock()
        mock_window.name = "main"
        mock_session1.windows = [mock_window]
        mock_session1.active_window = mock_window
        mock_session1.clients = []

        # Non-prefixed session should be filtered out
        mock_session2 = MagicMock()
        mock_session2.name = "regular-session"
        mock_session2.attached = False

        mock_server.sessions = [mock_session1, mock_session2]

        sessions = await tmux_service.list_sessions()

        assert len(sessions) == 1
        assert sessions[0].session_name == "cc-orchestrator-test1"

    @pytest.mark.asyncio
    async def test_list_sessions_with_none_name(
        self, tmux_service, mock_server, mock_logging
    ):
        """Test list_sessions handles sessions with None names."""
        mock_session1 = MagicMock()
        mock_session1.name = "cc-orchestrator-test1"
        mock_session1.attached = False
        mock_session1.start_directory = "/tmp"
        mock_window = MagicMock()
        mock_window.name = "main"
        mock_session1.windows = [mock_window]
        mock_session1.active_window = mock_window
        mock_session1.clients = []

        # Session with None name
        mock_session2 = MagicMock()
        mock_session2.name = None

        mock_server.sessions = [mock_session1, mock_session2]

        sessions = await tmux_service.list_sessions()

        assert len(sessions) == 1
        assert sessions[0].session_name == "cc-orchestrator-test1"

    @pytest.mark.asyncio
    async def test_list_sessions_get_session_info_returns_none(
        self, tmux_service, mock_server, mock_logging
    ):
        """Test list_sessions when _get_session_info returns None."""
        mock_session = MagicMock()
        mock_session.name = "cc-orchestrator-test1"
        mock_server.sessions = [mock_session]

        with patch.object(tmux_service, "_get_session_info", return_value=None):
            sessions = await tmux_service.list_sessions()

        # Should filter out sessions where _get_session_info returns None
        assert len(sessions) == 0

    @pytest.mark.asyncio
    async def test_get_session_info_not_in_tracking_session_none(
        self, tmux_service, mock_server
    ):
        """Test get_session_info when session not in tracking and tmux returns None."""
        mock_server.sessions.get.return_value = None

        result = await tmux_service.get_session_info("test")

        assert result is None

    @pytest.mark.asyncio
    async def test_cleanup_sessions_destroy_failure(
        self, tmux_service, mock_server, mock_logging
    ):
        """Test cleanup_sessions when destroy_session fails."""
        session_info = SessionInfo(
            session_name="cc-orchestrator-test",
            instance_id="test-instance",
            status=SessionStatus.ACTIVE,
            working_directory=Path("/tmp"),
            layout_template="default",
            created_at=1234567890.0,
            windows=["main"],
        )
        tmux_service._sessions = {"cc-orchestrator-test": session_info}

        with patch.object(tmux_service, "destroy_session", return_value=False):
            result = await tmux_service.cleanup_sessions()

        # Should return 0 since destroy_session returned False
        assert result == 0

    def test_add_layout_template_override(self, tmux_service, mock_logging):
        """Test adding layout template that overrides existing one."""
        original_template = tmux_service._layout_templates["default"]

        new_template = LayoutTemplate(
            name="default",
            description="Override default",
            windows=[],
        )

        tmux_service.add_layout_template(new_template)

        assert tmux_service._layout_templates["default"] == new_template
        assert tmux_service._layout_templates["default"] != original_template

    def test_get_layout_templates_immutability(self, tmux_service):
        """Test that get_layout_templates returns a copy."""
        templates = tmux_service.get_layout_templates()
        original_count = len(templates)

        # Modify returned dict
        templates["new_template"] = LayoutTemplate("new", "New template", [])

        # Original should be unchanged
        new_templates = tmux_service.get_layout_templates()
        assert len(new_templates) == original_count
        assert "new_template" not in new_templates

    @pytest.mark.asyncio
    async def test_apply_layout_template_kill_default_window(
        self, tmux_service, mock_logging
    ):
        """Test _apply_layout_template kills default window when template has windows."""
        mock_session = MagicMock()
        mock_session.name = "test-session"

        # Mock default window
        mock_default_window = MagicMock()
        mock_session.windows = [mock_default_window]

        # Mock new window creation
        mock_new_window = MagicMock()
        mock_session.new_window.return_value = mock_new_window
        mock_new_window.panes = [MagicMock()]

        template = LayoutTemplate(
            name="test",
            description="Test",
            windows=[
                {
                    "name": "new-window",
                    "command": "bash",
                    "panes": [{"command": "bash"}],
                }
            ],
        )

        await tmux_service._apply_layout_template(mock_session, template)

        # Default window should be killed
        mock_default_window.kill.assert_called_once()

    @pytest.mark.asyncio
    async def test_apply_layout_template_no_default_window_kill(
        self, tmux_service, mock_logging
    ):
        """Test _apply_layout_template doesn't kill window when no template windows."""
        mock_session = MagicMock()
        mock_session.name = "test-session"
        mock_session.windows = [MagicMock()]

        template = LayoutTemplate(
            name="test",
            description="Test",
            windows=[],  # No windows
        )

        await tmux_service._apply_layout_template(mock_session, template)

        # No windows should be killed
        for window in mock_session.windows:
            window.kill.assert_not_called()

    @pytest.mark.asyncio
    async def test_apply_layout_template_first_window_existing_session(
        self, tmux_service, mock_logging
    ):
        """Test _apply_layout_template handles first window with existing session windows."""
        mock_session = MagicMock()
        mock_session.name = "test-session"

        # Mock existing window
        mock_existing_window = MagicMock()
        mock_session.windows = [mock_existing_window]

        # Mock new window creation for first window
        mock_new_window = MagicMock()
        mock_session.new_window.return_value = mock_new_window
        mock_new_window.panes = [MagicMock()]

        template = LayoutTemplate(
            name="test",
            description="Test",
            windows=[
                {
                    "name": "first-window",
                    "command": "bash",
                    "panes": [{"command": "bash"}],
                }
            ],
        )

        await tmux_service._apply_layout_template(mock_session, template)

        # Should kill existing window and create new one
        mock_existing_window.kill.assert_called_once()
        mock_session.new_window.assert_called_once()

    @pytest.mark.asyncio
    async def test_apply_layout_template_first_window_no_existing_session(
        self, tmux_service, mock_logging
    ):
        """Test _apply_layout_template handles first window with no existing session windows."""
        mock_session = MagicMock()
        mock_session.name = "test-session"
        mock_session.windows = []  # No existing windows

        # Mock new window creation
        mock_new_window = MagicMock()
        mock_session.new_window.return_value = mock_new_window
        mock_new_window.panes = [MagicMock()]

        template = LayoutTemplate(
            name="test",
            description="Test",
            windows=[
                {
                    "name": "first-window",
                    "command": "bash",
                    "panes": [{"command": "bash"}],
                }
            ],
        )

        await tmux_service._apply_layout_template(mock_session, template)

        # Should create new window
        mock_session.new_window.assert_called_once()

    @pytest.mark.asyncio
    async def test_apply_layout_template_pane_configuration(
        self, tmux_service, mock_logging
    ):
        """Test _apply_layout_template with various pane configurations."""
        mock_session = MagicMock()
        mock_session.name = "test-session"
        mock_session.windows = []

        # Mock window and panes
        mock_window = MagicMock()
        mock_session.new_window.return_value = mock_window

        # Mock first pane (existing)
        mock_first_pane = MagicMock()
        mock_window.panes = [mock_first_pane]

        # Mock split panes
        mock_split_pane = MagicMock()
        mock_window.split_window.return_value = mock_split_pane

        template = LayoutTemplate(
            name="test",
            description="Test",
            windows=[
                {
                    "name": "multi-pane",
                    "command": "bash",
                    "panes": [
                        {"command": "bash"},  # First pane (uses existing)
                        {"command": "htop", "split": "vertical"},  # Vertical split
                        {
                            "command": "tail -f /var/log/messages",
                            "split": "horizontal",
                        },  # Horizontal split
                    ],
                }
            ],
        )

        await tmux_service._apply_layout_template(mock_session, template)

        # First pane should send keys
        mock_first_pane.send_keys.assert_called_with("bash")

        # Should create two split windows
        assert mock_window.split_window.call_count == 2

        # Check split directions
        calls = mock_window.split_window.call_args_list
        assert calls[0] == call(vertical=True, attach=False)  # Vertical split
        assert calls[1] == call(vertical=False, attach=False)  # Horizontal split

        # Split panes should send keys
        assert mock_split_pane.send_keys.call_count == 2

    @pytest.mark.asyncio
    async def test_apply_layout_template_default_pane_commands(
        self, tmux_service, mock_logging
    ):
        """Test _apply_layout_template uses default commands when not specified."""
        mock_session = MagicMock()
        mock_session.name = "test-session"
        mock_session.windows = []

        mock_window = MagicMock()
        mock_session.new_window.return_value = mock_window
        mock_pane = MagicMock()
        mock_window.panes = [mock_pane]

        template = LayoutTemplate(
            name="test",
            description="Test",
            windows=[
                {
                    "name": "default-commands",
                    # No command specified, should use template default
                    "panes": [
                        {},  # No command specified, should use template default
                    ],
                }
            ],
            default_pane_command="zsh",
        )

        await tmux_service._apply_layout_template(mock_session, template)

        # Should use template default command
        mock_pane.send_keys.assert_called_with("zsh")

    @pytest.mark.asyncio
    async def test_apply_layout_template_window_default_command(
        self, tmux_service, mock_logging
    ):
        """Test _apply_layout_template uses window command when panes not specified."""
        mock_session = MagicMock()
        mock_session.name = "test-session"
        mock_session.windows = []

        mock_window = MagicMock()
        mock_session.new_window.return_value = mock_window
        mock_pane = MagicMock()
        mock_window.panes = [mock_pane]

        template = LayoutTemplate(
            name="test",
            description="Test",
            windows=[
                {
                    "name": "window-command",
                    "command": "vim",
                    # No panes specified, should create default pane with window command
                }
            ],
        )

        await tmux_service._apply_layout_template(mock_session, template)

        # Should use window command for default pane
        mock_pane.send_keys.assert_called_with("vim")

    @pytest.mark.asyncio
    async def test_apply_layout_template_session_start_directory(
        self, tmux_service, mock_logging
    ):
        """Test _apply_layout_template passes session start directory to windows."""
        mock_session = MagicMock()
        mock_session.name = "test-session"
        mock_session.start_directory = "/tmp/session"
        mock_session.windows = []

        mock_window = MagicMock()
        mock_session.new_window.return_value = mock_window
        mock_window.panes = [MagicMock()]

        template = LayoutTemplate(
            name="test",
            description="Test",
            windows=[
                {
                    "name": "test-window",
                    "command": "bash",
                    "panes": [{"command": "bash"}],
                }
            ],
        )

        await tmux_service._apply_layout_template(mock_session, template)

        # Should pass start directory to new window
        mock_session.new_window.assert_called_once_with(
            window_name="test-window",
            start_directory="/tmp/session",
            attach=False,
        )

    @pytest.mark.asyncio
    async def test_apply_layout_template_no_session_start_directory(
        self, tmux_service, mock_logging
    ):
        """Test _apply_layout_template handles missing session start directory."""
        mock_session = MagicMock()
        mock_session.name = "test-session"
        # No start_directory attribute
        del mock_session.start_directory
        mock_session.windows = []

        mock_window = MagicMock()
        mock_session.new_window.return_value = mock_window
        mock_window.panes = [MagicMock()]

        template = LayoutTemplate(
            name="test",
            description="Test",
            windows=[
                {
                    "name": "test-window",
                    "command": "bash",
                    "panes": [{"command": "bash"}],
                }
            ],
        )

        await tmux_service._apply_layout_template(mock_session, template)

        # Should pass None as start directory
        mock_session.new_window.assert_called_once_with(
            window_name="test-window",
            start_directory=None,
            attach=False,
        )

    @pytest.mark.asyncio
    async def test_get_session_info_with_tracking_no_clients_attribute(
        self, tmux_service
    ):
        """Test _get_session_info when session has no clients attribute."""
        session_info = SessionInfo(
            session_name="test-session",
            instance_id="test-instance",
            status=SessionStatus.ACTIVE,
            working_directory=Path("/tmp"),
            layout_template="default",
            created_at=1234567890.0,
            windows=["main"],
        )
        tmux_service._sessions["test-session"] = session_info

        mock_session = MagicMock()
        mock_session.name = "test-session"
        mock_window = MagicMock()
        mock_window.name = "updated-window"
        mock_session.windows = [mock_window]
        mock_session.active_window = mock_window
        # No clients attribute
        if hasattr(mock_session, "clients"):
            del mock_session.clients

        result = await tmux_service._get_session_info(mock_session)

        assert result is session_info
        assert result.attached_clients == 0

    @pytest.mark.asyncio
    async def test_get_session_info_without_tracking_no_active_window(
        self, tmux_service
    ):
        """Test _get_session_info when session has no active window."""
        mock_session = MagicMock()
        mock_session.name = "test-session"
        mock_session.active_window = None
        mock_session.windows = []
        mock_session.start_directory = "/tmp"
        # Use spec to avoid hasattr returning True for non-existent attributes
        type(mock_session).attached = PropertyMock(return_value=False)
        type(mock_session).clients = PropertyMock(return_value=[])

        result = await tmux_service._get_session_info(mock_session)

        assert result is not None
        assert result.current_window is None

    @pytest.mark.asyncio
    async def test_get_session_info_without_tracking_no_start_directory(
        self, tmux_service
    ):
        """Test _get_session_info when session has no start directory."""
        mock_session = MagicMock()
        mock_session.name = "test-session"
        mock_session.active_window = None
        mock_session.windows = []
        mock_session.start_directory = None  # No start directory
        type(mock_session).attached = PropertyMock(return_value=False)
        type(mock_session).clients = PropertyMock(return_value=[])

        result = await tmux_service._get_session_info(mock_session)

        assert result is not None
        assert result.working_directory == Path("/")

    @pytest.mark.asyncio
    async def test_get_session_info_attached_status_true(self, tmux_service):
        """Test _get_session_info when session is attached."""
        mock_session = MagicMock()
        mock_session.name = "test-session"
        mock_session.windows = []
        mock_session.active_window = None
        mock_session.start_directory = "/tmp"
        type(mock_session).attached = PropertyMock(return_value=True)
        type(mock_session).clients = PropertyMock(return_value=["client1"])

        result = await tmux_service._get_session_info(mock_session)

        assert result is not None
        assert result.status == SessionStatus.ACTIVE
        assert result.attached_clients == 1

    @pytest.mark.asyncio
    async def test_detect_orphaned_sessions_complete(self, tmux_service, mock_server):
        """Test _detect_orphaned_sessions with various session types."""
        # Mock sessions: managed, orphaned, and non-prefixed
        mock_managed = MagicMock()
        mock_managed.name = "cc-orchestrator-managed"

        mock_orphaned = MagicMock()
        mock_orphaned.name = "cc-orchestrator-orphaned"

        mock_non_prefixed = MagicMock()
        mock_non_prefixed.name = "regular-session"

        mock_none_name = MagicMock()
        mock_none_name.name = None

        mock_server.sessions = [
            mock_managed,
            mock_orphaned,
            mock_non_prefixed,
            mock_none_name,
        ]

        # Add managed session to tracking
        tmux_service._sessions["cc-orchestrator-managed"] = SessionInfo(
            session_name="cc-orchestrator-managed",
            instance_id="managed",
            status=SessionStatus.ACTIVE,
            working_directory=Path("/tmp"),
            layout_template="default",
            created_at=1234567890.0,
            windows=["main"],
        )

        result = await tmux_service._detect_orphaned_sessions()

        # Should only return the orphaned session
        assert result == ["cc-orchestrator-orphaned"]


class TestTmuxError:
    """Test TmuxError exception class."""

    def test_tmux_error_minimal(self):
        """Test TmuxError with minimal parameters."""
        error = TmuxError("Test error")
        assert str(error) == "Test error"
        assert error.session_name is None

    def test_tmux_error_with_session_name(self):
        """Test TmuxError with session name."""
        error = TmuxError("Test error", session_name="test-session")
        assert str(error) == "Test error"
        assert error.session_name == "test-session"

    def test_tmux_error_inheritance(self):
        """Test TmuxError inheritance from Exception."""
        error = TmuxError("Test error")
        assert isinstance(error, Exception)


class TestGlobalFunctions:
    """Test global functions for tmux service management."""

    def test_get_tmux_service_singleton(self):
        """Test get_tmux_service returns singleton instance."""
        with patch("cc_orchestrator.tmux.service.TmuxService") as MockTmuxService:
            # Clear global instance
            import cc_orchestrator.tmux.service

            cc_orchestrator.tmux.service._tmux_service = None

            mock_instance = MockTmuxService.return_value

            # First call should create instance
            service1 = get_tmux_service()
            assert service1 is mock_instance
            MockTmuxService.assert_called_once()

            # Second call should return same instance
            service2 = get_tmux_service()
            assert service2 is service1
            # Should not create another instance
            MockTmuxService.assert_called_once()

    def test_get_tmux_service_existing_instance(self):
        """Test get_tmux_service with existing instance."""
        with patch("cc_orchestrator.tmux.service.TmuxService") as MockTmuxService:
            import cc_orchestrator.tmux.service

            # Set existing instance
            existing_instance = MockTmuxService.return_value
            cc_orchestrator.tmux.service._tmux_service = existing_instance

            # Should return existing instance without creating new one
            service = get_tmux_service()
            assert service is existing_instance
            MockTmuxService.assert_not_called()

    @pytest.mark.asyncio
    async def test_cleanup_tmux_service_with_instance(self):
        """Test cleanup_tmux_service with existing instance."""
        with patch("cc_orchestrator.tmux.service.TmuxService") as MockTmuxService:
            import cc_orchestrator.tmux.service

            mock_instance = MockTmuxService.return_value
            mock_instance.cleanup_sessions = AsyncMock()
            cc_orchestrator.tmux.service._tmux_service = mock_instance

            await cleanup_tmux_service()

            mock_instance.cleanup_sessions.assert_called_once_with(force=True)
            # Should clear global instance
            assert cc_orchestrator.tmux.service._tmux_service is None

    @pytest.mark.asyncio
    async def test_cleanup_tmux_service_no_instance(self):
        """Test cleanup_tmux_service with no existing instance."""
        import cc_orchestrator.tmux.service

        cc_orchestrator.tmux.service._tmux_service = None

        # Should not raise any errors
        await cleanup_tmux_service()

        # Should remain None
        assert cc_orchestrator.tmux.service._tmux_service is None


class TestEdgeCasesAndErrorConditions:
    """Test edge cases and error conditions for comprehensive coverage."""

    @pytest.fixture
    def mock_server(self):
        """Mock libtmux server."""
        with patch("cc_orchestrator.tmux.service.libtmux.Server") as mock:
            server_instance = MagicMock()
            mock.return_value = server_instance
            yield server_instance

    @pytest.fixture
    def mock_logging(self):
        """Mock all logging functions."""
        with (
            patch("cc_orchestrator.tmux.service.log_session_operation") as log_op,
            patch("cc_orchestrator.tmux.service.log_session_attach") as log_attach,
            patch("cc_orchestrator.tmux.service.log_session_detach") as log_detach,
            patch("cc_orchestrator.tmux.service.log_session_cleanup") as log_cleanup,
            patch("cc_orchestrator.tmux.service.log_session_list") as log_list,
            patch("cc_orchestrator.tmux.service.log_orphaned_sessions") as log_orphaned,
            patch("cc_orchestrator.tmux.service.log_layout_setup") as log_layout,
            patch("cc_orchestrator.tmux.service.tmux_logger") as logger,
        ):
            yield {
                "operation": log_op,
                "attach": log_attach,
                "detach": log_detach,
                "cleanup": log_cleanup,
                "list": log_list,
                "orphaned": log_orphaned,
                "layout": log_layout,
                "logger": logger,
            }

    @pytest.fixture
    def tmux_service(self, mock_server, mock_logging):
        """Create TmuxService instance with mocked dependencies."""
        return TmuxService()

    @pytest.mark.asyncio
    async def test_create_session_mkdir_exception(
        self, tmux_service, mock_server, tmp_path, mock_logging
    ):
        """Test create_session handles mkdir exceptions."""
        # Create a path that will cause mkdir to fail
        restricted_path = tmp_path / "restricted"
        restricted_path.mkdir()
        restricted_path.chmod(0o444)  # Read-only

        config = SessionConfig(
            session_name="test",
            working_directory=restricted_path / "subdir",
            instance_id="test-instance",
        )

        mock_server.sessions.get.return_value = None

        with pytest.raises(TmuxError):
            await tmux_service.create_session(config)

    @pytest.mark.asyncio
    async def test_create_session_set_environment_exception(
        self, tmux_service, mock_server, tmp_path, mock_logging
    ):
        """Test create_session handles set_environment exceptions."""
        config = SessionConfig(
            session_name="test",
            working_directory=tmp_path,
            instance_id="test-instance",
            environment={"TEST_VAR": "value"},
        )

        mock_session = MagicMock()
        mock_session.set_environment.side_effect = Exception("Set env failed")
        mock_session.windows = []
        mock_server.new_session.return_value = mock_session
        mock_server.sessions.get.return_value = None

        with pytest.raises(TmuxError):
            await tmux_service.create_session(config)

    @pytest.mark.asyncio
    async def test_apply_layout_template_no_windows_in_session(
        self, tmux_service, mock_logging
    ):
        """Test _apply_layout_template when session has no windows."""
        mock_session = MagicMock()
        mock_session.name = "test-session"
        mock_session.windows = []

        template = LayoutTemplate(
            name="test",
            description="Test",
            windows=[
                {
                    "name": "test-window",
                    "command": "bash",
                    "panes": [{"command": "bash"}],
                }
            ],
        )

        # Mock window creation but no panes
        mock_window = MagicMock()
        mock_window.panes = []
        mock_session.new_window.return_value = mock_window

        await tmux_service._apply_layout_template(mock_session, template)

        # Should still attempt to create window
        mock_session.new_window.assert_called_once()

    @pytest.mark.asyncio
    async def test_apply_layout_template_pane_send_keys_exception(
        self, tmux_service, mock_logging
    ):
        """Test _apply_layout_template handles pane send_keys exceptions."""
        mock_session = MagicMock()
        mock_session.name = "test-session"
        mock_session.windows = []

        mock_window = MagicMock()
        mock_session.new_window.return_value = mock_window

        mock_pane = MagicMock()
        mock_pane.send_keys.side_effect = Exception("Send keys failed")
        mock_window.panes = [mock_pane]

        template = LayoutTemplate(
            name="test",
            description="Test",
            windows=[
                {
                    "name": "test-window",
                    "command": "bash",
                    "panes": [{"command": "bash"}],
                }
            ],
        )

        with pytest.raises(TmuxError):
            await tmux_service._apply_layout_template(mock_session, template)

    @pytest.mark.asyncio
    async def test_list_sessions_orphaned_detection_failure(
        self, tmux_service, mock_server, mock_logging
    ):
        """Test list_sessions with failure in orphaned detection."""
        mock_session1 = MagicMock()
        mock_session1.name = "cc-orchestrator-test1"

        mock_server.sessions = [mock_session1]

        # When orphaned detection fails, the entire try block fails and returns empty list
        with patch.object(
            tmux_service,
            "_detect_orphaned_sessions",
            side_effect=Exception("Detection failed"),
        ):
            sessions = await tmux_service.list_sessions(include_orphaned=True)

        # Should return empty list due to exception in the outer try-catch
        assert len(sessions) == 0


class TestAdditionalCoverageScenarios:
    """Additional test scenarios to achieve 100% coverage for specific uncovered lines."""

    @pytest.fixture
    def mock_server(self):
        """Mock libtmux server."""
        with patch("cc_orchestrator.tmux.service.libtmux.Server") as mock:
            server_instance = MagicMock()
            mock.return_value = server_instance
            yield server_instance

    @pytest.fixture
    def mock_logging(self):
        """Mock all logging functions."""
        with (
            patch("cc_orchestrator.tmux.service.log_session_operation") as log_op,
            patch("cc_orchestrator.tmux.service.log_session_attach") as log_attach,
            patch("cc_orchestrator.tmux.service.log_session_detach") as log_detach,
            patch("cc_orchestrator.tmux.service.log_session_cleanup") as log_cleanup,
            patch("cc_orchestrator.tmux.service.log_session_list") as log_list,
            patch("cc_orchestrator.tmux.service.log_orphaned_sessions") as log_orphaned,
            patch("cc_orchestrator.tmux.service.log_layout_setup") as log_layout,
            patch("cc_orchestrator.tmux.service.tmux_logger") as logger,
        ):
            yield {
                "operation": log_op,
                "attach": log_attach,
                "detach": log_detach,
                "cleanup": log_cleanup,
                "list": log_list,
                "orphaned": log_orphaned,
                "layout": log_layout,
                "logger": logger,
            }

    @pytest.fixture
    def tmux_service(self, mock_server, mock_logging):
        """Create TmuxService instance with mocked dependencies."""
        return TmuxService()

    @pytest.mark.asyncio
    async def test_create_session_session_exists_raises_error(
        self, tmux_service, mock_server, tmp_path, mock_logging
    ):
        """Test create_session when session already exists (line 121)."""
        config = SessionConfig(
            session_name="existing-session",
            working_directory=tmp_path,
            instance_id="test-instance",
        )

        # Mock session_exists to return True
        with patch.object(tmux_service, "session_exists", return_value=True):
            with pytest.raises(TmuxError, match="Session .* already exists"):
                await tmux_service.create_session(config)

    @pytest.mark.asyncio
    async def test_create_session_auto_attach_failure(
        self, tmux_service, mock_server, tmp_path, mock_logging
    ):
        """Test create_session with auto_attach that fails (line 165)."""
        config = SessionConfig(
            session_name="test-session",
            working_directory=tmp_path,
            instance_id="test-instance",
            auto_attach=True,
        )

        mock_session = MagicMock()
        mock_window = MagicMock()
        mock_window.name = "main"
        mock_session.windows = [mock_window]
        mock_server.new_session.return_value = mock_session
        mock_server.sessions.get.return_value = None

        with (
            patch("asyncio.get_event_loop") as mock_loop,
            patch.object(
                tmux_service, "attach_session", return_value=False
            ) as mock_attach,
        ):
            mock_loop.return_value.time.return_value = 1234567890.0

            # Should not raise error even if attach fails
            result = await tmux_service.create_session(config)

            assert isinstance(result, SessionInfo)
            mock_attach.assert_called_once()

    @pytest.mark.asyncio
    async def test_destroy_session_session_does_not_exist(
        self, tmux_service, mock_server, mock_logging
    ):
        """Test destroy_session when session doesn't exist (lines 192-193)."""
        with patch.object(tmux_service, "session_exists", return_value=False):
            result = await tmux_service.destroy_session("nonexistent")
            assert result is False

        # Should log warning
        mock_logging["logger"].warning.assert_called_once()

    @pytest.mark.asyncio
    async def test_destroy_session_server_returns_none(
        self, tmux_service, mock_server, mock_logging
    ):
        """Test destroy_session when server returns None for session (lines 199-200)."""
        mock_server.sessions.get.return_value = None

        with patch.object(tmux_service, "session_exists", return_value=True):
            result = await tmux_service.destroy_session("test")
            assert result is False

    @pytest.mark.asyncio
    async def test_destroy_session_not_in_tracking(
        self, tmux_service, mock_server, mock_logging
    ):
        """Test destroy_session when session not in tracking (line 213)."""
        mock_session = MagicMock()
        mock_session.attached = False
        mock_server.sessions.get.return_value = mock_session

        # Ensure session is not in tracking
        assert "cc-orchestrator-test" not in tmux_service._sessions

        with patch.object(tmux_service, "session_exists", return_value=True):
            result = await tmux_service.destroy_session("test")
            assert result is True
            mock_session.kill.assert_called_once()

    @pytest.mark.asyncio
    async def test_destroy_session_exception_handling_generic(
        self, tmux_service, mock_server, mock_logging
    ):
        """Test destroy_session with generic exception (lines 223-226)."""
        mock_session = MagicMock()
        mock_session.attached = False
        mock_session.kill.side_effect = RuntimeError("Generic error")
        mock_server.sessions.get.return_value = mock_session

        with patch.object(tmux_service, "session_exists", return_value=True):
            result = await tmux_service.destroy_session("test")
            assert result is False

        # Should log error
        mock_logging["logger"].error.assert_called()

    @pytest.mark.asyncio
    async def test_attach_session_session_does_not_exist(
        self, tmux_service, mock_server, mock_logging
    ):
        """Test attach_session when session doesn't exist (lines 240-241)."""
        with patch.object(tmux_service, "session_exists", return_value=False):
            result = await tmux_service.attach_session("nonexistent")
            assert result is False

        # Should log error
        mock_logging["logger"].error.assert_called_once()

    @pytest.mark.asyncio
    async def test_attach_session_server_returns_none(
        self, tmux_service, mock_server, mock_logging
    ):
        """Test attach_session when server returns None (lines 245-246)."""
        mock_server.sessions.get.return_value = None

        with patch.object(tmux_service, "session_exists", return_value=True):
            result = await tmux_service.attach_session("test")
            assert result is False

    @pytest.mark.asyncio
    async def test_attach_session_not_in_tracking(
        self, tmux_service, mock_server, mock_logging
    ):
        """Test attach_session when session not in tracking (lines 250-251, 257-258)."""
        mock_session = MagicMock()
        mock_server.sessions.get.return_value = mock_session

        # Ensure session is not in tracking
        assert "cc-orchestrator-test" not in tmux_service._sessions

        with patch.object(tmux_service, "session_exists", return_value=True):
            result = await tmux_service.attach_session("test")
            assert result is True

        # Should proceed without updating tracking

    @pytest.mark.asyncio
    async def test_attach_session_exception_handling(
        self, tmux_service, mock_server, mock_logging
    ):
        """Test attach_session exception handling (lines 263-265)."""
        mock_server.sessions.get.side_effect = Exception("Server error")

        with patch.object(tmux_service, "session_exists", return_value=True):
            result = await tmux_service.attach_session("test")
            assert result is False

        # Should log error
        mock_logging["logger"].error.assert_called()

    @pytest.mark.asyncio
    async def test_detach_session_server_returns_none(
        self, tmux_service, mock_server, mock_logging
    ):
        """Test detach_session when server returns None (line 281)."""
        mock_server.sessions.get.return_value = None

        result = await tmux_service.detach_session("test")
        assert result is False

    @pytest.mark.asyncio
    async def test_detach_session_not_in_tracking(
        self, tmux_service, mock_server, mock_logging
    ):
        """Test detach_session when session not in tracking (lines 288-289, 295-296)."""
        mock_session = MagicMock()
        mock_server.sessions.get.return_value = mock_session

        # Ensure session is not in tracking
        assert "cc-orchestrator-test" not in tmux_service._sessions

        result = await tmux_service.detach_session("test")
        assert result is True
        mock_session.cmd.assert_called_once_with("detach-client", "-a")

    @pytest.mark.asyncio
    async def test_detach_session_exception_handling(
        self, tmux_service, mock_server, mock_logging
    ):
        """Test detach_session exception handling (lines 301-303)."""
        mock_session = MagicMock()
        mock_session.cmd.side_effect = Exception("Detach failed")
        mock_server.sessions.get.return_value = mock_session

        result = await tmux_service.detach_session("test")
        assert result is False

        # Should log error
        mock_logging["logger"].error.assert_called()

    @pytest.mark.asyncio
    async def test_list_sessions_include_orphaned_with_orphaned_found(
        self, tmux_service, mock_server, mock_logging
    ):
        """Test list_sessions with orphaned sessions found (line 346)."""
        mock_session = MagicMock()
        mock_session.name = "cc-orchestrator-test"
        mock_session.attached = False
        mock_session.start_directory = "/tmp"
        mock_window = MagicMock()
        mock_window.name = "main"
        mock_session.windows = [mock_window]
        mock_session.active_window = mock_window
        mock_session.clients = []

        mock_server.sessions = [mock_session]

        with patch.object(
            tmux_service,
            "_detect_orphaned_sessions",
            return_value=["cc-orchestrator-orphaned"],
        ):
            sessions = await tmux_service.list_sessions(include_orphaned=True)

        assert len(sessions) == 1
        # Should log orphaned sessions
        mock_logging["orphaned"].assert_called_once_with(["cc-orchestrator-orphaned"])

    @pytest.mark.asyncio
    async def test_get_session_info_in_tracking(self, tmux_service):
        """Test get_session_info when session exists in tracking (line 367)."""
        session_info = SessionInfo(
            session_name="cc-orchestrator-test",
            instance_id="test-instance",
            status=SessionStatus.ACTIVE,
            working_directory=Path("/tmp"),
            layout_template="default",
            created_at=1234567890.0,
            windows=["main"],
        )
        tmux_service._sessions["cc-orchestrator-test"] = session_info

        result = await tmux_service.get_session_info("test")
        assert result is session_info

    @pytest.mark.asyncio
    async def test_get_session_info_tmux_direct_with_session(
        self, tmux_service, mock_server
    ):
        """Test get_session_info from tmux directly when session exists (line 373)."""
        mock_session = MagicMock()
        mock_session.name = "cc-orchestrator-test"
        mock_server.sessions.get.return_value = mock_session

        with patch.object(tmux_service, "_get_session_info") as mock_get_info:
            mock_session_info = SessionInfo(
                session_name="cc-orchestrator-test",
                instance_id="test",
                status=SessionStatus.ACTIVE,
                working_directory=Path("/tmp"),
                layout_template="default",
                created_at=1234567890.0,
                windows=["main"],
            )
            mock_get_info.return_value = mock_session_info

            result = await tmux_service.get_session_info("test")
            assert result is mock_session_info

    @pytest.mark.asyncio
    async def test_get_session_info_exception_debug_log(
        self, tmux_service, mock_server, mock_logging
    ):
        """Test get_session_info exception handling debug log (lines 374-375)."""
        mock_server.sessions.get.side_effect = Exception("Server error")

        result = await tmux_service.get_session_info("test")
        assert result is None

        # Should log debug message
        mock_logging["logger"].debug.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_sessions_with_specific_instance(
        self, tmux_service, mock_logging
    ):
        """Test cleanup_sessions with specific instance (lines 398-400)."""
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
            status=SessionStatus.ACTIVE,
            working_directory=Path("/tmp"),
            layout_template="default",
            created_at=1234567890.0,
            windows=["main"],
        )

        tmux_service._sessions = {
            "cc-orchestrator-session1": session1,
            "cc-orchestrator-session2": session2,
        }

        with patch.object(tmux_service, "destroy_session", return_value=True):
            result = await tmux_service.cleanup_sessions(instance_id="instance1")

        assert result == 1  # Only one session should be cleaned up

    @pytest.mark.asyncio
    async def test_cleanup_sessions_destroy_session_failure(
        self, tmux_service, mock_logging
    ):
        """Test cleanup_sessions when destroy_session fails (line 407)."""
        session_info = SessionInfo(
            session_name="cc-orchestrator-test",
            instance_id="test-instance",
            status=SessionStatus.ACTIVE,
            working_directory=Path("/tmp"),
            layout_template="default",
            created_at=1234567890.0,
            windows=["main"],
        )
        tmux_service._sessions = {"cc-orchestrator-test": session_info}

        with patch.object(tmux_service, "destroy_session", return_value=False):
            result = await tmux_service.cleanup_sessions()

        assert result == 0  # No sessions cleaned due to failure

    @pytest.mark.asyncio
    async def test_cleanup_sessions_exception_handling(
        self, tmux_service, mock_logging
    ):
        """Test cleanup_sessions exception handling (lines 416-418)."""
        session_info = SessionInfo(
            session_name="cc-orchestrator-test",
            instance_id="test-instance",
            status=SessionStatus.ACTIVE,
            working_directory=Path("/tmp"),
            layout_template="default",
            created_at=1234567890.0,
            windows=["main"],
        )
        tmux_service._sessions = {"cc-orchestrator-test": session_info}

        with patch.object(
            tmux_service, "destroy_session", side_effect=Exception("Cleanup failed")
        ):
            result = await tmux_service.cleanup_sessions()

        assert result == 0  # Should return 0 due to exception
        mock_logging["logger"].error.assert_called()

    @pytest.mark.asyncio
    async def test_get_session_info_no_name_early_return(self, tmux_service):
        """Test _get_session_info with no session name (line 618)."""
        mock_session = MagicMock()
        mock_session.name = None

        result = await tmux_service._get_session_info(mock_session)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_session_info_exception_handling_internal(
        self, tmux_service, mock_logging
    ):
        """Test _get_session_info exception handling (lines 641-643)."""
        mock_session = MagicMock()
        mock_session.name = "test-session"
        # Make accessing the name property raise an exception
        type(mock_session).name = PropertyMock(side_effect=Exception("Session error"))

        result = await tmux_service._get_session_info(mock_session)
        assert result is None

        mock_logging["logger"].debug.assert_called_once()

    @pytest.mark.asyncio
    async def test_detect_orphaned_sessions_exception_handling(
        self, tmux_service, mock_server, mock_logging
    ):
        """Test _detect_orphaned_sessions exception handling (lines 676-677)."""
        mock_server.sessions.__iter__.side_effect = Exception("Server error")

        result = await tmux_service._detect_orphaned_sessions()
        assert result == []

        mock_logging["logger"].debug.assert_called_once()


class TestFinalCoverageScenarios:
    """Final test scenarios to achieve 100% coverage for the remaining uncovered lines."""

    @pytest.fixture
    def mock_server(self):
        """Mock libtmux server."""
        with patch("cc_orchestrator.tmux.service.libtmux.Server") as mock:
            server_instance = MagicMock()
            mock.return_value = server_instance
            yield server_instance

    @pytest.fixture
    def mock_logging(self):
        """Mock all logging functions."""
        with (
            patch("cc_orchestrator.tmux.service.log_session_operation") as log_op,
            patch("cc_orchestrator.tmux.service.log_session_attach") as log_attach,
            patch("cc_orchestrator.tmux.service.log_session_detach") as log_detach,
            patch("cc_orchestrator.tmux.service.log_session_cleanup") as log_cleanup,
            patch("cc_orchestrator.tmux.service.log_session_list") as log_list,
            patch("cc_orchestrator.tmux.service.log_orphaned_sessions") as log_orphaned,
            patch("cc_orchestrator.tmux.service.log_layout_setup") as log_layout,
            patch("cc_orchestrator.tmux.service.tmux_logger") as logger,
        ):
            yield {
                "operation": log_op,
                "attach": log_attach,
                "detach": log_detach,
                "cleanup": log_cleanup,
                "list": log_list,
                "orphaned": log_orphaned,
                "layout": log_layout,
                "logger": logger,
            }

    @pytest.fixture
    def tmux_service(self, mock_server, mock_logging):
        """Create TmuxService instance with mocked dependencies."""
        return TmuxService()

    @pytest.mark.asyncio
    async def test_destroy_session_in_tracking(
        self, tmux_service, mock_server, mock_logging
    ):
        """Test destroy_session when session is in tracking (line 213)."""
        # Add session to tracking first
        session_info = SessionInfo(
            session_name="cc-orchestrator-test",
            instance_id="test-instance",
            status=SessionStatus.ACTIVE,
            working_directory=Path("/tmp"),
            layout_template="default",
            created_at=1234567890.0,
            windows=["main"],
        )
        tmux_service._sessions["cc-orchestrator-test"] = session_info

        mock_session = MagicMock()
        mock_session.attached = False
        mock_server.sessions.get.return_value = mock_session

        with patch.object(tmux_service, "session_exists", return_value=True):
            result = await tmux_service.destroy_session("test")
            assert result is True

        # Should remove from tracking (line 213)
        assert "cc-orchestrator-test" not in tmux_service._sessions

    @pytest.mark.asyncio
    async def test_attach_session_in_tracking(
        self, tmux_service, mock_server, mock_logging
    ):
        """Test attach_session when session is in tracking (lines 250-251, 258)."""
        # Add session to tracking first
        session_info = SessionInfo(
            session_name="cc-orchestrator-test",
            instance_id="test-instance",
            status=SessionStatus.DETACHED,
            working_directory=Path("/tmp"),
            layout_template="default",
            created_at=1234567890.0,
            windows=["main"],
        )
        tmux_service._sessions["cc-orchestrator-test"] = session_info

        mock_session = MagicMock()
        mock_server.sessions.get.return_value = mock_session

        with patch.object(tmux_service, "session_exists", return_value=True):
            with patch("asyncio.get_event_loop") as mock_loop:
                mock_loop.return_value.time.return_value = 1234567900.0
                result = await tmux_service.attach_session("test")

        assert result is True
        # Should update status and last_activity (lines 250-251)
        assert session_info.status == SessionStatus.ACTIVE
        assert session_info.last_activity == 1234567900.0

    @pytest.mark.asyncio
    async def test_detach_session_in_tracking(
        self, tmux_service, mock_server, mock_logging
    ):
        """Test detach_session when session is in tracking (lines 288-289, 296)."""
        # Add session to tracking first
        session_info = SessionInfo(
            session_name="cc-orchestrator-test",
            instance_id="test-instance",
            status=SessionStatus.ACTIVE,
            working_directory=Path("/tmp"),
            layout_template="default",
            created_at=1234567890.0,
            windows=["main"],
        )
        tmux_service._sessions["cc-orchestrator-test"] = session_info

        mock_session = MagicMock()
        mock_server.sessions.get.return_value = mock_session

        with patch("asyncio.get_event_loop") as mock_loop:
            mock_loop.return_value.time.return_value = 1234567900.0
            result = await tmux_service.detach_session("test")

        assert result is True
        # Should update status and last_activity (lines 288-289)
        assert session_info.status == SessionStatus.DETACHED
        assert session_info.last_activity == 1234567900.0
