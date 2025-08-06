"""
Instance management API endpoints.

Provides REST endpoints for Claude Code instance operations.
"""

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


class InstanceCreateRequest(BaseModel):
    """Request model for creating a new instance."""

    task_id: str
    branch: str | None = None
    tmux_session: str | None = None


class InstanceResponse(BaseModel):
    """Response model for instance information."""

    instance_id: str
    task_id: str
    status: str
    branch: str | None = None
    tmux_session: str | None = None
    created_at: str
    last_seen: str | None = None


@router.get("/")
async def list_instances() -> list[InstanceResponse]:
    """
    List all Claude Code instances.

    Returns:
        List of instance information
    """
    # TODO: Implement actual instance listing
    # This is a placeholder that would integrate with the core orchestrator
    return []


@router.post("/")
async def create_instance(request: InstanceCreateRequest) -> InstanceResponse:
    """
    Create a new Claude Code instance.

    Args:
        request: Instance creation parameters

    Returns:
        Created instance information
    """
    # TODO: Implement actual instance creation
    # This would integrate with the core orchestrator to spawn instances
    raise HTTPException(status_code=501, detail="Instance creation not yet implemented")


@router.get("/{instance_id}")
async def get_instance(instance_id: str) -> InstanceResponse:
    """
    Get details for a specific instance.

    Args:
        instance_id: ID of the instance to retrieve

    Returns:
        Instance information
    """
    # TODO: Implement actual instance retrieval
    raise HTTPException(status_code=404, detail="Instance not found")


@router.delete("/{instance_id}")
async def stop_instance(instance_id: str) -> dict[str, Any]:
    """
    Stop a Claude Code instance.

    Args:
        instance_id: ID of the instance to stop

    Returns:
        Operation result
    """
    # TODO: Implement actual instance stopping
    raise HTTPException(status_code=501, detail="Instance stopping not yet implemented")


@router.post("/{instance_id}/restart")
async def restart_instance(instance_id: str) -> dict[str, Any]:
    """
    Restart a Claude Code instance.

    Args:
        instance_id: ID of the instance to restart

    Returns:
        Operation result
    """
    # TODO: Implement actual instance restarting
    raise HTTPException(
        status_code=501, detail="Instance restarting not yet implemented"
    )
