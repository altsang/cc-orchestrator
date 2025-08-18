"""Comprehensive tests for cli.tmux module to achieve 100% coverage."""

import json
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest
from click.testing import CliRunner

from cc_orchestrator.cli.tmux import (
    add_template,
    attach,
    cleanup,
    create,
    destroy,
    detach,
    info,
    list,
    templates,
    tmux,
)
from cc_orchestrator.tmux import TmuxError


class TestTmuxGroup:
    """Test the main tmux command group."""

    def test_tmux_group(self):
        """Test tmux command group basic functionality."""
        runner = CliRunner()
        result = runner.invoke(tmux, ["--help"])
        assert result.exit_code == 0
        assert "Manage tmux sessions" in result.output
        assert "Claude Code instances" in result.output


class TestCreateCommand:
    """Test the create command."""

    @pytest.fixture
    def mock_tmux_service(self):
        """Mock tmux service."""
        service = Mock()
        service.create_session = AsyncMock()
        return service

    @pytest.fixture
    def mock_session_info(self):
        """Mock session info response."""
        session_info = Mock()
        session_info.session_name = "test-session"
        session_info.instance_id = "test-instance"
        session_info.status = Mock()
        session_info.status.value = "active"
        session_info.working_directory = Path("/test/dir")
        session_info.layout_template = "default"
        session_info.windows = ["main", "logs"]
        session_info.created_at = "2023-01-01T12:00:00Z"
        return session_info

    def test_create_success_basic(self, mock_tmux_service, mock_session_info):
        """Test successful session creation with basic options."""
        mock_tmux_service.create_session.return_value = mock_session_info

        with patch(
            "cc_orchestrator.cli.tmux.get_tmux_service", return_value=mock_tmux_service
        ):
            with patch("asyncio.run") as mock_run:

                mock_result = {
                    "session_name": "test-session",
                    "instance_id": "test-instance",
                    "status": "active",
                    "working_directory": "/test/dir",
                    "layout_template": "default",
                    "windows": ["main", "logs"],
                    "created_at": "2023-01-01T12:00:00Z",
                }

                mock_run.return_value = mock_result

                runner = CliRunner()
                with runner.isolated_filesystem():
                    # Create test directory
                    Path("test_dir").mkdir()

                    result = runner.invoke(
                        create,
                        ["test-session", "test_dir", "--instance-id", "test-instance"],
                    )

                    assert result.exit_code == 0
                    assert "Created tmux session 'test-session'" in result.output
                    assert "Instance ID: test-instance" in result.output
                    assert "Layout: default" in result.output
                    assert "Windows: main, logs" in result.output

    def test_create_success_with_all_options(
        self, mock_tmux_service, mock_session_info
    ):
        """Test successful session creation with all options."""
        mock_tmux_service.create_session.return_value = mock_session_info

        with patch(
            "cc_orchestrator.cli.tmux.get_tmux_service", return_value=mock_tmux_service
        ):
            with patch("asyncio.run") as mock_run:
                mock_run.return_value = {
                    "session_name": "test-session",
                    "instance_id": "test-instance",
                    "status": "active",
                    "working_directory": "/test/dir",
                    "layout_template": "development",
                    "windows": ["main", "logs", "dev"],
                    "created_at": "2023-01-01T12:00:00Z",
                }

                runner = CliRunner()
                with runner.isolated_filesystem():
                    Path("test_dir").mkdir()

                    result = runner.invoke(
                        create,
                        [
                            "test-session",
                            "test_dir",
                            "--instance-id",
                            "test-instance",
                            "--layout",
                            "development",
                            "--auto-attach",
                            "--env",
                            "NODE_ENV=development",
                            "--env",
                            "DEBUG=true",
                        ],
                    )

                    assert result.exit_code == 0
                    assert "Session attached automatically" in result.output

    def test_create_with_json_output(self, mock_tmux_service, mock_session_info):
        """Test session creation with JSON output."""
        mock_tmux_service.create_session.return_value = mock_session_info

        with patch(
            "cc_orchestrator.cli.tmux.get_tmux_service", return_value=mock_tmux_service
        ):
            with patch("asyncio.run") as mock_run:
                expected_result = {
                    "session_name": "test-session",
                    "instance_id": "test-instance",
                    "status": "active",
                    "working_directory": "/test/dir",
                    "layout_template": "default",
                    "windows": ["main", "logs"],
                    "created_at": "2023-01-01T12:00:00Z",
                }
                mock_run.return_value = expected_result

                runner = CliRunner()
                with runner.isolated_filesystem():
                    Path("test_dir").mkdir()

                    result = runner.invoke(
                        create,
                        ["test-session", "test_dir", "--instance-id", "test-instance"],
                        obj={"json": True},
                    )

                    assert result.exit_code == 0
                    output_json = json.loads(result.output)
                    assert output_json == expected_result

    def test_create_invalid_env_format(self):
        """Test creation with invalid environment variable format."""
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path("test_dir").mkdir()

            result = runner.invoke(
                create,
                [
                    "test-session",
                    "test_dir",
                    "--instance-id",
                    "test-instance",
                    "--env",
                    "INVALID_FORMAT",
                ],
            )

            assert result.exit_code == 1
            assert "Invalid environment variable format" in result.output

    def test_create_tmux_error(self, mock_tmux_service):
        """Test creation with TmuxError."""
        with patch(
            "cc_orchestrator.cli.tmux.get_tmux_service", return_value=mock_tmux_service
        ):
            with patch("asyncio.run", side_effect=TmuxError("Tmux service error")):
                runner = CliRunner()
                with runner.isolated_filesystem():
                    Path("test_dir").mkdir()

                    result = runner.invoke(
                        create,
                        ["test-session", "test_dir", "--instance-id", "test-instance"],
                    )

                    assert result.exit_code == 1
                    assert "Failed to create tmux session" in result.output

    def test_create_env_parsing(self, mock_tmux_service, mock_session_info):
        """Test environment variable parsing."""
        mock_tmux_service.create_session.return_value = mock_session_info

        with patch(
            "cc_orchestrator.cli.tmux.get_tmux_service", return_value=mock_tmux_service
        ):
            with patch("asyncio.run") as mock_run:
                mock_run.return_value = {
                    "session_name": "test-session",
                    "instance_id": "test-instance",
                    "status": "active",
                    "working_directory": "/test/dir",
                    "layout_template": "default",
                    "windows": ["main"],
                    "created_at": "2023-01-01T12:00:00Z",
                }

                runner = CliRunner()
                with runner.isolated_filesystem():
                    Path("test_dir").mkdir()

                    result = runner.invoke(
                        create,
                        [
                            "test-session",
                            "test_dir",
                            "--instance-id",
                            "test-instance",
                            "--env",
                            "KEY1=value1",
                            "--env",
                            "KEY2=value2=with=equals",
                        ],
                    )

                    assert result.exit_code == 0


