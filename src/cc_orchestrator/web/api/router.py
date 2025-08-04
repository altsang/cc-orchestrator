"""
Main API router for REST endpoints.

Provides comprehensive REST API for orchestrator operations.
"""

from fastapi import APIRouter

from .instances import router as instances_router
from .tasks import router as tasks_router
from .websocket_stats import router as websocket_stats_router

router = APIRouter()

# Include sub-routers
router.include_router(instances_router, prefix="/instances", tags=["instances"])
router.include_router(tasks_router, prefix="/tasks", tags=["tasks"])
router.include_router(websocket_stats_router, prefix="/websocket", tags=["websocket"])


@router.get("/status")
async def get_system_status() -> dict[str, str]:
    """Get overall system status."""
    return {
        "status": "operational",
        "service": "cc-orchestrator-api",
        "version": "0.1.0",
    }
