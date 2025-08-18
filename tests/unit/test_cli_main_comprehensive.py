"""Comprehensive tests for CLI main module."""

import warnings

import click
import pytest
from click.testing import CliRunner

from cc_orchestrator.cli.main import main


class TestMainCommand:
    """Test the main CLI command."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    def test_main_command_help(self):
        """Test main command shows help information."""
        result = self.runner.invoke(main, ["--help"])

        assert result.exit_code == 0
        assert "Claude Code Orchestrator" in result.output
        assert "Manage multiple Claude instances through git" in result.output
        assert "worktrees" in result.output
        assert "--config" in result.output
        assert "--verbose" in result.output
        assert "--quiet" in result.output
        assert "--json" in result.output

    def test_main_command_version(self):
        """Test main command shows version information."""
        result = self.runner.invoke(main, ["--version"])

        assert result.exit_code == 0
        assert "cc-orchestrator, version 0.1.0" in result.output

    def test_main_command_with_verbose_and_quiet_fails(self):
        """Test main command fails with both verbose and quiet flags."""
        result = self.runner.invoke(main, ["--verbose", "--quiet", "config", "--help"])

        assert result.exit_code != 0
        assert "Cannot use both --verbose and --quiet options" in result.output


class TestMainCommandContext:
    """Test main command context setup using actual callback function."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    def test_main_callback_function_basic_setup(self):
        """Test main callback function sets up context properly."""
        # Use standalone mode false to get context object
        from cc_orchestrator.cli.main import main as main_func

        with main_func.make_context(
            "main",
            [
                "--config",
                "test-config.yaml",
                "--profile",
                "dev",
                "--verbose",
                "--json",
                "--max-instances",
                "10",
                "--web-port",
                "8080",
                "--web-host",
                "localhost",
                "--log-level",
                "DEBUG",
                "--worktree-base-path",
                "/tmp/worktrees",
                "--cpu-threshold",
                "80.5",
                "--memory-limit",
                "4096",
            ],
        ) as ctx:
            # Manually invoke the callback function to set up context
            with ctx:
                main_func.callback(
                    config="test-config.yaml",
                    profile="dev",
                    verbose=True,
                    quiet=False,
                    json=True,
                    max_instances=10,
                    web_port=8080,
                    web_host="localhost",
                    log_level="DEBUG",
                    worktree_base_path="/tmp/worktrees",
                    cpu_threshold=80.5,
                    memory_limit=4096,
                )

            # Verify context is set up correctly
            assert ctx.obj["config"] == "test-config.yaml"
            assert ctx.obj["profile"] == "dev"
            assert ctx.obj["verbose"] is True
            assert ctx.obj["quiet"] is False
            assert ctx.obj["json"] is True

            overrides = ctx.obj["cli_overrides"]
            assert overrides["max_instances"] == 10
            assert overrides["web_port"] == 8080
            assert overrides["web_host"] == "localhost"
            assert overrides["log_level"] == "DEBUG"
            assert overrides["worktree_base_path"] == "/tmp/worktrees"
            assert overrides["cpu_threshold"] == 80.5
            assert overrides["memory_limit"] == 4096

    def test_main_callback_removes_none_values(self):
        """Test main callback removes None values from CLI overrides."""
        from cc_orchestrator.cli.main import main as main_func

        with main_func.make_context("main", ["config"]) as ctx:
            # Manually invoke the callback function with all None values
            with ctx:
                main_func.callback(
                    config=None,
                    profile=None,
                    verbose=False,
                    quiet=False,
                    json=False,
                    max_instances=None,
                    web_port=None,
                    web_host=None,
                    log_level=None,
                    worktree_base_path=None,
                    cpu_threshold=None,
                    memory_limit=None,
                )

            overrides = ctx.obj["cli_overrides"]
            assert len(overrides) == 0

    def test_main_callback_partial_overrides(self):
        """Test main callback with partial CLI overrides."""
        from cc_orchestrator.cli.main import main as main_func

        with main_func.make_context(
            "main",
            [
                "--config",
                "config.yaml",
                "--profile",
                "prod",
                "--quiet",
                "--max-instances",
                "5",
                "--web-port",
                "9000",
            ],
        ) as ctx:
            # Manually invoke the callback function with partial overrides
            with ctx:
                main_func.callback(
                    config="config.yaml",
                    profile="prod",
                    verbose=False,
                    quiet=True,
                    json=False,
                    max_instances=5,
                    web_port=9000,
                    web_host=None,
                    log_level=None,
                    worktree_base_path=None,
                    cpu_threshold=None,
                    memory_limit=None,
                )

            assert ctx.obj["config"] == "config.yaml"
            assert ctx.obj["profile"] == "prod"
            assert ctx.obj["quiet"] is True

            overrides = ctx.obj["cli_overrides"]
            assert overrides["max_instances"] == 5
            assert overrides["web_port"] == 9000
            assert "web_host" not in overrides
            assert "log_level" not in overrides
            assert len(overrides) == 2

    def test_main_callback_verbose_quiet_validation(self):
        """Test main callback validates verbose and quiet conflict."""
        from cc_orchestrator.cli.main import main as main_func

        with pytest.raises(click.UsageError) as exc_info:
            with main_func.make_context("main", ["--verbose", "--quiet"]) as ctx:
                # Manually invoke the callback to trigger validation
                with ctx:
                    main_func.callback(
                        config=None,
                        profile=None,
                        verbose=True,
                        quiet=True,
                        json=False,
                        max_instances=None,
                        web_port=None,
                        web_host=None,
                        log_level=None,
                        worktree_base_path=None,
                        cpu_threshold=None,
                        memory_limit=None,
                    )

        assert "Cannot use both --verbose and --quiet options" in str(exc_info.value)