class TestDestroyCommand:
    """Test the destroy command."""

    @pytest.fixture
    def mock_tmux_service(self):
        """Mock tmux service."""
        service = Mock()
        service.destroy_session = AsyncMock()
        return service

    def test_destroy_success(self, mock_tmux_service):
        """Test successful session destruction."""
        with patch(
            "cc_orchestrator.cli.tmux.get_tmux_service", return_value=mock_tmux_service
        ):
            with patch("asyncio.run") as mock_run:
                mock_run.return_value = {
                    "success": True,
                    "session_name": "test-session",
                }

                runner = CliRunner()
                result = runner.invoke(destroy, ["test-session"])

                assert result.exit_code == 0
                assert "Destroyed tmux session 'test-session'" in result.output

    def test_destroy_with_force(self, mock_tmux_service):
        """Test session destruction with force flag."""
        with patch(
            "cc_orchestrator.cli.tmux.get_tmux_service", return_value=mock_tmux_service
        ):
            with patch("asyncio.run") as mock_run:
                mock_run.return_value = {
                    "success": True,
                    "session_name": "test-session",
                }

                runner = CliRunner()
                result = runner.invoke(destroy, ["test-session", "--force"])

                assert result.exit_code == 0
                assert "Destroyed tmux session 'test-session'" in result.output

    def test_destroy_json_output(self, mock_tmux_service):
        """Test destruction with JSON output."""
        with patch(
            "cc_orchestrator.cli.tmux.get_tmux_service", return_value=mock_tmux_service
        ):
            with patch("asyncio.run") as mock_run:
                expected_result = {"success": True, "session_name": "test-session"}
                mock_run.return_value = expected_result

                runner = CliRunner()
                result = runner.invoke(destroy, ["test-session"], obj={"json": True})

                assert result.exit_code == 0
                output_json = json.loads(result.output)
                assert output_json == expected_result

    def test_destroy_failure(self, mock_tmux_service):
        """Test session destruction failure."""
        with patch(
            "cc_orchestrator.cli.tmux.get_tmux_service", return_value=mock_tmux_service
        ):
            with patch("asyncio.run") as mock_run:
                mock_run.return_value = {
                    "success": False,
                    "session_name": "test-session",
                }

                runner = CliRunner()
                result = runner.invoke(destroy, ["test-session"])

                assert result.exit_code == 1
                assert "Failed to destroy session 'test-session'" in result.output

    def test_destroy_tmux_error(self, mock_tmux_service):
        """Test destruction with TmuxError."""
        with patch(
            "cc_orchestrator.cli.tmux.get_tmux_service", return_value=mock_tmux_service
        ):
            with patch("asyncio.run", side_effect=TmuxError("Tmux error")):
                runner = CliRunner()
                result = runner.invoke(destroy, ["test-session"])

                assert result.exit_code == 1
                assert "Error destroying session" in result.output


