"""Instance management commands."""

import asyncio
import builtins
import json
from pathlib import Path
from typing import Any

import click

from ..core.orchestrator import DatabaseSyncError, Orchestrator
from ..utils.logging import LogContext, get_logger

logger = get_logger(__name__, LogContext.CLI)


@click.group()
def instances() -> None:
    """Manage Claude Code instances."""
    pass


@instances.command()
@click.option("--json", "output_json", is_flag=True, help="Output in JSON format")
def status(output_json: bool) -> None:
    """Show status of all Claude instances."""

    async def _status() -> None:
        try:
            orchestrator = Orchestrator()
            await orchestrator.initialize(
                lazy_load=False
            )  # Need all instances for status

            instances = await orchestrator.list_instances()

            if not instances:
                if output_json:
                    click.echo(json.dumps({"instances": [], "total": 0}))
                else:
                    click.echo("No active instances found.")
                return

            # Gather status information
            status_data: builtins.list[dict[str, Any]] = []
            for instance in instances:
                info = instance.get_info()
                process_info = await instance.get_process_status()

                if process_info:
                    info.update(
                        {
                            "process_status": process_info.status.value,
                            "cpu_percent": process_info.cpu_percent,
                            "memory_mb": process_info.memory_mb,
                        }
                    )

                status_data.append(info)

            if output_json:
                click.echo(
                    json.dumps(
                        {"instances": status_data, "total": len(status_data)}, indent=2
                    )
                )
            else:
                # Human-readable output
                click.echo(f"\nActive Claude Instances ({len(status_data)}):\n")
                for info in status_data:
                    click.echo(f"Issue ID: {info['issue_id']}")
                    click.echo(f"  Status: {info['status']}")
                    click.echo(f"  Workspace: {info['workspace_path']}")
                    click.echo(f"  Branch: {info['branch_name']}")
                    click.echo(f"  Tmux Session: {info['tmux_session']}")
                    if info.get("process_id"):
                        click.echo(f"  Process ID: {info['process_id']}")
                        if info.get("cpu_percent") is not None:
                            click.echo(f"  CPU: {info['cpu_percent']:.1f}%")
                        if info.get("memory_mb") is not None:
                            click.echo(f"  Memory: {info['memory_mb']:.1f} MB")
                    click.echo()

            await orchestrator.cleanup()

        except Exception as e:
            logger.error("Error getting instance status", error=str(e))
            if output_json:
                click.echo(json.dumps({"error": str(e)}))
            else:
                click.echo(f"Error: {e}", err=True)

    asyncio.run(_status())


