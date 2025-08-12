"""Comprehensive tests for src/cc_orchestrator/utils/logging.py module.

This test suite provides comprehensive coverage for all logging utilities including:
- Log level and context enumerations
- All exception classes
- StructuredFormatter JSON formatting
- ContextualLogger functionality
- Logger setup and configuration
- Error handling decorators
- Performance logging decorators
- Audit logging decorators
- Module-level logger instances

Target: 100% coverage (197/197 statements)
"""

import json
import logging
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from cc_orchestrator.utils.logging import (
    CCOrchestratorException,
    ConfigurationError,
    ContextualLogger,
    DatabaseError,
    InstanceError,
    IntegrationError,
    LogContext,
    LogLevel,
    StructuredFormatter,
    TaskError,
    TmuxError,
    WorktreeError,
    audit_log,
    get_logger,
    handle_errors,
    log_performance,
    orchestrator_logger,
    setup_logging,
)


class TestLogLevel:
    """Test LogLevel enumeration."""

    def test_log_levels_values(self):
        """Test that all log levels have correct string values."""
        assert LogLevel.DEBUG == "DEBUG"
        assert LogLevel.INFO == "INFO"
        assert LogLevel.WARNING == "WARNING"
        assert LogLevel.ERROR == "ERROR"
        assert LogLevel.CRITICAL == "CRITICAL"

    def test_log_levels_are_strings(self):
        """Test that LogLevel enum values are strings."""
        for level in LogLevel:
            assert isinstance(level.value, str)

    def test_log_levels_comparison(self):
        """Test LogLevel enum comparison and iteration."""
        levels = list(LogLevel)
        assert len(levels) == 5
        assert LogLevel.DEBUG in levels
        assert LogLevel.INFO in levels
        assert LogLevel.WARNING in levels
        assert LogLevel.ERROR in levels
        assert LogLevel.CRITICAL in levels


class TestLogContext:
    """Test LogContext enumeration."""

    def test_log_contexts_values(self):
        """Test that all log contexts have correct string values."""
        assert LogContext.ORCHESTRATOR == "orchestrator"
        assert LogContext.INSTANCE == "instance"
        assert LogContext.TASK == "task"
        assert LogContext.WORKTREE == "worktree"
        assert LogContext.WEB == "web"
        assert LogContext.CLI == "cli"
        assert LogContext.TMUX == "tmux"
        assert LogContext.INTEGRATION == "integration"
        assert LogContext.DATABASE == "database"
        assert LogContext.PROCESS == "process"

    def test_log_contexts_are_strings(self):
        """Test that LogContext enum values are strings."""
        for context in LogContext:
            assert isinstance(context.value, str)

    def test_log_contexts_count(self):
        """Test all expected log contexts are present."""
        contexts = list(LogContext)
        assert len(contexts) == 10


class TestCCOrchestratorException:
    """Test base exception class."""

    def test_basic_exception_creation(self):
        """Test creating exception with just a message."""
        exc = CCOrchestratorException("Test error")
        assert exc.message == "Test error"
        assert exc.context == {}
        assert isinstance(exc.timestamp, datetime)
        assert str(exc) == "Test error"

    def test_exception_with_context(self):
        """Test creating exception with context."""
        context = {"key": "value", "number": 42}
        exc = CCOrchestratorException("Test error", context)
        assert exc.message == "Test error"
        assert exc.context == context
        assert isinstance(exc.timestamp, datetime)

    def test_exception_with_none_context(self):
        """Test creating exception with None context."""
        exc = CCOrchestratorException("Test error", None)
        assert exc.context == {}

    def test_exception_timestamp_precision(self):
        """Test exception timestamp is set at creation time."""
        before = datetime.utcnow()
        exc = CCOrchestratorException("Test error")
        after = datetime.utcnow()

        assert before <= exc.timestamp <= after

    def test_exception_inheritance(self):
        """Test exception inherits from Exception."""
        exc = CCOrchestratorException("Test error")
        assert isinstance(exc, Exception)


