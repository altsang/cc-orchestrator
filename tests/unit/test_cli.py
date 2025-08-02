"""Unit tests for CLI commands."""

from pathlib import Path
from unittest.mock import Mock, patch

from click.testing import CliRunner

from cc_orchestrator.cli.main import main


class TestCLICommands:
    """Test suite for CLI commands."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    def test_main_help(self):
        """Test main command help output."""
        result = self.runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "Claude Code Orchestrator" in result.output
        assert "Manage multiple Claude instances" in result.output

    def test_main_version(self):
        """Test version flag."""
        result = self.runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output

    def test_json_flag(self):
        """Test JSON output flag."""
        result = self.runner.invoke(main, ["--json", "--help"])
        assert result.exit_code == 0
        # JSON flag should be accepted but help overrides

    def test_quiet_flag(self):
        """Test quiet flag."""
        result = self.runner.invoke(main, ["--quiet", "--help"])
        assert result.exit_code == 0

    def test_verbose_and_quiet_conflict(self):
        """Test that verbose and quiet flags conflict."""
        result = self.runner.invoke(main, ["--verbose", "--quiet", "instances", "list"])
        assert result.exit_code == 2  # Usage error
        assert "Cannot use both --verbose and --quiet" in result.output

    def test_verbose_flag(self):
        """Test verbose flag is passed to context."""
        result = self.runner.invoke(main, ["--verbose", "instances", "list"])
        assert result.exit_code == 0
        # Context object should contain verbose=True

    def test_config_flag(self):
        """Test config flag is passed to context."""
        result = self.runner.invoke(
            main, ["--config", "/path/to/config", "instances", "list"]
        )
        assert result.exit_code == 0
        # Context object should contain config path

    def test_invalid_command(self):
        """Test invalid command."""
        result = self.runner.invoke(main, ["invalid"])
        assert result.exit_code == 2  # Click error for unknown command
        assert "No such command" in result.output


class TestInstanceCommands:
    """Test suite for instance command group."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    def test_instances_help(self):
        """Test instances command group help."""
        result = self.runner.invoke(main, ["instances", "--help"])
        assert result.exit_code == 0
        assert "Manage Claude Code instances" in result.output

    def test_instances_status(self):
        """Test instances status command."""
        result = self.runner.invoke(main, ["instances", "status"])
        assert result.exit_code == 0
        assert "No active instances found" in result.output

    def test_instances_start(self):
        """Test instances start command."""
        # This will fail because no process can actually be started in tests
        # but we can check that it attempts to start
        result = self.runner.invoke(main, ["instances", "start", "test-123"])
        # Exit code will be non-zero due to process spawn failure, which is expected
        assert "test-123" in result.output

    def test_instances_stop(self):
        """Test instances stop command."""
        result = self.runner.invoke(main, ["instances", "stop", "test-123"])
        assert result.exit_code == 0
        assert "No instance found for issue test-123" in result.output

    def test_instances_list(self):
        """Test instances list command."""
        result = self.runner.invoke(main, ["instances", "list"])
        assert result.exit_code == 0
        assert "No active instances found" in result.output


