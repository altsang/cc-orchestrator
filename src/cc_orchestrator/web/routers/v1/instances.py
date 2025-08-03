"""
Instance management API endpoints.

This module provides REST API endpoints for managing Claude Code instances,
including CRUD operations, status updates, and health monitoring.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ....database.models import InstanceStatus
from ...crud_adapter import CRUDBase
from ...dependencies import (
    PaginationParams,
    get_crud,
    get_pagination_params,
    validate_instance_id,
)
from ...logging_utils import handle_api_errors, track_api_performance
from ...schemas import (
    APIResponse,
    InstanceCreate,
    InstanceResponse,
    InstanceUpdate,
    PaginatedResponse,
)

router = APIRouter()


@router.get("/", response_model=PaginatedResponse)
@track_api_performance()
@handle_api_errors()
async def list_instances(
    pagination: PaginationParams = Depends(get_pagination_params),
    status_filter: InstanceStatus | None = Query(None, alias="status"),
    branch_name: str | None = Query(None, alias="branch"),
    crud: CRUDBase = Depends(get_crud),
) -> dict[str, Any]:
    """
    List all instances with optional filtering and pagination.

    - **page**: Page number (default: 1)
    - **size**: Items per page (default: 20, max: 100)
    - **status**: Filter by instance status
    - **branch**: Filter by branch name
    """
    # Build filter criteria
    filters = {}
    if status_filter:
        filters["status"] = status_filter
    if branch_name:
        filters["branch_name"] = branch_name

    # Get instances with pagination
    instances, total = await crud.list_instances(
        offset=pagination.offset, limit=pagination.size, filters=filters
    )

    # Convert to response schemas
    instance_responses = [
        InstanceResponse.model_validate(instance) for instance in instances
    ]

    return {
        "items": instance_responses,
        "total": total,
        "page": pagination.page,
        "size": pagination.size,
        "pages": (total + pagination.size - 1) // pagination.size,
    }


@router.post("/", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
@track_api_performance()
@handle_api_errors()
async def create_instance(
    instance_data: InstanceCreate,
    crud: CRUDBase = Depends(get_crud),
) -> dict[str, Any]:
    """
    Create a new Claude Code instance.

    - **issue_id**: Unique GitHub issue ID
    - **status**: Initial instance status (default: initializing)
    - **workspace_path**: Path to the workspace directory
    - **branch_name**: Git branch name
    - **tmux_session**: Tmux session name
    """
    # Check if instance with this issue_id already exists
    existing = await crud.get_instance_by_issue_id(instance_data.issue_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Instance with issue_id '{instance_data.issue_id}' already exists",
        )

    # Create the instance
    instance = await crud.create_instance(instance_data.model_dump())

    return {
        "success": True,
        "message": "Instance created successfully",
        "data": InstanceResponse.model_validate(instance),
    }


@router.get("/{instance_id}", response_model=APIResponse)
@track_api_performance()
@handle_api_errors()
async def get_instance(
    instance_id: int = Depends(validate_instance_id),
    crud: CRUDBase = Depends(get_crud),
) -> dict[str, Any]:
    """
    Get a specific instance by ID.

    - **instance_id**: The ID of the instance to retrieve
    """
    instance = await crud.get_instance(instance_id)
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Instance with ID {instance_id} not found",
        )

    return {
        "success": True,
        "message": "Instance retrieved successfully",
        "data": InstanceResponse.model_validate(instance),
    }


@router.put("/{instance_id}", response_model=APIResponse)
@track_api_performance()
@handle_api_errors()
async def update_instance(
    instance_data: InstanceUpdate,
    instance_id: int = Depends(validate_instance_id),
    crud: CRUDBase = Depends(get_crud),
) -> dict[str, Any]:
    """
    Update an existing instance.

    - **instance_id**: The ID of the instance to update
    - Only provided fields will be updated
    """
    # Check if instance exists
    existing = await crud.get_instance(instance_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Instance with ID {instance_id} not found",
        )

    # Update the instance
    update_data = instance_data.model_dump(exclude_unset=True)
    instance = await crud.update_instance(instance_id, update_data)

    return {
        "success": True,
        "message": "Instance updated successfully",
        "data": InstanceResponse.model_validate(instance),
    }


@router.delete("/{instance_id}", response_model=APIResponse)
@track_api_performance()
@handle_api_errors()
async def delete_instance(
    instance_id: int = Depends(validate_instance_id),
    crud: CRUDBase = Depends(get_crud),
) -> dict[str, Any]:
    """
    Delete an instance.

    - **instance_id**: The ID of the instance to delete
    - This will also delete all associated tasks and configurations
    """
    # Check if instance exists
    existing = await crud.get_instance(instance_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Instance with ID {instance_id} not found",
        )

    # Delete the instance
    await crud.delete_instance(instance_id)

    return {"success": True, "message": "Instance deleted successfully", "data": None}


@router.post("/{instance_id}/start", response_model=APIResponse)
@track_api_performance()
@handle_api_errors()
async def start_instance(
    instance_id: int = Depends(validate_instance_id),
    crud: CRUDBase = Depends(get_crud),
) -> dict[str, Any]:
    """
    Start a Claude Code instance.

    - **instance_id**: The ID of the instance to start
    """
    # Check if instance exists
    instance = await crud.get_instance(instance_id)
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Instance with ID {instance_id} not found",
        )

    # Check if instance is already running
    if instance.status == InstanceStatus.RUNNING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Instance is already running",
        )

    # Update status to running
    # TODO: Integrate with actual instance management system
    updated_instance = await crud.update_instance(
        instance_id, {"status": InstanceStatus.RUNNING}
    )

    return {
        "success": True,
        "message": "Instance started successfully",
        "data": InstanceResponse.model_validate(updated_instance),
    }


@router.post("/{instance_id}/stop", response_model=APIResponse)
@track_api_performance()
@handle_api_errors()
async def stop_instance(
    instance_id: int = Depends(validate_instance_id),
    crud: CRUDBase = Depends(get_crud),
) -> dict[str, Any]:
    """
    Stop a Claude Code instance.

    - **instance_id**: The ID of the instance to stop
    """
    # Check if instance exists
    instance = await crud.get_instance(instance_id)
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Instance with ID {instance_id} not found",
        )

    # Check if instance is already stopped
    if instance.status == InstanceStatus.STOPPED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Instance is already stopped",
        )

    # Update status to stopped
    # TODO: Integrate with actual instance management system
    updated_instance = await crud.update_instance(
        instance_id, {"status": InstanceStatus.STOPPED}
    )

    return {
        "success": True,
        "message": "Instance stopped successfully",
        "data": InstanceResponse.model_validate(updated_instance),
    }


@router.get("/{instance_id}/status", response_model=APIResponse)
@track_api_performance()
@handle_api_errors()
async def get_instance_status(
    instance_id: int = Depends(validate_instance_id),
    crud: CRUDBase = Depends(get_crud),
) -> dict[str, Any]:
    """
    Get the current status of an instance.

    - **instance_id**: The ID of the instance
    """
    instance = await crud.get_instance(instance_id)
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Instance with ID {instance_id} not found",
        )

    status_data = {
        "id": instance.id,
        "issue_id": instance.issue_id,
        "status": instance.status,
        "health_status": instance.health_status,
        "last_health_check": instance.last_health_check,
        "last_activity": instance.last_activity,
        "process_id": instance.process_id,
        "tmux_session": instance.tmux_session,
    }

    return {
        "success": True,
        "message": "Instance status retrieved successfully",
        "data": status_data,
    }


@router.get("/{instance_id}/tasks", response_model=PaginatedResponse)
@track_api_performance()
@handle_api_errors()
async def get_instance_tasks(
    instance_id: int = Depends(validate_instance_id),
    pagination: PaginationParams = Depends(get_pagination_params),
    crud: CRUDBase = Depends(get_crud),
) -> dict[str, Any]:
    """
    Get all tasks assigned to an instance.

    - **instance_id**: The ID of the instance
    - **page**: Page number (default: 1)
    - **size**: Items per page (default: 20, max: 100)
    """
    # Check if instance exists
    instance = await crud.get_instance(instance_id)
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Instance with ID {instance_id} not found",
        )

    # Get tasks for this instance
    tasks, total = await crud.list_tasks(
        offset=pagination.offset,
        limit=pagination.size,
        filters={"instance_id": instance_id},
    )

    return {
        "items": [task.__dict__ for task in tasks],
        "total": total,
        "page": pagination.page,
        "size": pagination.size,
        "pages": (total + pagination.size - 1) // pagination.size,
    }
