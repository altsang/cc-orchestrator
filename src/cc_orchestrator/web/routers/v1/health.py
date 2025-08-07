"""
Health monitoring API endpoints.

This module provides REST API endpoints for health checks,
monitoring instance health, and retrieving health metrics.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

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
    HealthCheckResponse,
    HealthStatus,
    PaginatedResponse,
)

router = APIRouter()


@router.get("/", response_model=APIResponse)
@track_api_performance()
@handle_api_errors()
async def health_check() -> dict[str, Any]:
    """
    API health check endpoint.

    Returns the overall health status of the API and its dependencies.
    """
    # TODO: Add actual health checks for database, external services, etc.
    health_data = {
        "status": "healthy",
        "timestamp": "2025-08-03T05:31:33Z",
        "version": "1.0.0",
        "checks": {"database": "healthy", "api": "healthy"},
    }

    return {
        "success": True,
        "message": "Health check completed successfully",
        "data": health_data,
    }


@router.get("/instances", response_model=PaginatedResponse)
@track_api_performance()
@handle_api_errors()
async def list_instance_health(
    pagination: PaginationParams = Depends(get_pagination_params),
    health_status: HealthStatus | None = Query(None, alias="status"),
    crud: CRUDBase = Depends(get_crud),
) -> dict[str, Any]:
    """
    List health status of all instances.

    - **page**: Page number (default: 1)
    - **size**: Items per page (default: 20, max: 100)
    - **status**: Filter by health status
    """
    # Build filter criteria
    filters = {}
    if health_status:
        filters["health_status"] = health_status

    # Get instances with their health status
    instances, total = await crud.list_instances(
        offset=pagination.offset, limit=pagination.size, filters=filters
    )

    # Extract health information
    health_data = []
    for instance in instances:
        health_data.append(
            {
                "instance_id": instance.id,
                "issue_id": instance.issue_id,
                "health_status": instance.health_status,
                "last_health_check": instance.last_health_check,
                "health_check_count": instance.health_check_count,
                "healthy_check_count": instance.healthy_check_count,
                "last_recovery_attempt": instance.last_recovery_attempt,
                "recovery_attempt_count": instance.recovery_attempt_count,
                "health_check_details": instance.health_check_details,
            }
        )

    return {
        "items": health_data,
        "total": total,
        "page": pagination.page,
        "size": pagination.size,
        "pages": (total + pagination.size - 1) // pagination.size,
    }


@router.get("/instances/{instance_id}", response_model=APIResponse)
@track_api_performance()
@handle_api_errors()
async def get_instance_health(
    instance_id: int = Depends(validate_instance_id),
    crud: CRUDBase = Depends(get_crud),
) -> dict[str, Any]:
    """
    Get health status of a specific instance.

    - **instance_id**: The ID of the instance
    """
    instance = await crud.get_instance(instance_id)
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Instance with ID {instance_id} not found",
        )

    health_data = {
        "instance_id": instance.id,
        "issue_id": instance.issue_id,
        "health_status": instance.health_status,
        "last_health_check": instance.last_health_check,
        "health_check_count": instance.health_check_count,
        "healthy_check_count": instance.healthy_check_count,
        "last_recovery_attempt": instance.last_recovery_attempt,
        "recovery_attempt_count": instance.recovery_attempt_count,
        "health_check_details": instance.health_check_details,
        "status": instance.status,
        "last_activity": instance.last_activity,
    }

    return {
        "success": True,
        "message": "Instance health retrieved successfully",
        "data": health_data,
    }


@router.post("/instances/{instance_id}/check", response_model=APIResponse)
@track_api_performance()
@handle_api_errors()
async def perform_health_check(
    instance_id: int = Depends(validate_instance_id),
    crud: CRUDBase = Depends(get_crud),
) -> dict[str, Any]:
    """
    Perform a health check on a specific instance.

    - **instance_id**: The ID of the instance to check
    """
    instance = await crud.get_instance(instance_id)
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Instance with ID {instance_id} not found",
        )

    # TODO: Integrate with actual health monitoring system
    # For now, simulate a health check
    import json
    from datetime import datetime

    # Simulate health check results
    check_results = {
        "process_running": True,
        "tmux_session_active": bool(instance.tmux_session),
        "workspace_accessible": bool(instance.workspace_path),
        "response_time_ms": 150,
    }

    # Determine overall health status
    if all(check_results.values()):
        overall_status = HealthStatus.HEALTHY
    else:
        overall_status = HealthStatus.DEGRADED

    # Create health check record
    health_check_data = {
        "instance_id": instance_id,
        "overall_status": overall_status,
        "check_results": json.dumps(check_results),
        "duration_ms": 150.0,
        "check_timestamp": datetime.now(),
    }

    health_check = await crud.create_health_check(health_check_data)

    # Update instance health status
    await crud.update_instance(
        instance_id,
        {
            "health_status": overall_status,
            "last_health_check": datetime.now(),
            "health_check_count": instance.health_check_count + 1,
            "healthy_check_count": instance.healthy_check_count
            + (1 if overall_status == HealthStatus.HEALTHY else 0),
            "health_check_details": json.dumps(check_results),
        },
    )

    return {
        "success": True,
        "message": "Health check completed successfully",
        "data": HealthCheckResponse.model_validate(health_check),
    }


@router.get("/instances/{instance_id}/history", response_model=PaginatedResponse)
@track_api_performance()
@handle_api_errors()
async def get_health_check_history(
    instance_id: int = Depends(validate_instance_id),
    pagination: PaginationParams = Depends(get_pagination_params),
    crud: CRUDBase = Depends(get_crud),
) -> dict[str, Any]:
    """
    Get health check history for an instance.

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

    # Get health check history
    health_checks, total = await crud.list_health_checks(
        offset=pagination.offset,
        limit=pagination.size,
        filters={"instance_id": instance_id},
    )

    health_check_responses = [
        HealthCheckResponse.model_validate(hc) for hc in health_checks
    ]

    return {
        "items": health_check_responses,
        "total": total,
        "page": pagination.page,
        "size": pagination.size,
        "pages": (total + pagination.size - 1) // pagination.size,
    }


