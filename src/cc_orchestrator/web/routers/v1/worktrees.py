"""
Worktree management API endpoints.

This module provides REST API endpoints for managing git worktrees,
including CRUD operations, status updates, and git integration.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ....database.models import WorktreeStatus
from ...crud_adapter import CRUDBase
from ...dependencies import (
    PaginationParams,
    get_crud,
    get_pagination_params,
    validate_worktree_id,
)
from ...logging_utils import handle_api_errors, track_api_performance
from ...schemas import (
    APIResponse,
    PaginatedResponse,
    WorktreeCreate,
    WorktreeResponse,
    WorktreeUpdate,
)

router = APIRouter()


@router.get("/", response_model=PaginatedResponse)
@track_api_performance()
@handle_api_errors()
async def list_worktrees(
    pagination: PaginationParams = Depends(get_pagination_params),
    status_filter: WorktreeStatus | None = Query(None, alias="status"),
    branch_name: str | None = Query(None, alias="branch"),
    instance_id: int | None = Query(None, alias="instance_id"),
    crud: CRUDBase = Depends(get_crud),
) -> dict[str, Any]:
    """
    List all worktrees with optional filtering and pagination.

    - **page**: Page number (default: 1)
    - **size**: Items per page (default: 20, max: 100)
    - **status**: Filter by worktree status
    - **branch**: Filter by branch name
    - **instance_id**: Filter by associated instance
    """
    # Build filter criteria
    filters = {}
    if status_filter:
        filters["status"] = status_filter
    if branch_name:
        filters["branch_name"] = branch_name  # type: ignore[assignment]
    if instance_id:
        filters["instance_id"] = instance_id  # type: ignore[assignment]

    # Get worktrees with pagination
    worktrees, total = await crud.list_worktrees(
        offset=pagination.offset, limit=pagination.size, filters=filters
    )

    # Convert to response schemas
    worktree_responses = [
        WorktreeResponse.model_validate(worktree) for worktree in worktrees
    ]

    return {
        "items": worktree_responses,
        "total": total,
        "page": pagination.page,
        "size": pagination.size,
        "pages": (total + pagination.size - 1) // pagination.size,
    }


@router.post("/", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
@track_api_performance()
@handle_api_errors()
async def create_worktree(
    worktree_data: WorktreeCreate,
    crud: CRUDBase = Depends(get_crud),
) -> dict[str, Any]:
    """
    Create a new git worktree.

    - **name**: Worktree name (required)
    - **path**: Worktree path (required, must be unique)
    - **branch_name**: Git branch name (required)
    - **repository_url**: Repository URL
    - **status**: Initial status (default: active)
    - **instance_id**: Associated instance ID
    """
    # Check if worktree with this path already exists
    if worktree_data.path:
        existing = await crud.get_worktree_by_path(worktree_data.path)
    else:
        existing = None
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Worktree with path '{worktree_data.path}' already exists",
        )

    # Validate instance_id if provided
    if worktree_data.instance_id:
        instance = await crud.get_instance(worktree_data.instance_id)
        if not instance:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Instance with ID {worktree_data.instance_id} not found",
            )

    # Create the worktree
    worktree = await crud.create_worktree(worktree_data.model_dump())

    return {
        "success": True,
        "message": "Worktree created successfully",
        "data": WorktreeResponse.model_validate(worktree),
    }


@router.get("/{worktree_id}", response_model=APIResponse)
@track_api_performance()
@handle_api_errors()
async def get_worktree(
    worktree_id: int = Depends(validate_worktree_id),
    crud: CRUDBase = Depends(get_crud),
) -> dict[str, Any]:
    """
    Get a specific worktree by ID.

    - **worktree_id**: The ID of the worktree to retrieve
    """
    worktree = await crud.get_worktree(worktree_id)
    if not worktree:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Worktree with ID {worktree_id} not found",
        )

    return {
        "success": True,
        "message": "Worktree retrieved successfully",
        "data": WorktreeResponse.model_validate(worktree),
    }


@router.put("/{worktree_id}", response_model=APIResponse)
@track_api_performance()
@handle_api_errors()
async def update_worktree(
    worktree_data: WorktreeUpdate,
    worktree_id: int = Depends(validate_worktree_id),
    crud: CRUDBase = Depends(get_crud),
) -> dict[str, Any]:
    """
    Update an existing worktree.

    - **worktree_id**: The ID of the worktree to update
    - Only provided fields will be updated
    """
    # Check if worktree exists
    existing = await crud.get_worktree(worktree_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Worktree with ID {worktree_id} not found",
        )

    # Validate instance_id if provided
    if worktree_data.instance_id:
        instance = await crud.get_instance(worktree_data.instance_id)
        if not instance:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Instance with ID {worktree_data.instance_id} not found",
            )

    # Update the worktree
    update_data = worktree_data.model_dump(exclude_unset=True)
    worktree = await crud.update_worktree(worktree_id, update_data)

    return {
        "success": True,
        "message": "Worktree updated successfully",
        "data": WorktreeResponse.model_validate(worktree),
    }


@router.delete("/{worktree_id}", response_model=APIResponse)
@track_api_performance()
@handle_api_errors()
async def delete_worktree(
    worktree_id: int = Depends(validate_worktree_id),
    crud: CRUDBase = Depends(get_crud),
) -> dict[str, Any]:
    """
    Delete a worktree.

    - **worktree_id**: The ID of the worktree to delete
    - This will also unassign any associated tasks
    """
    # Check if worktree exists
    existing = await crud.get_worktree(worktree_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Worktree with ID {worktree_id} not found",
        )

    # Delete the worktree
    await crud.delete_worktree(worktree_id)

    return {"success": True, "message": "Worktree deleted successfully", "data": None}


@router.post("/{worktree_id}/sync", response_model=APIResponse)
@track_api_performance()
@handle_api_errors()
async def sync_worktree(
    worktree_id: int = Depends(validate_worktree_id),
    crud: CRUDBase = Depends(get_crud),
) -> dict[str, Any]:
    """
    Sync a worktree with the remote repository.

    - **worktree_id**: The ID of the worktree to sync
    """
    # Check if worktree exists
    worktree = await crud.get_worktree(worktree_id)
    if not worktree:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Worktree with ID {worktree_id} not found",
        )

    # TODO: Integrate with actual git operations
    # For now, just update the last_sync timestamp
    from datetime import datetime

    updated_worktree = await crud.update_worktree(
        worktree_id, {"last_sync": datetime.now()}
    )

    return {
        "success": True,
        "message": "Worktree synced successfully",
        "data": WorktreeResponse.model_validate(updated_worktree),
    }


@router.get("/{worktree_id}/status", response_model=APIResponse)
@track_api_performance()
@handle_api_errors()
async def get_worktree_status(
    worktree_id: int = Depends(validate_worktree_id),
    crud: CRUDBase = Depends(get_crud),
) -> dict[str, Any]:
    """
    Get the current status of a worktree.

    - **worktree_id**: The ID of the worktree
    """
    worktree = await crud.get_worktree(worktree_id)
    if not worktree:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Worktree with ID {worktree_id} not found",
        )

    status_data = {
        "id": worktree.id,
        "name": worktree.name,
        "path": worktree.path,
        "branch": worktree.branch_name,  # Map branch_name to branch for API consistency
        "base_branch": getattr(
            worktree, "base_branch", "main"
        ),  # Add base_branch if not present
        "active": getattr(worktree, "active", True),
        "status": worktree.status,
        "current_commit": worktree.current_commit,
        "has_uncommitted_changes": worktree.has_uncommitted_changes,
        "last_sync": worktree.last_sync,
        "created_at": worktree.created_at,
        "updated_at": worktree.updated_at,
    }

    return {
        "success": True,
        "message": "Worktree status retrieved successfully",
        "data": status_data,
    }


@router.get("/{worktree_id}/tasks", response_model=PaginatedResponse)
@track_api_performance()
@handle_api_errors()
async def get_worktree_tasks(
    worktree_id: int = Depends(validate_worktree_id),
    pagination: PaginationParams = Depends(get_pagination_params),
    crud: CRUDBase = Depends(get_crud),
) -> dict[str, Any]:
    """
    Get all tasks associated with a worktree.

    - **worktree_id**: The ID of the worktree
    - **page**: Page number (default: 1)
    - **size**: Items per page (default: 20, max: 100)
    """
    # Check if worktree exists
    worktree = await crud.get_worktree(worktree_id)
    if not worktree:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Worktree with ID {worktree_id} not found",
        )

    # Get tasks for this worktree
    tasks, total = await crud.list_tasks(
        offset=pagination.offset,
        limit=pagination.size,
        filters={"worktree_id": worktree_id},
    )

    return {
        "items": [task.__dict__ for task in tasks],
        "total": total,
        "page": pagination.page,
        "size": pagination.size,
        "pages": (total + pagination.size - 1) // pagination.size,
    }
