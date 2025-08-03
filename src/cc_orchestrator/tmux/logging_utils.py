"""Logging utilities for tmux operations."""

import logging
from typing import Any

# Create tmux logger
tmux_logger = logging.getLogger("cc_orchestrator.tmux")


def log_session_operation(operation: str, session_name: str, status: str, context: dict[str, Any] | None = None) -> None:
    """Log session operation."""
    message = f"Session {operation} {status} - {session_name}"
    if context:
        message += f" - {context}"
    
    if status == "success":
        tmux_logger.info(message)
    elif status == "error":
        tmux_logger.error(message)
    else:
        tmux_logger.info(message)


def log_session_attach(session_name: str, instance_id: str | None = None) -> None:
    """Log session attachment."""
    message = f"Session attached - {session_name}"
    if instance_id:
        message += f" (instance: {instance_id})"
    tmux_logger.info(message)


def log_session_detach(session_name: str, instance_id: str | None = None) -> None:
    """Log session detachment."""
    message = f"Session detached - {session_name}"
    if instance_id:
        message += f" (instance: {instance_id})"
    tmux_logger.info(message)


def log_session_cleanup(session_name: str, force: bool, cleanup_type: str) -> None:
    """Log session cleanup."""
    message = f"Session cleanup initiated - {session_name} (force: {force}, type: {cleanup_type})"
    tmux_logger.info(message)


def log_session_list(sessions: list[dict[str, Any]]) -> None:
    """Log session listing."""
    message = f"Sessions listed - count: {len(sessions)}"
    tmux_logger.debug(message)


def log_orphaned_sessions(orphaned: list[str]) -> None:
    """Log orphaned sessions detected."""
    if orphaned:
        message = f"Orphaned sessions detected - count: {len(orphaned)}, sessions: {orphaned}"
        tmux_logger.warning(message)
    else:
        tmux_logger.debug("No orphaned sessions found")


def log_layout_setup(session_name: str, template_name: str, windows: list[str]) -> None:
    """Log layout template setup."""
    message = f"Layout template applied - {session_name} (template: {template_name}, windows: {windows})"
    tmux_logger.info(message)