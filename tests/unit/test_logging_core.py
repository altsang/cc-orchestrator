"""
Unit tests for the core logging framework.

Tests cover:
- Logging setup and configuration
- Structured formatter
- Contextual logger functionality
- Log level management
- File and console output
"""

import json
import logging
from unittest.mock import patch

from cc_orchestrator.utils.logging import (
    ContextualLogger,
    LogContext,
    LogLevel,
    StructuredFormatter,
    get_logger,
    orchestrator_logger,
    setup_logging,
)


class TestLoggingSetup:
    """Test logging setup and configuration."""

    def test_setup_logging_console_only(self, reset_logging):
        """Test logging setup with console output only."""
        setup_logging(
            log_level=LogLevel.DEBUG, enable_console=True, enable_structured=False
        )

        root_logger = logging.getLogger()
        # Check the level was set correctly
        assert root_logger.level == logging.DEBUG
        assert len(root_logger.handlers) == 1
        assert isinstance(root_logger.handlers[0], logging.StreamHandler)

    def test_setup_logging_file_only(self, temp_log_file, reset_logging):
        """Test logging setup with file output only."""
        setup_logging(
            log_level=LogLevel.INFO,
            log_file=temp_log_file,
            enable_console=False,
            enable_structured=True,
        )

        root_logger = logging.getLogger()
        assert root_logger.level == logging.INFO
        assert len(root_logger.handlers) == 1
        assert isinstance(root_logger.handlers[0], logging.FileHandler)

    def test_setup_logging_both_console_and_file(self, temp_log_file, reset_logging):
        """Test logging setup with both console and file output."""
        setup_logging(
            log_level=LogLevel.WARNING,
            log_file=temp_log_file,
            enable_console=True,
            enable_structured=True,
        )

        root_logger = logging.getLogger()
        assert root_logger.level == logging.WARNING
        assert len(root_logger.handlers) == 2

    def test_setup_logging_creates_log_directory(self, temp_log_dir, reset_logging):
        """Test that logging setup creates log directory if it doesn't exist."""
        log_file = temp_log_dir / "subdir" / "test.log"
        assert not log_file.parent.exists()

        setup_logging(log_file=log_file, enable_console=False)

        assert log_file.parent.exists()

    def test_setup_logging_string_log_level(self, reset_logging):
        """Test logging setup with string log level."""
        setup_logging(log_level="ERROR", enable_console=True)

        root_logger = logging.getLogger()
        assert root_logger.level == logging.ERROR


class TestStructuredFormatter:
    """Test the structured JSON formatter."""

    def test_format_basic_record(self, sample_log_record_object):
        """Test formatting a basic log record."""
        formatter = StructuredFormatter()
        formatted = formatter.format(sample_log_record_object)

        data = json.loads(formatted)
        assert data["level"] == "INFO"
        assert data["logger"] == "test_logger"
        assert data["message"] == "Test message"
        assert data["module"] == "path"
        assert data["function"] == "test_function"
        assert data["line"] == 42
        assert "timestamp" in data

    def test_format_record_with_context(self, sample_log_record_object):
        """Test formatting a record with context information."""
        formatter = StructuredFormatter()
        formatted = formatter.format(sample_log_record_object)

        data = json.loads(formatted)
        assert data["context"] == "test_context"
        assert data["instance_id"] == "test-instance-001"
        assert data["task_id"] == "TEST-123"

    def test_format_record_with_exception(self):
        """Test formatting a record with exception information."""
        try:
            raise ValueError("Test exception")
        except ValueError:
            import sys

            exc_info = sys.exc_info()
            record = logging.LogRecord(
                name="test_logger",
                level=logging.ERROR,
                pathname="/test/path.py",
                lineno=42,
                msg="Error occurred",
                args=(),
                exc_info=exc_info,
            )

        formatter = StructuredFormatter()
        formatted = formatter.format(record)

        data = json.loads(formatted)
        assert "exception" in data
        assert data["exception"]["type"] == "ValueError"
        assert data["exception"]["message"] == "Test exception"
        assert "traceback" in data["exception"]


