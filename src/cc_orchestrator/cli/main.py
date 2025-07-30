"""Main CLI entry point for CC-Orchestrator."""

import warnings

import click

from .config import config
from .instances import instances
from .tasks import tasks
from .web import web
from .worktrees import worktrees

# Suppress Pydantic serialization warnings globally for better CLI UX
warnings.filterwarnings("ignore", message=".*Pydantic serializer warnings.*")


@click.group()
@click.version_option(version="0.1.0", prog_name="cc-orchestrator")
@click.option("--config", "-c", help="Configuration file path")
@click.option("--profile", "-p", help="Configuration profile to use")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.option("--quiet", "-q", is_flag=True, help="Suppress non-essential output")
@click.option("--json", is_flag=True, help="Output in JSON format")
# Configuration override flags
@click.option("--max-instances", type=int, help="Override max_instances setting")
@click.option("--web-port", type=int, help="Override web_port setting")
@click.option("--web-host", help="Override web_host setting")
@click.option("--log-level", help="Override log_level setting")
@click.option("--worktree-base-path", help="Override worktree_base_path setting")
@click.option("--cpu-threshold", type=float, help="Override cpu_threshold setting")
@click.option("--memory-limit", type=int, help="Override memory_limit setting")
@click.pass_context
def main(
    ctx: click.Context,
    config: str | None,
    profile: str | None,
    verbose: bool,
    quiet: bool,
    json: bool,
    max_instances: int | None,
    web_port: int | None,
    web_host: str | None,
    log_level: str | None,
    worktree_base_path: str | None,
    cpu_threshold: float | None,
    memory_limit: int | None,
) -> None:
    """Claude Code Orchestrator - Manage multiple Claude instances through git worktrees.

    This tool helps manage multiple Claude Code instances running in parallel,
    each isolated in their own git worktrees for concurrent development on
    different issues or features.

    Use command groups to organize functionality:
    - instances: Manage Claude Code instances
    - tasks: Manage work items and assignments
    - worktrees: Manage git worktrees
    - config: Manage configuration settings
    - web: Control the web interface
    """
    ctx.ensure_object(dict)
    ctx.obj["config"] = config
    ctx.obj["profile"] = profile
    ctx.obj["verbose"] = verbose
    ctx.obj["quiet"] = quiet
    ctx.obj["json"] = json

    # Store CLI overrides for configuration
    ctx.obj["cli_overrides"] = {
        "max_instances": max_instances,
        "web_port": web_port,
        "web_host": web_host,
        "log_level": log_level,
        "worktree_base_path": worktree_base_path,
        "cpu_threshold": cpu_threshold,
        "memory_limit": memory_limit,
    }
    # Remove None values
    ctx.obj["cli_overrides"] = {
        k: v for k, v in ctx.obj["cli_overrides"].items() if v is not None
    }

    # Validate conflicting options
    if verbose and quiet:
        raise click.UsageError("Cannot use both --verbose and --quiet options")


# Add command groups
main.add_command(instances)
main.add_command(tasks)
main.add_command(worktrees)
main.add_command(config)
main.add_command(web)


if __name__ == "__main__":
    main()
