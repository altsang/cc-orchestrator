"""
Logging utilities for web interface components.

This module provides specialized logging for:
- FastAPI request/response logging
- WebSocket connection management
- API authentication and authorization
- Real-time event streaming
"""

from collections.abc import Callable
from typing import Any

from ..utils.logging import LogContext, get_logger, handle_errors, log_performance

# Web component loggers
api_logger = get_logger(__name__ + ".api", LogContext.WEB)
websocket_logger = get_logger(__name__ + ".websocket", LogContext.WEB)
auth_logger = get_logger(__name__ + ".auth", LogContext.WEB)


def log_api_request(
    method: str,
    path: str,
    client_ip: str,
    user_agent: str | None = None,
    request_id: str | None = None,
) -> None:
    """Log incoming API requests."""
    api_logger.info(
        "API request received",
        method=method,
        path=path,
        client_ip=client_ip,
        user_agent=user_agent,
        request_id=request_id,
    )


def log_api_response(
    method: str,
    path: str,
    status_code: int,
    response_time_ms: float,
    request_id: str | None = None,
) -> None:
    """Log API responses with timing."""
    log_level = "info" if 200 <= status_code < 400 else "warning"

    getattr(api_logger, log_level)(
        "API response sent",
        method=method,
        path=path,
        status_code=status_code,
        response_time_ms=response_time_ms,
        request_id=request_id,
    )


def log_websocket_connection(
    client_ip: str,
    action: str,  # connect, disconnect
    connection_id: str,
    reason: str | None = None,
) -> None:
    """Log WebSocket connection events."""
    websocket_logger.info(
        f"WebSocket {action}",
        action=action,
        client_ip=client_ip,
        connection_id=connection_id,
        reason=reason,
    )


def log_websocket_message(
    connection_id: str,
    message_type: str,
    direction: str,  # inbound, outbound
    message_size: int,
) -> None:
    """Log WebSocket message traffic."""
    websocket_logger.debug(
        f"WebSocket message {direction}",
        connection_id=connection_id,
        message_type=message_type,
        direction=direction,
        message_size=message_size,
    )


def log_authentication_attempt(
    auth_method: str,
    client_ip: str,
    success: bool,
    user_id: str | None = None,
    reason: str | None = None,
) -> None:
    """Log authentication attempts."""
    if success:
        auth_logger.info(
            "Authentication successful",
            auth_method=auth_method,
            client_ip=client_ip,
            user_id=user_id,
        )
    else:
        auth_logger.warning(
            "Authentication failed",
            auth_method=auth_method,
            client_ip=client_ip,
            reason=reason,
        )


def log_authorization_check(
    user_id: str, resource: str, action: str, allowed: bool, reason: str | None = None
) -> None:
    """Log authorization decisions."""
    if allowed:
        auth_logger.debug(
            "Authorization granted", user_id=user_id, resource=resource, action=action
        )
    else:
        auth_logger.warning(
            "Authorization denied",
            user_id=user_id,
            resource=resource,
            action=action,
            reason=reason,
        )


def log_real_time_event(
    event_type: str,
    target_connections: int,
    payload_size: int,
    instance_id: str | None = None,
    task_id: str | None = None,
) -> None:
    """Log real-time event broadcasting."""
    logger = get_logger(__name__ + ".websocket", LogContext.WEB)

    if instance_id:
        logger.set_instance_id(instance_id)
    if task_id:
        logger.set_task_id(task_id)

    logger.debug(
        "Real-time event broadcast",
        event_type=event_type,
        target_connections=target_connections,
        payload_size=payload_size,
    )


def log_dashboard_access(
    client_ip: str, user_agent: str, session_id: str | None = None
) -> None:
    """Log dashboard access events."""
    api_logger.info(
        "Dashboard accessed",
        client_ip=client_ip,
        user_agent=user_agent,
        session_id=session_id,
    )


# Decorator functions for web operations
import asyncio
import functools
import time


def handle_api_errors(
    recovery_strategy: Callable[..., Any] | None = None,
) -> Callable[..., Any]:
    """Async-aware decorator for API error handling."""
    def decorator(func: Callable) -> Callable:
        if asyncio.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    api_logger.error(
                        f"API error in {func.__name__}: {str(e)}",
                        extra={
                            "function": func.__name__,
                            "error_type": type(e).__name__,
                            "error_message": str(e),
                        },
                        exc_info=True,
                    )
                    if recovery_strategy:
                        try:
                            if asyncio.iscoroutinefunction(recovery_strategy):
                                return await recovery_strategy(*args, **kwargs)
                            else:
                                return recovery_strategy(*args, **kwargs)
                        except Exception as recovery_error:
                            api_logger.error(
                                f"Recovery strategy failed: {str(recovery_error)}",
                                extra={
                                    "function": func.__name__,
                                    "recovery_error": str(recovery_error),
                                },
                            )
                    raise
            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    api_logger.error(
                        f"API error in {func.__name__}: {str(e)}",
                        extra={
                            "function": func.__name__,
                            "error_type": type(e).__name__,
                            "error_message": str(e),
                        },
                        exc_info=True,
                    )
                    if recovery_strategy:
                        try:
                            return recovery_strategy(*args, **kwargs)
                        except Exception as recovery_error:
                            api_logger.error(
                                f"Recovery strategy failed: {str(recovery_error)}",
                                extra={
                                    "function": func.__name__,
                                    "recovery_error": str(recovery_error),
                                },
                            )
                    raise
            return sync_wrapper
    return decorator


def track_api_performance() -> Callable[..., Any]:
    """Async-aware decorator for API performance tracking."""
    def decorator(func: Callable) -> Callable:
        if asyncio.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                start_time = time.time()
                api_logger.debug(
                    f"Performance tracking started for {func.__name__}",
                    function=func.__name__,
                )
                try:
                    result = await func(*args, **kwargs)
                    execution_time = (time.time() - start_time) * 1000  # ms
                    api_logger.info(
                        f"Performance: {func.__name__} completed",
                        function=func.__name__,
                        execution_time_ms=execution_time,
                        status="success",
                    )
                    return result
                except Exception as e:
                    execution_time = (time.time() - start_time) * 1000  # ms
                    api_logger.warning(
                        f"Performance: {func.__name__} failed",
                        function=func.__name__,
                        execution_time_ms=execution_time,
                        status="error",
                        error=str(e),
                    )
                    raise
            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                start_time = time.time()
                api_logger.debug(
                    f"Performance tracking started for {func.__name__}",
                    function=func.__name__,
                )
                try:
                    result = func(*args, **kwargs)
                    execution_time = (time.time() - start_time) * 1000  # ms
                    api_logger.info(
                        f"Performance: {func.__name__} completed",
                        function=func.__name__,
                        execution_time_ms=execution_time,
                        status="success",
                    )
                    return result
                except Exception as e:
                    execution_time = (time.time() - start_time) * 1000  # ms
                    api_logger.warning(
                        f"Performance: {func.__name__} failed",
                        function=func.__name__,
                        execution_time_ms=execution_time,
                        status="error",
                        error=str(e),
                    )
                    raise
            return sync_wrapper
    return decorator
