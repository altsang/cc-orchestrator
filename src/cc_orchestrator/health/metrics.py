"""Performance metrics collection and analysis for health monitoring."""

import asyncio
import statistics
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta

import psutil

from ..utils.logging import LogContext, get_logger

logger = get_logger(__name__, LogContext.HEALTH)


@dataclass
class PerformanceMetrics:
    """Performance metrics for an instance."""

    instance_id: str
    timestamp: datetime

    # Process metrics
    cpu_percent: float = 0.0
    memory_mb: float = 0.0
    memory_percent: float = 0.0

    # System metrics
    system_cpu_percent: float = 0.0
    system_memory_percent: float = 0.0
    system_disk_percent: float = 0.0

    # Network metrics (if available)
    network_bytes_sent: int = 0
    network_bytes_recv: int = 0

    # Health check metrics
    health_check_duration_ms: float = 0.0
    health_check_success: bool = True

    # Custom metrics
    custom_metrics: dict[str, float] = field(default_factory=dict)


@dataclass
class MetricsSummary:
    """Summary statistics for metrics over a time period."""

    instance_id: str
    start_time: datetime
    end_time: datetime
    sample_count: int

    # CPU statistics
    cpu_avg: float = 0.0
    cpu_min: float = 0.0
    cpu_max: float = 0.0
    cpu_p95: float = 0.0

    # Memory statistics
    memory_avg: float = 0.0
    memory_min: float = 0.0
    memory_max: float = 0.0
    memory_p95: float = 0.0

    # Health check statistics
    health_check_success_rate: float = 0.0
    health_check_avg_duration: float = 0.0

    # Uptime
    uptime_percentage: float = 0.0