class TestContextualLogger:
    """Test the contextual logger functionality."""

    def test_contextual_logger_creation(self):
        """Test creating a contextual logger."""
        logger = get_logger("test.module", LogContext.INSTANCE)

        assert isinstance(logger, ContextualLogger)
        assert logger.context == "instance"
        assert logger.instance_id is None
        assert logger.task_id is None

    def test_set_instance_id(self):
        """Test setting instance ID on logger."""
        logger = get_logger("test.module", LogContext.INSTANCE)
        logger.set_instance_id("test-instance-123")

        assert logger.instance_id == "test-instance-123"

    def test_set_task_id(self):
        """Test setting task ID on logger."""
        logger = get_logger("test.module", LogContext.TASK)
        logger.set_task_id("TASK-456")

        assert logger.task_id == "TASK-456"

    @patch("logging.Logger.log")
    def test_debug_logging(self, mock_log):
        """Test debug level logging with context."""
        logger = get_logger("test.module", LogContext.ORCHESTRATOR)
        logger.set_instance_id("instance-123")
        logger.set_task_id("TASK-456")

        logger.debug("Debug message", extra_key="extra_value")

        mock_log.assert_called_once()
        args, kwargs = mock_log.call_args
        assert args[0] == logging.DEBUG
        assert args[1] == "Debug message"
        assert kwargs["extra"]["context"] == "orchestrator"
        assert kwargs["extra"]["instance_id"] == "instance-123"
        assert kwargs["extra"]["task_id"] == "TASK-456"
        assert kwargs["extra"]["extra_key"] == "extra_value"

    @patch("logging.Logger.log")
    def test_info_logging(self, mock_log):
        """Test info level logging with context."""
        logger = get_logger("test.module", LogContext.WEB)
        logger.info("Info message", user_id="user123")

        mock_log.assert_called_once()
        args, kwargs = mock_log.call_args
        assert args[0] == logging.INFO
        assert args[1] == "Info message"
        assert kwargs["extra"]["context"] == "web"
        assert kwargs["extra"]["user_id"] == "user123"

    @patch("logging.Logger.error")
    def test_error_logging_with_exception(self, mock_error):
        """Test error logging with exception information."""
        logger = get_logger("test.module", LogContext.TASK)
        exception = ValueError("Test error")

        logger.error("Error occurred", exception=exception)

        mock_error.assert_called_once()
        args, kwargs = mock_error.call_args
        assert args[0] == "Error occurred"
        assert kwargs["exc_info"] == exception
        assert kwargs["extra"]["context"] == "task"

    @patch("logging.Logger.critical")
    def test_critical_logging_with_exception(self, mock_critical):
        """Test critical logging with exception information."""
        logger = get_logger("test.module", LogContext.DATABASE)
        exception = RuntimeError("Critical error")

        logger.critical("Critical error occurred", exception=exception)

        mock_critical.assert_called_once()
        args, kwargs = mock_critical.call_args
        assert args[0] == "Critical error occurred"
        assert kwargs["exc_info"] == exception
        assert kwargs["extra"]["context"] == "database"


class TestLogContextAndLevels:
    """Test log context and level enumerations."""

    def test_log_level_enum_values(self):
        """Test that LogLevel enum has correct values."""
        assert LogLevel.DEBUG == "DEBUG"
        assert LogLevel.INFO == "INFO"
        assert LogLevel.WARNING == "WARNING"
        assert LogLevel.ERROR == "ERROR"
        assert LogLevel.CRITICAL == "CRITICAL"

    def test_log_context_enum_values(self):
        """Test that LogContext enum has all expected values."""
        expected_contexts = [
            "orchestrator",
            "instance",
            "task",
            "worktree",
            "web",
            "cli",
            "tmux",
            "integration",
            "database",
            "process",
        ]

        for context in expected_contexts:
            assert hasattr(LogContext, context.upper())
            assert getattr(LogContext, context.upper()).value == context


class TestModuleLevelLogger:
    """Test the module-level orchestrator logger."""

    def test_orchestrator_logger_exists(self):
        """Test that the orchestrator logger is available."""
        assert orchestrator_logger is not None
        assert isinstance(orchestrator_logger, ContextualLogger)
        assert orchestrator_logger.context == "orchestrator"


class TestLoggingIntegration:
    """Integration tests for the complete logging system."""

    def test_logger_creation_and_context(self):
        """Test logger creation and context management without file operations."""
        logger = get_logger("integration.test", LogContext.INSTANCE)
        logger.set_instance_id("test-instance")
        logger.set_task_id("TEST-789")

        assert logger.context == "instance"
        assert logger.instance_id == "test-instance"
        assert logger.task_id == "TEST-789"

    def test_multiple_loggers_different_contexts(self):
        """Test multiple loggers with different contexts."""
        instance_logger = get_logger("test.instance", LogContext.INSTANCE)
        task_logger = get_logger("test.task", LogContext.TASK)
        web_logger = get_logger("test.web", LogContext.WEB)

        assert instance_logger.context == "instance"
        assert task_logger.context == "task"
        assert web_logger.context == "web"

        # Test that they're independent
        instance_logger.set_instance_id("inst-001")
        task_logger.set_task_id("TASK-001")

        assert instance_logger.instance_id == "inst-001"
        assert task_logger.task_id == "TASK-001"
        assert web_logger.instance_id is None
        assert web_logger.task_id is None
