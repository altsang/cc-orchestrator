"""
Pytest configuration and shared fixtures for CC-Orchestrator tests.
"""

import logging
import tempfile
from pathlib import Path
from typing import Generator
from unittest.mock import AsyncMock, Mock

import pytest

# Add src to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cc_orchestrator.core.instance import ClaudeInstance, InstanceStatus
from cc_orchestrator.core.orchestrator import Orchestrator


@pytest.fixture
def temp_log_file() -> Generator[Path, None, None]:
    """Provide a temporary log file for testing."""
    with tempfile.NamedTemporaryFile(suffix=".log", delete=False) as f:
        log_file = Path(f.name)
    
    yield log_file
    
    # Cleanup
    if log_file.exists():
        log_file.unlink()


@pytest.fixture
def temp_log_dir() -> Generator[Path, None, None]:
    """Provide a temporary directory for log files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


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


@pytest.fixture
def mock_logger():
    """Provide a mock logger for testing."""
    return Mock(spec=logging.Logger)


@pytest.fixture
def sample_exception_context():
    """Provide sample exception context for testing."""
    return {
        "instance_id": "test-instance-001",
        "task_id": "TEST-123",
        "operation": "test_operation",
        "timestamp": "2025-07-27T10:30:00Z"
    }


@pytest.fixture
def sample_log_record():
    """Provide a sample log record for testing."""
    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname="/test/path.py",
        lineno=42,
        msg="Test message",
        args=(),
        exc_info=None,
        func="test_function"
    )
    record.context = "test_context"
    record.instance_id = "test-instance-001"
    record.task_id = "TEST-123"
    return record


@pytest.fixture(autouse=True)
def reset_logging():
    """Reset logging configuration before each test."""
    # Store original state
    root_logger = logging.getLogger()
    original_handlers = root_logger.handlers[:]
    original_level = root_logger.level
    
    # Clear all existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Reset to a clean state
    root_logger.setLevel(logging.NOTSET)
    
    yield
    
    # Cleanup after test - remove any handlers added during test
    for handler in root_logger.handlers[:]:
        handler.close()
        root_logger.removeHandler(handler)
    
    # Restore original state
    root_logger.setLevel(original_level)
    for handler in original_handlers:
        root_logger.addHandler(handler)


@pytest.fixture
def capture_logs():
    """Capture log output during tests."""
    import io
    from unittest.mock import patch
    
    log_capture = io.StringIO()
    
    with patch('sys.stdout', log_capture):
        yield log_capture
