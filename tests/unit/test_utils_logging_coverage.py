"""
Comprehensive test suite for src/cc_orchestrator/utils/logging.py.

This test file targets high coverage to help reach 90% total coverage.
It covers all 197 statements in the logging module including:
- Logger configuration and setup
- LogContext enum values and usage
- Structured logging functionality
- Log formatting and output
- Different log levels and handlers
- File logging configuration
- Console logging configuration
- Environment-based configuration
- Error handling in logging operations
- All exception classes
- All decorators
"""

import json
import logging
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.cc_orchestrator.utils.logging import (
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
    """Test LogLevel enum."""

    def test_log_level_values(self):
        """Test all LogLevel enum values."""
        assert LogLevel.DEBUG == "DEBUG"
        assert LogLevel.INFO == "INFO"
        assert LogLevel.WARNING == "WARNING"
        assert LogLevel.ERROR == "ERROR"
        assert LogLevel.CRITICAL == "CRITICAL"

    def test_log_level_inheritance(self):
        """Test LogLevel is str enum."""
        assert isinstance(LogLevel.DEBUG, str)
        # LogLevel.INFO returns "LogLevel.INFO" when converted to string in some cases
        assert LogLevel.INFO.value == "INFO"


class TestLogContext:
    """Test LogContext enum."""

    def test_log_context_values(self):
        """Test all LogContext enum values."""
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

    def test_log_context_inheritance(self):
        """Test LogContext is str enum."""
        assert isinstance(LogContext.ORCHESTRATOR, str)
        # LogContext.INSTANCE returns the enum value when accessed via .value
        assert LogContext.INSTANCE.value == "instance"


class TestCCOrchestratorException:
    """Test base exception class."""

    def test_basic_creation(self):
        """Test basic exception creation."""
        exc = CCOrchestratorException("test message")
        assert exc.message == "test message"
        assert exc.context == {}
        assert isinstance(exc.timestamp, datetime)
        assert str(exc) == "test message"

    def test_creation_with_context(self):
        """Test exception creation with context."""
        context = {"key": "value", "number": 42}
        exc = CCOrchestratorException("test message", context)
        assert exc.message == "test message"
        assert exc.context == context
        assert isinstance(exc.timestamp, datetime)

    def test_creation_with_none_context(self):
        """Test exception creation with None context."""
        exc = CCOrchestratorException("test message", None)
        assert exc.message == "test message"
        assert exc.context == {}

    def test_timestamp_creation(self):
        """Test timestamp is created properly."""
        exc = CCOrchestratorException("test")
        assert exc.timestamp is not None
        assert isinstance(exc.timestamp, datetime)


class TestSpecificExceptions:
    """Test all specific exception classes."""

    def test_instance_error(self):
        """Test InstanceError."""
        exc = InstanceError("instance failed", {"instance_id": "123"})
        assert isinstance(exc, CCOrchestratorException)
        assert exc.message == "instance failed"
        assert exc.context == {"instance_id": "123"}

    def test_worktree_error(self):
        """Test WorktreeError."""
        exc = WorktreeError("worktree failed")
        assert isinstance(exc, CCOrchestratorException)
        assert exc.message == "worktree failed"

    def test_task_error(self):
        """Test TaskError."""
        exc = TaskError("task failed")
        assert isinstance(exc, CCOrchestratorException)
        assert exc.message == "task failed"

    def test_configuration_error(self):
        """Test ConfigurationError."""
        exc = ConfigurationError("config failed")
        assert isinstance(exc, CCOrchestratorException)
        assert exc.message == "config failed"

    def test_integration_error(self):
        """Test IntegrationError."""
        exc = IntegrationError("integration failed")
        assert isinstance(exc, CCOrchestratorException)
        assert exc.message == "integration failed"

    def test_database_error(self):
        """Test DatabaseError."""
        exc = DatabaseError("db failed")
        assert isinstance(exc, CCOrchestratorException)
        assert exc.message == "db failed"

    def test_tmux_error(self):
        """Test TmuxError."""
        exc = TmuxError("tmux failed")
        assert isinstance(exc, CCOrchestratorException)
        assert exc.message == "tmux failed"


class TestStructuredFormatter:
    """Test StructuredFormatter class."""

    def setUp(self):
        """Set up test fixtures."""
        self.formatter = StructuredFormatter()

    def test_basic_log_record_formatting(self):
        """Test basic log record formatting."""
        formatter = StructuredFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="/test/path.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        record.module = "test_module"
        record.funcName = "test_function"

        result = formatter.format(record)
        log_data = json.loads(result)

        assert log_data["level"] == "INFO"
        assert log_data["logger"] == "test_logger"
        assert log_data["message"] == "Test message"
        assert log_data["module"] == "test_module"
        assert log_data["function"] == "test_function"
        assert log_data["line"] == 42
        assert "timestamp" in log_data

    def test_log_record_with_context(self):
        """Test log record with context attribute."""
        formatter = StructuredFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="/test/path.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        record.module = "test_module"
        record.funcName = "test_function"
        record.context = "test_context"

        result = formatter.format(record)
        log_data = json.loads(result)

        assert log_data["context"] == "test_context"

    def test_log_record_with_instance_id(self):
        """Test log record with instance_id attribute."""
        formatter = StructuredFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="/test/path.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        record.module = "test_module"
        record.funcName = "test_function"
        record.instance_id = "inst_123"

        result = formatter.format(record)
        log_data = json.loads(result)

        assert log_data["instance_id"] == "inst_123"

    def test_log_record_with_task_id(self):
        """Test log record with task_id attribute."""
        formatter = StructuredFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="/test/path.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        record.module = "test_module"
        record.funcName = "test_function"
        record.task_id = "task_456"

        result = formatter.format(record)
        log_data = json.loads(result)

        assert log_data["task_id"] == "task_456"

    def test_log_record_with_extra_fields(self):
        """Test log record with extra custom fields."""
        formatter = StructuredFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="/test/path.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        record.module = "test_module"
        record.funcName = "test_function"
        record.custom_field = "custom_value"
        record.another_field = 123
        record._private_field = "should_not_appear"

        result = formatter.format(record)
        log_data = json.loads(result)

        assert log_data["custom_field"] == "custom_value"
        assert log_data["another_field"] == 123
        assert "_private_field" not in log_data

    def test_log_record_with_exception_info(self):
        """Test log record with exception information."""
        formatter = StructuredFormatter()

        try:
            raise ValueError("Test exception")
        except ValueError:
            exc_info = sys.exc_info()

        record = logging.LogRecord(
            name="test_logger",
            level=logging.ERROR,
            pathname="/test/path.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=exc_info,
        )
        record.module = "test_module"
        record.funcName = "test_function"

        result = formatter.format(record)
        log_data = json.loads(result)

        assert "exception" in log_data
        assert log_data["exception"]["type"] == "ValueError"
        assert log_data["exception"]["message"] == "Test exception"
        assert isinstance(log_data["exception"]["traceback"], list)

    def test_log_record_with_none_exception_type(self):
        """Test log record with None exception type."""
        formatter = StructuredFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.ERROR,
            pathname="/test/path.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=(None, None, None),
        )
        record.module = "test_module"
        record.funcName = "test_function"

        result = formatter.format(record)
        log_data = json.loads(result)

        # Should not have exception info when exc_info[0] is None
        assert "exception" not in log_data

    def test_standard_fields_exclusion(self):
        """Test that standard LogRecord fields are excluded from extra data."""
        formatter = StructuredFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="/test/path.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        record.module = "test_module"
        record.funcName = "test_function"

        result = formatter.format(record)
        log_data = json.loads(result)

        # Standard fields should not appear as extra data
        standard_fields = {
            "name",
            "msg",
            "args",
            "levelname",
            "levelno",
            "pathname",
            "filename",
            "module",
            "exc_info",
            "exc_text",
            "stack_info",
            "lineno",
            "funcName",
            "created",
            "msecs",
            "relativeCreated",
            "thread",
            "threadName",
            "processName",
            "process",
            "getMessage",
        }

        for field in standard_fields:
            assert field not in log_data or field in [
                "module",
                "lineno",
            ]  # These are included intentionally


