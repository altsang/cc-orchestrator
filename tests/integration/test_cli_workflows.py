"""Integration tests for CLI workflows."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import yaml
from click.testing import CliRunner

from cc_orchestrator.cli.main import main


class TestConfigWorkflows:
    """Test configuration management workflows."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    def test_config_init_and_show_workflow(self):
        """Test initializing config and then showing it."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / "test-config.yaml"

            # Initialize config
            result = self.runner.invoke(
                main, ["config", "init", "--path", str(config_path)]
            )
            assert result.exit_code == 0
            assert "Configuration initialized" in result.output
            assert config_path.exists()

            # Verify config file content
            with open(config_path) as f:
                config_data = yaml.safe_load(f)
            assert "max_instances" in config_data
            assert config_data["max_instances"] == 5  # Default value

            # Show config
            result = self.runner.invoke(
                main, ["--config", str(config_path), "config", "show"]
            )
            assert result.exit_code == 0

    def test_config_json_output_workflow(self):
        """Test config operations with JSON output."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / "test-config.yaml"

            # Initialize config
            result = self.runner.invoke(
                main, ["config", "init", "--path", str(config_path)]
            )
            assert result.exit_code == 0

            # Show config with JSON output
            result = self.runner.invoke(
                main, ["--json", "--config", str(config_path), "config", "show"]
            )
            assert result.exit_code == 0
            # Output should be valid JSON (basic check)
            assert "{" in result.output and "}" in result.output

    def test_config_validate_workflow(self):
        """Test config validation workflow."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / "test-config.yaml"

            # Initialize config
            result = self.runner.invoke(
                main, ["config", "init", "--path", str(config_path)]
            )
            assert result.exit_code == 0

            # Validate config
            result = self.runner.invoke(
                main, ["--config", str(config_path), "config", "validate"]
            )
            assert result.exit_code == 0
            assert "Configuration is valid" in result.output

    def test_config_get_workflow(self):
        """Test getting individual config values."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / "test-config.yaml"

            # Initialize config
            result = self.runner.invoke(
                main, ["config", "init", "--path", str(config_path)]
            )
            assert result.exit_code == 0

            # Get specific config value
            result = self.runner.invoke(
                main, ["--config", str(config_path), "config", "get", "max_instances"]
            )
            assert result.exit_code == 0


