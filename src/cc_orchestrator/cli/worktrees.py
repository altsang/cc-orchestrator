"""Git worktree management commands."""

import json

import click

from ..core.worktree_service import WorktreeService, WorktreeServiceError
from ..utils.logging import LogContext, get_logger

logger = get_logger(__name__, LogContext.CLI)


@click.group()
def worktrees() -> None:
    """Manage git worktrees."""
    pass


@worktrees.command()
@click.option(
    "--format",
    default="table",
    type=click.Choice(["table", "json"]),
    help="Output format",
)
@click.option("--sync/--no-sync", default=True, help="Sync with git before listing")
def list(format: str, sync: bool) -> None:
    """List all git worktrees."""
    try:
        service = WorktreeService()
        worktrees = service.list_worktrees(sync_with_git=sync)

        if format == "json":
            # Convert datetime objects to strings for JSON serialization
            for wt in worktrees:
                if wt.get("created_at"):
                    wt["created_at"] = wt["created_at"].isoformat()
                if wt.get("last_sync"):
                    wt["last_sync"] = wt["last_sync"].isoformat()
            click.echo(json.dumps(worktrees, indent=2))
        else:
            if not worktrees:
                click.echo("No worktrees found.")
                return

            # Table format
            click.echo("ID  | Name             | Branch           | Status   | Path")
            click.echo("-" * 70)
            for wt in worktrees:
                click.echo(
                    f"{wt['id']:<3} | {wt['name']:<15} | {wt['branch']:<15} | {wt['status']:<8} | {wt['path']}"
                )

    except WorktreeServiceError as e:
        logger.error(f"Failed to list worktrees: {e}")
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()
    except Exception as e:
        logger.error(f"Unexpected error listing worktrees: {e}")
        click.echo(f"Unexpected error: {e}", err=True)
        raise click.Abort()


@worktrees.command()
@click.argument("name")
@click.argument("branch_name")
@click.option("--path", help="Custom path for worktree")
@click.option("--from-branch", help="Branch to checkout from (defaults to main/master)")
@click.option("--instance-id", type=int, help="Associate with instance ID")
@click.option("--force", is_flag=True, help="Force creation even if path exists")
@click.option(
    "--format",
    default="table",
    type=click.Choice(["table", "json"]),
    help="Output format",
)
def create(
    name: str,
    branch_name: str,
    path: str | None,
    from_branch: str | None,
    instance_id: int | None,
    force: bool,
    format: str,
) -> None:
    """Create a new git worktree.

    NAME: Name for the worktree (used for directory if --path not specified)
    BRANCH_NAME: Name of the new branch to create for the worktree
    """
    try:
        service = WorktreeService()

        worktree = service.create_worktree(
            name=name,
            branch=branch_name,
            checkout_branch=from_branch,
            custom_path=path,
            instance_id=instance_id,
            force=force,
        )

        if format == "json":
            click.echo(json.dumps(worktree, indent=2))
        else:
            click.echo(f"✓ Created worktree '{worktree['name']}'")
            click.echo(f"  Path: {worktree['path']}")
            click.echo(f"  Branch: {worktree['branch']}")
            click.echo(f"  Commit: {worktree['commit'][:8]}...")
            if worktree["instance_id"]:
                click.echo(f"  Instance: {worktree['instance_id']}")

    except WorktreeServiceError as e:
        logger.error(f"Failed to create worktree: {e}")
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()
    except Exception as e:
        logger.error(f"Unexpected error creating worktree: {e}")
        click.echo(f"Unexpected error: {e}", err=True)
        raise click.Abort()