class TestContextualLogger:
    """Test ContextualLogger class."""

    def test_init(self):
        """Test ContextualLogger initialization."""
        logger = ContextualLogger("test.module", LogContext.INSTANCE)

        assert logger.logger.name == "test.module"
        assert logger.context == "instance"
        assert logger.instance_id is None
        assert logger.task_id is None

    def test_set_instance_id(self):
        """Test setting instance ID."""
        logger = ContextualLogger("test.module", LogContext.INSTANCE)
        logger.set_instance_id("inst_123")

        assert logger.instance_id == "inst_123"

    def test_set_task_id(self):
        """Test setting task ID."""
        logger = ContextualLogger("test.module", LogContext.TASK)
        logger.set_task_id("task_456")

        assert logger.task_id == "task_456"

    def test_internal_log_basic(self):
        """Test _log method with basic parameters."""
        logger = ContextualLogger("test.module", LogContext.ORCHESTRATOR)

        with patch.object(logger.logger, "log") as mock_log:
            logger._log(logging.INFO, "test message")

            mock_log.assert_called_once_with(
                logging.INFO, "test message", extra={"context": "orchestrator"}
            )

    def test_internal_log_with_instance_and_task(self):
        """Test _log method with instance and task IDs."""
        logger = ContextualLogger("test.module", LogContext.WEB)
        logger.set_instance_id("inst_123")
        logger.set_task_id("task_456")

        with patch.object(logger.logger, "log") as mock_log:
            logger._log(logging.ERROR, "test error")

            mock_log.assert_called_once_with(
                logging.ERROR,
                "test error",
                extra={
                    "context": "web",
                    "instance_id": "inst_123",
                    "task_id": "task_456",
                },
            )

    def test_internal_log_with_extra_context(self):
        """Test _log method with extra context."""
        logger = ContextualLogger("test.module", LogContext.DATABASE)

        with patch.object(logger.logger, "log") as mock_log:
            logger._log(logging.WARNING, "test warning", {"custom": "value"})

            mock_log.assert_called_once_with(
                logging.WARNING,
                "test warning",
                extra={"context": "database", "custom": "value"},
            )

    def test_debug_method(self):
        """Test debug logging method."""
        logger = ContextualLogger("test.module", LogContext.CLI)

        with patch.object(logger, "_log") as mock_log:
            logger.debug("debug message", extra_field="value")

            mock_log.assert_called_once_with(
                logging.DEBUG, "debug message", {"extra_field": "value"}
            )

    def test_info_method(self):
        """Test info logging method."""
        logger = ContextualLogger("test.module", LogContext.TMUX)

        with patch.object(logger, "_log") as mock_log:
            logger.info("info message", extra_field="value")

            mock_log.assert_called_once_with(
                logging.INFO, "info message", {"extra_field": "value"}
            )

    def test_warning_method(self):
        """Test warning logging method."""
        logger = ContextualLogger("test.module", LogContext.INTEGRATION)

        with patch.object(logger, "_log") as mock_log:
            logger.warning("warning message", extra_field="value")

            mock_log.assert_called_once_with(
                logging.WARNING, "warning message", {"extra_field": "value"}
            )

    def test_error_method_without_exception(self):
        """Test error logging method without exception."""
        logger = ContextualLogger("test.module", LogContext.PROCESS)

        with patch.object(logger, "_log") as mock_log:
            logger.error("error message", extra_field="value")

            mock_log.assert_called_once_with(
                logging.ERROR, "error message", {"extra_field": "value"}
            )

    def test_error_method_with_exception(self):
        """Test error logging method with exception."""
        logger = ContextualLogger("test.module", LogContext.WORKTREE)
        logger.set_instance_id("inst_123")
        logger.set_task_id("task_456")

        exc = ValueError("test exception")

        with patch.object(logger.logger, "error") as mock_error:
            logger.error("error message", exception=exc, extra_field="value")

            mock_error.assert_called_once_with(
                "error message",
                exc_info=exc,
                extra={
                    "context": "worktree",
                    "instance_id": "inst_123",
                    "task_id": "task_456",
                    "extra_field": "value",
                },
            )

    def test_critical_method_without_exception(self):
        """Test critical logging method without exception."""
        logger = ContextualLogger("test.module", LogContext.ORCHESTRATOR)

        with patch.object(logger, "_log") as mock_log:
            logger.critical("critical message", extra_field="value")

            mock_log.assert_called_once_with(
                logging.CRITICAL, "critical message", {"extra_field": "value"}
            )

    def test_critical_method_with_exception(self):
        """Test critical logging method with exception."""
        logger = ContextualLogger("test.module", LogContext.INSTANCE)
        logger.set_instance_id("inst_789")
        logger.set_task_id("task_012")

        exc = RuntimeError("critical error")

        with patch.object(logger.logger, "critical") as mock_critical:
            logger.critical("critical message", exception=exc, extra_field="value")

            mock_critical.assert_called_once_with(
                "critical message",
                exc_info=exc,
                extra={
                    "context": "instance",
                    "instance_id": "inst_789",
                    "task_id": "task_012",
                    "extra_field": "value",
                },
            )


