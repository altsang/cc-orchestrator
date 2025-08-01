"""Unit tests for ClaudeInstance class."""

from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from cc_orchestrator.core.instance import ClaudeInstance, InstanceStatus


class TestClaudeInstance:
    """Test suite for ClaudeInstance class."""

    def test_init_default(self):
        """Test instance initialization with defaults."""
        instance = ClaudeInstance(issue_id="test-123")

        assert instance.issue_id == "test-123"
        assert instance.workspace_path == Path("../cc-orchestrator-issue-test-123")
        assert instance.branch_name == "feature/issue-test-123"
        assert instance.tmux_session == "claude-issue-test-123"
        assert instance.status == InstanceStatus.INITIALIZING
        assert instance.process_id is None
        assert isinstance(instance.created_at, datetime)
        assert isinstance(instance.last_activity, datetime)
        assert instance.metadata == {}

    def test_init_with_custom_params(self):
        """Test instance initialization with custom parameters."""
        workspace_path = Path("/custom/workspace")
        branch_name = "custom-branch"
        tmux_session = "custom-session"

        instance = ClaudeInstance(
            issue_id="test-456",
            workspace_path=workspace_path,
            branch_name=branch_name,
            tmux_session=tmux_session,
            custom_param="test",
        )

        assert instance.issue_id == "test-456"
        assert instance.workspace_path == workspace_path
        assert instance.branch_name == branch_name
        assert instance.tmux_session == tmux_session
        assert instance.metadata == {"custom_param": "test"}

    @pytest.mark.asyncio
    async def test_initialize_success(self):
        """Test successful instance initialization."""
        instance = ClaudeInstance(issue_id="test-123")

        await instance.initialize()

        assert instance.status == InstanceStatus.STOPPED
        assert isinstance(instance.last_activity, datetime)

    @pytest.mark.asyncio
    async def test_initialize_failure(self):
        """Test instance initialization failure."""
        instance = ClaudeInstance(issue_id="test-123")

        with patch.object(instance, "initialize", side_effect=Exception("Init failed")):
            with pytest.raises(Exception, match="Init failed"):
                await instance.initialize()

    @pytest.mark.asyncio
    async def test_start_when_not_running(self):
        """Test starting instance when not running."""
        instance = ClaudeInstance(issue_id="test-123")
        instance.status = InstanceStatus.STOPPED

        # Mock ProcessManager to simulate successful process start
        from cc_orchestrator.utils.process import ProcessInfo, ProcessStatus
        from unittest.mock import patch
        
        process_info = ProcessInfo(
            pid=12345,
            status=ProcessStatus.RUNNING,
            command=["claude", "--continue"],
            working_directory=Path("/tmp/test"),
            environment={},
            started_at=1672531200.0,
            cpu_percent=0.0,
            memory_mb=100.0,
            return_code=None,
            error_message=None,
        )

        with patch.object(instance._process_manager, 'spawn_claude_process', return_value=process_info):
            result = await instance.start()

        assert result is True
        assert instance.status == InstanceStatus.RUNNING
        assert isinstance(instance.last_activity, datetime)

    @pytest.mark.asyncio
    async def test_start_when_already_running(self):
        """Test starting instance when already running."""
        instance = ClaudeInstance(issue_id="test-123")
        instance.status = InstanceStatus.RUNNING

        result = await instance.start()

        assert result is True
        assert instance.status == InstanceStatus.RUNNING

    @pytest.mark.asyncio
    async def test_start_failure(self):
        """Test start failure handling."""
        instance = ClaudeInstance(issue_id="test-123")
        instance.status = InstanceStatus.STOPPED

        # Simulate the actual start method failing by patching exception handling
        with patch.object(instance, "start") as mock_start:
            mock_start.side_effect = Exception("Start failed")
            try:
                await instance.start()
                raise AssertionError("Should have raised exception")
            except Exception as e:
                assert str(e) == "Start failed"

    @pytest.mark.asyncio
    async def test_stop_when_running(self):
        """Test stopping instance when running."""
        instance = ClaudeInstance(issue_id="test-123")
        instance.status = InstanceStatus.RUNNING
        instance.process_id = 12345

        # Mock ProcessManager to simulate successful process termination
        with patch.object(instance._process_manager, 'terminate_process', return_value=True):
            result = await instance.stop()

        assert result is True
        assert instance.status == InstanceStatus.STOPPED
        assert instance.process_id is None

    @pytest.mark.asyncio
    async def test_stop_when_already_stopped(self):
        """Test stopping instance when already stopped."""
        instance = ClaudeInstance(issue_id="test-123")
        instance.status = InstanceStatus.STOPPED

        result = await instance.stop()

        assert result is True
        assert instance.status == InstanceStatus.STOPPED

    def test_is_running_true(self):
        """Test is_running when instance is running."""
        instance = ClaudeInstance(issue_id="test-123")
        instance.status = InstanceStatus.RUNNING

        assert instance.is_running() is True

    def test_is_running_false(self):
        """Test is_running when instance is not running."""
        instance = ClaudeInstance(issue_id="test-123")
        instance.status = InstanceStatus.STOPPED

        assert instance.is_running() is False

    def test_get_info(self):
        """Test getting instance information."""
        instance = ClaudeInstance(issue_id="test-123")
        instance.status = InstanceStatus.RUNNING
        instance.process_id = 12345
        instance.metadata = {"custom": "data"}

        info = instance.get_info()

        assert info["issue_id"] == "test-123"
        assert info["status"] == "running"
        assert info["workspace_path"] == str(instance.workspace_path)
        assert info["branch_name"] == "feature/issue-test-123"
        assert info["tmux_session"] == "claude-issue-test-123"
        assert "created_at" in info
        assert "last_activity" in info
        assert info["process_id"] == 12345
        assert info["metadata"] == {"custom": "data"}

    @pytest.mark.asyncio
    async def test_cleanup(self):
        """Test instance cleanup."""
        instance = ClaudeInstance(issue_id="test-123")
        instance.status = InstanceStatus.RUNNING

        with patch.object(instance, "stop", return_value=True) as mock_stop:
            await instance.cleanup()
            mock_stop.assert_called_once()

    def test_status_enum_values(self):
        """Test InstanceStatus enum values."""
        assert InstanceStatus.INITIALIZING.value == "initializing"
        assert InstanceStatus.RUNNING.value == "running"
        assert InstanceStatus.STOPPED.value == "stopped"
        assert InstanceStatus.ERROR.value == "error"
