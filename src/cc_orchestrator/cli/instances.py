"""Instance management commands."""

import asyncio
import builtins
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import click

from ..core.health_monitor import get_health_monitor
from ..core.orchestrator import Orchestrator
from ..database.models import HealthStatus
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
            await orchestrator.initialize()

            instances = orchestrator.list_instances()

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
            await orchestrator.initialize()

            # Check if instance already exists
            existing_instance = orchestrator.get_instance(issue_id)
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
            await orchestrator.initialize()

            instance = orchestrator.get_instance(issue_id)
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
            await orchestrator.initialize()

            instances = orchestrator.list_instances()

            if running_only:
                instances = [i for i in instances if i.is_running()]

            if not instances:
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


@instances.group()
def health() -> None:
    """Health monitoring commands for instances."""
    pass


@health.command()
@click.argument("issue_id")
@click.option("--json", "output_json", is_flag=True, help="Output in JSON format")
def check(issue_id: str, output_json: bool) -> None:
    """Perform a health check on a specific instance."""

    async def _health_check() -> None:
        try:
            health_monitor = get_health_monitor()
            result = await health_monitor.check_instance_health(issue_id)

            if output_json:
                # Convert enum to string value for JSON serialization
                json_result = result.copy()
                if "overall_status" in json_result and hasattr(
                    json_result["overall_status"], "value"
                ):
                    json_result["overall_status"] = json_result["overall_status"].value
                click.echo(json.dumps(json_result, indent=2, default=str))
            else:
                status = result["overall_status"]
                status_icon = {
                    HealthStatus.HEALTHY: "🟢",
                    HealthStatus.DEGRADED: "🟡",
                    HealthStatus.UNHEALTHY: "🟠",
                    HealthStatus.CRITICAL: "🔴",
                    HealthStatus.UNKNOWN: "⚪",
                }.get(status, "❓")

                click.echo(f"\nHealth Check Results for {issue_id}:")
                click.echo(f"  Overall Status: {status_icon} {status.value.upper()}")
                click.echo(f"  Duration: {result['duration_ms']:.1f}ms")

                if "error" in result:
                    click.echo(f"  Error: {result['error']}")
                else:
                    click.echo("  Individual Checks:")
                    checks = result.get("checks", {})

                    for check_name, check_result in checks.items():
                        if isinstance(check_result, bool):
                            icon = "✅" if check_result else "❌"
                            click.echo(f"    {icon} {check_name}")
                        elif check_result is not None:
                            click.echo(f"    ℹ️  {check_name}: {check_result}")

        except Exception as e:
            logger.error(
                "Error performing health check", issue_id=issue_id, error=str(e)
            )
            if output_json:
                click.echo(json.dumps({"error": str(e)}))
            else:
                click.echo(f"Error: {e}", err=True)

    asyncio.run(_health_check())


@health.command()
@click.option("--json", "output_json", is_flag=True, help="Output in JSON format")
@click.option(
    "--status",
    type=click.Choice([s.value for s in HealthStatus]),
    help="Filter by health status",
)
def health_status(output_json: bool, status: str | None) -> None:
    """Show health status of all instances."""

    async def _health_status() -> None:
        try:
            # For now, show health status of active processes
            health_monitor = get_health_monitor()
            processes = await health_monitor.process_manager.list_processes()

            if not processes:
                if output_json:
                    click.echo(json.dumps({"instances": [], "total": 0}))
                else:
                    click.echo("No active processes found to monitor.")
                return

            instance_health = []
            for instance_id, _process_info in processes.items():
                # Skip if filtering by status (would need database for full filtering)
                if status:
                    continue  # Skip filtering for now

                # Perform quick health check
                health_result = await health_monitor.check_instance_health(instance_id)

                health_data = {
                    "issue_id": instance_id,
                    "health_status": health_result["overall_status"].value,
                    "process_status": health_result["checks"].get(
                        "process_status", "unknown"
                    ),
                    "cpu_percent": health_result["checks"].get("cpu_percent", 0.0),
                    "memory_mb": health_result["checks"].get("memory_mb", 0.0),
                    "duration_ms": health_result["duration_ms"],
                }
                instance_health.append(health_data)

            if output_json:
                click.echo(
                    json.dumps(
                        {"instances": instance_health, "total": len(instance_health)},
                        indent=2,
                    )
                )
            else:
                click.echo(
                    f"\nInstance Health Status ({len(instance_health)} processes):\n"
                )

                for health_data in instance_health:
                    status_val = health_data["health_status"]
                    status_icon = {
                        "healthy": "🟢",
                        "degraded": "🟡",
                        "unhealthy": "🟠",
                        "critical": "🔴",
                        "unknown": "⚪",
                    }.get(status_val, "❓")

                    click.echo(f"{status_icon} {health_data['issue_id']}")
                    click.echo(f"   Status: {status_val.upper()}")
                    click.echo(f"   Process: {health_data['process_status']}")
                    click.echo(f"   CPU: {health_data['cpu_percent']:.1f}%")
                    click.echo(f"   Memory: {health_data['memory_mb']:.1f} MB")
                    click.echo(f"   Check Duration: {health_data['duration_ms']:.1f}ms")
                    click.echo()

        except Exception as e:
            logger.error("Error getting health status", error=str(e))
            if output_json:
                click.echo(json.dumps({"error": str(e)}))
            else:
                click.echo(f"Error: {e}", err=True)

    asyncio.run(_health_status())


