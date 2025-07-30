"""Configuration management commands."""

import warnings
from typing import Any, Union

import click

from ..config.loader import (
    OrchestratorConfig,
    find_config_file,
    load_config,
    load_config_file,
    save_config,
)
from .utils import format_output, handle_error

# Suppress Pydantic warnings early to prevent CLI noise
warnings.filterwarnings("ignore", message=".*Pydantic serializer warnings.*")


@click.group()
def config() -> None:
    """Manage configuration settings."""
    pass


@config.command()
@click.pass_context
def show(ctx: click.Context) -> None:
    """Show current configuration."""
    try:
        config_path = ctx.obj.get("config") if ctx.obj else None
        profile = ctx.obj.get("profile") if ctx.obj else None
        cli_overrides = ctx.obj.get("cli_overrides") if ctx.obj else None
        config_obj = load_config(config_path, profile, cli_overrides)
        config_dict = config_obj.model_dump()

        format_output(ctx, {"configuration": config_dict})
    except Exception as e:
        handle_error(f"Failed to load configuration: {e}")


@config.command()
@click.argument("key")
@click.argument("value")
@click.pass_context
def set(ctx: click.Context, key: str, value: str) -> None:
    """Set a configuration value."""
    # Suppress Pydantic warnings for CLI operations
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")
        warnings.filterwarnings("ignore", message=".*serializer warnings.*")
        _set_config_value(ctx, key, value)


def _set_config_value(ctx: click.Context, key: str, value: str) -> None:
    """Internal function to set configuration value."""
    try:
        config_path = ctx.obj.get("config") if ctx.obj else None
        profile = ctx.obj.get("profile") if ctx.obj else None
        cli_overrides = ctx.obj.get("cli_overrides") if ctx.obj else None
        config_obj = load_config(config_path, profile, cli_overrides)

        # Check if key exists in model
        if not hasattr(config_obj, key):
            handle_error(f"Unknown configuration key: {key}")

        # Get the field type and convert value accordingly
        field_info = config_obj.model_fields.get(key)
        converted_value: Any = value
        if field_info:
            field_type = field_info.annotation

            # Handle Union types (e.g., int | None, str | None)
            if (
                hasattr(field_type, "__origin__")
                and getattr(field_type, "__origin__", None) is Union
            ):
                # This is a Union type, get the args
                union_args = getattr(field_type, "__args__", ())
                # Try to convert to non-None type first
                non_none_types = [arg for arg in union_args if arg is not type(None)]
                if non_none_types:
                    field_type = non_none_types[0]  # Use the first non-None type

            # Handle common type conversions
            if field_type is int:
                try:
                    converted_value = int(value)
                except ValueError:
                    handle_error(f"Invalid integer value for {key}: {value}")
            elif field_type is bool:
                converted_value = value.lower() in ("true", "1", "yes", "on")
            elif field_type is float:
                try:
                    converted_value = float(value)
                except ValueError:
                    handle_error(f"Invalid float value for {key}: {value}")

        # Create a new config with the updated value
        config_dict = config_obj.model_dump()
        config_dict[key] = converted_value
        config_obj = OrchestratorConfig(**config_dict)

        # Save configuration
        saved_path = save_config(config_obj, config_path)

        if not (ctx.obj and ctx.obj.get("quiet")):
            click.echo(f"Configuration updated: {key}={converted_value}")
            click.echo(f"Saved to: {saved_path}")

    except Exception as e:
        handle_error(f"Failed to set configuration: {e}")


@config.command()
@click.argument("key")
@click.pass_context
def get(ctx: click.Context, key: str) -> None:
    """Get a configuration value."""
    try:
        config_path = ctx.obj.get("config") if ctx.obj else None
        profile = ctx.obj.get("profile") if ctx.obj else None
        cli_overrides = ctx.obj.get("cli_overrides") if ctx.obj else None
        config_obj = load_config(config_path, profile, cli_overrides)

        if hasattr(config_obj, key):
            value = getattr(config_obj, key)
            format_output(ctx, {key: value})
        else:
            handle_error(f"Unknown configuration key: {key}")

    except Exception as e:
        handle_error(f"Failed to get configuration: {e}")


@config.command()
@click.pass_context
def validate(ctx: click.Context) -> None:
    """Validate current configuration."""
    try:
        config_path = ctx.obj.get("config") if ctx.obj else None
        profile = ctx.obj.get("profile") if ctx.obj else None
        cli_overrides = ctx.obj.get("cli_overrides") if ctx.obj else None
        load_config(config_path, profile, cli_overrides)  # This will raise if invalid

        if not (ctx.obj and ctx.obj.get("quiet")):
            click.echo("Configuration is valid")

    except Exception as e:
        handle_error(f"Configuration validation failed: {e}")


@config.command()
@click.option("--path", help="Custom path for config file")
@click.pass_context
def init(ctx: click.Context, path: str | None) -> None:
    """Initialize configuration file with defaults."""
    try:
        config_obj = OrchestratorConfig()  # Use defaults
        saved_path = save_config(config_obj, path)

        if not (ctx.obj and ctx.obj.get("quiet")):
            click.echo(f"Configuration initialized at: {saved_path}")

    except Exception as e:
        handle_error(f"Failed to initialize configuration: {e}")


@config.command()
@click.pass_context
def profiles(ctx: click.Context) -> None:
    """List available configuration profiles."""
    try:
        config_path = ctx.obj.get("config") if ctx.obj else None
        config_file = find_config_file(config_path)

        if not config_file:
            if not (ctx.obj and ctx.obj.get("quiet")):
                click.echo(
                    "No configuration file found. Use 'config init' to create one."
                )
            return

        config_data = load_config_file(config_file)

        if "profiles" not in config_data:
            if not (ctx.obj and ctx.obj.get("quiet")):
                click.echo("No profiles defined in configuration file.")
            return

        profiles_data = config_data["profiles"]
        format_output(ctx, {"profiles": list(profiles_data.keys())})

    except Exception as e:
        handle_error(f"Failed to list profiles: {e}")


@config.command()
def locations() -> None:
    """Show configuration file search locations."""
    locations = [
        "./cc-orchestrator.yaml",
        "./cc-orchestrator.yml",
        "~/.config/cc-orchestrator/config.yaml",
        "~/.cc-orchestrator.yaml",
    ]

    click.echo("Configuration file search locations (in order):")
    for i, location in enumerate(locations, 1):
        click.echo(f"  {i}. {location}")

    click.echo("\nEnvironment variables (CC_ORCHESTRATOR_*):")
    env_vars = [
        "MAX_INSTANCES",
        "INSTANCE_TIMEOUT",
        "WORKTREE_BASE_PATH",
        "AUTO_CLEANUP",
        "WEB_HOST",
        "WEB_PORT",
        "GITHUB_TOKEN",
        "GITHUB_ORG",
        "GITHUB_REPO",
        "LOG_LEVEL",
        "LOG_FILE",
        "DEFAULT_OUTPUT_FORMAT",
    ]
    for var in env_vars:
        click.echo(f"  CC_ORCHESTRATOR_{var}")
