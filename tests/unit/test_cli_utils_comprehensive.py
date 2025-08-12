"""Comprehensive tests for CLI utils module."""

import json
from unittest.mock import Mock, patch

import click
import pytest
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
    """Test CliError exception class."""

    def test_cli_error_with_default_exit_code(self):
        """Test CliError with default exit code."""
        error = CliError("Test error message")

        assert str(error) == "Test error message"
        assert error.message == "Test error message"
        assert error.exit_code == 1

    def test_cli_error_with_custom_exit_code(self):
        """Test CliError with custom exit code."""
        error = CliError("Custom error", exit_code=2)

        assert str(error) == "Custom error"
        assert error.message == "Custom error"
        assert error.exit_code == 2

    def test_cli_error_inheritance(self):
        """Test CliError inherits from Exception."""
        error = CliError("Test")
        assert isinstance(error, Exception)

    def test_cli_error_with_empty_message(self):
        """Test CliError with empty message."""
        error = CliError("", exit_code=5)

        assert error.message == ""
        assert error.exit_code == 5


class TestErrorHandler:
    """Test error_handler decorator."""

    def test_error_handler_successful_execution(self):
        """Test error handler with successful function execution."""

        @error_handler
        def successful_function(value):
            return value * 2

        result = successful_function(5)
        assert result == 10

    def test_error_handler_with_cli_error(self):
        """Test error handler with CliError exception."""

        @error_handler
        def function_with_cli_error():
            raise CliError("Test CLI error", exit_code=2)

        with patch("click.echo") as mock_echo, patch("sys.exit") as mock_exit:

            function_with_cli_error()

            mock_echo.assert_called_once()
            args = mock_echo.call_args[0]
            assert "Error: Test CLI error" in args[0]
            mock_exit.assert_called_once_with(2)

    def test_error_handler_with_generic_exception(self):
        """Test error handler with generic exception."""

        @error_handler
        def function_with_exception():
            raise ValueError("Test generic error")

        with patch("click.echo") as mock_echo, patch("sys.exit") as mock_exit:

            function_with_exception()

            mock_echo.assert_called_once()
            args = mock_echo.call_args[0]
            assert "Unexpected error: Test generic error" in args[0]
            mock_exit.assert_called_once_with(1)

    def test_error_handler_preserves_function_metadata(self):
        """Test error handler preserves function metadata."""

        @error_handler
        def original_function():
            """Original docstring."""
            return "original"

        assert original_function.__name__ == "original_function"
        assert original_function.__doc__ == "Original docstring."

    def test_error_handler_with_args_and_kwargs(self):
        """Test error handler with function arguments."""

        @error_handler
        def function_with_args(a, b, c=None):
            return f"{a}-{b}-{c}"

        result = function_with_args("x", "y", c="z")
        assert result == "x-y-z"


class TestSuccessMessage:
    """Test success_message function."""

    def test_success_message_output(self):
        """Test success message displays correctly."""
        runner = CliRunner()

        with runner.isolated_filesystem():
            # Capture click output
            with patch("click.echo") as mock_echo:
                success_message("Operation completed")

                mock_echo.assert_called_once()
                args = mock_echo.call_args[0]
                assert "✓ Operation completed" in args[0]

    def test_success_message_with_empty_string(self):
        """Test success message with empty string."""
        with patch("click.echo") as mock_echo:
            success_message("")

            mock_echo.assert_called_once()
            args = mock_echo.call_args[0]
            assert "✓ " in args[0]

    def test_success_message_with_special_characters(self):
        """Test success message with special characters."""
        with patch("click.echo") as mock_echo:
            success_message("File 'test.txt' created successfully!")

            mock_echo.assert_called_once()
            args = mock_echo.call_args[0]
            assert "✓ File 'test.txt' created successfully!" in args[0]


