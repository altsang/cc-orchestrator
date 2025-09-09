"""Integration tests for health monitoring functionality."""

import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from click.testing import CliRunner

from src.cc_orchestrator.cli.instances import health
from src.cc_orchestrator.core.health_monitor import get_health_monitor
from src.cc_orchestrator.database.models import HealthStatus
from src.cc_orchestrator.utils.process import ProcessInfo, ProcessStatus


@pytest.fixture
def cli_runner():
    """Create a CLI runner for testing."""
    return CliRunner()


@pytest.fixture
def mock_instance():
    """Create a mock instance for testing."""
    instance = MagicMock()
    instance.id = 1
    instance.issue_id = "test-issue"
    instance.health_status = HealthStatus.HEALTHY
    instance.last_health_check = datetime.now()
    instance.health_check_count = 10
    instance.healthy_check_count = 9
    instance.recovery_attempt_count = 1
    instance.tmux_session = "test-session"
    instance.workspace_path = "/test/workspace"
    return instance


class TestHealthCLI:
    """Test health monitoring CLI commands."""

    def test_health_check_command(self, cli_runner):
        """Test the health check CLI command."""
        with patch(
            "src.cc_orchestrator.cli.instances.get_health_monitor"
        ) as mock_get_monitor:
            mock_monitor = AsyncMock()
            mock_monitor.check_instance_health.return_value = {
                "overall_status": HealthStatus.HEALTHY,
                "duration_ms": 125.0,
                "checks": {
                    "process_running": True,
                    "cpu_healthy": True,
                    "memory_healthy": True,
                    "cpu_percent": 25.0,
                    "memory_mb": 512.0,
                },
            }
            mock_get_monitor.return_value = mock_monitor

            result = cli_runner.invoke(health, ["check", "test-issue"])

            assert result.exit_code == 0
            assert "HEALTHY" in result.output
            assert "125.0ms" in result.output

    def test_health_check_command_json(self, cli_runner):
        """Test the health check CLI command with JSON output."""
        with patch(
            "src.cc_orchestrator.cli.instances.get_health_monitor"
        ) as mock_get_monitor:
            mock_monitor = AsyncMock()
            mock_monitor.check_instance_health.return_value = {
                "overall_status": HealthStatus.DEGRADED,
                "duration_ms": 200.0,
                "checks": {
                    "process_running": True,
                    "tmux_session_active": False,
                },
            }
            mock_get_monitor.return_value = mock_monitor

            result = cli_runner.invoke(health, ["check", "test-issue", "--json"])

            assert result.exit_code == 0
            output_data = json.loads(result.output)
            assert output_data["overall_status"] == "degraded"
            assert output_data["duration_ms"] == 200.0

    def test_health_status_command(self, cli_runner, mock_instance):
        """Test the health status CLI command."""
        with patch(
            "src.cc_orchestrator.cli.instances.get_health_monitor"
        ) as mock_get_monitor:
            mock_monitor = AsyncMock()
            mock_process_manager = AsyncMock()
            mock_process_manager.list_processes.return_value = {
                "test-issue": {"pid": 1234, "status": "running"}
            }
            mock_monitor.process_manager = mock_process_manager
            mock_monitor.check_instance_health.return_value = {
                "overall_status": HealthStatus.HEALTHY,
                "checks": {"process_running": True},
                "duration_ms": 100.0,
            }
            mock_get_monitor.return_value = mock_monitor

            result = cli_runner.invoke(health, ["summary"])

            assert result.exit_code == 0
            assert "test-issue" in result.output
            assert "HEALTHY" in result.output

    def test_health_status_command_filtered(self, cli_runner, mock_instance):
        """Test the health status CLI command with status filter (currently not implemented)."""
        with patch(
            "src.cc_orchestrator.cli.instances.get_health_monitor"
        ) as mock_get_monitor:
            mock_monitor = AsyncMock()
            mock_process_manager = AsyncMock()
            mock_process_manager.list_processes.return_value = {
                "test-issue": {"pid": 1234, "status": "running"}
            }
            mock_monitor.process_manager = mock_process_manager
            mock_monitor.check_instance_health.return_value = {
                "overall_status": HealthStatus.CRITICAL,
                "checks": {"process_running": False},
                "duration_ms": 100.0,
            }
            mock_get_monitor.return_value = mock_monitor

            # Note: status filtering is not yet implemented, so just test summary
            result = cli_runner.invoke(health, ["summary"])

            assert result.exit_code == 0
            assert "test-issue" in result.output
            assert "CRITICAL" in result.output

    def test_health_overview_command(self, cli_runner, mock_instance):
        """Test the health overview CLI command."""
        with patch(
            "src.cc_orchestrator.cli.instances.get_health_monitor"
        ) as mock_get_monitor:
            mock_monitor = AsyncMock()
            mock_process_manager = AsyncMock()
            mock_process_manager.list_processes.return_value = {
                "test-issue-1": {"pid": 1234, "status": "running"},
                "test-issue-2": {"pid": 5678, "status": "running"},
            }
            mock_monitor.process_manager = mock_process_manager

            # Mock sequential health checks for different instances
            health_results = [
                {
                    "overall_status": HealthStatus.HEALTHY,
                    "checks": {"process_running": True},
                    "duration_ms": 100.0,
                },
                {
                    "overall_status": HealthStatus.CRITICAL,
                    "checks": {"process_running": False},
                    "duration_ms": 150.0,
                },
            ]
            mock_monitor.check_instance_health.side_effect = health_results
            mock_get_monitor.return_value = mock_monitor

            result = cli_runner.invoke(health, ["overview"])

            assert result.exit_code == 0
            assert "Total Active Processes: 2" in result.output
            assert "Overall Health:" in result.output

    def test_health_configure_command(self, cli_runner):
        """Test the health configure CLI command."""
        with patch(
            "src.cc_orchestrator.cli.instances.get_health_monitor"
        ) as mock_get_monitor:
            mock_monitor = AsyncMock()
            mock_get_monitor.return_value = mock_monitor

            result = cli_runner.invoke(health, ["configure", "--interval", "60"])

            assert result.exit_code == 0
            assert "60 seconds" in result.output
            assert mock_monitor.check_interval == 60.0

    def test_health_configure_disable(self, cli_runner):
        """Test disabling health monitoring via CLI."""
        with patch(
            "src.cc_orchestrator.cli.instances.get_health_monitor"
        ) as mock_get_monitor:
            mock_monitor = AsyncMock()
            mock_get_monitor.return_value = mock_monitor

            result = cli_runner.invoke(health, ["configure", "--disable"])

            assert result.exit_code == 0
            assert "disabled" in result.output
            assert mock_monitor.enabled is False


