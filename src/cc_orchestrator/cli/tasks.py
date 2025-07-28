"""Task management commands."""

import click


@click.group()
def tasks() -> None:
    """Manage tasks and work items."""
    pass


@tasks.command()
def list() -> None:
    """List all tasks."""
    click.echo("Task list command - to be implemented")


@tasks.command()
@click.argument("task_id")
def show(task_id: str) -> None:
    """Show details for a specific task."""
    click.echo(f"Task details for: {task_id} - to be implemented")


@tasks.command()
@click.argument("task_id")
def assign(task_id: str) -> None:
    """Assign a task to an instance."""
    click.echo(f"Assigning task {task_id} - to be implemented")