class TestAttachCommand:
    """Test the attach command."""

    @pytest.fixture
    def mock_tmux_service(self):
        """Mock tmux service."""
        service = Mock()
        service.attach_session = AsyncMock()
        return service

    def test_attach_success(self, mock_tmux_service):
        """Test successful session attachment."""
        with patch(
            "cc_orchestrator.cli.tmux.get_tmux_service", return_value=mock_tmux_service
        ):
            with patch("asyncio.run") as mock_run:
                mock_run.return_value = {
                    "success": True,
                    "session_name": "test-session",
                }

                runner = CliRunner()
                result = runner.invoke(attach, ["test-session"])

                assert result.exit_code == 0
                assert "Attached to tmux session 'test-session'" in result.output
                assert "Ctrl+b d" in result.output

    def test_attach_json_output(self, mock_tmux_service):
        """Test attachment with JSON output."""
        with patch(
            "cc_orchestrator.cli.tmux.get_tmux_service", return_value=mock_tmux_service
        ):
            with patch("asyncio.run") as mock_run:
                expected_result = {"success": True, "session_name": "test-session"}
                mock_run.return_value = expected_result

                runner = CliRunner()
                result = runner.invoke(attach, ["test-session"], obj={"json": True})

                assert result.exit_code == 0
                output_json = json.loads(result.output)
                assert output_json == expected_result

    def test_attach_failure(self, mock_tmux_service):
        """Test session attachment failure."""
        with patch(
            "cc_orchestrator.cli.tmux.get_tmux_service", return_value=mock_tmux_service
        ):
            with patch("asyncio.run") as mock_run:
                mock_run.return_value = {
                    "success": False,
                    "session_name": "test-session",
                }

                runner = CliRunner()
                result = runner.invoke(attach, ["test-session"])

                assert result.exit_code == 1
                assert "Failed to attach to session 'test-session'" in result.output

    def test_attach_tmux_error(self, mock_tmux_service):
        """Test attachment with TmuxError."""
        with patch(
            "cc_orchestrator.cli.tmux.get_tmux_service", return_value=mock_tmux_service
        ):
            with patch("asyncio.run", side_effect=TmuxError("Attach error")):
                runner = CliRunner()
                result = runner.invoke(attach, ["test-session"])

                assert result.exit_code == 1
                assert "Error attaching to session" in result.output


