"""Unit tests for CLI utilities."""

import json
from unittest.mock import Mock, patch

import click
from click.testing import CliRunner

from cc_orchestrator.cli.utils import (
    CliError,
    error_handler,
    format_output,
    handle_error,
    output_json,
    output_table,
    quiet_echo,
    success_message,
    verbose_echo,
)


class TestCliError:
    """Test suite for CliError exception."""

    def test_cli_error_default_exit_code(self):
        """Test CliError with default exit code."""
        error = CliError("Test error message")
        assert str(error) == "Test error message"
        assert error.message == "Test error message"
        assert error.exit_code == 1

    def test_cli_error_custom_exit_code(self):
        """Test CliError with custom exit code."""
        error = CliError("Custom error", exit_code=2)
        assert str(error) == "Custom error"
        assert error.message == "Custom error"
        assert error.exit_code == 2


class TestErrorHandler:
    """Test suite for error_handler decorator."""

    def test_error_handler_success(self):
        """Test error_handler decorator with successful function execution."""

        @error_handler
        def successful_function(value):
            return value * 2

        result = successful_function(5)
        assert result == 10

    def test_error_handler_cli_error(self):
        """Test error_handler decorator with CliError."""

        @error_handler
        def failing_function():
            raise CliError("Test CLI error", exit_code=2)

        with patch("click.echo") as mock_echo, patch("sys.exit") as mock_exit:

            failing_function()

            # Verify error message was echoed
            mock_echo.assert_called_once()
            args, kwargs = mock_echo.call_args
            assert "Error: Test CLI error" in str(args[0])
            assert kwargs.get("err") is True

            # Verify exit was called with correct code
            mock_exit.assert_called_once_with(2)

    def test_error_handler_generic_exception(self):
        """Test error_handler decorator with generic Exception - covers lines 37-39."""

        @error_handler
        def failing_function():
            raise ValueError("Generic error")

        with patch("click.echo") as mock_echo, patch("sys.exit") as mock_exit:

            failing_function()

            # Verify error message was echoed
            mock_echo.assert_called_once()
            args, kwargs = mock_echo.call_args
            assert "Unexpected error: Generic error" in str(args[0])
            assert kwargs.get("err") is True

            # Verify exit was called with code 1
            mock_exit.assert_called_once_with(1)


class TestOutputFunctions:
    """Test suite for output formatting functions."""

    def test_success_message(self):
        """Test success_message function."""
        with patch("click.echo") as mock_echo:
            success_message("Operation completed")

            mock_echo.assert_called_once()
            args = mock_echo.call_args[0]
            # Verify green formatting and checkmark
            assert "✓ Operation completed" in str(args[0])

    def test_output_json(self):
        """Test output_json function."""
        test_data = {"key": "value", "number": 42}

        with patch("click.echo") as mock_echo:
            output_json(test_data)

            mock_echo.assert_called_once()
            args = mock_echo.call_args[0]
            output = args[0]

            # Verify JSON formatting
            parsed = json.loads(output)
            assert parsed == test_data

    def test_output_table_empty_rows(self):
        """Test output_table function with empty rows."""
        headers = ["Column 1", "Column 2"]
        rows: list[list[str]] = []

        with patch("click.echo") as mock_echo:
            output_table(headers, rows)

            mock_echo.assert_called_once_with("No data to display")

    def test_output_table_with_data(self):
        """Test output_table function with data - covers lines 56-79."""
        headers = ["Name", "Age", "City"]
        rows = [
            ["Alice", "25", "New York"],
            ["Bob", "30", "San Francisco"],
            ["Charlie", "35", "Chicago"],
        ]

        with patch("click.echo") as mock_echo:
            output_table(headers, rows)

            # Should be called multiple times: header, separator, rows
            assert mock_echo.call_count >= 5  # header + separator + 3 rows

            calls = [call[0][0] for call in mock_echo.call_args_list]

            # Check header formatting
            header_line = calls[0]
            assert "Name" in header_line
            assert "Age" in header_line
            assert "City" in header_line
            assert " | " in header_line

            # Check separator line
            separator_line = calls[1]
            assert all(c in "-|" or c.isspace() for c in separator_line)

            # Check data rows
            data_lines = calls[2:]
            assert len(data_lines) == 3
            assert "Alice" in data_lines[0]
            assert "Bob" in data_lines[1]
            assert "Charlie" in data_lines[2]

    def test_output_table_with_varying_lengths(self):
        """Test output_table with varying column lengths."""
        headers = ["Short", "Very Long Header"]
        rows = [["A", "Short"], ["Very Long Value", "B"]]

        with patch("click.echo") as mock_echo:
            output_table(headers, rows)

            calls = [call[0][0] for call in mock_echo.call_args_list]
            header_line = calls[0]

            # Verify proper spacing/alignment
            assert " | " in header_line
            assert len(header_line) > len("Short | Very Long Header")

    def test_handle_error(self):
        """Test handle_error function."""
        with patch("click.echo") as mock_echo, patch("sys.exit") as mock_exit:

            handle_error("Test error message", exit_code=3)

            # Verify error message was echoed
            mock_echo.assert_called_once()
            args, kwargs = mock_echo.call_args
            assert "Error: Test error message" in str(args[0])
            assert kwargs.get("err") is True

            # Verify exit was called with correct code
            mock_exit.assert_called_once_with(3)

    def test_handle_error_default_exit_code(self):
        """Test handle_error function with default exit code."""
        with patch("click.echo") as mock_echo, patch("sys.exit") as mock_exit:

            handle_error("Test error")

            mock_echo.assert_called_once()
            mock_exit.assert_called_once_with(1)


