"""
Comprehensive tests for cli/instances.py targeting 74% coverage compliance.

This test suite provides complete coverage for CLI instance management including:
- Instance status command functionality
- Instance start command with various options
- Instance stop command with force and timeout options
- Instance list command with filtering
- Async command execution patterns
- JSON output formatting
- Error handling and exception paths
- Click command group and option handling

Target: 100% coverage of cli/instances.py (204 statements)
"""

import json
from unittest.mock import AsyncMock, Mock, patch

import click
from click.testing import CliRunner

from cc_orchestrator.cli.instances import (
    instances,
    start,
    status,
    stop,
)
from cc_orchestrator.cli.instances import (
    list as list_command,
)


class TestInstancesCommandGroup:
    """Test the instances command group."""

    def test_instances_group_creation(self):
        """Test instances command group is properly created."""
        assert instances is not None
        assert isinstance(instances, click.Group)

    def test_instances_group_help(self):
        """Test instances group has help text."""
        runner = CliRunner()
        result = runner.invoke(instances, ["--help"])
        assert result.exit_code == 0
        assert "Manage Claude Code instances" in result.output


class TestStatusCommand:
    """Test the instance status command."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    @patch("cc_orchestrator.cli.instances.Orchestrator")
    def test_status_command_basic(self, mock_orchestrator):
        """Test basic status command execution."""
        # Mock the orchestrator - use Mock, not AsyncMock for main object
        mock_orch_instance = Mock()
        mock_orchestrator.return_value = mock_orch_instance

        # Mock empty instances list (synchronous call)
        mock_orch_instance.list_instances.return_value = []
        # These are async methods
        mock_orch_instance.initialize = AsyncMock()
        mock_orch_instance.cleanup = AsyncMock()

        result = self.runner.invoke(status)

        assert result.exit_code == 0
        assert "No active instances found" in result.output

    @patch("cc_orchestrator.cli.instances.Orchestrator")
    def test_status_command_json_output(self, mock_orchestrator):
        """Test status command with JSON output."""
        # Mock the orchestrator
        mock_orch_instance = Mock()
        mock_orchestrator.return_value = mock_orch_instance

        # Mock empty instances list
        mock_orch_instance.list_instances.return_value = []
        mock_orch_instance.initialize = AsyncMock()
        mock_orch_instance.cleanup = AsyncMock()

        result = self.runner.invoke(status, ["--json"])

        assert result.exit_code == 0
        # Should output valid JSON
        output_data = json.loads(result.output)
        assert output_data["instances"] == []
        assert output_data["total"] == 0

    @patch("cc_orchestrator.cli.instances.Orchestrator")
    def test_status_command_with_instances(self, mock_orchestrator):
        """Test status command with active instances."""
        # Mock the orchestrator
        mock_orch_instance = Mock()
        mock_orchestrator.return_value = mock_orch_instance

        # Mock instance
        mock_instance = Mock()
        mock_instance.get_info.return_value = {
            "issue_id": "TEST-123",
            "status": "running",
            "workspace_path": "/test/workspace",
            "branch_name": "feature/test",
            "tmux_session": "claude-test-123",
            "process_id": 12345,
        }
        mock_instance.get_process_status = AsyncMock(
            return_value=Mock(
                status=Mock(value="running"), cpu_percent=25.5, memory_mb=512.0
            )
        )

        mock_orch_instance.list_instances.return_value = [mock_instance]
        mock_orch_instance.initialize = AsyncMock()
        mock_orch_instance.cleanup = AsyncMock()

        result = self.runner.invoke(status)

        assert result.exit_code == 0
        assert "TEST-123" in result.output
        assert "running" in result.output

    @patch("cc_orchestrator.cli.instances.Orchestrator")
    def test_status_command_error_handling(self, mock_orchestrator):
        """Test status command error handling."""
        # Mock orchestrator to raise exception
        mock_orchestrator.side_effect = Exception("Connection failed")

        result = self.runner.invoke(status)

        assert result.exit_code == 0  # Command handles errors gracefully
        assert "Error:" in result.output or "Connection failed" in result.output


class TestStartCommand:
    """Test the instance start command."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    @patch("cc_orchestrator.cli.instances.Orchestrator")
    def test_start_command_basic(self, mock_orchestrator):
        """Test basic start command execution."""
        # Mock the orchestrator
        mock_orch_instance = Mock()
        mock_orchestrator.return_value = mock_orch_instance

        # Mock no existing instance
        mock_orch_instance.get_instance.return_value = None
        mock_orch_instance.initialize = AsyncMock()
        mock_orch_instance.cleanup = AsyncMock()

        # Mock create and start instance
        mock_instance = Mock()
        mock_instance.start = AsyncMock(return_value=True)
        mock_instance.get_info.return_value = {
            "process_id": 12345,
            "workspace_path": "/test/workspace",
            "branch_name": "feature/test",
            "tmux_session": "claude-test-123",
        }
        mock_orch_instance.create_instance = AsyncMock(return_value=mock_instance)

        result = self.runner.invoke(start, ["TEST-123"])

        assert result.exit_code == 0
        assert "Successfully started" in result.output or "started" in result.output

    @patch("cc_orchestrator.cli.instances.Orchestrator")
    def test_start_command_with_options(self, mock_orchestrator):
        """Test start command with various options."""
        # Mock the orchestrator
        mock_orch_instance = Mock()
        mock_orchestrator.return_value = mock_orch_instance

        # Mock no existing instance
        mock_orch_instance.get_instance.return_value = None
        mock_orch_instance.initialize = AsyncMock()
        mock_orch_instance.cleanup = AsyncMock()

        # Mock create and start instance
        mock_instance = Mock()
        mock_instance.start = AsyncMock(return_value=True)
        mock_instance.get_info.return_value = {
            "process_id": 12345,
            "workspace_path": "/custom/workspace",
            "branch_name": "custom-branch",
            "tmux_session": "custom-session",
        }
        mock_orch_instance.create_instance = AsyncMock(return_value=mock_instance)
        result = self.runner.invoke(
            start,
            [
                "TEST-456",
                "--workspace",
                "/custom/workspace",
                "--branch",
                "custom-branch",
                "--tmux-session",
                "custom-session",
            ],
        )

        assert result.exit_code == 0

    @patch("cc_orchestrator.cli.instances.Orchestrator")
    def test_start_command_existing_running(self, mock_orchestrator):
        """Test start command with existing running instance."""
        # Mock the orchestrator
        mock_orch_instance = Mock()
        mock_orchestrator.return_value = mock_orch_instance

        # Mock existing running instance
        mock_instance = Mock()
        mock_instance.is_running.return_value = True
        mock_orch_instance.get_instance.return_value = mock_instance
        mock_orch_instance.initialize = AsyncMock()
        mock_orch_instance.cleanup = AsyncMock()
        result = self.runner.invoke(start, ["TEST-789"])

        assert result.exit_code == 0
        assert "already running" in result.output

    @patch("cc_orchestrator.cli.instances.Orchestrator")
    def test_start_command_existing_stopped(self, mock_orchestrator):
        """Test start command with existing stopped instance."""
        # Mock the orchestrator
        mock_orch_instance = Mock()
        mock_orchestrator.return_value = mock_orch_instance

        # Mock existing stopped instance
        mock_instance = Mock()
        mock_instance.is_running.return_value = False
        mock_instance.start = AsyncMock(return_value=True)
        mock_instance.get_info.return_value = {
            "process_id": 12345,
            "workspace_path": "/test/workspace",
        }
        mock_orch_instance.get_instance.return_value = mock_instance
        mock_orch_instance.initialize = AsyncMock()
        mock_orch_instance.cleanup = AsyncMock()
        result = self.runner.invoke(start, ["TEST-999"])

        assert result.exit_code == 0
        assert "Started existing instance" in result.output

    @patch("cc_orchestrator.cli.instances.Orchestrator")
    def test_start_command_json_output(self, mock_orchestrator):
        """Test start command with JSON output."""
        # Mock the orchestrator
        mock_orch_instance = Mock()
        mock_orchestrator.return_value = mock_orch_instance

        # Mock no existing instance
        mock_orch_instance.get_instance.return_value = None
        mock_orch_instance.initialize = AsyncMock()
        mock_orch_instance.cleanup = AsyncMock()

        # Mock create and start instance
        mock_instance = Mock()
        mock_instance.start = AsyncMock(return_value=True)
        mock_instance.get_info.return_value = {
            "process_id": 12345,
            "workspace_path": "/test/workspace",
            "branch_name": "feature/test",
            "tmux_session": "claude-test-123",
        }
        mock_orch_instance.create_instance = AsyncMock(return_value=mock_instance)
        result = self.runner.invoke(start, ["TEST-JSON", "--json"])

        assert result.exit_code == 0
        # Should output valid JSON
        output_data = json.loads(result.output)
        assert output_data["status"] == "started"
        assert "instance" in output_data

    @patch("cc_orchestrator.cli.instances.Orchestrator")
    def test_start_command_failure(self, mock_orchestrator):
        """Test start command when start fails."""
        # Mock the orchestrator
        mock_orch_instance = Mock()
        mock_orchestrator.return_value = mock_orch_instance

        # Mock no existing instance
        mock_orch_instance.get_instance.return_value = None
        mock_orch_instance.initialize = AsyncMock()
        mock_orch_instance.cleanup = AsyncMock()

        # Mock create instance but start fails
        mock_instance = Mock()
        mock_instance.start = AsyncMock(return_value=False)
        mock_orch_instance.create_instance = AsyncMock(return_value=mock_instance)
        result = self.runner.invoke(start, ["TEST-FAIL"])

        assert result.exit_code == 0
        assert "Failed to start" in result.output


