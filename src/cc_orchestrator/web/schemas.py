"""Pydantic schemas for API request/response validation."""

from datetime import datetime
from enum import Enum
from typing import Any, Generic, TypeVar

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

# Generic type for paginated responses
T = TypeVar("T")


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


# Common API Response Schemas
class APIResponse(BaseModel, Generic[T]):
    """Generic API response schema."""

    success: bool = True
    message: str = ""
    data: T | None = None


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response schema."""

    items: list[T]
    total: int
    page: int = 1
    page_size: int = 20
    pages: int = 1


# Instance Update Schema
class InstanceUpdate(BaseModel):
    """Schema for updating instances."""

    status: InstanceStatus | None = None


# Alert Schemas
class AlertLevel(str, Enum):
    """Alert severity levels."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertCreate(BaseModel):
    """Schema for creating alerts."""

    title: str = Field(min_length=1, max_length=200)
    message: str = Field(min_length=1, max_length=1000)
    level: AlertLevel
    instance_id: int | None = None
    alert_id: str | None = None


class AlertResponse(BaseModel):
    """Schema for alert responses."""

    id: int
    title: str
    message: str
    level: AlertLevel
    instance_id: int | None = None
    created_at: datetime
    acknowledged: bool = False
    acknowledged_at: datetime | None = None


# Task Schemas
class TaskCreate(BaseModel):
    """Schema for creating tasks."""

    name: str = Field(min_length=1, max_length=200)
    description: str = ""
    instance_id: int | None = None
    command: str | None = None
    schedule: str | None = None  # Cron expression
    worktree_id: int | None = None


class TaskUpdate(BaseModel):
    """Schema for updating tasks."""

    name: str | None = None
    description: str | None = None
    command: str | None = None
    schedule: str | None = None
    enabled: bool | None = None
    instance_id: int | None = None
    worktree_id: int | None = None


class TaskResponse(BaseModel):
    """Schema for task responses."""

    id: int
    name: str
    description: str
    instance_id: int | None = None
    command: str | None = None
    schedule: str | None = None
    enabled: bool = True
    created_at: datetime
    updated_at: datetime | None = None
    last_run: datetime | None = None
    next_run: datetime | None = None
    status: str = "pending"


# Worktree Schemas
class WorktreeCreate(BaseModel):
    """Schema for creating worktrees."""

    name: str = Field(min_length=1, max_length=100)
    branch: str = Field(min_length=1, max_length=100)
    base_branch: str = "main"
    path: str | None = None
    instance_id: int | None = None


class WorktreeUpdate(BaseModel):
    """Schema for updating worktrees."""

    name: str | None = None
    branch: str | None = None
    active: bool | None = None
    instance_id: int | None = None


class WorktreeResponse(BaseModel):
    """Schema for worktree responses."""

    id: int
    name: str
    branch: str
    base_branch: str
    path: str
    active: bool = True
    created_at: datetime
    updated_at: datetime | None = None


# Configuration Schemas
class ConfigurationCreate(BaseModel):
    """Schema for creating configuration."""

    key: str = Field(min_length=1, max_length=100)
    value: str = Field(max_length=1000)
    description: str = ""
    category: str = "general"
    scope: str = "global"
    instance_id: int | None = None


class ConfigurationUpdate(BaseModel):
    """Schema for updating configuration."""

    value: str | None = None
    description: str | None = None
    category: str | None = None


class ConfigurationResponse(BaseModel):
    """Schema for configuration responses."""

    id: int
    key: str
    value: str
    description: str
    category: str
    created_at: datetime
    updated_at: datetime | None = None


# Health Check Schemas
class HealthStatus(str, Enum):
    """Health check status values."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class HealthCheckResponse(BaseModel):
    """Schema for health check responses."""

    status: HealthStatus
    timestamp: datetime
    checks: dict[str, Any] = Field(default_factory=dict)
    uptime_seconds: int = 0
    version: str = "unknown"