class TestContextUtilities:
    """Test suite for context-based utility functions."""

    def test_verbose_echo_enabled(self):
        """Test verbose_echo when verbose mode is enabled - covers lines 90-91."""
        # Create a context with verbose enabled
        ctx = Mock(spec=click.Context)
        ctx.obj = {"verbose": True}

        with patch("click.echo") as mock_echo:
            verbose_echo(ctx, "Debug message")

            mock_echo.assert_called_once()
            args, kwargs = mock_echo.call_args
            assert "[VERBOSE] Debug message" in str(args[0])
            assert kwargs.get("err") is True

    def test_verbose_echo_disabled(self):
        """Test verbose_echo when verbose mode is disabled."""
        # Create a context with verbose disabled
        ctx = Mock(spec=click.Context)
        ctx.obj = {"verbose": False}

        with patch("click.echo") as mock_echo:
            verbose_echo(ctx, "Debug message")

            mock_echo.assert_not_called()

    def test_verbose_echo_no_obj(self):
        """Test verbose_echo when ctx.obj is None."""
        ctx = Mock(spec=click.Context)
        ctx.obj = None

        with patch("click.echo") as mock_echo:
            verbose_echo(ctx, "Debug message")

            mock_echo.assert_not_called()

    def test_quiet_echo_not_quiet(self):
        """Test quiet_echo when not in quiet mode - covers lines 96-97."""
        # Create a context with quiet disabled
        ctx = Mock(spec=click.Context)
        ctx.obj = {"quiet": False}

        with patch("click.echo") as mock_echo:
            quiet_echo(ctx, "Normal message")

            mock_echo.assert_called_once_with("Normal message")

    def test_quiet_echo_enabled(self):
        """Test quiet_echo when quiet mode is enabled."""
        # Create a context with quiet enabled
        ctx = Mock(spec=click.Context)
        ctx.obj = {"quiet": True}

        with patch("click.echo") as mock_echo:
            quiet_echo(ctx, "Normal message")

            mock_echo.assert_not_called()

    def test_quiet_echo_no_obj(self):
        """Test quiet_echo when ctx.obj is None."""
        ctx = Mock(spec=click.Context)
        ctx.obj = None

        with patch("click.echo") as mock_echo:
            quiet_echo(ctx, "Normal message")

            mock_echo.assert_called_once_with("Normal message")

    def test_format_output_json_mode(self):
        """Test format_output in JSON mode."""
        ctx = Mock(spec=click.Context)
        ctx.obj = {"json": True}
        data = {"test": "data"}

        with patch("cc_orchestrator.cli.utils.output_json") as mock_output_json:
            format_output(ctx, data)

            mock_output_json.assert_called_once_with(data)

    def test_format_output_with_human_format_func(self):
        """Test format_output with human format function - covers line 107."""
        ctx = Mock(spec=click.Context)
        ctx.obj = {"json": False}
        data = {"test": "data"}

        # Create a mock human format function
        mock_human_format = Mock()

        format_output(ctx, data, human_format_func=mock_human_format)

        mock_human_format.assert_called_once_with(data)

    def test_format_output_default_human_format(self):
        """Test format_output with default human formatting."""
        ctx = Mock(spec=click.Context)
        ctx.obj = {"json": False}
        data = {"key1": "value1", "key2": "value2"}

        with patch("click.echo") as mock_echo:
            format_output(ctx, data)

            # Should echo each key-value pair
            assert mock_echo.call_count == 2
            calls = [call[0][0] for call in mock_echo.call_args_list]
            assert "key1: value1" in calls
            assert "key2: value2" in calls

    def test_format_output_no_obj(self):
        """Test format_output when ctx.obj is None."""
        ctx = Mock(spec=click.Context)
        ctx.obj = None
        data = {"test": "data"}

        with patch("click.echo") as mock_echo:
            format_output(ctx, data)

            # Should use default human format
            mock_echo.assert_called_once_with("test: data")


class TestIntegrationWithClick:
    """Integration tests with actual Click commands."""

    def test_error_handler_with_click_command(self):
        """Test error_handler decorator integration with Click command."""

        @click.command()
        @error_handler
        def test_command():
            raise CliError("Command failed", exit_code=2)

        runner = CliRunner()
        result = runner.invoke(test_command)

        assert result.exit_code == 2
        assert "Error: Command failed" in result.output

    def test_context_utilities_with_click_context(self):
        """Test context utilities with actual Click context."""

        @click.command()
        @click.pass_context
        def test_command(ctx):
            ctx.obj = {"verbose": True, "quiet": False}
            verbose_echo(ctx, "Verbose message")
            quiet_echo(ctx, "Normal message")

        runner = CliRunner()
        result = runner.invoke(test_command)

        assert result.exit_code == 0
        assert "[VERBOSE] Verbose message" in result.stderr
        assert "Normal message" in result.output
