"""Health monitoring CLI commands."""

import asyncio
import json

import click

from ..health.config import (
    get_health_monitoring_settings,
    save_health_monitoring_config,
)
from ..health.integration import get_health_monitoring_integration
from ..utils.logging import LogContext, get_logger

logger = get_logger(__name__, LogContext.CLI)


@click.group()
def health() -> None:
    """Health monitoring commands."""
    pass


@health.command()
@click.argument("instance_id")
@click.option("--json", "output_json", is_flag=True, help="Output in JSON format")
def status(instance_id: str, output_json: bool) -> None:
    """Get health status for an instance."""

    async def _status():
        try:
            integration = get_health_monitoring_integration()

            if not integration.is_monitoring_enabled():
                message = "Health monitoring is disabled"
                if output_json:
                    click.echo(json.dumps({"error": message}))
                else:
                    click.echo(f"Error: {message}")
                return

            if not integration.is_instance_monitored(instance_id):
                message = f"Instance {instance_id} is not being monitored"
                if output_json:
                    click.echo(
                        json.dumps({"error": message, "instance_id": instance_id})
                    )
                else:
                    click.echo(f"Error: {message}")
                return

            # Get health status
            health_status = await integration.get_instance_health_status(instance_id)
            if not health_status:
                message = f"No health data available for instance {instance_id}"
                if output_json:
                    click.echo(
                        json.dumps({"error": message, "instance_id": instance_id})
                    )
                else:
                    click.echo(f"Error: {message}")
                return

            if output_json:
                click.echo(json.dumps(health_status, indent=2))
            else:
                # Human-readable output
                click.echo(f"\nHealth Status for Instance: {instance_id}\n")
                click.echo(f"Overall Status: {health_status['overall_status'].upper()}")
                click.echo(f"Uptime: {health_status['uptime_percentage']:.1f}%")
                click.echo(f"Total Checks: {health_status['total_checks']}")
                click.echo(f"Healthy Checks: {health_status['healthy_checks']}")
                click.echo(f"Monitoring Active: {health_status['is_being_monitored']}")

                if health_status["last_check"]:
                    click.echo("\nLast Health Check Results:")
                    for check_name, result in health_status["last_check"].items():
                        status_icon = "✅" if result["status"] == "healthy" else "❌"
                        click.echo(f"  {status_icon} {check_name}: {result['message']}")
                        if result.get("details"):
                            for key, value in result["details"].items():
                                click.echo(f"    {key}: {value}")

        except Exception as e:
            logger.error(
                "Error getting health status", instance_id=instance_id, error=str(e)
            )
            if output_json:
                click.echo(json.dumps({"error": str(e), "instance_id": instance_id}))
            else:
                click.echo(f"Error: {e}", err=True)

    asyncio.run(_status())


@health.command("list")
@click.option("--json", "output_json", is_flag=True, help="Output in JSON format")
def list_health(output_json: bool) -> None:
    """List health status for all monitored instances."""

    async def _list():
        try:
            integration = get_health_monitoring_integration()

            if not integration.is_monitoring_enabled():
                message = "Health monitoring is disabled"
                if output_json:
                    click.echo(json.dumps({"error": message}))
                else:
                    click.echo(f"Error: {message}")
                return

            # Get all health status
            all_status = await integration.get_all_health_status()

            if not all_status:
                if output_json:
                    click.echo(json.dumps({"instances": [], "total": 0}))
                else:
                    click.echo("No instances are being monitored.")
                return

            if output_json:
                click.echo(
                    json.dumps(
                        {"instances": all_status, "total": len(all_status)}, indent=2
                    )
                )
            else:
                # Human-readable output
                click.echo(f"\nHealth Status Summary ({len(all_status)} instances):\n")

                for instance_id, status in all_status.items():
                    status_icon = {
                        "healthy": "🟢",
                        "degraded": "🟡",
                        "unhealthy": "🟠",
                        "critical": "🔴",
                        "unknown": "⚪",
                    }.get(status["overall_status"], "⚪")

                    click.echo(f"{status_icon} {instance_id}")
                    click.echo(f"   Status: {status['overall_status'].upper()}")
                    click.echo(f"   Uptime: {status['uptime_percentage']:.1f}%")
                    click.echo(
                        f"   Checks: {status['healthy_checks']}/{status['total_checks']}"
                    )
                    click.echo()

        except Exception as e:
            logger.error("Error listing health status", error=str(e))
            if output_json:
                click.echo(json.dumps({"error": str(e)}))
            else:
                click.echo(f"Error: {e}", err=True)

    asyncio.run(_list())


