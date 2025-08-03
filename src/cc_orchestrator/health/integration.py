"""Integration of health monitoring with Claude instances."""

from ..core.instance import ClaudeInstance
from ..utils.logging import LogContext, get_logger
from .config import get_health_monitoring_settings
from .metrics import get_metrics_collector
from .monitor import HealthMonitor

logger = get_logger(__name__, LogContext.HEALTH)


class HealthMonitoringIntegration:
    """Integrates health monitoring with Claude instance management."""

    def __init__(self):
        """Initialize health monitoring integration."""
        self.settings = get_health_monitoring_settings()
        self.health_monitor = HealthMonitor(
            check_interval=self.settings.config.check_interval
        )
        self.metrics_collector = get_metrics_collector()
        self._monitored_instances: dict[str, ClaudeInstance] = {}

        logger.info("Health monitoring integration initialized")

    async def start_monitoring_instance(self, instance: ClaudeInstance) -> None:
        """Start monitoring a Claude instance.

        Args:
            instance: Claude instance to monitor
        """
        if not self.settings.config.enabled:
            logger.debug("Health monitoring disabled", instance_id=instance.issue_id)
            return

        instance_id = instance.issue_id

        if instance_id in self._monitored_instances:
            logger.warning("Instance already being monitored", instance_id=instance_id)
            return

        logger.info("Starting health monitoring for instance", instance_id=instance_id)

        try:
            # Store instance reference
            self._monitored_instances[instance_id] = instance

            # Start health monitoring
            await self.health_monitor.start_monitoring(instance)

            # Start metrics collection if enabled
            if self.settings.config.metrics.enabled:
                process_info = await instance.get_process_status()
                process_id = process_info.pid if process_info else None
                await self.metrics_collector.start_collection(instance_id, process_id)

            logger.info("Health monitoring started", instance_id=instance_id)

        except Exception as e:
            logger.error(
                "Failed to start health monitoring",
                instance_id=instance_id,
                error=str(e),
            )
            # Clean up on failure
            await self._cleanup_instance_monitoring(instance_id)
            raise

    async def stop_monitoring_instance(self, instance_id: str) -> None:
        """Stop monitoring a Claude instance.

        Args:
            instance_id: Instance identifier
        """
        if instance_id not in self._monitored_instances:
            logger.warning("Instance not being monitored", instance_id=instance_id)
            return

        logger.info("Stopping health monitoring for instance", instance_id=instance_id)

        await self._cleanup_instance_monitoring(instance_id)

        logger.info("Health monitoring stopped", instance_id=instance_id)

    async def stop_all_monitoring(self) -> None:
        """Stop monitoring all instances."""
        logger.info("Stopping all health monitoring")

        # Stop health monitoring
        await self.health_monitor.stop_all_monitoring()

        # Stop metrics collection
        await self.metrics_collector.stop_all_collection()

        # Clear tracked instances
        self._monitored_instances.clear()

        logger.info("All health monitoring stopped")

    async def force_health_check(self, instance_id: str) -> dict | None:
        """Force an immediate health check for an instance.

        Args:
            instance_id: Instance identifier

        Returns:
            Health check results or None if instance not monitored
        """
        if instance_id not in self._monitored_instances:
            logger.warning("Instance not being monitored", instance_id=instance_id)
            return None

        instance = self._monitored_instances[instance_id]
        results = await self.health_monitor.force_health_check(instance)

        # Convert results to serializable format
        return {
            check_name: {
                "status": result.status.value,
                "message": result.message,
                "details": result.details,
                "timestamp": result.timestamp.isoformat(),
                "duration_ms": result.duration_ms,
            }
            for check_name, result in results.items()
        }

    async def get_instance_health_status(self, instance_id: str) -> dict | None:
        """Get health status for an instance.

        Args:
            instance_id: Instance identifier

        Returns:
            Health status information or None if not monitored
        """
        return await self.health_monitor.get_health_status(instance_id)

    async def get_all_health_status(self) -> dict[str, dict]:
        """Get health status for all monitored instances.

        Returns:
            Dictionary mapping instance IDs to health status
        """
        return await self.health_monitor.get_all_health_status()

    def get_instance_metrics(self, instance_id: str, limit: int | None = None) -> dict:
        """Get performance metrics for an instance.

        Args:
            instance_id: Instance identifier
            limit: Maximum number of metrics to return

        Returns:
            Metrics information
        """
        if not self.settings.config.metrics.enabled:
            return {"error": "Metrics collection disabled"}

        # Get latest metrics
        latest = self.metrics_collector.get_latest_metrics(instance_id)

        # Get metrics history
        history = self.metrics_collector.get_metrics_history(instance_id, limit=limit)

        # Get metrics summary
        summary = self.metrics_collector.get_metrics_summary(instance_id)

        return {
            "latest": (
                {
                    "timestamp": latest.timestamp.isoformat(),
                    "cpu_percent": latest.cpu_percent,
                    "memory_mb": latest.memory_mb,
                    "memory_percent": latest.memory_percent,
                    "system_cpu_percent": latest.system_cpu_percent,
                    "system_memory_percent": latest.system_memory_percent,
                    "system_disk_percent": latest.system_disk_percent,
                }
                if latest
                else None
            ),
            "history_count": len(history),
            "summary": (
                {
                    "sample_count": summary.sample_count,
                    "cpu_avg": summary.cpu_avg,
                    "cpu_max": summary.cpu_max,
                    "memory_avg": summary.memory_avg,
                    "memory_max": summary.memory_max,
                    "uptime_percentage": summary.uptime_percentage,
                }
                if summary
                else None
            ),
        }

    def is_monitoring_enabled(self) -> bool:
        """Check if health monitoring is enabled.

        Returns:
            True if monitoring is enabled
        """
        return self.settings.config.enabled

    def is_instance_monitored(self, instance_id: str) -> bool:
        """Check if an instance is being monitored.

        Args:
            instance_id: Instance identifier

        Returns:
            True if instance is monitored
        """
        return instance_id in self._monitored_instances

    def get_monitored_instance_ids(self) -> list[str]:
        """Get list of monitored instance IDs.

        Returns:
            List of instance IDs
        """
        return list(self._monitored_instances.keys())

    async def update_settings(self, new_settings) -> None:
        """Update health monitoring settings.

        Args:
            new_settings: New HealthMonitoringSettings
        """
        old_enabled = self.settings.config.enabled
        self.settings = new_settings

        # If monitoring was disabled, stop all monitoring
        if old_enabled and not new_settings.config.enabled:
            await self.stop_all_monitoring()

        # If monitoring was enabled, restart with new settings
        elif new_settings.config.enabled:
            # Update monitor settings
            self.health_monitor.check_interval = new_settings.config.check_interval

            # Update metrics collector settings
            self.metrics_collector.collection_interval = (
                new_settings.config.metrics.collection_interval
            )
            self.metrics_collector.max_samples = new_settings.config.metrics.max_samples

        logger.info("Health monitoring settings updated")

    async def _cleanup_instance_monitoring(self, instance_id: str) -> None:
        """Clean up monitoring for an instance.

        Args:
            instance_id: Instance identifier
        """
        try:
            # Stop health monitoring
            await self.health_monitor.stop_monitoring(instance_id)
        except Exception as e:
            logger.error(
                "Error stopping health monitoring",
                instance_id=instance_id,
                error=str(e),
            )

        try:
            # Stop metrics collection
            await self.metrics_collector.stop_collection(instance_id)
        except Exception as e:
            logger.error(
                "Error stopping metrics collection",
                instance_id=instance_id,
                error=str(e),
            )

        # Remove from tracked instances
        self._monitored_instances.pop(instance_id, None)


# Global integration instance
_health_monitoring_integration: HealthMonitoringIntegration | None = None


def get_health_monitoring_integration() -> HealthMonitoringIntegration:
    """Get the global health monitoring integration instance.

    Returns:
        HealthMonitoringIntegration instance
    """
    global _health_monitoring_integration
    if _health_monitoring_integration is None:
        _health_monitoring_integration = HealthMonitoringIntegration()
    return _health_monitoring_integration


async def cleanup_health_monitoring_integration() -> None:
    """Clean up the global health monitoring integration."""
    global _health_monitoring_integration
    if _health_monitoring_integration is not None:
        await _health_monitoring_integration.stop_all_monitoring()
        _health_monitoring_integration = None
