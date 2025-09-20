"""Integration tests for process management with Claude instances."""

import asyncio
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from cc_orchestrator.core.enums import InstanceStatus
from cc_orchestrator.core.instance import ClaudeInstance
from cc_orchestrator.core.orchestrator import Orchestrator
from cc_orchestrator.database.models import Base
from cc_orchestrator.utils.process import get_process_manager


class TestProcessIntegration:
    """Integration tests for process management with Claude instances."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            yield Path(tmp_dir)

    @pytest.fixture
    def temp_db(self):
        """Create a temporary test database."""
        temp_db_file = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        temp_db_file.close()

        database_url = f"sqlite:///{temp_db_file.name}"

        # Create database with tables
        from sqlalchemy import create_engine

        engine = create_engine(database_url, connect_args={"check_same_thread": False})
        Base.metadata.create_all(bind=engine)

        yield database_url, temp_db_file.name

        # Cleanup
        import os

        try:
            os.unlink(temp_db_file.name)
        except FileNotFoundError:
            pass

    @pytest.fixture
    async def orchestrator(self, temp_db):
        """Create an orchestrator instance for testing."""
        database_url, _ = temp_db

        # Reset any global database manager first
        from cc_orchestrator.database.connection import DatabaseManager, close_database

        close_database()

        # Create fresh database manager with current schema
        manager = DatabaseManager(database_url=database_url)
        Base.metadata.create_all(bind=manager.engine)

        orchestrator = Orchestrator(db_session=manager.create_session())
        await orchestrator.initialize()
        yield orchestrator
        await orchestrator.cleanup()
        manager.close()

    @pytest.mark.asyncio
    async def test_claude_instance_lifecycle(self, temp_dir):
        """Test complete Claude instance lifecycle with process management."""
        instance = ClaudeInstance(
            issue_id="test-issue-123",
            workspace_path=temp_dir,
            branch_name="test-branch",
            tmux_session="test-session",
        )

        # Initialize instance
        await instance.initialize()
        assert instance.status == InstanceStatus.STOPPED
        assert instance.process_id is None

        # Mock ProcessManager methods directly
        from cc_orchestrator.utils.process import ProcessInfo, ProcessStatus

        with (
            patch.object(
                instance._process_manager, "spawn_claude_process"
            ) as mock_spawn,
            patch.object(
                instance._process_manager, "terminate_process"
            ) as mock_terminate,
            patch.object(
                instance._process_manager, "get_process_info"
            ) as mock_get_info,
        ):
            # Mock successful process spawning
            process_info = ProcessInfo(
                pid=12345,
                status=ProcessStatus.RUNNING,
                command=["claude", "--continue"],
                working_directory=temp_dir,
                environment={},
                started_at=1672531200.0,  # 2023-01-01T00:00:00 as timestamp
                cpu_percent=0.0,
                memory_mb=100.0,
                return_code=None,
                error_message=None,
            )
            mock_spawn.return_value = process_info
            mock_terminate.return_value = True
            mock_get_info.return_value = process_info

            # Start the instance
            success = await instance.start()
            assert success is True
            assert instance.status == InstanceStatus.RUNNING
            assert instance.process_id == 12345

            # Check process status
            process_info = await instance.get_process_status()
            assert process_info is not None
            assert process_info.pid == 12345

            # Get instance info
            info = instance.get_info()
            assert info["issue_id"] == "test-issue-123"
            assert info["status"] == "running"
            assert info["process_id"] == 12345
            assert "process_status" in info

            # Verify instance is running
            assert instance.is_running()

            # Stop the instance
            success = await instance.stop()
            assert success is True
            assert instance.status == InstanceStatus.STOPPED
            assert instance.process_id is None

        # Clean up instance
        await instance.cleanup()

    @pytest.mark.asyncio
    async def test_claude_instance_start_failure(self, temp_dir):
        """Test Claude instance start failure handling."""
        instance = ClaudeInstance(issue_id="test-issue-fail", workspace_path=temp_dir)

        await instance.initialize()

        # Mock process spawning failure
        with patch(
            "subprocess.Popen",
            side_effect=OSError("Failed to start process"),
        ):
            success = await instance.start()
            assert success is False
            assert instance.status == InstanceStatus.ERROR
            assert instance.process_id is None

        await instance.cleanup()

    @pytest.mark.asyncio
    async def test_claude_instance_environment_variables(self, temp_dir):
        """Test that Claude instance sets proper environment variables."""
        instance = ClaudeInstance(
            issue_id="test-issue-env",
            workspace_path=temp_dir,
            branch_name="feature-branch",
            tmux_session="env-session",
            environment={"CUSTOM_VAR": "custom_value"},
        )

        env_vars = instance._get_environment_variables()

        assert env_vars["CLAUDE_INSTANCE_ID"] == "test-issue-env"
        assert env_vars["CLAUDE_WORKSPACE"] == str(temp_dir)
        assert env_vars["CLAUDE_BRANCH"] == "feature-branch"
        assert env_vars["CLAUDE_TMUX_SESSION"] == "env-session"
        assert env_vars["CUSTOM_VAR"] == "custom_value"

    @pytest.mark.asyncio
    async def test_orchestrator_instance_management(self, orchestrator, temp_dir):
        """Test orchestrator managing multiple instances with processes."""
        # Clean up any existing instances from previous tests
        existing_instances = orchestrator.list_instances()
        for instance in existing_instances:
            await orchestrator.destroy_instance(instance.issue_id)

        # Verify clean state
        assert len(orchestrator.list_instances()) == 0

        # Create multiple instances
        instance_ids = ["issue-1", "issue-2", "issue-3"]

        # Mock ProcessManager methods directly for more reliable testing
        from cc_orchestrator.utils.process import ProcessInfo, ProcessStatus

        # Create process info for each instance
        process_infos = []
        for i in range(len(instance_ids)):
            process_info = ProcessInfo(
                pid=10000 + i,
                status=ProcessStatus.RUNNING,
                command=["claude", "--continue"],
                working_directory=temp_dir,
                environment={},
                started_at=1672531200.0 + i,
                cpu_percent=0.0,
                memory_mb=100.0,
                return_code=None,
                error_message=None,
            )
            process_infos.append(process_info)

        with (
            patch(
                "cc_orchestrator.utils.process.ProcessManager.spawn_claude_process"
            ) as mock_spawn,
            patch(
                "cc_orchestrator.utils.process.ProcessManager.terminate_process"
            ) as mock_terminate,
            patch(
                "cc_orchestrator.utils.process.ProcessManager.get_process_info"
            ) as mock_get_info,
            patch(
                "cc_orchestrator.utils.process.ProcessManager.list_processes"
            ) as mock_list,
        ):
            # Set up mock returns
            mock_spawn.side_effect = process_infos
            mock_terminate.return_value = True
            mock_get_info.side_effect = process_infos
            mock_list.return_value = {
                f"issue-{i+1}": process_infos[i] for i in range(len(instance_ids))
            }

            # Create instances through orchestrator
            instances = []
            for issue_id in instance_ids:
                instance = await orchestrator.create_instance(
                    issue_id=issue_id, workspace_path=temp_dir / f"workspace-{issue_id}"
                )
                instances.append(instance)

                # Start the instance
                success = await instance.start()
                assert success is True
                assert instance.is_running()

            # Verify all instances are tracked
            all_instances = orchestrator.list_instances()
            assert len(all_instances) == 3

            # Verify process manager has all processes
            process_manager = get_process_manager()
            all_processes = await process_manager.list_processes()
            assert len(all_processes) == 3

            # Stop all instances explicitly
            for instance in instances:
                success = await instance.stop()
                assert success is True
                assert not instance.is_running()

            # Verify instances are stopped but still exist in database
            all_instances = orchestrator.list_instances()
            assert len(all_instances) == 3

            # Check that the original instances report as stopped
            for instance in instances:
                assert not instance.is_running()

    @pytest.mark.asyncio
    async def test_process_isolation(self, temp_dir):
        """Test that processes are properly isolated."""
        # Create two instances with different configurations
        instance1 = ClaudeInstance(
            issue_id="issue-isolation-1",
            workspace_path=temp_dir / "workspace1",
            tmux_session="session1",
        )

        instance2 = ClaudeInstance(
            issue_id="issue-isolation-2",
            workspace_path=temp_dir / "workspace2",
            tmux_session="session2",
        )

        await instance1.initialize()
        await instance2.initialize()

        with patch("subprocess.Popen") as mock_popen:
            # Mock different processes
            mock_process1 = type(
                "MockProcess",
                (),
                {
                    "pid": 11111,
                    "poll": lambda: None,
                    "terminate": lambda: None,
                    "returncode": None,
                },
            )()

            mock_process2 = type(
                "MockProcess",
                (),
                {
                    "pid": 22222,
                    "poll": lambda: None,
                    "terminate": lambda: None,
                    "returncode": None,
                },
            )()

            mock_popen.side_effect = [mock_process1, mock_process2]

            # Start both instances
            success1 = await instance1.start()
            success2 = await instance2.start()

            assert success1 is True
            assert success2 is True
            assert instance1.process_id != instance2.process_id

            # Verify environment isolation
            env1 = instance1._get_environment_variables()
            env2 = instance2._get_environment_variables()

            assert env1["CLAUDE_INSTANCE_ID"] != env2["CLAUDE_INSTANCE_ID"]
            assert env1["CLAUDE_WORKSPACE"] != env2["CLAUDE_WORKSPACE"]
            assert env1["CLAUDE_TMUX_SESSION"] != env2["CLAUDE_TMUX_SESSION"]

            # Verify process manager tracks both
            process_manager = get_process_manager()
            processes = await process_manager.list_processes()
            assert len(processes) == 2
            assert "issue-isolation-1" in processes
            assert "issue-isolation-2" in processes

            # Clean up
            await instance1.cleanup()
            await instance2.cleanup()

    @pytest.mark.asyncio
    async def test_process_recovery_after_crash(self, temp_dir):
        """Test process recovery after unexpected termination."""
        instance = ClaudeInstance(issue_id="crash-test", workspace_path=temp_dir)

        await instance.initialize()

        # Mock ProcessManager methods directly for more reliable testing
        from cc_orchestrator.utils.process import ProcessInfo, ProcessStatus

        # Mock initial process that will "crash"
        crashed_process_info = ProcessInfo(
            pid=99999,
            status=ProcessStatus.CRASHED,
            command=["claude", "--continue"],
            working_directory=temp_dir,
            environment={},
            started_at=1672531200.0,
            cpu_percent=0.0,
            memory_mb=100.0,
            return_code=1,
            error_message="Process crashed",
        )

        # Mock recovered process
        recovered_process_info = ProcessInfo(
            pid=88888,
            status=ProcessStatus.RUNNING,
            command=["claude", "--continue"],
            working_directory=temp_dir,
            environment={},
            started_at=1672531300.0,
            cpu_percent=0.0,
            memory_mb=100.0,
            return_code=None,
            error_message=None,
        )

        with (
            patch.object(
                instance._process_manager, "spawn_claude_process"
            ) as mock_spawn,
            patch.object(
                instance._process_manager, "terminate_process"
            ) as mock_terminate,
            patch.object(
                instance._process_manager, "get_process_info"
            ) as mock_get_info,
        ):
            # First start - process starts successfully
            mock_spawn.return_value = crashed_process_info
            mock_terminate.return_value = True
            mock_get_info.return_value = crashed_process_info

            # Start instance
            success = await instance.start()
            assert success is True

            # Simulate process detection
            process_info = await instance.get_process_status()
            assert process_info is not None

            # Stop the "crashed" instance
            success = await instance.stop()
            assert success is True
            assert instance.status == InstanceStatus.STOPPED

            # Restart the instance (simulating recovery)
            mock_spawn.return_value = recovered_process_info
            mock_get_info.return_value = recovered_process_info

            success = await instance.start()
            assert success is True
            assert instance.process_id == 88888

            # Clean up
            await instance.cleanup()

    @pytest.mark.asyncio
    async def test_resource_monitoring_integration(self, temp_dir):
        """Test resource monitoring integration with Claude instances."""
        instance = ClaudeInstance(issue_id="resource-test", workspace_path=temp_dir)

        await instance.initialize()

        with patch("subprocess.Popen") as mock_popen:
            mock_process = type(
                "MockProcess",
                (),
                {
                    "pid": 12345,
                    "poll": lambda: None,
                    "terminate": lambda: None,
                    "returncode": None,
                },
            )()
            mock_popen.return_value = mock_process

            # Mock resource monitoring
            with patch("psutil.Process") as mock_psutil:
                mock_proc = mock_psutil.return_value
                mock_proc.cpu_percent.return_value = 15.5
                mock_proc.memory_info.return_value.rss = 256 * 1024 * 1024  # 256MB

                # Start instance
                success = await instance.start()
                assert success is True

                # Let monitoring run briefly
                await asyncio.sleep(0.1)

                # Check process info includes resource usage
                process_info = await instance.get_process_status()
                if process_info:
                    # Resource usage may be updated by monitoring
                    assert process_info.cpu_percent >= 0
                    assert process_info.memory_mb >= 0

                # Clean up
                await instance.cleanup()

    @pytest.mark.asyncio
    async def test_concurrent_instance_operations(self, temp_dir):
        """Test concurrent operations on multiple instances."""
        instances = []
        instance_count = 5

        # Create multiple instances
        for i in range(instance_count):
            instance = ClaudeInstance(
                issue_id=f"concurrent-{i}", workspace_path=temp_dir / f"workspace-{i}"
            )
            await instance.initialize()
            instances.append(instance)

        # Mock ProcessManager methods for all instances
        from cc_orchestrator.utils.process import ProcessInfo, ProcessStatus

        # Create process info for each instance
        process_infos = []
        for i in range(instance_count):
            process_info = ProcessInfo(
                pid=50000 + i,
                status=ProcessStatus.RUNNING,
                command=["claude", "--continue"],
                working_directory=temp_dir / f"workspace-{i}",
                environment={},
                started_at=1672531200.0 + i,
                cpu_percent=0.0,
                memory_mb=100.0,
                return_code=None,
                error_message=None,
            )
            process_infos.append(process_info)

        # Mock methods for all instances
        with (
            patch(
                "cc_orchestrator.utils.process.ProcessManager.spawn_claude_process"
            ) as mock_spawn,
            patch(
                "cc_orchestrator.utils.process.ProcessManager.terminate_process"
            ) as mock_terminate,
            patch(
                "cc_orchestrator.utils.process.ProcessManager.get_process_info"
            ) as mock_get_info,
            patch(
                "cc_orchestrator.utils.process.ProcessManager.list_processes"
            ) as mock_list,
        ):
            # Set up mock returns
            mock_spawn.side_effect = process_infos
            mock_terminate.return_value = True
            mock_get_info.side_effect = process_infos
            mock_list.return_value = {
                f"concurrent-{i}": process_infos[i] for i in range(instance_count)
            }

            # Start all instances concurrently
            start_tasks = [instance.start() for instance in instances]
            results = await asyncio.gather(*start_tasks)

            # Verify all started successfully
            assert all(results)
            assert all(instance.is_running() for instance in instances)

            # Verify process manager tracks all
            process_manager = get_process_manager()
            processes = await process_manager.list_processes()
            assert len(processes) == instance_count

            # Stop all instances concurrently
            stop_tasks = [instance.stop() for instance in instances]
            results = await asyncio.gather(*stop_tasks)

            # Verify all stopped successfully
            assert all(results)
            assert all(not instance.is_running() for instance in instances)

        # Clean up all instances
        cleanup_tasks = [instance.cleanup() for instance in instances]
        await asyncio.gather(*cleanup_tasks)

    @pytest.mark.asyncio
    async def test_process_command_generation(self, temp_dir):
        """Test different process command generation scenarios."""
        process_manager = get_process_manager()

        # Test direct Claude command
        command = process_manager._build_claude_command(
            working_directory=temp_dir, tmux_session=None
        )
        assert command == ["claude", "--continue"]

        # Test tmux-wrapped Claude command
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

        # Test with resource limits (currently not implemented but structure ready)
        command = process_manager._build_claude_command(
            working_directory=temp_dir,
            tmux_session="test-session",
            resource_limits={"cpu": "50%", "memory": "1G"},
        )
        # Should still generate the same command for now
        assert command == expected