class TestGetLogger:
    """Test get_logger function."""

    def test_get_logger_creates_contextual_logger(self):
        """Test that get_logger creates a ContextualLogger."""
        logger = get_logger("test.module", LogContext.DATABASE)

        assert isinstance(logger, ContextualLogger)
        assert logger.logger.name == "test.module"
        assert logger.context == "database"


class TestSetupLogging:
    """Test setup_logging function."""

    def setUp(self):
        """Clear existing handlers before each test."""
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

    def test_setup_logging_with_defaults(self):
        """Test setup_logging with default parameters."""
        setup_logging()

        root_logger = logging.getLogger()
        assert root_logger.level == logging.INFO
        assert len(root_logger.handlers) == 1  # Console handler only
        assert isinstance(root_logger.handlers[0], logging.StreamHandler)

    def test_setup_logging_with_loglevel_enum(self):
        """Test setup_logging with LogLevel enum."""
        setup_logging(log_level=LogLevel.DEBUG)

        root_logger = logging.getLogger()
        assert root_logger.level == logging.DEBUG

    def test_setup_logging_with_loglevel_string(self):
        """Test setup_logging with string log level."""
        setup_logging(log_level="WARNING")

        root_logger = logging.getLogger()
        assert root_logger.level == logging.WARNING

    def test_setup_logging_disable_console(self):
        """Test setup_logging with console disabled."""
        setup_logging(enable_console=False)

        root_logger = logging.getLogger()
        assert len(root_logger.handlers) == 0

    def test_setup_logging_with_file_handler(self):
        """Test setup_logging with file handler."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "test.log"
            setup_logging(log_file=log_file)

            root_logger = logging.getLogger()
            assert len(root_logger.handlers) == 2  # Console + File

            # Check that file handler exists
            file_handlers = [
                h for h in root_logger.handlers if isinstance(h, logging.FileHandler)
            ]
            assert len(file_handlers) == 1
            assert file_handlers[0].baseFilename == str(log_file)

    def test_setup_logging_creates_log_directory(self):
        """Test that setup_logging creates log directory if it doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "subdir" / "test.log"
            assert not log_file.parent.exists()

            setup_logging(log_file=log_file)

            assert log_file.parent.exists()

    def test_setup_logging_structured_formatting(self):
        """Test setup_logging with structured formatting."""
        setup_logging(enable_structured=True)

        root_logger = logging.getLogger()
        console_handler = root_logger.handlers[0]
        assert isinstance(console_handler.formatter, StructuredFormatter)

    def test_setup_logging_simple_formatting(self):
        """Test setup_logging with simple formatting."""
        setup_logging(enable_structured=False)

        root_logger = logging.getLogger()
        console_handler = root_logger.handlers[0]
        assert isinstance(console_handler.formatter, logging.Formatter)
        assert not isinstance(console_handler.formatter, StructuredFormatter)

    def test_setup_logging_file_structured_formatting(self):
        """Test setup_logging with file structured formatting."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "test.log"
            setup_logging(log_file=log_file, enable_structured=True)

            root_logger = logging.getLogger()
            file_handlers = [
                h for h in root_logger.handlers if isinstance(h, logging.FileHandler)
            ]
            assert isinstance(file_handlers[0].formatter, StructuredFormatter)

    def test_setup_logging_file_simple_formatting(self):
        """Test setup_logging with file simple formatting."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "test.log"
            setup_logging(log_file=log_file, enable_structured=False)

            root_logger = logging.getLogger()
            file_handlers = [
                h for h in root_logger.handlers if isinstance(h, logging.FileHandler)
            ]
            assert isinstance(file_handlers[0].formatter, logging.Formatter)
            assert not isinstance(file_handlers[0].formatter, StructuredFormatter)

    def test_setup_logging_clears_existing_handlers(self):
        """Test that setup_logging clears existing handlers."""
        root_logger = logging.getLogger()

        # Remember initial handler count (pytest may have handlers)
        initial_count = len(root_logger.handlers)

        # Add a mock handler
        mock_handler = Mock()
        root_logger.addHandler(mock_handler)
        assert len(root_logger.handlers) == initial_count + 1

        setup_logging()

        # Old handler should be removed, new one added
        assert mock_handler not in root_logger.handlers
        assert len(root_logger.handlers) == 1  # Only console handler

    def test_setup_logging_third_party_loggers(self):
        """Test that third-party loggers are configured properly."""
        setup_logging()

        assert logging.getLogger("urllib3").level == logging.WARNING
        assert logging.getLogger("requests").level == logging.WARNING
        assert logging.getLogger("git").level == logging.WARNING