class TestSpecificExceptions:
    """Test all specific exception classes."""

    def test_instance_error(self):
        """Test InstanceError creation and inheritance."""
        exc = InstanceError("Instance failed", {"instance_id": "test-123"})
        assert isinstance(exc, CCOrchestratorException)
        assert exc.message == "Instance failed"
        assert exc.context == {"instance_id": "test-123"}

    def test_worktree_error(self):
        """Test WorktreeError creation and inheritance."""
        exc = WorktreeError("Worktree failed")
        assert isinstance(exc, CCOrchestratorException)
        assert exc.message == "Worktree failed"
        assert exc.context == {}

    def test_task_error(self):
        """Test TaskError creation and inheritance."""
        exc = TaskError("Task failed", {"task_id": "task-456"})
        assert isinstance(exc, CCOrchestratorException)
        assert exc.message == "Task failed"
        assert exc.context == {"task_id": "task-456"}

    def test_configuration_error(self):
        """Test ConfigurationError creation and inheritance."""
        exc = ConfigurationError("Config invalid")
        assert isinstance(exc, CCOrchestratorException)
        assert exc.message == "Config invalid"

    def test_integration_error(self):
        """Test IntegrationError creation and inheritance."""
        exc = IntegrationError("GitHub API failed")
        assert isinstance(exc, CCOrchestratorException)
        assert exc.message == "GitHub API failed"

    def test_database_error(self):
        """Test DatabaseError creation and inheritance."""
        exc = DatabaseError("Database connection lost")
        assert isinstance(exc, CCOrchestratorException)
        assert exc.message == "Database connection lost"

    def test_tmux_error(self):
        """Test TmuxError creation and inheritance."""
        exc = TmuxError("Tmux session failed")
        assert isinstance(exc, CCOrchestratorException)
        assert exc.message == "Tmux session failed"


class TestStructuredFormatter:
    """Test StructuredFormatter for JSON logging."""

    def setUp(self):
        """Set up test fixtures."""
        self.formatter = StructuredFormatter()

    def test_basic_log_formatting(self):
        """Test basic log record formatting."""
        formatter = StructuredFormatter()
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="/test/path.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
            func="test_function"
        )
        record.module = "path"

        result = formatter.format(record)
        data = json.loads(result)

        assert data["level"] == "INFO"
        assert data["logger"] == "test.logger"
        assert data["message"] == "Test message"
        assert data["module"] == "path"
        assert data["function"] == "test_function"
        assert data["line"] == 42
        assert "timestamp" in data

    def test_formatting_with_context(self):
        """Test log formatting with context field."""
        formatter = StructuredFormatter()
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="/test/path.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
            func="test_function"
        )
        record.module = "path"
        record.context = "test_context"

        result = formatter.format(record)
        data = json.loads(result)

        assert data["context"] == "test_context"

    def test_formatting_with_instance_id(self):
        """Test log formatting with instance_id field."""
        formatter = StructuredFormatter()
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="/test/path.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
            func="test_function"
        )
        record.module = "path"
        record.instance_id = "instance-123"

        result = formatter.format(record)
        data = json.loads(result)

        assert data["instance_id"] == "instance-123"

    def test_formatting_with_task_id(self):
        """Test log formatting with task_id field."""
        formatter = StructuredFormatter()
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="/test/path.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
            func="test_function"
        )
        record.module = "path"
        record.task_id = "task-456"

        result = formatter.format(record)
        data = json.loads(result)

        assert data["task_id"] == "task-456"

    def test_formatting_with_custom_fields(self):
        """Test log formatting with additional custom fields."""
        formatter = StructuredFormatter()
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="/test/path.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
            func="test_function"
        )
        record.module = "path"
        record.custom_field = "custom_value"
        record.another_field = 123

        result = formatter.format(record)
        data = json.loads(result)

        assert data["custom_field"] == "custom_value"
        assert data["another_field"] == 123

    def test_formatting_with_exception_info(self):
        """Test log formatting with exception information."""
        formatter = StructuredFormatter()

        try:
            raise ValueError("Test exception")
        except ValueError:
            exc_info = sys.exc_info()

        record = logging.LogRecord(
            name="test.logger",
            level=logging.ERROR,
            pathname="/test/path.py",
            lineno=42,
            msg="Test error message",
            args=(),
            exc_info=exc_info,
            func="test_function"
        )
        record.module = "path"

        result = formatter.format(record)
        data = json.loads(result)

        assert "exception" in data
        assert data["exception"]["type"] == "ValueError"
        assert data["exception"]["message"] == "Test exception"
        assert "traceback" in data["exception"]
        assert isinstance(data["exception"]["traceback"], list)

    def test_formatting_with_none_exception_type(self):
        """Test log formatting with None exception type."""
        formatter = StructuredFormatter()
        record = logging.LogRecord(
            name="test.logger",
            level=logging.ERROR,
            pathname="/test/path.py",
            lineno=42,
            msg="Test error message",
            args=(),
            exc_info=(None, ValueError("test"), None),
            func="test_function"
        )
        record.module = "path"

        result = formatter.format(record)
        data = json.loads(result)

        assert data["exception"]["type"] == "UnknownError"

    def test_excludes_standard_fields(self):
        """Test that standard LogRecord fields are excluded from extra data."""
        formatter = StructuredFormatter()
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="/test/path.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
            func="test_function"
        )
        record.module = "path"

        result = formatter.format(record)
        data = json.loads(result)

        # Standard fields should not be in the extra data
        assert "name" not in data
        assert "args" not in data
        assert "pathname" not in data
        assert "filename" not in data

    def test_excludes_private_fields(self):
        """Test that private fields (starting with _) are excluded."""
        formatter = StructuredFormatter()
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="/test/path.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
            func="test_function"
        )
        record.module = "path"
        record._private_field = "should_not_appear"
        record.public_field = "should_appear"

        result = formatter.format(record)
        data = json.loads(result)

        assert "_private_field" not in data
        assert data["public_field"] == "should_appear"


