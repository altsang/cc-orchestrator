"""Main CLI entry point for CC-Orchestrator."""

import click
from typing import Optional


@click.group()
@click.version_option(version="0.1.0", prog_name="cc-orchestrator")
@click.option("--config", "-c", help="Configuration file path")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.pass_context
def main(ctx: click.Context, config: Optional[str], verbose: bool) -> None:
    """Claude Code Orchestrator - Manage multiple Claude instances through git worktrees."""
    ctx.ensure_object(dict)
    ctx.obj["config"] = config
    ctx.obj["verbose"] = verbose


@main.command()
def status() -> None:
    """Show status of all Claude instances."""
    click.echo("Status command - to be implemented")


@main.command()
@click.argument("issue_id")
def start(issue_id: str) -> None:
    """Start a new Claude instance for an issue."""
    click.echo(f"Starting instance for issue: {issue_id}")


@main.command()
@click.argument("issue_id")
def stop(issue_id: str) -> None:
    """Stop a Claude instance."""
    click.echo(f"Stopping instance for issue: {issue_id}")


@main.command()
def list() -> None:
    """List all active instances."""
    click.echo("List command - to be implemented")


@main.command()
def web() -> None:
    """Start the web interface."""
    click.echo("Starting web interface - to be implemented")


if __name__ == "__main__":
    main()