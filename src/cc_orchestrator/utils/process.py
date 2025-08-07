"""Process management utilities for Claude Code instances."""

import asyncio
import os
import subprocess  # nosec B404
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

import psutil

from .logging import LogContext, get_logger

logger = get_logger(__name__, LogContext.PROCESS)


class ProcessStatus(Enum):
    """Status of a managed process."""

    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"
    CRASHED = "crashed"


@dataclass
class ProcessInfo:
    """Information about a managed process."""

    pid: int
    status: ProcessStatus
    command: list[str]
    working_directory: Path
    environment: dict[str, str]
    started_at: float
    cpu_percent: float = 0.0
    memory_mb: float = 0.0
    return_code: int | None = None
    error_message: str | None = None


class ProcessManager:
    """Manages Claude Code processes with isolation and monitoring."""

    def __init__(self) -> None:
        """Initialize the process manager."""
        self._processes: dict[str, ProcessInfo] = {}
        self._subprocess_map: dict[str, subprocess.Popen[bytes]] = {}
        self._monitoring_tasks: dict[str, asyncio.Task[None]] = {}
        self._shutdown_event = asyncio.Event()
        logger.info("Process manager initialized")

    async def spawn_claude_process(
        self,
        instance_id: str,
        working_directory: Path,
        tmux_session: str | None = None,
        environment: dict[str, str] | None = None,
        resource_limits: dict[str, Any] | None = None,
    ) -> ProcessInfo:
        """Spawn a Claude Code process for a specific instance.

        Args:
            instance_id: Unique identifier for the instance
            working_directory: Directory to run Claude in
            tmux_session: Optional tmux session name
            environment: Additional environment variables
            resource_limits: CPU/memory limits for the process

        Returns:
            ProcessInfo object containing process details

        Raises:
            ProcessError: If process creation fails
        """
        if instance_id in self._processes:
            raise ProcessError(f"Process for instance {instance_id} already exists")

        logger.info(
            "Spawning Claude process",
            instance_id=instance_id,
            working_directory=str(working_directory),
            tmux_session=tmux_session,
        )

        # Prepare environment
        env = os.environ.copy()
        if environment:
            env.update(environment)

        # Build command
        command = self._build_claude_command(
            working_directory=working_directory,
            tmux_session=tmux_session,
            resource_limits=resource_limits,
        )

        try:
            # Ensure working directory exists
            working_directory.mkdir(parents=True, exist_ok=True)

            # Start process
            process = await self._start_process(
                command=command, working_directory=working_directory, environment=env
            )

            # Create process info
            process_info = ProcessInfo(
                pid=process.pid,
                status=ProcessStatus.STARTING,
                command=command,
                working_directory=working_directory,
                environment=env,
                started_at=asyncio.get_event_loop().time(),
            )

            # Store process references
            self._processes[instance_id] = process_info
            self._subprocess_map[instance_id] = process

            # Start monitoring
            monitor_task = asyncio.create_task(
                self._monitor_process(instance_id, process)
            )
            self._monitoring_tasks[instance_id] = monitor_task

            logger.info(
                "Claude process spawned successfully",
                instance_id=instance_id,
                pid=process.pid,
            )

            return process_info

        except Exception as e:
            logger.error(
                "Failed to spawn Claude process", instance_id=instance_id, error=str(e)
            )
            raise ProcessError(f"Failed to spawn process for {instance_id}: {e}")

    async def terminate_process(self, instance_id: str, timeout: float = 30.0) -> bool:
        """Terminate a Claude Code process gracefully.

        Args:
            instance_id: Instance identifier
            timeout: Maximum time to wait for graceful shutdown

        Returns:
            True if process was terminated successfully
        """
        if instance_id not in self._processes:
            logger.warning(
                "Attempt to terminate non-existent process", instance_id=instance_id
            )
            return False

        logger.info(
            "Terminating Claude process", instance_id=instance_id, timeout=timeout
        )

        process_info = self._processes[instance_id]
        subprocess_obj = self._subprocess_map.get(instance_id)

        if not subprocess_obj or subprocess_obj.poll() is not None:
            # Process already terminated
            await self._cleanup_process(instance_id)
            return True

        try:
            # Update status
            process_info.status = ProcessStatus.STOPPING

            # Try graceful termination first
            subprocess_obj.terminate()

            try:
                await asyncio.wait_for(
                    self._wait_for_process(subprocess_obj), timeout=timeout
                )
                logger.info("Process terminated gracefully", instance_id=instance_id)
                return True

            except TimeoutError:
                # Force kill if graceful termination failed
                logger.warning(
                    "Graceful termination timed out, force killing",
                    instance_id=instance_id,
                )
                subprocess_obj.kill()
                await self._wait_for_process(subprocess_obj)
                return True

        except Exception as e:
            logger.error(
                "Error terminating process", instance_id=instance_id, error=str(e)
            )
            return False
        finally:
            await self._cleanup_process(instance_id)

    async def get_process_info(self, instance_id: str) -> ProcessInfo | None:
        """Get information about a managed process.

        Args:
            instance_id: Instance identifier

        Returns:
            ProcessInfo if process exists, None otherwise
        """
        return self._processes.get(instance_id)

    async def list_processes(self) -> dict[str, ProcessInfo]:
        """List all managed processes.

        Returns:
            Dictionary mapping instance IDs to ProcessInfo objects
        """
        return self._processes.copy()

    async def is_process_running(self, instance_id: str) -> bool:
        """Check if a process is currently running.

        Args:
            instance_id: Instance identifier

        Returns:
            True if process is running, False otherwise
        """
        process_info = self._processes.get(instance_id)
        if not process_info:
            return False

        return process_info.status == ProcessStatus.RUNNING

    async def cleanup_all(self) -> None:
        """Clean up all managed processes."""
        logger.info("Cleaning up all processes", process_count=len(self._processes))

        # Signal shutdown
        self._shutdown_event.set()

        # Terminate all processes
        terminate_tasks = []
        for instance_id in list(self._processes.keys()):
            terminate_task = asyncio.create_task(self.terminate_process(instance_id))
            terminate_tasks.append(terminate_task)

        if terminate_tasks:
            await asyncio.gather(*terminate_tasks, return_exceptions=True)

        # Cancel monitoring tasks
        for monitor_task in self._monitoring_tasks.values():
            if not monitor_task.done():
                monitor_task.cancel()

        if self._monitoring_tasks:
            await asyncio.gather(
                *self._monitoring_tasks.values(), return_exceptions=True
            )

        # Clear all references
        self._processes.clear()
        self._subprocess_map.clear()
        self._monitoring_tasks.clear()

        logger.info("Process cleanup completed")

    def _build_claude_command(
        self,
        working_directory: Path,
        tmux_session: str | None = None,
        resource_limits: dict[str, Any] | None = None,
    ) -> list[str]:
        """Build the command to execute Claude Code.

        Args:
            working_directory: Directory to run Claude in
            tmux_session: Optional tmux session name
            resource_limits: CPU/memory limits

        Returns:
            Command as list of strings
        """
        if tmux_session:
            # Run Claude in tmux session
            tmux_cmd = [
                "tmux",
                "new-session",
                "-d",
                "-s",
                tmux_session,
                "-c",
                str(working_directory),
                "claude",
                "--continue",
            ]
            return tmux_cmd
        else:
            # Run Claude directly
            return ["claude", "--continue"]

    async def _start_process(
        self, command: list[str], working_directory: Path, environment: dict[str, str]
    ) -> subprocess.Popen[bytes]:
        """Start a subprocess with the given parameters.

        Args:
            command: Command to execute
            working_directory: Working directory
            environment: Environment variables

        Returns:
            Started subprocess.Popen[bytes] object
        """
        logger.debug(
            "Starting subprocess",
            command=command,
            working_directory=str(working_directory),
        )

        # Create subprocess
        process = subprocess.Popen(  # nosec B603
            command,
            cwd=working_directory,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.PIPE,
            start_new_session=True,  # Create new process group
        )

        return process

    async def _monitor_process(
        self, instance_id: str, process: subprocess.Popen[bytes]
    ) -> None:
        """Monitor a process for status changes and resource usage.

        Args:
            instance_id: Instance identifier
            process: subprocess.Popen[bytes] object to monitor
        """
        logger.debug("Starting process monitoring", instance_id=instance_id)

        try:
            # Wait a bit for process to fully start
            await asyncio.sleep(1.0)

            # Update status to running if process is still alive
            if process.poll() is None:
                self._processes[instance_id].status = ProcessStatus.RUNNING
                logger.info("Process started successfully", instance_id=instance_id)

            # Monitor process
            while not self._shutdown_event.is_set():
                try:
                    # Check if process is still running
                    return_code = process.poll()
                    if return_code is not None:
                        # Process has terminated
                        logger.info(
                            "Process terminated",
                            instance_id=instance_id,
                            return_code=return_code,
                        )

                        process_info = self._processes[instance_id]
                        process_info.return_code = return_code

                        if return_code == 0:
                            process_info.status = ProcessStatus.STOPPED
                        else:
                            process_info.status = ProcessStatus.CRASHED
                            process_info.error_message = (
                                f"Process exited with code {return_code}"
                            )

                        break

                    # Update resource usage
                    await self._update_resource_usage(instance_id, process.pid)

                    # Wait before next check
                    await asyncio.sleep(5.0)

                except psutil.NoSuchProcess:
                    # Process no longer exists
                    logger.warning("Process no longer exists", instance_id=instance_id)
                    self._processes[instance_id].status = ProcessStatus.CRASHED
                    break
                except Exception as e:
                    logger.error(
                        "Error monitoring process",
                        instance_id=instance_id,
                        error=str(e),
                    )
                    break

        except Exception as e:
            logger.error(
                "Process monitoring failed", instance_id=instance_id, error=str(e)
            )
        finally:
            logger.debug("Process monitoring ended", instance_id=instance_id)

    async def _update_resource_usage(self, instance_id: str, pid: int) -> None:
        """Update resource usage information for a process.

        Args:
            instance_id: Instance identifier
            pid: Process ID
        """
        try:
            process = psutil.Process(pid)
            process_info = self._processes[instance_id]

            # Get CPU and memory usage
            process_info.cpu_percent = process.cpu_percent()
            process_info.memory_mb = process.memory_info().rss / 1024 / 1024

        except (psutil.NoSuchProcess, psutil.AccessDenied):
            # Process no longer accessible
            pass
        except Exception as e:
            logger.debug(
                "Error updating resource usage", instance_id=instance_id, error=str(e)
            )

    async def _wait_for_process(self, process: subprocess.Popen[bytes]) -> None:
        """Wait for a process to terminate.

        Args:
            process: subprocess.Popen[bytes] object to wait for
        """
        while process.poll() is None:
            await asyncio.sleep(0.1)

    async def _cleanup_process(self, instance_id: str) -> None:
        """Clean up process references and monitoring tasks.

        Args:
            instance_id: Instance identifier
        """
        # Cancel monitoring task
        if instance_id in self._monitoring_tasks:
            task = self._monitoring_tasks.pop(instance_id)
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        # Remove subprocess reference
        if instance_id in self._subprocess_map:
            del self._subprocess_map[instance_id]

        # Update process status
        if instance_id in self._processes:
            process_info = self._processes[instance_id]
            if process_info.status not in [
                ProcessStatus.STOPPED,
                ProcessStatus.CRASHED,
            ]:
                process_info.status = ProcessStatus.STOPPED


class ProcessError(Exception):
    """Exception raised for process management errors."""

    def __init__(
        self, message: str, instance_id: str | None = None, pid: int | None = None
    ):
        """Initialize ProcessError.

        Args:
            message: Error message
            instance_id: Optional instance identifier
            pid: Optional process ID
        """
        super().__init__(message)
        self.instance_id = instance_id
        self.pid = pid


# Global process manager instance
_process_manager: ProcessManager | None = None


def get_process_manager() -> ProcessManager:
    """Get the global process manager instance.

    Returns:
        ProcessManager instance
    """
    global _process_manager
    if _process_manager is None:
        _process_manager = ProcessManager()
    return _process_manager


async def cleanup_process_manager() -> None:
    """Clean up the global process manager."""
    global _process_manager
    if _process_manager is not None:
        await _process_manager.cleanup_all()
        _process_manager = None