class TestStopCommand:
    """Test the instance stop command."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    @patch("cc_orchestrator.cli.instances.Orchestrator")
    def test_stop_command_basic(self, mock_orchestrator):
        """Test basic stop command execution."""
        # Mock the orchestrator
        mock_orch_instance = Mock()
        mock_orchestrator.return_value = mock_orch_instance

        # Mock running instance
        mock_instance = Mock()
        mock_instance.is_running.return_value = True
        mock_instance.stop = AsyncMock(return_value=True)
        mock_orch_instance.get_instance.return_value = mock_instance
        mock_orch_instance.initialize = AsyncMock()
        mock_orch_instance.cleanup = AsyncMock()
        result = self.runner.invoke(stop, ["TEST-123"])

        assert result.exit_code == 0
        assert "Successfully stopped" in result.output

    @patch("cc_orchestrator.cli.instances.Orchestrator")
    def test_stop_command_not_found(self, mock_orchestrator):
        """Test stop command with non-existent instance."""
        # Mock the orchestrator
        mock_orch_instance = Mock()
        mock_orchestrator.return_value = mock_orch_instance

        # Mock no instance found
        mock_orch_instance.get_instance.return_value = None
        mock_orch_instance.initialize = AsyncMock()
        mock_orch_instance.cleanup = AsyncMock()
        result = self.runner.invoke(stop, ["TEST-404"])

        assert result.exit_code == 0
        assert "No instance found" in result.output

    @patch("cc_orchestrator.cli.instances.Orchestrator")
    def test_stop_command_not_running(self, mock_orchestrator):
        """Test stop command with stopped instance."""
        # Mock the orchestrator
        mock_orch_instance = Mock()
        mock_orchestrator.return_value = mock_orch_instance

        # Mock stopped instance
        mock_instance = Mock()
        mock_instance.is_running.return_value = False
        mock_orch_instance.get_instance.return_value = mock_instance
        mock_orch_instance.initialize = AsyncMock()
        mock_orch_instance.cleanup = AsyncMock()
        result = self.runner.invoke(stop, ["TEST-STOPPED"])

        assert result.exit_code == 0
        assert "already stopped" in result.output

    @patch("cc_orchestrator.cli.instances.Orchestrator")
    def test_stop_command_with_options(self, mock_orchestrator):
        """Test stop command with force and timeout options."""
        # Mock the orchestrator
        mock_orch_instance = Mock()
        mock_orchestrator.return_value = mock_orch_instance

        # Mock running instance
        mock_instance = Mock()
        mock_instance.is_running.return_value = True
        mock_instance.stop = AsyncMock(return_value=True)
        mock_orch_instance.get_instance.return_value = mock_instance
        mock_orch_instance.initialize = AsyncMock()
        mock_orch_instance.cleanup = AsyncMock()
        result = self.runner.invoke(stop, ["TEST-FORCE", "--force", "--timeout", "60"])

        assert result.exit_code == 0
        assert "Successfully stopped" in result.output

    @patch("cc_orchestrator.cli.instances.Orchestrator")
    def test_stop_command_json_output(self, mock_orchestrator):
        """Test stop command with JSON output."""
        # Mock the orchestrator
        mock_orch_instance = Mock()
        mock_orchestrator.return_value = mock_orch_instance

        # Mock running instance
        mock_instance = Mock()
        mock_instance.is_running.return_value = True
        mock_instance.stop = AsyncMock(return_value=True)
        mock_orch_instance.get_instance.return_value = mock_instance
        mock_orch_instance.initialize = AsyncMock()
        mock_orch_instance.cleanup = AsyncMock()
        result = self.runner.invoke(stop, ["TEST-JSON", "--json"])

        assert result.exit_code == 0
        # Should output valid JSON
        output_data = json.loads(result.output)
        assert output_data["status"] == "stopped"


class TestListCommand:
    """Test the instance list command."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    @patch("cc_orchestrator.cli.instances.Orchestrator")
    def test_list_command_basic(self, mock_orchestrator):
        """Test basic list command execution."""
        # Mock the orchestrator
        mock_orch_instance = Mock()
        mock_orchestrator.return_value = mock_orch_instance

        # Mock empty instances list
        mock_orch_instance.list_instances.return_value = []
        mock_orch_instance.initialize = AsyncMock()
        mock_orch_instance.cleanup = AsyncMock()
        result = self.runner.invoke(list_command)

        assert result.exit_code == 0
        assert "No active instances found" in result.output

    @patch("cc_orchestrator.cli.instances.Orchestrator")
    def test_list_command_with_instances(self, mock_orchestrator):
        """Test list command with instances."""
        # Mock the orchestrator
        mock_orch_instance = Mock()
        mock_orchestrator.return_value = mock_orch_instance

        # Mock instances
        mock_instance1 = Mock()
        mock_instance1.is_running.return_value = True
        mock_instance1.get_info.return_value = {
            "issue_id": "TEST-123",
            "status": "running",
            "workspace_path": "/test/workspace1",
            "process_id": 12345,
        }
        mock_instance1.get_process_status = AsyncMock(
            return_value=Mock(
                status=Mock(value="running"), cpu_percent=25.5, memory_mb=512.0
            )
        )

        mock_instance2 = Mock()
        mock_instance2.is_running.return_value = False
        mock_instance2.get_info.return_value = {
            "issue_id": "TEST-456",
            "status": "stopped",
            "workspace_path": "/test/workspace2",
            "process_id": None,
        }
        mock_instance2.get_process_status = AsyncMock(return_value=None)

        mock_orch_instance.list_instances.return_value = [
            mock_instance1,
            mock_instance2,
        ]
        mock_orch_instance.initialize = AsyncMock()
        mock_orch_instance.cleanup = AsyncMock()
        result = self.runner.invoke(list_command)

        assert result.exit_code == 0
        assert "TEST-123" in result.output
        assert "TEST-456" in result.output
        assert "Active Claude Instances (2)" in result.output

    @patch("cc_orchestrator.cli.instances.Orchestrator")
    def test_list_command_running_only(self, mock_orchestrator):
        """Test list command with running-only filter."""
        # Mock the orchestrator
        mock_orch_instance = Mock()
        mock_orchestrator.return_value = mock_orch_instance

        # Mock mixed instances
        mock_running = Mock()
        mock_running.is_running.return_value = True
        mock_running.get_info.return_value = {
            "issue_id": "RUNNING-123",
            "status": "running",
        }
        mock_running.get_process_status = AsyncMock(
            return_value=Mock(
                status=Mock(value="running"), cpu_percent=30.0, memory_mb=256.0
            )
        )

        mock_stopped = Mock()
        mock_stopped.is_running.return_value = False

        mock_orch_instance.list_instances.return_value = [mock_running, mock_stopped]
        mock_orch_instance.initialize = AsyncMock()
        mock_orch_instance.cleanup = AsyncMock()
        result = self.runner.invoke(list_command, ["--running-only"])

        assert result.exit_code == 0
        assert "RUNNING-123" in result.output
        assert "Running Claude Instances (1)" in result.output

    @patch("cc_orchestrator.cli.instances.Orchestrator")
    def test_list_command_json_output(self, mock_orchestrator):
        """Test list command with JSON output."""
        # Mock the orchestrator
        mock_orch_instance = Mock()
        mock_orchestrator.return_value = mock_orch_instance

        # Mock single instance
        mock_instance = Mock()
        mock_instance.is_running.return_value = True
        mock_instance.get_info.return_value = {
            "issue_id": "JSON-TEST",
            "status": "running",
            "workspace_path": "/test/workspace",
            "process_id": 99999,
        }
        mock_instance.get_process_status = AsyncMock(
            return_value=Mock(
                status=Mock(value="running"), cpu_percent=15.5, memory_mb=1024.0
            )
        )

        mock_orch_instance.list_instances.return_value = [mock_instance]
        mock_orch_instance.initialize = AsyncMock()
        mock_orch_instance.cleanup = AsyncMock()
        result = self.runner.invoke(list_command, ["--json"])

        assert result.exit_code == 0
        # Should output valid JSON
        output_data = json.loads(result.output)
        assert "instances" in output_data
        assert output_data["total"] == 1
        assert output_data["instances"][0]["issue_id"] == "JSON-TEST"