@health.command("check")
@click.argument("instance_id")
@click.option("--json", "output_json", is_flag=True, help="Output in JSON format")
def force_check(instance_id: str, output_json: bool) -> None:
    """Force an immediate health check for an instance."""

    async def _check():
        try:
            integration = get_health_monitoring_integration()

            if not integration.is_monitoring_enabled():
                message = "Health monitoring is disabled"
                if output_json:
                    click.echo(json.dumps({"error": message}))
                else:
                    click.echo(f"Error: {message}")
                return

            if not integration.is_instance_monitored(instance_id):
                message = f"Instance {instance_id} is not being monitored"
                if output_json:
                    click.echo(
                        json.dumps({"error": message, "instance_id": instance_id})
                    )
                else:
                    click.echo(f"Error: {message}")
                return

            # Force health check
            results = await integration.force_health_check(instance_id)

            if output_json:
                click.echo(
                    json.dumps(
                        {"instance_id": instance_id, "results": results}, indent=2
                    )
                )
            else:
                # Human-readable output
                click.echo(f"\nHealth Check Results for: {instance_id}\n")

                for check_name, result in results.items():
                    status_icon = {
                        "healthy": "✅",
                        "degraded": "⚠️",
                        "unhealthy": "❌",
                        "critical": "🚨",
                        "unknown": "❓",
                    }.get(result["status"], "❓")

                    click.echo(f"{status_icon} {check_name.upper()}")
                    click.echo(f"   Status: {result['status'].upper()}")
                    click.echo(f"   Message: {result['message']}")
                    click.echo(f"   Duration: {result['duration_ms']:.1f}ms")

                    if result.get("details"):
                        click.echo("   Details:")
                        for key, value in result["details"].items():
                            click.echo(f"     {key}: {value}")
                    click.echo()

        except Exception as e:
            logger.error(
                "Error forcing health check", instance_id=instance_id, error=str(e)
            )
            if output_json:
                click.echo(json.dumps({"error": str(e), "instance_id": instance_id}))
            else:
                click.echo(f"Error: {e}", err=True)

    asyncio.run(_check())


@health.command()
@click.argument("instance_id")
@click.option("--limit", type=int, default=10, help="Maximum number of metrics to show")
@click.option("--json", "output_json", is_flag=True, help="Output in JSON format")
def metrics(instance_id: str, limit: int, output_json: bool) -> None:
    """Get performance metrics for an instance."""

    try:
        integration = get_health_monitoring_integration()

        if not integration.is_monitoring_enabled():
            message = "Health monitoring is disabled"
            if output_json:
                click.echo(json.dumps({"error": message}))
            else:
                click.echo(f"Error: {message}")
            return

        if not integration.is_instance_monitored(instance_id):
            message = f"Instance {instance_id} is not being monitored"
            if output_json:
                click.echo(json.dumps({"error": message, "instance_id": instance_id}))
            else:
                click.echo(f"Error: {message}")
            return

        # Get metrics
        metrics_data = integration.get_instance_metrics(instance_id, limit=limit)

        if output_json:
            click.echo(
                json.dumps(
                    {"instance_id": instance_id, "metrics": metrics_data}, indent=2
                )
            )
        else:
            # Human-readable output
            click.echo(f"\nPerformance Metrics for: {instance_id}\n")

            if metrics_data.get("latest"):
                latest = metrics_data["latest"]
                click.echo("Latest Metrics:")
                click.echo(f"  Timestamp: {latest['timestamp']}")
                click.echo(f"  CPU: {latest['cpu_percent']:.1f}%")
                click.echo(
                    f"  Memory: {latest['memory_mb']:.1f} MB ({latest['memory_percent']:.1f}%)"
                )
                click.echo(f"  System CPU: {latest['system_cpu_percent']:.1f}%")
                click.echo(f"  System Memory: {latest['system_memory_percent']:.1f}%")
                click.echo(f"  System Disk: {latest['system_disk_percent']:.1f}%")
                click.echo()

            if metrics_data.get("summary"):
                summary = metrics_data["summary"]
                click.echo("Summary Statistics:")
                click.echo(f"  Sample Count: {summary['sample_count']}")
                click.echo(f"  Average CPU: {summary['cpu_avg']:.1f}%")
                click.echo(f"  Peak CPU: {summary['cpu_max']:.1f}%")
                click.echo(f"  Average Memory: {summary['memory_avg']:.1f} MB")
                click.echo(f"  Peak Memory: {summary['memory_max']:.1f} MB")
                click.echo(f"  Uptime: {summary['uptime_percentage']:.1f}%")
                click.echo()

            click.echo(f"History Count: {metrics_data['history_count']}")

    except Exception as e:
        logger.error("Error getting metrics", instance_id=instance_id, error=str(e))
        if output_json:
            click.echo(json.dumps({"error": str(e), "instance_id": instance_id}))
        else:
            click.echo(f"Error: {e}", err=True)


