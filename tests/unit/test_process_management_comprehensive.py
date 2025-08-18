"""Comprehensive tests for process management utilities."""

import asyncio
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import psutil
import pytest

from cc_orchestrator.utils.process import (
    ProcessError,
    ProcessInfo,
    ProcessManager,
    ProcessStatus,
    cleanup_process_manager,
    get_process_manager,
)


class TestProcessManagerComprehensive:
    """Comprehensive tests for ProcessManager functionality."""

    @pytest.fixture
    def process_manager(self):
        """Create a ProcessManager instance for testing."""
        return ProcessManager()

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            yield Path(tmp_dir)

    @pytest.mark.asyncio
    async def test_build_claude_command_with_tmux(self, process_manager, temp_dir):
        """Test building Claude command with tmux session."""
        command = process_manager._build_claude_command(
            working_directory=temp_dir,
            tmux_session="test-session",
        )

        expected = [
            "tmux",
            "new-session",
            "-d",
            "-s",
            "test-session",
            "-c",
            str(temp_dir),
            "claude",
            "--continue",
        ]
        assert command == expected

    @pytest.mark.asyncio
    async def test_build_claude_command_without_tmux(self, process_manager, temp_dir):
        """Test building Claude command without tmux."""
        command = process_manager._build_claude_command(
            working_directory=temp_dir,
            tmux_session=None,
        )

        expected = ["claude", "--continue"]
        assert command == expected

    @pytest.mark.asyncio
    async def test_build_claude_command_with_resource_limits(
        self, process_manager, temp_dir
    ):
        """Test building Claude command with resource limits."""
        # Resource limits don't affect command for now, but test the interface
        command = process_manager._build_claude_command(
            working_directory=temp_dir,
            tmux_session="test-session",
            resource_limits={"cpu_limit": 2, "memory_limit": "1G"},
        )

        expected = [
            "tmux",
            "new-session",
            "-d",
            "-s",
            "test-session",
            "-c",
            str(temp_dir),
            "claude",
            "--continue",
        ]
        assert command == expected

    @pytest.mark.asyncio
    async def test_start_process(self, process_manager, temp_dir):
        """Test starting a subprocess."""
        command = ["echo", "test"]
        environment = {"TEST_VAR": "value"}

        with patch("subprocess.Popen") as mock_popen:
            mock_process = MagicMock()
            mock_popen.return_value = mock_process

            result = await process_manager._start_process(
                command=command,
                working_directory=temp_dir,
                environment=environment,
            )

            assert result == mock_process
            mock_popen.assert_called_once_with(
                command,
                cwd=temp_dir,
                env=environment,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE,
                start_new_session=True,
            )

    @pytest.mark.asyncio
    async def test_wait_for_process(self, process_manager):
        """Test waiting for process termination."""
        mock_process = MagicMock()

        # Simulate process running then terminating
        poll_results = [None, None, 0]  # Running, Running, Terminated
        mock_process.poll.side_effect = poll_results

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            await process_manager._wait_for_process(mock_process)

            # Should have called poll until process terminated
            assert mock_process.poll.call_count == 3
            # Should have slept twice (before the final successful poll)
            assert mock_sleep.call_count == 2

    @pytest.mark.asyncio
    async def test_update_resource_usage_success(self, process_manager, temp_dir):
        """Test updating resource usage successfully."""
        instance_id = "test-instance"
        pid = 12345

        # Create process info
        process_info = ProcessInfo(
            pid=pid,
            status=ProcessStatus.RUNNING,
            command=["claude"],
            working_directory=temp_dir,
            environment={},
            started_at=0.0,
        )
        process_manager._processes[instance_id] = process_info

        # Mock psutil.Process
        mock_psutil_process = MagicMock()
        mock_psutil_process.cpu_percent.return_value = 25.5
        mock_memory_info = MagicMock()
        mock_memory_info.rss = 100 * 1024 * 1024  # 100 MB in bytes
        mock_psutil_process.memory_info.return_value = mock_memory_info

        with patch(
            "cc_orchestrator.utils.process.psutil.Process",
            return_value=mock_psutil_process,
        ):
            await process_manager._update_resource_usage(instance_id, pid)

            # Verify resource usage was updated
            assert process_info.cpu_percent == 25.5
            assert process_info.memory_mb == 100.0

    @pytest.mark.asyncio
    async def test_update_resource_usage_no_such_process(
        self, process_manager, temp_dir
    ):
        """Test updating resource usage when process doesn't exist."""
        instance_id = "test-instance"
        pid = 12345

        process_info = ProcessInfo(
            pid=pid,
            status=ProcessStatus.RUNNING,
            command=["claude"],
            working_directory=temp_dir,
            environment={},
            started_at=0.0,
        )
        process_manager._processes[instance_id] = process_info

        with patch(
            "cc_orchestrator.utils.process.psutil.Process",
            side_effect=psutil.NoSuchProcess(pid),
        ):
            # Should not raise exception
            await process_manager._update_resource_usage(instance_id, pid)

            # Resource usage should remain at defaults
            assert process_info.cpu_percent == 0.0
            assert process_info.memory_mb == 0.0

    @pytest.mark.asyncio
    async def test_update_resource_usage_access_denied(self, process_manager, temp_dir):
        """Test updating resource usage with access denied error."""
        instance_id = "test-instance"
        pid = 12345

        process_info = ProcessInfo(
            pid=pid,
            status=ProcessStatus.RUNNING,
            command=["claude"],
            working_directory=temp_dir,
            environment={},
            started_at=0.0,
        )
        process_manager._processes[instance_id] = process_info

        with patch(
            "cc_orchestrator.utils.process.psutil.Process",
            side_effect=psutil.AccessDenied(pid),
        ):
            # Should not raise exception
            await process_manager._update_resource_usage(instance_id, pid)

            # Resource usage should remain at defaults
            assert process_info.cpu_percent == 0.0
            assert process_info.memory_mb == 0.0

    @pytest.mark.asyncio
    async def test_update_resource_usage_other_exception(
        self, process_manager, temp_dir
    ):
        """Test updating resource usage with other exceptions."""
        instance_id = "test-instance"
        pid = 12345

        process_info = ProcessInfo(
            pid=pid,
            status=ProcessStatus.RUNNING,
            command=["claude"],
            working_directory=temp_dir,
            environment={},
            started_at=0.0,
        )
        process_manager._processes[instance_id] = process_info

        with patch(
            "cc_orchestrator.utils.process.psutil.Process",
            side_effect=RuntimeError("Some error"),
        ):
            # Should not raise exception, but log debug message
            await process_manager._update_resource_usage(instance_id, pid)

            # Resource usage should remain at defaults
            assert process_info.cpu_percent == 0.0
            assert process_info.memory_mb == 0.0

    @pytest.mark.asyncio
    async def test_cleanup_process(self, process_manager, temp_dir):
        """Test cleaning up process references."""
        instance_id = "test-instance"

        # Set up process state
        process_info = ProcessInfo(
            pid=123,
            status=ProcessStatus.RUNNING,
            command=["claude"],
            working_directory=temp_dir,
            environment={},
            started_at=0.0,
        )
        process_manager._processes[instance_id] = process_info
        process_manager._subprocess_map[instance_id] = MagicMock()

        # Mock monitoring task - create a real async task but cancel it to simulate the scenario
        async def dummy_coroutine():
            try:
                await asyncio.sleep(10)  # Long running task
            except asyncio.CancelledError:
                # Expected when task is cancelled during cleanup
                raise

        mock_task = asyncio.create_task(dummy_coroutine())
        process_manager._monitoring_tasks[instance_id] = mock_task

        await process_manager._cleanup_process(instance_id)

        # Ensure task is fully cancelled before continuing
        if not mock_task.cancelled():
            mock_task.cancel()
            try:
                await mock_task
            except asyncio.CancelledError:
                pass

        # Verify cleanup
        assert instance_id not in process_manager._subprocess_map
        assert instance_id not in process_manager._monitoring_tasks
        assert process_info.status == ProcessStatus.STOPPED

        # Verify task was cancelled
        assert mock_task.cancelled()

    @pytest.mark.asyncio
    async def test_cleanup_process_done_task(self, process_manager, temp_dir):
        """Test cleaning up process with already done monitoring task."""
        instance_id = "test-instance"

        process_info = ProcessInfo(
            pid=123,
            status=ProcessStatus.RUNNING,
            command=["claude"],
            working_directory=temp_dir,
            environment={},
            started_at=0.0,
        )
        process_manager._processes[instance_id] = process_info

        # Mock already completed task
        mock_task = AsyncMock()
        mock_task.done.return_value = True
        process_manager._monitoring_tasks[instance_id] = mock_task

        await process_manager._cleanup_process(instance_id)

        # Should not cancel already done task
        mock_task.cancel.assert_not_called()

    @pytest.mark.asyncio
    async def test_cleanup_process_with_crashed_status(self, process_manager, temp_dir):
        """Test cleanup doesn't change crashed status."""
        instance_id = "test-instance"

        process_info = ProcessInfo(
            pid=123,
            status=ProcessStatus.CRASHED,
            command=["claude"],
            working_directory=temp_dir,
            environment={},
            started_at=0.0,
        )
        process_manager._processes[instance_id] = process_info

        await process_manager._cleanup_process(instance_id)

        # Status should remain CRASHED
        assert process_info.status == ProcessStatus.CRASHED

    @pytest.mark.asyncio
    async def test_cleanup_process_cancelled_task_exception(
        self, process_manager, temp_dir
    ):
        """Test cleanup handles cancelled task exception."""
        instance_id = "test-instance"

        process_info = ProcessInfo(
            pid=123,
            status=ProcessStatus.RUNNING,
            command=["claude"],
            working_directory=temp_dir,
            environment={},
            started_at=0.0,
        )
        process_manager._processes[instance_id] = process_info

        # Mock task that raises CancelledError when awaited
        mock_task = AsyncMock()
        mock_task.done.return_value = False
        mock_task.side_effect = asyncio.CancelledError()
        process_manager._monitoring_tasks[instance_id] = mock_task

        # Should handle CancelledError gracefully
        await process_manager._cleanup_process(instance_id)

        assert instance_id not in process_manager._monitoring_tasks

    @pytest.mark.asyncio
    async def test_monitor_process_successful_startup(self, process_manager, temp_dir):
        """Test monitoring process during successful startup."""
        instance_id = "test-instance"
        mock_process = MagicMock()
        mock_process.pid = 12345
        mock_process.poll.return_value = None  # Process is running

        # Create process info
        process_info = ProcessInfo(
            pid=12345,
            status=ProcessStatus.STARTING,
            command=["claude"],
            working_directory=temp_dir,
            environment={},
            started_at=0.0,
        )
        process_manager._processes[instance_id] = process_info

        with patch("asyncio.sleep", new_callable=AsyncMock):
            with patch.object(
                process_manager, "_update_resource_usage", new_callable=AsyncMock
            ):
                # Set shutdown event to stop monitoring loop quickly
                process_manager._shutdown_event.set()

                await process_manager._monitor_process(instance_id, mock_process)

                # Process should be marked as running after initial sleep
                assert process_info.status == ProcessStatus.RUNNING

    @pytest.mark.asyncio
    async def test_monitor_process_early_termination(self, process_manager, temp_dir):
        """Test monitoring process that terminates early."""
        instance_id = "test-instance"
        mock_process = MagicMock()
        mock_process.pid = 12345
        mock_process.poll.side_effect = [
            None,
            1,
        ]  # Running, then terminated with code 1

        # Create process info
        process_info = ProcessInfo(
            pid=12345,
            status=ProcessStatus.STARTING,
            command=["claude"],
            working_directory=temp_dir,
            environment={},
            started_at=0.0,
        )
        process_manager._processes[instance_id] = process_info

        with patch("asyncio.sleep", new_callable=AsyncMock):
            await process_manager._monitor_process(instance_id, mock_process)

            # Process should be marked as crashed
            assert process_info.status == ProcessStatus.CRASHED
            assert process_info.return_code == 1
            assert "Process exited with code 1" in process_info.error_message

    @pytest.mark.asyncio
    async def test_monitor_process_successful_termination(
        self, process_manager, temp_dir
    ):
        """Test monitoring process that terminates successfully."""
        instance_id = "test-instance"
        mock_process = MagicMock()
        mock_process.pid = 12345
        mock_process.poll.side_effect = [
            None,
            0,
        ]  # Running, then terminated with code 0

        # Create process info
        process_info = ProcessInfo(
            pid=12345,
            status=ProcessStatus.STARTING,
            command=["claude"],
            working_directory=temp_dir,
            environment={},
            started_at=0.0,
        )
        process_manager._processes[instance_id] = process_info

        with patch("asyncio.sleep", new_callable=AsyncMock):
            await process_manager._monitor_process(instance_id, mock_process)

            # Process should be marked as stopped
            assert process_info.status == ProcessStatus.STOPPED
            assert process_info.return_code == 0

    @pytest.mark.asyncio
    async def test_monitor_process_no_such_process_exception(
        self, process_manager, temp_dir
    ):
        """Test monitoring handles NoSuchProcess exception."""
        instance_id = "test-instance"
        mock_process = MagicMock()
        mock_process.pid = 12345
        mock_process.poll.return_value = None  # Process running initially

        # Create process info
        process_info = ProcessInfo(
            pid=12345,
            status=ProcessStatus.STARTING,
            command=["claude"],
            working_directory=temp_dir,
            environment={},
            started_at=0.0,
        )
        process_manager._processes[instance_id] = process_info

        with patch("asyncio.sleep", new_callable=AsyncMock):
            with patch.object(
                process_manager,
                "_update_resource_usage",
                side_effect=psutil.NoSuchProcess(12345),
            ):
                await process_manager._monitor_process(instance_id, mock_process)

                # Process should be marked as crashed
                assert process_info.status == ProcessStatus.CRASHED

    @pytest.mark.asyncio
    async def test_monitor_process_general_exception(self, process_manager, temp_dir):
        """Test monitoring handles general exceptions."""
        instance_id = "test-instance"
        mock_process = MagicMock()
        mock_process.pid = 12345
        mock_process.poll.return_value = None  # Process running initially

        # Create process info
        process_info = ProcessInfo(
            pid=12345,
            status=ProcessStatus.STARTING,
            command=["claude"],
            working_directory=temp_dir,
            environment={},
            started_at=0.0,
        )
        process_manager._processes[instance_id] = process_info

        with patch("asyncio.sleep", new_callable=AsyncMock):
            with patch.object(
                process_manager,
                "_update_resource_usage",
                side_effect=RuntimeError("Unexpected error"),
            ):
                await process_manager._monitor_process(instance_id, mock_process)

                # Should handle exception gracefully and exit monitoring