@instances.command()
@click.argument("issue_id")
@click.option(
    "--workspace",
    type=click.Path(path_type=Path),
    help="Workspace directory (default: ../cc-orchestrator-issue-{issue_id})",
)
@click.option("--branch", help="Git branch name (default: feature/issue-{issue_id})")
@click.option(
    "--tmux-session", help="Tmux session name (default: claude-issue-{issue_id})"
)
@click.option("--json", "output_json", is_flag=True, help="Output in JSON format")
def start(
    issue_id: str,
    workspace: Path | None,
    branch: str | None,
    tmux_session: str | None,
    output_json: bool,
) -> None:
    """Start a new Claude instance for an issue."""

    async def _start() -> None:
        try:
            orchestrator = Orchestrator()
            await orchestrator.initialize(lazy_load=True)  # Performance optimization

            # Check if instance already exists
            existing_instance = await orchestrator.get_instance(issue_id)
            if existing_instance:
                if existing_instance.is_running():
                    message = f"Instance for issue {issue_id} is already running"
                    if output_json:
                        click.echo(json.dumps({"error": message, "issue_id": issue_id}))
                    else:
                        click.echo(f"Error: {message}")
                    return
                else:
                    # Instance exists but not running, start it
                    success = await existing_instance.start()

                    # Sync instance state to database (FAIL-FAST)
                    try:
                        await orchestrator.sync_instance_state(issue_id)
                        logger.info(
                            "Existing instance state synced to database",
                            instance_id=issue_id,
                        )
                    except DatabaseSyncError as e:
                        # Critical failure - stop the instance and fail the operation
                        logger.error(
                            "Critical database sync failure - stopping existing instance",
                            instance_id=issue_id,
                            error=str(e),
                        )
                        await existing_instance.stop()  # Clean up the running process

                        if output_json:
                            click.echo(
                                json.dumps(
                                    {
                                        "error": "Database sync failed - instance stopped",
                                        "issue_id": issue_id,
                                        "details": str(e),
                                    }
                                )
                            )
                        else:
                            click.echo(
                                f"ERROR: Failed to persist instance {issue_id} to database",
                                err=True,
                            )
                            click.echo(
                                "Instance has been stopped to prevent inconsistent state",
                                err=True,
                            )
                        await orchestrator.cleanup()
                        return
                    except Exception as e:
                        # Unexpected error - also fail fast
                        logger.error(
                            "Unexpected error during database sync for existing instance",
                            instance_id=issue_id,
                            error=str(e),
                        )
                        await existing_instance.stop()  # Clean up the running process

                        if output_json:
                            click.echo(
                                json.dumps(
                                    {
                                        "error": "Instance sync failed",
                                        "issue_id": issue_id,
                                        "details": str(e),
                                    }
                                )
                            )
                        else:
                            click.echo(
                                f"ERROR: Failed to sync existing instance {issue_id} - operation aborted",
                                err=True,
                            )
                        await orchestrator.cleanup()
                        return

                    if success:
                        info = existing_instance.get_info()
                        if output_json:
                            click.echo(
                                json.dumps({"status": "started", "instance": info})
                            )
                        else:
                            click.echo(
                                f"Started existing instance for issue {issue_id}"
                            )
                            click.echo(f"  Process ID: {info['process_id']}")
                            click.echo(f"  Workspace: {info['workspace_path']}")
                    else:
                        message = (
                            f"Failed to start existing instance for issue {issue_id}"
                        )
                        if output_json:
                            click.echo(
                                json.dumps({"error": message, "issue_id": issue_id})
                            )
                        else:
                            click.echo(f"Error: {message}")
                    await orchestrator.cleanup()
                    return

            # Create new instance
            kwargs: dict[str, Any] = {}
            if workspace:
                kwargs["workspace_path"] = workspace
            if branch:
                kwargs["branch_name"] = branch
            if tmux_session:
                kwargs["tmux_session"] = tmux_session

            instance = await orchestrator.create_instance(issue_id, **kwargs)

            # Start the instance
            success = await instance.start()

            # CRITICAL: Sync instance state to database (FAIL-FAST BEHAVIOR)
            # This is the core fix for Issue #59 - ensures instances persist across sessions
            try:
                await orchestrator.sync_instance_state(issue_id)
                logger.info("Instance state synced to database", instance_id=issue_id)

            except DatabaseSyncError as e:
                # FAIL-FAST: Critical database sync failure
                # Rather than allow inconsistent state (instance running but not persisted),
                # we stop the instance immediately to maintain system integrity
                logger.error(
                    "Critical database sync failure - stopping instance",
                    instance_id=issue_id,
                    error=str(e),
                )

                # Step 1: Stop the running process to prevent orphaned instances
                await instance.stop()

                # Step 2: Remove from in-memory cache
                await orchestrator.destroy_instance(issue_id)

                # Step 3: Report failure to user
                if output_json:
                    click.echo(
                        json.dumps(
                            {
                                "error": "Database sync failed - instance stopped",
                                "issue_id": issue_id,
                                "details": str(e),
                            }
                        )
                    )
                else:
                    click.echo(
                        f"ERROR: Failed to persist instance {issue_id} to database",
                        err=True,
                    )
                    click.echo(
                        "Instance has been stopped to prevent inconsistent state",
                        err=True,
                    )
                    click.echo(f"Details: {e}", err=True)

                await orchestrator.cleanup()
                return

            except Exception as e:
                # FAIL-FAST: Unexpected database error
                # Same fail-fast behavior for any database-related failure
                logger.error(
                    "Unexpected error during database sync",
                    instance_id=issue_id,
                    error=str(e),
                )

                # Clean up running instance to prevent inconsistency
                await instance.stop()
                await orchestrator.destroy_instance(issue_id)

                if output_json:
                    click.echo(
                        json.dumps(
                            {
                                "error": "Instance sync failed",
                                "issue_id": issue_id,
                                "details": str(e),
                            }
                        )
                    )
                else:
                    click.echo(
                        f"ERROR: Failed to sync instance {issue_id} - operation aborted",
                        err=True,
                    )
                    click.echo(f"Details: {e}", err=True)

                await orchestrator.cleanup()
                return

            if success:
                info = instance.get_info()
                if output_json:
                    click.echo(json.dumps({"status": "started", "instance": info}))
                else:
                    click.echo(
                        f"Successfully started Claude instance for issue {issue_id}"
                    )
                    click.echo(f"  Process ID: {info['process_id']}")
                    click.echo(f"  Workspace: {info['workspace_path']}")
                    click.echo(f"  Branch: {info['branch_name']}")
                    click.echo(f"  Tmux Session: {info['tmux_session']}")

                # TODO: Register instance with health monitor
                try:
                    # Health monitor registration would go here
                    pass
                except Exception as e:
                    logger.error(
                        "Failed to register instance with health monitor",
                        instance_id=issue_id,
                        error=str(e),
                    )
                    click.echo(
                        "Failed to register instance with health monitor", err=True
                    )

            else:
                message = f"Failed to start instance for issue {issue_id}"
                if output_json:
                    click.echo(json.dumps({"error": message, "issue_id": issue_id}))
                else:
                    click.echo(f"Error: {message}")

            await orchestrator.cleanup()

        except Exception as e:
            logger.error("Error starting instance", issue_id=issue_id, error=str(e))
            if output_json:
                click.echo(json.dumps({"error": str(e), "issue_id": issue_id}))
            else:
                click.echo(f"Error: {e}", err=True)

    asyncio.run(_start())