class TestDetachCommand:
    """Test the detach command."""

    @pytest.fixture
    def mock_tmux_service(self):
        """Mock tmux service."""
        service = Mock()
        service.detach_session = AsyncMock()
        return service

    def test_detach_success(self, mock_tmux_service):
        """Test successful session detachment."""
        with patch(
            "cc_orchestrator.cli.tmux.get_tmux_service", return_value=mock_tmux_service
        ):
            with patch("asyncio.run") as mock_run:
                mock_run.return_value = {
                    "success": True,
                    "session_name": "test-session",
                }

                runner = CliRunner()
                result = runner.invoke(detach, ["test-session"])

                assert result.exit_code == 0
                assert "Detached from tmux session 'test-session'" in result.output

    def test_detach_json_output(self, mock_tmux_service):
        """Test detachment with JSON output."""
        with patch(
            "cc_orchestrator.cli.tmux.get_tmux_service", return_value=mock_tmux_service
        ):
            with patch("asyncio.run") as mock_run:
                expected_result = {"success": True, "session_name": "test-session"}
                mock_run.return_value = expected_result

                runner = CliRunner()
                result = runner.invoke(detach, ["test-session"], obj={"json": True})

                assert result.exit_code == 0
                output_json = json.loads(result.output)
                assert output_json == expected_result

    def test_detach_failure(self, mock_tmux_service):
        """Test session detachment failure."""
        with patch(
            "cc_orchestrator.cli.tmux.get_tmux_service", return_value=mock_tmux_service
        ):
            with patch("asyncio.run") as mock_run:
                mock_run.return_value = {
                    "success": False,
                    "session_name": "test-session",
                }

                runner = CliRunner()
                result = runner.invoke(detach, ["test-session"])

                assert result.exit_code == 1
                assert "Failed to detach from session 'test-session'" in result.output

    def test_detach_tmux_error(self, mock_tmux_service):
        """Test detachment with TmuxError."""
        with patch(
            "cc_orchestrator.cli.tmux.get_tmux_service", return_value=mock_tmux_service
        ):
            with patch("asyncio.run", side_effect=TmuxError("Detach error")):
                runner = CliRunner()
                result = runner.invoke(detach, ["test-session"])

                assert result.exit_code == 1
                assert "Error detaching from session" in result.output


class TestListCommand:
    """Test the list command."""

    @pytest.fixture
    def mock_tmux_service(self):
        """Mock tmux service."""
        service = Mock()
        service.list_sessions = AsyncMock()
        return service

    @pytest.fixture
    def mock_sessions(self):
        """Mock session list."""
        session1 = Mock()
        session1.session_name = "session-1"
        session1.instance_id = "instance-1"
        session1.status = Mock()
        session1.status.value = "active"
        session1.working_directory = Path("/test/dir1")
        session1.layout_template = "default"
        session1.windows = ["main", "logs"]
        session1.current_window = "main"
        session1.attached_clients = 1
        session1.created_at = "2023-01-01T12:00:00Z"

        session2 = Mock()
        session2.session_name = "session-2"
        session2.instance_id = "instance-2"
        session2.status = Mock()
        session2.status.value = "inactive"
        session2.working_directory = Path("/test/dir2")
        session2.layout_template = "development"
        session2.windows = ["main"]
        session2.current_window = None
        session2.attached_clients = 0
        session2.created_at = "2023-01-01T13:00:00Z"

        return [session1, session2]

    def test_list_success(self, mock_tmux_service, mock_sessions):
        """Test successful session listing."""
        with patch(
            "cc_orchestrator.cli.tmux.get_tmux_service", return_value=mock_tmux_service
        ):
            with patch("asyncio.run") as mock_run:
                mock_run.return_value = [
                    {
                        "session_name": "session-1",
                        "instance_id": "instance-1",
                        "status": "active",
                        "working_directory": "/test/dir1",
                        "layout_template": "default",
                        "windows": ["main", "logs"],
                        "current_window": "main",
                        "attached_clients": 1,
                        "created_at": "2023-01-01T12:00:00Z",
                    },
                    {
                        "session_name": "session-2",
                        "instance_id": "instance-2",
                        "status": "inactive",
                        "working_directory": "/test/dir2",
                        "layout_template": "development",
                        "windows": ["main"],
                        "current_window": None,
                        "attached_clients": 0,
                        "created_at": "2023-01-01T13:00:00Z",
                    },
                ]

                runner = CliRunner()
                result = runner.invoke(list, [])

                assert result.exit_code == 0
                assert "● session-1" in result.output
                assert "○ session-2" in result.output
                assert "Instance: instance-1" in result.output
                assert "Status: active" in result.output
                assert "Current: main" in result.output
                assert "Clients: 1" in result.output

    def test_list_with_orphaned(self, mock_tmux_service):
        """Test session listing with orphaned sessions."""
        with patch(
            "cc_orchestrator.cli.tmux.get_tmux_service", return_value=mock_tmux_service
        ):
            with patch("asyncio.run") as mock_run:
                mock_run.return_value = []

                runner = CliRunner()
                result = runner.invoke(list, ["--include-orphaned"])

                assert result.exit_code == 0

    def test_list_empty(self, mock_tmux_service):
        """Test listing with no sessions."""
        with patch(
            "cc_orchestrator.cli.tmux.get_tmux_service", return_value=mock_tmux_service
        ):
            with patch("asyncio.run") as mock_run:
                mock_run.return_value = []

                runner = CliRunner()
                result = runner.invoke(list, [])

                assert result.exit_code == 0
                assert "No tmux sessions found" in result.output

    def test_list_json_output(self, mock_tmux_service):
        """Test listing with JSON output."""
        with patch(
            "cc_orchestrator.cli.tmux.get_tmux_service", return_value=mock_tmux_service
        ):
            with patch("asyncio.run") as mock_run:
                expected_result = [
                    {
                        "session_name": "session-1",
                        "instance_id": "instance-1",
                        "status": "active",
                        "working_directory": "/test/dir1",
                        "layout_template": "default",
                        "windows": ["main"],
                        "current_window": "main",
                        "attached_clients": 1,
                        "created_at": "2023-01-01T12:00:00Z",
                    }
                ]
                mock_run.return_value = expected_result

                runner = CliRunner()
                result = runner.invoke(list, [], obj={"json": True})

                assert result.exit_code == 0
                output_json = json.loads(result.output)
                assert output_json == expected_result

    def test_list_tmux_error(self, mock_tmux_service):
        """Test listing with TmuxError."""
        with patch(
            "cc_orchestrator.cli.tmux.get_tmux_service", return_value=mock_tmux_service
        ):
            with patch("asyncio.run", side_effect=TmuxError("List error")):
                runner = CliRunner()
                result = runner.invoke(list, [])

                assert result.exit_code == 1
                assert "Error listing sessions" in result.output


