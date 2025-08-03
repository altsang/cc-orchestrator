"""Tests for health monitoring checker module."""

import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import psutil
import pytest

from cc_orchestrator.health.checker import (
    HealthChecker,
    HealthCheckResult,
    HealthStatus,
    ProcessHealthCheck,
    ResponseHealthCheck,
    TmuxHealthCheck,
    WorkspaceHealthCheck,
)


class TestHealthCheckResult:
    """Test HealthCheckResult dataclass."""

    def test_basic_creation(self):
        """Test basic HealthCheckResult creation."""
        result = HealthCheckResult(status=HealthStatus.HEALTHY, message="All good")

        assert result.status == HealthStatus.HEALTHY
        assert result.message == "All good"
        assert result.details == {}
        assert isinstance(result.timestamp, datetime)
        assert result.duration_ms == 0.0

    def test_creation_with_details(self):
        """Test HealthCheckResult creation with details."""
        details = {"cpu": 25.5, "memory": 512.0}
        result = HealthCheckResult(
            status=HealthStatus.DEGRADED,
            message="High CPU usage",
            details=details,
            duration_ms=123.45,
        )

        assert result.status == HealthStatus.DEGRADED
        assert result.message == "High CPU usage"
        assert result.details == details
        assert result.duration_ms == 123.45


class TestProcessHealthCheck:
    """Test ProcessHealthCheck class."""

    @pytest.fixture
    def process_check(self):
        """Create ProcessHealthCheck instance."""
        return ProcessHealthCheck()

    @pytest.mark.asyncio
    async def test_no_process_info(self, process_check):
        """Test health check with no process info."""
        result = await process_check.check("test-instance")

        assert result.status == HealthStatus.CRITICAL
        assert "No process information available" in result.message

    @pytest.mark.asyncio
    async def test_process_not_found(self, process_check):
        """Test health check with non-existent process."""
        mock_process_info = Mock()
        mock_process_info.pid = 99999  # Non-existent PID

        with patch("psutil.Process") as mock_process_class:
            mock_process_class.side_effect = psutil.NoSuchProcess(99999)

            result = await process_check.check(
                "test-instance", process_info=mock_process_info
            )

        assert result.status == HealthStatus.CRITICAL
        assert "does not exist" in result.message

    @pytest.mark.asyncio
    async def test_healthy_process(self, process_check):
        """Test health check with healthy process."""
        mock_process_info = Mock()
        mock_process_info.pid = 1234

        mock_process = Mock()
        mock_process.is_running.return_value = True
        mock_process.status.return_value = psutil.STATUS_RUNNING
        mock_process.cpu_percent.return_value = 25.5
        mock_process.memory_info.return_value = Mock(rss=512 * 1024 * 1024)  # 512MB
        mock_process.create_time.return_value = 1234567890.0
        mock_process.num_threads.return_value = 8

        with patch("psutil.Process", return_value=mock_process):
            result = await process_check.check(
                "test-instance", process_info=mock_process_info
            )

        assert result.status == HealthStatus.HEALTHY
        assert "running normally" in result.message
        assert result.details["pid"] == 1234
        assert result.details["cpu_percent"] == 25.5
        assert result.details["memory_mb"] == 512.0

    @pytest.mark.asyncio
    async def test_high_cpu_process(self, process_check):
        """Test health check with high CPU usage."""
        mock_process_info = Mock()
        mock_process_info.pid = 1234

        mock_process = Mock()
        mock_process.is_running.return_value = True
        mock_process.status.return_value = psutil.STATUS_RUNNING
        mock_process.cpu_percent.return_value = 95.0  # High CPU
        mock_process.memory_info.return_value = Mock(rss=512 * 1024 * 1024)
        mock_process.create_time.return_value = 1234567890.0
        mock_process.num_threads.return_value = 8

        with patch("psutil.Process", return_value=mock_process):
            result = await process_check.check(
                "test-instance", process_info=mock_process_info
            )

        assert result.status == HealthStatus.DEGRADED
        assert "High CPU usage" in result.message

    @pytest.mark.asyncio
    async def test_high_memory_process(self, process_check):
        """Test health check with high memory usage."""
        mock_process_info = Mock()
        mock_process_info.pid = 1234

        mock_process = Mock()
        mock_process.is_running.return_value = True
        mock_process.status.return_value = psutil.STATUS_RUNNING
        mock_process.cpu_percent.return_value = 25.0
        mock_process.memory_info.return_value = Mock(rss=3 * 1024 * 1024 * 1024)  # 3GB
        mock_process.create_time.return_value = 1234567890.0
        mock_process.num_threads.return_value = 8

        with patch("psutil.Process", return_value=mock_process):
            result = await process_check.check(
                "test-instance", process_info=mock_process_info
            )

        assert result.status == HealthStatus.DEGRADED
        assert "High memory usage" in result.message


