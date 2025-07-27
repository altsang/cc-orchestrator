"""
Unit tests for custom exception classes.

Tests cover:
- Base exception functionality
- All specialized exception types
- Exception context handling
- Exception message formatting
- Timestamp tracking
"""

from datetime import datetime
from unittest.mock import patch
import pytest

from cc_orchestrator.utils.logging import (
    CCOrchestratorException,
    InstanceError,
    WorktreeError,
    TaskError,
    ConfigurationError,
    IntegrationError,
    DatabaseError,
    TmuxError
)


class TestCCOrchestratorException:
    """Test the base exception class."""
    
    def test_basic_exception_creation(self):
        """Test creating a basic exception with just a message."""
        message = "Test error message"
        exc = CCOrchestratorException(message)
        
        assert str(exc) == message
        assert exc.message == message
        assert exc.context == {}
        assert isinstance(exc.timestamp, datetime)
    
    def test_exception_with_context(self):
        """Test creating an exception with context information."""
        message = "Error with context"
        context = {
            "instance_id": "test-instance",
            "operation": "test_operation",
            "details": {"key": "value"}
        }
        
        exc = CCOrchestratorException(message, context)
        
        assert exc.message == message
        assert exc.context == context
        assert exc.context["instance_id"] == "test-instance"
        assert exc.context["operation"] == "test_operation"
        assert exc.context["details"]["key"] == "value"
    
    def test_exception_without_context(self):
        """Test that exception works when context is None."""
        exc = CCOrchestratorException("Test message", None)
        
        assert exc.context == {}
    
    def test_exception_inheritance(self):
        """Test that CCOrchestratorException inherits from Exception."""
        exc = CCOrchestratorException("Test")
        
        assert isinstance(exc, Exception)
        assert isinstance(exc, CCOrchestratorException)
    
    @patch('cc_orchestrator.utils.logging.datetime')
    def test_exception_timestamp(self, mock_datetime):
        """Test that exception captures timestamp correctly."""
        test_time = datetime(2025, 7, 27, 10, 30, 0)
        mock_datetime.utcnow.return_value = test_time
        
        exc = CCOrchestratorException("Test message")
        
        assert exc.timestamp == test_time
        mock_datetime.utcnow.assert_called_once()


class TestInstanceError:
    """Test the InstanceError exception class."""
    
    def test_instance_error_creation(self):
        """Test creating an InstanceError."""
        message = "Instance failed to start"
        context = {"instance_id": "claude-001", "port": 8080}
        
        exc = InstanceError(message, context)
        
        assert isinstance(exc, CCOrchestratorException)
        assert isinstance(exc, InstanceError)
        assert exc.message == message
        assert exc.context == context
    
    def test_instance_error_inheritance(self):
        """Test InstanceError inheritance chain."""
        exc = InstanceError("Test error")
        
        assert isinstance(exc, Exception)
        assert isinstance(exc, CCOrchestratorException)
        assert isinstance(exc, InstanceError)
    
    def test_instance_error_typical_context(self):
        """Test InstanceError with typical context information."""
        context = {
            "instance_id": "claude-test-001",
            "tmux_session": "cc-orchestrator-claude-test-001",
            "worktree_path": "/tmp/worktree-001",
            "pid": 12345,
            "error_code": "STARTUP_FAILED"
        }
        
        exc = InstanceError("Instance startup failed", context)
        
        assert exc.context["instance_id"] == "claude-test-001"
        assert exc.context["tmux_session"] == "cc-orchestrator-claude-test-001"
        assert exc.context["pid"] == 12345


class TestWorktreeError:
    """Test the WorktreeError exception class."""
    
    def test_worktree_error_creation(self):
        """Test creating a WorktreeError."""
        message = "Worktree creation failed"
        context = {"path": "/tmp/worktree", "branch": "feature/test"}
        
        exc = WorktreeError(message, context)
        
        assert isinstance(exc, CCOrchestratorException)
        assert isinstance(exc, WorktreeError)
        assert exc.message == message
        assert exc.context == context
    
    def test_worktree_error_git_context(self):
        """Test WorktreeError with git-specific context."""
        context = {
            "worktree_path": "/tmp/cc-orchestrator/worktree-001",
            "branch": "feature/new-feature",
            "base_branch": "main",
            "repository": "/home/user/project",
            "git_error": "fatal: destination path already exists"
        }
        
        exc = WorktreeError("Git worktree operation failed", context)
        
        assert exc.context["worktree_path"] == "/tmp/cc-orchestrator/worktree-001"
        assert exc.context["branch"] == "feature/new-feature"
        assert exc.context["git_error"] == "fatal: destination path already exists"