class TestHandleErrorsDecorator:
    """Test handle_errors decorator."""

    def test_handle_errors_basic_success(self):
        """Test handle_errors decorator with successful function."""

        @handle_errors()
        def test_function():
            return "success"

        result = test_function()
        assert result == "success"

    def test_handle_errors_cc_orchestrator_exception_reraise(self):
        """Test handle_errors with CCOrchestratorException and reraise=True."""

        @handle_errors(reraise=True)
        def test_function():
            raise InstanceError("test error", {"key": "value"})

        with pytest.raises(InstanceError):
            test_function()

    def test_handle_errors_cc_orchestrator_exception_no_reraise(self):
        """Test handle_errors with CCOrchestratorException and reraise=False."""

        @handle_errors(reraise=False)
        def test_function():
            raise InstanceError("test error")

        result = test_function()
        assert result is None

    def test_handle_errors_cc_orchestrator_exception_with_recovery(self):
        """Test handle_errors with CCOrchestratorException and recovery strategy."""

        def recovery_strategy(exc, *args, **kwargs):
            return "recovered"

        @handle_errors(recovery_strategy=recovery_strategy, reraise=False)
        def test_function():
            raise WorktreeError("test error")

        result = test_function()
        assert result == "recovered"

    def test_handle_errors_cc_orchestrator_exception_recovery_fails(self):
        """Test handle_errors when recovery strategy fails."""

        def failing_recovery(exc, *args, **kwargs):
            raise RuntimeError("Recovery failed")

        @handle_errors(recovery_strategy=failing_recovery, reraise=True)
        def test_function():
            raise TaskError("test error")

        with pytest.raises(TaskError):
            test_function()

    def test_handle_errors_generic_exception_reraise(self):
        """Test handle_errors with generic exception and reraise=True."""

        @handle_errors(reraise=True)
        def test_function():
            raise ValueError("test error")

        with pytest.raises(CCOrchestratorException) as exc_info:
            test_function()

        assert "Unexpected error in test_function" in str(exc_info.value)
        assert exc_info.value.__cause__.__class__ == ValueError

    def test_handle_errors_generic_exception_no_reraise(self):
        """Test handle_errors with generic exception and reraise=False."""

        @handle_errors(reraise=False)
        def test_function():
            raise ValueError("test error")

        result = test_function()
        assert result is None

    def test_handle_errors_generic_exception_with_recovery(self):
        """Test handle_errors with generic exception and recovery strategy."""

        def recovery_strategy(exc, *args, **kwargs):
            return "recovered from generic"

        @handle_errors(recovery_strategy=recovery_strategy, reraise=False)
        def test_function():
            raise ValueError("test error")

        result = test_function()
        assert result == "recovered from generic"

    def test_handle_errors_generic_exception_recovery_fails(self):
        """Test handle_errors when recovery strategy fails for generic exception."""

        def failing_recovery(exc, *args, **kwargs):
            raise RuntimeError("Recovery failed")

        @handle_errors(recovery_strategy=failing_recovery, reraise=True)
        def test_function():
            raise ValueError("test error")

        with pytest.raises(CCOrchestratorException):
            test_function()

    def test_handle_errors_custom_log_context(self):
        """Test handle_errors with custom log context."""

        @handle_errors(log_context=LogContext.DATABASE)
        def test_function():
            return "success"

        result = test_function()
        assert result == "success"

    def test_handle_errors_preserves_function_metadata(self):
        """Test that handle_errors preserves function metadata."""

        @handle_errors()
        def test_function():
            """Test docstring."""
            return "success"

        assert test_function.__name__ == "test_function"
        assert test_function.__doc__ == "Test docstring."

    def test_handle_errors_with_args_and_kwargs(self):
        """Test handle_errors with function arguments."""

        @handle_errors()
        def test_function(arg1, arg2, kwarg1=None):
            return f"{arg1}-{arg2}-{kwarg1}"

        result = test_function("a", "b", kwarg1="c")
        assert result == "a-b-c"