@worktrees.command()
@click.argument("path_or_id")
@click.option(
    "--force", is_flag=True, help="Force removal even with uncommitted changes"
)
def remove(path_or_id: str, force: bool) -> None:
    """Remove a git worktree.

    PATH_OR_ID: Worktree path or database ID to remove
    """
    try:
        service = WorktreeService()

        # Try to parse as int for ID, otherwise treat as path
        try:
            worktree_id = int(path_or_id)
            removed = service.remove_worktree(worktree_id, force=force)
        except ValueError:
            removed = service.remove_worktree(path_or_id, force=force)

        if removed:
            click.echo(f"✓ Successfully removed worktree: {path_or_id}")
        else:
            click.echo(f"Failed to remove worktree: {path_or_id}")
            raise click.Abort()

    except WorktreeServiceError as e:
        logger.error(f"Failed to remove worktree: {e}")
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()
    except Exception as e:
        logger.error(f"Unexpected error removing worktree: {e}")
        click.echo(f"Unexpected error: {e}", err=True)
        raise click.Abort()


@worktrees.command()
@click.option(
    "--format",
    default="table",
    type=click.Choice(["table", "json"]),
    help="Output format",
)
def cleanup(format: str) -> None:
    """Clean up stale worktree references."""
    try:
        service = WorktreeService()
        result = service.cleanup_worktrees()

        if format == "json":
            click.echo(json.dumps(result, indent=2))
        else:
            git_count = len(result["git_cleaned"])
            db_count = len(result["db_cleaned"])

            if git_count == 0 and db_count == 0:
                click.echo("✓ No cleanup needed - all worktrees are up to date")
            else:
                click.echo("✓ Cleanup completed:")
                if git_count > 0:
                    click.echo(f"  Git references cleaned: {git_count}")
                    for path in result["git_cleaned"]:
                        click.echo(f"    - {path}")
                if db_count > 0:
                    click.echo(f"  Database records cleaned: {db_count}")
                    for path in result["db_cleaned"]:
                        click.echo(f"    - {path}")

    except WorktreeServiceError as e:
        logger.error(f"Failed to cleanup worktrees: {e}")
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()
    except Exception as e:
        logger.error(f"Unexpected error during cleanup: {e}")
        click.echo(f"Unexpected error: {e}", err=True)
        raise click.Abort()


@worktrees.command()
@click.argument("path_or_id")
@click.option(
    "--format",
    default="table",
    type=click.Choice(["table", "json"]),
    help="Output format",
)
def status(path_or_id: str, format: str) -> None:
    """Get detailed status of a worktree.

    PATH_OR_ID: Worktree path or database ID
    """
    try:
        service = WorktreeService()

        # Try to parse as int for ID, otherwise treat as path
        try:
            worktree_id = int(path_or_id)
            status_info = service.get_worktree_status(worktree_id)
        except ValueError:
            status_info = service.get_worktree_status(path_or_id)

        if format == "json":
            # Convert datetime objects to strings for JSON serialization
            if status_info.get("created_at"):
                status_info["created_at"] = status_info["created_at"].isoformat()
            if status_info.get("last_sync"):
                status_info["last_sync"] = status_info["last_sync"].isoformat()
            click.echo(json.dumps(status_info, indent=2))
        else:
            click.echo(f"Worktree: {status_info['name']} (ID: {status_info['id']})")
            click.echo(f"Path: {status_info['path']}")
            click.echo(f"Branch: {status_info['branch']}")
            click.echo(f"Database Status: {status_info['db_status']}")

            git_status = status_info["git_status"]
            click.echo("Git Status:")
            click.echo(f"  Current Commit: {git_status['commit'][:8]}...")
            click.echo(f"  Has Changes: {'Yes' if git_status['has_changes'] else 'No'}")
            click.echo(f"  Is Dirty: {'Yes' if git_status['is_dirty'] else 'No'}")
            if git_status["ahead"] > 0:
                click.echo(f"  Ahead by: {git_status['ahead']} commits")
            if git_status["behind"] > 0:
                click.echo(f"  Behind by: {git_status['behind']} commits")

            if status_info["instance_id"]:
                click.echo(f"Instance: {status_info['instance_id']}")

    except WorktreeServiceError as e:
        logger.error(f"Failed to get worktree status: {e}")
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()
    except Exception as e:
        logger.error(f"Unexpected error getting status: {e}")
        click.echo(f"Unexpected error: {e}", err=True)
        raise click.Abort()