@instances.command()
@click.argument("issue_id")
@click.option(
    "--force", is_flag=True, help="Force kill the process if graceful stop fails"
)
@click.option(
    "--timeout", type=int, default=30, help="Timeout for graceful shutdown in seconds"
)
@click.option("--json", "output_json", is_flag=True, help="Output in JSON format")
def stop(issue_id: str, force: bool, timeout: int, output_json: bool) -> None:
    """Stop a Claude instance."""

    async def _stop() -> None:
        try:
            orchestrator = Orchestrator()
            await orchestrator.initialize(
                lazy_load=True
            )  # Performance optimization - only load specific instance

            instance = await orchestrator.get_instance(issue_id)
            if not instance:
                message = f"No instance found for issue {issue_id}"
                if output_json:
                    click.echo(json.dumps({"error": message, "issue_id": issue_id}))
                else:
                    click.echo(f"Error: {message}")
                await orchestrator.cleanup()
                return

            if not instance.is_running():
                message = f"Instance for issue {issue_id} is not running"
                if output_json:
                    click.echo(
                        json.dumps({"status": "already_stopped", "issue_id": issue_id})
                    )
                else:
                    click.echo(f"Instance for issue {issue_id} is already stopped")
                await orchestrator.cleanup()
                return

            # Stop the instance
            success = await instance.stop()

            # Sync instance state to database
            try:
                await orchestrator.sync_instance_state(issue_id)
                logger.info(
                    "Instance stop state synced to database", instance_id=issue_id
                )
            except Exception as e:
                logger.error(
                    "Failed to sync instance stop state to database",
                    instance_id=issue_id,
                    error=str(e),
                )

            if success:
                if output_json:
                    click.echo(json.dumps({"status": "stopped", "issue_id": issue_id}))
                else:
                    click.echo(f"Successfully stopped instance for issue {issue_id}")
            else:
                message = f"Failed to stop instance for issue {issue_id}"
                if output_json:
                    click.echo(json.dumps({"error": message, "issue_id": issue_id}))
                else:
                    click.echo(f"Error: {message}")

            await orchestrator.cleanup()

        except Exception as e:
            logger.error("Error stopping instance", issue_id=issue_id, error=str(e))
            if output_json:
                click.echo(json.dumps({"error": str(e), "issue_id": issue_id}))
            else:
                click.echo(f"Error: {e}", err=True)

    asyncio.run(_stop())


@instances.command()
@click.option("--json", "output_json", is_flag=True, help="Output in JSON format")
@click.option("--running-only", is_flag=True, help="Show only running instances")
def list(output_json: bool, running_only: bool) -> None:
    """List all active instances."""

    async def _list() -> None:
        try:
            orchestrator = Orchestrator()
            await orchestrator.initialize(
                lazy_load=False
            )  # Need all instances for list

            instances = await orchestrator.list_instances()
            logger.info("Retrieved instances from orchestrator", count=len(instances))

            if running_only:
                instances = [i for i in instances if i.is_running()]
                logger.info("Filtered for running instances", count=len(instances))

            if not instances:
                logger.info("No instances to display")
                if output_json:
                    click.echo(json.dumps({"instances": [], "total": 0}))
                else:
                    status_msg = "running" if running_only else "active"
                    click.echo(f"No {status_msg} instances found.")
                await orchestrator.cleanup()
                return

            # Gather instance information
            instance_data: builtins.list[dict[str, Any]] = []
            for instance in instances:
                info = instance.get_info()
                process_info = await instance.get_process_status()

                if process_info:
                    info.update(
                        {
                            "process_status": process_info.status.value,
                            "cpu_percent": process_info.cpu_percent,
                            "memory_mb": process_info.memory_mb,
                        }
                    )

                instance_data.append(info)

            if output_json:
                click.echo(
                    json.dumps(
                        {
                            "instances": instance_data,
                            "total": len(instance_data),
                            "filter": "running" if running_only else "all",
                        },
                        indent=2,
                    )
                )
            else:
                # Human-readable output
                status_msg = "Running" if running_only else "Active"
                click.echo(f"\n{status_msg} Claude Instances ({len(instance_data)}):\n")

                for info in instance_data:
                    status_indicator = "🟢" if info["status"] == "running" else "🔴"
                    click.echo(f"{status_indicator} {info['issue_id']}")
                    click.echo(f"   Status: {info['status']}")
                    click.echo(f"   Workspace: {info['workspace_path']}")
                    if info.get("process_id"):
                        click.echo(f"   PID: {info['process_id']}")
                        if (
                            info.get("cpu_percent") is not None
                            and info.get("memory_mb") is not None
                        ):
                            click.echo(
                                f"   Resources: {info['cpu_percent']:.1f}% CPU, {info['memory_mb']:.1f} MB RAM"
                            )
                    click.echo()

            await orchestrator.cleanup()

        except Exception as e:
            logger.error("Error listing instances", error=str(e))
            if output_json:
                click.echo(json.dumps({"error": str(e)}))
            else:
                click.echo(f"Error: {e}", err=True)

    asyncio.run(_list())