class TestTmuxHealthCheck:
    """Test TmuxHealthCheck class."""

    @pytest.fixture
    def tmux_check(self):
        """Create TmuxHealthCheck instance."""
        return TmuxHealthCheck()

    @pytest.mark.asyncio
    async def test_no_tmux_session(self, tmux_check):
        """Test health check with no tmux session."""
        result = await tmux_check.check("test-instance")

        assert result.status == HealthStatus.HEALTHY
        assert "No tmux session configured" in result.message

    @pytest.mark.asyncio
    async def test_tmux_session_exists(self, tmux_check):
        """Test health check with existing tmux session."""

        async def mock_create_subprocess_exec(*args, **kwargs):
            if "has-session" in args:
                mock_process = Mock()
                mock_process.wait = AsyncMock(return_value=None)
                mock_process.returncode = 0
                return mock_process
            elif "display-message" in args:
                mock_process = Mock()
                mock_process.communicate = AsyncMock(
                    return_value=(b"test-session:2:1234567890", b"")
                )
                mock_process.returncode = 0
                return mock_process

        with patch(
            "asyncio.create_subprocess_exec", side_effect=mock_create_subprocess_exec
        ):
            result = await tmux_check.check(
                "test-instance", tmux_session="test-session"
            )

        assert result.status == HealthStatus.HEALTHY
        assert "active" in result.message
        assert result.details["session_name"] == "test-session"
        assert result.details["window_count"] == 2

    @pytest.mark.asyncio
    async def test_tmux_session_not_exists(self, tmux_check):
        """Test health check with non-existent tmux session."""

        async def mock_create_subprocess_exec(*args, **kwargs):
            mock_process = Mock()
            mock_process.wait = AsyncMock(return_value=None)
            mock_process.returncode = 1  # Session doesn't exist
            return mock_process

        with patch(
            "asyncio.create_subprocess_exec", side_effect=mock_create_subprocess_exec
        ):
            result = await tmux_check.check(
                "test-instance", tmux_session="non-existent"
            )

        assert result.status == HealthStatus.DEGRADED
        assert "does not exist" in result.message


class TestWorkspaceHealthCheck:
    """Test WorkspaceHealthCheck class."""

    @pytest.fixture
    def workspace_check(self):
        """Create WorkspaceHealthCheck instance."""
        return WorkspaceHealthCheck()

    @pytest.mark.asyncio
    async def test_no_workspace_path(self, workspace_check):
        """Test health check with no workspace path."""
        result = await workspace_check.check("test-instance")

        assert result.status == HealthStatus.DEGRADED
        assert "No workspace path configured" in result.message

    @pytest.mark.asyncio
    async def test_workspace_not_exists(self, workspace_check):
        """Test health check with non-existent workspace."""
        result = await workspace_check.check(
            "test-instance", workspace_path="/non/existent/path"
        )

        assert result.status == HealthStatus.CRITICAL
        assert "does not exist" in result.message

    @pytest.mark.asyncio
    async def test_healthy_workspace(self, workspace_check):
        """Test health check with healthy workspace."""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_path = Path(temp_dir)

            # Create .git directory
            git_dir = workspace_path / ".git"
            git_dir.mkdir()

            with patch("psutil.disk_usage") as mock_disk_usage:
                mock_disk_usage.return_value = Mock(
                    free=5 * 1024**3,  # 5GB free
                    total=10 * 1024**3,  # 10GB total
                    used=5 * 1024**3,  # 5GB used
                )

                result = await workspace_check.check(
                    "test-instance", workspace_path=str(workspace_path)
                )

        assert result.status == HealthStatus.HEALTHY
        assert "accessible" in result.message
        assert result.details["is_git_repo"] is True
        assert result.details["disk_free_gb"] == 5.0

    @pytest.mark.asyncio
    async def test_workspace_low_disk_space(self, workspace_check):
        """Test health check with low disk space."""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_path = Path(temp_dir)
            # Create mock .git directory
            (workspace_path / ".git").mkdir()

            with patch("psutil.disk_usage") as mock_disk_usage:
                mock_disk_usage.return_value = Mock(
                    free=0.5 * 1024**3,  # 0.5GB free (low)
                    total=10 * 1024**3,  # 10GB total
                    used=9.5 * 1024**3,  # 9.5GB used
                )

                result = await workspace_check.check(
                    "test-instance", workspace_path=str(workspace_path)
                )

        assert result.status == HealthStatus.DEGRADED
        assert "Low disk space" in result.message