class TestOutputJson:
    """Test output_json function."""

    def test_output_json_simple_dict(self):
        """Test JSON output with simple dictionary."""
        data = {"name": "test", "value": 42}

        with patch("click.echo") as mock_echo:
            output_json(data)

            mock_echo.assert_called_once()
            output = mock_echo.call_args[0][0]
            parsed = json.loads(output)
            assert parsed == data

    def test_output_json_nested_dict(self):
        """Test JSON output with nested dictionary."""
        data = {
            "config": {
                "database": {"host": "localhost", "port": 5432},
                "api": {"timeout": 30},
            },
            "status": "active",
        }

        with patch("click.echo") as mock_echo:
            output_json(data)

            mock_echo.assert_called_once()
            output = mock_echo.call_args[0][0]
            parsed = json.loads(output)
            assert parsed == data

    def test_output_json_with_arrays(self):
        """Test JSON output with arrays."""
        data = {"items": ["item1", "item2", "item3"], "count": 3}

        with patch("click.echo") as mock_echo:
            output_json(data)

            mock_echo.assert_called_once()
            output = mock_echo.call_args[0][0]
            parsed = json.loads(output)
            assert parsed == data

    def test_output_json_empty_dict(self):
        """Test JSON output with empty dictionary."""
        data = {}

        with patch("click.echo") as mock_echo:
            output_json(data)

            mock_echo.assert_called_once()
            output = mock_echo.call_args[0][0]
            parsed = json.loads(output)
            assert parsed == {}

    def test_output_json_formatting(self):
        """Test JSON output is properly formatted with indentation."""
        data = {"key": "value"}

        with patch("click.echo") as mock_echo:
            output_json(data)

            mock_echo.assert_called_once()
            output = mock_echo.call_args[0][0]
            # Should have indentation (indent=2)
            assert "{\n  " in output


class TestOutputTable:
    """Test output_table function."""

    def test_output_table_simple(self):
        """Test table output with simple data."""
        headers = ["Name", "Age"]
        rows = [["Alice", "25"], ["Bob", "30"]]

        with patch("click.echo") as mock_echo:
            output_table(headers, rows)

            # Should call echo multiple times (header, separator, rows)
            assert mock_echo.call_count >= 4

            # Check header formatting
            calls = mock_echo.call_args_list
            header_call = calls[0][0][0]
            assert "Name" in header_call
            assert "Age" in header_call
            assert "|" in header_call

    def test_output_table_empty_rows(self):
        """Test table output with empty rows."""
        headers = ["Name", "Age"]
        rows = []

        with patch("click.echo") as mock_echo:
            output_table(headers, rows)

            mock_echo.assert_called_once_with("No data to display")

    def test_output_table_variable_column_widths(self):
        """Test table output adjusts column widths correctly."""
        headers = ["Name", "Description"]
        rows = [
            ["Alice", "Short desc"],
            ["Bob", "Very long description that should expand the column"],
            ["Charlie", "Medium length"],
        ]

        with patch("click.echo") as mock_echo:
            output_table(headers, rows)

            calls = mock_echo.call_args_list
            # Header should be padded to accommodate longest content
            header_call = calls[0][0][0]
            separator_call = calls[1][0][0]

            # Separator length should match header length
            assert len(separator_call) == len(header_call)

    def test_output_table_with_numbers(self):
        """Test table output converts numbers to strings."""
        headers = ["ID", "Score"]
        rows = [[1, 95.5], [2, 87], [3, 92.1]]

        with patch("click.echo") as mock_echo:
            output_table(headers, rows)

            # Should not raise any errors with number conversion
            assert mock_echo.call_count >= 5  # header + separator + 3 rows

    def test_output_table_single_column(self):
        """Test table output with single column."""
        headers = ["Status"]
        rows = [["Active"], ["Inactive"], ["Pending"]]

        with patch("click.echo") as mock_echo:
            output_table(headers, rows)

            calls = mock_echo.call_args_list
            # Should still format properly
            assert len(calls) >= 5

    def test_output_table_empty_cells(self):
        """Test table output handles empty cells."""
        headers = ["Name", "Optional"]
        rows = [["Alice", ""], ["Bob", "Value"], ["Charlie", ""]]

        with patch("click.echo") as mock_echo:
            output_table(headers, rows)

            # Should handle empty strings without errors
            assert mock_echo.call_count >= 5


