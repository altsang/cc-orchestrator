"""
Alert management API endpoints.

This module provides REST API endpoints for managing alerts,
including viewing alert history and acknowledging alerts.
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
    AlertCreate,
    AlertLevel,
    AlertResponse,
    APIResponse,
    PaginatedResponse,
)

router = APIRouter()


@router.get("/", response_model=PaginatedResponse)
@track_api_performance()
@handle_api_errors()
async def list_alerts(
    pagination: PaginationParams = Depends(get_pagination_params),
    level: AlertLevel | None = Query(None, alias="level"),
    instance_id: int | None = Query(None, alias="instance_id"),
    crud: CRUDBase = Depends(get_crud),
) -> dict[str, Any]:
    """
    List all alerts with optional filtering and pagination.

    - **page**: Page number (default: 1)
    - **size**: Items per page (default: 20, max: 100)
    - **level**: Filter by alert level
    - **instance_id**: Filter by instance
    """
    # Build filter criteria
    filters = {}
    if level:
        filters["level"] = level
    if instance_id:
        filters["instance_id"] = instance_id

    # Get alerts with pagination
    alerts, total = await crud.list_alerts(
        offset=pagination.offset, limit=pagination.size, filters=filters
    )

    # Convert to response schemas
    alert_responses = [AlertResponse.model_validate(alert) for alert in alerts]

    return {
        "items": alert_responses,
        "total": total,
        "page": pagination.page,
        "size": pagination.size,
        "pages": (total + pagination.size - 1) // pagination.size,
    }


@router.post("/", response_model=APIResponse, status_code=status.HTTP_201_CREATED)
@track_api_performance()
@handle_api_errors()
async def create_alert(
    alert_data: AlertCreate,
    crud: CRUDBase = Depends(get_crud),
) -> dict[str, Any]:
    """
    Create a new alert.

    - **instance_id**: Instance ID (required)
    - **alert_id**: Unique alert identifier (required)
    - **level**: Alert level (required)
    - **message**: Alert message (required)
    - **details**: Additional alert details
    - **timestamp**: Alert timestamp (default: now)
    """
    # Validate instance exists
    instance = await crud.get_instance(alert_data.instance_id)
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Instance with ID {alert_data.instance_id} not found",
        )

    # Check if alert with this alert_id already exists
    existing = await crud.get_alert_by_alert_id(alert_data.alert_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Alert with ID '{alert_data.alert_id}' already exists",
        )

    # Create the alert
    alert = await crud.create_alert(alert_data.model_dump())

    return {
        "success": True,
        "message": "Alert created successfully",
        "data": AlertResponse.model_validate(alert),
    }


@router.get("/{alert_id}", response_model=APIResponse)
@track_api_performance()
@handle_api_errors()
async def get_alert(
    alert_id: str,
    crud: CRUDBase = Depends(get_crud),
) -> dict[str, Any]:
    """
    Get a specific alert by alert ID.

    - **alert_id**: The unique alert identifier
    """
    alert = await crud.get_alert_by_alert_id(alert_id)
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert with ID '{alert_id}' not found",
        )

    return {
        "success": True,
        "message": "Alert retrieved successfully",
        "data": AlertResponse.model_validate(alert),
    }


@router.get("/instances/{instance_id}", response_model=PaginatedResponse)
@track_api_performance()
@handle_api_errors()
async def get_instance_alerts(
    instance_id: int = Depends(validate_instance_id),
    pagination: PaginationParams = Depends(get_pagination_params),
    level: AlertLevel | None = Query(None, alias="level"),
    crud: CRUDBase = Depends(get_crud),
) -> dict[str, Any]:
    """
    Get all alerts for a specific instance.

    - **instance_id**: The ID of the instance
    - **page**: Page number (default: 1)
    - **size**: Items per page (default: 20, max: 100)
    - **level**: Filter by alert level
    """
    # Check if instance exists
    instance = await crud.get_instance(instance_id)
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Instance with ID {instance_id} not found",
        )

    # Build filters
    filters = {"instance_id": instance_id}
    if level:
        filters["level"] = level

    # Get alerts for this instance
    alerts, total = await crud.list_alerts(
        offset=pagination.offset, limit=pagination.size, filters=filters
    )

    alert_responses = [AlertResponse.model_validate(alert) for alert in alerts]

    return {
        "items": alert_responses,
        "total": total,
        "page": pagination.page,
        "size": pagination.size,
        "pages": (total + pagination.size - 1) // pagination.size,
    }


@router.get("/levels/{level}", response_model=PaginatedResponse)
@track_api_performance()
@handle_api_errors()
async def get_alerts_by_level(
    level: AlertLevel,
    pagination: PaginationParams = Depends(get_pagination_params),
    instance_id: int | None = Query(None, alias="instance_id"),
    crud: CRUDBase = Depends(get_crud),
) -> dict[str, Any]:
    """
    Get all alerts of a specific level.

    - **level**: Alert level to filter by
    - **page**: Page number (default: 1)
    - **size**: Items per page (default: 20, max: 100)
    - **instance_id**: Optional instance filter
    """
    # Build filters
    filters = {"level": level}
    if instance_id:
        filters["instance_id"] = instance_id

    # Get alerts with the specified level
    alerts, total = await crud.list_alerts(
        offset=pagination.offset, limit=pagination.size, filters=filters
    )

    alert_responses = [AlertResponse.model_validate(alert) for alert in alerts]

    return {
        "items": alert_responses,
        "total": total,
        "page": pagination.page,
        "size": pagination.size,
        "pages": (total + pagination.size - 1) // pagination.size,
    }


@router.get("/summary/counts", response_model=APIResponse)
@track_api_performance()
@handle_api_errors()
async def get_alert_summary(
    instance_id: int | None = Query(None, alias="instance_id"),
    hours: int = Query(24, ge=1, le=168, description="Hours to look back"),
    crud: CRUDBase = Depends(get_crud),
) -> dict[str, Any]:
    """
    Get alert summary with counts by level.

    - **instance_id**: Optional instance filter
    - **hours**: Hours to look back (1-168, default: 24)
    """
    # TODO: Implement time-based filtering in CRUD layer
    # For now, get all alerts and filter in memory

    filters = {}
    if instance_id:
        filters["instance_id"] = instance_id

    # Get all alerts (up to reasonable limit for summary)
    alerts, total = await crud.list_alerts(offset=0, limit=10000, filters=filters)

    # Count alerts by level
    level_counts = {}
    for level in AlertLevel:
        level_counts[level.value] = 0

    for alert in alerts:
        level_counts[alert.level.value] += 1

    # Calculate summary metrics
    critical_alerts = level_counts.get("critical", 0)
    error_alerts = level_counts.get("error", 0)
    warning_alerts = level_counts.get("warning", 0)
    info_alerts = level_counts.get("info", 0)

    total_alerts = sum(level_counts.values())

    summary = {
        "total_alerts": total_alerts,
        "period_hours": hours,
        "level_counts": level_counts,
        "critical_alerts": critical_alerts,
        "error_alerts": error_alerts,
        "warning_alerts": warning_alerts,
        "info_alerts": info_alerts,
        "high_priority_alerts": critical_alerts + error_alerts,
        "instance_filter": instance_id,
    }

    return {
        "success": True,
        "message": "Alert summary retrieved successfully",
        "data": summary,
    }


@router.get("/recent/critical", response_model=PaginatedResponse)
@track_api_performance()
@handle_api_errors()
async def get_recent_critical_alerts(
    pagination: PaginationParams = Depends(get_pagination_params),
    instance_id: int | None = Query(None, alias="instance_id"),
    crud: CRUDBase = Depends(get_crud),
) -> dict[str, Any]:
    """
    Get recent critical alerts.

    - **page**: Page number (default: 1)
    - **size**: Items per page (default: 20, max: 100)
    - **instance_id**: Optional instance filter
    """
    # Build filters for critical alerts
    filters = {"level": AlertLevel.CRITICAL}
    if instance_id:
        filters["instance_id"] = instance_id

    # Get recent critical alerts
    alerts, total = await crud.list_alerts(
        offset=pagination.offset, limit=pagination.size, filters=filters
    )

    alert_responses = [AlertResponse.model_validate(alert) for alert in alerts]

    return {
        "items": alert_responses,
        "total": total,
        "page": pagination.page,
        "size": pagination.size,
        "pages": (total + pagination.size - 1) // pagination.size,
    }