@health.command()
@click.option("--json", "output_json", is_flag=True, help="Output in JSON format")
def config(output_json: bool) -> None:
    """Show current health monitoring configuration."""

    try:
        settings = get_health_monitoring_settings()

        if output_json:
            click.echo(json.dumps(settings.config.dict(), indent=2))
        else:
            # Human-readable output
            config = settings.config
            click.echo("\nHealth Monitoring Configuration:\n")

            click.echo(f"Enabled: {config.enabled}")
            click.echo(f"Check Interval: {config.check_interval}s")
            click.echo()

            click.echo("Health Checks:")
            click.echo(
                f"  Process Check: {'✅' if config.process_check.enabled else '❌'}"
            )
            click.echo(f"  Tmux Check: {'✅' if config.tmux_check.enabled else '❌'}")
            click.echo(
                f"  Workspace Check: {'✅' if config.workspace_check.enabled else '❌'}"
            )
            click.echo(
                f"  Response Check: {'✅' if config.response_check.enabled else '❌'}"
            )
            click.echo()

            click.echo("Recovery:")
            click.echo(f"  Enabled: {'✅' if config.recovery.enabled else '❌'}")
            click.echo(f"  Max Attempts: {config.recovery.max_attempts}")
            click.echo(f"  Base Delay: {config.recovery.base_delay}s")
            click.echo()

            click.echo("Alerts:")
            click.echo(f"  Enabled: {'✅' if config.alerts.enabled else '❌'}")
            click.echo(f"  Cooldown: {config.alerts.cooldown_minutes}m")
            click.echo(f"  Log Alerts: {'✅' if config.alerts.log_alerts else '❌'}")
            click.echo(f"  File Alerts: {'✅' if config.alerts.file_alerts else '❌'}")
            click.echo()

            click.echo("Metrics:")
            click.echo(f"  Enabled: {'✅' if config.metrics.enabled else '❌'}")
            click.echo(f"  Collection Interval: {config.metrics.collection_interval}s")
            click.echo(f"  Max Samples: {config.metrics.max_samples}")

    except Exception as e:
        logger.error("Error getting health config", error=str(e))
        if output_json:
            click.echo(json.dumps({"error": str(e)}))
        else:
            click.echo(f"Error: {e}", err=True)


@health.command("enable")
def enable() -> None:
    """Enable health monitoring."""

    try:
        settings = get_health_monitoring_settings()
        settings.config.enabled = True

        # Save config if file path is available
        if settings.config_file_path:
            save_health_monitoring_config(settings, settings.config_file_path)

        click.echo("Health monitoring enabled.")

    except Exception as e:
        logger.error("Error enabling health monitoring", error=str(e))
        click.echo(f"Error: {e}", err=True)


@health.command("disable")
def disable() -> None:
    """Disable health monitoring."""

    try:
        settings = get_health_monitoring_settings()
        settings.config.enabled = False

        # Save config if file path is available
        if settings.config_file_path:
            save_health_monitoring_config(settings, settings.config_file_path)

        click.echo("Health monitoring disabled.")

    except Exception as e:
        logger.error("Error disabling health monitoring", error=str(e))
        click.echo(f"Error: {e}", err=True)
