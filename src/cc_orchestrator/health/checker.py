"""Health check strategies for Claude instances."""

import asyncio
import tempfile
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

import psutil

from ..utils.logging import LogContext, get_logger

logger = get_logger(__name__, LogContext.HEALTH)


class HealthStatus(Enum):
    """Health status of an instance."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


@dataclass
class HealthCheckResult:
    """Result of a health check."""

    status: HealthStatus
    message: str
    details: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    duration_ms: float = 0.0


class HealthCheck(ABC):
    """Abstract base class for health checks."""

    def __init__(self, name: str, timeout: float = 30.0):
        """Initialize health check.

        Args:
            name: Name of the health check
            timeout: Timeout for the check in seconds
        """
        self.name = name
        self.timeout = timeout

    @abstractmethod
    async def check(self, instance_id: str, **kwargs: Any) -> HealthCheckResult:
        """Perform the health check.

        Args:
            instance_id: Instance identifier
            **kwargs: Additional parameters for the check

        Returns:
            HealthCheckResult containing the check outcome
        """
        pass


class ProcessHealthCheck(HealthCheck):
    """Check if the instance process is running and responsive."""

    def __init__(self, timeout: float = 10.0):
        super().__init__("process", timeout)

    async def check(self, instance_id: str, **kwargs: Any) -> HealthCheckResult:
        """Check process health."""
        start_time = time.time()

        try:
            # Get process info from kwargs
            process_info = kwargs.get("process_info")
            if not process_info:
                return HealthCheckResult(
                    status=HealthStatus.CRITICAL,
                    message="No process information available",
                    duration_ms=(time.time() - start_time) * 1000,
                )

            # Check if process exists
            try:
                process = psutil.Process(process_info.pid)

                # Check process status first to catch zombies
                status = process.status()
                if status == psutil.STATUS_ZOMBIE:
                    return HealthCheckResult(
                        status=HealthStatus.CRITICAL,
                        message=f"Process {process_info.pid} is a zombie",
                        duration_ms=(time.time() - start_time) * 1000,
                    )

                if not process.is_running():
                    return HealthCheckResult(
                        status=HealthStatus.CRITICAL,
                        message=f"Process {process_info.pid} is not running",
                        duration_ms=(time.time() - start_time) * 1000,
                    )

                # Check resource usage
                cpu_percent = process.cpu_percent()
                memory_mb = process.memory_info().rss / 1024 / 1024

                details = {
                    "pid": process_info.pid,
                    "status": status,
                    "cpu_percent": cpu_percent,
                    "memory_mb": memory_mb,
                    "create_time": process.create_time(),
                    "num_threads": process.num_threads(),
                }

                # Determine health status based on resource usage
                if cpu_percent > 90:
                    return HealthCheckResult(
                        status=HealthStatus.DEGRADED,
                        message=f"High CPU usage: {cpu_percent:.1f}%",
                        details=details,
                        duration_ms=(time.time() - start_time) * 1000,
                    )

                if memory_mb > 2048:  # 2GB threshold
                    return HealthCheckResult(
                        status=HealthStatus.DEGRADED,
                        message=f"High memory usage: {memory_mb:.1f} MB",
                        details=details,
                        duration_ms=(time.time() - start_time) * 1000,
                    )

                return HealthCheckResult(
                    status=HealthStatus.HEALTHY,
                    message="Process is running normally",
                    details=details,
                    duration_ms=(time.time() - start_time) * 1000,
                )

            except psutil.NoSuchProcess:
                return HealthCheckResult(
                    status=HealthStatus.CRITICAL,
                    message=f"Process {process_info.pid} does not exist",
                    duration_ms=(time.time() - start_time) * 1000,
                )

        except Exception as e:
            logger.error(
                "Process health check failed", instance_id=instance_id, error=str(e)
            )
            return HealthCheckResult(
                status=HealthStatus.CRITICAL,
                message=f"Error checking process: {str(e)}",
                duration_ms=(time.time() - start_time) * 1000,
            )


class TmuxHealthCheck(HealthCheck):
    """Check if the tmux session is active and responsive."""

    def __init__(self, timeout: float = 10.0):
        super().__init__("tmux", timeout)

    async def check(self, instance_id: str, **kwargs: Any) -> HealthCheckResult:
        """Check tmux session health."""
        start_time = time.time()

        try:
            tmux_session = kwargs.get("tmux_session")
            if not tmux_session:
                return HealthCheckResult(
                    status=HealthStatus.HEALTHY,  # Not critical if no tmux session
                    message="No tmux session configured",
                    duration_ms=(time.time() - start_time) * 1000,
                )

            # Check if tmux session exists
            process = await asyncio.create_subprocess_exec(
                "tmux",
                "has-session",
                "-t",
                tmux_session,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                await asyncio.wait_for(process.wait(), timeout=self.timeout)

                if process.returncode == 0:
                    # Session exists, get session info
                    info_process = await asyncio.create_subprocess_exec(
                        "tmux",
                        "display-message",
                        "-t",
                        tmux_session,
                        "-p",
                        "#{session_name}:#{session_windows}:#{session_activity}",
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                    )

                    stdout, stderr = await info_process.communicate()
                    if info_process.returncode == 0:
                        session_info = stdout.decode().strip().split(":")
                        details = {
                            "session_name": (
                                session_info[0]
                                if len(session_info) > 0
                                else tmux_session
                            ),
                            "window_count": (
                                int(session_info[1]) if len(session_info) > 1 else 0
                            ),
                            "last_activity": (
                                session_info[2] if len(session_info) > 2 else "unknown"
                            ),
                        }

                        return HealthCheckResult(
                            status=HealthStatus.HEALTHY,
                            message="Tmux session is active",
                            details=details,
                            duration_ms=(time.time() - start_time) * 1000,
                        )

                return HealthCheckResult(
                    status=HealthStatus.DEGRADED,
                    message=f"Tmux session '{tmux_session}' does not exist",
                    duration_ms=(time.time() - start_time) * 1000,
                )

            except TimeoutError:
                process.kill()
                return HealthCheckResult(
                    status=HealthStatus.DEGRADED,
                    message="Tmux health check timed out",
                    duration_ms=(time.time() - start_time) * 1000,
                )

        except Exception as e:
            logger.error(
                "Tmux health check failed", instance_id=instance_id, error=str(e)
            )
            return HealthCheckResult(
                status=HealthStatus.CRITICAL,
                message=f"Tmux check error: {str(e)}",
                duration_ms=(time.time() - start_time) * 1000,
            )


class WorkspaceHealthCheck(HealthCheck):
    """Check if the workspace directory is accessible and has expected structure."""

    def __init__(self, timeout: float = 5.0):
        super().__init__("workspace", timeout)

    async def check(self, instance_id: str, **kwargs: Any) -> HealthCheckResult:
        """Check workspace health."""
        start_time = time.time()

        try:
            workspace_path = kwargs.get("workspace_path")
            if not workspace_path:
                return HealthCheckResult(
                    status=HealthStatus.DEGRADED,
                    message="No workspace path configured",
                    duration_ms=(time.time() - start_time) * 1000,
                )

            workspace = Path(workspace_path)

            # Check if workspace exists
            if not workspace.exists():
                return HealthCheckResult(
                    status=HealthStatus.CRITICAL,
                    message=f"Workspace directory does not exist: {workspace_path}",
                    duration_ms=(time.time() - start_time) * 1000,
                )

            # Check if it's a directory
            if not workspace.is_dir():
                return HealthCheckResult(
                    status=HealthStatus.CRITICAL,
                    message=f"Workspace path is not a directory: {workspace_path}",
                    duration_ms=(time.time() - start_time) * 1000,
                )

            # Check if it's a git repository
            git_dir = workspace / ".git"
            if not git_dir.exists():
                return HealthCheckResult(
                    status=HealthStatus.DEGRADED,
                    message="Workspace is not a git repository",
                    details={"workspace_path": str(workspace_path)},
                    duration_ms=(time.time() - start_time) * 1000,
                )

            # Check disk space
            disk_usage = psutil.disk_usage(str(workspace))
            free_gb = disk_usage.free / (1024**3)

            details = {
                "workspace_path": str(workspace_path),
                "is_git_repo": git_dir.exists(),
                "disk_free_gb": free_gb,
                "disk_total_gb": disk_usage.total / (1024**3),
                "disk_used_percent": (disk_usage.used / disk_usage.total) * 100,
            }

            if free_gb < 1.0:  # Less than 1GB free
                return HealthCheckResult(
                    status=HealthStatus.DEGRADED,
                    message=f"Low disk space: {free_gb:.2f} GB free",
                    details=details,
                    duration_ms=(time.time() - start_time) * 1000,
                )

            return HealthCheckResult(
                status=HealthStatus.HEALTHY,
                message="Workspace is accessible",
                details=details,
                duration_ms=(time.time() - start_time) * 1000,
            )

        except Exception as e:
            logger.error(
                "Workspace health check failed", instance_id=instance_id, error=str(e)
            )
            return HealthCheckResult(
                status=HealthStatus.CRITICAL,
                message=f"Workspace check error: {str(e)}",
                duration_ms=(time.time() - start_time) * 1000,
            )


class ResponseHealthCheck(HealthCheck):
    """Check if the instance is responsive by sending a simple command."""

    def __init__(self, timeout: float = 30.0):
        super().__init__("response", timeout)

    async def check(self, instance_id: str, **kwargs: Any) -> HealthCheckResult:
        """Check instance responsiveness."""
        start_time = time.time()

        try:
            tmux_session = kwargs.get("tmux_session")
            if not tmux_session:
                return HealthCheckResult(
                    status=HealthStatus.HEALTHY,  # Skip if no tmux session
                    message="No tmux session to test responsiveness",
                    duration_ms=(time.time() - start_time) * 1000,
                )

            # Send a simple command to the tmux session and check if it responds
            # This is a basic ping-like test
            temp_dir = tempfile.gettempdir()
            test_file = (
                f"{temp_dir}/claude_health_check_{instance_id}_{int(time.time())}"
            )

            # Send command to create a test file
            process = await asyncio.create_subprocess_exec(
                "tmux",
                "send-keys",
                "-t",
                tmux_session,
                f"touch {test_file}",
                "Enter",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                await asyncio.wait_for(process.wait(), timeout=5.0)

                # Wait a bit for command to execute
                await asyncio.sleep(2.0)

                # Check if test file was created
                if Path(test_file).exists():
                    # Clean up test file
                    try:
                        Path(test_file).unlink()
                    except OSError:
                        pass

                    return HealthCheckResult(
                        status=HealthStatus.HEALTHY,
                        message="Instance is responsive",
                        details={"response_time_ms": (time.time() - start_time) * 1000},
                        duration_ms=(time.time() - start_time) * 1000,
                    )
                else:
                    return HealthCheckResult(
                        status=HealthStatus.DEGRADED,
                        message="Instance did not respond to test command",
                        duration_ms=(time.time() - start_time) * 1000,
                    )

            except TimeoutError:
                process.kill()
                return HealthCheckResult(
                    status=HealthStatus.DEGRADED,
                    message="Response check timed out",
                    duration_ms=(time.time() - start_time) * 1000,
                )

        except Exception as e:
            logger.error(
                "Response health check failed", instance_id=instance_id, error=str(e)
            )
            return HealthCheckResult(
                status=HealthStatus.CRITICAL,
                message=f"Response check error: {str(e)}",
                duration_ms=(time.time() - start_time) * 1000,
            )


class HealthChecker:
    """Coordinates multiple health checks for an instance."""

    def __init__(self, checks: list[HealthCheck] | None = None):
        """Initialize health checker.

        Args:
            checks: List of health checks to perform (uses defaults if None)
        """
        if checks is None:
            self.checks = [
                ProcessHealthCheck(),
                TmuxHealthCheck(),
                WorkspaceHealthCheck(),
                # ResponseHealthCheck(),  # Disabled by default as it can be intrusive
            ]
        else:
            self.checks = checks

        logger.info("Health checker initialized", check_count=len(self.checks))

    async def check_health(
        self, instance_id: str, **kwargs: Any
    ) -> dict[str, HealthCheckResult]:
        """Run all health checks for an instance.

        Args:
            instance_id: Instance identifier
            **kwargs: Parameters to pass to health checks

        Returns:
            Dictionary mapping check names to results
        """
        logger.debug(
            "Running health checks",
            instance_id=instance_id,
            check_count=len(self.checks),
        )

        results = {}

        # Run all checks concurrently
        check_tasks = []
        for check in self.checks:
            task = asyncio.create_task(
                self._run_check_with_timeout(check, instance_id, **kwargs)
            )
            check_tasks.append((check.name, task))

        # Gather results
        for check_name, task in check_tasks:
            try:
                result = await task
                results[check_name] = result
            except Exception as e:
                logger.error(
                    "Health check failed",
                    check=check_name,
                    instance_id=instance_id,
                    error=str(e),
                )
                results[check_name] = HealthCheckResult(
                    status=HealthStatus.CRITICAL, message=f"Check failed: {str(e)}"
                )

        logger.debug(
            "Health checks completed", instance_id=instance_id, results=len(results)
        )
        return results

    async def _run_check_with_timeout(
        self, check: HealthCheck, instance_id: str, **kwargs: Any
    ) -> HealthCheckResult:
        """Run a health check with timeout protection.

        Args:
            check: Health check to run
            instance_id: Instance identifier
            **kwargs: Parameters for the check

        Returns:
            HealthCheckResult
        """
        try:
            return await asyncio.wait_for(
                check.check(instance_id, **kwargs), timeout=check.timeout
            )
        except TimeoutError:
            return HealthCheckResult(
                status=HealthStatus.UNKNOWN,
                message=f"Health check timed out after {check.timeout}s",
            )

    def get_overall_status(self, results: dict[str, HealthCheckResult]) -> HealthStatus:
        """Determine overall health status from individual check results.

        Args:
            results: Dictionary of health check results

        Returns:
            Overall health status
        """
        if not results:
            return HealthStatus.UNKNOWN

        statuses = [result.status for result in results.values()]

        # Determine worst status
        if HealthStatus.CRITICAL in statuses:
            return HealthStatus.CRITICAL
        elif HealthStatus.UNHEALTHY in statuses:
            return HealthStatus.UNHEALTHY
        elif HealthStatus.DEGRADED in statuses:
            return HealthStatus.DEGRADED
        elif HealthStatus.UNKNOWN in statuses:
            return HealthStatus.UNKNOWN
        else:
            return HealthStatus.HEALTHY