class TestMainCommandGroups:
    """Test main command groups are properly registered."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    def test_command_groups_listed_in_help(self):
        """Test command groups are listed in main help."""
        result = self.runner.invoke(main, ["--help"])

        assert result.exit_code == 0
        # Check that all command groups appear in help
        commands_section = result.output
        assert "instances" in commands_section
        assert "tasks" in commands_section
        assert "worktrees" in commands_section
        assert "config" in commands_section
        assert "web" in commands_section
        assert "tmux" in commands_section


class TestMainCommandValidation:
    """Test main command validation and error handling."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    def test_invalid_integer_option_fails(self):
        """Test invalid integer option fails gracefully."""
        result = self.runner.invoke(main, ["--max-instances", "not-a-number"])

        assert result.exit_code != 0
        assert "Invalid value" in result.output

    def test_invalid_float_option_fails(self):
        """Test invalid float option fails gracefully."""
        result = self.runner.invoke(main, ["--cpu-threshold", "not-a-float"])

        assert result.exit_code != 0
        assert "Invalid value" in result.output


class TestMainCommandWarningsFilter:
    """Test warnings filter setup."""

    def test_warnings_module_imported(self):
        """Test warnings module is imported correctly."""
        # Just verify the module can import warnings correctly
        assert warnings is not None

    def test_warnings_filter_can_be_applied(self):
        """Test warnings filter functionality works."""
        # Test that the warning filter mechanism works
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            warnings.filterwarnings("ignore", message=".*test.*")
            warnings.warn("test warning should be ignored", UserWarning, stacklevel=2)
            # Should be filtered out
            assert len(w) == 0


class TestMainCommandDocumentation:
    """Test main command documentation and help text."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    def test_main_docstring_in_help(self):
        """Test main command docstring appears in help."""
        result = self.runner.invoke(main, ["--help"])

        assert result.exit_code == 0
        # Key parts of the docstring should appear
        assert "Claude Code Orchestrator" in result.output
        assert "git worktrees" in result.output

    def test_option_help_text(self):
        """Test option help text is descriptive."""
        result = self.runner.invoke(main, ["--help"])

        assert result.exit_code == 0
        # Check that options have helpful descriptions
        assert "Configuration file path" in result.output
        assert "Configuration profile to use" in result.output
        assert "Enable verbose output" in result.output
        assert "Suppress non-essential output" in result.output
        assert "Output in JSON format" in result.output
        assert "Override max_instances setting" in result.output
        assert "Override web_port setting" in result.output

    def test_program_name_in_version(self):
        """Test program name is correctly set in version."""
        result = self.runner.invoke(main, ["--version"])

        assert result.exit_code == 0
        assert "cc-orchestrator" in result.output
        assert "version 0.1.0" in result.output


class TestMainCommandIntegration:
    """Test main command integration scenarios."""

    def test_main_module_can_be_executed(self):
        """Test main module can be imported and executed."""
        # Test that the main module can be imported without errors
        from cc_orchestrator.cli import main as main_module

        assert main_module is not None
        assert hasattr(main_module, "main")

    def test_command_structure_is_valid(self):
        """Test command structure is properly set up."""
        assert main.commands is not None
        assert len(main.commands) > 0

        # Verify expected commands are registered
        command_names = list(main.commands.keys())
        expected_commands = ["instances", "tasks", "worktrees", "config", "web", "tmux"]
        for cmd in expected_commands:
            assert cmd in command_names
