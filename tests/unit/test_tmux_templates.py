"""Unit tests for tmux layout template functionality."""

from unittest.mock import MagicMock, patch

import pytest

from cc_orchestrator.tmux import (
    LayoutTemplate,
    SessionConfig,
    TmuxService,
)


class TestTmuxTemplates:
    """Test all tmux layout templates work correctly."""

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

    def _create_mock_session_with_window(self, session_name: str = "test-session"):
        """Create a mock session with a default window."""
        mock_session = MagicMock()
        mock_session.name = session_name

        # Mock default window
        mock_window = MagicMock()
        mock_window.name = "default"
        mock_window.panes = [MagicMock()]  # Default pane
        mock_session.windows = [mock_window]

        # Mock window creation
        mock_session.new_window.return_value = mock_window

        return mock_session

    @pytest.mark.asyncio
    async def test_default_template_application(self, tmux_service):
        """Test that default template applies successfully."""
        mock_session = self._create_mock_session_with_window()
        template = tmux_service._layout_templates["default"]

        # Should not raise an exception
        await tmux_service._apply_layout_template(mock_session, template)

        # Verify window was renamed to "main"
        mock_session.windows[0].rename_window.assert_called_once_with("main")

    @pytest.mark.asyncio
    async def test_development_template_application(self, tmux_service):
        """Test that development template applies successfully."""
        mock_session = self._create_mock_session_with_window()
        template = tmux_service._layout_templates["development"]

        # Mock additional windows for development template
        mock_terminal_window = MagicMock()
        mock_terminal_window.name = "terminal"
        mock_terminal_window.panes = [MagicMock()]

        mock_monitoring_window = MagicMock()
        mock_monitoring_window.name = "monitoring"
        mock_monitoring_window.panes = [MagicMock()]
        mock_monitoring_window.split_window.return_value = (
            MagicMock()
        )  # For second pane

        mock_session.new_window.side_effect = [
            mock_terminal_window,
            mock_monitoring_window,
        ]

        # Should not raise an exception
        await tmux_service._apply_layout_template(mock_session, template)

        # Verify first window was renamed to "editor"
        mock_session.windows[0].rename_window.assert_called_once_with("editor")

        # Verify additional windows were created
        assert mock_session.new_window.call_count == 2

    @pytest.mark.asyncio
    async def test_claude_template_application(self, tmux_service):
        """Test that claude template applies successfully."""
        mock_session = self._create_mock_session_with_window()
        template = tmux_service._layout_templates["claude"]

        # Mock shell window for claude template
        mock_shell_window = MagicMock()
        mock_shell_window.name = "shell"
        mock_shell_window.panes = [MagicMock()]

        mock_session.new_window.return_value = mock_shell_window

        # Should not raise an exception
        await tmux_service._apply_layout_template(mock_session, template)

        # Verify first window was renamed to "claude"
        mock_session.windows[0].rename_window.assert_called_once_with("claude")

        # Verify additional window was created for shell
        mock_session.new_window.assert_called_once()

    @pytest.mark.asyncio
    async def test_template_with_pane_splitting(self, tmux_service):
        """Test template with horizontal pane splitting works."""
        mock_session = self._create_mock_session_with_window()

        # Create a custom template with pane splitting
        template = LayoutTemplate(
            name="test-split",
            description="Test template with pane splitting",
            windows=[
                {
                    "name": "split-window",
                    "command": "bash",
                    "panes": [
                        {"command": "bash"},
                        {"command": "top", "split": "horizontal"},
                        {"command": "htop", "split": "vertical"},
                    ],
                }
            ],
        )

        # Mock pane splitting
        mock_h_pane = MagicMock()
        mock_v_pane = MagicMock()
        mock_session.windows[0].split_window.side_effect = [mock_h_pane, mock_v_pane]

        # Should not raise an exception
        await tmux_service._apply_layout_template(mock_session, template)

        # Verify window was renamed
        mock_session.windows[0].rename_window.assert_called_once_with("split-window")

        # Verify both panes were created with correct splitting
        assert mock_session.windows[0].split_window.call_count == 2

        # Verify commands were sent to panes
        mock_h_pane.send_keys.assert_called_with("top")
        mock_v_pane.send_keys.assert_called_with("htop")

    @pytest.mark.asyncio
    async def test_template_with_no_windows(self, tmux_service):
        """Test template with no windows defined."""
        mock_session = self._create_mock_session_with_window()

        template = LayoutTemplate(
            name="empty-template",
            description="Template with no windows",
            windows=[],
        )

        # Should not raise an exception and should return early
        await tmux_service._apply_layout_template(mock_session, template)

        # Should not try to rename or create windows
        mock_session.windows[0].rename_window.assert_not_called()
        mock_session.new_window.assert_not_called()

    @pytest.mark.asyncio
    async def test_template_with_pane_creation_failure(self, tmux_service):
        """Test template gracefully handles pane creation failures."""
        mock_session = self._create_mock_session_with_window()

        template = LayoutTemplate(
            name="fail-template",
            description="Template that fails pane creation",
            windows=[
                {
                    "name": "fail-window",
                    "command": "bash",
                    "panes": [
                        {"command": "bash"},
                        {"command": "failing-command", "split": "horizontal"},
                    ],
                }
            ],
        )

        # Make pane splitting fail
        mock_session.windows[0].split_window.side_effect = Exception(
            "Pane creation failed"
        )

        # Should not raise an exception (should be caught and logged)
        await tmux_service._apply_layout_template(mock_session, template)

        # Window should still be renamed
        mock_session.windows[0].rename_window.assert_called_once_with("fail-window")

    @pytest.mark.asyncio
    async def test_session_creation_with_all_templates(
        self, tmux_service, mock_server, tmp_path
    ):
        """Test session creation works with all available templates."""
        templates_to_test = ["default", "development", "claude"]

        for i, template_name in enumerate(templates_to_test):
            # Setup new mock session for each template test
            mock_session = self._create_mock_session_with_window(
                f"test-session-{template_name}"
            )
            mock_server.new_session.return_value = mock_session
            mock_server.sessions.get.return_value = None  # Session doesn't exist

            config = SessionConfig(
                session_name=f"test-{template_name}",
                working_directory=tmp_path / template_name,
                instance_id=f"test-instance-{template_name}",
                layout_template=template_name,
            )

            with patch("asyncio.get_event_loop") as mock_loop:
                mock_loop.return_value.time.return_value = 1234567890.0 + i

                # Should successfully create session with template
                result = await tmux_service.create_session(config)

                assert result.layout_template == template_name
                assert result.session_name == f"cc-orchestrator-test-{template_name}"

    def test_all_default_templates_exist(self, tmux_service):
        """Test that all required default templates are available."""
        templates = tmux_service.get_layout_templates()

        required_templates = ["default", "development", "claude"]
        for template_name in required_templates:
            assert template_name in templates
            assert isinstance(templates[template_name], LayoutTemplate)
            assert templates[template_name].name == template_name
            assert len(templates[template_name].windows) > 0

    def test_template_window_configurations(self, tmux_service):
        """Test that template window configurations are properly defined."""
        templates = tmux_service.get_layout_templates()

        # Default template should have 1 window
        default = templates["default"]
        assert len(default.windows) == 1
        assert default.windows[0]["name"] == "main"

        # Development template should have 3 windows
        development = templates["development"]
        assert len(development.windows) == 3
        expected_windows = ["editor", "terminal", "monitoring"]
        for i, expected_name in enumerate(expected_windows):
            assert development.windows[i]["name"] == expected_name

        # Claude template should have 2 windows
        claude = templates["claude"]
        assert len(claude.windows) == 2
        assert claude.windows[0]["name"] == "claude"
        assert claude.windows[1]["name"] == "shell"
