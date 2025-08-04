"""
Task management API endpoints.

This module provides REST API endpoints for managing tasks,
including CRUD operations, status updates, and assignment to instances.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from ....database.models import TaskPriority, TaskStatus
from ...crud_adapter import CRUDBase
from ...dependencies import (
    PaginationParams,
    get_crud,
    get_pagination_params,
    validate_task_id,
)
from ...logging_utils import handle_api_errors, track_api_performance
from ...schemas import (
    APIResponse,
    PaginatedResponse,
    TaskCreate,
    TaskResponse,
    TaskUpdate,
)

router = APIRouter()


@router.get("/", response_model=PaginatedResponse)
@track_api_performance()
@handle_api_errors()
async def list_tasks(
    pagination: PaginationParams = Depends(get_pagination_params),
    status_filter: TaskStatus | None = Query(None, alias="status"),
    priority_filter: TaskPriority | None = Query(None, alias="priority"),
    instance_id: int | None = Query(None, alias="instance_id"),
    worktree_id: int | None = Query(None, alias="worktree_id"),
    crud: CRUDBase = Depends(get_crud),
) -> dict[str, Any]:
    """
    List all tasks with optional filtering and pagination.

    - **page**: Page number (default: 1)
    - **size**: Items per page (default: 20, max: 100)
    - **status**: Filter by task status
    - **priority**: Filter by task priority
    - **instance_id**: Filter by assigned instance
    - **worktree_id**: Filter by associated worktree
    """
    # Build filter criteria
    filters = {}
    if status_filter:
        filters["status"] = status_filter
    if priority_filter:
        filters["priority"] = priority_filter  # type: ignore[assignment]
    if instance_id:
        filters["instance_id"] = instance_id  # type: ignore[assignment]
    if worktree_id:
        filters["worktree_id"] = worktree_id  # type: ignore[assignment]

    # Get tasks with pagination
    tasks, total = await crud.list_tasks(
        offset=pagination.offset, limit=pagination.size, filters=filters
    )

    # Convert to response schemas
    task_responses = [TaskResponse.model_validate(task) for task in tasks]

    return {
        "items": task_responses,
        "total": total,
        "page": pagination.page,
        "size": pagination.size,
        "pages": (total + pagination.size - 1) // pagination.size,
    }


@router.post("/", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
@track_api_performance()
@handle_api_errors()
async def create_task(
    task_data: TaskCreate,
    crud: CRUDBase = Depends(get_crud),
) -> dict[str, Any]:
    """
    Create a new task.

    - **title**: Task title (required)
    - **description**: Task description
    - **status**: Initial task status (default: pending)
    - **priority**: Task priority (default: medium)
    - **instance_id**: Assigned instance ID
    - **worktree_id**: Associated worktree ID
    - **due_date**: Task due date
    - **estimated_duration**: Estimated duration in minutes
    - **requirements**: Task requirements as JSON
    """
    # Validate instance_id if provided
    if task_data.instance_id:
        instance = await crud.get_instance(task_data.instance_id)
        if not instance:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Instance with ID {task_data.instance_id} not found",
            )

    # Validate worktree_id if provided
    if task_data.worktree_id:
        worktree = await crud.get_worktree(task_data.worktree_id)
        if not worktree:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Worktree with ID {task_data.worktree_id} not found",
            )

    # Create the task
    task = await crud.create_task(task_data.model_dump())

    return {
        "success": True,
        "message": "Task created successfully",
        "data": TaskResponse.model_validate(task),
    }


@router.get("/{task_id}", response_model=APIResponse)
@track_api_performance()
@handle_api_errors()
async def get_task(
    task_id: int = Depends(validate_task_id),
    crud: CRUDBase = Depends(get_crud),
) -> dict[str, Any]:
    """
    Get a specific task by ID.

    - **task_id**: The ID of the task to retrieve
    """
    task = await crud.get_task(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with ID {task_id} not found",
        )

    return {
        "success": True,
        "message": "Task retrieved successfully",
        "data": TaskResponse.model_validate(task),
    }


@router.put("/{task_id}", response_model=APIResponse)
@track_api_performance()
@handle_api_errors()
async def update_task(
    task_data: TaskUpdate,
    task_id: int = Depends(validate_task_id),
    crud: CRUDBase = Depends(get_crud),
) -> dict[str, Any]:
    """
    Update an existing task.

    - **task_id**: The ID of the task to update
    - Only provided fields will be updated
    """
    # Check if task exists
    existing = await crud.get_task(task_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with ID {task_id} not found",
        )

    # Validate instance_id if provided
    if task_data.instance_id:
        instance = await crud.get_instance(task_data.instance_id)
        if not instance:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Instance with ID {task_data.instance_id} not found",
            )

    # Validate worktree_id if provided
    if task_data.worktree_id:
        worktree = await crud.get_worktree(task_data.worktree_id)
        if not worktree:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Worktree with ID {task_data.worktree_id} not found",
            )

    # Update the task
    update_data = task_data.model_dump(exclude_unset=True)
    task = await crud.update_task(task_id, update_data)

    return {
        "success": True,
        "message": "Task updated successfully",
        "data": TaskResponse.model_validate(task),
    }


@router.delete("/{task_id}", response_model=APIResponse)
@track_api_performance()
@handle_api_errors()
async def delete_task(
    task_id: int = Depends(validate_task_id),
    crud: CRUDBase = Depends(get_crud),
) -> dict[str, Any]:
    """
    Delete a task.

    - **task_id**: The ID of the task to delete
    """
    # Check if task exists
    existing = await crud.get_task(task_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with ID {task_id} not found",
        )

    # Delete the task
    await crud.delete_task(task_id)

    return {"success": True, "message": "Task deleted successfully", "data": None}


@router.post("/{task_id}/start", response_model=APIResponse)
@track_api_performance()
@handle_api_errors()
async def start_task(
    task_id: int = Depends(validate_task_id),
    crud: CRUDBase = Depends(get_crud),
) -> dict[str, Any]:
    """
    Start working on a task.

    - **task_id**: The ID of the task to start
    """
    # Check if task exists
    task = await crud.get_task(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with ID {task_id} not found",
        )

    # Check if task can be started
    if task.status == TaskStatus.IN_PROGRESS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Task is already in progress",
        )

    if task.status in [TaskStatus.COMPLETED, TaskStatus.CANCELLED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot start a {task.status.value} task",
        )

    # Update task status to in_progress
    from datetime import datetime

    updated_task = await crud.update_task(
        task_id, {"status": TaskStatus.IN_PROGRESS, "started_at": datetime.now()}
    )

    return {
        "success": True,
        "message": "Task started successfully",
        "data": TaskResponse.model_validate(updated_task),
    }


@router.post("/{task_id}/complete", response_model=APIResponse)
@track_api_performance()
@handle_api_errors()
async def complete_task(
    task_id: int = Depends(validate_task_id),
    results: dict[str, Any] | None = None,
    crud: CRUDBase = Depends(get_crud),
) -> dict[str, Any]:
    """
    Mark a task as completed.

    - **task_id**: The ID of the task to complete
    - **results**: Task results as JSON (optional)
    """
    # Check if task exists
    task = await crud.get_task(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with ID {task_id} not found",
        )

    # Check if task can be completed
    if task.status == TaskStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Task is already completed"
        )

    if task.status == TaskStatus.CANCELLED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot complete a cancelled task",
        )

    # Calculate actual duration if task was started
    actual_duration = None
    if task.started_at:
        from datetime import datetime

        duration_delta = datetime.now() - task.started_at
        actual_duration = int(duration_delta.total_seconds() / 60)  # Convert to minutes

    # Update task status to completed
    update_data = {
        "status": TaskStatus.COMPLETED,
        "completed_at": datetime.now(),
    }

    if actual_duration:
        update_data["actual_duration"] = actual_duration

    if results:
        update_data["results"] = results

    updated_task = await crud.update_task(task_id, update_data)

    return {
        "success": True,
        "message": "Task completed successfully",
        "data": TaskResponse.model_validate(updated_task),
    }


@router.post("/{task_id}/cancel", response_model=APIResponse)
@track_api_performance()
@handle_api_errors()
async def cancel_task(
    task_id: int = Depends(validate_task_id),
    crud: CRUDBase = Depends(get_crud),
) -> dict[str, Any]:
    """
    Cancel a task.

    - **task_id**: The ID of the task to cancel
    """
    # Check if task exists
    task = await crud.get_task(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with ID {task_id} not found",
        )

    # Check if task can be cancelled
    if task.status in [TaskStatus.COMPLETED, TaskStatus.CANCELLED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel a {task.status.value} task",
        )

    # Update task status to cancelled
    updated_task = await crud.update_task(task_id, {"status": TaskStatus.CANCELLED})

    return {
        "success": True,
        "message": "Task cancelled successfully",
        "data": TaskResponse.model_validate(updated_task),
    }


@router.post("/{task_id}/assign", response_model=APIResponse)
@track_api_performance()
@handle_api_errors()
async def assign_task(
    instance_id: int,
    task_id: int = Depends(validate_task_id),
    crud: CRUDBase = Depends(get_crud),
) -> dict[str, Any]:
    """
    Assign a task to an instance.

    - **task_id**: The ID of the task to assign
    - **instance_id**: The ID of the instance to assign to
    """
    # Check if task exists
    task = await crud.get_task(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with ID {task_id} not found",
        )

    # Check if instance exists
    instance = await crud.get_instance(instance_id)
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Instance with ID {instance_id} not found",
        )

    # Assign task to instance
    updated_task = await crud.update_task(task_id, {"instance_id": instance_id})

    return {
        "success": True,
        "message": "Task assigned successfully",
        "data": TaskResponse.model_validate(updated_task),
    }


@router.delete("/{task_id}/assign", response_model=APIResponse)
@track_api_performance()
@handle_api_errors()
async def unassign_task(
    task_id: int = Depends(validate_task_id),
    crud: CRUDBase = Depends(get_crud),
) -> dict[str, Any]:
    """
    Unassign a task from its current instance.

    - **task_id**: The ID of the task to unassign
    """
    # Check if task exists
    task = await crud.get_task(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with ID {task_id} not found",
        )

    # Unassign task
    updated_task = await crud.update_task(task_id, {"instance_id": None})

    return {
        "success": True,
        "message": "Task unassigned successfully",
        "data": TaskResponse.model_validate(updated_task),
    }