class TestHandleError:
    """Test handle_error function."""

    def test_handle_error_with_default_exit_code(self):
        """Test handle_error with default exit code."""
        with patch("click.echo") as mock_echo, patch("sys.exit") as mock_exit:

            handle_error("Test error message")

            mock_echo.assert_called_once()
            args, kwargs = mock_echo.call_args
            assert "Error: Test error message" in args[0]
            assert kwargs.get("err") is True
            mock_exit.assert_called_once_with(1)

    def test_handle_error_with_custom_exit_code(self):
        """Test handle_error with custom exit code."""
        with patch("click.echo") as mock_echo, patch("sys.exit") as mock_exit:

            handle_error("Custom error", exit_code=5)

            mock_echo.assert_called_once()
            mock_exit.assert_called_once_with(5)

    def test_handle_error_message_formatting(self):
        """Test handle_error formats message correctly."""
        with patch("click.echo") as mock_echo, patch("sys.exit"):

            handle_error("File not found")

            args = mock_echo.call_args[0]
            assert "Error: File not found" in args[0]


class TestVerboseEcho:
    """Test verbose_echo function."""

    def test_verbose_echo_when_verbose_enabled(self):
        """Test verbose echo when verbose mode is enabled."""
        ctx = click.Context(click.Command("test"))
        ctx.obj = {"verbose": True}

        with patch("click.echo") as mock_echo:
            verbose_echo(ctx, "Verbose message")

            mock_echo.assert_called_once()
            args, kwargs = mock_echo.call_args
            assert "[VERBOSE] Verbose message" in args[0]
            assert kwargs.get("err") is True

    def test_verbose_echo_when_verbose_disabled(self):
        """Test verbose echo when verbose mode is disabled."""
        ctx = click.Context(click.Command("test"))
        ctx.obj = {"verbose": False}

        with patch("click.echo") as mock_echo:
            verbose_echo(ctx, "Verbose message")

            mock_echo.assert_not_called()

    def test_verbose_echo_with_no_context_obj(self):
        """Test verbose echo with no context object."""
        ctx = click.Context(click.Command("test"))
        ctx.obj = None

        with patch("click.echo") as mock_echo:
            verbose_echo(ctx, "Verbose message")

            mock_echo.assert_not_called()

    def test_verbose_echo_with_empty_context_obj(self):
        """Test verbose echo with empty context object."""
        ctx = click.Context(click.Command("test"))
        ctx.obj = {}

        with patch("click.echo") as mock_echo:
            verbose_echo(ctx, "Verbose message")

            mock_echo.assert_not_called()


class TestQuietEcho:
    """Test quiet_echo function."""

    def test_quiet_echo_when_not_quiet(self):
        """Test quiet echo when not in quiet mode."""
        ctx = click.Context(click.Command("test"))
        ctx.obj = {"quiet": False}

        with patch("click.echo") as mock_echo:
            quiet_echo(ctx, "Normal message")

            mock_echo.assert_called_once_with("Normal message")

    def test_quiet_echo_when_quiet_enabled(self):
        """Test quiet echo when quiet mode is enabled."""
        ctx = click.Context(click.Command("test"))
        ctx.obj = {"quiet": True}

        with patch("click.echo") as mock_echo:
            quiet_echo(ctx, "Quiet message")

            mock_echo.assert_not_called()

    def test_quiet_echo_with_no_context_obj(self):
        """Test quiet echo with no context object."""
        ctx = click.Context(click.Command("test"))
        ctx.obj = None

        with patch("click.echo") as mock_echo:
            quiet_echo(ctx, "Default message")

            mock_echo.assert_called_once_with("Default message")

    def test_quiet_echo_with_empty_context_obj(self):
        """Test quiet echo with empty context object."""
        ctx = click.Context(click.Command("test"))
        ctx.obj = {}

        with patch("click.echo") as mock_echo:
            quiet_echo(ctx, "Default message")

            mock_echo.assert_called_once_with("Default message")