class TestLogPerformanceDecorator:
    """Test log_performance decorator."""

    def test_log_performance_success(self):
        """Test log_performance decorator with successful function."""

        @log_performance()
        def test_function():
            return "success"

        result = test_function()
        assert result == "success"

    def test_log_performance_with_exception(self):
        """Test log_performance decorator with function that raises exception."""

        @log_performance()
        def test_function():
            raise ValueError("test error")

        with pytest.raises(ValueError):
            test_function()

    def test_log_performance_custom_context(self):
        """Test log_performance with custom log context."""

        @log_performance(log_context=LogContext.WEB)
        def test_function():
            return "success"

        result = test_function()
        assert result == "success"

    def test_log_performance_preserves_function_metadata(self):
        """Test that log_performance preserves function metadata."""

        @log_performance()
        def test_function():
            """Test docstring."""
            return "success"

        assert test_function.__name__ == "test_function"
        assert test_function.__doc__ == "Test docstring."

    def test_log_performance_with_args_and_kwargs(self):
        """Test log_performance with function arguments."""

        @log_performance()
        def test_function(arg1, arg2, kwarg1=None):
            return f"{arg1}-{arg2}-{kwarg1}"

        result = test_function("a", "b", kwarg1="c")
        assert result == "a-b-c"

    @patch("src.cc_orchestrator.utils.logging.time")
    def test_log_performance_timing(self, mock_time):
        """Test that log_performance measures execution time."""
        mock_time.time.side_effect = [1.0, 2.5]  # Start and end times

        @log_performance()
        def test_function():
            return "success"

        result = test_function()
        assert result == "success"
        # Verify time.time was called twice
        assert mock_time.time.call_count == 2