class TestTaskError:
    """Test the TaskError exception class."""
    
    def test_task_error_creation(self):
        """Test creating a TaskError."""
        message = "Task validation failed"
        context = {"task_id": "TASK-123", "validation_errors": ["missing title"]}
        
        exc = TaskError(message, context)
        
        assert isinstance(exc, CCOrchestratorException)
        assert isinstance(exc, TaskError)
        assert exc.message == message
        assert exc.context == context
    
    def test_task_error_coordination_context(self):
        """Test TaskError with task coordination context."""
        context = {
            "task_id": "TASK-456",
            "title": "Implement feature X",
            "assigned_instance": "claude-002",
            "status": "in_progress",
            "dependencies": ["TASK-123", "TASK-789"],
            "source": "github",
            "external_id": "123"
        }
        
        exc = TaskError("Task coordination failed", context)
        
        assert exc.context["task_id"] == "TASK-456"
        assert exc.context["assigned_instance"] == "claude-002"
        assert exc.context["dependencies"] == ["TASK-123", "TASK-789"]


class TestConfigurationError:
    """Test the ConfigurationError exception class."""
    
    def test_configuration_error_creation(self):
        """Test creating a ConfigurationError."""
        message = "Invalid configuration file"
        context = {"file_path": "/config/settings.yaml", "line": 15}
        
        exc = ConfigurationError(message, context)
        
        assert isinstance(exc, CCOrchestratorException)
        assert isinstance(exc, ConfigurationError)
        assert exc.message == message
        assert exc.context == context
    
    def test_configuration_error_validation_context(self):
        """Test ConfigurationError with validation context."""
        context = {
            "config_file": "/home/user/.cc-orchestrator/config.yaml",
            "validation_errors": [
                "max_instances must be positive integer",
                "github_token is required when github integration is enabled"
            ],
            "config_section": "integrations.github",
            "provided_value": None,
            "expected_type": "string"
        }
        
        exc = ConfigurationError("Configuration validation failed", context)
        
        assert len(exc.context["validation_errors"]) == 2
        assert exc.context["config_section"] == "integrations.github"


class TestIntegrationError:
    """Test the IntegrationError exception class."""
    
    def test_integration_error_creation(self):
        """Test creating an IntegrationError."""
        message = "GitHub API request failed"
        context = {"service": "github", "endpoint": "/repos/owner/repo/issues"}
        
        exc = IntegrationError(message, context)
        
        assert isinstance(exc, CCOrchestratorException)
        assert isinstance(exc, IntegrationError)
        assert exc.message == message
        assert exc.context == context
    
    def test_integration_error_api_context(self):
        """Test IntegrationError with API-specific context."""
        context = {
            "service": "github",
            "endpoint": "/repos/user/project/issues",
            "method": "POST",
            "status_code": 422,
            "response_body": {"message": "Validation Failed"},
            "rate_limit_remaining": 45,
            "rate_limit_reset": "2025-07-27T11:00:00Z"
        }
        
        exc = IntegrationError("GitHub API validation failed", context)
        
        assert exc.context["service"] == "github"
        assert exc.context["status_code"] == 422
        assert exc.context["rate_limit_remaining"] == 45


