"""Tests for health monitoring module."""

import asyncio
from datetime import timedelta
from unittest.mock import AsyncMock, Mock

import pytest

from cc_orchestrator.core.instance import ClaudeInstance
from cc_orchestrator.health.alerts import AlertLevel, AlertManager
from cc_orchestrator.health.checker import (
    HealthChecker,
    HealthCheckResult,
    HealthStatus,
)
from cc_orchestrator.health.monitor import HealthMonitor
from cc_orchestrator.health.recovery import RecoveryManager


class TestHealthMonitor:
    """Test HealthMonitor class."""

    @pytest.fixture
    def mock_health_checker(self):
        """Create mock health checker."""
        checker = Mock(spec=HealthChecker)
        checker.check_health = AsyncMock(
            return_value={
                "process": HealthCheckResult(
                    status=HealthStatus.HEALTHY, message="Process OK"
                )
            }
        )
        checker.get_overall_status = Mock(return_value=HealthStatus.HEALTHY)
        return checker

    @pytest.fixture
    def mock_recovery_manager(self):
        """Create mock recovery manager."""
        manager = Mock(spec=RecoveryManager)
        manager.should_recover = AsyncMock(return_value=False)
        manager.recover_instance = AsyncMock(return_value=True)
        return manager

    @pytest.fixture
    def mock_alert_manager(self):
        """Create mock alert manager."""
        manager = Mock(spec=AlertManager)
        manager.send_alert = AsyncMock()
        return manager

    @pytest.fixture
    def mock_instance(self):
        """Create mock Claude instance."""
        instance = Mock(spec=ClaudeInstance)
        instance.issue_id = "test-instance"
        instance.workspace_path = "/tmp/test"
        instance.tmux_session = "test-session"
        instance.get_process_status = AsyncMock(return_value=Mock(pid=1234))
        return instance

    @pytest.fixture
    def health_monitor(
        self, mock_health_checker, mock_recovery_manager, mock_alert_manager
    ):
        """Create HealthMonitor instance with mocks."""
        monitor = HealthMonitor(
            check_interval=0.1,  # Short interval for testing
            health_checker=mock_health_checker,
            recovery_manager=mock_recovery_manager,
            alert_manager=mock_alert_manager,
        )
        # Set short cooldown for testing
        from datetime import timedelta

        monitor.alert_cooldown = timedelta(seconds=0.1)
        return monitor

    @pytest.mark.asyncio
    async def test_start_monitoring(self, health_monitor, mock_instance):
        """Test starting monitoring for an instance."""
        await health_monitor.start_monitoring(mock_instance)

        assert "test-instance" in health_monitor._monitoring_tasks
        assert "test-instance" in health_monitor._health_history

        # Clean up
        await health_monitor.stop_monitoring("test-instance")

    @pytest.mark.asyncio
    async def test_stop_monitoring(self, health_monitor, mock_instance):
        """Test stopping monitoring for an instance."""
        await health_monitor.start_monitoring(mock_instance)
        await health_monitor.stop_monitoring("test-instance")

        assert "test-instance" not in health_monitor._monitoring_tasks
        assert "test-instance" not in health_monitor._last_alert_time

    @pytest.mark.asyncio
    async def test_stop_all_monitoring(self, health_monitor, mock_instance):
        """Test stopping all monitoring."""
        await health_monitor.start_monitoring(mock_instance)
        await health_monitor.stop_all_monitoring()

        assert len(health_monitor._monitoring_tasks) == 0
        assert len(health_monitor._last_alert_time) == 0

    @pytest.mark.asyncio
    async def test_force_health_check(self, health_monitor, mock_instance):
        """Test forcing an immediate health check."""
        results = await health_monitor.force_health_check(mock_instance)

        assert "process" in results
        assert results["process"].status == HealthStatus.HEALTHY

        # Verify results were stored
        assert "test-instance" in health_monitor._health_history
        assert len(health_monitor._health_history["test-instance"]) == 1

    @pytest.mark.asyncio
    async def test_get_health_status(self, health_monitor, mock_instance):
        """Test getting health status for an instance."""
        # Force a health check to populate history
        await health_monitor.force_health_check(mock_instance)

        status = await health_monitor.get_health_status("test-instance")

        assert status is not None
        assert status["instance_id"] == "test-instance"
        assert status["overall_status"] == HealthStatus.HEALTHY.value
        assert status["total_checks"] == 1
        assert status["healthy_checks"] == 1
        assert status["uptime_percentage"] == 100.0

    @pytest.mark.asyncio
    async def test_get_health_status_no_data(self, health_monitor):
        """Test getting health status with no data."""
        status = await health_monitor.get_health_status("non-existent")
        assert status is None

    @pytest.mark.asyncio
    async def test_get_all_health_status(self, health_monitor, mock_instance):
        """Test getting health status for all instances."""
        await health_monitor.force_health_check(mock_instance)

        all_status = await health_monitor.get_all_health_status()

        assert "test-instance" in all_status
        assert (
            all_status["test-instance"]["overall_status"] == HealthStatus.HEALTHY.value
        )

    @pytest.mark.asyncio
    async def test_health_monitoring_loop(self, health_monitor, mock_instance):
        """Test the health monitoring loop."""
        # Start monitoring
        await health_monitor.start_monitoring(mock_instance)

        # Wait for a few checks
        await asyncio.sleep(0.3)

        # Stop monitoring
        await health_monitor.stop_monitoring("test-instance")

        # Verify health checks were performed
        health_monitor.health_checker.check_health.assert_called()

        # Verify history was populated
        assert len(health_monitor._health_history["test-instance"]) >= 2

    @pytest.mark.asyncio
    async def test_unhealthy_instance_handling(self, health_monitor, mock_instance):
        """Test handling of unhealthy instance."""
        # Configure health checker to return critical status
        health_monitor.health_checker.check_health.return_value = {
            "process": HealthCheckResult(
                status=HealthStatus.CRITICAL, message="Process failed"
            )
        }
        health_monitor.health_checker.get_overall_status.return_value = (
            HealthStatus.CRITICAL
        )

        # Configure recovery manager to attempt recovery
        health_monitor.recovery_manager.should_recover.return_value = True

        # Force health check
        await health_monitor.force_health_check(mock_instance)

        # Verify recovery was attempted
        health_monitor.recovery_manager.should_recover.assert_called()
        health_monitor.recovery_manager.recover_instance.assert_called()

        # Verify alert was sent
        health_monitor.alert_manager.send_alert.assert_called()

    @pytest.mark.asyncio
    async def test_alert_cooldown(self, health_monitor, mock_instance):
        """Test alert cooldown functionality."""
        # Set very short cooldown for testing
        health_monitor.alert_cooldown = timedelta(milliseconds=100)

        # Send first alert
        await health_monitor._send_alert_if_needed(
            "test-instance", AlertLevel.WARNING, "Test alert", {}
        )

        # Send second alert immediately (should be suppressed)
        await health_monitor._send_alert_if_needed(
            "test-instance", AlertLevel.WARNING, "Test alert 2", {}
        )

        # Verify only one alert was sent
        assert health_monitor.alert_manager.send_alert.call_count == 1

        # Wait for cooldown to expire
        await asyncio.sleep(0.2)

        # Send third alert (should go through)
        await health_monitor._send_alert_if_needed(
            "test-instance", AlertLevel.WARNING, "Test alert 3", {}
        )

        # Verify second alert was sent
        assert health_monitor.alert_manager.send_alert.call_count == 2

    @pytest.mark.asyncio
    async def test_degraded_instance_handling(self, health_monitor, mock_instance):
        """Test handling of degraded instance."""
        # Configure health checker to return degraded status
        health_monitor.health_checker.check_health.return_value = {
            "process": HealthCheckResult(
                status=HealthStatus.DEGRADED, message="High CPU usage"
            )
        }
        health_monitor.health_checker.get_overall_status.return_value = (
            HealthStatus.DEGRADED
        )

        # Force health check
        await health_monitor.force_health_check(mock_instance)

        # Verify recovery was not attempted (degraded doesn't trigger recovery)
        health_monitor.recovery_manager.should_recover.assert_not_called()

        # Verify warning alert was sent
        health_monitor.alert_manager.send_alert.assert_called_with(
            instance_id="test-instance",
            level=AlertLevel.WARNING,
            message="Instance test-instance is degraded",
            details={
                "status": "degraded",
                "results": health_monitor.health_checker.check_health.return_value,
            },
        )

    def test_store_health_results_limit(self, health_monitor):
        """Test health results storage respects limit."""
        instance_id = "test-instance"
        health_monitor.max_history_entries = 3

        # Store more results than the limit
        for i in range(5):
            results = {
                "test": HealthCheckResult(
                    status=HealthStatus.HEALTHY, message=f"Test {i}"
                )
            }
            health_monitor._store_health_results(instance_id, results)

        # Verify only the last 3 entries are kept
        history = health_monitor._health_history[instance_id]
        assert len(history) == 3
        assert history[-1]["test"].message == "Test 4"  # Most recent
        assert history[0]["test"].message == "Test 2"  # Oldest kept