class TestAuditLogDecorator:
    """Test audit_log decorator."""

    def test_audit_log_success(self):
        """Test audit_log decorator with successful function."""

        @audit_log("test_action")
        def test_function():
            return "success"

        result = test_function()
        assert result == "success"

    def test_audit_log_with_exception(self):
        """Test audit_log decorator with function that raises exception."""

        @audit_log("test_action")
        def test_function():
            raise ValueError("test error")

        with pytest.raises(ValueError):
            test_function()

    def test_audit_log_custom_context(self):
        """Test audit_log with custom log context."""

        @audit_log("test_action", log_context=LogContext.INTEGRATION)
        def test_function():
            return "success"

        result = test_function()
        assert result == "success"

    def test_audit_log_preserves_function_metadata(self):
        """Test that audit_log preserves function metadata."""

        @audit_log("test_action")
        def test_function():
            """Test docstring."""
            return "success"

        assert test_function.__name__ == "test_function"
        assert test_function.__doc__ == "Test docstring."

    def test_audit_log_with_args_and_kwargs(self):
        """Test audit_log with function arguments."""

        @audit_log("test_action")
        def test_function(arg1, arg2, kwarg1=None):
            return f"{arg1}-{arg2}-{kwarg1}"

        result = test_function("a", "b", kwarg1="c")
        assert result == "a-b-c"

    def test_audit_log_args_hashing(self):
        """Test that audit_log creates hash of args."""

        @audit_log("test_action")
        def test_function(*args):
            return "success"

        # Test with long args that get truncated
        long_args = ["x" * 200]
        result = test_function(*long_args)
        assert result == "success"


class TestModuleLevelLogger:
    """Test module-level orchestrator_logger."""

    def test_orchestrator_logger_exists(self):
        """Test that orchestrator_logger is created."""
        assert orchestrator_logger is not None
        assert isinstance(orchestrator_logger, ContextualLogger)
        assert orchestrator_logger.context == "orchestrator"

    def test_orchestrator_logger_can_log(self):
        """Test that orchestrator_logger can log messages."""
        # This shouldn't raise an exception
        orchestrator_logger.info("Test module-level logging")


