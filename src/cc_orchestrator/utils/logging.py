"""
Comprehensive logging and error handling framework for CC-Orchestrator.

This module provides:
- Structured logging configuration
- Custom exception classes
- Error handling decorators
- Context-aware logging utilities
- Performance and audit logging
"""

import functools
import json
import logging
import logging.config
import sys
import time
import traceback
from collections.abc import Callable
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any


class LogLevel(str, Enum):
    """Log level enumeration for type safety."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogContext(str, Enum):
    """Log context categories for structured logging."""

    ORCHESTRATOR = "orchestrator"
    INSTANCE = "instance"
    TASK = "task"
    WORKTREE = "worktree"
    WEB = "web"
    CLI = "cli"
    TMUX = "tmux"
    INTEGRATION = "integration"
    DATABASE = "database"
    PROCESS = "process"


class CCOrchestratorException(Exception):
    """Base exception class for all CC-Orchestrator errors."""

    def __init__(self, message: str, context: dict[str, Any] | None = None):
        super().__init__(message)
        self.message = message
        self.context = context or {}
        self.timestamp = datetime.utcnow()


class InstanceError(CCOrchestratorException):
    """Errors related to Claude instance management."""

    pass


class WorktreeError(CCOrchestratorException):
    """Errors related to git worktree operations."""

    pass


class TaskError(CCOrchestratorException):
    """Errors related to task management and coordination."""

    pass


class ConfigurationError(CCOrchestratorException):
    """Errors related to configuration and setup."""

    pass


class IntegrationError(CCOrchestratorException):
    """Errors related to external integrations (GitHub, Jira, etc.)."""

    pass


class DatabaseError(CCOrchestratorException):
    """Errors related to database operations."""

    pass


class TmuxError(CCOrchestratorException):
    """Errors related to tmux session management."""

    pass


class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured JSON logging."""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add context if available
        if hasattr(record, "context"):
            log_data["context"] = record.context

        # Add instance_id if available
        if hasattr(record, "instance_id"):
            log_data["instance_id"] = record.instance_id

        # Add task_id if available
        if hasattr(record, "task_id"):
            log_data["task_id"] = record.task_id

        # Add all other extra fields from the record
        # Exclude standard LogRecord attributes and our own fields
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
            "context",
            "instance_id",
            "task_id",
        }

        for key, value in record.__dict__.items():
            if key not in standard_fields and not key.startswith("_"):
                log_data[key] = value

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info),
            }

        return json.dumps(log_data)


class ContextualLogger:
    """Logger with context management for structured logging."""

    def __init__(self, name: str, context: LogContext):
        self.logger = logging.getLogger(name)
        self.context = context.value
        self.instance_id: str | None = None
        self.task_id: str | None = None

    def set_instance_id(self, instance_id: str) -> None:
        """Set the instance ID for all subsequent log messages."""
        self.instance_id = instance_id

    def set_task_id(self, task_id: str) -> None:
        """Set the task ID for all subsequent log messages."""
        self.task_id = task_id

    def _log(
        self, level: int, message: str, extra_context: dict[str, Any] | None = None
    ) -> None:
        """Internal logging method with context injection."""
        extra = {
            "context": self.context,
        }

        if self.instance_id:
            extra["instance_id"] = self.instance_id

        if self.task_id:
            extra["task_id"] = self.task_id

        if extra_context:
            extra.update(extra_context)

        self.logger.log(level, message, extra=extra)

    def debug(self, message: str, **kwargs) -> None:
        """Log debug message with context."""
        self._log(logging.DEBUG, message, kwargs)

    def info(self, message: str, **kwargs) -> None:
        """Log info message with context."""
        self._log(logging.INFO, message, kwargs)

    def warning(self, message: str, **kwargs) -> None:
        """Log warning message with context."""
        self._log(logging.WARNING, message, kwargs)

    def error(self, message: str, exception: Exception | None = None, **kwargs) -> None:
        """Log error message with context and optional exception."""
        if exception:
            self.logger.error(
                message,
                exc_info=exception,
                extra={
                    "context": self.context,
                    "instance_id": self.instance_id,
                    "task_id": self.task_id,
                    **kwargs,
                },
            )
        else:
            self._log(logging.ERROR, message, kwargs)

    def critical(
        self, message: str, exception: Exception | None = None, **kwargs
    ) -> None:
        """Log critical message with context and optional exception."""
        if exception:
            self.logger.critical(
                message,
                exc_info=exception,
                extra={
                    "context": self.context,
                    "instance_id": self.instance_id,
                    "task_id": self.task_id,
                    **kwargs,
                },
            )
        else:
            self._log(logging.CRITICAL, message, kwargs)


def get_logger(name: str, context: LogContext) -> ContextualLogger:
    """Get a contextual logger instance."""
    return ContextualLogger(name, context)