class TestDatabaseError:
    """Test the DatabaseError exception class."""
    
    def test_database_error_creation(self):
        """Test creating a DatabaseError."""
        message = "Database connection failed"
        context = {"database": "sqlite", "operation": "connect"}
        
        exc = DatabaseError(message, context)
        
        assert isinstance(exc, CCOrchestratorException)
        assert isinstance(exc, DatabaseError)
        assert exc.message == message
        assert exc.context == context
    
    def test_database_error_query_context(self):
        """Test DatabaseError with query-specific context."""
        context = {
            "database": "sqlite",
            "table": "instances",
            "operation": "INSERT",
            "query": "INSERT INTO instances (id, status) VALUES (?, ?)",
            "parameters": ["claude-001", "running"],
            "sqlite_error": "UNIQUE constraint failed: instances.id"
        }
        
        exc = DatabaseError("Database constraint violation", context)
        
        assert exc.context["table"] == "instances"
        assert exc.context["operation"] == "INSERT"
        assert "UNIQUE constraint failed" in exc.context["sqlite_error"]


class TestTmuxError:
    """Test the TmuxError exception class."""
    
    def test_tmux_error_creation(self):
        """Test creating a TmuxError."""
        message = "Tmux session creation failed"
        context = {"session_name": "cc-orchestrator-claude-001"}
        
        exc = TmuxError(message, context)
        
        assert isinstance(exc, CCOrchestratorException)
        assert isinstance(exc, TmuxError)
        assert exc.message == message
        assert exc.context == context
    
    def test_tmux_error_session_context(self):
        """Test TmuxError with session-specific context."""
        context = {
            "session_name": "cc-orchestrator-claude-002",
            "command": "tmux new-session -d -s cc-orchestrator-claude-002",
            "exit_code": 1,
            "stderr": "duplicate session: cc-orchestrator-claude-002",
            "existing_sessions": ["cc-orchestrator-claude-001", "cc-orchestrator-claude-002"]
        }
        
        exc = TmuxError("Tmux session already exists", context)
        
        assert exc.context["session_name"] == "cc-orchestrator-claude-002"
        assert exc.context["exit_code"] == 1
        assert "duplicate session" in exc.context["stderr"]


class TestExceptionUsagePatterns:
    """Test common exception usage patterns."""
    
    def test_exception_chaining(self):
        """Test that exceptions can be chained properly."""
        try:
            try:
                raise ValueError("Original error")
            except ValueError as e:
                raise InstanceError("Instance failed", {"cause": str(e)}) from e
        except InstanceError as exc:
            assert exc.message == "Instance failed"
            assert exc.context["cause"] == "Original error"
            assert exc.__cause__ is not None
            assert isinstance(exc.__cause__, ValueError)
    
    def test_exception_context_accumulation(self):
        """Test accumulating context across exception handling layers."""
        base_context = {"instance_id": "claude-001"}
        
        try:
            try:
                raise DatabaseError("DB error", base_context)
            except DatabaseError as db_exc:
                enhanced_context = {**db_exc.context, "recovery_attempted": True}
                raise InstanceError("Instance failed due to DB error", enhanced_context) from db_exc
        except InstanceError as inst_exc:
            assert inst_exc.context["instance_id"] == "claude-001"
            assert inst_exc.context["recovery_attempted"] is True
            assert inst_exc.__cause__ is not None
            assert isinstance(inst_exc.__cause__, DatabaseError)
    
    def test_exception_serialization_safety(self):
        """Test that exception context can be safely serialized."""
        import json
        
        context = {
            "instance_id": "claude-001",
            "numeric_value": 42,
            "boolean_flag": True,
            "list_data": ["a", "b", "c"],
            "nested_dict": {"key": "value"}
        }
        
        exc = TaskError("Serialization test", context)
        
        # Should be able to serialize context to JSON
        serialized = json.dumps(exc.context)
        deserialized = json.loads(serialized)
        
        assert deserialized == context
    
    def test_all_exception_types_inherit_properly(self):
        """Test that all exception types have proper inheritance."""
        exception_classes = [
            InstanceError,
            WorktreeError,
            TaskError,
            ConfigurationError,
            IntegrationError,
            DatabaseError,
            TmuxError
        ]
        
        for exc_class in exception_classes:
            exc = exc_class("Test message")
            
            assert isinstance(exc, Exception)
            assert isinstance(exc, CCOrchestratorException)
            assert isinstance(exc, exc_class)
            assert hasattr(exc, 'message')
            assert hasattr(exc, 'context')
            assert hasattr(exc, 'timestamp')