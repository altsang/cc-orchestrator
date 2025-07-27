"""
Logging utilities for tmux session management.

This module provides specialized logging for tmux operations including:
- Session creation and management
- Window and pane operations
- Layout management
- Session cleanup
"""

from typing import Any

from ..utils.logging import LogContext, audit_log, get_logger, handle_errors

# Tmux component logger
tmux_logger = get_logger(__name__, LogContext.TMUX)


def log_session_operation(
    operation: str,
    session_name: str,
    status: str = "success",
    details: dict[str, Any] | None = None,
) -> None:
    """Log tmux session operations."""
    if status == "success":
        tmux_logger.info(
            f"Tmux session {operation} completed",
            operation=operation,
            session_name=session_name,
            details=details or {},
        )
    elif status == "error":
        tmux_logger.error(
            f"Tmux session {operation} failed",
            operation=operation,
            session_name=session_name,
            details=details or {},
        )
    else:
        tmux_logger.info(
            f"Tmux session {operation} in progress",
            operation=operation,
            session_name=session_name,
            status=status,
            details=details or {},
        )


def log_session_list(sessions: list[dict[str, Any]]) -> None:
    """Log current tmux sessions."""
    tmux_logger.debug(
        "Tmux sessions listed",
        session_count=len(sessions),
        sessions=[s.get("name", "unknown") for s in sessions],
    )


def log_session_attach(session_name: str, instance_id: str | None = None) -> None:
    """Log session attachment."""
    logger = get_logger(__name__, LogContext.TMUX)
    if instance_id:
        logger.set_instance_id(instance_id)

    logger.info("Attached to tmux session", session_name=session_name)


def log_session_detach(session_name: str, instance_id: str | None = None) -> None:
    """Log session detachment."""
    logger = get_logger(__name__, LogContext.TMUX)
    if instance_id:
        logger.set_instance_id(instance_id)

    logger.info("Detached from tmux session", session_name=session_name)


def log_layout_setup(session_name: str, layout_name: str, windows: list[str]) -> None:
    """Log tmux layout configuration."""
    tmux_logger.info(
        "Tmux layout configured",
        session_name=session_name,
        layout_name=layout_name,
        window_count=len(windows),
        windows=windows,
    )


def log_session_cleanup(
    session_name: str, force: bool = False, reason: str = "normal"
) -> None:
    """Log session cleanup operations."""
    tmux_logger.info(
        "Tmux session cleanup initiated",
        session_name=session_name,
        force=force,
        reason=reason,
    )


def log_orphaned_sessions(orphaned: list[str]) -> None:
    """Log discovery of orphaned tmux sessions."""
    if orphaned:
        tmux_logger.warning(
            "Orphaned tmux sessions detected",
            session_count=len(orphaned),
            sessions=orphaned,
        )
    else:
        tmux_logger.debug("No orphaned tmux sessions found")


# Decorator functions for tmux operations
def handle_tmux_errors(recovery_strategy=None):
    """Decorator for tmux error handling."""
    return handle_errors(
        recovery_strategy=recovery_strategy, log_context=LogContext.TMUX, reraise=True
    )


def log_tmux_operation(operation_name: str):
    """Decorator for tmux operations with automatic logging."""
    return audit_log(f"tmux_{operation_name}", LogContext.TMUX)