@health.command()
@click.argument("issue_id")
@click.option(
    "--days", type=int, default=7, help="Number of days of history to show (default: 7)"
)
@click.option("--json", "output_json", is_flag=True, help="Output in JSON format")
def history(issue_id: str, days: int, output_json: bool) -> None:
    """Show health check history for an instance."""

    async def _health_history() -> None:
        try:
            # For now, just perform a current health check
            # Full history would require database integration
            health_monitor = get_health_monitor()
            result = await health_monitor.check_instance_health(issue_id)

            if "error" in result:
                if output_json:
                    click.echo(
                        json.dumps({"error": result["error"], "instance_id": issue_id})
                    )
                else:
                    click.echo(f"Error: {result['error']}")
                return

            # Create a single history entry with current status
            history_data = [
                {
                    "timestamp": result["timestamp"],
                    "status": result["overall_status"].value,
                    "duration_ms": result["duration_ms"],
                    "checks": result["checks"],
                }
            ]

            if output_json:
                click.echo(
                    json.dumps(
                        {
                            "instance_id": issue_id,
                            "history": history_data,
                            "total": 1,
                            "note": "Full history requires database integration",
                        },
                        indent=2,
                        default=str,
                    )
                )
            else:
                click.echo(f"\nCurrent Health Status for {issue_id}:\n")
                click.echo("(Full history requires database integration)\n")

                entry = history_data[0]
                status_val = entry["status"]
                status_icon = {
                    "healthy": "🟢",
                    "degraded": "🟡",
                    "unhealthy": "🟠",
                    "critical": "🔴",
                    "unknown": "⚪",
                }.get(status_val, "❓")

                click.echo(
                    f"{status_icon} {entry['timestamp']} - {status_val.upper()} ({entry['duration_ms']:.1f}ms)"
                )

                # Show key check results
                checks = entry.get("checks", {})
                if checks.get("process_running") is False:
                    click.echo("    ❌ Process not running")
                elif checks.get("cpu_healthy") is False:
                    click.echo(
                        f"    ⚠️  High CPU usage: {checks.get('cpu_percent', 'N/A')}%"
                    )
                elif checks.get("memory_healthy") is False:
                    click.echo(
                        f"    ⚠️  High memory usage: {checks.get('memory_mb', 'N/A')} MB"
                    )

        except Exception as e:
            logger.error(
                "Error getting health history", issue_id=issue_id, error=str(e)
            )
            if output_json:
                click.echo(json.dumps({"error": str(e)}))
            else:
                click.echo(f"Error: {e}", err=True)

    asyncio.run(_health_history())


@health.command()
@click.option("--json", "output_json", is_flag=True, help="Output in JSON format")
def overview(output_json: bool) -> None:
    """Show overall health overview of all instances."""

    async def _health_overview() -> None:
        try:
            # For now, show overview of active processes
            health_monitor = get_health_monitor()
            processes = await health_monitor.process_manager.list_processes()

            if not processes:
                if output_json:
                    click.echo(
                        json.dumps({"total_instances": 0, "health_percentage": 100.0})
                    )
                else:
                    click.echo("No active processes found.")
                return

            # Calculate overview metrics from current processes
            status_counts = {status.value: 0 for status in HealthStatus}
            total_instances = len(processes)

            for instance_id in processes:
                try:
                    health_result = await health_monitor.check_instance_health(
                        instance_id
                    )
                    status = health_result["overall_status"]
                    status_counts[status.value] += 1
                except Exception:
                    status_counts["unknown"] += 1

            # Calculate overall health percentage
            healthy_count = status_counts.get("healthy", 0)
            overall_health_percentage = (healthy_count / max(total_instances, 1)) * 100

            overview_data = {
                "total_instances": total_instances,
                "overall_health_percentage": overall_health_percentage,
                "status_distribution": status_counts,
                "timestamp": datetime.now().isoformat(),
                "note": "Based on current running processes. Full metrics require database integration.",
            }

            if output_json:
                click.echo(json.dumps(overview_data, indent=2))
            else:
                click.echo("\n📊 Health Overview:\n")
                click.echo(f"Total Active Processes: {total_instances}")
                click.echo(f"Overall Health: {overall_health_percentage:.1f}%")
                click.echo("(Based on current running processes)")

                click.echo("\nStatus Distribution:")
                for status_name, count in status_counts.items():
                    if count > 0:
                        icon = {
                            "healthy": "🟢",
                            "degraded": "🟡",
                            "unhealthy": "🟠",
                            "critical": "🔴",
                            "unknown": "⚪",
                        }.get(status_name, "❓")
                        percentage = (count / total_instances) * 100
                        click.echo(
                            f"  {icon} {status_name.capitalize()}: {count} ({percentage:.1f}%)"
                        )

        except Exception as e:
            logger.error("Error getting health overview", error=str(e))
            if output_json:
                click.echo(json.dumps({"error": str(e)}))
            else:
                click.echo(f"Error: {e}", err=True)

    asyncio.run(_health_overview())


@health.command()
@click.option(
    "--enable/--disable", default=True, help="Enable or disable health monitoring"
)
@click.option(
    "--interval", type=int, help="Health check interval in seconds (default: 30)"
)
def configure(enable: bool, interval: int | None) -> None:
    """Configure health monitoring settings."""

    async def _configure() -> None:
        try:
            health_monitor = get_health_monitor()

            # Update configuration
            if interval is not None:
                health_monitor.check_interval = float(interval)
                click.echo(f"Health check interval set to {interval} seconds")

            health_monitor.enabled = enable
            status_msg = "enabled" if enable else "disabled"
            click.echo(f"Health monitoring {status_msg}")

            # Restart monitoring with new settings if enabled
            if enable:
                await health_monitor.stop()
                await health_monitor.start()
                click.echo("Health monitoring restarted with new settings")
            else:
                await health_monitor.stop()
                click.echo("Health monitoring stopped")

        except Exception as e:
            logger.error("Error configuring health monitoring", error=str(e))
            click.echo(f"Error: {e}", err=True)

    asyncio.run(_configure())
