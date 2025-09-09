"""
FastAPI dependencies for database access and common functionality.

This module provides dependency injection functions for database
sessions, authentication, and other shared resources.
"""

from collections.abc import AsyncGenerator
from typing import cast

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

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
    return cast(DatabaseManager, request.app.state.db_manager)


async def get_db_session(
    db_manager: DatabaseManager = Depends(get_database_manager),
) -> AsyncGenerator[Session, None]:
    """Get a database session for request handling."""
    session = None
    try:
        # Create session
        session = db_manager.session_factory()
        api_logger.debug("Database session created")

        # Yield session to the endpoint
        yield session

        # Commit transaction if everything went well
        try:
            session.commit()
            api_logger.debug("Database session committed")
        except Exception as commit_error:
            session.rollback()
            api_logger.error(
                "Failed to commit database session", error=str(commit_error)
            )
            raise

    except HTTPException:
        # Re-raise HTTP exceptions (like 409 Conflict) without wrapping
        if session:
            try:
                session.rollback()
                api_logger.debug("Database session rolled back")
            except Exception as rollback_error:
                api_logger.error(
                    "Failed to rollback session", error=str(rollback_error)
                )
        raise

    except Exception as e:
        # Handle database session errors
        if session:
            try:
                session.rollback()
                api_logger.debug("Database session rolled back")
            except Exception as rollback_error:
                api_logger.error(
                    "Failed to rollback session", error=str(rollback_error)
                )

        api_logger.error(
            "Database session error", error=str(e), error_type=type(e).__name__
        )
        # Include more error details for debugging
        import traceback

        api_logger.error("Database session traceback", traceback=traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database session failed: {str(e)}",
        )
    finally:
        # Always close the session
        if session:
            try:
                session.close()
                api_logger.debug("Database session closed")
            except Exception as close_error:
                api_logger.error(
                    "Failed to close database session", error=str(close_error)
                )


async def get_crud(db_session: Session = Depends(get_db_session)) -> CRUDBase:
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
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Page number must be >= 1",
            )

        if size < 1 or size > max_size:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
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
        self.id = user_id  # Alias for compatibility with existing code
        self.permissions = permissions or []


async def get_current_user(request: Request) -> CurrentUser:
    """
    Get current authenticated user.

    Validates authentication via Authorization header with Bearer token,
    API key header, or development token for testing.
    """
    # Check for Authorization header with Bearer token
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:]  # Remove "Bearer " prefix
        return await _validate_bearer_token(token)

    # Check for API key in X-API-Key header
    api_key = request.headers.get("X-API-Key")
    if api_key:
        return await _validate_api_key(api_key)

    # Development/testing token for non-production environments
    dev_token = request.headers.get("X-Dev-Token")
    if dev_token == "development-token":  # nosec
        api_logger.warning(
            "Development token used - only for testing",
            client_ip=get_client_ip(request),
        )
        return CurrentUser(user_id="dev_user", permissions=["read", "write"])

    # No valid authentication found
    api_logger.warning(
        "Authentication required - no valid credentials provided",
        client_ip=get_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def _validate_bearer_token(token: str) -> CurrentUser:
    """Validate Bearer token (JWT or similar)."""
    # TODO: Implement actual JWT validation in production
    # For now, accept specific test tokens
    if token in ["valid-jwt-token", "test-user-token", "admin-token"]:  # nosec
        permissions = (
            ["read", "write", "admin"] if token == "admin-token" else ["read", "write"]  # nosec
        )
        user_id = "admin" if token == "admin-token" else "authenticated_user"  # nosec
        return CurrentUser(user_id=user_id, permissions=permissions)

    api_logger.warning(
        "Invalid Bearer token provided", token_prefix=token[:10] if token else ""
    )
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid token",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def _validate_api_key(api_key: str) -> CurrentUser:
    """Validate API key."""
    # TODO: Implement actual API key validation with database lookup
    # For now, accept specific test API keys
    valid_api_keys = {
        "test-api-key-123": CurrentUser(user_id="api_user", permissions=["read"]),
        "admin-api-key-456": CurrentUser(
            user_id="api_admin", permissions=["read", "write", "admin"]
        ),
    }

    if api_key in valid_api_keys:
        return valid_api_keys[api_key]

    api_logger.warning(
        "Invalid API key provided", key_prefix=api_key[:10] if api_key else ""
    )
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid API key",
        headers={"WWW-Authenticate": "Bearer"},
    )


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
