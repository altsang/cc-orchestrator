"""Version 1 API routers."""

from fastapi import APIRouter

from . import alerts, config, health, instances, logs, tasks, worktrees

# Create the main v1 router
api_router_v1 = APIRouter()

# Include all v1 routers
api_router_v1.include_router(
    instances.router, prefix="/instances", tags=["v1-instances"]
)
api_router_v1.include_router(tasks.router, prefix="/tasks", tags=["v1-tasks"])
api_router_v1.include_router(
    worktrees.router, prefix="/worktrees", tags=["v1-worktrees"]
)
api_router_v1.include_router(config.router, prefix="/config", tags=["v1-config"])
api_router_v1.include_router(health.router, prefix="/health", tags=["v1-health"])
api_router_v1.include_router(alerts.router, prefix="/alerts", tags=["v1-alerts"])
api_router_v1.include_router(logs.router, prefix="/logs", tags=["v1-logs"])

__all__ = ["api_router_v1"]