class TestFormatOutput:
    """Test format_output function."""

    def test_format_output_json_mode(self):
        """Test format output in JSON mode."""
        ctx = click.Context(click.Command("test"))
        ctx.obj = {"json": True}
        data = {"status": "success", "count": 5}

        with patch("cc_orchestrator.cli.utils.output_json") as mock_json:
            format_output(ctx, data)

            mock_json.assert_called_once_with(data)

    def test_format_output_human_format_with_function(self):
        """Test format output with custom human format function."""
        ctx = click.Context(click.Command("test"))
        ctx.obj = {"json": False}
        data = {"name": "test", "status": "active"}

        human_format_func = Mock()

        format_output(ctx, data, human_format_func)

        human_format_func.assert_called_once_with(data)

    def test_format_output_default_human_format(self):
        """Test format output with default human format."""
        ctx = click.Context(click.Command("test"))
        ctx.obj = {"json": False}
        data = {"name": "test", "status": "active"}

        with patch("click.echo") as mock_echo:
            format_output(ctx, data)

            # Should call echo for each key-value pair
            assert mock_echo.call_count == 2
            calls = [call[0][0] for call in mock_echo.call_args_list]
            assert any("name: test" in call for call in calls)
            assert any("status: active" in call for call in calls)

    def test_format_output_no_context_obj(self):
        """Test format output with no context object."""
        ctx = click.Context(click.Command("test"))
        ctx.obj = None
        data = {"key": "value"}

        with patch("click.echo") as mock_echo:
            format_output(ctx, data)

            mock_echo.assert_called_once_with("key: value")

    def test_format_output_empty_data(self):
        """Test format output with empty data."""
        ctx = click.Context(click.Command("test"))
        ctx.obj = {"json": False}
        data = {}

        with patch("click.echo") as mock_echo:
            format_output(ctx, data)

            mock_echo.assert_not_called()

    def test_format_output_complex_values(self):
        """Test format output with complex values."""
        ctx = click.Context(click.Command("test"))
        ctx.obj = {}
        data = {
            "list": [1, 2, 3],
            "dict": {"nested": "value"},
            "number": 42,
            "boolean": True,
        }

        with patch("click.echo") as mock_echo:
            format_output(ctx, data)

            assert mock_echo.call_count == 4
            calls = [call[0][0] for call in mock_echo.call_args_list]
            assert any("list: [1, 2, 3]" in call for call in calls)
            assert any("dict: {'nested': 'value'}" in call for call in calls)
            assert any("number: 42" in call for call in calls)
            assert any("boolean: True" in call for call in calls)


class TestIntegrationScenarios:
    """Test integration scenarios and edge cases."""

    def test_error_handler_with_success_message(self):
        """Test error handler doesn't interfere with success messages."""

        @error_handler
        def successful_operation():
            success_message("Operation completed")
            return "result"

        with patch("click.echo") as mock_echo:
            result = successful_operation()

            assert result == "result"
            mock_echo.assert_called_once()

    def test_table_output_with_unicode_characters(self):
        """Test table output handles Unicode characters."""
        headers = ["Name", "Symbol"]
        rows = [["Alpha", "α"], ["Beta", "β"], ["Gamma", "γ"]]

        with patch("click.echo") as mock_echo:
            output_table(headers, rows)

            # Should handle Unicode without errors
            assert mock_echo.call_count >= 5

    def test_json_output_with_unicode_data(self):
        """Test JSON output handles Unicode data."""
        data = {"message": "Hello 世界", "emoji": "🚀", "symbols": "αβγ"}

        with patch("click.echo") as mock_echo:
            output_json(data)

            mock_echo.assert_called_once()
            output = mock_echo.call_args[0][0]
            parsed = json.loads(output)
            assert parsed == data

    def test_format_output_with_human_format_function_error(self):
        """Test format output handles human format function errors."""
        ctx = click.Context(click.Command("test"))
        ctx.obj = {"json": False}
        data = {"test": "value"}

        def failing_format_func(data):
            raise ValueError("Format function failed")

        # Should not raise the ValueError, but might fall back to default
        with pytest.raises(ValueError):
            format_output(ctx, data, failing_format_func)