class TestInfoCommand:
    """Test the info command."""

    @pytest.fixture
    def mock_tmux_service(self):
        """Mock tmux service."""
        service = Mock()
        service.get_session_info = AsyncMock()
        return service

    @pytest.fixture
    def mock_session_info(self):
        """Mock detailed session info."""
        return {
            "session_name": "test-session",
            "instance_id": "test-instance",
            "status": "active",
            "working_directory": "/test/dir",
            "layout_template": "default",
            "windows": ["main", "logs"],
            "current_window": "main",
            "attached_clients": 1,
            "created_at": "2023-01-01T12:00:00Z",
            "last_activity": "2023-01-01T12:30:00Z",
            "environment": {"NODE_ENV": "development", "DEBUG": "true"},
        }

    def test_info_success(self, mock_tmux_service, mock_session_info):
        """Test successful session info retrieval."""
        with patch(
            "cc_orchestrator.cli.tmux.get_tmux_service", return_value=mock_tmux_service
        ):
            with patch("asyncio.run") as mock_run:
                mock_run.return_value = mock_session_info

                runner = CliRunner()
                result = runner.invoke(info, ["test-session"])

                assert result.exit_code == 0
                assert "Session: test-session" in result.output
                assert "Instance ID: test-instance" in result.output
                assert "Status: active" in result.output
                assert "Working Directory: /test/dir" in result.output
                assert "Layout Template: default" in result.output
                assert "Windows: main, logs" in result.output
                assert "Current Window: main" in result.output
                assert "Attached Clients: 1" in result.output
                assert "Environment Variables:" in result.output
                assert "NODE_ENV=development" in result.output
                assert "DEBUG=true" in result.output

    def test_info_no_current_window(self, mock_tmux_service):
        """Test info with no current window."""
        info_data = {
            "session_name": "test-session",
            "instance_id": "test-instance",
            "status": "active",
            "working_directory": "/test/dir",
            "layout_template": "default",
            "windows": ["main"],
            "current_window": None,
            "attached_clients": 0,
            "created_at": "2023-01-01T12:00:00Z",
            "last_activity": "2023-01-01T12:30:00Z",
            "environment": None,
        }

        with patch(
            "cc_orchestrator.cli.tmux.get_tmux_service", return_value=mock_tmux_service
        ):
            with patch("asyncio.run") as mock_run:
                mock_run.return_value = info_data

                runner = CliRunner()
                result = runner.invoke(info, ["test-session"])

                assert result.exit_code == 0
                assert "Session: test-session" in result.output
                assert "Current Window:" not in result.output
                assert "Environment Variables:" not in result.output

    def test_info_not_found(self, mock_tmux_service):
        """Test info for non-existent session."""
        with patch(
            "cc_orchestrator.cli.tmux.get_tmux_service", return_value=mock_tmux_service
        ):
            with patch("asyncio.run") as mock_run:
                mock_run.return_value = None

                runner = CliRunner()
                result = runner.invoke(info, ["nonexistent"])

                assert result.exit_code == 1
                assert "Session 'nonexistent' not found" in result.output

    def test_info_json_output(self, mock_tmux_service, mock_session_info):
        """Test info with JSON output."""
        with patch(
            "cc_orchestrator.cli.tmux.get_tmux_service", return_value=mock_tmux_service
        ):
            with patch("asyncio.run") as mock_run:
                mock_run.return_value = mock_session_info

                runner = CliRunner()
                result = runner.invoke(info, ["test-session"], obj={"json": True})

                assert result.exit_code == 0
                output_json = json.loads(result.output)
                assert output_json == mock_session_info

    def test_info_tmux_error(self, mock_tmux_service):
        """Test info with TmuxError."""
        with patch(
            "cc_orchestrator.cli.tmux.get_tmux_service", return_value=mock_tmux_service
        ):
            with patch("asyncio.run", side_effect=TmuxError("Info error")):
                runner = CliRunner()
                result = runner.invoke(info, ["test-session"])

                assert result.exit_code == 1
                assert "Error getting session info" in result.output