def setup_logging(
    log_level: str | LogLevel = LogLevel.INFO,
    log_file: Path | None = None,
    enable_structured: bool = True,
    enable_console: bool = True,
) -> None:
    """
    Setup comprehensive logging configuration.

    Args:
        log_level: Minimum log level to capture
        log_file: Optional file path for log output
        enable_structured: Use JSON structured logging format
        enable_console: Enable console output
    """
    if isinstance(log_level, LogLevel):
        log_level = log_level.value

    # Create logs directory if using file logging
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)

    handlers = []

    # Console handler
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        if enable_structured:
            console_handler.setFormatter(StructuredFormatter())
        else:
            console_handler.setFormatter(
                logging.Formatter(
                    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                )
            )
        handlers.append(console_handler)

    # File handler
    if log_file:
        file_handler = logging.FileHandler(log_file)
        if enable_structured:
            file_handler.setFormatter(StructuredFormatter())
        else:
            file_handler.setFormatter(
                logging.Formatter(
                    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                )
            )
        handlers.append(file_handler)

    # Configure root logger
    root_logger = logging.getLogger()

    # Clear existing handlers first
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Set level and add our handlers
    root_logger.setLevel(getattr(logging, log_level.upper()))
    for handler in handlers:
        root_logger.addHandler(handler)

    # Suppress noisy third-party loggers
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("git").setLevel(logging.WARNING)


def handle_errors(
    recovery_strategy: Callable | None = None,
    log_context: LogContext = LogContext.ORCHESTRATOR,
    reraise: bool = True,
):
    """
    Decorator for comprehensive error handling with logging and recovery.

    Args:
        recovery_strategy: Optional function to call for error recovery
        log_context: Context for logging
        reraise: Whether to reraise the exception after handling
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            logger = get_logger(func.__module__, log_context)

            try:
                logger.debug(f"Starting {func.__name__}", function=func.__name__)
                result = func(*args, **kwargs)
                logger.debug(f"Completed {func.__name__}", function=func.__name__)
                return result

            except CCOrchestratorException as e:
                logger.error(
                    f"CC-Orchestrator error in {func.__name__}: {e.message}",
                    exception=e,
                    function=func.__name__,
                    error_context=e.context,
                )

                if recovery_strategy:
                    try:
                        logger.info(f"Attempting recovery for {func.__name__}")
                        recovery_result = recovery_strategy(e, *args, **kwargs)
                        logger.info(f"Recovery successful for {func.__name__}")
                        return recovery_result
                    except Exception as recovery_error:
                        logger.error(
                            f"Recovery failed for {func.__name__}",
                            exception=recovery_error,
                            function=func.__name__,
                        )

                if reraise:
                    raise

            except Exception as e:
                logger.error(
                    f"Unexpected error in {func.__name__}: {str(e)}",
                    exception=e,
                    function=func.__name__,
                )

                if recovery_strategy:
                    try:
                        logger.info(f"Attempting recovery for {func.__name__}")
                        recovery_result = recovery_strategy(e, *args, **kwargs)
                        logger.info(f"Recovery successful for {func.__name__}")
                        return recovery_result
                    except Exception as recovery_error:
                        logger.error(
                            f"Recovery failed for {func.__name__}",
                            exception=recovery_error,
                            function=func.__name__,
                        )

                if reraise:
                    raise CCOrchestratorException(
                        f"Unexpected error in {func.__name__}: {str(e)}",
                        context={"function": func.__name__, "args": str(args)[:200]},
                    ) from e

        return wrapper

    return decorator


def log_performance(log_context: LogContext = LogContext.ORCHESTRATOR):
    """Decorator to log function performance metrics."""

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            logger = get_logger(func.__module__, log_context)

            start_time = time.time()
            logger.debug(
                f"Performance tracking started for {func.__name__}",
                function=func.__name__,
            )

            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time

                logger.info(
                    f"Performance: {func.__name__} completed",
                    function=func.__name__,
                    execution_time=execution_time,
                    status="success",
                )

                return result

            except Exception as e:
                execution_time = time.time() - start_time

                logger.warning(
                    f"Performance: {func.__name__} failed",
                    function=func.__name__,
                    execution_time=execution_time,
                    status="error",
                    error=str(e),
                )

                raise

        return wrapper

    return decorator


def audit_log(action: str, log_context: LogContext = LogContext.ORCHESTRATOR):
    """Decorator for audit logging of important operations."""

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            logger = get_logger(f"{func.__module__}.audit", log_context)

            # Log start of operation
            logger.info(
                f"Audit: {action} started",
                action=action,
                function=func.__name__,
                args_hash=hash(str(args)[:100]),
            )

            try:
                result = func(*args, **kwargs)

                # Log successful completion
                logger.info(
                    f"Audit: {action} completed successfully",
                    action=action,
                    function=func.__name__,
                    status="success",
                )

                return result

            except Exception as e:
                # Log failure
                logger.error(
                    f"Audit: {action} failed",
                    action=action,
                    function=func.__name__,
                    status="error",
                    error=str(e),
                )

                raise

        return wrapper

    return decorator


# Module-level logger for general orchestrator operations
orchestrator_logger = get_logger(__name__, LogContext.ORCHESTRATOR)
