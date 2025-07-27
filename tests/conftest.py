"""Pytest configuration and shared fixtures."""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest

from cc_orchestrator.core.instance import ClaudeInstance, InstanceStatus
from cc_orchestrator.core.orchestrator import Orchestrator


@pytest.fixture
def temp_workspace():
    """Create a temporary workspace directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def mock_orchestrator():
    """Create a mock orchestrator for testing."""
    orchestrator = Mock(spec=Orchestrator)
    orchestrator.instances = {}
    orchestrator._initialized = False
    orchestrator.initialize = AsyncMock()
    orchestrator.get_instance = Mock(return_value=None)
    orchestrator.list_instances = Mock(return_value=[])
    orchestrator.create_instance = AsyncMock()
    orchestrator.destroy_instance = AsyncMock(return_value=True)
    orchestrator.cleanup = AsyncMock()
    return orchestrator


@pytest.fixture
def mock_claude_instance():
    """Create a mock Claude instance for testing."""
    instance = Mock(spec=ClaudeInstance)
    instance.issue_id = "test-123"
    instance.status = InstanceStatus.INITIALIZING
    instance.workspace_path = Path("/tmp/test-workspace")
    instance.branch_name = "feature/test-123"
    instance.tmux_session = "claude-test-123"
    instance.process_id = None
    instance.metadata = {}

    instance.initialize = AsyncMock()
    instance.start = AsyncMock(return_value=True)
    instance.stop = AsyncMock(return_value=True)
    instance.is_running = Mock(return_value=False)
    instance.get_info = Mock(
        return_value={
            "issue_id": "test-123",
            "status": "initializing",
            "workspace_path": "/tmp/test-workspace",
            "branch_name": "feature/test-123",
            "tmux_session": "claude-test-123",
            "created_at": "2025-01-01T00:00:00",
            "last_activity": "2025-01-01T00:00:00",
            "process_id": None,
            "metadata": {},
        }
    )
    instance.cleanup = AsyncMock()

    return instance


@pytest.fixture
def sample_issue_data():
    """Sample issue data for testing."""
    return {
        "issue_id": "123",
        "title": "Test Issue",
        "description": "A test issue for unit testing",
        "status": "open",
        "assignee": "test-user",
        "labels": ["feature", "priority-high"],
    }
