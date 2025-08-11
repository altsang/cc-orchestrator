"""Comprehensive unit tests for CLI instances commands."""

import json
import time
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

from click.testing import CliRunner

from cc_orchestrator.cli.main import main
from cc_orchestrator.core.instance import ClaudeInstance
from cc_orchestrator.utils.process import ProcessInfo, ProcessStatus


def create_mock_orchestrator():
    """Create a properly mocked orchestrator."""
    mock_orchestrator = Mock()
    mock_orchestrator.initialize = AsyncMock()
    mock_orchestrator.cleanup = AsyncMock()
    return mock_orchestrator


def create_mock_instance(issue_id="test-123", with_process_info=True):
    """Create a properly mocked instance."""
    mock_instance = Mock(spec=ClaudeInstance)
    mock_instance.get_info.return_value = {
        "issue_id": issue_id,
        "status": "running" if with_process_info else "stopped",
        "workspace_path": "/test/workspace",
        "branch_name": f"feature/{issue_id}",
        "tmux_session": f"claude-{issue_id}",
        "process_id": 12345 if with_process_info else None,
    }

    if with_process_info:
        mock_instance.get_process_status = AsyncMock(
            return_value=ProcessInfo(
                pid=12345,
                status=ProcessStatus.RUNNING,
                command=["claude", "code"],
                working_directory=Path("/test/workspace"),
                environment={"PATH": "/usr/bin"},
                started_at=time.time(),
                cpu_percent=25.5,
                memory_mb=128.0,
            )
        )
    else:
        mock_instance.get_process_status = AsyncMock(return_value=None)

    mock_instance.is_running.return_value = with_process_info
    mock_instance.start = AsyncMock(return_value=True)
    mock_instance.stop = AsyncMock(return_value=True)

    return mock_instance


