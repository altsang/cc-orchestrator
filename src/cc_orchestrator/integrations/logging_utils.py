"""
Logging utilities for external integrations.

This module provides specialized logging for:
- GitHub API operations
- Jira API operations
- Webhook handling
- External service rate limiting
"""

from collections.abc import Callable
from typing import Any

from ..utils.logging import (
    LogContext,
    audit_log,
    get_logger,
    handle_errors,
)

# Integration component loggers
github_logger = get_logger(__name__ + ".github", LogContext.INTEGRATION)
jira_logger = get_logger(__name__ + ".jira", LogContext.INTEGRATION)
webhook_logger = get_logger(__name__ + ".webhook", LogContext.INTEGRATION)


def log_github_api_call(
    operation: str,
    endpoint: str,
    method: str,
    status_code: int,
    response_time_ms: float,
    rate_limit_remaining: int | None = None,
) -> None:
    """Log GitHub API operations."""
    log_level = "info" if 200 <= status_code < 400 else "warning"

    getattr(github_logger, log_level)(
        f"GitHub API {operation}",
        operation=operation,
        endpoint=endpoint,
        method=method,
        status_code=status_code,
        response_time_ms=response_time_ms,
        rate_limit_remaining=rate_limit_remaining,
    )


def log_github_sync(
    repository: str,
    sync_type: str,  # issues, pull_requests, etc.
    items_processed: int,
    items_created: int,
    items_updated: int,
    errors: int = 0,
) -> None:
    """Log GitHub synchronization operations."""
    github_logger.info(
        f"GitHub {sync_type} sync completed",
        repository=repository,
        sync_type=sync_type,
        items_processed=items_processed,
        items_created=items_created,
        items_updated=items_updated,
        errors=errors,
    )


def log_jira_api_call(
    operation: str,
    endpoint: str,
    method: str,
    status_code: int,
    response_time_ms: float,
    project_key: str | None = None,
) -> None:
    """Log Jira API operations."""
    log_level = "info" if 200 <= status_code < 400 else "warning"

    getattr(jira_logger, log_level)(
        f"Jira API {operation}",
        operation=operation,
        endpoint=endpoint,
        method=method,
        status_code=status_code,
        response_time_ms=response_time_ms,
        project_key=project_key,
    )


def log_jira_sync(
    project_key: str,
    sync_type: str,  # issues, sprints, etc.
    items_processed: int,
    items_created: int,
    items_updated: int,
    errors: int = 0,
) -> None:
    """Log Jira synchronization operations."""
    jira_logger.info(
        f"Jira {sync_type} sync completed",
        project_key=project_key,
        sync_type=sync_type,
        items_processed=items_processed,
        items_created=items_created,
        items_updated=items_updated,
        errors=errors,
    )


def log_webhook_received(
    source: str,  # github, jira, etc.
    event_type: str,
    payload_size: int,
    signature_valid: bool,
    processing_time_ms: float,
) -> None:
    """Log incoming webhook events."""
    webhook_logger.info(
        "Webhook received",
        source=source,
        event_type=event_type,
        payload_size=payload_size,
        signature_valid=signature_valid,
        processing_time_ms=processing_time_ms,
    )


def log_webhook_processing(
    source: str,
    event_type: str,
    tasks_created: int,
    tasks_updated: int,
    errors: list[str] | None = None,
) -> None:
    """Log webhook processing results."""
    webhook_logger.info(
        "Webhook processing completed",
        source=source,
        event_type=event_type,
        tasks_created=tasks_created,
        tasks_updated=tasks_updated,
        errors=errors or [],
    )


def log_rate_limit_warning(
    service: str, remaining_requests: int, reset_time: str, operation: str
) -> None:
    """Log rate limit warnings."""
    github_logger.warning(
        f"{service} rate limit warning",
        service=service,
        remaining_requests=remaining_requests,
        reset_time=reset_time,
        operation=operation,
    )


def log_service_status_change(
    service: str, old_status: str, new_status: str, reason: str | None = None
) -> None:
    """Log external service status changes."""
    logger = github_logger if service == "github" else jira_logger

    logger.info(
        f"{service} status changed",
        service=service,
        old_status=old_status,
        new_status=new_status,
        reason=reason,
    )


def log_integration_configuration(
    service: str, enabled: bool, configuration: dict[str, Any]
) -> None:
    """Log integration configuration changes."""
    logger = github_logger if service == "github" else jira_logger

    # Remove sensitive information
    safe_config = {
        k: v
        for k, v in configuration.items()
        if k not in ["token", "secret", "password"]
    }

    logger.info(
        f"{service} integration configured",
        service=service,
        enabled=enabled,
        configuration=safe_config,
    )


def log_task_sync_status(
    task_id: str,
    external_id: str,
    service: str,
    sync_direction: str,  # to_external, from_external
    status: str,  # success, error, skipped
    details: dict[str, Any] | None = None,
) -> None:
    """Log task synchronization with external services."""
    logger = get_logger(__name__ + f".{service}", LogContext.INTEGRATION)
    logger.set_task_id(task_id)

    logger.info(
        f"Task sync {sync_direction}",
        external_id=external_id,
        service=service,
        sync_direction=sync_direction,
        status=status,
        details=details or {},
    )


# Decorator functions for integration operations
def handle_integration_errors(
    service: str, recovery_strategy: Callable[..., Any] | None = None
) -> Callable[..., Any]:
    """Decorator for integration error handling."""
    return handle_errors(
        recovery_strategy=recovery_strategy,
        log_context=LogContext.INTEGRATION,
        reraise=True,
    )


def log_integration_operation(service: str, operation_name: str) -> Callable[..., Any]:
    """Decorator for integration operations with automatic logging."""
    return audit_log(f"{service}_{operation_name}", LogContext.INTEGRATION)
