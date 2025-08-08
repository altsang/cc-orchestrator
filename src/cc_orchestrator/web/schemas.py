"""Pydantic schemas for API request/response validation."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from ..database.models import Instance, InstanceStatus

# Explicit exports for mypy
__all__ = [
    "HealthStatus",
    "InstanceStatus",
    "TaskStatus",
    "TaskPriority",
    "WorktreeStatus",
    "ConfigScope",
    "AlertLevel",
    "BaseSchema",
    "TimestampMixin",
    "InstanceBase",
    "InstanceCreate",
    "InstanceUpdate",
    "InstanceResponse",
    "TaskBase",
    "TaskCreate",
    "TaskUpdate",
    "TaskResponse",
    "WorktreeBase",
    "WorktreeCreate",
    "WorktreeUpdate",
    "WorktreeResponse",
    "ConfigurationBase",
    "ConfigurationCreate",
    "ConfigurationUpdate",
    "ConfigurationResponse",
    "HealthCheckBase",
    "HealthCheckCreate",
    "HealthCheckResponse",
    "AlertBase",
    "AlertCreate",
    "AlertResponse",
    "RecoveryAttemptBase",
    "RecoveryAttemptCreate",
    "RecoveryAttemptResponse",
    "PaginationParams",
    "PaginatedResponse",
    "InstanceFilter",
    "TaskFilter",
    "WorktreeFilter",
    "APIResponse",
    "ErrorResponse",
]


class InstanceBase(BaseModel):
    """Base instance schema."""

    issue_id: str
    status: InstanceStatus


class InstanceCreate(InstanceBase):
    """Schema for creating instances."""

    pass


class InstanceStatusUpdate(BaseModel):
    """Schema for updating instance status."""

    status: InstanceStatus


class InstanceResponse(InstanceBase):
    """Schema for instance responses."""

    id: int
    created_at: datetime
    updated_at: datetime | None = None

    @classmethod
    def from_model(cls, instance: Instance) -> "InstanceResponse":
        """Create schema from database model."""
        return cls(
            id=instance.id,
            issue_id=instance.issue_id,
            status=instance.status,
            created_at=instance.created_at,
            updated_at=instance.updated_at,
        )

    class Config:
        from_attributes = True


class InstanceListResponse(BaseModel):
    """Schema for instance list responses."""

    instances: list[InstanceResponse]
    total: int


class InstanceHealthResponse(BaseModel):
    """Schema for instance health responses."""

    instance_id: int
    status: InstanceStatus
    health: str
    cpu_usage: float
    memory_usage: float
    uptime_seconds: int
    last_activity: str | None = None


class InstanceLogsResponse(BaseModel):
    """Schema for instance logs responses."""

    instance_id: int
    logs: list[dict[str, Any]]
    total: int
    limit: int
    search: str | None = None


class WebSocketMessage(BaseModel):
    """Schema for WebSocket messages."""

    type: str
    data: dict[str, Any] = Field(default_factory=dict)
    timestamp: str | None = None


class InstanceMetrics(BaseModel):
    """Schema for instance resource metrics."""

    instance_id: int
    cpu_usage: float = Field(ge=0.0, le=100.0)
    memory_usage: float = Field(ge=0.0, le=100.0)
    disk_usage: float = Field(ge=0.0, le=100.0)
    network_in: float = Field(ge=0.0)
    network_out: float = Field(ge=0.0)
    uptime_seconds: int = Field(ge=0)
    timestamp: datetime


class SystemStatus(BaseModel):
    """Schema for overall system status."""

    total_instances: int
    running_instances: int
    stopped_instances: int
    failed_instances: int
    pending_instances: int
    system_cpu_usage: float = Field(ge=0.0, le=100.0)
    system_memory_usage: float = Field(ge=0.0, le=100.0)
    active_connections: int = Field(ge=0)
