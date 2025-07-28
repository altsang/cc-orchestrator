"""Configuration management commands."""

import click

from ..config.loader import OrchestratorConfig, load_config, save_config
from .utils import format_output, handle_error


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
        config_obj = load_config(config_path)
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
    try:
        config_path = ctx.obj.get("config") if ctx.obj else None
        config_obj = load_config(config_path)

        # Check if key exists in model
        if not hasattr(config_obj, key):
            handle_error(f"Unknown configuration key: {key}")

        # Update configuration
        setattr(config_obj, key, value)

        # Save configuration
        saved_path = save_config(config_obj, config_path)

        if not (ctx.obj and ctx.obj.get("quiet")):
            click.echo(f"Configuration updated: {key}={value}")
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
        config_obj = load_config(config_path)

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
        load_config(config_path)  # This will raise if invalid

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