@router.get("/instances/{instance_id}/metrics", response_model=APIResponse)
@track_api_performance()
@handle_api_errors()
async def get_health_metrics(
    instance_id: int = Depends(validate_instance_id),
    days: int = Query(7, ge=1, le=30, description="Number of days to analyze"),
    crud: CRUDBase = Depends(get_crud),
) -> dict[str, Any]:
    """
    Get health metrics for an instance over a time period.

    - **instance_id**: The ID of the instance
    - **days**: Number of days to analyze (1-30, default: 7)
    """
    # Check if instance exists
    instance = await crud.get_instance(instance_id)
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Instance with ID {instance_id} not found",
        )

    # TODO: Calculate actual metrics from health check history
    # For now, return simulated metrics
    metrics = {
        "instance_id": instance_id,
        "period_days": days,
        "uptime_percentage": 98.5,
        "total_checks": instance.health_check_count,
        "healthy_checks": instance.healthy_check_count,
        "health_percentage": (
            instance.healthy_check_count / max(instance.health_check_count, 1)
        )
        * 100,
        "recovery_attempts": instance.recovery_attempt_count,
        "last_health_check": instance.last_health_check,
        "current_status": instance.health_status,
        "average_response_time_ms": 145.2,
        "incidents": 2,
    }

    return {
        "success": True,
        "message": "Health metrics retrieved successfully",
        "data": metrics,
    }


@router.get("/overview", response_model=APIResponse)
@track_api_performance()
@handle_api_errors()
async def get_health_overview(
    crud: CRUDBase = Depends(get_crud),
) -> dict[str, Any]:
    """
    Get overall health overview of all instances.
    """
    # Get all instances
    instances, total_instances = await crud.list_instances(offset=0, limit=1000)

    # Calculate overview metrics
    status_counts = {}
    for health_status in HealthStatus:
        status_counts[health_status.value] = 0

    for instance in instances:
        status_counts[instance.health_status.value] += 1

    # Calculate overall health percentage
    healthy_count = status_counts.get("healthy", 0)
    health_percentage = (healthy_count / max(total_instances, 1)) * 100

    overview = {
        "total_instances": total_instances,
        "health_percentage": health_percentage,
        "status_distribution": status_counts,
        "critical_instances": status_counts.get("critical", 0),
        "unhealthy_instances": status_counts.get("unhealthy", 0),
        "degraded_instances": status_counts.get("degraded", 0),
        "healthy_instances": status_counts.get("healthy", 0),
        "timestamp": "2025-08-03T05:31:33Z",
    }

    return {
        "success": True,
        "message": "Health overview retrieved successfully",
        "data": overview,
    }