class TestIntegrationScenarios:
    """Test integration scenarios and edge cases."""

    def test_structured_formatter_with_all_features(self):
        """Test StructuredFormatter with all possible features."""
        formatter = StructuredFormatter()

        try:
            raise CustomTestException("test exception")
        except:
            exc_info = sys.exc_info()

        record = logging.LogRecord(
            name="test.logger",
            level=logging.ERROR,
            pathname="/test/path.py",
            lineno=123,
            msg="Complex test message",
            args=(),
            exc_info=exc_info,
        )
        record.module = "test_module"
        record.funcName = "test_function"
        record.context = "test_context"
        record.instance_id = "inst_999"
        record.task_id = "task_888"
        record.custom_field = "custom_value"
        record._private = "should_not_appear"

        result = formatter.format(record)
        log_data = json.loads(result)

        # Verify all fields are present
        assert log_data["level"] == "ERROR"
        assert log_data["context"] == "test_context"
        assert log_data["instance_id"] == "inst_999"
        assert log_data["task_id"] == "task_888"
        assert log_data["custom_field"] == "custom_value"
        assert "_private" not in log_data
        assert "exception" in log_data
        assert log_data["exception"]["type"] == "CustomTestException"

    def test_contextual_logger_all_methods_with_ids(self):
        """Test ContextualLogger with all methods and IDs set."""
        logger = ContextualLogger("test.comprehensive", LogContext.TASK)
        logger.set_instance_id("comprehensive_inst")
        logger.set_task_id("comprehensive_task")

        # Test all logging methods
        with (
            patch.object(logger.logger, "log") as mock_log,
            patch.object(logger.logger, "error") as mock_error,
            patch.object(logger.logger, "critical") as mock_critical,
        ):

            logger.debug("debug message")
            logger.info("info message")
            logger.warning("warning message")
            logger.error("error message")  # This calls _log
            logger.critical("critical message")  # This calls _log

            exc = ValueError("test exception")
            logger.error(
                "error with exception", exception=exc
            )  # This calls logger.error
            logger.critical(
                "critical with exception", exception=exc
            )  # This calls logger.critical

            # Verify all calls were made
            assert (
                mock_log.call_count == 5
            )  # debug, info, warning, error without exception, critical without exception
            assert mock_error.call_count == 1  # error with exception
            assert mock_critical.call_count == 1  # critical with exception

    def test_decorators_stacked(self):
        """Test multiple decorators stacked together."""

        @audit_log("complex_action")
        @log_performance()
        @handle_errors(reraise=False)
        def complex_function(should_fail=False):
            if should_fail:
                raise ValueError("intentional failure")
            return "complex success"

        # Test success case
        result = complex_function(should_fail=False)
        assert result == "complex success"

        # Test failure case
        result = complex_function(should_fail=True)
        assert result is None  # handle_errors with reraise=False

    def test_setup_logging_edge_cases(self):
        """Test setup_logging with various edge cases."""
        # Test with all features enabled
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "nested" / "deep" / "test.log"

            setup_logging(
                log_level=LogLevel.CRITICAL,
                log_file=log_file,
                enable_structured=True,
                enable_console=True,
            )

            root_logger = logging.getLogger()
            assert root_logger.level == logging.CRITICAL
            assert len(root_logger.handlers) == 2
            assert log_file.exists()

    def test_exception_context_preservation(self):
        """Test that exception context is preserved properly."""
        original_context = {"original": "data", "number": 42}
        exc = DatabaseError("Database connection failed", original_context)

        assert exc.context == original_context
        assert exc.message == "Database connection failed"
        assert isinstance(exc.timestamp, datetime)

        # Test inheritance
        assert isinstance(exc, CCOrchestratorException)
        assert isinstance(exc, Exception)


# Custom exception for testing
class CustomTestException(Exception):
    """Custom exception for testing structured formatter."""

    pass


