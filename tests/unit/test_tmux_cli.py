"""Unit tests for tmux CLI commands."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from cc_orchestrator.cli.tmux import tmux
from cc_orchestrator.tmux import SessionInfo, SessionStatus, TmuxError


class TestTmuxCLI:
    """Test cases for tmux CLI commands."""

    @pytest.fixture
    def runner(self):
        """Click CLI runner."""
        return CliRunner()

    @pytest.fixture
    def mock_tmux_service(self):
        """Mock tmux service."""
        with patch("cc_orchestrator.cli.tmux.get_tmux_service") as mock:
            service = MagicMock()
            mock.return_value = service
            yield service

    def test_tmux_group_help(self, runner):
        """Test tmux group help command."""
        result = runner.invoke(tmux, ["--help"])
        assert result.exit_code == 0
        assert "Manage tmux sessions for Claude Code instances" in result.output

    def test_create_command_success(self, runner, mock_tmux_service, tmp_path):
        """Test successful session creation command."""
        # Setup mock to return coroutine
        async def mock_create_session(config):
            return SessionInfo(
                session_name="cc-orchestrator-test-session",
                instance_id="test-instance",
                status=SessionStatus.ACTIVE,
                working_directory=tmp_path,
                layout_template="default",
                created_at=1234567890.0,
                windows=["main"],
                current_window="main",
            )
        
        mock_tmux_service.create_session = mock_create_session

        result = runner.invoke(tmux, [
            "create",
            "test-session",
            str(tmp_path),
            "--instance-id", "test-instance",
        ])

        assert result.exit_code == 0
        assert "Created tmux session 'cc-orchestrator-test-session'" in result.output
        assert "Instance ID: test-instance" in result.output
        assert "Layout: default" in result.output
        assert "Windows: main" in result.output

    def test_create_command_invalid_env_format(self, runner, mock_tmux_service, tmp_path):
        """Test create command with invalid environment variable format."""
        result = runner.invoke(tmux, [
            "create",
            "test-session",
            str(tmp_path),
            "--instance-id", "test-instance",
            "--env", "INVALID_FORMAT",
        ])

        assert result.exit_code == 1
        assert "Invalid environment variable format: INVALID_FORMAT" in result.output

    def test_destroy_command_success(self, runner, mock_tmux_service):
        """Test successful session destruction."""
        async def mock_destroy_session(session_name, force=False):
            return True
        
        mock_tmux_service.destroy_session = mock_destroy_session

        result = runner.invoke(tmux, ["destroy", "test-session"])

        assert result.exit_code == 0
        assert "Destroyed tmux session 'test-session'" in result.output

    def test_destroy_command_failure(self, runner, mock_tmux_service):
        """Test session destruction failure."""
        async def mock_destroy_session(session_name, force=False):
            return False
        
        mock_tmux_service.destroy_session = mock_destroy_session

        result = runner.invoke(tmux, ["destroy", "test-session"])

        assert result.exit_code == 1
        assert "Failed to destroy session 'test-session'" in result.output

    def test_list_command_no_sessions(self, runner, mock_tmux_service):
        """Test listing sessions with no results."""
        async def mock_list_sessions(include_orphaned=False):
            return []
        
        mock_tmux_service.list_sessions = mock_list_sessions

        result = runner.invoke(tmux, ["list"])

        assert result.exit_code == 0
        assert "No tmux sessions found" in result.output

    def test_info_command_not_found(self, runner, mock_tmux_service):
        """Test session info command when session not found."""
        async def mock_get_session_info(session_name):
            return None
        
        mock_tmux_service.get_session_info = mock_get_session_info

        result = runner.invoke(tmux, ["info", "test-session"])

        assert result.exit_code == 1
        assert "Session 'test-session' not found" in result.output

    def test_cleanup_command_no_sessions(self, runner, mock_tmux_service):
        """Test session cleanup with no sessions to clean."""
        async def mock_cleanup_sessions(instance_id=None, force=False):
            return 0
        
        mock_tmux_service.cleanup_sessions = mock_cleanup_sessions

        result = runner.invoke(tmux, ["cleanup"])

        assert result.exit_code == 0
        assert "No sessions to clean up" in result.output

    def test_templates_command(self, runner, mock_tmux_service):
        """Test templates list command."""
        from cc_orchestrator.tmux import LayoutTemplate

        templates = {
            "default": LayoutTemplate(
                name="default",
                description="Single window with default shell",
                windows=[{"name": "main", "command": "bash", "panes": [{"command": "bash"}]}],
            ),
        }
        mock_tmux_service.get_layout_templates.return_value = templates

        result = runner.invoke(tmux, ["templates"])

        assert result.exit_code == 0
        assert "Available Layout Templates:" in result.output
        assert "● default" in result.output
        assert "Single window with default shell" in result.output

    def test_add_template_command(self, runner, mock_tmux_service):
        """Test adding custom layout template."""
        result = runner.invoke(tmux, [
            "add-template",
            "custom-template",
            "Custom development template",
            "--window", "editor:vim",
            "--window", "terminal:bash",
        ])

        assert result.exit_code == 0
        assert "Added layout template 'custom-template'" in result.output
        assert "Description: Custom development template" in result.output
        assert "Windows: 2" in result.output

        # Verify service was called
        mock_tmux_service.add_layout_template.assert_called_once()
        template = mock_tmux_service.add_layout_template.call_args[0][0]
        assert template.name == "custom-template"
        assert template.description == "Custom development template"
        assert len(template.windows) == 2