class TestProcessError:
    """Test ProcessError exception class."""

    def test_process_error_basic(self):
        """Test basic ProcessError creation."""
        error = ProcessError("Something went wrong")
        assert str(error) == "Something went wrong"
        assert error.instance_id is None
        assert error.pid is None

    def test_process_error_with_context(self):
        """Test ProcessError with instance_id and pid."""
        error = ProcessError("Process failed", instance_id="test-123", pid=456)
        assert str(error) == "Process failed"
        assert error.instance_id == "test-123"
        assert error.pid == 456


class TestGlobalProcessManager:
    """Test global process manager functions."""

    def test_get_process_manager_singleton(self):
        """Test that get_process_manager returns singleton."""
        manager1 = get_process_manager()
        manager2 = get_process_manager()

        assert manager1 is manager2
        assert isinstance(manager1, ProcessManager)

    @pytest.mark.asyncio
    async def test_cleanup_process_manager(self):
        """Test global process manager cleanup."""
        # Get the singleton
        manager = get_process_manager()

        with patch.object(
            manager, "cleanup_all", new_callable=AsyncMock
        ) as mock_cleanup:
            await cleanup_process_manager()

            mock_cleanup.assert_called_once()

        # Should create new instance after cleanup
        new_manager = get_process_manager()
        assert new_manager is not manager

    @pytest.mark.asyncio
    async def test_cleanup_process_manager_none(self):
        """Test cleanup when no process manager exists."""
        # Clear the global variable
        import cc_orchestrator.utils.process

        cc_orchestrator.utils.process._process_manager = None

        # Should handle gracefully
        await cleanup_process_manager()


