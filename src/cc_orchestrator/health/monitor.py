"""Health monitoring system for Claude instances."""

import asyncio
from datetime import datetime, timedelta
from typing import Any

from ..core.instance import ClaudeInstance
from ..utils.logging import LogContext, get_logger
from .alerts import AlertLevel, AlertManager
from .checker import HealthChecker, HealthCheckResult, HealthStatus
from .recovery import RecoveryManager

logger = get_logger(__name__, LogContext.HEALTH)


class HealthMonitor:
    """Monitors health of Claude instances and coordinates recovery."""

    def __init__(
        self,
        check_interval: float = 60.0,  # seconds
        health_checker: HealthChecker | None = None,
        recovery_manager: RecoveryManager | None = None,
        alert_manager: AlertManager | None = None,
    ):
        """Initialize health monitor.

        Args:
            check_interval: Interval between health checks in seconds
            health_checker: Health checker instance (creates default if None)
            recovery_manager: Recovery manager instance (creates default if None)
            alert_manager: Alert manager instance (creates default if None)
        """
        self.check_interval = check_interval
        self.health_checker = health_checker or HealthChecker()
        self.recovery_manager = recovery_manager or RecoveryManager()
        self.alert_manager = alert_manager or AlertManager()

        # Monitoring state
        self._monitoring_tasks: dict[str, asyncio.Task] = {}
        self._health_history: dict[str, list[dict[str, HealthCheckResult]]] = {}
        self._last_alert_time: dict[str, datetime] = {}
        self._shutdown_event = asyncio.Event()

        # Configuration
        self.max_history_entries = 100
        self.alert_cooldown = timedelta(minutes=5)  # Minimum time between alerts

        logger.info("Health monitor initialized", check_interval=check_interval)

    async def start_monitoring(self, instance: ClaudeInstance) -> None:
        """Start monitoring an instance.

        Args:
            instance: Claude instance to monitor
        """
        instance_id = instance.issue_id

        if instance_id in self._monitoring_tasks:
            logger.warning("Instance already being monitored", instance_id=instance_id)
            return

        logger.info("Starting health monitoring", instance_id=instance_id)

        # Create monitoring task
        task = asyncio.create_task(self._monitor_instance(instance))
        self._monitoring_tasks[instance_id] = task

        # Initialize health history
        if instance_id not in self._health_history:
            self._health_history[instance_id] = []

    async def stop_monitoring(self, instance_id: str) -> None:
        """Stop monitoring an instance.

        Args:
            instance_id: Instance identifier
        """
        if instance_id not in self._monitoring_tasks:
            logger.warning("Instance not being monitored", instance_id=instance_id)
            return

        logger.info("Stopping health monitoring", instance_id=instance_id)

        # Cancel monitoring task
        task = self._monitoring_tasks.pop(instance_id)
        if not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        # Clean up state
        self._last_alert_time.pop(instance_id, None)

    async def stop_all_monitoring(self) -> None:
        """Stop monitoring all instances."""
        logger.info(
            "Stopping all health monitoring", instance_count=len(self._monitoring_tasks)
        )

        # Signal shutdown
        self._shutdown_event.set()

        # Cancel all monitoring tasks
        tasks = list(self._monitoring_tasks.values())
        for task in tasks:
            if not task.done():
                task.cancel()

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        # Clear state
        self._monitoring_tasks.clear()
        self._last_alert_time.clear()

        logger.info("All health monitoring stopped")

    async def get_health_status(self, instance_id: str) -> dict[str, Any] | None:
        """Get current health status for an instance.

        Args:
            instance_id: Instance identifier

        Returns:
            Health status information or None if not monitored
        """
        if instance_id not in self._health_history:
            return None

        history = self._health_history[instance_id]
        if not history:
            return None

        # Get most recent health check results
        latest_results = history[-1]
        overall_status = self.health_checker.get_overall_status(latest_results)

        # Calculate health metrics
        total_checks = len(history)
        healthy_checks = sum(
            1
            for results in history
            if self.health_checker.get_overall_status(results) == HealthStatus.HEALTHY
        )

        uptime_percentage = (
            (healthy_checks / total_checks * 100) if total_checks > 0 else 0
        )

        return {
            "instance_id": instance_id,
            "overall_status": overall_status.value,
            "last_check": latest_results,
            "uptime_percentage": uptime_percentage,
            "total_checks": total_checks,
            "healthy_checks": healthy_checks,
            "is_being_monitored": instance_id in self._monitoring_tasks,
        }

    async def get_all_health_status(self) -> dict[str, dict[str, Any]]:
        """Get health status for all monitored instances.

        Returns:
            Dictionary mapping instance IDs to health status
        """
        statuses = {}

        for instance_id in self._health_history:
            status = await self.get_health_status(instance_id)
            if status:
                statuses[instance_id] = status

        return statuses

    async def force_health_check(
        self, instance: ClaudeInstance
    ) -> dict[str, HealthCheckResult]:
        """Force an immediate health check for an instance.

        Args:
            instance: Claude instance to check

        Returns:
            Health check results
        """
        logger.info("Forcing health check", instance_id=instance.issue_id)

        results = await self._perform_health_check(instance)

        # Store results in history
        self._store_health_results(instance.issue_id, results)

        # Determine overall status and handle if unhealthy
        overall_status = self.health_checker.get_overall_status(results)

        # Handle unhealthy status
        if overall_status in [HealthStatus.CRITICAL, HealthStatus.UNHEALTHY]:
            await self._handle_unhealthy_instance(instance, overall_status, results)
        elif overall_status == HealthStatus.DEGRADED:
            await self._handle_degraded_instance(instance, results)

        return results

    async def _monitor_instance(self, instance: ClaudeInstance) -> None:
        """Monitor a single instance continuously.

        Args:
            instance: Claude instance to monitor
        """
        instance_id = instance.issue_id
        logger.debug("Starting instance monitoring loop", instance_id=instance_id)

        try:
            while not self._shutdown_event.is_set():
                try:
                    # Perform health check
                    results = await self._perform_health_check(instance)

                    # Store results
                    self._store_health_results(instance_id, results)

                    # Determine overall status
                    overall_status = self.health_checker.get_overall_status(results)

                    # Handle unhealthy status
                    if overall_status in [
                        HealthStatus.CRITICAL,
                        HealthStatus.UNHEALTHY,
                    ]:
                        await self._handle_unhealthy_instance(
                            instance, overall_status, results
                        )
                    elif overall_status == HealthStatus.DEGRADED:
                        await self._handle_degraded_instance(instance, results)

                    # Log health status
                    logger.debug(
                        "Health check completed",
                        instance_id=instance_id,
                        status=overall_status.value,
                        check_count=len(results),
                    )

                except Exception as e:
                    logger.error(
                        "Error during health monitoring",
                        instance_id=instance_id,
                        error=str(e),
                    )

                # Wait for next check
                try:
                    await asyncio.wait_for(
                        self._shutdown_event.wait(), timeout=self.check_interval
                    )
                    break  # Shutdown event was set
                except TimeoutError:
                    continue  # Normal timeout, continue monitoring

        except asyncio.CancelledError:
            logger.debug("Instance monitoring cancelled", instance_id=instance_id)
            raise
        except Exception as e:
            logger.error(
                "Instance monitoring failed", instance_id=instance_id, error=str(e)
            )
        finally:
            logger.debug("Instance monitoring ended", instance_id=instance_id)

    async def _perform_health_check(
        self, instance: ClaudeInstance
    ) -> dict[str, HealthCheckResult]:
        """Perform health check on an instance.

        Args:
            instance: Claude instance to check

        Returns:
            Health check results
        """
        # Get current instance state
        process_info = await instance.get_process_status()

        # Prepare check parameters
        check_params = {
            "process_info": process_info,
            "tmux_session": instance.tmux_session,
            "workspace_path": instance.workspace_path,
            "instance": instance,
        }

        # Run health checks
        return await self.health_checker.check_health(instance.issue_id, **check_params)

    def _store_health_results(
        self, instance_id: str, results: dict[str, HealthCheckResult]
    ) -> None:
        """Store health check results in history.

        Args:
            instance_id: Instance identifier
            results: Health check results to store
        """
        if instance_id not in self._health_history:
            self._health_history[instance_id] = []

        history = self._health_history[instance_id]
        history.append(results)

        # Limit history size
        if len(history) > self.max_history_entries:
            history.pop(0)

    async def _handle_unhealthy_instance(
        self,
        instance: ClaudeInstance,
        status: HealthStatus,
        results: dict[str, HealthCheckResult],
    ) -> None:
        """Handle an unhealthy instance.

        Args:
            instance: Unhealthy instance
            status: Health status
            results: Health check results
        """
        instance_id = instance.issue_id

        logger.warning(
            "Instance is unhealthy", instance_id=instance_id, status=status.value
        )

        # Send alert if not in cooldown
        await self._send_alert_if_needed(
            instance_id,
            (
                AlertLevel.CRITICAL
                if status == HealthStatus.CRITICAL
                else AlertLevel.WARNING
            ),
            f"Instance {instance_id} is {status.value}",
            {"status": status.value, "results": results},
        )

        # Attempt recovery
        try:
            recovery_needed = await self.recovery_manager.should_recover(
                instance, status, results
            )
            if recovery_needed:
                logger.info("Attempting recovery", instance_id=instance_id)
                success = await self.recovery_manager.recover_instance(
                    instance, status, results
                )

                if success:
                    logger.info("Recovery successful", instance_id=instance_id)
                    await self._send_alert_if_needed(
                        instance_id,
                        AlertLevel.INFO,
                        f"Instance {instance_id} recovered successfully",
                        {"status": "recovered"},
                    )
                else:
                    logger.error("Recovery failed", instance_id=instance_id)
                    await self._send_alert_if_needed(
                        instance_id,
                        AlertLevel.CRITICAL,
                        f"Failed to recover instance {instance_id}",
                        {"status": "recovery_failed"},
                    )
        except Exception as e:
            logger.error(
                "Error during recovery attempt", instance_id=instance_id, error=str(e)
            )

    async def _handle_degraded_instance(
        self, instance: ClaudeInstance, results: dict[str, HealthCheckResult]
    ) -> None:
        """Handle a degraded instance.

        Args:
            instance: Degraded instance
            results: Health check results
        """
        instance_id = instance.issue_id

        logger.info("Instance is degraded", instance_id=instance_id)

        # Send alert if not in cooldown
        await self._send_alert_if_needed(
            instance_id,
            AlertLevel.WARNING,
            f"Instance {instance_id} is degraded",
            {"status": "degraded", "results": results},
        )

    async def _send_alert_if_needed(
        self, instance_id: str, level: AlertLevel, message: str, details: dict[str, Any]
    ) -> None:
        """Send alert if not in cooldown period.

        Args:
            instance_id: Instance identifier
            level: Alert level
            message: Alert message
            details: Additional alert details
        """
        now = datetime.now()
        last_alert = self._last_alert_time.get(instance_id)

        # Check cooldown
        if last_alert and (now - last_alert) < self.alert_cooldown:
            logger.debug(
                "Alert suppressed due to cooldown",
                instance_id=instance_id,
                last_alert=last_alert,
            )
            return

        # Send alert
        await self.alert_manager.send_alert(
            instance_id=instance_id, level=level, message=message, details=details
        )

        # Update last alert time
        self._last_alert_time[instance_id] = now
