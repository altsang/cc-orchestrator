"""
FastAPI dependencies for database access and common functionality.

This module provides dependency injection functions for database
sessions, authentication, and other shared resources.
"""

from collections.abc import AsyncGenerator

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.connection import DatabaseManager
from .crud_adapter import CRUDBase
from .logging_utils import api_logger


async def get_database_manager(request: Request) -> DatabaseManager:
    """Get the database manager from application state."""
    if not hasattr(request.app.state, "db_manager"):
        api_logger.error("Database manager not found in application state")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database connection not available",
        )
    return request.app.state.db_manager


async def get_db_session(
    db_manager: DatabaseManager = Depends(get_database_manager),
) -> AsyncGenerator[AsyncSession, None]:
    """Get a database session for request handling."""
    try:
        async with db_manager.get_session() as session:
            api_logger.debug("Database session created")
            yield session
    except Exception as e:
        api_logger.error("Failed to create database session", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database session creation failed",
        )


async def get_crud(db_session: AsyncSession = Depends(get_db_session)) -> CRUDBase:
    """Get CRUD operations instance."""
    return CRUDBase(db_session)


def get_request_id(request: Request) -> str:
    """Get the request ID from request state."""
    return getattr(request.state, "request_id", "unknown")


def get_client_ip(request: Request) -> str:
    """Extract client IP address from request."""
    # Check for forwarded headers (load balancer/proxy)
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()

    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip

    # Fall back to direct client IP
    return request.client.host if request.client else "unknown"


# Pagination dependencies
class PaginationParams:
    """Pagination parameters for list endpoints."""

    def __init__(self, page: int = 1, size: int = 20, max_size: int = 100):
        if page < 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Page number must be >= 1",
            )

        if size < 1 or size > max_size:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Page size must be between 1 and {max_size}",
            )

        self.page = page
        self.size = size
        self.offset = (page - 1) * size


def get_pagination_params(page: int = 1, size: int = 20) -> PaginationParams:
    """Get pagination parameters with validation."""
    return PaginationParams(page=page, size=size)


# Authentication dependencies (placeholder for future implementation)
class CurrentUser:
    """Current authenticated user information."""

    def __init__(self, user_id: str, permissions: list[str] | None = None):
        self.user_id = user_id
        self.permissions = permissions or []


async def get_current_user(request: Request) -> CurrentUser:
    """
    Get current authenticated user.

    This is a placeholder implementation that returns a default user.
    In a real implementation, this would validate JWT tokens, API keys,
    or other authentication mechanisms.
    """
    # TODO: Implement actual authentication
    # For now, return a default user for development
    return CurrentUser(user_id="default", permissions=["read", "write"])


async def require_permission(
    permission: str, current_user: CurrentUser = Depends(get_current_user)
) -> CurrentUser:
    """Require a specific permission for the current user."""
    if permission not in current_user.permissions:
        api_logger.warning(
            "Permission denied",
            user_id=current_user.user_id,
            required_permission=permission,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permission '{permission}' required",
        )
    return current_user


# Helper functions for common validation
def validate_instance_id(instance_id: int) -> int:
    """Validate instance ID parameter."""
    if instance_id < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Instance ID must be a positive integer",
        )
    return instance_id


def validate_task_id(task_id: int) -> int:
    """Validate task ID parameter."""
    if task_id < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Task ID must be a positive integer",
        )
    return task_id


def validate_worktree_id(worktree_id: int) -> int:
    """Validate worktree ID parameter."""
    if worktree_id < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Worktree ID must be a positive integer",
        )
    return worktree_id


def validate_config_id(config_id: int) -> int:
    """Validate configuration ID parameter."""
    if config_id < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Configuration ID must be a positive integer",
        )
    return config_id