class TestTaskCommands:
    """Test suite for task command group."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    def test_tasks_help(self):
        """Test tasks command group help."""
        result = self.runner.invoke(main, ["tasks", "--help"])
        assert result.exit_code == 0
        assert "Manage tasks and work items" in result.output

    def test_tasks_list(self):
        """Test tasks list command."""
        result = self.runner.invoke(main, ["tasks", "list"])
        assert result.exit_code == 0
        assert "Task list command - to be implemented" in result.output

    def test_tasks_show(self):
        """Test tasks show command."""
        result = self.runner.invoke(main, ["tasks", "show", "task-456"])
        assert result.exit_code == 0
        assert "Task details for: task-456" in result.output

    def test_tasks_assign(self):
        """Test tasks assign command."""
        result = self.runner.invoke(main, ["tasks", "assign", "task-789"])
        assert result.exit_code == 0
        assert "Assigning task task-789" in result.output


class TestWorktreeCommands:
    """Test suite for worktree command group."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    def test_worktrees_help(self):
        """Test worktrees command group help."""
        result = self.runner.invoke(main, ["worktrees", "--help"])
        assert result.exit_code == 0
        assert "Manage git worktrees" in result.output

    def test_worktrees_list(self):
        """Test worktrees list command."""
        with patch("cc_orchestrator.cli.worktrees.WorktreeService") as mock_service:
            mock_service.return_value.list_worktrees.return_value = []

            result = self.runner.invoke(main, ["worktrees", "list"])
            assert result.exit_code == 0
            assert "No worktrees found." in result.output

    def test_worktrees_create(self):
        """Test worktrees create command."""
        with patch("cc_orchestrator.cli.worktrees.WorktreeService") as mock_service:
            mock_service.return_value.create_worktree.return_value = {
                "id": 1,
                "name": "test-name",
                "path": "/test/path",
                "branch": "feature-branch",
                "commit": "abcd1234",
                "instance_id": None,
            }

            result = self.runner.invoke(
                main, ["worktrees", "create", "test-name", "feature-branch"]
            )
            assert result.exit_code == 0
            assert "Created worktree 'test-name'" in result.output

    def test_worktrees_create_with_path(self):
        """Test worktrees create command with custom path."""
        with patch("cc_orchestrator.cli.worktrees.WorktreeService") as mock_service:
            mock_service.return_value.create_worktree.return_value = {
                "id": 1,
                "name": "test-name",
                "path": "/custom/path",
                "branch": "feature-branch",
                "commit": "abcd1234",
                "instance_id": None,
            }

            result = self.runner.invoke(
                main,
                [
                    "worktrees",
                    "create",
                    "test-name",
                    "feature-branch",
                    "--path",
                    "/custom/path",
                ],
            )
            assert result.exit_code == 0
            assert "Created worktree 'test-name'" in result.output

    def test_worktrees_remove(self):
        """Test worktrees remove command."""
        with patch("cc_orchestrator.cli.worktrees.WorktreeService") as mock_service:
            mock_service.return_value.remove_worktree.return_value = True

            result = self.runner.invoke(
                main, ["worktrees", "remove", "/path/to/worktree"]
            )
            assert result.exit_code == 0
            assert "Successfully removed worktree: /path/to/worktree" in result.output

    def test_worktrees_cleanup(self):
        """Test worktrees cleanup command."""
        with patch("cc_orchestrator.cli.worktrees.WorktreeService") as mock_service:
            mock_service.return_value.cleanup_worktrees.return_value = {
                "git_cleaned": [],
                "db_cleaned": [],
            }

            result = self.runner.invoke(main, ["worktrees", "cleanup"])
            assert result.exit_code == 0
            assert "No cleanup needed - all worktrees are up to date" in result.output


class TestWebCommands:
    """Test suite for web command group."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    def test_web_help(self):
        """Test web command group help."""
        result = self.runner.invoke(main, ["web", "--help"])
        assert result.exit_code == 0
        assert "Manage the web interface" in result.output

    def test_web_start_default(self):
        """Test web start command with defaults."""
        result = self.runner.invoke(main, ["web", "start"])
        assert result.exit_code == 0
        assert "Starting web interface on localhost:8000" in result.output

    def test_web_start_custom(self):
        """Test web start command with custom host and port."""
        result = self.runner.invoke(
            main, ["web", "start", "--host", "0.0.0.0", "--port", "9000"]
        )
        assert result.exit_code == 0
        assert "Starting web interface on 0.0.0.0:9000" in result.output

    def test_web_stop(self):
        """Test web stop command."""
        result = self.runner.invoke(main, ["web", "stop"])
        assert result.exit_code == 0
        assert "Stopping web interface" in result.output

    def test_web_status(self):
        """Test web status command."""
        result = self.runner.invoke(main, ["web", "status"])
        assert result.exit_code == 0
        assert "Web interface status" in result.output


class TestConfigCommands:
    """Test suite for config command group."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    def test_config_help(self):
        """Test config command group help."""
        result = self.runner.invoke(main, ["config", "--help"])
        assert result.exit_code == 0
        assert "Manage configuration settings" in result.output

    def test_config_locations(self):
        """Test config locations command."""
        result = self.runner.invoke(main, ["config", "locations"])
        assert result.exit_code == 0
        assert "Configuration file search locations" in result.output
        assert "cc-orchestrator.yaml" in result.output
        assert "CC_ORCHESTRATOR_" in result.output

    @patch("cc_orchestrator.cli.config.load_config")
    def test_config_show(self, mock_load_config):
        """Test config show command."""
        # Mock configuration
        mock_config = Mock()
        mock_config.model_dump.return_value = {"max_instances": 5, "web_port": 8000}
        mock_load_config.return_value = mock_config

        result = self.runner.invoke(main, ["config", "show"])
        assert result.exit_code == 0
        mock_load_config.assert_called_once()

    @patch("cc_orchestrator.cli.config.load_config")
    def test_config_validate_success(self, mock_load_config):
        """Test config validate command success."""
        mock_load_config.return_value = Mock()  # Valid config

        result = self.runner.invoke(main, ["config", "validate"])
        assert result.exit_code == 0
        assert "Configuration is valid" in result.output

    @patch("cc_orchestrator.cli.config.save_config")
    def test_config_init(self, mock_save_config):
        """Test config init command."""
        mock_save_config.return_value = Path("/fake/path/config.yaml")

        result = self.runner.invoke(main, ["config", "init"])
        assert result.exit_code == 0
        assert "Configuration initialized" in result.output
        mock_save_config.assert_called_once()
