"""Tests for health monitoring functionality."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.cc_orchestrator.core.health_monitor import (
    AlertSystem,
    HealthMonitor,
    RestartManager,
    get_health_monitor,
)
from src.cc_orchestrator.database.models import HealthStatus
from src.cc_orchestrator.utils.process import ProcessInfo, ProcessStatus


class TestRestartManager:
    """Test the RestartManager class."""

    def test_can_restart_new_instance(self):
        """Test that new instances can be restarted."""
        restart_manager = RestartManager()
        assert restart_manager.can_restart("test-instance")

    def test_can_restart_within_limit(self):
        """Test that instances can be restarted within the limit."""
        restart_manager = RestartManager()

        # Record attempts within limit
        restart_manager.record_restart_attempt("test-instance")
        restart_manager.record_restart_attempt("test-instance")

        assert restart_manager.can_restart("test-instance")  # Should be allowed (< 3)

    def test_cannot_restart_over_limit(self):
        """Test that instances cannot be restarted over the limit."""
        restart_manager = RestartManager()

        # Record max attempts
        for _ in range(3):
            restart_manager.record_restart_attempt("test-instance")

        assert not restart_manager.can_restart("test-instance")  # Should be denied

    def test_restart_attempts_expire(self):
        """Test that old restart attempts are cleaned up."""
        restart_manager = RestartManager()

        # Mock time to simulate old attempts
        import time

        old_time = time.time() - 3700  # 1 hour + 100 seconds ago

        with patch("time.time", return_value=old_time):
            for _ in range(3):
                restart_manager.record_restart_attempt("test-instance")

        # Current time should allow restarts again
        assert restart_manager.can_restart("test-instance")

    def test_calculate_delay_exponential(self):
        """Test that delay increases exponentially."""
        restart_manager = RestartManager()

        # First attempt
        delay1 = restart_manager.calculate_delay("test-instance")
        restart_manager.record_restart_attempt("test-instance")

        # Second attempt
        delay2 = restart_manager.calculate_delay("test-instance")
        restart_manager.record_restart_attempt("test-instance")

        # Third attempt
        delay3 = restart_manager.calculate_delay("test-instance")

        assert delay1 == 30.0  # Base delay
        assert delay2 == 60.0  # 2^1 * base
        assert delay3 == 120.0  # 2^2 * base

    def test_delay_max_limit(self):
        """Test that delay doesn't exceed maximum."""
        restart_manager = RestartManager()
        restart_manager.max_delay = 100.0  # Set low max for testing

        # Record many attempts
        for _ in range(10):
            restart_manager.record_restart_attempt("test-instance")

        delay = restart_manager.calculate_delay("test-instance")
        assert delay == 100.0  # Should be capped at max

    def test_clear_attempts(self):
        """Test clearing restart attempts."""
        restart_manager = RestartManager()

        for _ in range(3):
            restart_manager.record_restart_attempt("test-instance")

        assert not restart_manager.can_restart("test-instance")

        restart_manager.clear_attempts("test-instance")
        assert restart_manager.can_restart("test-instance")


class TestAlertSystem:
    """Test the AlertSystem class."""

    @pytest.mark.asyncio
    async def test_send_alert(self):
        """Test sending alerts."""
        alert_system = AlertSystem()

        with patch("src.cc_orchestrator.core.health_monitor.logger") as mock_logger:
            await alert_system.send_alert(
                level="warning",
                message="Test alert",
                instance_id="test-instance",
                details={"key": "value"},
            )

            # Check that warning level log was called
            mock_logger.warning.assert_called_once()

    @pytest.mark.asyncio
    async def test_alert_disabled(self):
        """Test that alerts can be disabled."""
        alert_system = AlertSystem()
        alert_system.enabled = False

        with patch("src.cc_orchestrator.core.health_monitor.logger") as mock_logger:
            await alert_system.send_alert(
                level="error", message="Test alert", instance_id="test-instance"
            )

            # Should not log when disabled
            mock_logger.error.assert_not_called()


