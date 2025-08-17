"""Pydantic schemas for API request/response validation."""

from datetime import datetime
from enum import Enum
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field, field_validator

from ..database.models import (
    Instance,
    InstanceStatus,
    TaskPriority,
    TaskStatus,
)

# Explicit exports for mypy - only include what's actually defined
__all__ = [
    "InstanceStatus",
    "InstanceBase",
    "InstanceCreate",
    "InstanceUpdate",
    "InstanceResponse",
    "ConfigurationResponse",
    "APIResponse",
]

# Generic type for paginated responses
T = TypeVar("T")


class InstanceBase(BaseModel):
    """Base instance schema."""

    issue_id: str
    status: InstanceStatus = InstanceStatus.INITIALIZING


class InstanceCreate(InstanceBase):
    """Schema for creating instances."""

    # Additional fields for instance creation
    workspace_path: str | None = None
    branch_name: str | None = None
    tmux_session: str | None = None


class InstanceStatusUpdate(BaseModel):
    """Schema for updating instance status."""

    status: InstanceStatus

    @field_validator("status", mode="before")
    @classmethod
    def validate_status(cls, value):
        """Convert status string to InstanceStatus enum."""
        if isinstance(value, str):
            try:
                return InstanceStatus(value.lower())
            except ValueError:
                # If invalid enum value, return as-is to let Pydantic handle validation error
                return value
        return value


class InstanceResponse(InstanceBase):
    """Schema for instance responses."""

    id: int
    created_at: datetime
    updated_at: datetime | None = None

    # Override parent class status field to be string instead of enum
    status: str

    # Additional fields used in router endpoints
    health_status: str | None = None
    last_health_check: datetime | None = None
    last_activity: datetime | None = None
    process_id: int | None = None
    tmux_session: str | None = None

    @field_validator("status", mode="before")
    @classmethod
    def validate_status(cls, value):
        """Convert InstanceStatus enum to string value."""
        if hasattr(value, "value"):
            return value.value
        return value

    @field_validator("health_status", mode="before")
    @classmethod
    def validate_health_status(cls, value):
        """Convert HealthStatus enum to string value."""
        if hasattr(value, "value"):
            return value.value
        return value

    @classmethod
    def from_model(cls, instance: Instance) -> "InstanceResponse":
        """Create schema from database model."""
        return cls(
            id=instance.id,
            issue_id=instance.issue_id,
            status=instance.status,
            created_at=instance.created_at,
            updated_at=instance.updated_at,
            health_status=getattr(instance, "health_status", None),
            last_health_check=getattr(instance, "last_health_check", None),
            last_activity=getattr(instance, "last_activity", None),
            process_id=getattr(instance, "process_id", None),
            tmux_session=getattr(instance, "tmux_session", None),
        )

    class Config:
        from_attributes = True


class InstanceListResponse(BaseModel):
    """Schema for instance list responses."""

    items: list[InstanceResponse]
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
    size: int = 20
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

    title: str = Field(min_length=1, max_length=200)
    description: str = ""
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.MEDIUM
    instance_id: int | None = None
    command: str | None = None
    schedule: str | None = None  # Cron expression
    worktree_id: int | None = None


class TaskUpdate(BaseModel):
    """Schema for updating tasks."""

    title: str | None = None
    description: str | None = None
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    command: str | None = None
    schedule: str | None = None
    enabled: bool | None = None
    instance_id: int | None = None
    worktree_id: int | None = None


class TaskResponse(BaseModel):
    """Schema for task responses."""

    id: int
    title: str
    description: str
    status: str = "pending"
    priority: str = "medium"
    instance_id: int | None = None
    command: str | None = None
    schedule: str | None = None
    enabled: bool = True
    created_at: datetime
    updated_at: datetime | None = None
    last_run: datetime | None = None
    next_run: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    due_date: datetime | None = None
    estimated_duration: int | None = None
    actual_duration: int | None = None
    requirements: dict[str, Any] = Field(default_factory=dict)
    results: dict[str, Any] = Field(default_factory=dict)
    extra_metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("status", mode="before")
    @classmethod
    def validate_status(cls, value):
        """Convert TaskStatus enum to string value."""
        if hasattr(value, "value"):
            return value.value
        return value

    @field_validator("priority", mode="before")
    @classmethod
    def validate_priority(cls, value):
        """Convert TaskPriority enum to string value."""
        if hasattr(value, "value"):
            return value.name.lower()
        return value


# Worktree Schemas
class WorktreeCreate(BaseModel):
    """Schema for creating worktrees."""

    name: str = Field(min_length=1, max_length=100)
    branch_name: str = Field(min_length=1, max_length=100)
    base_branch: str = "main"
    path: str | None = None
    instance_id: int | None = None


class WorktreeUpdate(BaseModel):
    """Schema for updating worktrees."""

    name: str | None = None
    branch_name: str | None = None
    active: bool | None = None
    instance_id: int | None = None


class WorktreeResponse(BaseModel):
    """Schema for worktree responses."""

    id: int
    name: str
    branch_name: str
    base_branch: str
    path: str
    active: bool = True
    created_at: datetime
    updated_at: datetime | None = None

    # Additional fields from database model
    status: str | None = None
    current_commit: str | None = None
    has_uncommitted_changes: bool = False
    last_sync: datetime | None = None

    class Config:
        from_attributes = True


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
    description: str | None = None
    category: str
    scope: str  # Changed from ConfigScope to str for API consistency
    instance_id: int | None = None
    is_secret: bool = False
    is_readonly: bool = False
    created_at: datetime
    updated_at: datetime | None = None

    @field_validator("scope", mode="before")
    @classmethod
    def validate_scope(cls, value):
        """Convert ConfigScope enum to string value."""
        if hasattr(value, "value"):
            return value.value
        return value


# Health Check Schemas
class HealthStatus(str, Enum):
    """Health check status values."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class HealthCheckResponse(BaseModel):
    """Schema for health check responses."""

    id: int
    instance_id: int
    overall_status: HealthStatus
    check_results: str  # JSON string
    duration_ms: float
    check_timestamp: datetime
    created_at: datetime
    updated_at: datetime | None = None

    @field_validator("overall_status", mode="before")
    @classmethod
    def validate_overall_status(cls, value):
        """Convert HealthStatus enum to string value if needed."""
        if hasattr(value, "value"):
            return value.value
        return value

    class Config:
        from_attributes = True
