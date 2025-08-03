"""Integration tests for tmux session management."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cc_orchestrator.tmux import (
    LayoutTemplate,
    SessionConfig,
    SessionStatus,
    TmuxError,
    TmuxService,
    get_tmux_service,
)


class TestTmuxIntegration:
    """Integration tests for tmux functionality."""

    @pytest.fixture
    def mock_libtmux(self):
        """Mock libtmux for integration testing without actual tmux."""
        with patch("cc_orchestrator.tmux.service.libtmux") as mock:
            # Create mock server
            mock_server = MagicMock()
            mock.Server.return_value = mock_server
            
            # Create mock session
            mock_session = MagicMock()
            mock_session.name = "cc-orchestrator-test-session"
            mock_session.start_directory = "/tmp/test"
            mock_session.attached = False
            mock_session.clients = []
            
            # Create mock window
            mock_window = MagicMock()
            mock_window.name = "main"
            mock_session.windows = [mock_window]
            mock_session.active_window = mock_window
            
            # Set up server methods
            mock_server.new_session.return_value = mock_session
            mock_server.sessions = MagicMock()
            mock_server.sessions.get.return_value = None  # Initially no sessions
            
            yield {
                "server": mock_server,
                "session": mock_session,
                "window": mock_window,
            }

    @pytest.fixture
    def tmux_service(self, mock_libtmux):
        """Create TmuxService with mocked libtmux."""
        return TmuxService()

    @pytest.mark.asyncio
    async def test_complete_session_lifecycle(self, tmux_service, mock_libtmux):
        """Test complete session lifecycle: create -> attach -> detach -> destroy."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            working_dir = Path(tmp_dir)
            
            # Step 1: Create session
            config = SessionConfig(
                session_name="integration-test",
                working_directory=working_dir,
                instance_id="test-instance-123",
                layout_template="default",
            )
            
            # Mock session doesn't exist initially
            mock_libtmux["server"].sessions.get.return_value = None
            
            session_info = await tmux_service.create_session(config)
            
            assert session_info.session_name == "cc-orchestrator-integration-test"
            assert session_info.instance_id == "test-instance-123"
            assert session_info.status == SessionStatus.ACTIVE
            assert session_info.working_directory == working_dir
            assert session_info.layout_template == "default"
            
            # Verify session was created
            mock_libtmux["server"].new_session.assert_called_once_with(
                session_name="cc-orchestrator-integration-test",
                start_directory=str(working_dir),
                detach=True,
            )
            
            # Step 2: Session should now exist
            mock_libtmux["server"].sessions.get.return_value = mock_libtmux["session"]
            exists = await tmux_service.session_exists("integration-test")
            assert exists is True
            
            # Step 3: Attach to session
            attach_result = await tmux_service.attach_session("integration-test")
            assert attach_result is True
            
            # Step 4: Detach from session
            detach_result = await tmux_service.detach_session("integration-test")
            assert detach_result is True
            mock_libtmux["session"].detach.assert_called_once()
            
            # Step 5: Destroy session
            destroy_result = await tmux_service.destroy_session("integration-test")
            assert destroy_result is True
            mock_libtmux["session"].kill.assert_called_once()

    @pytest.mark.asyncio
    async def test_session_with_environment_variables(self, tmux_service, mock_libtmux):
        """Test session creation with environment variables."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            working_dir = Path(tmp_dir)
            
            config = SessionConfig(
                session_name="env-test",
                working_directory=working_dir,
                instance_id="env-instance",
                environment={
                    "PROJECT_NAME": "test-project",
                    "DEBUG_MODE": "true",
                    "API_KEY": "secret-key-123",
                },
            )
            
            mock_libtmux["server"].sessions.get.return_value = None
            
            await tmux_service.create_session(config)
            
            # Verify environment variables were set
            mock_session = mock_libtmux["session"]
            mock_session.set_environment.assert_any_call("PROJECT_NAME", "test-project")
            mock_session.set_environment.assert_any_call("DEBUG_MODE", "true")
            mock_session.set_environment.assert_any_call("API_KEY", "secret-key-123")

    @pytest.mark.asyncio
    async def test_error_handling_integration(self, tmux_service, mock_libtmux):
        """Test error handling in integration scenarios."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            working_dir = Path(tmp_dir)
            
            # Test 1: Create session that already exists
            config = SessionConfig(
                session_name="existing-session",
                working_directory=working_dir,
                instance_id="test-instance",
            )
            
            # Mock session already exists
            mock_libtmux["server"].sessions.get.return_value = mock_libtmux["session"]
            
            with pytest.raises(TmuxError, match="Session .* already exists"):
                await tmux_service.create_session(config)
            
            # Test 2: Destroy session with attached clients (without force)
            mock_libtmux["session"].attached = True
            
            with pytest.raises(TmuxError, match="has attached clients"):
                await tmux_service.destroy_session("existing-session", force=False)
            
            # Test 3: Force destroy should work
            result = await tmux_service.destroy_session("existing-session", force=True)
            assert result is True
            
            # Test 4: Attach to non-existent session
            mock_libtmux["server"].sessions.get.return_value = None
            result = await tmux_service.attach_session("non-existent")
            assert result is False

    @pytest.mark.asyncio
    async def test_custom_layout_template_integration(self, tmux_service, mock_libtmux):
        """Test integration with custom layout templates."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            working_dir = Path(tmp_dir)
            
            # Create custom layout template
            custom_template = LayoutTemplate(
                name="integration-layout",
                description="Custom integration testing layout",
                windows=[
                    {
                        "name": "editor",
                        "command": "vim",
                        "panes": [{"command": "vim"}],
                    },
                    {
                        "name": "terminal",
                        "command": "bash",
                        "panes": [
                            {"command": "bash"},
                            {"command": "htop", "split": "horizontal"},
                        ],
                    },
                ],
            )
            
            # Add custom template
            tmux_service.add_layout_template(custom_template)
            
            # Verify template was added
            templates = tmux_service.get_layout_templates()
            assert "integration-layout" in templates
            assert templates["integration-layout"].description == "Custom integration testing layout"
            
            # Create session with custom layout
            config = SessionConfig(
                session_name="custom-layout-test",
                working_directory=working_dir,
                instance_id="custom-instance",
                layout_template="integration-layout",
            )
            
            # Set up mock windows for the layout
            mock_editor_window = MagicMock()
            mock_editor_window.name = "editor"
            mock_terminal_window = MagicMock()
            mock_terminal_window.name = "terminal"
            
            mock_session = mock_libtmux["session"]
            mock_session.windows = [mock_editor_window, mock_terminal_window]
            mock_session.active_window = mock_editor_window
            
            mock_libtmux["server"].sessions.get.return_value = None
            mock_libtmux["server"].new_session.return_value = mock_session
            
            session_info = await tmux_service.create_session(config)
            
            assert session_info.layout_template == "integration-layout"
            assert session_info.windows == ["editor", "terminal"]

    @pytest.mark.asyncio
    async def test_global_service_instance(self):
        """Test global service instance management."""
        # Test getting global instance
        service1 = get_tmux_service()
        service2 = get_tmux_service()
        
        # Should be the same instance
        assert service1 is service2
        
        # Test cleanup
        from cc_orchestrator.tmux.service import cleanup_tmux_service
        
        # Mock the cleanup to avoid actual session destruction
        with patch.object(service1, "cleanup_sessions", return_value=0) as mock_cleanup:
            await cleanup_tmux_service()
            mock_cleanup.assert_called_once_with(force=True)
        
        # Service should be reset after cleanup
        service3 = get_tmux_service()
        assert service3 is not service1

    def test_layout_template_creation_and_management(self, tmux_service):
        """Test layout template creation and management."""
        # Test built-in templates exist
        templates = tmux_service.get_layout_templates()
        assert "default" in templates
        assert "development" in templates
        assert "claude" in templates
        
        # Test adding custom template
        custom_template = LayoutTemplate(
            name="test-layout",
            description="Test layout for unit testing",
            windows=[
                {
                    "name": "test-window",
                    "command": "bash",
                    "panes": [{"command": "bash"}],
                }
            ],
        )
        
        tmux_service.add_layout_template(custom_template)
        
        # Verify template was added
        updated_templates = tmux_service.get_layout_templates()
        assert "test-layout" in updated_templates
        assert updated_templates["test-layout"].description == "Test layout for unit testing"
        
        # Verify templates dict is a copy (immutable)
        updated_templates["modified"] = "test"
        final_templates = tmux_service.get_layout_templates()
        assert "modified" not in final_templates