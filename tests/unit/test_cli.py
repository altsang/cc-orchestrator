"""Unit tests for CLI commands."""

from unittest.mock import patch

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

    def test_status_command(self):
        """Test status command."""
        result = self.runner.invoke(main, ["status"])
        assert result.exit_code == 0
        assert "Status command - to be implemented" in result.output

    def test_start_command(self):
        """Test start command with issue ID."""
        result = self.runner.invoke(main, ["start", "test-123"])
        assert result.exit_code == 0
        assert "Starting instance for issue: test-123" in result.output

    def test_start_command_missing_argument(self):
        """Test start command without issue ID."""
        result = self.runner.invoke(main, ["start"])
        assert result.exit_code == 2  # Click error for missing argument
        assert "Missing argument" in result.output

    def test_stop_command(self):
        """Test stop command with issue ID."""
        result = self.runner.invoke(main, ["stop", "test-123"])
        assert result.exit_code == 0
        assert "Stopping instance for issue: test-123" in result.output

    def test_stop_command_missing_argument(self):
        """Test stop command without issue ID."""
        result = self.runner.invoke(main, ["stop"])
        assert result.exit_code == 2  # Click error for missing argument
        assert "Missing argument" in result.output

    def test_list_command(self):
        """Test list command."""
        result = self.runner.invoke(main, ["list"])
        assert result.exit_code == 0
        assert "List command - to be implemented" in result.output

    def test_web_command(self):
        """Test web command."""
        result = self.runner.invoke(main, ["web"])
        assert result.exit_code == 0
        assert "Starting web interface - to be implemented" in result.output

    def test_verbose_flag(self):
        """Test verbose flag is passed to context."""
        with patch("cc_orchestrator.cli.main.click.echo"):
            result = self.runner.invoke(main, ["--verbose", "status"])
            assert result.exit_code == 0
            # Context object should contain verbose=True

    def test_config_flag(self):
        """Test config flag is passed to context."""
        with patch("cc_orchestrator.cli.main.click.echo"):
            result = self.runner.invoke(main, ["--config", "/path/to/config", "status"])
            assert result.exit_code == 0
            # Context object should contain config path

    def test_invalid_command(self):
        """Test invalid command."""
        result = self.runner.invoke(main, ["invalid"])
        assert result.exit_code == 2  # Click error for unknown command
        assert "No such command" in result.output