class TestResponseHealthCheck:
    """Test ResponseHealthCheck class."""

    @pytest.fixture
    def response_check(self):
        """Create ResponseHealthCheck instance."""
        return ResponseHealthCheck()

    @pytest.mark.asyncio
    async def test_no_tmux_session(self, response_check):
        """Test response check with no tmux session."""
        result = await response_check.check("test-instance")

        assert result.status == HealthStatus.HEALTHY
        assert "No tmux session" in result.message

    @pytest.mark.asyncio
    async def test_response_success(self, response_check):
        """Test successful response check."""

        async def mock_create_subprocess_exec(*args, **kwargs):
            mock_process = Mock()
            mock_process.wait = AsyncMock(return_value=None)
            mock_process.returncode = 0
            return mock_process

        with patch(
            "asyncio.create_subprocess_exec", side_effect=mock_create_subprocess_exec
        ):
            with patch("pathlib.Path.exists", return_value=True):
                with patch("pathlib.Path.unlink"):
                    result = await response_check.check(
                        "test-instance", tmux_session="test-session"
                    )

        assert result.status == HealthStatus.HEALTHY
        assert "responsive" in result.message

    @pytest.mark.asyncio
    async def test_response_timeout(self, response_check):
        """Test response check timeout."""

        async def mock_create_subprocess_exec(*args, **kwargs):
            mock_process = Mock()
            mock_process.wait = AsyncMock(side_effect=TimeoutError())
            mock_process.kill = Mock()
            return mock_process

        with patch(
            "asyncio.create_subprocess_exec", side_effect=mock_create_subprocess_exec
        ):
            with patch("asyncio.wait_for", side_effect=TimeoutError()):
                result = await response_check.check(
                    "test-instance", tmux_session="test-session"
                )

        assert result.status == HealthStatus.DEGRADED
        assert "timed out" in result.message


class TestHealthChecker:
    """Test HealthChecker class."""

    @pytest.fixture
    def health_checker(self):
        """Create HealthChecker instance with mock checks."""
        mock_check1 = Mock()
        mock_check1.name = "test1"
        mock_check1.timeout = 10.0
        mock_check1.check = AsyncMock(
            return_value=HealthCheckResult(
                status=HealthStatus.HEALTHY, message="Test 1 passed"
            )
        )

        mock_check2 = Mock()
        mock_check2.name = "test2"
        mock_check2.timeout = 10.0
        mock_check2.check = AsyncMock(
            return_value=HealthCheckResult(
                status=HealthStatus.DEGRADED, message="Test 2 degraded"
            )
        )

        return HealthChecker([mock_check1, mock_check2])

    @pytest.mark.asyncio
    async def test_check_health(self, health_checker):
        """Test running health checks."""
        results = await health_checker.check_health("test-instance", param1="value1")

        assert len(results) == 2
        assert "test1" in results
        assert "test2" in results
        assert results["test1"].status == HealthStatus.HEALTHY
        assert results["test2"].status == HealthStatus.DEGRADED

        # Verify checks were called with correct parameters
        health_checker.checks[0].check.assert_called_once_with(
            "test-instance", param1="value1"
        )
        health_checker.checks[1].check.assert_called_once_with(
            "test-instance", param1="value1"
        )

    def test_get_overall_status_healthy(self, health_checker):
        """Test overall status calculation with all healthy."""
        results = {
            "test1": HealthCheckResult(status=HealthStatus.HEALTHY, message="OK"),
            "test2": HealthCheckResult(status=HealthStatus.HEALTHY, message="OK"),
        }

        status = health_checker.get_overall_status(results)
        assert status == HealthStatus.HEALTHY

    def test_get_overall_status_degraded(self, health_checker):
        """Test overall status calculation with degraded."""
        results = {
            "test1": HealthCheckResult(status=HealthStatus.HEALTHY, message="OK"),
            "test2": HealthCheckResult(
                status=HealthStatus.DEGRADED, message="Degraded"
            ),
        }

        status = health_checker.get_overall_status(results)
        assert status == HealthStatus.DEGRADED

    def test_get_overall_status_critical(self, health_checker):
        """Test overall status calculation with critical."""
        results = {
            "test1": HealthCheckResult(
                status=HealthStatus.DEGRADED, message="Degraded"
            ),
            "test2": HealthCheckResult(
                status=HealthStatus.CRITICAL, message="Critical"
            ),
        }

        status = health_checker.get_overall_status(results)
        assert status == HealthStatus.CRITICAL

    def test_get_overall_status_empty(self, health_checker):
        """Test overall status calculation with no results."""
        status = health_checker.get_overall_status({})
        assert status == HealthStatus.UNKNOWN
