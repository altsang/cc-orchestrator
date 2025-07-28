"""Git worktree management commands."""

import click


@click.group()
def worktrees() -> None:
    """Manage git worktrees."""
    pass


@worktrees.command()
def list() -> None:
    """List all git worktrees."""
    click.echo("Worktree list command - to be implemented")


@worktrees.command()
@click.argument("branch_name")
@click.option("--path", help="Custom path for worktree")
def create(branch_name: str, path: str | None) -> None:
    """Create a new git worktree."""
    path_msg = f" at {path}" if path else ""
    click.echo(f"Creating worktree for {branch_name}{path_msg} - to be implemented")


@worktrees.command()
@click.argument("worktree_path")
def remove(worktree_path: str) -> None:
    """Remove a git worktree."""
    click.echo(f"Removing worktree {worktree_path} - to be implemented")


@worktrees.command()
def cleanup() -> None:
    """Clean up stale worktree references."""
    click.echo("Worktree cleanup - to be implemented")
