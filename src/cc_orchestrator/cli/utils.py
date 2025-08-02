"""CLI utilities for output formatting and common functionality."""

import json
import sys
from functools import wraps
from typing import Any, Callable

import click


class CliError(Exception):
    """Exception for CLI errors."""

    def __init__(self, message: str, exit_code: int = 1):
        """Initialize CLI error.

        Args:
            message: Error message
            exit_code: Exit code for the CLI
        """
        super().__init__(message)
        self.message = message
        self.exit_code = exit_code


def error_handler(func: Callable) -> Callable:
    """Decorator for handling CLI errors."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except CliError as e:
            click.echo(click.style(f"Error: {e.message}", fg="red"), err=True)
            sys.exit(e.exit_code)
        except Exception as e:
            click.echo(click.style(f"Unexpected error: {e}", fg="red"), err=True)
            sys.exit(1)

    return wrapper


def success_message(message: str) -> None:
    """Display a success message."""
    click.echo(click.style(f"✓ {message}", fg="green"))


def output_json(data: dict[str, Any]) -> None:
    """Output data as JSON."""
    click.echo(json.dumps(data, indent=2))


def output_table(headers: list[str], rows: list[list[str]]) -> None:
    """Output data as a formatted table."""
    if not rows:
        click.echo("No data to display")
        return

    # Calculate column widths
    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            if i < len(col_widths):
                col_widths[i] = max(col_widths[i], len(str(cell)))

    # Print header
    header_row = " | ".join(
        h.ljust(w) for h, w in zip(headers, col_widths, strict=False)
    )
    click.echo(header_row)
    click.echo("-" * len(header_row))

    # Print rows
    for row in rows:
        formatted_row = " | ".join(
            str(cell).ljust(w) for cell, w in zip(row, col_widths, strict=False)
        )
        click.echo(formatted_row)


def handle_error(message: str, exit_code: int = 1) -> None:
    """Handle errors with consistent formatting."""
    click.echo(click.style(f"Error: {message}", fg="red"), err=True)
    sys.exit(exit_code)


def verbose_echo(ctx: click.Context, message: str) -> None:
    """Echo message only if verbose mode is enabled."""
    if ctx.obj and ctx.obj.get("verbose"):
        click.echo(click.style(f"[VERBOSE] {message}", fg="blue"), err=True)


def quiet_echo(ctx: click.Context, message: str) -> None:
    """Echo message only if not in quiet mode."""
    if not (ctx.obj and ctx.obj.get("quiet")):
        click.echo(message)


def format_output(
    ctx: click.Context, data: dict[str, Any], human_format_func: Any = None
) -> None:
    """Format output based on context (JSON or human-readable)."""
    if ctx.obj and ctx.obj.get("json"):
        output_json(data)
    elif human_format_func:
        human_format_func(data)
    else:
        # Default human format
        for key, value in data.items():
            click.echo(f"{key}: {value}")