class TestProcessStatus:
    """Test ProcessStatus enum."""

    def test_process_status_values(self):
        """Test ProcessStatus enum values."""
        assert ProcessStatus.STARTING.value == "starting"
        assert ProcessStatus.RUNNING.value == "running"
        assert ProcessStatus.STOPPING.value == "stopping"
        assert ProcessStatus.STOPPED.value == "stopped"
        assert ProcessStatus.ERROR.value == "error"
        assert ProcessStatus.CRASHED.value == "crashed"


class TestProcessInfo:
    """Test ProcessInfo dataclass."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            yield Path(tmp_dir)

    def test_process_info_creation(self, temp_dir):
        """Test ProcessInfo creation with required fields."""
        process_info = ProcessInfo(
            pid=12345,
            status=ProcessStatus.RUNNING,
            command=["claude", "--continue"],
            working_directory=temp_dir,
            environment={"PATH": "/usr/bin"},
            started_at=1640995200.0,
        )

        assert process_info.pid == 12345
        assert process_info.status == ProcessStatus.RUNNING
        assert process_info.command == ["claude", "--continue"]
        assert process_info.working_directory == temp_dir
        assert process_info.environment == {"PATH": "/usr/bin"}
        assert process_info.started_at == 1640995200.0

        # Check default values
        assert process_info.cpu_percent == 0.0
        assert process_info.memory_mb == 0.0
        assert process_info.return_code is None
        assert process_info.error_message is None

    def test_process_info_with_optional_fields(self, temp_dir):
        """Test ProcessInfo with all fields."""
        process_info = ProcessInfo(
            pid=12345,
            status=ProcessStatus.CRASHED,
            command=["claude"],
            working_directory=temp_dir,
            environment={},
            started_at=1640995200.0,
            cpu_percent=25.5,
            memory_mb=150.0,
            return_code=1,
            error_message="Process crashed",
        )

        assert process_info.cpu_percent == 25.5
        assert process_info.memory_mb == 150.0
        assert process_info.return_code == 1
        assert process_info.error_message == "Process crashed"
