"""Unit tests for process management functionality."""

import asyncio
import os
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cc_orchestrator.utils.process import (
    ProcessError,
    ProcessInfo,
    ProcessManager,
    ProcessStatus,
    cleanup_process_manager,
    get_process_manager,
)


class TestProcessManager:
    """Test ProcessManager class."""

    @pytest.fixture
    def process_manager(self):
        """Create a ProcessManager instance for testing."""
        return ProcessManager()

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            yield Path(tmp_dir)

    def test_process_manager_initialization(self, process_manager):
        """Test ProcessManager initialization."""
        assert process_manager._processes == {}
        assert process_manager._subprocess_map == {}
        assert process_manager._monitoring_tasks == {}
        assert not process_manager._shutdown_event.is_set()

    @pytest.mark.asyncio
    async def test_spawn_claude_process_success(self, process_manager, temp_dir):
        """Test successful Claude process spawning."""
        instance_id = "test-instance-1"

        # Mock subprocess creation
        mock_process = MagicMock()
        mock_process.pid = 12345
        mock_process.poll.return_value = None  # Process is running

        with patch.object(
            process_manager, "_start_process", return_value=mock_process
        ) as mock_start:
            with patch("asyncio.create_task") as mock_create_task:
                mock_task = AsyncMock()
                mock_create_task.return_value = mock_task

                process_info = await process_manager.spawn_claude_process(
                    instance_id=instance_id,
                    working_directory=temp_dir,
                    tmux_session="test-session",
                )

                # Verify process info
                assert process_info.pid == 12345
                assert process_info.status == ProcessStatus.STARTING
                assert process_info.working_directory == temp_dir
                assert (
                    "tmux" in process_info.command[0]
                    or "claude" in process_info.command
                )

                # Verify internal state
                assert instance_id in process_manager._processes
                assert instance_id in process_manager._subprocess_map
                assert instance_id in process_manager._monitoring_tasks

                # Verify mocks were called
                mock_start.assert_called_once()
                mock_create_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_spawn_claude_process_duplicate_instance(
        self, process_manager, temp_dir
    ):
        """Test spawning process for existing instance ID."""
        instance_id = "test-instance-1"

        # Add an existing process
        process_manager._processes[instance_id] = ProcessInfo(
            pid=123,
            status=ProcessStatus.RUNNING,
            command=["test"],
            working_directory=temp_dir,
            environment={},
            started_at=0.0,
        )

        with pytest.raises(ProcessError, match="already exists"):
            await process_manager.spawn_claude_process(
                instance_id=instance_id, working_directory=temp_dir
            )

    @pytest.mark.asyncio
    async def test_spawn_claude_process_failure(self, process_manager, temp_dir):
        """Test process spawn failure."""
        instance_id = "test-instance-1"

        with patch.object(
            process_manager, "_start_process", side_effect=OSError("Failed to start")
        ):
            with pytest.raises(ProcessError, match="Failed to spawn process"):
                await process_manager.spawn_claude_process(
                    instance_id=instance_id, working_directory=temp_dir
                )

    @pytest.mark.asyncio
    async def test_terminate_process_success(self, process_manager, temp_dir):
        """Test successful process termination."""
        instance_id = "test-instance-1"

        # Create mock process
        mock_process = MagicMock()
        mock_process.poll.return_value = None  # Process is running initially
        mock_process.terminate = MagicMock()

        # Add process to manager
        process_info = ProcessInfo(
            pid=12345,
            status=ProcessStatus.RUNNING,
            command=["test"],
            working_directory=temp_dir,
            environment={},
            started_at=0.0,
        )
        process_manager._processes[instance_id] = process_info
        process_manager._subprocess_map[instance_id] = mock_process
        process_manager._monitoring_tasks[instance_id] = AsyncMock()

        # Mock _wait_for_process to simulate successful termination
        with patch.object(process_manager, "_wait_for_process", return_value=None):
            with patch.object(
                process_manager, "_cleanup_process", return_value=None
            ) as mock_cleanup:
                result = await process_manager.terminate_process(instance_id)

                assert result is True
                mock_process.terminate.assert_called_once()
                mock_cleanup.assert_called_once_with(instance_id)

    @pytest.mark.asyncio
    async def test_terminate_process_nonexistent(self, process_manager):
        """Test terminating non-existent process."""
        result = await process_manager.terminate_process("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_terminate_process_force_kill(self, process_manager, temp_dir):
        """Test force killing process after timeout."""
        instance_id = "test-instance-1"

        # Create mock process
        mock_process = MagicMock()
        mock_process.poll.return_value = None  # Process is running
        mock_process.terminate = MagicMock()
        mock_process.kill = MagicMock()

        # Add process to manager
        process_info = ProcessInfo(
            pid=12345,
            status=ProcessStatus.RUNNING,
            command=["test"],
            working_directory=temp_dir,
            environment={},
            started_at=0.0,
        )
        process_manager._processes[instance_id] = process_info
        process_manager._subprocess_map[instance_id] = mock_process
        process_manager._monitoring_tasks[instance_id] = AsyncMock()

        # Mock timeout on graceful termination
        with patch.object(
            process_manager,
            "_wait_for_process",
            side_effect=[TimeoutError(), None],
        ):
            with patch.object(process_manager, "_cleanup_process", return_value=None):
                with patch("asyncio.wait_for", side_effect=TimeoutError()):
                    result = await process_manager.terminate_process(
                        instance_id, timeout=0.1
                    )

                    assert result is True
                    mock_process.terminate.assert_called_once()
                    mock_process.kill.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_process_info(self, process_manager, temp_dir):
        """Test getting process information."""
        instance_id = "test-instance-1"

        # Add process to manager
        process_info = ProcessInfo(
            pid=12345,
            status=ProcessStatus.RUNNING,
            command=["test"],
            working_directory=temp_dir,
            environment={},
            started_at=0.0,
        )
        process_manager._processes[instance_id] = process_info

        result = await process_manager.get_process_info(instance_id)
        assert result == process_info

        # Test non-existent process
        result = await process_manager.get_process_info("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_list_processes(self, process_manager, temp_dir):
        """Test listing all processes."""
        # Add multiple processes
        for i in range(3):
            instance_id = f"test-instance-{i}"
            process_info = ProcessInfo(
                pid=12345 + i,
                status=ProcessStatus.RUNNING,
                command=["test"],
                working_directory=temp_dir,
                environment={},
                started_at=0.0,
            )
            process_manager._processes[instance_id] = process_info

        result = await process_manager.list_processes()
        assert len(result) == 3
        assert all(isinstance(info, ProcessInfo) for info in result.values())

    @pytest.mark.asyncio
    async def test_is_process_running(self, process_manager, temp_dir):
        """Test checking if process is running."""
        instance_id = "test-instance-1"

        # Test non-existent process
        result = await process_manager.is_process_running(instance_id)
        assert result is False

        # Add running process
        process_info = ProcessInfo(
            pid=12345,
            status=ProcessStatus.RUNNING,
            command=["test"],
            working_directory=temp_dir,
            environment={},
            started_at=0.0,
        )
        process_manager._processes[instance_id] = process_info

        result = await process_manager.is_process_running(instance_id)
        assert result is True

        # Change status to stopped
        process_info.status = ProcessStatus.STOPPED
        result = await process_manager.is_process_running(instance_id)
        assert result is False

    @pytest.mark.asyncio
    async def test_cleanup_all(self, process_manager, temp_dir):
        """Test cleaning up all processes."""
        # Add multiple processes
        instances = []
        for i in range(3):
            instance_id = f"test-instance-{i}"
            instances.append(instance_id)

            process_info = ProcessInfo(
                pid=12345 + i,
                status=ProcessStatus.RUNNING,
                command=["test"],
                working_directory=temp_dir,
                environment={},
                started_at=0.0,
            )
            process_manager._processes[instance_id] = process_info
            process_manager._monitoring_tasks[instance_id] = AsyncMock()

        with patch.object(
            process_manager, "terminate_process", return_value=True
        ) as mock_terminate:
            await process_manager.cleanup_all()

            # Verify all processes were terminated
            assert mock_terminate.call_count == 3

            # Verify cleanup
            assert len(process_manager._processes) == 0
            assert len(process_manager._subprocess_map) == 0
            assert len(process_manager._monitoring_tasks) == 0
            assert process_manager._shutdown_event.is_set()

    def test_build_claude_command_direct(self, process_manager, temp_dir):
        """Test building Claude command without tmux."""
        command = process_manager._build_claude_command(
            working_directory=temp_dir, tmux_session=None
        )

        assert command == ["claude", "--continue"]

    def test_build_claude_command_tmux(self, process_manager, temp_dir):
        """Test building Claude command with tmux."""
        command = process_manager._build_claude_command(
            working_directory=temp_dir, tmux_session="test-session"
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
        environment = {"TEST_VAR": "test_value"}

        process = await process_manager._start_process(
            command=command, working_directory=temp_dir, environment=environment
        )

        assert isinstance(process, subprocess.Popen)
        assert process.returncode is None or process.returncode == 0

        # Clean up
        if process.poll() is None:
            process.terminate()
            process.wait()

    @pytest.mark.asyncio
    async def test_monitor_process_success(self, process_manager, temp_dir):
        """Test process monitoring for successful process."""
        instance_id = "test-instance-1"

        # Create a real process that will exit quickly
        mock_process = MagicMock()
        mock_process.pid = 12345
        mock_process.poll.side_effect = [
            None,
            None,
            0,
        ]  # Running, then exits with code 0

        # Add process to manager
        process_info = ProcessInfo(
            pid=12345,
            status=ProcessStatus.STARTING,
            command=["test"],
            working_directory=temp_dir,
            environment={},
            started_at=0.0,
        )
        process_manager._processes[instance_id] = process_info

        with patch.object(process_manager, "_update_resource_usage", return_value=None):
            # Run monitor for a short time
            monitor_task = asyncio.create_task(
                process_manager._monitor_process(instance_id, mock_process)
            )

            # Let it run briefly
            await asyncio.sleep(0.1)

            # Check that status was updated to running
            assert process_info.status == ProcessStatus.RUNNING

            # Cancel the task
            monitor_task.cancel()
            try:
                await monitor_task
            except asyncio.CancelledError:
                pass

    @pytest.mark.asyncio
    async def test_update_resource_usage(self, process_manager, temp_dir):
        """Test updating resource usage."""
        instance_id = "test-instance-1"
        pid = os.getpid()  # Use current process PID

        # Add process to manager
        process_info = ProcessInfo(
            pid=pid,
            status=ProcessStatus.RUNNING,
            command=["test"],
            working_directory=temp_dir,
            environment={},
            started_at=0.0,
        )
        process_manager._processes[instance_id] = process_info

        await process_manager._update_resource_usage(instance_id, pid)

        # Resource usage should be updated
        assert process_info.cpu_percent >= 0
        assert process_info.memory_mb > 0

    @pytest.mark.asyncio
    async def test_update_resource_usage_no_process(self, process_manager, temp_dir):
        """Test updating resource usage for non-existent process."""
        instance_id = "test-instance-1"
        pid = 999999  # Non-existent PID

        # Add process to manager
        process_info = ProcessInfo(
            pid=pid,
            status=ProcessStatus.RUNNING,
            command=["test"],
            working_directory=temp_dir,
            environment={},
            started_at=0.0,
        )
        process_manager._processes[instance_id] = process_info

        # Should not raise exception
        await process_manager._update_resource_usage(instance_id, pid)

    @pytest.mark.asyncio
    async def test_wait_for_process(self, process_manager):
        """Test waiting for process termination."""
        mock_process = MagicMock()
        mock_process.poll.side_effect = [None, None, 0]  # Running, then terminated

        # This should complete after a few poll attempts
        with patch("asyncio.sleep", return_value=None):  # Speed up the test
            await process_manager._wait_for_process(mock_process)

        assert mock_process.poll.call_count >= 3

    @pytest.mark.asyncio
    async def test_cleanup_process(self, process_manager, temp_dir):
        """Test cleaning up process references."""
        instance_id = "test-instance-1"

        # Add process references
        process_info = ProcessInfo(
            pid=12345,
            status=ProcessStatus.RUNNING,
            command=["test"],
            working_directory=temp_dir,
            environment={},
            started_at=0.0,
        )
        process_manager._processes[instance_id] = process_info
        process_manager._subprocess_map[instance_id] = MagicMock()

        # Add monitoring task
        mock_task = MagicMock()
        mock_task.done.return_value = False
        mock_task.cancel = MagicMock()
        process_manager._monitoring_tasks[instance_id] = mock_task

        await process_manager._cleanup_process(instance_id)

        # Verify cleanup
        assert instance_id not in process_manager._subprocess_map
        assert instance_id not in process_manager._monitoring_tasks
        mock_task.cancel.assert_called_once()

        # Process info should still exist but status updated
        assert instance_id in process_manager._processes
        assert process_info.status == ProcessStatus.STOPPED


class TestProcessError:
    """Test ProcessError exception."""

    def test_process_error_basic(self):
        """Test basic ProcessError creation."""
        error = ProcessError("Test error")
        assert str(error) == "Test error"
        assert error.instance_id is None
        assert error.pid is None

    def test_process_error_with_details(self):
        """Test ProcessError with instance and PID details."""
        error = ProcessError("Test error", instance_id="instance-1", pid=12345)
        assert str(error) == "Test error"
        assert error.instance_id == "instance-1"
        assert error.pid == 12345


class TestGlobalProcessManager:
    """Test global process manager functions."""

    def test_get_process_manager_singleton(self):
        """Test that get_process_manager returns the same instance."""
        manager1 = get_process_manager()
        manager2 = get_process_manager()
        assert manager1 is manager2
        assert isinstance(manager1, ProcessManager)

    @pytest.mark.asyncio
    async def test_cleanup_process_manager(self):
        """Test cleaning up the global process manager."""
        # Get the global manager
        manager = get_process_manager()

        with patch.object(manager, "cleanup_all", return_value=None) as mock_cleanup:
            await cleanup_process_manager()
            mock_cleanup.assert_called_once()

        # After cleanup, a new manager should be created
        new_manager = get_process_manager()
        assert new_manager is not manager


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

    def test_process_info_creation(self):
        """Test ProcessInfo creation and attributes."""
        temp_dir = Path("/tmp/test")
        process_info = ProcessInfo(
            pid=12345,
            status=ProcessStatus.RUNNING,
            command=["test", "command"],
            working_directory=temp_dir,
            environment={"TEST": "value"},
            started_at=1234567890.0,
        )

        assert process_info.pid == 12345
        assert process_info.status == ProcessStatus.RUNNING
        assert process_info.command == ["test", "command"]
        assert process_info.working_directory == temp_dir
        assert process_info.environment == {"TEST": "value"}
        assert process_info.started_at == 1234567890.0
        assert process_info.cpu_percent == 0.0
        assert process_info.memory_mb == 0.0
        assert process_info.return_code is None
        assert process_info.error_message is None

    def test_process_info_with_optional_fields(self):
        """Test ProcessInfo with optional fields set."""
        temp_dir = Path("/tmp/test")
        process_info = ProcessInfo(
            pid=12345,
            status=ProcessStatus.CRASHED,
            command=["test"],
            working_directory=temp_dir,
            environment={},
            started_at=0.0,
            cpu_percent=25.5,
            memory_mb=128.0,
            return_code=1,
            error_message="Process crashed",
        )

        assert process_info.cpu_percent == 25.5
        assert process_info.memory_mb == 128.0
        assert process_info.return_code == 1
        assert process_info.error_message == "Process crashed"