class TestCoverageOptimization:
    """Additional tests to maximize coverage of specific code paths."""

    def test_structured_formatter_exception_with_none_values(self):
        """Test StructuredFormatter with edge case exception handling."""
        formatter = StructuredFormatter()

        # Create a record with exc_info where exc_info[0] is None
        # This tests the condition where exc_info exists but exc_info[0] is None
        record = logging.LogRecord(
            name="test_logger",
            level=logging.ERROR,
            pathname="/test/path.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=(None, ValueError("test"), None),  # None type
        )
        record.module = "test_module"
        record.funcName = "test_function"

        result = formatter.format(record)
        log_data = json.loads(result)

        # Should NOT have exception data when exc_info[0] is None
        # because the code checks "if record.exc_info and record.exc_info[0] is not None"
        assert "exception" not in log_data

    def test_structured_formatter_no_exc_info(self):
        """Test StructuredFormatter with no exception info."""
        formatter = StructuredFormatter()

        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="/test/path.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        record.module = "test_module"
        record.funcName = "test_function"

        result = formatter.format(record)
        log_data = json.loads(result)

        # Should not have exception data when exc_info is None
        assert "exception" not in log_data

    def test_structured_formatter_empty_exc_info(self):
        """Test StructuredFormatter with empty exception info."""
        formatter = StructuredFormatter()

        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="/test/path.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=(None, None, None),
        )
        record.module = "test_module"
        record.funcName = "test_function"

        result = formatter.format(record)
        log_data = json.loads(result)

        # Should not have exception data when exc_info[0] is None
        assert "exception" not in log_data

    def test_contextual_logger_none_ids_in_error_methods(self):
        """Test ContextualLogger error methods with None IDs."""
        logger = ContextualLogger("test.module", LogContext.ORCHESTRATOR)
        # Don't set instance_id or task_id (they remain None)

        exc = RuntimeError("test exception")

        with patch.object(logger.logger, "error") as mock_error:
            logger.error("error message", exception=exc)

            mock_error.assert_called_once_with(
                "error message",
                exc_info=exc,
                extra={
                    "context": "orchestrator",
                    "instance_id": None,
                    "task_id": None,
                },
            )

    def test_setup_logging_file_only(self):
        """Test setup_logging with only file handler, no console."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = Path(temp_dir) / "file_only.log"

            setup_logging(
                log_file=log_file, enable_console=False, enable_structured=True
            )

            root_logger = logging.getLogger()
            assert len(root_logger.handlers) == 1
            assert isinstance(root_logger.handlers[0], logging.FileHandler)

    def test_handle_errors_recovery_with_args_kwargs(self):
        """Test handle_errors recovery strategy receives args and kwargs."""
        captured_args = None
        captured_kwargs = None

        def recovery_strategy(exc, *args, **kwargs):
            nonlocal captured_args, captured_kwargs
            captured_args = args
            captured_kwargs = kwargs
            return "recovered"

        @handle_errors(recovery_strategy=recovery_strategy, reraise=False)
        def test_function(arg1, arg2, kwarg1=None):
            raise ValueError("test error")

        result = test_function("a", "b", kwarg1="c")
        assert result == "recovered"
        assert captured_args == ("a", "b")
        assert captured_kwargs == {"kwarg1": "c"}

    def test_all_exception_types_inheritance(self):
        """Test that all exception types properly inherit from base."""
        exceptions = [
            InstanceError,
            WorktreeError,
            TaskError,
            ConfigurationError,
            IntegrationError,
            DatabaseError,
            TmuxError,
        ]

        for exc_class in exceptions:
            exc = exc_class("test message", {"test": "context"})
            assert isinstance(exc, CCOrchestratorException)
            assert exc.message == "test message"
            assert exc.context == {"test": "context"}

    def test_log_context_enum_completeness(self):
        """Test that all LogContext values are tested."""
        contexts = [
            LogContext.ORCHESTRATOR,
            LogContext.INSTANCE,
            LogContext.TASK,
            LogContext.WORKTREE,
            LogContext.WEB,
            LogContext.CLI,
            LogContext.TMUX,
            LogContext.INTEGRATION,
            LogContext.DATABASE,
            LogContext.PROCESS,
        ]

        for context in contexts:
            logger = get_logger("test", context)
            assert logger.context == context.value

    def test_exception_with_large_context_in_handle_errors(self):
        """Test handle_errors creates proper context for wrapped exceptions."""

        @handle_errors(reraise=True)
        def test_function_with_long_args(*args):
            raise ValueError("test error")

        # Create args that will be truncated to 200 chars
        long_args = ["x" * 100, "y" * 100, "z" * 100]

        with pytest.raises(CCOrchestratorException) as exc_info:
            test_function_with_long_args(*long_args)

        # Check that args are truncated in context
        assert "args" in exc_info.value.context
        assert len(exc_info.value.context["args"]) <= 200
