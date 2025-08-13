"""
Pytest configuration and shared fixtures for CC-Orchestrator tests.
"""

import logging
import os

# Set up environment variables BEFORE any imports to avoid collection errors
os.environ.setdefault(
    "JWT_SECRET_KEY", "test-secret-key-for-pytest-only-never-use-in-production"
)
os.environ.setdefault("FRONTEND_URL", "http://localhost:3000")
os.environ.setdefault("ENABLE_DEMO_USERS", "true")
os.environ.setdefault("DEBUG", "true")
os.environ.setdefault("DEMO_ADMIN_PASSWORD", "admin123")

# Add src to path for imports
import sys
import tempfile
from collections.abc import Generator
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cc_orchestrator.core.instance import ClaudeInstance, InstanceStatus
from cc_orchestrator.core.orchestrator import Orchestrator


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Set up environment variables for testing."""
    # Set required environment variables for security fixes
    os.environ["JWT_SECRET_KEY"] = (
        "test-secret-key-for-pytest-only-never-use-in-production"
    )
    os.environ["ENABLE_DEMO_USERS"] = "true"
    os.environ["DEBUG"] = "true"
    os.environ["DEMO_ADMIN_PASSWORD"] = "admin123"

    yield

    # Cleanup after tests if needed
    # Note: Don't cleanup environment variables as other tests might depend on them


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
def mock_logger():
    """Provide a mock logger for testing."""
    return Mock(spec=logging.Logger)


@pytest.fixture
def sample_exception_context():
    """Provide sample exception context for testing."""
    return {
        "instance_id": "test-instance-001",
        "task_id": "TASK-123",
        "operation": "test_operation",
        "timestamp": "2025-01-15T10:30:00Z",
        "additional_info": "test context data",
    }


@pytest.fixture
def sample_log_record():
    """Provide sample log record data for testing."""
    return {
        "timestamp": "2025-01-15T10:30:00.123Z",
        "level": "INFO",
        "message": "Test log message",
        "component": "test_component",
        "instance_id": "test-instance-001",
        "task_id": "TASK-123",
        "context": {"operation": "test_operation"},
    }


@pytest.fixture
def sample_structured_log():
    """Provide sample structured log output for testing."""
    return {
        "timestamp": "2025-01-15T10:30:00.123456Z",
        "level": "INFO",
        "logger": "cc_orchestrator.test",
        "message": "Test structured log message",
        "instance_id": "test-instance-001",
        "task_id": "TASK-123",
        "component": "ORCHESTRATOR",
        "operation": "test_operation",
        "execution_time": 0.123,
        "metadata": {"test_key": "test_value", "count": 42},
    }


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
def sample_log_record_object():
    """Provide a sample log record for testing."""
    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname="/test/path.py",
        lineno=42,
        msg="Test message",
        args=(),
        exc_info=None,
        func="test_function",
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

    with patch("sys.stdout", log_capture):
        yield log_capture
