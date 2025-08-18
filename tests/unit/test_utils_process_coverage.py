"""
Comprehensive test coverage for cc_orchestrator.utils.process module.

This test file targets high coverage to help reach 90% total coverage by focusing on:
- Process creation and management edge cases
- Subprocess execution monitoring and lifecycle
- Signal handling and process communication
- Timeout handling and resource management
- Error paths and exception scenarios
- Environment variable handling
- Process cleanup and termination scenarios
"""

import asyncio
import os
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


class TestProcessManagerAdvanced:
    """Advanced tests for ProcessManager with comprehensive coverage."""

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
    async def test_spawn_claude_process_with_environment_merge(
        self, process_manager, temp_dir
    ):
        """Test environment variable merging during process spawn."""
        instance_id = "test-env-merge"
        custom_env = {"CUSTOM_VAR": "custom_value", "PATH": "/custom/path"}

        mock_process = MagicMock()
        mock_process.pid = 12345
        mock_process.poll.return_value = None

        with patch.object(
            process_manager, "_start_process", return_value=mock_process
        ) as mock_start:
            with patch.object(process_manager, "_monitor_process"):
                with patch("asyncio.create_task"):
                    with patch.dict(os.environ, {"EXISTING_VAR": "existing_value"}):
                        await process_manager.spawn_claude_process(
                            instance_id=instance_id,
                            working_directory=temp_dir,
                            environment=custom_env,
                        )

                        # Verify environment merging
                        call_args = mock_start.call_args
                        passed_env = call_args.kwargs["environment"]
                        assert "EXISTING_VAR" in passed_env
                        assert "CUSTOM_VAR" in passed_env
                        assert passed_env["CUSTOM_VAR"] == "custom_value"
                        assert "PATH" in passed_env

    @pytest.mark.asyncio
    async def test_spawn_claude_process_directory_creation(self, process_manager):
        """Test working directory creation during process spawn."""
        instance_id = "test-dir-creation"
        non_existent_dir = Path("/tmp/test_nonexistent_dir_12345")

        mock_process = MagicMock()
        mock_process.pid = 12345
        mock_process.poll.return_value = None

        try:
            with patch.object(
                process_manager, "_start_process", return_value=mock_process
            ):
                with patch.object(process_manager, "_monitor_process"):
                    with patch("asyncio.create_task"):
                        await process_manager.spawn_claude_process(
                            instance_id=instance_id,
                            working_directory=non_existent_dir,
                        )

                        # Directory should be created
                        assert non_existent_dir.exists()
        finally:
            # Cleanup
            if non_existent_dir.exists():
                non_existent_dir.rmdir()

    @pytest.mark.asyncio
    async def test_spawn_claude_process_with_resource_limits(
        self, process_manager, temp_dir
    ):
        """Test process spawning with resource limits."""
        instance_id = "test-resource-limits"
        resource_limits = {"cpu_percent": 50, "memory_mb": 512}

        mock_process = MagicMock()
        mock_process.pid = 12345
        mock_process.poll.return_value = None

        with patch.object(process_manager, "_start_process", return_value=mock_process):
            with patch.object(process_manager, "_monitor_process"):
                with patch("asyncio.create_task"):
                    result = await process_manager.spawn_claude_process(
                        instance_id=instance_id,
                        working_directory=temp_dir,
                        resource_limits=resource_limits,
                    )

                    assert result.status == ProcessStatus.STARTING
                    assert instance_id in process_manager._processes

    @pytest.mark.asyncio
    async def test_terminate_process_already_terminated(
        self, process_manager, temp_dir
    ):
        """Test terminating a process that's already terminated."""
        instance_id = "test-already-terminated"

        mock_process = MagicMock()
        mock_process.poll.return_value = 0  # Already terminated

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

        with patch.object(process_manager, "_cleanup_process") as mock_cleanup:
            result = await process_manager.terminate_process(instance_id)

            assert result is True
            mock_cleanup.assert_called_once_with(instance_id)
            # terminate() should not be called since process is already dead
            mock_process.terminate.assert_not_called()

    @pytest.mark.asyncio
    async def test_terminate_process_graceful_timeout(self, process_manager, temp_dir):
        """Test process termination with graceful timeout leading to force kill."""
        instance_id = "test-timeout"

        mock_process = MagicMock()
        mock_process.poll.return_value = None  # Process is running
        mock_process.terminate = MagicMock()
        mock_process.kill = MagicMock()

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

        # Mock timeout during graceful termination
        async def mock_wait_timeout(*args, **kwargs):
            raise TimeoutError("Graceful termination timed out")

        with patch.object(
            process_manager, "_wait_for_process", side_effect=[mock_wait_timeout, None]
        ):
            with patch.object(process_manager, "_cleanup_process") as mock_cleanup:
                with patch("asyncio.wait_for", side_effect=TimeoutError):
                    result = await process_manager.terminate_process(
                        instance_id, timeout=0.1
                    )

                    assert result is True
                    mock_process.terminate.assert_called_once()
                    mock_process.kill.assert_called_once()
                    mock_cleanup.assert_called_once_with(instance_id)
                    assert process_info.status == ProcessStatus.STOPPING

    @pytest.mark.asyncio
    async def test_terminate_process_exception_handling(
        self, process_manager, temp_dir
    ):
        """Test exception handling during process termination."""
        instance_id = "test-exception"

        mock_process = MagicMock()
        mock_process.poll.return_value = None
        mock_process.terminate.side_effect = OSError("Failed to terminate")

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

        with patch.object(process_manager, "_cleanup_process") as mock_cleanup:
            result = await process_manager.terminate_process(instance_id)

            assert result is False
            mock_cleanup.assert_called_once_with(instance_id)

    @pytest.mark.asyncio
    async def test_cleanup_all_with_multiple_processes(self, process_manager, temp_dir):
        """Test cleanup_all with multiple processes and monitoring tasks."""
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

            # Add mock subprocess and monitoring task
            mock_subprocess = MagicMock()
            mock_subprocess.poll.return_value = None
            process_manager._subprocess_map[instance_id] = mock_subprocess

            # Create a real asyncio task that we can control
            async def dummy_monitor():
                await asyncio.sleep(10)  # Long running task

            mock_task = asyncio.create_task(dummy_monitor())
            process_manager._monitoring_tasks[instance_id] = mock_task

        async def mock_terminate(instance_id, timeout=30.0):
            return True

        with patch.object(
            process_manager, "terminate_process", side_effect=mock_terminate
        ) as mock_terminate_patch:
            await process_manager.cleanup_all()

            # Verify all processes were terminated
            assert mock_terminate_patch.call_count == 3

            # Verify shutdown event is set
            assert process_manager._shutdown_event.is_set()

            # Verify all data structures are cleared
            assert len(process_manager._processes) == 0
            assert len(process_manager._subprocess_map) == 0
            assert len(process_manager._monitoring_tasks) == 0

    @pytest.mark.asyncio
    async def test_cleanup_all_with_completed_monitoring_tasks(
        self, process_manager, temp_dir
    ):
        """Test cleanup_all with some completed monitoring tasks."""
        instance_id = "test-completed-task"
        process_info = ProcessInfo(
            pid=12345,
            status=ProcessStatus.RUNNING,
            command=["test"],
            working_directory=temp_dir,
            environment={},
            started_at=0.0,
        )
        process_manager._processes[instance_id] = process_info

        # Add completed monitoring task
        async def completed_monitor():
            return True  # Simple completed task

        mock_task = asyncio.create_task(completed_monitor())
        await mock_task  # Let it complete
        process_manager._monitoring_tasks[instance_id] = mock_task

        async def mock_terminate(instance_id, timeout=30.0):
            return True

        with patch.object(
            process_manager, "terminate_process", side_effect=mock_terminate
        ):
            await process_manager.cleanup_all()

            # Completed task should remain done (not cancelled)
            assert mock_task.done()
            assert not mock_task.cancelled()

    @pytest.mark.asyncio
    async def test_monitor_process_startup_sequence(self, process_manager, temp_dir):
        """Test process monitoring startup sequence."""
        instance_id = "test-startup"

        mock_process = MagicMock()
        mock_process.poll.side_effect = [None, None, 0]  # Running, then exits
        mock_process.pid = 12345

        process_info = ProcessInfo(
            pid=12345,
            status=ProcessStatus.STARTING,
            command=["test"],
            working_directory=temp_dir,
            environment={},
            started_at=0.0,
        )
        process_manager._processes[instance_id] = process_info

        with patch("asyncio.sleep", return_value=None):
            with patch.object(process_manager, "_update_resource_usage"):
                # Run monitoring for a short time
                task = asyncio.create_task(
                    process_manager._monitor_process(instance_id, mock_process)
                )

                # Let it run briefly then signal shutdown
                await asyncio.sleep(0.01)
                process_manager._shutdown_event.set()

                try:
                    await asyncio.wait_for(task, timeout=1.0)
                except TimeoutError:
                    task.cancel()

                # Status should have been updated to RUNNING initially
                assert process_info.status in [
                    ProcessStatus.RUNNING,
                    ProcessStatus.STOPPED,
                ]

    @pytest.mark.asyncio
    async def test_monitor_process_exit_codes(self, process_manager, temp_dir):
        """Test monitoring process with different exit codes."""
        instance_id = "test-exit-codes"

        process_info = ProcessInfo(
            pid=12345,
            status=ProcessStatus.STARTING,
            command=["test"],
            working_directory=temp_dir,
            environment={},
            started_at=0.0,
        )
        process_manager._processes[instance_id] = process_info

        # Test successful exit (code 0)
        mock_process = MagicMock()
        mock_process.poll.side_effect = [None, 0]  # Running, then exits with 0
        mock_process.pid = 12345

        with patch("asyncio.sleep", return_value=None):
            with patch.object(process_manager, "_update_resource_usage"):
                await process_manager._monitor_process(instance_id, mock_process)

                assert process_info.status == ProcessStatus.STOPPED
                assert process_info.return_code == 0

        # Reset for crash test
        process_info.status = ProcessStatus.STARTING
        process_info.return_code = None
        process_info.error_message = None

        # Test crash (non-zero exit code)
        mock_process.poll.side_effect = [None, 1]  # Running, then exits with 1

        with patch("asyncio.sleep", return_value=None):
            with patch.object(process_manager, "_update_resource_usage"):
                await process_manager._monitor_process(instance_id, mock_process)

                assert process_info.status == ProcessStatus.CRASHED
                assert process_info.return_code == 1
                assert "Process exited with code 1" in process_info.error_message

    @pytest.mark.asyncio
    async def test_monitor_process_psutil_exceptions(self, process_manager, temp_dir):
        """Test monitoring process with psutil exceptions."""
        instance_id = "test-psutil-exceptions"

        mock_process = MagicMock()
        mock_process.poll.side_effect = [None, psutil.NoSuchProcess(12345)]
        mock_process.pid = 12345

        process_info = ProcessInfo(
            pid=12345,
            status=ProcessStatus.STARTING,
            command=["test"],
            working_directory=temp_dir,
            environment={},
            started_at=0.0,
        )
        process_manager._processes[instance_id] = process_info

        with patch("asyncio.sleep", return_value=None):
            await process_manager._monitor_process(instance_id, mock_process)

            assert process_info.status == ProcessStatus.CRASHED

    @pytest.mark.asyncio
    async def test_monitor_process_general_exception(self, process_manager, temp_dir):
        """Test monitoring process with general exception in monitoring loop."""
        instance_id = "test-general-exception"

        mock_process = MagicMock()
        mock_process.poll.side_effect = [None, Exception("Unexpected error")]
        mock_process.pid = 12345

        process_info = ProcessInfo(
            pid=12345,
            status=ProcessStatus.STARTING,
            command=["test"],
            working_directory=temp_dir,
            environment={},
            started_at=0.0,
        )
        process_manager._processes[instance_id] = process_info

        with patch("asyncio.sleep", return_value=None):
            # Should not raise exception, just log and exit
            await process_manager._monitor_process(instance_id, mock_process)

    @pytest.mark.asyncio
    async def test_monitor_process_outer_exception(self, process_manager, temp_dir):
        """Test monitoring process with exception in outer try block."""
        instance_id = "test-outer-exception"

        mock_process = MagicMock()
        mock_process.poll.return_value = None
        mock_process.pid = 12345

        process_info = ProcessInfo(
            pid=12345,
            status=ProcessStatus.STARTING,
            command=["test"],
            working_directory=temp_dir,
            environment={},
            started_at=0.0,
        )
        process_manager._processes[instance_id] = process_info

        with patch("asyncio.sleep", side_effect=Exception("Outer exception")):
            # Should not raise exception, just log and exit
            await process_manager._monitor_process(instance_id, mock_process)

    @pytest.mark.asyncio
    async def test_update_resource_usage_psutil_access_denied(
        self, process_manager, temp_dir
    ):
        """Test resource usage update with psutil.AccessDenied."""
        instance_id = "test-access-denied"
        pid = 12345

        process_info = ProcessInfo(
            pid=pid,
            status=ProcessStatus.RUNNING,
            command=["test"],
            working_directory=temp_dir,
            environment={},
            started_at=0.0,
        )
        process_manager._processes[instance_id] = process_info

        with patch("psutil.Process", side_effect=psutil.AccessDenied()):
            # Should not raise exception
            await process_manager._update_resource_usage(instance_id, pid)

            # Values should remain unchanged
            assert process_info.cpu_percent == 0.0
            assert process_info.memory_mb == 0.0

    @pytest.mark.asyncio
    async def test_update_resource_usage_general_exception(
        self, process_manager, temp_dir
    ):
        """Test resource usage update with general exception."""
        instance_id = "test-general-exception"
        pid = 12345

        process_info = ProcessInfo(
            pid=pid,
            status=ProcessStatus.RUNNING,
            command=["test"],
            working_directory=temp_dir,
            environment={},
            started_at=0.0,
        )
        process_manager._processes[instance_id] = process_info

        mock_process = MagicMock()
        mock_process.cpu_percent.side_effect = Exception("Unexpected error")

        with patch("psutil.Process", return_value=mock_process):
            # Should not raise exception, just log
            await process_manager._update_resource_usage(instance_id, pid)

    @pytest.mark.asyncio
    async def test_update_resource_usage_success(self, process_manager, temp_dir):
        """Test successful resource usage update."""
        instance_id = "test-success"
        pid = 12345

        process_info = ProcessInfo(
            pid=pid,
            status=ProcessStatus.RUNNING,
            command=["test"],
            working_directory=temp_dir,
            environment={},
            started_at=0.0,
        )
        process_manager._processes[instance_id] = process_info

        mock_process = MagicMock()
        mock_process.cpu_percent.return_value = 25.5
        mock_memory_info = MagicMock()
        mock_memory_info.rss = 134217728  # 128 MB in bytes
        mock_process.memory_info.return_value = mock_memory_info

        with patch("psutil.Process", return_value=mock_process):
            await process_manager._update_resource_usage(instance_id, pid)

            assert process_info.cpu_percent == 25.5
            assert process_info.memory_mb == 128.0

    @pytest.mark.asyncio
    async def test_cleanup_process_with_monitoring_task(
        self, process_manager, temp_dir
    ):
        """Test cleanup process with active monitoring task."""
        instance_id = "test-cleanup-task"

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

        # Create a real asyncio task that we can cancel
        async def dummy_task():
            await asyncio.sleep(10)  # Long running task

        task = asyncio.create_task(dummy_task())
        process_manager._monitoring_tasks[instance_id] = task

        await process_manager._cleanup_process(instance_id)

        # Verify task was cancelled
        assert task.cancelled()

        # Verify cleanup
        assert instance_id not in process_manager._monitoring_tasks
        assert instance_id not in process_manager._subprocess_map
        assert process_info.status == ProcessStatus.STOPPED

    @pytest.mark.asyncio
    async def test_cleanup_process_with_completed_task(self, process_manager, temp_dir):
        """Test cleanup process with completed monitoring task."""
        instance_id = "test-cleanup-completed"

        process_info = ProcessInfo(
            pid=12345,
            status=ProcessStatus.RUNNING,
            command=["test"],
            working_directory=temp_dir,
            environment={},
            started_at=0.0,
        )
        process_manager._processes[instance_id] = process_info

        # Create a mock task that's already done
        mock_task = AsyncMock()
        mock_task.done.return_value = True
        process_manager._monitoring_tasks[instance_id] = mock_task

        await process_manager._cleanup_process(instance_id)

        # Verify task was not cancelled since it's already done
        mock_task.cancel.assert_not_called()

        # Verify cleanup
        assert instance_id not in process_manager._monitoring_tasks

    @pytest.mark.asyncio
    async def test_cleanup_process_preserve_final_status(
        self, process_manager, temp_dir
    ):
        """Test cleanup process preserves final status for stopped/crashed processes."""
        instance_id = "test-preserve-status"

        # Test with STOPPED status
        process_info = ProcessInfo(
            pid=12345,
            status=ProcessStatus.STOPPED,
            command=["test"],
            working_directory=temp_dir,
            environment={},
            started_at=0.0,
        )
        process_manager._processes[instance_id] = process_info

        await process_manager._cleanup_process(instance_id)

        # Status should remain STOPPED
        assert process_info.status == ProcessStatus.STOPPED

        # Test with CRASHED status
        process_info.status = ProcessStatus.CRASHED
        await process_manager._cleanup_process(instance_id)

        # Status should remain CRASHED
        assert process_info.status == ProcessStatus.CRASHED

    def test_build_claude_command_with_resource_limits(self, process_manager, temp_dir):
        """Test building Claude command with resource limits (currently unused)."""
        resource_limits = {"cpu_percent": 50, "memory_mb": 512}

        # Without tmux
        command = process_manager._build_claude_command(
            working_directory=temp_dir,
            tmux_session=None,
            resource_limits=resource_limits,
        )
        assert command == ["claude", "--continue"]

        # With tmux
        command = process_manager._build_claude_command(
            working_directory=temp_dir,
            tmux_session="test-session",
            resource_limits=resource_limits,
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
    async def test_start_process_comprehensive(self, process_manager, temp_dir):
        """Test subprocess creation with comprehensive parameter coverage."""
        command = ["python", "-c", "print('test')"]
        environment = {"TEST_VAR": "test_value", "PYTHONPATH": "/test/path"}

        with patch("subprocess.Popen") as mock_popen:
            mock_process = MagicMock()
            mock_process.pid = 12345
            mock_popen.return_value = mock_process

            result = await process_manager._start_process(
                command=command,
                working_directory=temp_dir,
                environment=environment,
            )

            # Verify subprocess.Popen was called with correct parameters
            mock_popen.assert_called_once_with(
                command,
                cwd=temp_dir,
                env=environment,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE,
                start_new_session=True,
            )

            assert result == mock_process


class TestGlobalProcessManagerAdvanced:
    """Advanced tests for global process manager functionality."""

    def test_get_process_manager_initialization(self):
        """Test global process manager initialization."""
        # Clear global manager
        import cc_orchestrator.utils.process

        cc_orchestrator.utils.process._process_manager = None

        manager1 = get_process_manager()
        assert isinstance(manager1, ProcessManager)

        # Second call should return same instance
        manager2 = get_process_manager()
        assert manager1 is manager2

    @pytest.mark.asyncio
    async def test_cleanup_process_manager_with_none(self):
        """Test cleanup when global manager is None."""
        import cc_orchestrator.utils.process

        # Set global manager to None
        cc_orchestrator.utils.process._process_manager = None

        # Should not raise exception
        await cleanup_process_manager()

        # Global manager should still be None
        assert cc_orchestrator.utils.process._process_manager is None

    @pytest.mark.asyncio
    async def test_cleanup_process_manager_full_cycle(self):
        """Test full cleanup cycle of global process manager."""
        import cc_orchestrator.utils.process

        # Get initial manager
        manager = get_process_manager()
        assert manager is not None

        with patch.object(manager, "cleanup_all") as mock_cleanup:
            await cleanup_process_manager()
            mock_cleanup.assert_called_once()

        # Global manager should be reset to None
        assert cc_orchestrator.utils.process._process_manager is None

        # New manager should be different
        new_manager = get_process_manager()
        assert new_manager is not manager


class TestProcessErrorAdvanced:
    """Advanced tests for ProcessError exception handling."""

    def test_process_error_inheritance(self):
        """Test ProcessError inherits from Exception properly."""
        error = ProcessError("Test error")
        assert isinstance(error, Exception)
        assert issubclass(ProcessError, Exception)

    def test_process_error_string_representation(self):
        """Test ProcessError string representation with all attributes."""
        error = ProcessError(
            "Complex error scenario", instance_id="instance-123", pid=54321
        )

        assert str(error) == "Complex error scenario"
        assert error.instance_id == "instance-123"
        assert error.pid == 54321

    def test_process_error_exception_context(self):
        """Test ProcessError in exception context."""
        try:
            raise ProcessError("Test exception", instance_id="test-id", pid=999)
        except ProcessError as e:
            assert str(e) == "Test exception"
            assert e.instance_id == "test-id"
            assert e.pid == 999
        except Exception:
            pytest.fail("ProcessError should be caught as ProcessError")


class TestProcessInfoAdvanced:
    """Advanced tests for ProcessInfo dataclass functionality."""

    def test_process_info_dataclass_behavior(self):
        """Test ProcessInfo dataclass behavior and immutability aspects."""
        temp_dir = Path("/tmp/test")

        # Test with minimal required fields
        info1 = ProcessInfo(
            pid=123,
            status=ProcessStatus.RUNNING,
            command=["test"],
            working_directory=temp_dir,
            environment={},
            started_at=1000.0,
        )

        # Test with all fields
        info2 = ProcessInfo(
            pid=456,
            status=ProcessStatus.CRASHED,
            command=["test", "full"],
            working_directory=temp_dir,
            environment={"VAR": "value"},
            started_at=2000.0,
            cpu_percent=15.5,
            memory_mb=256.0,
            return_code=-1,
            error_message="Test error",
        )

        # Test equality
        assert info1 != info2

        # Test field modification
        info1.cpu_percent = 10.0
        assert info1.cpu_percent == 10.0

    def test_process_info_environment_handling(self):
        """Test ProcessInfo with various environment configurations."""
        temp_dir = Path("/tmp/test")

        # Empty environment
        info = ProcessInfo(
            pid=123,
            status=ProcessStatus.RUNNING,
            command=["test"],
            working_directory=temp_dir,
            environment={},
            started_at=1000.0,
        )
        assert info.environment == {}

        # Complex environment
        complex_env = {
            "PATH": "/usr/bin:/bin",
            "HOME": "/home/user",
            "CUSTOM_VAR": "custom_value",
            "DEBUG": "true",
        }
        info = ProcessInfo(
            pid=123,
            status=ProcessStatus.RUNNING,
            command=["test"],
            working_directory=temp_dir,
            environment=complex_env,
            started_at=1000.0,
        )
        assert info.environment == complex_env


class TestProcessStatusAdvanced:
    """Advanced tests for ProcessStatus enum."""

    def test_process_status_enum_completeness(self):
        """Test all ProcessStatus enum values are present and correct."""
        expected_statuses = {
            "STARTING": "starting",
            "RUNNING": "running",
            "STOPPING": "stopping",
            "STOPPED": "stopped",
            "ERROR": "error",
            "CRASHED": "crashed",
        }

        for name, value in expected_statuses.items():
            status = getattr(ProcessStatus, name)
            assert status.value == value

    def test_process_status_equality_and_comparison(self):
        """Test ProcessStatus equality and comparison operations."""
        assert ProcessStatus.STARTING == ProcessStatus.STARTING
        assert ProcessStatus.RUNNING != ProcessStatus.STOPPED

        # Test string comparison
        assert ProcessStatus.RUNNING.value == "running"
        assert ProcessStatus.CRASHED.value != "stopped"

    def test_process_status_in_collections(self):
        """Test ProcessStatus usage in collections."""
        active_statuses = {ProcessStatus.STARTING, ProcessStatus.RUNNING}
        inactive_statuses = {
            ProcessStatus.STOPPED,
            ProcessStatus.CRASHED,
            ProcessStatus.ERROR,
        }

        assert ProcessStatus.RUNNING in active_statuses
        assert ProcessStatus.STOPPED in inactive_statuses
        assert ProcessStatus.STOPPING not in active_statuses
        assert ProcessStatus.STOPPING not in inactive_statuses


class TestCoverageGapsSpecific:
    """Tests targeting specific coverage gaps."""

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
    async def test_get_process_info_returns_actual_info(
        self, process_manager, temp_dir
    ):
        """Test get_process_info returns actual process info (line 213)."""
        instance_id = "test-get-info"
        process_info = ProcessInfo(
            pid=12345,
            status=ProcessStatus.RUNNING,
            command=["test"],
            working_directory=temp_dir,
            environment={},
            started_at=0.0,
        )
        process_manager._processes[instance_id] = process_info

        # This covers line 213: return self._processes.get(instance_id)
        result = await process_manager.get_process_info(instance_id)
        assert result == process_info

    @pytest.mark.asyncio
    async def test_list_processes_returns_copy(self, process_manager, temp_dir):
        """Test list_processes returns copy of processes dict (line 221)."""
        instance_id = "test-list"
        process_info = ProcessInfo(
            pid=12345,
            status=ProcessStatus.RUNNING,
            command=["test"],
            working_directory=temp_dir,
            environment={},
            started_at=0.0,
        )
        process_manager._processes[instance_id] = process_info

        # This covers line 221: return self._processes.copy()
        result = await process_manager.list_processes()
        assert result == {instance_id: process_info}
        assert result is not process_manager._processes  # Verify it's a copy

    @pytest.mark.asyncio
    async def test_is_process_running_missing_instance(self, process_manager):
        """Test is_process_running with missing instance (line 234)."""
        # This covers line 234: return False
        result = await process_manager.is_process_running("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_wait_for_process_polling_loop(self, process_manager):
        """Test _wait_for_process polling loop (lines 443-444)."""
        mock_process = MagicMock()
        # First call returns None (running), second returns 0 (terminated)
        mock_process.poll.side_effect = [None, 0]

        with patch("asyncio.sleep", return_value=None) as mock_sleep:
            # This covers lines 443-444
            await process_manager._wait_for_process(mock_process)

            # Verify sleep was called
            mock_sleep.assert_called_with(0.1)
            assert mock_process.poll.call_count == 2

    @pytest.mark.asyncio
    async def test_monitor_process_resource_update_and_sleep(
        self, process_manager, temp_dir
    ):
        """Test monitor process resource usage update and sleep (lines 389-392)."""
        instance_id = "test-resource-monitor"

        mock_process = MagicMock()
        mock_process.pid = 12345
        # Process runs multiple times to get into the monitoring loop, then exits
        mock_process.poll.side_effect = [None, None, None, 0]

        process_info = ProcessInfo(
            pid=12345,
            status=ProcessStatus.STARTING,
            command=["test"],
            working_directory=temp_dir,
            environment={},
            started_at=0.0,
        )
        process_manager._processes[instance_id] = process_info

        # Track calls to sleep to control when to exit
        sleep_calls = []

        async def mock_sleep(duration):
            sleep_calls.append(duration)
            # Exit after the monitoring loop sleep
            if duration == 5.0:
                # Set shutdown to exit the loop
                process_manager._shutdown_event.set()

        with patch("asyncio.sleep", side_effect=mock_sleep):
            with patch.object(process_manager, "_update_resource_usage") as mock_update:
                await process_manager._monitor_process(instance_id, mock_process)

                # Verify resource usage was updated (line 389)
                mock_update.assert_called_with(instance_id, 12345)

                # Verify sleep was called with 5.0 (line 392)
                assert 5.0 in sleep_calls

    @pytest.mark.asyncio
    async def test_spawn_process_duplicate_instance_error(
        self, process_manager, temp_dir
    ):
        """Test spawning process with duplicate instance ID raises error (line 80)."""
        instance_id = "test-duplicate"

        # Add existing process
        existing_process = ProcessInfo(
            pid=12345,
            status=ProcessStatus.RUNNING,
            command=["test"],
            working_directory=temp_dir,
            environment={},
            started_at=0.0,
        )
        process_manager._processes[instance_id] = existing_process

        # Try to spawn another process with same ID
        with pytest.raises(ProcessError, match="already exists"):
            await process_manager.spawn_claude_process(
                instance_id=instance_id,
                working_directory=temp_dir,
            )

    @pytest.mark.asyncio
    async def test_terminate_nonexistent_process_warning(self, process_manager):
        """Test terminating nonexistent process logs warning (lines 155-158)."""
        instance_id = "nonexistent-process"

        # This should trigger the warning and return False
        # This covers lines 155-158
        result = await process_manager.terminate_process(instance_id)
        assert result is False


class TestIntegrationScenarios:
    """Integration-style tests covering complex scenarios."""

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
    async def test_full_process_lifecycle(self, process_manager, temp_dir):
        """Test complete process lifecycle from spawn to cleanup."""
        instance_id = "test-lifecycle"

        # Mock subprocess
        mock_process = MagicMock()
        mock_process.pid = 12345
        mock_process.poll.side_effect = [None, None, 0]  # Running, then exits

        with patch.object(process_manager, "_start_process", return_value=mock_process):
            with patch("asyncio.sleep", return_value=None):
                with patch.object(process_manager, "_monitor_process") as mock_monitor:
                    # Make monitor process do nothing
                    mock_monitor.return_value = None

                    # Spawn process
                    info = await process_manager.spawn_claude_process(
                        instance_id=instance_id,
                        working_directory=temp_dir,
                    )

                    assert info.status == ProcessStatus.STARTING
                    assert (
                        await process_manager.is_process_running(instance_id) is False
                    )

                    # Terminate process
                    with patch.object(process_manager, "_wait_for_process"):
                        with patch.object(process_manager, "_cleanup_process"):
                            result = await process_manager.terminate_process(
                                instance_id
                            )
                            assert result is True

    @pytest.mark.asyncio
    async def test_error_recovery_scenarios(self, process_manager, temp_dir):
        """Test error recovery in various scenarios."""
        instance_id = "test-error-recovery"

        # Test subprocess creation failure
        with patch.object(
            process_manager, "_start_process", side_effect=OSError("Failed")
        ):
            with pytest.raises(ProcessError):
                await process_manager.spawn_claude_process(
                    instance_id=instance_id,
                    working_directory=temp_dir,
                )

        # Verify no partial state left behind
        assert instance_id not in process_manager._processes
        assert instance_id not in process_manager._subprocess_map
        assert instance_id not in process_manager._monitoring_tasks

    @pytest.mark.asyncio
    async def test_concurrent_operations(self, process_manager, temp_dir):
        """Test concurrent operations on the process manager."""
        instance_ids = [f"test-concurrent-{i}" for i in range(3)]

        # Mock subprocess for each instance
        mock_processes = []
        for i, _instance_id in enumerate(instance_ids):
            mock_process = MagicMock()
            mock_process.pid = 12345 + i
            mock_process.poll.return_value = None
            mock_processes.append(mock_process)

        with patch.object(
            process_manager, "_start_process", side_effect=mock_processes
        ):
            with patch.object(process_manager, "_monitor_process"):
                with patch("asyncio.create_task"):
                    # Spawn multiple processes concurrently
                    spawn_tasks = [
                        process_manager.spawn_claude_process(
                            instance_id=instance_id,
                            working_directory=temp_dir,
                        )
                        for instance_id in instance_ids
                    ]

                    results = await asyncio.gather(*spawn_tasks)

                    # Verify all processes were created
                    assert len(results) == 3
                    assert all(
                        result.status == ProcessStatus.STARTING for result in results
                    )

                    # Verify all are tracked
                    for instance_id in instance_ids:
                        assert instance_id in process_manager._processes
                        assert instance_id in process_manager._subprocess_map
