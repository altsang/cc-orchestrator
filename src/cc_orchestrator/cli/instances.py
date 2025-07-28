"""Instance management commands."""

import click


@click.group()
def instances() -> None:
    """Manage Claude Code instances."""
    pass


@instances.command()
def status() -> None:
    """Show status of all Claude instances."""
    click.echo("Status command - to be implemented")


@instances.command()
@click.argument("issue_id")
def start(issue_id: str) -> None:
    """Start a new Claude instance for an issue."""
    click.echo(f"Starting instance for issue: {issue_id}")


@instances.command()
@click.argument("issue_id")
def stop(issue_id: str) -> None:
    """Stop a Claude instance."""
    click.echo(f"Stopping instance for issue: {issue_id}")


@instances.command()
def list() -> None:
    """List all active instances."""
    click.echo("List command - to be implemented")