class TestCleanupCommand:
    """Test the cleanup command."""

    @pytest.fixture
    def mock_tmux_service(self):
        """Mock tmux service."""
        service = Mock()
        service.cleanup_sessions = AsyncMock()
        return service

    def test_cleanup_success(self, mock_tmux_service):
        """Test successful cleanup."""
        with patch(
            "cc_orchestrator.cli.tmux.get_tmux_service", return_value=mock_tmux_service
        ):
            with patch("asyncio.run") as mock_run:
                mock_run.return_value = {"cleaned_up": 3, "instance_id": None}

                runner = CliRunner()
                result = runner.invoke(cleanup, [])

                assert result.exit_code == 0
                assert "Cleaned up 3 session(s)" in result.output

    def test_cleanup_with_instance_id(self, mock_tmux_service):
        """Test cleanup for specific instance."""
        with patch(
            "cc_orchestrator.cli.tmux.get_tmux_service", return_value=mock_tmux_service
        ):
            with patch("asyncio.run") as mock_run:
                mock_run.return_value = {
                    "cleaned_up": 1,
                    "instance_id": "test-instance",
                }

                runner = CliRunner()
                result = runner.invoke(cleanup, ["--instance-id", "test-instance"])

                assert result.exit_code == 0
                assert (
                    "Cleaned up 1 session(s) for instance test-instance"
                    in result.output
                )

    def test_cleanup_with_force(self, mock_tmux_service):
        """Test cleanup with force flag."""
        with patch(
            "cc_orchestrator.cli.tmux.get_tmux_service", return_value=mock_tmux_service
        ):
            with patch("asyncio.run") as mock_run:
                mock_run.return_value = {"cleaned_up": 2, "instance_id": None}

                runner = CliRunner()
                result = runner.invoke(cleanup, ["--force"])

                assert result.exit_code == 0
                assert "Cleaned up 2 session(s)" in result.output

    def test_cleanup_no_sessions(self, mock_tmux_service):
        """Test cleanup with no sessions to clean."""
        with patch(
            "cc_orchestrator.cli.tmux.get_tmux_service", return_value=mock_tmux_service
        ):
            with patch("asyncio.run") as mock_run:
                mock_run.return_value = {"cleaned_up": 0, "instance_id": None}

                runner = CliRunner()
                result = runner.invoke(cleanup, [])

                assert result.exit_code == 0
                assert "No sessions to clean up" in result.output

    def test_cleanup_json_output(self, mock_tmux_service):
        """Test cleanup with JSON output."""
        with patch(
            "cc_orchestrator.cli.tmux.get_tmux_service", return_value=mock_tmux_service
        ):
            with patch("asyncio.run") as mock_run:
                expected_result = {"cleaned_up": 2, "instance_id": None}
                mock_run.return_value = expected_result

                runner = CliRunner()
                result = runner.invoke(cleanup, [], obj={"json": True})

                assert result.exit_code == 0
                output_json = json.loads(result.output)
                assert output_json == expected_result

    def test_cleanup_tmux_error(self, mock_tmux_service):
        """Test cleanup with TmuxError."""
        with patch(
            "cc_orchestrator.cli.tmux.get_tmux_service", return_value=mock_tmux_service
        ):
            with patch("asyncio.run", side_effect=TmuxError("Cleanup error")):
                runner = CliRunner()
                result = runner.invoke(cleanup, [])

                assert result.exit_code == 1
                assert "Error during cleanup" in result.output


