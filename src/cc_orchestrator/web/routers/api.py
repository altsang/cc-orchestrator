"""REST API endpoints for CC-Orchestrator."""

from typing import Any

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from ...database.connection import get_db_session
from ...database.crud import InstanceCRUD
from ...database.models import InstanceStatus
from ..auth import get_current_user
from ..exceptions import (
    InstanceNotFoundError,
    InstanceOperationError,
)
from ..logging_utils import handle_api_errors, track_api_performance
from ..rate_limiter import get_client_ip, rate_limiter
from ..schemas import (
    InstanceCreate,
    InstanceListResponse,
    InstanceResponse,
    InstanceStatusUpdate,
)

router = APIRouter(tags=["instances"])


@router.get("/instances", response_model=InstanceListResponse)
@handle_api_errors()
@track_api_performance()
async def get_instances(
    request: Request,
    status: str | None = Query(None, description="Filter by instance status"),
    db: Session = Depends(get_db_session),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> InstanceListResponse:
    """Get all instances with optional status filtering."""
    # Apply rate limiting
    client_ip = get_client_ip(request)
    rate_limiter.check_rate_limit(client_ip, "GET:/api/v1/instances", 30, 60)

    # Convert status string to enum if provided
    status_filter = None
    if status:
        try:
            status_filter = InstanceStatus(status.lower())
        except ValueError:
            # Invalid status value, ignore filter
            status_filter = None

    instances = InstanceCRUD.list_all(db, status=status_filter)
    return InstanceListResponse(
        items=[InstanceResponse.from_model(instance) for instance in instances],
        total=len(instances),
    )


@router.get("/instances/{instance_id}", response_model=InstanceResponse)
@handle_api_errors()
@track_api_performance()
async def get_instance_by_id(
    instance_id: int,
    db: Session = Depends(get_db_session),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> InstanceResponse:
    """Get a specific instance by ID."""
    try:
        instance = InstanceCRUD.get_by_id(db, instance_id)
        return InstanceResponse.from_model(instance)
    except Exception as e:
        raise InstanceNotFoundError(instance_id) from e


@router.post("/instances", response_model=InstanceResponse, status_code=201)
@handle_api_errors()
@track_api_performance()
async def create_instance(
    request: Request,
    instance_data: InstanceCreate,
    db: Session = Depends(get_db_session),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> InstanceResponse:
    """Create a new instance."""
    # Apply stricter rate limiting for create operations
    client_ip = get_client_ip(request)
    rate_limiter.check_rate_limit(client_ip, "POST:/api/v1/instances", 10, 60)
    """Create a new instance."""
    instance = InstanceCRUD.create(
        db,
        issue_id=instance_data.issue_id,
    )
    return InstanceResponse.from_model(instance)


@router.patch("/instances/{instance_id}/status", response_model=InstanceResponse)
@handle_api_errors()
@track_api_performance()
async def update_instance_status_endpoint(
    instance_id: int,
    status_update: InstanceStatusUpdate,
    db: Session = Depends(get_db_session),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> InstanceResponse:
    """Update instance status."""
    try:
        instance = InstanceCRUD.update(db, instance_id, status=status_update.status)
        return InstanceResponse.from_model(instance)
    except Exception as e:
        raise InstanceNotFoundError(instance_id) from e


@router.post("/instances/{instance_id}/start")
@handle_api_errors()
@track_api_performance()
async def start_instance(
    request: Request,
    instance_id: int,
    db: Session = Depends(get_db_session),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Start an instance."""
    # Apply rate limiting for control operations
    client_ip = get_client_ip(request)
    rate_limiter.check_rate_limit(client_ip, "POST:/api/v1/instances/*/start", 20, 60)
    """Start an instance."""
    # TODO: Implement actual instance starting logic
    # For now, just update the status
    try:
        InstanceCRUD.update(db, instance_id, status=InstanceStatus.RUNNING)
        return {"message": "Instance start requested", "instance_id": str(instance_id)}
    except Exception as e:
        raise InstanceOperationError("Failed to start instance", instance_id) from e


@router.post("/instances/{instance_id}/stop")
@handle_api_errors()
@track_api_performance()
async def stop_instance(
    request: Request,
    instance_id: int,
    db: Session = Depends(get_db_session),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Stop an instance."""
    # Apply rate limiting for control operations
    client_ip = get_client_ip(request)
    rate_limiter.check_rate_limit(client_ip, "POST:/api/v1/instances/*/stop", 20, 60)
    """Stop an instance."""
    # TODO: Implement actual instance stopping logic
    # For now, just update the status
    try:
        InstanceCRUD.update(db, instance_id, status=InstanceStatus.STOPPED)
        return {"message": "Instance stop requested", "instance_id": str(instance_id)}
    except Exception as e:
        raise InstanceOperationError("Failed to stop instance", instance_id) from e


@router.post("/instances/{instance_id}/restart")
@handle_api_errors()
@track_api_performance()
async def restart_instance(
    request: Request,
    instance_id: int,
    db: Session = Depends(get_db_session),
    current_user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Restart an instance."""
    # Apply rate limiting for control operations
    client_ip = get_client_ip(request)
    rate_limiter.check_rate_limit(client_ip, "POST:/api/v1/instances/*/restart", 20, 60)
    """Restart an instance."""
    # TODO: Implement actual instance restart logic
    # For now, just update the status
    try:
        InstanceCRUD.update(db, instance_id, status=InstanceStatus.RUNNING)
        return {
            "message": "Instance restart requested",
            "instance_id": str(instance_id),
        }
    except Exception as e:
        raise InstanceOperationError("Failed to restart instance", instance_id) from e


# Health and monitoring endpoints
@router.get("/instances/{instance_id}/health")
@handle_api_errors()
@track_api_performance()
async def get_instance_health(
    instance_id: int, db: Session = Depends(get_db_session)
) -> dict[str, Any]:
    """Get instance health metrics."""
    try:
        instance = InstanceCRUD.get_by_id(db, instance_id)
        # TODO: Implement actual health checking
        return {
            "instance_id": instance_id,
            "status": instance.status,
            "health": "healthy",
            "cpu_usage": 0.0,
            "memory_usage": 0.0,
            "uptime_seconds": 0,
            "last_activity": (
                instance.updated_at.isoformat() if instance.updated_at else None
            ),
        }
    except Exception as e:
        raise InstanceNotFoundError(instance_id) from e


@router.get("/instances/{instance_id}/logs")
@handle_api_errors()
@track_api_performance()
async def get_instance_logs(
    instance_id: int,
    limit: int = 100,
    search: str | None = None,
    db: Session = Depends(get_db_session),
) -> dict[str, Any]:
    """Get instance logs with optional search filtering."""
    try:
        InstanceCRUD.get_by_id(db, instance_id)  # Verify instance exists
        # TODO: Implement actual log retrieval
        return {
            "instance_id": instance_id,
            "logs": [],
            "total": 0,
            "limit": limit,
            "search": search,
        }
    except Exception as e:
        raise InstanceNotFoundError(instance_id) from e