class TestAsyncCommandExecution:
    """Test async command execution patterns and error handling."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    @patch("cc_orchestrator.cli.instances.Orchestrator")
    def test_async_exception_handling(self, mock_orchestrator):
        """Test async exception handling in commands."""
        # Mock orchestrator to raise exception during initialization
        mock_orch_instance = Mock()
        mock_orchestrator.return_value = mock_orch_instance
        mock_orch_instance.initialize = AsyncMock(side_effect=Exception("Async error"))
        result = self.runner.invoke(status)

        assert result.exit_code == 0  # Commands handle errors gracefully
        assert "Error:" in result.output or "error" in result.output.lower()

    @patch("cc_orchestrator.cli.instances.logger")
    @patch("cc_orchestrator.cli.instances.Orchestrator")
    def test_logging_in_error_paths(self, mock_orchestrator, mock_logger):
        """Test logging occurs during error conditions."""
        # Mock orchestrator to raise exception
        mock_orchestrator.side_effect = Exception("Test error")
        self.runner.invoke(status)

        # Verify logger was called for error
        mock_logger.error.assert_called()


class TestCommandArgumentValidation:
    """Test command argument and option validation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    def test_start_command_missing_issue_id(self):
        """Test start command without required issue_id argument."""
        result = self.runner.invoke(start, [])

        assert result.exit_code != 0  # Should fail due to missing argument

    def test_stop_command_missing_issue_id(self):
        """Test stop command without required issue_id argument."""
        result = self.runner.invoke(stop, [])

        assert result.exit_code != 0  # Should fail due to missing argument

    @patch("cc_orchestrator.cli.instances.Orchestrator")
    def test_workspace_option_path_validation(self, mock_orchestrator):
        """Test workspace option accepts Path objects."""
        # This tests the click.Path(path_type=Path) type conversion
        # Mock the orchestrator
        mock_orch_instance = Mock()
        mock_orchestrator.return_value = mock_orch_instance
        mock_orch_instance.get_instance.return_value = None
        mock_orch_instance.initialize = AsyncMock()
        mock_orch_instance.cleanup = AsyncMock()

        # Mock create instance
        mock_instance = Mock()
        mock_instance.start = AsyncMock(return_value=True)
        mock_instance.get_info.return_value = {
            "process_id": 12345,
            "workspace_path": "/valid/path",
            "branch_name": "feature/test",
            "tmux_session": "claude-test",
        }
        mock_orch_instance.create_instance = AsyncMock(return_value=mock_instance)

        result = self.runner.invoke(start, ["TEST-PATH", "--workspace", "/valid/path"])

        # Should not fail due to path validation
        assert result.exit_code == 0


