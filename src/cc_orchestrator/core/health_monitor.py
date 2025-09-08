"""
Health monitoring service for Claude Code instances.

This module provides comprehensive health monitoring with automatic recovery,
alerting, and configurable health check intervals.
"""

import asyncio
import time
from datetime import datetime
from typing import Any

from ..config.loader import OrchestratorConfig, load_config
from ..database.models import HealthStatus
from ..utils.logging import LogContext, get_logger
from ..utils.process import ProcessStatus, get_process_manager

logger = get_logger(__name__, LogContext.HEALTH)


class AlertSystem:
    """Alert system for health monitoring notifications."""

    def __init__(self) -> None:
        """Initialize the alert system."""
        self.enabled = True

    async def send_alert(
        self,
        level: str,
        message: str,
        instance_id: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Send an alert notification.

        Args:
            level: Alert level (info, warning, error, critical)
            message: Alert message
            instance_id: Instance ID that triggered the alert
            details: Additional alert details
        """
        if not self.enabled:
            return

        alert_data = {
            "timestamp": datetime.now().isoformat(),
            "instance_id": instance_id,
            "details": details or {},
        }

        # Log the alert (could be extended to send to external systems)
        try:
            log_method = getattr(logger, level.lower(), logger.info)
            log_method(
                f"Health alert: {message}",
                alert_level=level,
                **alert_data,
            )
        except Exception as e:
            # Fallback to error logging if alert logging fails
            logger.error(
                f"Failed to log health alert: {message}",
                alert_level=level,
                error=str(e),
                **alert_data,
            )

        # TODO: Add webhook/email/slack notification support based on configuration


class RestartManager:
    """Manages automatic restart attempts with exponential backoff."""

    def __init__(self, config: OrchestratorConfig | None = None) -> None:
        """Initialize the restart manager."""
        if config is None:
            config = load_config()

        self.restart_attempts: dict[str, list[float]] = {}
        self.max_attempts = config.restart_max_attempts
        self.base_delay = config.restart_base_delay
        self.max_delay = config.restart_max_delay

    def can_restart(self, instance_id: str) -> bool:
        """Check if an instance can be restarted.

        Args:
            instance_id: Instance identifier

        Returns:
            True if restart is allowed, False otherwise
        """
        attempts = self.restart_attempts.get(instance_id, [])

        # Remove attempts older than 1 hour
        one_hour_ago = time.time() - 3600
        attempts = [t for t in attempts if t > one_hour_ago]
        self.restart_attempts[instance_id] = attempts

        return len(attempts) < self.max_attempts

    def calculate_delay(self, instance_id: str) -> float:
        """Calculate delay before next restart attempt.

        Args:
            instance_id: Instance identifier

        Returns:
            Delay in seconds
        """
        attempts = self.restart_attempts.get(instance_id, [])

        # Remove attempts older than 1 hour to prevent memory leaks
        one_hour_ago = time.time() - 3600
        attempts = [t for t in attempts if t > one_hour_ago]
        self.restart_attempts[instance_id] = attempts

        attempt_count = len(attempts)

        # Exponential backoff: 2^attempt_count * base_delay
        # 0 attempts: 30s, 1 attempt: 60s, 2 attempts: 120s, etc.
        delay = self.base_delay * (2**attempt_count)

        return min(delay, self.max_delay)

    def record_restart_attempt(self, instance_id: str) -> None:
        """Record a restart attempt.

        Args:
            instance_id: Instance identifier
        """
        if instance_id not in self.restart_attempts:
            self.restart_attempts[instance_id] = []

        self.restart_attempts[instance_id].append(time.time())

    def clear_attempts(self, instance_id: str) -> None:
        """Clear restart attempts for an instance (called on successful restart).

        Args:
            instance_id: Instance identifier
        """
        self.restart_attempts.pop(instance_id, None)


class HealthMonitor:
    """Health monitoring service for Claude Code instances."""

    def __init__(self, config: OrchestratorConfig | None = None) -> None:
        """Initialize the health monitor."""
        if config is None:
            config = load_config()

        self.process_manager = get_process_manager()
        self.alert_system = AlertSystem()
        self.restart_manager = RestartManager(config)
        self.monitoring_task: asyncio.Task | None = None
        self.shutdown_event = asyncio.Event()

        # Configuration from config file/environment
        self.check_interval = config.health_check_interval
        self.enabled = True

        # Health check thresholds from config
        self.cpu_threshold = config.health_cpu_threshold
        self.memory_threshold_mb = config.health_memory_threshold_mb
        self.response_timeout = config.health_response_timeout

        logger.info(
            "Health monitor initialized",
            check_interval=self.check_interval,
            cpu_threshold=self.cpu_threshold,
            memory_threshold_mb=self.memory_threshold_mb,
        )

    async def start(self) -> None:
        """Start the health monitoring daemon."""
        if self.monitoring_task and not self.monitoring_task.done():
            logger.warning("Health monitor is already running")
            return

        logger.info("Starting health monitoring daemon", interval=self.check_interval)
        self.shutdown_event.clear()
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())

    async def stop(self) -> None:
        """Stop the health monitoring daemon."""
        logger.info("Stopping health monitoring daemon")
        self.shutdown_event.set()

        if self.monitoring_task:
            try:
                await asyncio.wait_for(self.monitoring_task, timeout=5.0)
            except TimeoutError:
                logger.warning("Health monitor shutdown timed out, cancelling task")
                self.monitoring_task.cancel()
                try:
                    await self.monitoring_task
                except asyncio.CancelledError:
                    pass

        logger.info("Health monitoring daemon stopped")

    async def check_instance_health(self, instance_id: str) -> dict[str, Any]:
        """Perform a comprehensive health check on an instance.

        Args:
            instance_id: Instance identifier

        Returns:
            Health check results
        """
        start_time = time.time()

        try:
            checks = {}

            # Check process status
            process_info = await self.process_manager.get_process_info(instance_id)
            if process_info:
                checks["process_running"] = process_info.status == ProcessStatus.RUNNING
                checks["process_status"] = process_info.status.value
                checks["cpu_percent"] = process_info.cpu_percent
                checks["memory_mb"] = process_info.memory_mb

                # Check resource thresholds
                checks["cpu_healthy"] = process_info.cpu_percent < self.cpu_threshold
                checks["memory_healthy"] = (
                    process_info.memory_mb < self.memory_threshold_mb
                )
            else:
                checks["process_running"] = False
                checks["process_status"] = "not_found"
                checks["cpu_percent"] = 0.0
                checks["memory_mb"] = 0.0
                checks["cpu_healthy"] = True
                checks["memory_healthy"] = True

            # For now, skip tmux and workspace checks as they require instance data
            # These can be enabled when database integration is added
            checks["tmux_session_active"] = None
            checks["workspace_accessible"] = None

            # Determine overall health status
            overall_status = self._determine_health_status(checks)

            duration_ms = (time.time() - start_time) * 1000

            result = {
                "overall_status": overall_status,
                "checks": checks,
                "duration_ms": duration_ms,
                "timestamp": datetime.now().isoformat(),
            }

            # Log health check result
            logger.debug(
                "Health check completed",
                instance_id=instance_id,
                status=overall_status.value,
                duration_ms=duration_ms,
            )

            return result

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(
                "Health check failed",
                instance_id=instance_id,
                error=str(e),
                duration_ms=duration_ms,
            )

            return {
                "overall_status": HealthStatus.CRITICAL,
                "error": str(e),
                "checks": {},
                "duration_ms": duration_ms,
                "timestamp": datetime.now().isoformat(),
            }

    async def perform_recovery(
        self, instance_id: str, health_result: dict[str, Any]
    ) -> bool:
        """Attempt to recover an unhealthy instance.

        Args:
            instance_id: Instance identifier
            health_result: Health check results

        Returns:
            True if recovery was attempted, False otherwise
        """
        if not self.restart_manager.can_restart(instance_id):
            logger.warning(
                "Maximum restart attempts exceeded for instance",
                instance_id=instance_id,
            )
            await self.alert_system.send_alert(
                level="critical",
                message=f"Instance {instance_id} has exceeded maximum restart attempts",
                instance_id=instance_id,
                details={
                    "restart_attempts": len(
                        self.restart_manager.restart_attempts.get(instance_id, [])
                    )
                },
            )
            return False

        delay = self.restart_manager.calculate_delay(instance_id)
        logger.info(
            "Scheduling instance recovery",
            instance_id=instance_id,
            delay_seconds=delay,
        )

        await self.alert_system.send_alert(
            level="warning",
            message=f"Starting recovery for instance {instance_id} after {delay:.1f}s delay",
            instance_id=instance_id,
            details=health_result,
        )

        # Wait for the calculated delay
        await asyncio.sleep(delay)

        try:
            # Record the restart attempt
            self.restart_manager.record_restart_attempt(instance_id)

            # TODO: Update database when integration is added

            # Attempt restart through process manager
            await self.process_manager.terminate_process(instance_id)
            await asyncio.sleep(2.0)  # Give time for cleanup

            # TODO: Integrate with orchestrator to restart the instance properly
            # For now, we'll just log the attempt
            logger.info("Recovery attempt completed", instance_id=instance_id)

            await self.alert_system.send_alert(
                level="info",
                message=f"Recovery attempt completed for instance {instance_id}",
                instance_id=instance_id,
            )

            return True

        except Exception as e:
            logger.error(
                "Recovery attempt failed",
                instance_id=instance_id,
                error=str(e),
            )

            await self.alert_system.send_alert(
                level="error",
                message=f"Recovery failed for instance {instance_id}: {e}",
                instance_id=instance_id,
                details={"error": str(e)},
            )

            return False

    async def _monitoring_loop(self) -> None:
        """Main monitoring loop that runs continuously."""
        logger.info("Health monitoring loop started")

        try:
            while not self.shutdown_event.is_set():
                try:
                    await self._perform_health_checks()
                except Exception as e:
                    logger.error("Error in health monitoring loop", error=str(e))

                # Wait for next check interval or shutdown
                try:
                    await asyncio.wait_for(
                        self.shutdown_event.wait(), timeout=self.check_interval
                    )
                    # If we reach here, shutdown was requested
                    break
                except TimeoutError:
                    # Timeout is expected, continue with next iteration
                    continue

        except asyncio.CancelledError:
            logger.info("Health monitoring loop cancelled")
            raise
        except Exception as e:
            logger.error("Health monitoring loop failed", error=str(e))
        finally:
            logger.info("Health monitoring loop ended")

    async def _perform_health_checks(self) -> None:
        """Perform health checks on all active instances."""
        try:
            # Get all instances from the process manager
            processes = await self.process_manager.list_processes()

            if not processes:
                logger.debug("No active processes to monitor")
                return

            # Perform health checks concurrently
            health_tasks = [
                self._check_and_update_instance(instance_id)
                for instance_id in processes.keys()
            ]

            if health_tasks:
                await asyncio.gather(*health_tasks, return_exceptions=True)

        except Exception as e:
            logger.error("Error performing health checks", error=str(e))

    async def _check_and_update_instance(self, instance_id: str) -> None:
        """Check health of a single instance."""
        try:
            # Perform health check
            health_result = await self.check_instance_health(instance_id)

            # Log health check results
            logger.info(
                "Health check completed",
                instance_id=instance_id,
                status=health_result["overall_status"].value,
                duration_ms=health_result["duration_ms"],
            )

            # Check if recovery is needed
            status = health_result["overall_status"]
            if status in [HealthStatus.CRITICAL, HealthStatus.UNHEALTHY]:
                await self.perform_recovery(instance_id, health_result)
            elif status == HealthStatus.DEGRADED:
                # For degraded status, send alert but don't restart
                await self.alert_system.send_alert(
                    level="warning",
                    message=f"Instance {instance_id} is in degraded state",
                    instance_id=instance_id,
                    details=health_result,
                )
            elif status == HealthStatus.HEALTHY:
                # Clear restart attempts on successful health check
                self.restart_manager.clear_attempts(instance_id)
            else:
                # Handle unexpected status (UNKNOWN, etc.)
                logger.warning(
                    f"Unexpected health status: {status.value}",
                    instance_id=instance_id,
                    status=status.value,
                )

        except Exception as e:
            logger.error(
                "Error checking instance health",
                instance_id=instance_id,
                error=str(e),
            )

    async def _check_tmux_session(self, session_name: str) -> bool:
        """Check if a tmux session is active.

        Args:
            session_name: Tmux session name

        Returns:
            True if session is active, False otherwise
        """
        try:
            import re
            import subprocess

            # Input validation: only allow alphanumeric characters, hyphens, and underscores
            if not re.match(r"^[a-zA-Z0-9_-]+$", session_name):
                logger.warning(
                    "Invalid tmux session name format", session_name=session_name
                )
                return False

            result = subprocess.run(
                ["tmux", "list-sessions", "-f", f"#{session_name}"],
                capture_output=True,
                text=True,
                timeout=5.0,
            )

            return result.returncode == 0 and session_name in result.stdout

        except (subprocess.SubprocessError, subprocess.TimeoutExpired):
            return False

    async def _check_workspace_accessible(self, workspace_path: str) -> bool:
        """Check if workspace directory is accessible.

        Args:
            workspace_path: Path to workspace directory

        Returns:
            True if accessible, False otherwise
        """
        try:
            from pathlib import Path

            path = Path(workspace_path)
            return path.exists() and path.is_dir()

        except Exception:
            return False

    def _determine_health_status(self, checks: dict[str, Any]) -> HealthStatus:
        """Determine overall health status from individual checks.

        Args:
            checks: Dictionary of check results

        Returns:
            Overall health status
        """
        # Critical: process not running
        if not checks.get("process_running", False):
            return HealthStatus.CRITICAL

        # Critical: resource thresholds exceeded
        if not checks.get("cpu_healthy", True) or not checks.get(
            "memory_healthy", True
        ):
            return HealthStatus.CRITICAL

        # Degraded: optional checks failing
        tmux_active = checks.get("tmux_session_active")
        workspace_accessible = checks.get("workspace_accessible")

        if tmux_active is False or workspace_accessible is False:
            return HealthStatus.DEGRADED

        # Healthy: all checks passing
        return HealthStatus.HEALTHY


# Global health monitor instance
_health_monitor: HealthMonitor | None = None


def get_health_monitor(config: OrchestratorConfig | None = None) -> HealthMonitor:
    """Get the global health monitor instance.

    Args:
        config: Optional configuration to use for initialization

    Returns:
        HealthMonitor instance
    """
    global _health_monitor
    if _health_monitor is None:
        _health_monitor = HealthMonitor(config)
    return _health_monitor


async def cleanup_health_monitor() -> None:
    """Clean up the global health monitor."""
    global _health_monitor
    if _health_monitor is not None:
        await _health_monitor.stop()
        _health_monitor = None