class TestHealthMonitor:
    """Test the HealthMonitor class."""

    @pytest.fixture
    def health_monitor(self):
        """Create a health monitor for testing."""
        monitor = HealthMonitor()
        monitor.check_interval = 0.1  # Fast interval for testing
        return monitor

    @pytest.mark.asyncio
    async def test_start_stop(self, health_monitor):
        """Test starting and stopping the health monitor."""
        await health_monitor.start()
        assert health_monitor.monitoring_task is not None
        assert not health_monitor.monitoring_task.done()

        await health_monitor.stop()
        assert health_monitor.monitoring_task.done()

    @pytest.mark.asyncio
    async def test_check_instance_health_no_instance(self, health_monitor):
        """Test health check for non-existent instance."""
        with patch("src.cc_orchestrator.core.health_monitor.get_crud") as mock_get_crud:
            mock_crud = AsyncMock()
            mock_crud.get_instance_by_issue_id.return_value = None
            mock_get_crud.return_value = mock_crud

            result = await health_monitor.check_instance_health("nonexistent")

            assert result["overall_status"] == HealthStatus.CRITICAL
            assert "not found" in result["error"]

    @pytest.mark.asyncio
    async def test_check_instance_health_running_process(self, health_monitor):
        """Test health check for instance with running process."""
        # Mock instance
        mock_instance = MagicMock()
        mock_instance.tmux_session = "test-session"
        mock_instance.workspace_path = "/test/path"

        # Mock process info
        mock_process_info = ProcessInfo(
            pid=1234,
            status=ProcessStatus.RUNNING,
            command=["claude"],
            working_directory="/test/path",
            environment={},
            started_at=1234567890,
            cpu_percent=25.0,
            memory_mb=512.0,
        )

        with patch("src.cc_orchestrator.core.health_monitor.get_crud") as mock_get_crud:
            mock_crud = AsyncMock()
            mock_crud.get_instance_by_issue_id.return_value = mock_instance
            mock_get_crud.return_value = mock_crud

            with patch.object(
                health_monitor.process_manager, "get_process_info"
            ) as mock_get_process:
                mock_get_process.return_value = mock_process_info

                with patch.object(health_monitor, "_check_tmux_session") as mock_tmux:
                    mock_tmux.return_value = True

                    with patch.object(
                        health_monitor, "_check_workspace_accessible"
                    ) as mock_workspace:
                        mock_workspace.return_value = True

                        result = await health_monitor.check_instance_health(
                            "test-instance"
                        )

                        assert result["overall_status"] == HealthStatus.HEALTHY
                        assert result["checks"]["process_running"] is True
                        assert result["checks"]["cpu_healthy"] is True
                        assert result["checks"]["memory_healthy"] is True

    @pytest.mark.asyncio
    async def test_check_instance_health_high_cpu(self, health_monitor):
        """Test health check for instance with high CPU usage."""
        mock_instance = MagicMock()
        mock_instance.tmux_session = None
        mock_instance.workspace_path = None

        # Mock process info with high CPU
        mock_process_info = ProcessInfo(
            pid=1234,
            status=ProcessStatus.RUNNING,
            command=["claude"],
            working_directory="/test/path",
            environment={},
            started_at=1234567890,
            cpu_percent=95.0,  # Above threshold
            memory_mb=512.0,
        )

        with patch("src.cc_orchestrator.core.health_monitor.get_crud") as mock_get_crud:
            mock_crud = AsyncMock()
            mock_crud.get_instance_by_issue_id.return_value = mock_instance
            mock_get_crud.return_value = mock_crud

            with patch.object(
                health_monitor.process_manager, "get_process_info"
            ) as mock_get_process:
                mock_get_process.return_value = mock_process_info

                result = await health_monitor.check_instance_health("test-instance")

                assert result["overall_status"] == HealthStatus.CRITICAL
                assert result["checks"]["cpu_healthy"] is False

    @pytest.mark.asyncio
    async def test_check_instance_health_not_running(self, health_monitor):
        """Test health check for instance with stopped process."""
        mock_instance = MagicMock()
        mock_instance.tmux_session = None
        mock_instance.workspace_path = None

        with patch("src.cc_orchestrator.core.health_monitor.get_crud") as mock_get_crud:
            mock_crud = AsyncMock()
            mock_crud.get_instance_by_issue_id.return_value = mock_instance
            mock_get_crud.return_value = mock_crud

            with patch.object(
                health_monitor.process_manager, "get_process_info"
            ) as mock_get_process:
                mock_get_process.return_value = None  # No process info = not running

                result = await health_monitor.check_instance_health("test-instance")

                assert result["overall_status"] == HealthStatus.CRITICAL
                assert result["checks"]["process_running"] is False

    @pytest.mark.asyncio
    async def test_perform_recovery_max_attempts_exceeded(self, health_monitor):
        """Test recovery when max attempts are exceeded."""
        health_monitor.restart_manager.restart_attempts["test-instance"] = [
            1,
            2,
            3,
        ]  # Max attempts

        result = await health_monitor.perform_recovery(
            "test-instance", {"overall_status": HealthStatus.CRITICAL}
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_perform_recovery_success(self, health_monitor):
        """Test successful recovery attempt."""
        health_result = {"overall_status": HealthStatus.CRITICAL}

        with patch("src.cc_orchestrator.core.health_monitor.get_crud") as mock_get_crud:
            mock_crud = AsyncMock()
            mock_instance = MagicMock()
            mock_instance.recovery_attempt_count = 0
            mock_crud.get_instance_by_issue_id.return_value = mock_instance
            mock_get_crud.return_value = mock_crud

            with patch.object(
                health_monitor.process_manager, "terminate_process"
            ) as mock_terminate:
                mock_terminate.return_value = True

                with patch("asyncio.sleep"):  # Speed up test
                    result = await health_monitor.perform_recovery(
                        "test-instance", health_result
                    )

                    assert result is True
                    mock_terminate.assert_called_once_with("test-instance")

    @pytest.mark.asyncio
    async def test_check_tmux_session(self, health_monitor):
        """Test tmux session checking."""
        with patch("subprocess.run") as mock_run:
            # Mock successful tmux check
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = "test-session: 1 windows"
            mock_run.return_value = mock_result

            result = await health_monitor._check_tmux_session("test-session")
            assert result is True

    @pytest.mark.asyncio
    async def test_check_tmux_session_not_found(self, health_monitor):
        """Test tmux session not found."""
        with patch("subprocess.run") as mock_run:
            # Mock failed tmux check
            mock_result = MagicMock()
            mock_result.returncode = 1
            mock_result.stdout = ""
            mock_run.return_value = mock_result

            result = await health_monitor._check_tmux_session("nonexistent")
            assert result is False

    @pytest.mark.asyncio
    async def test_check_workspace_accessible(self, health_monitor):
        """Test workspace accessibility checking."""
        with patch("pathlib.Path.exists") as mock_exists:
            with patch("pathlib.Path.is_dir") as mock_is_dir:
                mock_exists.return_value = True
                mock_is_dir.return_value = True

                result = await health_monitor._check_workspace_accessible("/test/path")
                assert result is True

    @pytest.mark.asyncio
    async def test_check_workspace_not_accessible(self, health_monitor):
        """Test workspace not accessible."""
        with patch("pathlib.Path.exists") as mock_exists:
            mock_exists.return_value = False

            result = await health_monitor._check_workspace_accessible("/nonexistent")
            assert result is False

    def test_determine_health_status_healthy(self, health_monitor):
        """Test determining healthy status."""
        checks = {
            "process_running": True,
            "cpu_healthy": True,
            "memory_healthy": True,
            "tmux_session_active": True,
            "workspace_accessible": True,
        }

        status = health_monitor._determine_health_status(checks)
        assert status == HealthStatus.HEALTHY

    def test_determine_health_status_critical_not_running(self, health_monitor):
        """Test determining critical status when process not running."""
        checks = {
            "process_running": False,
            "cpu_healthy": True,
            "memory_healthy": True,
        }

        status = health_monitor._determine_health_status(checks)
        assert status == HealthStatus.CRITICAL

    def test_determine_health_status_critical_high_resources(self, health_monitor):
        """Test determining critical status for high resource usage."""
        checks = {
            "process_running": True,
            "cpu_healthy": False,  # High CPU
            "memory_healthy": True,
        }

        status = health_monitor._determine_health_status(checks)
        assert status == HealthStatus.CRITICAL

    def test_determine_health_status_degraded(self, health_monitor):
        """Test determining degraded status."""
        checks = {
            "process_running": True,
            "cpu_healthy": True,
            "memory_healthy": True,
            "tmux_session_active": False,  # Tmux issue
            "workspace_accessible": True,
        }

        status = health_monitor._determine_health_status(checks)
        assert status == HealthStatus.DEGRADED


class TestHealthMonitorIntegration:
    """Integration tests for health monitor."""

    @pytest.mark.asyncio
    async def test_monitoring_loop(self):
        """Test the monitoring loop functionality."""
        health_monitor = HealthMonitor()
        health_monitor.check_interval = 0.05  # Very fast for testing

        with patch.object(health_monitor, "_perform_health_checks") as mock_checks:
            mock_checks.return_value = None

            # Start monitoring
            await health_monitor.start()

            # Let it run for a short time
            await asyncio.sleep(0.15)  # Should trigger at least 2 checks

            # Stop monitoring
            await health_monitor.stop()

            # Verify checks were called
            assert mock_checks.call_count >= 2

    @pytest.mark.asyncio
    async def test_global_health_monitor(self):
        """Test global health monitor instance."""
        monitor1 = get_health_monitor()
        monitor2 = get_health_monitor()

        assert monitor1 is monitor2  # Should be the same instance


if __name__ == "__main__":
    pytest.main([__file__])