class MetricsCollector:
    """Collects and analyzes performance metrics for instances."""

    def __init__(self, max_samples: int = 1000, collection_interval: float = 30.0):
        """Initialize metrics collector.

        Args:
            max_samples: Maximum number of samples to keep per instance
            collection_interval: Interval between metric collections in seconds
        """
        self.max_samples = max_samples
        self.collection_interval = collection_interval

        # Storage for metrics
        self._metrics: dict[str, deque] = defaultdict(lambda: deque(maxlen=max_samples))
        self._collection_tasks: dict[str, asyncio.Task] = {}
        self._shutdown_event = asyncio.Event()

        # Network baseline for delta calculations
        self._network_baseline: dict[str, tuple[int, int]] = {}

        logger.info("Metrics collector initialized", max_samples=max_samples)

    async def start_collection(
        self, instance_id: str, process_id: int | None = None
    ) -> None:
        """Start collecting metrics for an instance.

        Args:
            instance_id: Instance identifier
            process_id: Process ID to monitor (if None, will try to find it)
        """
        if instance_id in self._collection_tasks:
            logger.warning(
                "Metrics collection already running", instance_id=instance_id
            )
            return

        logger.info("Starting metrics collection", instance_id=instance_id)

        task = asyncio.create_task(self._collect_metrics_loop(instance_id, process_id))
        self._collection_tasks[instance_id] = task

    async def stop_collection(self, instance_id: str) -> None:
        """Stop collecting metrics for an instance.

        Args:
            instance_id: Instance identifier
        """
        if instance_id not in self._collection_tasks:
            logger.warning("Metrics collection not running", instance_id=instance_id)
            return

        logger.info("Stopping metrics collection", instance_id=instance_id)

        task = self._collection_tasks.pop(instance_id)
        if not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        # Clean up baseline
        self._network_baseline.pop(instance_id, None)

    async def stop_all_collection(self) -> None:
        """Stop collecting metrics for all instances."""
        logger.info("Stopping all metrics collection")

        self._shutdown_event.set()

        tasks = list(self._collection_tasks.values())
        for task in tasks:
            if not task.done():
                task.cancel()

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        self._collection_tasks.clear()
        self._network_baseline.clear()

    async def collect_snapshot(
        self, instance_id: str, process_id: int | None = None
    ) -> PerformanceMetrics | None:
        """Collect a single metrics snapshot.

        Args:
            instance_id: Instance identifier
            process_id: Process ID to monitor

        Returns:
            PerformanceMetrics snapshot or None if collection failed
        """
        try:
            metrics = PerformanceMetrics(
                instance_id=instance_id, timestamp=datetime.now()
            )

            # Collect system metrics
            metrics.system_cpu_percent = psutil.cpu_percent()
            system_memory = psutil.virtual_memory()
            metrics.system_memory_percent = system_memory.percent

            # Collect disk usage for root partition
            disk_usage = psutil.disk_usage("/")
            metrics.system_disk_percent = (disk_usage.used / disk_usage.total) * 100

            # Collect process metrics if process_id is available
            if process_id:
                try:
                    process = psutil.Process(process_id)

                    # CPU and memory
                    metrics.cpu_percent = process.cpu_percent()
                    memory_info = process.memory_info()
                    metrics.memory_mb = memory_info.rss / 1024 / 1024
                    metrics.memory_percent = process.memory_percent()

                    # Network I/O (if available)
                    try:
                        network_io = process.io_counters()
                        if instance_id in self._network_baseline:
                            baseline_sent, baseline_recv = self._network_baseline[
                                instance_id
                            ]
                            metrics.network_bytes_sent = (
                                network_io.write_bytes - baseline_sent
                            )
                            metrics.network_bytes_recv = (
                                network_io.read_bytes - baseline_recv
                            )
                        else:
                            # Set baseline
                            self._network_baseline[instance_id] = (
                                network_io.write_bytes,
                                network_io.read_bytes,
                            )
                    except (AttributeError, psutil.AccessDenied):
                        # Network I/O not available on all platforms
                        pass

                except psutil.NoSuchProcess:
                    logger.warning(
                        "Process not found for metrics",
                        instance_id=instance_id,
                        pid=process_id,
                    )
                except psutil.AccessDenied:
                    logger.warning(
                        "Access denied for process metrics",
                        instance_id=instance_id,
                        pid=process_id,
                    )

            return metrics

        except Exception as e:
            logger.error(
                "Failed to collect metrics snapshot",
                instance_id=instance_id,
                error=str(e),
            )
            return None

    def add_metrics(self, metrics: PerformanceMetrics) -> None:
        """Add metrics to the collection.

        Args:
            metrics: Performance metrics to add
        """
        self._metrics[metrics.instance_id].append(metrics)

        logger.debug(
            "Metrics added",
            instance_id=metrics.instance_id,
            cpu_percent=metrics.cpu_percent,
            memory_mb=metrics.memory_mb,
        )

    def get_latest_metrics(self, instance_id: str) -> PerformanceMetrics | None:
        """Get the latest metrics for an instance.

        Args:
            instance_id: Instance identifier

        Returns:
            Latest PerformanceMetrics or None if no metrics available
        """
        metrics_deque = self._metrics.get(instance_id)
        if not metrics_deque:
            return None

        return metrics_deque[-1]

    def get_metrics_history(
        self, instance_id: str, limit: int | None = None, since: datetime | None = None
    ) -> list[PerformanceMetrics]:
        """Get metrics history for an instance.

        Args:
            instance_id: Instance identifier
            limit: Maximum number of metrics to return
            since: Only return metrics since this time

        Returns:
            List of PerformanceMetrics
        """
        metrics_deque = self._metrics.get(instance_id, deque())
        metrics_list = list(metrics_deque)

        # Filter by time if specified
        if since:
            metrics_list = [m for m in metrics_list if m.timestamp >= since]

        # Sort by timestamp (newest first)
        metrics_list.sort(key=lambda x: x.timestamp, reverse=True)

        # Apply limit
        if limit:
            metrics_list = metrics_list[:limit]

        return metrics_list

    def get_metrics_summary(
        self, instance_id: str, duration: timedelta = timedelta(hours=1)
    ) -> MetricsSummary | None:
        """Generate summary statistics for metrics over a time period.

        Args:
            instance_id: Instance identifier
            duration: Time period to analyze

        Returns:
            MetricsSummary or None if insufficient data
        """
        end_time = datetime.now()
        start_time = end_time - duration

        # Get metrics in time range
        metrics_list = self.get_metrics_history(instance_id, since=start_time)

        if not metrics_list:
            return None

        # Extract values for analysis
        cpu_values = [m.cpu_percent for m in metrics_list if m.cpu_percent > 0]
        memory_values = [m.memory_mb for m in metrics_list if m.memory_mb > 0]
        health_check_durations = [
            m.health_check_duration_ms
            for m in metrics_list
            if m.health_check_duration_ms > 0
        ]
        health_check_successes = [m.health_check_success for m in metrics_list]

        summary = MetricsSummary(
            instance_id=instance_id,
            start_time=start_time,
            end_time=end_time,
            sample_count=len(metrics_list),
        )

        # CPU statistics
        if cpu_values:
            summary.cpu_avg = statistics.mean(cpu_values)
            summary.cpu_min = min(cpu_values)
            summary.cpu_max = max(cpu_values)
            if len(cpu_values) >= 20:  # Need sufficient samples for percentile
                summary.cpu_p95 = statistics.quantiles(cpu_values, n=20)[-1]

        # Memory statistics
        if memory_values:
            summary.memory_avg = statistics.mean(memory_values)
            summary.memory_min = min(memory_values)
            summary.memory_max = max(memory_values)
            if len(memory_values) >= 20:
                summary.memory_p95 = statistics.quantiles(memory_values, n=20)[-1]

        # Health check statistics
        if health_check_successes:
            success_count = sum(health_check_successes)
            summary.health_check_success_rate = (
                success_count / len(health_check_successes)
            ) * 100

        if health_check_durations:
            summary.health_check_avg_duration = statistics.mean(health_check_durations)

        # Calculate uptime (simplified - based on successful health checks)
        if health_check_successes:
            summary.uptime_percentage = summary.health_check_success_rate

        return summary

    def clear_metrics(self, instance_id: str) -> None:
        """Clear metrics for an instance.

        Args:
            instance_id: Instance identifier
        """
        if instance_id in self._metrics:
            self._metrics[instance_id].clear()
            logger.info("Metrics cleared", instance_id=instance_id)

    def get_all_instance_ids(self) -> list[str]:
        """Get all instance IDs that have metrics.

        Returns:
            List of instance IDs
        """
        return list(self._metrics.keys())

    async def _collect_metrics_loop(
        self, instance_id: str, process_id: int | None
    ) -> None:
        """Continuously collect metrics for an instance.

        Args:
            instance_id: Instance identifier
            process_id: Process ID to monitor
        """
        logger.debug("Starting metrics collection loop", instance_id=instance_id)

        try:
            while not self._shutdown_event.is_set():
                try:
                    # Collect metrics snapshot
                    metrics = await self.collect_snapshot(instance_id, process_id)
                    if metrics:
                        self.add_metrics(metrics)

                except Exception as e:
                    logger.error(
                        "Error collecting metrics",
                        instance_id=instance_id,
                        error=str(e),
                    )

                # Wait for next collection
                try:
                    await asyncio.wait_for(
                        self._shutdown_event.wait(), timeout=self.collection_interval
                    )
                    break  # Shutdown event was set
                except TimeoutError:
                    continue  # Normal timeout, continue collecting

        except asyncio.CancelledError:
            logger.debug("Metrics collection cancelled", instance_id=instance_id)
            raise
        except Exception as e:
            logger.error(
                "Metrics collection failed", instance_id=instance_id, error=str(e)
            )
        finally:
            logger.debug("Metrics collection ended", instance_id=instance_id)


# Global metrics collector instance
_metrics_collector: MetricsCollector | None = None


def get_metrics_collector() -> MetricsCollector:
    """Get the global metrics collector instance.

    Returns:
        MetricsCollector instance
    """
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector


async def cleanup_metrics_collector() -> None:
    """Clean up the global metrics collector."""
    global _metrics_collector
    if _metrics_collector is not None:
        await _metrics_collector.stop_all_collection()
        _metrics_collector = None