class TestOutputFormattingWorkflows:
    """Test output formatting across different commands."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    def test_verbose_output_workflow(self):
        """Test verbose output across commands."""
        # Test verbose with different commands
        commands = [
            ["instances", "list"],
            ["tasks", "list"],
            ["worktrees", "list"],
        ]

        for cmd in commands:
            result = self.runner.invoke(main, ["--verbose"] + cmd)
            assert result.exit_code == 0

    def test_quiet_output_workflow(self):
        """Test quiet output across commands."""
        # Test quiet with different commands
        commands = [
            ["instances", "list"],
            ["tasks", "list"],
            ["worktrees", "list"],
        ]

        for cmd in commands:
            result = self.runner.invoke(main, ["--quiet"] + cmd)
            assert result.exit_code == 0

    def test_json_output_workflow(self):
        """Test JSON output across commands."""
        # Test JSON with different commands
        commands = [
            ["instances", "list"],
            ["tasks", "list"],
            ["worktrees", "list"],
        ]

        for cmd in commands:
            result = self.runner.invoke(main, ["--json"] + cmd)
            assert result.exit_code == 0


class TestCommandGroupWorkflows:
    """Test workflows across command groups."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    def test_help_system_workflow(self):
        """Test help system across all command groups."""
        # Test main help
        result = self.runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "Claude Code Orchestrator" in result.output

        # Test command group help
        groups = ["instances", "tasks", "worktrees", "config", "web"]
        for group in groups:
            result = self.runner.invoke(main, [group, "--help"])
            assert result.exit_code == 0

    def test_instance_management_workflow(self):
        """Test instance management command workflow."""
        # List instances
        result = self.runner.invoke(main, ["instances", "list"])
        assert result.exit_code == 0

        # Check status
        result = self.runner.invoke(main, ["instances", "status"])
        assert result.exit_code == 0

        # Start instance (simulated)
        result = self.runner.invoke(main, ["instances", "start", "test-issue-123"])
        assert result.exit_code == 0

        # Stop instance (simulated)
        result = self.runner.invoke(main, ["instances", "stop", "test-issue-123"])
        assert result.exit_code == 0

    def test_worktree_management_workflow(self):
        """Test worktree management command workflow."""
        with patch("cc_orchestrator.cli.worktrees.WorktreeService") as mock_service:
            # Mock service responses
            mock_service.return_value.list_worktrees.return_value = []
            mock_service.return_value.create_worktree.return_value = {
                "id": 1,
                "name": "test-feature",
                "path": "/test/path",
                "branch": "feature-branch",
                "commit": "abcd1234",
                "instance_id": None,
            }
            mock_service.return_value.cleanup_worktrees.return_value = {
                "git_cleaned": [],
                "db_cleaned": [],
            }

            # List worktrees
            result = self.runner.invoke(main, ["worktrees", "list"])
            assert result.exit_code == 0

            # Create worktree with correct syntax (name and branch required)
            result = self.runner.invoke(
                main, ["worktrees", "create", "test-feature", "feature-branch"]
            )
            assert result.exit_code == 0

            # Cleanup worktrees
            result = self.runner.invoke(main, ["worktrees", "cleanup"])
            assert result.exit_code == 0

    def test_task_management_workflow(self):
        """Test task management command workflow."""
        # List tasks
        result = self.runner.invoke(main, ["tasks", "list"])
        assert result.exit_code == 0

        # Show task details
        result = self.runner.invoke(main, ["tasks", "show", "task-456"])
        assert result.exit_code == 0

        # Assign task
        result = self.runner.invoke(main, ["tasks", "assign", "task-456"])
        assert result.exit_code == 0

    def test_web_interface_workflow(self):
        """Test web interface command workflow."""
        # Check web status
        result = self.runner.invoke(main, ["web", "status"])
        assert result.exit_code == 0

        # Mock uvicorn.run to prevent hanging during tests
        with patch('uvicorn.run') as mock_uvicorn:
            # Start web interface (simulated)
            result = self.runner.invoke(main, ["web", "start"])
            assert result.exit_code == 0
            mock_uvicorn.assert_called_once()

            # Reset mock for next test
            mock_uvicorn.reset_mock()

            # Start with custom settings
            result = self.runner.invoke(
                main, ["web", "start", "--host", "0.0.0.0", "--port", "9000"]
            )
            assert result.exit_code == 0
            mock_uvicorn.assert_called_once_with(
                "cc_orchestrator.web.app:app",
                host="0.0.0.0",
                port=9000,
                reload=False,
                log_level="info",
            )

        # Stop web interface (doesn't need mocking)
        result = self.runner.invoke(main, ["web", "stop"])
        assert result.exit_code == 0


class TestErrorHandlingWorkflows:
    """Test error handling across CLI workflows."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    def test_missing_arguments_workflow(self):
        """Test error handling for missing arguments."""
        # Test commands that require arguments
        commands_with_args = [
            ["instances", "start"],
            ["instances", "stop"],
            ["tasks", "show"],
            ["tasks", "assign"],
            ["worktrees", "create"],
            ["worktrees", "remove"],
        ]

        for cmd in commands_with_args:
            result = self.runner.invoke(main, cmd)
            assert result.exit_code == 2  # Click error for missing argument

    def test_invalid_subcommands_workflow(self):
        """Test error handling for invalid subcommands."""
        # Test invalid subcommands for each group
        groups = ["instances", "tasks", "worktrees", "config", "web"]
        for group in groups:
            result = self.runner.invoke(main, [group, "invalid-command"])
            assert result.exit_code == 2  # Click error for unknown command

    def test_config_error_handling_workflow(self):
        """Test config-related error handling."""
        # Test with non-existent config file
        result = self.runner.invoke(
            main, ["--config", "/non/existent/config.yaml", "config", "show"]
        )
        assert result.exit_code == 1  # Application error

    def test_conflicting_options_workflow(self):
        """Test error handling for conflicting CLI options."""
        # Test verbose and quiet options together
        result = self.runner.invoke(main, ["--verbose", "--quiet", "config", "show"])
        assert result.exit_code == 2  # Click usage error
        assert "Cannot use both --verbose and --quiet options" in result.output