class TestContextualLogger:
    """Test ContextualLogger class."""

    def test_contextual_logger_creation(self):
        """Test creating ContextualLogger."""
        logger = ContextualLogger("test.logger", LogContext.WEB)
        assert logger.context == "web"
        assert logger.instance_id is None
        assert logger.task_id is None
        assert logger.logger.name == "test.logger"

    def test_set_instance_id(self):
        """Test setting instance ID."""
        logger = ContextualLogger("test.logger", LogContext.INSTANCE)
        logger.set_instance_id("instance-123")
        assert logger.instance_id == "instance-123"

    def test_set_task_id(self):
        """Test setting task ID."""
        logger = ContextualLogger("test.logger", LogContext.TASK)
        logger.set_task_id("task-456")
        assert logger.task_id == "task-456"

    def test_debug_logging(self):
        """Test debug logging with context."""
        with patch('logging.getLogger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger

            logger = ContextualLogger("test.logger", LogContext.CLI)
            logger.set_instance_id("instance-123")
            logger.set_task_id("task-456")
            logger.debug("Test debug message", extra_field="extra_value")

            mock_logger.log.assert_called_once_with(
                logging.DEBUG,
                "Test debug message",
                extra={
                    "context": "cli",
                    "instance_id": "instance-123",
                    "task_id": "task-456",
                    "extra_field": "extra_value"
                }
            )

    def test_info_logging(self):
        """Test info logging with context."""
        with patch('logging.getLogger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger

            logger = ContextualLogger("test.logger", LogContext.DATABASE)
            logger.info("Test info message")

            mock_logger.log.assert_called_once_with(
                logging.INFO,
                "Test info message",
                extra={"context": "database"}
            )

    def test_warning_logging(self):
        """Test warning logging with context."""
        with patch('logging.getLogger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger

            logger = ContextualLogger("test.logger", LogContext.TMUX)
            logger.warning("Test warning message")

            mock_logger.log.assert_called_once_with(
                logging.WARNING,
                "Test warning message",
                extra={"context": "tmux"}
            )

    def test_error_logging_without_exception(self):
        """Test error logging without exception."""
        with patch('logging.getLogger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger

            logger = ContextualLogger("test.logger", LogContext.PROCESS)
            logger.error("Test error message")

            mock_logger.log.assert_called_once_with(
                logging.ERROR,
                "Test error message",
                extra={"context": "process"}
            )

    def test_error_logging_with_exception(self):
        """Test error logging with exception."""
        with patch('logging.getLogger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger

            logger = ContextualLogger("test.logger", LogContext.INTEGRATION)
            logger.set_instance_id("instance-789")
            exception = ValueError("Test exception")
            logger.error("Test error message", exception=exception)

            mock_logger.error.assert_called_once_with(
                "Test error message",
                exc_info=exception,
                extra={
                    "context": "integration",
                    "instance_id": "instance-789",
                    "task_id": None
                }
            )

    def test_critical_logging_without_exception(self):
        """Test critical logging without exception."""
        with patch('logging.getLogger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger

            logger = ContextualLogger("test.logger", LogContext.WORKTREE)
            logger.critical("Test critical message")

            mock_logger.log.assert_called_once_with(
                logging.CRITICAL,
                "Test critical message",
                extra={"context": "worktree"}
            )

    def test_critical_logging_with_exception(self):
        """Test critical logging with exception."""
        with patch('logging.getLogger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger

            logger = ContextualLogger("test.logger", LogContext.ORCHESTRATOR)
            exception = RuntimeError("Critical error")
            logger.critical("Test critical message", exception=exception)

            mock_logger.critical.assert_called_once_with(
                "Test critical message",
                exc_info=exception,
                extra={
                    "context": "orchestrator",
                    "instance_id": None,
                    "task_id": None
                }
            )

    def test_logging_with_all_context_ids(self):
        """Test logging with both instance and task IDs set."""
        with patch('logging.getLogger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger

            logger = ContextualLogger("test.logger", LogContext.WEB)
            logger.set_instance_id("instance-abc")
            logger.set_task_id("task-def")
            logger.info("Test message", custom="data")

            mock_logger.log.assert_called_once_with(
                logging.INFO,
                "Test message",
                extra={
                    "context": "web",
                    "instance_id": "instance-abc",
                    "task_id": "task-def",
                    "custom": "data"
                }
            )


class TestGetLogger:
    """Test get_logger function."""

    def test_get_logger_returns_contextual_logger(self):
        """Test get_logger returns ContextualLogger instance."""
        logger = get_logger("test.module", LogContext.CLI)
        assert isinstance(logger, ContextualLogger)
        assert logger.context == "cli"

    def test_get_logger_with_different_contexts(self):
        """Test get_logger with different context types."""
        logger1 = get_logger("test.module1", LogContext.DATABASE)
        logger2 = get_logger("test.module2", LogContext.WEB)

        assert logger1.context == "database"
        assert logger2.context == "web"


class TestSetupLogging:
    """Test setup_logging function."""

    def test_setup_logging_defaults(self):
        """Test setup_logging with default parameters."""
        with patch('logging.getLogger') as mock_get_logger, \
             patch('logging.StreamHandler') as mock_stream_handler:

            mock_root_logger = Mock()
            mock_get_logger.return_value = mock_root_logger
            mock_handler = Mock()
            mock_stream_handler.return_value = mock_handler

            setup_logging()

            mock_root_logger.setLevel.assert_called_with(logging.INFO)
            mock_root_logger.addHandler.assert_called()

    def test_setup_logging_with_log_level_enum(self):
        """Test setup_logging with LogLevel enum."""
        with patch('logging.getLogger') as mock_get_logger:
            mock_root_logger = Mock()
            mock_get_logger.return_value = mock_root_logger

            setup_logging(log_level=LogLevel.DEBUG)

            mock_root_logger.setLevel.assert_called_with(logging.DEBUG)

    def test_setup_logging_with_log_level_string(self):
        """Test setup_logging with string log level."""
        with patch('logging.getLogger') as mock_get_logger:
            mock_root_logger = Mock()
            mock_get_logger.return_value = mock_root_logger

            setup_logging(log_level="ERROR")

            mock_root_logger.setLevel.assert_called_with(logging.ERROR)

    def test_setup_logging_with_file_logging(self):
        """Test setup_logging with file logging enabled."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "test.log"

            with patch('logging.getLogger') as mock_get_logger, \
                 patch('logging.FileHandler') as mock_file_handler:

                mock_root_logger = Mock()
                mock_get_logger.return_value = mock_root_logger
                mock_handler = Mock()
                mock_file_handler.return_value = mock_handler

                setup_logging(log_file=log_file)

                assert log_file.parent.exists()
                mock_file_handler.assert_called_with(log_file)

    def test_setup_logging_creates_log_directory(self):
        """Test setup_logging creates log directory if it doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "subdir" / "test.log"

            with patch('logging.getLogger'), \
                 patch('logging.FileHandler'):

                setup_logging(log_file=log_file)

                assert log_file.parent.exists()

    def test_setup_logging_structured_vs_plain(self):
        """Test setup_logging with structured vs plain formatting."""
        with patch('logging.getLogger') as mock_get_logger, \
             patch('logging.StreamHandler') as mock_stream_handler:

            mock_root_logger = Mock()
            mock_get_logger.return_value = mock_root_logger
            mock_handler = Mock()
            mock_stream_handler.return_value = mock_handler

            # Test structured formatting
            setup_logging(enable_structured=True)
            mock_handler.setFormatter.assert_called()
            formatter_call = mock_handler.setFormatter.call_args[0][0]
            assert isinstance(formatter_call, StructuredFormatter)

            # Reset and test plain formatting
            mock_handler.reset_mock()
            setup_logging(enable_structured=False)
            mock_handler.setFormatter.assert_called()
            formatter_call = mock_handler.setFormatter.call_args[0][0]
            assert isinstance(formatter_call, logging.Formatter)
            assert not isinstance(formatter_call, StructuredFormatter)

    def test_setup_logging_console_disabled(self):
        """Test setup_logging with console output disabled."""
        with patch('logging.getLogger') as mock_get_logger, \
             patch('logging.StreamHandler') as mock_stream_handler:

            mock_root_logger = Mock()
            mock_get_logger.return_value = mock_root_logger

            setup_logging(enable_console=False)

            mock_stream_handler.assert_not_called()

    def test_setup_logging_clears_existing_handlers(self):
        """Test setup_logging clears existing handlers."""
        with patch('logging.getLogger') as mock_get_logger:
            mock_root_logger = Mock()
            existing_handler = Mock()
            mock_root_logger.handlers = [existing_handler]
            mock_get_logger.return_value = mock_root_logger

            setup_logging()

            mock_root_logger.removeHandler.assert_called_with(existing_handler)

    def test_setup_logging_suppresses_third_party_loggers(self):
        """Test setup_logging suppresses noisy third-party loggers."""
        with patch('logging.getLogger') as mock_get_logger:
            mock_root_logger = Mock()
            mock_urllib3_logger = Mock()
            mock_requests_logger = Mock()
            mock_git_logger = Mock()

            def get_logger_side_effect(name):
                if name == "urllib3":
                    return mock_urllib3_logger
                elif name == "requests":
                    return mock_requests_logger
                elif name == "git":
                    return mock_git_logger
                return mock_root_logger

            mock_get_logger.side_effect = get_logger_side_effect

            setup_logging()

            mock_urllib3_logger.setLevel.assert_called_with(logging.WARNING)
            mock_requests_logger.setLevel.assert_called_with(logging.WARNING)
            mock_git_logger.setLevel.assert_called_with(logging.WARNING)


class TestHandleErrorsDecorator:
    """Test handle_errors decorator."""

    def test_handle_errors_successful_execution(self):
        """Test handle_errors decorator with successful function execution."""
        @handle_errors()
        def test_function(x, y):
            return x + y

        with patch('cc_orchestrator.utils.logging.get_logger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger

            result = test_function(2, 3)

            assert result == 5
            assert mock_logger.debug.call_count == 2  # Starting and Completed

    def test_handle_errors_with_cc_orchestrator_exception(self):
        """Test handle_errors decorator with CCOrchestratorException."""
        @handle_errors()
        def test_function():
            raise InstanceError("Test instance error", {"id": "123"})

        with patch('cc_orchestrator.utils.logging.get_logger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger

            with pytest.raises(InstanceError):
                test_function()

            mock_logger.error.assert_called()
            error_call = mock_logger.error.call_args
            assert "CC-Orchestrator error in test_function" in error_call[0][0]

    def test_handle_errors_with_generic_exception(self):
        """Test handle_errors decorator with generic exception."""
        @handle_errors()
        def test_function():
            raise ValueError("Generic error")

        with patch('cc_orchestrator.utils.logging.get_logger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger

            with pytest.raises(CCOrchestratorException):
                test_function()

            mock_logger.error.assert_called()

    def test_handle_errors_with_recovery_strategy_success(self):
        """Test handle_errors decorator with successful recovery."""
        def recovery_strategy(exception, *args, **kwargs):
            return "recovered"

        @handle_errors(recovery_strategy=recovery_strategy)
        def test_function():
            raise ValueError("Test error")

        with patch('cc_orchestrator.utils.logging.get_logger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger

            result = test_function()

            assert result == "recovered"
            assert mock_logger.info.call_count >= 2  # Recovery attempt and success

    def test_handle_errors_with_recovery_strategy_failure(self):
        """Test handle_errors decorator with failed recovery."""
        def recovery_strategy(exception, *args, **kwargs):
            raise RuntimeError("Recovery failed")

        @handle_errors(recovery_strategy=recovery_strategy)
        def test_function():
            raise ValueError("Test error")

        with patch('cc_orchestrator.utils.logging.get_logger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger

            with pytest.raises(CCOrchestratorException):
                test_function()

            # Should log both the original error and recovery failure
            assert mock_logger.error.call_count >= 2

    def test_handle_errors_no_reraise(self):
        """Test handle_errors decorator with reraise=False."""
        @handle_errors(reraise=False)
        def test_function():
            raise ValueError("Test error")

        with patch('cc_orchestrator.utils.logging.get_logger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger

            result = test_function()  # Should not raise

            assert result is None
            mock_logger.error.assert_called()

    def test_handle_errors_custom_log_context(self):
        """Test handle_errors decorator with custom log context."""
        @handle_errors(log_context=LogContext.WEB)
        def test_function():
            return "success"

        with patch('cc_orchestrator.utils.logging.get_logger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger

            test_function()

            mock_get_logger.assert_called()
            get_logger_call = mock_get_logger.call_args
            assert get_logger_call[0][1] == LogContext.WEB

    def test_handle_errors_preserves_function_metadata(self):
        """Test handle_errors decorator preserves function metadata."""
        @handle_errors()
        def test_function():
            """Test docstring"""
            return "test"

        assert test_function.__name__ == "test_function"
        assert test_function.__doc__ == "Test docstring"


class TestLogPerformanceDecorator:
    """Test log_performance decorator."""

    def test_log_performance_successful_execution(self):
        """Test log_performance decorator with successful execution."""
        @log_performance()
        def test_function():
            time.sleep(0.01)  # Small delay for timing
            return "success"

        with patch('cc_orchestrator.utils.logging.get_logger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger

            result = test_function()

            assert result == "success"
            assert mock_logger.debug.call_count == 1  # Performance tracking started
            assert mock_logger.info.call_count == 1   # Performance completed

            info_call = mock_logger.info.call_args
            assert "Performance: test_function completed" in info_call[0][0]
            assert "execution_time" in info_call[1]
            assert "status" in info_call[1]
            assert info_call[1]["status"] == "success"

    def test_log_performance_with_exception(self):
        """Test log_performance decorator when function raises exception."""
        @log_performance()
        def test_function():
            time.sleep(0.01)  # Small delay for timing
            raise ValueError("Test error")

        with patch('cc_orchestrator.utils.logging.get_logger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger

            with pytest.raises(ValueError):
                test_function()

            assert mock_logger.debug.call_count == 1  # Performance tracking started
            assert mock_logger.warning.call_count == 1  # Performance failed

            warning_call = mock_logger.warning.call_args
            assert "Performance: test_function failed" in warning_call[0][0]
            assert "execution_time" in warning_call[1]
            assert "status" in warning_call[1]
            assert warning_call[1]["status"] == "error"

    def test_log_performance_custom_context(self):
        """Test log_performance decorator with custom log context."""
        @log_performance(log_context=LogContext.DATABASE)
        def test_function():
            return "success"

        with patch('cc_orchestrator.utils.logging.get_logger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger

            test_function()

            mock_get_logger.assert_called()
            get_logger_call = mock_get_logger.call_args
            assert get_logger_call[0][1] == LogContext.DATABASE

    def test_log_performance_timing_accuracy(self):
        """Test log_performance decorator measures time accurately."""
        @log_performance()
        def test_function():
            time.sleep(0.1)  # 100ms delay
            return "success"

        with patch('cc_orchestrator.utils.logging.get_logger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger

            test_function()

            info_call = mock_logger.info.call_args
            execution_time = info_call[1]["execution_time"]
            assert 0.09 <= execution_time <= 0.15  # Allow some variance

    def test_log_performance_preserves_function_metadata(self):
        """Test log_performance decorator preserves function metadata."""
        @log_performance()
        def test_function():
            """Test docstring"""
            return "test"

        assert test_function.__name__ == "test_function"
        assert test_function.__doc__ == "Test docstring"


class TestAuditLogDecorator:
    """Test audit_log decorator."""

    def test_audit_log_successful_execution(self):
        """Test audit_log decorator with successful execution."""
        @audit_log("user_login")
        def test_function(username):
            return f"logged in {username}"

        with patch('cc_orchestrator.utils.logging.get_logger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger

            result = test_function("testuser")

            assert result == "logged in testuser"
            assert mock_logger.info.call_count == 2  # Started and completed

            start_call = mock_logger.info.call_args_list[0]
            assert "Audit: user_login started" in start_call[0][0]
            assert start_call[1]["action"] == "user_login"

            complete_call = mock_logger.info.call_args_list[1]
            assert "Audit: user_login completed successfully" in complete_call[0][0]
            assert complete_call[1]["status"] == "success"

    def test_audit_log_with_exception(self):
        """Test audit_log decorator when function raises exception."""
        @audit_log("dangerous_operation")
        def test_function():
            raise PermissionError("Access denied")

        with patch('cc_orchestrator.utils.logging.get_logger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger

            with pytest.raises(PermissionError):
                test_function()

            assert mock_logger.info.call_count == 1   # Started
            assert mock_logger.error.call_count == 1  # Failed

            error_call = mock_logger.error.call_args
            assert "Audit: dangerous_operation failed" in error_call[0][0]
            assert error_call[1]["status"] == "error"
            assert error_call[1]["error"] == "Access denied"

    def test_audit_log_custom_context(self):
        """Test audit_log decorator with custom log context."""
        @audit_log("system_config", log_context=LogContext.CLI)
        def test_function():
            return "configured"

        with patch('cc_orchestrator.utils.logging.get_logger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger

            test_function()

            mock_get_logger.assert_called()
            get_logger_call = mock_get_logger.call_args
            assert get_logger_call[0][1] == LogContext.CLI

    def test_audit_log_args_hashing(self):
        """Test audit_log decorator hashes function arguments."""
        @audit_log("data_access")
        def test_function(data_id, sensitive_info):
            return "accessed"

        with patch('cc_orchestrator.utils.logging.get_logger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger

            test_function("id123", "secret")

            start_call = mock_logger.info.call_args_list[0]
            assert "args_hash" in start_call[1]
            assert isinstance(start_call[1]["args_hash"], int)

    def test_audit_log_logger_name(self):
        """Test audit_log decorator uses correct logger name."""
        @audit_log("test_action")
        def test_function():
            return "done"

        with patch('cc_orchestrator.utils.logging.get_logger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger

            test_function()

            get_logger_call = mock_get_logger.call_args
            assert get_logger_call[0][0].endswith(".audit")

    def test_audit_log_preserves_function_metadata(self):
        """Test audit_log decorator preserves function metadata."""
        @audit_log("test_action")
        def test_function():
            """Test docstring"""
            return "test"

        assert test_function.__name__ == "test_function"
        assert test_function.__doc__ == "Test docstring"


class TestModuleLevelLogger:
    """Test module-level orchestrator_logger instance."""

    def test_orchestrator_logger_exists(self):
        """Test module-level orchestrator_logger exists."""
        assert orchestrator_logger is not None
        assert isinstance(orchestrator_logger, ContextualLogger)

    def test_orchestrator_logger_context(self):
        """Test orchestrator_logger has correct context."""
        assert orchestrator_logger.context == "orchestrator"

    def test_orchestrator_logger_functionality(self):
        """Test orchestrator_logger can be used for logging."""
        with patch('logging.getLogger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger

            # Create a fresh logger instance for testing
            test_logger = get_logger("test_module", LogContext.ORCHESTRATOR)
            test_logger.info("Test module-level logging")

            mock_logger.log.assert_called_once_with(
                logging.INFO,
                "Test module-level logging",
                extra={"context": "orchestrator"}
            )


class TestIntegrationScenarios:
    """Test integration scenarios combining multiple logging features."""

    def test_comprehensive_logging_workflow(self):
        """Test comprehensive logging workflow with all components."""
        with patch('cc_orchestrator.utils.logging.get_logger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger

            @audit_log("complex_operation", LogContext.INTEGRATION)
            @log_performance(LogContext.INTEGRATION)
            @handle_errors(log_context=LogContext.INTEGRATION)
            def complex_function(data):
                logger = get_logger(__name__, LogContext.INTEGRATION)
                logger.set_instance_id("instance-complex")
                logger.set_task_id("task-complex")
                logger.info("Processing complex data", data_size=len(data))
                return f"processed {len(data)} items"

            result = complex_function("test_data")

            assert result == "processed 9 items"
            # Verify multiple logging calls were made
            assert mock_logger.debug.call_count >= 2  # handle_errors + performance
            assert mock_logger.info.call_count >= 3   # audit start/complete + performance + custom

    def test_exception_handling_with_structured_logging(self):
        """Test exception handling integrates properly with structured logging."""
        @handle_errors(log_context=LogContext.TASK)
        def failing_function():
            logger = get_logger(__name__, LogContext.TASK)
            logger.set_instance_id("failing-instance")
            raise TaskError("Task execution failed", {"task_type": "complex"})

        with patch('cc_orchestrator.utils.logging.get_logger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger

            with pytest.raises(TaskError):
                failing_function()

            # Verify error logging was called
            mock_logger.error.assert_called()

    def test_multiple_loggers_with_different_contexts(self):
        """Test multiple loggers with different contexts work independently."""
        web_logger = get_logger("web_module", LogContext.WEB)
        db_logger = get_logger("db_module", LogContext.DATABASE)

        web_logger.set_instance_id("web-123")
        db_logger.set_instance_id("db-456")

        assert web_logger.context == "web"
        assert db_logger.context == "database"
        assert web_logger.instance_id == "web-123"
        assert db_logger.instance_id == "db-456"

    def test_all_exception_types_inheritance(self):
        """Test all custom exception types inherit correctly."""
        exceptions = [
            InstanceError("instance error"),
            WorktreeError("worktree error"),
            TaskError("task error"),
            ConfigurationError("config error"),
            IntegrationError("integration error"),
            DatabaseError("database error"),
            TmuxError("tmux error")
        ]

        for exc in exceptions:
            assert isinstance(exc, CCOrchestratorException)
            assert isinstance(exc, Exception)
            assert hasattr(exc, 'message')
            assert hasattr(exc, 'context')
            assert hasattr(exc, 'timestamp')