class TestHealthAPI:
    """Test health monitoring API integration."""

    @pytest.mark.asyncio
    async def test_health_monitoring_with_api(self):
        """Test that health monitoring integrates with API endpoints."""

        # Mock the dependencies
        mock_crud = AsyncMock()
        mock_instance = MagicMock()
        mock_instance.id = 1
        mock_instance.tmux_session = "test-session"
        mock_instance.workspace_path = "/test/path"
        mock_instance.health_check_count = 5
        mock_instance.healthy_check_count = 4
        mock_crud.get_instance.return_value = mock_instance

        # Mock health check creation
        mock_health_check = MagicMock()
        mock_health_check.id = 1
        mock_health_check.overall_status = HealthStatus.HEALTHY
        mock_crud.create_health_check.return_value = mock_health_check

        with patch(
            "src.cc_orchestrator.web.routers.v1.health.get_crud", return_value=mock_crud
        ):
            # This would normally require proper FastAPI dependency injection setup
            # For integration testing, we'd need a proper test client
            pass  # Placeholder for API integration test


class TestHealthMonitoringWorkflow:
    """Test complete health monitoring workflow."""

    @pytest.mark.asyncio
    async def test_complete_health_monitoring_workflow(self):
        """Test a complete health monitoring workflow."""
        health_monitor = get_health_monitor()

        # Mock process manager directly since health monitor doesn't use database
        with patch.object(
            health_monitor.process_manager, "get_process_info"
        ) as mock_get_process:
            # First check: healthy process
            healthy_process = ProcessInfo(
                pid=1234,
                status=ProcessStatus.RUNNING,
                command=["claude"],
                working_directory="/test/path",
                environment={},
                started_at=1234567890,
                cpu_percent=25.0,
                memory_mb=512.0,
            )
            mock_get_process.return_value = healthy_process

            with patch.object(health_monitor, "_check_tmux_session") as mock_tmux:
                mock_tmux.return_value = True

                with patch.object(
                    health_monitor, "_check_workspace_accessible"
                ) as mock_workspace:
                    mock_workspace.return_value = True

                    # Perform health check
                    result = await health_monitor.check_instance_health("test-issue")

                    # Verify healthy result
                    assert result["overall_status"] == HealthStatus.HEALTHY
                    assert result["checks"]["process_running"] is True

                    # Simulate process failure
                    mock_get_process.return_value = None  # Process not running

                    # Perform another health check
                    result = await health_monitor.check_instance_health("test-issue")

                    # Verify critical result
                    assert result["overall_status"] == HealthStatus.CRITICAL
                    assert result["checks"]["process_running"] is False

    @pytest.mark.asyncio
    async def test_health_monitoring_with_recovery(self):
        """Test health monitoring with automatic recovery."""
        health_monitor = get_health_monitor()

        # Mock critical health result
        critical_result = {
            "overall_status": HealthStatus.CRITICAL,
            "checks": {"process_running": False},
        }

        with patch.object(
            health_monitor.process_manager, "terminate_process"
        ) as mock_terminate:
            mock_terminate.return_value = True

            with patch("asyncio.sleep"):  # Speed up test
                # Perform recovery
                success = await health_monitor.perform_recovery(
                    "test-issue", critical_result
                )

                assert success is True
                mock_terminate.assert_called_once_with("test-issue")

    @pytest.mark.asyncio
    async def test_health_check_persistence(self):
        """Test that health checks work properly (persistence would require database integration)."""
        health_monitor = get_health_monitor()

        # Mock process info
        with patch.object(
            health_monitor.process_manager, "get_process_info"
        ) as mock_get_process:
            mock_get_process.return_value = None  # Unhealthy state

            # Perform a health check
            result = await health_monitor.check_instance_health("test-issue")

            # Verify the health check result
            assert result["overall_status"] == HealthStatus.CRITICAL
            assert result["checks"]["process_running"] is False
            assert "duration_ms" in result
            assert "timestamp" in result


if __name__ == "__main__":
    pytest.main([__file__])