class TestCommandOutputFormatting:
    """Test command output formatting and display."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    @patch("cc_orchestrator.cli.instances.Orchestrator")
    def test_human_readable_output_formatting(self, mock_orchestrator):
        """Test human-readable output formatting includes emojis and formatting."""
        # Mock the orchestrator
        mock_orch_instance = Mock()
        mock_orchestrator.return_value = mock_orch_instance

        # Mock instances with different statuses
        mock_running = Mock()
        mock_running.is_running.return_value = True
        mock_running.get_info.return_value = {
            "issue_id": "RUNNING-TEST",
            "status": "running",
            "workspace_path": "/test/running-workspace",
        }
        mock_running.get_process_status = AsyncMock(
            return_value=Mock(
                status=Mock(value="running"), cpu_percent=50.0, memory_mb=2048.0
            )
        )

        mock_stopped = Mock()
        mock_stopped.is_running.return_value = False
        mock_stopped.get_info.return_value = {
            "issue_id": "STOPPED-TEST",
            "status": "stopped",
            "workspace_path": "/test/stopped-workspace",
        }
        mock_stopped.get_process_status = AsyncMock(return_value=None)

        mock_orch_instance.list_instances.return_value = [mock_running, mock_stopped]
        mock_orch_instance.initialize = AsyncMock()
        mock_orch_instance.cleanup = AsyncMock()
        result = self.runner.invoke(list_command)

        assert result.exit_code == 0
        # Should contain emoji status indicators
        assert "🟢" in result.output or "🔴" in result.output
        assert "RUNNING-TEST" in result.output
        assert "STOPPED-TEST" in result.output


class TestCoverageTargetedCalls:
    """Tests specifically targeting uncovered code paths for 100% coverage."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    @patch("cc_orchestrator.cli.instances.Orchestrator")
    def test_process_status_none_handling(self, mock_orchestrator):
        """Test handling when process status returns None."""
        # Mock the orchestrator
        mock_orch_instance = Mock()
        mock_orchestrator.return_value = mock_orch_instance

        # Mock instance with None process status
        mock_instance = Mock()
        mock_instance.get_info.return_value = {
            "issue_id": "NO-PROCESS",
            "status": "stopped",
            "workspace_path": "/test/workspace",
        }
        mock_instance.get_process_status = AsyncMock(return_value=None)

        mock_orch_instance.list_instances.return_value = [mock_instance]
        mock_orch_instance.initialize = AsyncMock()
        mock_orch_instance.cleanup = AsyncMock()
        result = self.runner.invoke(status)

        assert result.exit_code == 0
        assert "NO-PROCESS" in result.output

    @patch("cc_orchestrator.cli.instances.Orchestrator")
    def test_start_existing_instance_failure(self, mock_orchestrator):
        """Test start command when existing instance start fails."""
        # Mock the orchestrator
        mock_orch_instance = Mock()
        mock_orchestrator.return_value = mock_orch_instance

        # Mock existing stopped instance that fails to start
        mock_instance = Mock()
        mock_instance.is_running.return_value = False
        mock_instance.start = AsyncMock(return_value=False)  # Start fails
        mock_orch_instance.get_instance.return_value = mock_instance
        mock_orch_instance.initialize = AsyncMock()
        mock_orch_instance.cleanup = AsyncMock()
        result = self.runner.invoke(start, ["EXISTING-FAIL"])

        assert result.exit_code == 0
        assert "Failed to start existing instance" in result.output

    @patch("cc_orchestrator.cli.instances.Orchestrator")
    def test_stop_command_failure(self, mock_orchestrator):
        """Test stop command when stop operation fails."""
        # Mock the orchestrator
        mock_orch_instance = Mock()
        mock_orchestrator.return_value = mock_orch_instance

        # Mock running instance that fails to stop
        mock_instance = Mock()
        mock_instance.is_running.return_value = True
        mock_instance.stop = AsyncMock(return_value=False)  # Stop fails
        mock_orch_instance.get_instance.return_value = mock_instance
        mock_orch_instance.initialize = AsyncMock()
        mock_orch_instance.cleanup = AsyncMock()
        result = self.runner.invoke(stop, ["STOP-FAIL"])

        assert result.exit_code == 0
        assert "Failed to stop" in result.output

    @patch("cc_orchestrator.cli.instances.Orchestrator")
    def test_resource_display_conditional_paths(self, mock_orchestrator):
        """Test conditional resource display paths in list command."""
        # Mock the orchestrator
        mock_orch_instance = Mock()
        mock_orchestrator.return_value = mock_orch_instance

        # Mock instance with process but no resource info
        mock_instance = Mock()
        mock_instance.is_running.return_value = True
        mock_instance.get_info.return_value = {
            "issue_id": "RESOURCE-TEST",
            "status": "running",
            "workspace_path": "/test",
            "process_id": 12345,
        }
        # Process status with missing cpu/memory fields
        mock_instance.get_process_status = AsyncMock(
            return_value=Mock(
                status=Mock(value="running"),
                cpu_percent=None,  # Missing resource info
                memory_mb=None,
            )
        )

        mock_orch_instance.list_instances.return_value = [mock_instance]
        mock_orch_instance.initialize = AsyncMock()
        mock_orch_instance.cleanup = AsyncMock()
        result = self.runner.invoke(list_command)

        assert result.exit_code == 0
        assert "RESOURCE-TEST" in result.output