class TestInstanceCommands:
    """Comprehensive test suite for instance command group."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    def test_instances_help(self):
        """Test instances command group help."""
        result = self.runner.invoke(main, ["instances", "--help"])
        assert result.exit_code == 0
        assert "Manage Claude Code instances" in result.output

    # STATUS COMMAND TESTS

    @patch("cc_orchestrator.cli.instances.Orchestrator")
    def test_status_no_instances(self, mock_orchestrator_class):
        """Test status command with no instances."""
        mock_orchestrator = create_mock_orchestrator()
        mock_orchestrator.list_instances.return_value = []
        mock_orchestrator_class.return_value = mock_orchestrator

        result = self.runner.invoke(main, ["instances", "status"])
        assert result.exit_code == 0
        assert "No active instances found" in result.output
        mock_orchestrator.initialize.assert_called_once()
        # Note: cleanup is not called because function returns early when no instances

    @patch("cc_orchestrator.cli.instances.Orchestrator")
    def test_status_no_instances_json(self, mock_orchestrator_class):
        """Test status command with no instances in JSON format."""
        mock_orchestrator = create_mock_orchestrator()
        mock_orchestrator.list_instances.return_value = []
        mock_orchestrator_class.return_value = mock_orchestrator

        result = self.runner.invoke(main, ["instances", "status", "--json"])
        assert result.exit_code == 0

        output_data = json.loads(result.output)
        assert output_data == {"instances": [], "total": 0}
        # Note: cleanup is not called because function returns early when no instances

    @patch("cc_orchestrator.cli.instances.Orchestrator")
    def test_status_with_instances(self, mock_orchestrator_class):
        """Test status command with instances."""
        mock_instance = create_mock_instance()
        mock_orchestrator = create_mock_orchestrator()
        mock_orchestrator.list_instances.return_value = [mock_instance]
        mock_orchestrator_class.return_value = mock_orchestrator

        result = self.runner.invoke(main, ["instances", "status"])
        assert result.exit_code == 0
        assert "Active Claude Instances (1)" in result.output
        assert "Issue ID: test-123" in result.output
        assert "Status: running" in result.output
        assert "Process ID: 12345" in result.output
        assert "CPU: 25.5%" in result.output
        assert "Memory: 128.0 MB" in result.output

    @patch("cc_orchestrator.cli.instances.Orchestrator")
    def test_status_with_instances_json(self, mock_orchestrator_class):
        """Test status command with instances in JSON format."""
        mock_instance = create_mock_instance()
        mock_orchestrator = create_mock_orchestrator()
        mock_orchestrator.list_instances.return_value = [mock_instance]
        mock_orchestrator_class.return_value = mock_orchestrator

        result = self.runner.invoke(main, ["instances", "status", "--json"])
        assert result.exit_code == 0

        output_data = json.loads(result.output)
        assert output_data["total"] == 1
        assert len(output_data["instances"]) == 1
        instance_data = output_data["instances"][0]
        assert instance_data["issue_id"] == "test-123"
        assert instance_data["process_status"] == "running"
        assert instance_data["cpu_percent"] == 25.5
        assert instance_data["memory_mb"] == 128.0

    @patch("cc_orchestrator.cli.instances.Orchestrator")
    def test_status_with_instances_no_process_info(self, mock_orchestrator_class):
        """Test status command with instances that have no process info."""
        mock_instance = create_mock_instance(
            issue_id="test-456", with_process_info=False
        )
        mock_orchestrator = create_mock_orchestrator()
        mock_orchestrator.list_instances.return_value = [mock_instance]
        mock_orchestrator_class.return_value = mock_orchestrator

        result = self.runner.invoke(main, ["instances", "status"])
        assert result.exit_code == 0
        assert "Issue ID: test-456" in result.output
        assert "Status: stopped" in result.output
        # Should not contain process info
        assert "Process ID:" not in result.output
        assert "CPU:" not in result.output

    @patch("cc_orchestrator.cli.instances.Orchestrator")
    def test_status_error_handling(self, mock_orchestrator_class):
        """Test status command error handling."""
        mock_orchestrator = create_mock_orchestrator()
        mock_orchestrator.initialize.side_effect = Exception("Test error")
        mock_orchestrator_class.return_value = mock_orchestrator

        result = self.runner.invoke(main, ["instances", "status"])
        assert result.exit_code == 0
        assert "Error: Test error" in result.output

    @patch("cc_orchestrator.cli.instances.Orchestrator")
    def test_status_error_handling_json(self, mock_orchestrator_class):
        """Test status command error handling with JSON output."""
        mock_orchestrator = create_mock_orchestrator()
        mock_orchestrator.initialize.side_effect = Exception("Test error")
        mock_orchestrator_class.return_value = mock_orchestrator

        result = self.runner.invoke(main, ["instances", "status", "--json"])
        assert result.exit_code == 0

        output_data = json.loads(result.output)
        assert output_data == {"error": "Test error"}

    # START COMMAND TESTS

    @patch("cc_orchestrator.cli.instances.Orchestrator")
    def test_start_new_instance(self, mock_orchestrator_class):
        """Test start command for new instance."""
        mock_instance = create_mock_instance()
        mock_orchestrator = create_mock_orchestrator()
        mock_orchestrator.get_instance.return_value = None  # No existing instance
        mock_orchestrator.create_instance = AsyncMock(return_value=mock_instance)
        mock_orchestrator_class.return_value = mock_orchestrator

        result = self.runner.invoke(main, ["instances", "start", "test-123"])
        assert result.exit_code == 0
        assert (
            "Successfully started Claude instance for issue test-123" in result.output
        )
        assert "Process ID: 12345" in result.output
        mock_orchestrator.create_instance.assert_called_once_with("test-123")

    @patch("cc_orchestrator.cli.instances.Orchestrator")
    def test_start_new_instance_with_options(self, mock_orchestrator_class):
        """Test start command for new instance with custom options."""
        mock_instance = create_mock_instance()
        mock_instance.get_info.return_value.update(
            {
                "workspace_path": "/custom/workspace",
                "branch_name": "custom-branch",
                "tmux_session": "custom-session",
            }
        )

        mock_orchestrator = create_mock_orchestrator()
        mock_orchestrator.get_instance.return_value = None
        mock_orchestrator.create_instance = AsyncMock(return_value=mock_instance)
        mock_orchestrator_class.return_value = mock_orchestrator

        result = self.runner.invoke(
            main,
            [
                "instances",
                "start",
                "test-123",
                "--workspace",
                "/custom/workspace",
                "--branch",
                "custom-branch",
                "--tmux-session",
                "custom-session",
            ],
        )
        assert result.exit_code == 0
        assert (
            "Successfully started Claude instance for issue test-123" in result.output
        )
        mock_orchestrator.create_instance.assert_called_once_with(
            "test-123",
            workspace_path=Path("/custom/workspace"),
            branch_name="custom-branch",
            tmux_session="custom-session",
        )

    @patch("cc_orchestrator.cli.instances.Orchestrator")
    def test_start_new_instance_json(self, mock_orchestrator_class):
        """Test start command for new instance with JSON output."""
        mock_instance = create_mock_instance()
        mock_orchestrator = create_mock_orchestrator()
        mock_orchestrator.get_instance.return_value = None
        mock_orchestrator.create_instance = AsyncMock(return_value=mock_instance)
        mock_orchestrator_class.return_value = mock_orchestrator

        result = self.runner.invoke(main, ["instances", "start", "test-123", "--json"])
        assert result.exit_code == 0

        output_data = json.loads(result.output)
        assert output_data["status"] == "started"
        assert output_data["instance"]["issue_id"] == "test-123"

    @patch("cc_orchestrator.cli.instances.Orchestrator")
    def test_start_existing_running_instance(self, mock_orchestrator_class):
        """Test start command for already running instance."""
        mock_instance = create_mock_instance()
        mock_orchestrator = create_mock_orchestrator()
        mock_orchestrator.get_instance.return_value = mock_instance
        mock_orchestrator_class.return_value = mock_orchestrator

        result = self.runner.invoke(main, ["instances", "start", "test-123"])
        assert result.exit_code == 0
        assert "Instance for issue test-123 is already running" in result.output

    @patch("cc_orchestrator.cli.instances.Orchestrator")
    def test_start_existing_running_instance_json(self, mock_orchestrator_class):
        """Test start command for already running instance with JSON output."""
        mock_instance = create_mock_instance()
        mock_orchestrator = create_mock_orchestrator()
        mock_orchestrator.get_instance.return_value = mock_instance
        mock_orchestrator_class.return_value = mock_orchestrator

        result = self.runner.invoke(main, ["instances", "start", "test-123", "--json"])
        assert result.exit_code == 0

        output_data = json.loads(result.output)
        assert "error" in output_data
        assert "already running" in output_data["error"]
        assert output_data["issue_id"] == "test-123"

    @patch("cc_orchestrator.cli.instances.Orchestrator")
    def test_start_existing_stopped_instance_success(self, mock_orchestrator_class):
        """Test start command for existing stopped instance that starts successfully."""
        mock_instance = create_mock_instance(with_process_info=False)
        mock_instance.is_running.return_value = False
        mock_instance.start = AsyncMock(return_value=True)
        # After successful start, update info
        mock_instance.get_info.return_value.update(
            {"status": "running", "process_id": 12345}
        )

        mock_orchestrator = create_mock_orchestrator()
        mock_orchestrator.get_instance.return_value = mock_instance
        mock_orchestrator_class.return_value = mock_orchestrator

        result = self.runner.invoke(main, ["instances", "start", "test-123"])
        assert result.exit_code == 0
        assert "Started existing instance for issue test-123" in result.output
        assert "Process ID: 12345" in result.output
        mock_instance.start.assert_called_once()

    @patch("cc_orchestrator.cli.instances.Orchestrator")
    def test_start_existing_stopped_instance_success_json(
        self, mock_orchestrator_class
    ):
        """Test start command for existing stopped instance that starts successfully with JSON output."""
        mock_instance = create_mock_instance(with_process_info=False)
        mock_instance.is_running.return_value = False
        mock_instance.start = AsyncMock(return_value=True)
        # After successful start, update info
        mock_instance.get_info.return_value.update(
            {"status": "running", "process_id": 12345}
        )

        mock_orchestrator = create_mock_orchestrator()
        mock_orchestrator.get_instance.return_value = mock_instance
        mock_orchestrator_class.return_value = mock_orchestrator

        result = self.runner.invoke(main, ["instances", "start", "test-123", "--json"])
        assert result.exit_code == 0

        output_data = json.loads(result.output)
        assert output_data["status"] == "started"
        assert output_data["instance"]["issue_id"] == "test-123"
        mock_instance.start.assert_called_once()

    @patch("cc_orchestrator.cli.instances.Orchestrator")
    def test_start_existing_stopped_instance_failure(self, mock_orchestrator_class):
        """Test start command for existing stopped instance that fails to start."""
        mock_instance = create_mock_instance(with_process_info=False)
        mock_instance.is_running.return_value = False
        mock_instance.start = AsyncMock(return_value=False)

        mock_orchestrator = create_mock_orchestrator()
        mock_orchestrator.get_instance.return_value = mock_instance
        mock_orchestrator_class.return_value = mock_orchestrator

        result = self.runner.invoke(main, ["instances", "start", "test-123"])
        assert result.exit_code == 0
        assert "Failed to start existing instance for issue test-123" in result.output
        mock_instance.start.assert_called_once()

    @patch("cc_orchestrator.cli.instances.Orchestrator")
    def test_start_existing_stopped_instance_failure_json(
        self, mock_orchestrator_class
    ):
        """Test start command for existing stopped instance that fails to start with JSON output."""
        mock_instance = create_mock_instance(with_process_info=False)
        mock_instance.is_running.return_value = False
        mock_instance.start = AsyncMock(return_value=False)

        mock_orchestrator = create_mock_orchestrator()
        mock_orchestrator.get_instance.return_value = mock_instance
        mock_orchestrator_class.return_value = mock_orchestrator

        result = self.runner.invoke(main, ["instances", "start", "test-123", "--json"])
        assert result.exit_code == 0

        output_data = json.loads(result.output)
        assert "error" in output_data
        assert "Failed to start existing instance" in output_data["error"]
        assert output_data["issue_id"] == "test-123"
        mock_instance.start.assert_called_once()

    @patch("cc_orchestrator.cli.instances.Orchestrator")
    def test_start_new_instance_failure(self, mock_orchestrator_class):
        """Test start command when new instance fails to start."""
        mock_instance = create_mock_instance()
        mock_instance.start = AsyncMock(return_value=False)

        mock_orchestrator = create_mock_orchestrator()
        mock_orchestrator.get_instance.return_value = None
        mock_orchestrator.create_instance = AsyncMock(return_value=mock_instance)
        mock_orchestrator_class.return_value = mock_orchestrator

        result = self.runner.invoke(main, ["instances", "start", "test-123"])
        assert result.exit_code == 0
        assert "Failed to start instance for issue test-123" in result.output

    @patch("cc_orchestrator.cli.instances.Orchestrator")
    def test_start_new_instance_failure_json(self, mock_orchestrator_class):
        """Test start command when new instance fails to start with JSON output."""
        mock_instance = create_mock_instance()
        mock_instance.start = AsyncMock(return_value=False)

        mock_orchestrator = create_mock_orchestrator()
        mock_orchestrator.get_instance.return_value = None
        mock_orchestrator.create_instance = AsyncMock(return_value=mock_instance)
        mock_orchestrator_class.return_value = mock_orchestrator

        result = self.runner.invoke(main, ["instances", "start", "test-123", "--json"])
        assert result.exit_code == 0

        output_data = json.loads(result.output)
        assert "error" in output_data
        assert "Failed to start instance" in output_data["error"]
        assert output_data["issue_id"] == "test-123"

    @patch("cc_orchestrator.cli.instances.Orchestrator")
    def test_start_error_handling(self, mock_orchestrator_class):
        """Test start command error handling."""
        mock_orchestrator = create_mock_orchestrator()
        mock_orchestrator.initialize.side_effect = Exception("Test error")
        mock_orchestrator_class.return_value = mock_orchestrator

        result = self.runner.invoke(main, ["instances", "start", "test-123"])
        assert result.exit_code == 0
        assert "Error: Test error" in result.output

    @patch("cc_orchestrator.cli.instances.Orchestrator")
    def test_start_error_handling_json(self, mock_orchestrator_class):
        """Test start command error handling with JSON output."""
        mock_orchestrator = create_mock_orchestrator()
        mock_orchestrator.initialize.side_effect = Exception("Test error")
        mock_orchestrator_class.return_value = mock_orchestrator

        result = self.runner.invoke(main, ["instances", "start", "test-123", "--json"])
        assert result.exit_code == 0

        output_data = json.loads(result.output)
        assert output_data["error"] == "Test error"
        assert output_data["issue_id"] == "test-123"

    # STOP COMMAND TESTS

    @patch("cc_orchestrator.cli.instances.Orchestrator")
    def test_stop_no_instance(self, mock_orchestrator_class):
        """Test stop command with no instance found."""
        mock_orchestrator = create_mock_orchestrator()
        mock_orchestrator.get_instance.return_value = None
        mock_orchestrator_class.return_value = mock_orchestrator

        result = self.runner.invoke(main, ["instances", "stop", "test-123"])
        assert result.exit_code == 0
        assert "No instance found for issue test-123" in result.output
        # Cleanup is called in this case

    @patch("cc_orchestrator.cli.instances.Orchestrator")
    def test_stop_no_instance_json(self, mock_orchestrator_class):
        """Test stop command with no instance found in JSON format."""
        mock_orchestrator = create_mock_orchestrator()
        mock_orchestrator.get_instance.return_value = None
        mock_orchestrator_class.return_value = mock_orchestrator

        result = self.runner.invoke(main, ["instances", "stop", "test-123", "--json"])
        assert result.exit_code == 0

        output_data = json.loads(result.output)
        assert "error" in output_data
        assert "No instance found" in output_data["error"]
        assert output_data["issue_id"] == "test-123"

    @patch("cc_orchestrator.cli.instances.Orchestrator")
    def test_stop_already_stopped_instance(self, mock_orchestrator_class):
        """Test stop command with already stopped instance."""
        mock_instance = create_mock_instance(with_process_info=False)
        mock_orchestrator = create_mock_orchestrator()
        mock_orchestrator.get_instance.return_value = mock_instance
        mock_orchestrator_class.return_value = mock_orchestrator

        result = self.runner.invoke(main, ["instances", "stop", "test-123"])
        assert result.exit_code == 0
        assert "Instance for issue test-123 is already stopped" in result.output
        # Cleanup is called in this case

    @patch("cc_orchestrator.cli.instances.Orchestrator")
    def test_stop_already_stopped_instance_json(self, mock_orchestrator_class):
        """Test stop command with already stopped instance in JSON format."""
        mock_instance = create_mock_instance(with_process_info=False)
        mock_orchestrator = create_mock_orchestrator()
        mock_orchestrator.get_instance.return_value = mock_instance
        mock_orchestrator_class.return_value = mock_orchestrator

        result = self.runner.invoke(main, ["instances", "stop", "test-123", "--json"])
        assert result.exit_code == 0

        output_data = json.loads(result.output)
        assert output_data["status"] == "already_stopped"
        assert output_data["issue_id"] == "test-123"

    @patch("cc_orchestrator.cli.instances.Orchestrator")
    def test_stop_running_instance_success(self, mock_orchestrator_class):
        """Test stop command with running instance that stops successfully."""
        mock_instance = create_mock_instance()
        mock_orchestrator = create_mock_orchestrator()
        mock_orchestrator.get_instance.return_value = mock_instance
        mock_orchestrator_class.return_value = mock_orchestrator

        result = self.runner.invoke(main, ["instances", "stop", "test-123"])
        assert result.exit_code == 0
        assert "Successfully stopped instance for issue test-123" in result.output
        mock_instance.stop.assert_called_once()
        # Cleanup is called in this case

    @patch("cc_orchestrator.cli.instances.Orchestrator")
    def test_stop_running_instance_success_json(self, mock_orchestrator_class):
        """Test stop command with running instance that stops successfully in JSON format."""
        mock_instance = create_mock_instance()
        mock_orchestrator = create_mock_orchestrator()
        mock_orchestrator.get_instance.return_value = mock_instance
        mock_orchestrator_class.return_value = mock_orchestrator

        result = self.runner.invoke(main, ["instances", "stop", "test-123", "--json"])
        assert result.exit_code == 0

        output_data = json.loads(result.output)
        assert output_data["status"] == "stopped"
        assert output_data["issue_id"] == "test-123"

    @patch("cc_orchestrator.cli.instances.Orchestrator")
    def test_stop_running_instance_failure(self, mock_orchestrator_class):
        """Test stop command with running instance that fails to stop."""
        mock_instance = create_mock_instance()
        mock_instance.stop = AsyncMock(return_value=False)

        mock_orchestrator = create_mock_orchestrator()
        mock_orchestrator.get_instance.return_value = mock_instance
        mock_orchestrator_class.return_value = mock_orchestrator

        result = self.runner.invoke(main, ["instances", "stop", "test-123"])
        assert result.exit_code == 0
        assert "Failed to stop instance for issue test-123" in result.output
        mock_instance.stop.assert_called_once()

    @patch("cc_orchestrator.cli.instances.Orchestrator")
    def test_stop_running_instance_failure_json(self, mock_orchestrator_class):
        """Test stop command with running instance that fails to stop in JSON format."""
        mock_instance = create_mock_instance()
        mock_instance.stop = AsyncMock(return_value=False)

        mock_orchestrator = create_mock_orchestrator()
        mock_orchestrator.get_instance.return_value = mock_instance
        mock_orchestrator_class.return_value = mock_orchestrator

        result = self.runner.invoke(main, ["instances", "stop", "test-123", "--json"])
        assert result.exit_code == 0

        output_data = json.loads(result.output)
        assert "error" in output_data
        assert "Failed to stop" in output_data["error"]
        assert output_data["issue_id"] == "test-123"

    @patch("cc_orchestrator.cli.instances.Orchestrator")
    def test_stop_with_force_and_timeout_options(self, mock_orchestrator_class):
        """Test stop command with force and timeout options."""
        mock_instance = create_mock_instance()
        mock_orchestrator = create_mock_orchestrator()
        mock_orchestrator.get_instance.return_value = mock_instance
        mock_orchestrator_class.return_value = mock_orchestrator

        result = self.runner.invoke(
            main, ["instances", "stop", "test-123", "--force", "--timeout", "60"]
        )
        assert result.exit_code == 0
        assert "Successfully stopped instance for issue test-123" in result.output
        mock_instance.stop.assert_called_once()

    @patch("cc_orchestrator.cli.instances.Orchestrator")
    def test_stop_error_handling(self, mock_orchestrator_class):
        """Test stop command error handling."""
        mock_orchestrator = create_mock_orchestrator()
        mock_orchestrator.initialize.side_effect = Exception("Test error")
        mock_orchestrator_class.return_value = mock_orchestrator

        result = self.runner.invoke(main, ["instances", "stop", "test-123"])
        assert result.exit_code == 0
        assert "Error: Test error" in result.output

    @patch("cc_orchestrator.cli.instances.Orchestrator")
    def test_stop_error_handling_json(self, mock_orchestrator_class):
        """Test stop command error handling with JSON output."""
        mock_orchestrator = create_mock_orchestrator()
        mock_orchestrator.initialize.side_effect = Exception("Test error")
        mock_orchestrator_class.return_value = mock_orchestrator

        result = self.runner.invoke(main, ["instances", "stop", "test-123", "--json"])
        assert result.exit_code == 0

        output_data = json.loads(result.output)
        assert output_data["error"] == "Test error"

    # LIST COMMAND TESTS

    @patch("cc_orchestrator.cli.instances.Orchestrator")
    def test_list_no_instances(self, mock_orchestrator_class):
        """Test list command with no instances."""
        mock_orchestrator = create_mock_orchestrator()
        mock_orchestrator.list_instances.return_value = []
        mock_orchestrator_class.return_value = mock_orchestrator

        result = self.runner.invoke(main, ["instances", "list"])
        assert result.exit_code == 0
        assert "No active instances found" in result.output
        # Note: cleanup is not called because function returns early when no instances

    @patch("cc_orchestrator.cli.instances.Orchestrator")
    def test_list_no_instances_json(self, mock_orchestrator_class):
        """Test list command with no instances in JSON format."""
        mock_orchestrator = create_mock_orchestrator()
        mock_orchestrator.list_instances.return_value = []
        mock_orchestrator_class.return_value = mock_orchestrator

        result = self.runner.invoke(main, ["instances", "list", "--json"])
        assert result.exit_code == 0

        output_data = json.loads(result.output)
        assert output_data == {"instances": [], "total": 0}

    @patch("cc_orchestrator.cli.instances.Orchestrator")
    def test_list_no_running_instances(self, mock_orchestrator_class):
        """Test list command with no running instances when using --running-only filter."""
        mock_instance = create_mock_instance(with_process_info=False)
        mock_orchestrator = create_mock_orchestrator()
        mock_orchestrator.list_instances.return_value = [mock_instance]
        mock_orchestrator_class.return_value = mock_orchestrator

        result = self.runner.invoke(main, ["instances", "list", "--running-only"])
        assert result.exit_code == 0
        assert "No running instances found" in result.output
        # Note: cleanup is not called because function returns early when no instances

    @patch("cc_orchestrator.cli.instances.Orchestrator")
    def test_list_with_instances(self, mock_orchestrator_class):
        """Test list command with instances."""
        mock_instance = create_mock_instance()
        mock_orchestrator = create_mock_orchestrator()
        mock_orchestrator.list_instances.return_value = [mock_instance]
        mock_orchestrator_class.return_value = mock_orchestrator

        result = self.runner.invoke(main, ["instances", "list"])
        assert result.exit_code == 0
        assert "Active Claude Instances (1)" in result.output
        assert "🟢 test-123" in result.output
        assert "PID: 12345" in result.output
        assert "Resources: 25.5% CPU, 128.0 MB RAM" in result.output

    @patch("cc_orchestrator.cli.instances.Orchestrator")
    def test_list_with_instances_json(self, mock_orchestrator_class):
        """Test list command with instances in JSON format."""
        mock_instance = create_mock_instance()
        mock_orchestrator = create_mock_orchestrator()
        mock_orchestrator.list_instances.return_value = [mock_instance]
        mock_orchestrator_class.return_value = mock_orchestrator

        result = self.runner.invoke(main, ["instances", "list", "--json"])
        assert result.exit_code == 0

        output_data = json.loads(result.output)
        assert output_data["total"] == 1
        assert output_data["filter"] == "all"
        assert len(output_data["instances"]) == 1
        instance_data = output_data["instances"][0]
        assert instance_data["issue_id"] == "test-123"
        assert instance_data["process_status"] == "running"

    @patch("cc_orchestrator.cli.instances.Orchestrator")
    def test_list_running_only_filter(self, mock_orchestrator_class):
        """Test list command with --running-only filter."""
        mock_instance1 = create_mock_instance(
            issue_id="test-123", with_process_info=True
        )
        mock_instance2 = create_mock_instance(
            issue_id="test-456", with_process_info=False
        )

        mock_orchestrator = create_mock_orchestrator()
        mock_orchestrator.list_instances.return_value = [mock_instance1, mock_instance2]
        mock_orchestrator_class.return_value = mock_orchestrator

        result = self.runner.invoke(main, ["instances", "list", "--running-only"])
        assert result.exit_code == 0
        assert "Running Claude Instances (1)" in result.output
        assert "🟢 test-123" in result.output

    @patch("cc_orchestrator.cli.instances.Orchestrator")
    def test_list_running_only_filter_json(self, mock_orchestrator_class):
        """Test list command with --running-only filter in JSON format."""
        mock_instance1 = create_mock_instance(
            issue_id="test-123", with_process_info=True
        )
        mock_instance2 = create_mock_instance(
            issue_id="test-456", with_process_info=False
        )

        mock_orchestrator = create_mock_orchestrator()
        mock_orchestrator.list_instances.return_value = [mock_instance1, mock_instance2]
        mock_orchestrator_class.return_value = mock_orchestrator

        result = self.runner.invoke(
            main, ["instances", "list", "--running-only", "--json"]
        )
        assert result.exit_code == 0

        output_data = json.loads(result.output)
        assert output_data["total"] == 1
        assert output_data["filter"] == "running"
        assert len(output_data["instances"]) == 1
        assert output_data["instances"][0]["issue_id"] == "test-123"

    @patch("cc_orchestrator.cli.instances.Orchestrator")
    def test_list_error_handling(self, mock_orchestrator_class):
        """Test list command error handling."""
        mock_orchestrator = create_mock_orchestrator()
        mock_orchestrator.initialize.side_effect = Exception("Test error")
        mock_orchestrator_class.return_value = mock_orchestrator

        result = self.runner.invoke(main, ["instances", "list"])
        assert result.exit_code == 0
        assert "Error: Test error" in result.output

    @patch("cc_orchestrator.cli.instances.Orchestrator")
    def test_list_error_handling_json(self, mock_orchestrator_class):
        """Test list command error handling with JSON output."""
        mock_orchestrator = create_mock_orchestrator()
        mock_orchestrator.initialize.side_effect = Exception("Test error")
        mock_orchestrator_class.return_value = mock_orchestrator

        result = self.runner.invoke(main, ["instances", "list", "--json"])
        assert result.exit_code == 0

        output_data = json.loads(result.output)
        assert output_data == {"error": "Test error"}
