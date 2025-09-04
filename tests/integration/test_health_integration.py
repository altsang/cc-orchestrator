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
        with patch("src.cc_orchestrator.cli.instances.get_crud") as mock_get_crud:
            mock_crud = AsyncMock()
            mock_crud.list_instances.return_value = ([mock_instance], 1)
            mock_get_crud.return_value = mock_crud

            result = cli_runner.invoke(health, ["status"])

            assert result.exit_code == 0
            assert "test-issue" in result.output
            assert "HEALTHY" in result.output
            assert "90.0%" in result.output  # 9/10 * 100

    def test_health_status_command_filtered(self, cli_runner, mock_instance):
        """Test the health status CLI command with status filter."""
        mock_instance.health_status = HealthStatus.CRITICAL

        with patch("src.cc_orchestrator.cli.instances.get_crud") as mock_get_crud:
            mock_crud = AsyncMock()
            mock_crud.list_instances.return_value = ([mock_instance], 1)
            mock_get_crud.return_value = mock_crud

            result = cli_runner.invoke(health, ["status", "--status", "critical"])

            assert result.exit_code == 0
            assert "test-issue" in result.output
            assert "CRITICAL" in result.output

    def test_health_overview_command(self, cli_runner, mock_instance):
        """Test the health overview CLI command."""
        # Create multiple instances with different statuses
        healthy_instance = MagicMock()
        healthy_instance.health_status = HealthStatus.HEALTHY
        healthy_instance.health_check_count = 10
        healthy_instance.healthy_check_count = 10
        healthy_instance.recovery_attempt_count = 0

        critical_instance = MagicMock()
        critical_instance.health_status = HealthStatus.CRITICAL
        critical_instance.health_check_count = 5
        critical_instance.healthy_check_count = 2
        critical_instance.recovery_attempt_count = 3

        instances = [healthy_instance, critical_instance]

        with patch("src.cc_orchestrator.cli.instances.get_crud") as mock_get_crud:
            mock_crud = AsyncMock()
            mock_crud.list_instances.return_value = (instances, 2)
            mock_get_crud.return_value = mock_crud

            result = cli_runner.invoke(health, ["overview"])

            assert result.exit_code == 0
            assert "Total Instances: 2" in result.output
            assert "Overall Health: 50.0%" in result.output  # 1 healthy out of 2
            assert (
                "Check Success Rate: 80.0%" in result.output
            )  # 12 healthy out of 15 total

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

        # Mock all dependencies
        with patch("src.cc_orchestrator.core.health_monitor.get_crud") as mock_get_crud:
            mock_crud = AsyncMock()

            # Create mock instance
            mock_instance = MagicMock()
            mock_instance.id = 1
            mock_instance.issue_id = "test-issue"
            mock_instance.tmux_session = "test-session"
            mock_instance.workspace_path = "/test/path"
            mock_instance.health_check_count = 0
            mock_instance.healthy_check_count = 0
            mock_instance.recovery_attempt_count = 0

            mock_crud.get_instance_by_issue_id.return_value = mock_instance
            mock_get_crud.return_value = mock_crud

            # Mock process manager
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
                        result = await health_monitor.check_instance_health(
                            "test-issue"
                        )

                        # Verify healthy result
                        assert result["overall_status"] == HealthStatus.HEALTHY
                        assert result["checks"]["process_running"] is True

                        # Simulate process failure
                        mock_get_process.return_value = None  # Process not running

                        # Perform another health check
                        result = await health_monitor.check_instance_health(
                            "test-issue"
                        )

                        # Verify critical result
                        assert result["overall_status"] == HealthStatus.CRITICAL
                        assert result["checks"]["process_running"] is False

    @pytest.mark.asyncio
    async def test_health_monitoring_with_recovery(self):
        """Test health monitoring with automatic recovery."""
        health_monitor = get_health_monitor()

        with patch("src.cc_orchestrator.core.health_monitor.get_crud") as mock_get_crud:
            mock_crud = AsyncMock()

            mock_instance = MagicMock()
            mock_instance.id = 1
            mock_instance.issue_id = "test-issue"
            mock_instance.recovery_attempt_count = 0

            mock_crud.get_instance_by_issue_id.return_value = mock_instance
            mock_get_crud.return_value = mock_crud

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
                    mock_crud.update_instance_by_issue_id.assert_called()

    @pytest.mark.asyncio
    async def test_health_check_persistence(self):
        """Test that health checks are properly persisted."""
        health_monitor = get_health_monitor()

        with patch("src.cc_orchestrator.core.health_monitor.get_crud") as mock_get_crud:
            mock_crud = AsyncMock()

            mock_instance = MagicMock()
            mock_instance.id = 1
            mock_instance.health_check_count = 5
            mock_instance.healthy_check_count = 4

            mock_crud.get_instance_by_issue_id.return_value = mock_instance
            mock_get_crud.return_value = mock_crud

            # Mock process info
            with patch.object(
                health_monitor.process_manager, "get_process_info"
            ) as mock_get_process:
                mock_get_process.return_value = None  # Unhealthy state

                # Simulate the check and update flow
                await health_monitor._check_and_update_instance("test-issue")

                # Verify health check was created
                mock_crud.create_health_check.assert_called_once()
                call_args = mock_crud.create_health_check.call_args[0][0]

                assert call_args["instance_id"] == 1
                assert call_args["overall_status"] == HealthStatus.CRITICAL
                assert "check_results" in call_args
                assert "duration_ms" in call_args


if __name__ == "__main__":
    pytest.main([__file__])