class TestTemplatesCommand:
    """Test the templates command."""

    @pytest.fixture
    def mock_tmux_service(self):
        """Mock tmux service."""
        service = Mock()
        service.get_layout_templates = Mock()
        return service

    @pytest.fixture
    def mock_templates(self):
        """Mock layout templates."""
        template1 = Mock()
        template1.name = "default"
        template1.description = "Default layout"
        template1.windows = [{"name": "main", "command": "bash"}]
        template1.default_pane_command = "bash"

        template2 = Mock()
        template2.name = "development"
        template2.description = "Development layout"
        template2.windows = [
            {"name": "main", "command": "bash"},
            {"name": "logs", "command": "tail -f logs/app.log"},
        ]
        template2.default_pane_command = "bash"

        return {"default": template1, "development": template2}

    def test_templates_success(self, mock_tmux_service, mock_templates):
        """Test successful template listing."""
        mock_tmux_service.get_layout_templates.return_value = mock_templates

        with patch(
            "cc_orchestrator.cli.tmux.get_tmux_service", return_value=mock_tmux_service
        ):
            runner = CliRunner()
            result = runner.invoke(templates, [])

            assert result.exit_code == 0
            assert "Available Layout Templates:" in result.output
            assert "● default" in result.output
            assert "Default layout" in result.output
            assert "Windows: 1" in result.output
            assert "● development" in result.output
            assert "Development layout" in result.output
            assert "Windows: 2" in result.output

    def test_templates_empty(self, mock_tmux_service):
        """Test template listing with no templates."""
        mock_tmux_service.get_layout_templates.return_value = {}

        with patch(
            "cc_orchestrator.cli.tmux.get_tmux_service", return_value=mock_tmux_service
        ):
            runner = CliRunner()
            result = runner.invoke(templates, [])

            assert result.exit_code == 0
            assert "No layout templates available" in result.output

    def test_templates_json_output(self, mock_tmux_service, mock_templates):
        """Test template listing with JSON output."""
        mock_tmux_service.get_layout_templates.return_value = mock_templates

        with patch(
            "cc_orchestrator.cli.tmux.get_tmux_service", return_value=mock_tmux_service
        ):
            runner = CliRunner()
            result = runner.invoke(templates, [], obj={"json": True})

            assert result.exit_code == 0
            output_json = json.loads(result.output)
            assert "default" in output_json
            assert "development" in output_json
            assert output_json["default"]["name"] == "default"
            assert output_json["default"]["description"] == "Default layout"


class TestAddTemplateCommand:
    """Test the add_template command."""

    @pytest.fixture
    def mock_tmux_service(self):
        """Mock tmux service."""
        service = Mock()
        service.add_layout_template = Mock()
        return service

    def test_add_template_basic(self, mock_tmux_service):
        """Test adding basic template."""
        with patch(
            "cc_orchestrator.cli.tmux.get_tmux_service", return_value=mock_tmux_service
        ):
            runner = CliRunner()
            result = runner.invoke(
                add_template, ["custom-template", "Custom template description"]
            )

            assert result.exit_code == 0
            assert "Added layout template 'custom-template'" in result.output
            assert "Description: Custom template description" in result.output
            assert "Windows: 1" in result.output

    def test_add_template_with_windows(self, mock_tmux_service):
        """Test adding template with custom windows."""
        with patch(
            "cc_orchestrator.cli.tmux.get_tmux_service", return_value=mock_tmux_service
        ):
            runner = CliRunner()
            result = runner.invoke(
                add_template,
                [
                    "dev-template",
                    "Development template",
                    "--window",
                    "main:bash",
                    "--window",
                    "logs:tail -f app.log",
                    "--window",
                    "editor",
                ],
            )

            assert result.exit_code == 0
            assert "Added layout template 'dev-template'" in result.output
            assert "Windows: 3" in result.output

    def test_add_template_json_output(self, mock_tmux_service):
        """Test adding template with JSON output."""
        with patch(
            "cc_orchestrator.cli.tmux.get_tmux_service", return_value=mock_tmux_service
        ):
            runner = CliRunner()
            result = runner.invoke(
                add_template, ["json-template", "JSON template"], obj={"json": True}
            )

            assert result.exit_code == 0
            output_json = json.loads(result.output)
            assert output_json["template_name"] == "json-template"
            assert output_json["description"] == "JSON template"
            assert len(output_json["windows"]) == 1
