"""Main CLI entry point for CC-Orchestrator."""

import click

from .config import config
from .instances import instances
from .tasks import tasks
from .web import web
from .worktrees import worktrees


@click.group()
@click.version_option(version="0.1.0", prog_name="cc-orchestrator")
@click.option("--config", "-c", help="Configuration file path")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.option("--quiet", "-q", is_flag=True, help="Suppress non-essential output")
@click.option("--json", is_flag=True, help="Output in JSON format")
@click.pass_context
def main(
    ctx: click.Context, config: str | None, verbose: bool, quiet: bool, json: bool
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
    ctx.obj["verbose"] = verbose
    ctx.obj["quiet"] = quiet
    ctx.obj["json"] = json

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
