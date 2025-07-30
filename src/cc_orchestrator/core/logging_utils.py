"""
Logging utilities for core orchestrator components.

This module provides specialized logging functions for:
- Orchestrator operations
- Instance management
- Task coordination
- Database operations
"""

from collections.abc import Callable
from typing import Any

from ..utils.logging import (
    LogContext,
    audit_log,
    get_logger,
    handle_errors,
    log_performance,
)

# Core component loggers
orchestrator_logger = get_logger(__name__ + ".orchestrator", LogContext.ORCHESTRATOR)
instance_logger = get_logger(__name__ + ".instance", LogContext.INSTANCE)
task_logger = get_logger(__name__ + ".task", LogContext.TASK)
database_logger = get_logger(__name__ + ".database", LogContext.DATABASE)


def log_orchestrator_start(config: dict[str, Any]) -> None:
    """Log orchestrator startup with configuration."""
    orchestrator_logger.info(
        "CC-Orchestrator starting up",
        max_instances=config.get("max_instances", "unknown"),
        tmux_enabled=config.get("tmux_enabled", False),
        web_enabled=config.get("web_enabled", False),
        log_level=config.get("log_level", "INFO"),
    )


def log_orchestrator_shutdown(graceful: bool = True) -> None:
    """Log orchestrator shutdown."""
    orchestrator_logger.info("CC-Orchestrator shutting down", graceful=graceful)


def log_instance_lifecycle(
    instance_id: str,
    action: str,
    status: str = "success",
    details: dict[str, Any] | None = None,
) -> None:
    """Log instance lifecycle events."""
    logger = get_logger(__name__ + ".instance", LogContext.INSTANCE)
    logger.set_instance_id(instance_id)

    if status == "success":
        logger.info(
            f"Instance {action} completed", action=action, details=details or {}
        )
    elif status == "error":
        logger.error(f"Instance {action} failed", action=action, details=details or {})
    else:
        logger.info(
            f"Instance {action} in progress",
            action=action,
            status=status,
            details=details or {},
        )


def log_task_assignment(
    task_id: str, instance_id: str, task_details: dict[str, Any]
) -> None:
    """Log task assignment to instance."""
    logger = get_logger(__name__ + ".task", LogContext.TASK)
    logger.set_task_id(task_id)
    logger.set_instance_id(instance_id)

    logger.info(
        "Task assigned to instance",
        task_title=task_details.get("title", "Unknown"),
        task_priority=task_details.get("priority", "medium"),
        task_source=task_details.get("source", "manual"),
    )


def log_task_status_change(
    task_id: str, old_status: str, new_status: str, instance_id: str | None = None
) -> None:
    """Log task status changes."""
    logger = get_logger(__name__ + ".task", LogContext.TASK)
    logger.set_task_id(task_id)

    if instance_id:
        logger.set_instance_id(instance_id)

    logger.info("Task status changed", old_status=old_status, new_status=new_status)


def log_database_operation(
    operation: str,
    table: str,
    record_count: int | None = None,
    execution_time: float | None = None,
) -> None:
    """Log database operations with performance metrics."""
    database_logger.info(
        f"Database {operation} on {table}",
        operation=operation,
        table=table,
        record_count=record_count,
        execution_time=execution_time,
    )


def log_resource_usage(
    instance_id: str, cpu_percent: float, memory_mb: float, disk_usage_mb: float
) -> None:
    """Log resource usage metrics for an instance."""
    logger = get_logger(__name__ + ".instance", LogContext.INSTANCE)
    logger.set_instance_id(instance_id)

    logger.debug(
        "Resource usage update",
        cpu_percent=cpu_percent,
        memory_mb=memory_mb,
        disk_usage_mb=disk_usage_mb,
    )


# Decorator functions for common operations
def log_instance_operation(operation_name: str) -> Callable[..., Any]:
    """Decorator for instance operations with automatic logging."""
    return audit_log(f"instance_{operation_name}", LogContext.INSTANCE)


def log_task_operation(operation_name: str) -> Callable[..., Any]:
    """Decorator for task operations with automatic logging."""
    return audit_log(f"task_{operation_name}", LogContext.TASK)


def handle_instance_errors(
    recovery_strategy: Callable[..., Any] | None = None,
) -> Callable[..., Any]:
    """Decorator for instance error handling."""
    return handle_errors(
        recovery_strategy=recovery_strategy,
        log_context=LogContext.INSTANCE,
        reraise=True,
    )


def handle_task_errors(
    recovery_strategy: Callable[..., Any] | None = None,
) -> Callable[..., Any]:
    """Decorator for task error handling."""
    return handle_errors(
        recovery_strategy=recovery_strategy, log_context=LogContext.TASK, reraise=True
    )


def handle_database_errors(
    recovery_strategy: Callable[..., Any] | None = None,
) -> Callable[..., Any]:
    """Decorator for database error handling."""
    return handle_errors(
        recovery_strategy=recovery_strategy,
        log_context=LogContext.DATABASE,
        reraise=True,
    )


def track_performance(component_name: str) -> Callable[..., Any]:
    """Decorator for performance tracking of core operations."""
    return log_performance(LogContext.ORCHESTRATOR)
