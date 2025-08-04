"""
Pydantic schemas for API request/response validation.

This module defines the data models used for validating
API requests and responses in the FastAPI application.
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from ..database.models import (
    ConfigScope,
    HealthStatus,
    InstanceStatus,
    TaskPriority,
    TaskStatus,
    WorktreeStatus,
)


class AlertLevel(Enum):
    """Alert severity levels."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


# Base schemas
class BaseSchema(BaseModel):
    """Base schema with common configuration."""

    model_config = ConfigDict(
        from_attributes=True,
        use_enum_values=True,
        validate_assignment=True,
    )


class TimestampMixin(BaseModel):
    """Mixin for models with timestamp fields."""

    created_at: datetime
    updated_at: datetime


# Instance schemas
class InstanceBase(BaseSchema):
    """Base instance schema with common fields."""

    issue_id: str = Field(
        ..., min_length=1, max_length=50, description="GitHub issue ID"
    )
    status: InstanceStatus = Field(default=InstanceStatus.INITIALIZING)
    workspace_path: str | None = Field(None, max_length=500)
    branch_name: str | None = Field(None, max_length=255)
    tmux_session: str | None = Field(None, max_length=255)
    process_id: int | None = Field(None, ge=1)
    health_status: HealthStatus = Field(default=HealthStatus.UNKNOWN)
    extra_metadata: dict[str, Any] = Field(default_factory=dict)


class InstanceCreate(InstanceBase):
    """Schema for creating a new instance."""

    # issue_id is required for creation
    pass


class InstanceUpdate(BaseSchema):
    """Schema for updating an instance."""

    status: InstanceStatus | None = None
    workspace_path: str | None = Field(None, max_length=500)
    branch_name: str | None = Field(None, max_length=255)
    tmux_session: str | None = Field(None, max_length=255)
    process_id: int | None = Field(None, ge=1)
    health_status: HealthStatus | None = None
    extra_metadata: dict[str, Any] | None = None


class InstanceResponse(InstanceBase, TimestampMixin):
    """Schema for instance API responses."""

    id: int
    last_health_check: datetime | None = None
    health_check_count: int = 0
    healthy_check_count: int = 0
    last_recovery_attempt: datetime | None = None
    recovery_attempt_count: int = 0
    health_check_details: str | None = None
    last_activity: datetime | None = None


# Task schemas
class TaskBase(BaseSchema):
    """Base task schema with common fields."""

    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    status: TaskStatus = Field(default=TaskStatus.PENDING)
    priority: TaskPriority = Field(default=TaskPriority.MEDIUM)
    instance_id: int | None = Field(None, ge=1)
    worktree_id: int | None = Field(None, ge=1)
    due_date: datetime | None = None
    estimated_duration: int | None = Field(
        None, ge=1, description="Duration in minutes"
    )
    requirements: dict[str, Any] = Field(default_factory=dict)
    extra_metadata: dict[str, Any] = Field(default_factory=dict)


class TaskCreate(TaskBase):
    """Schema for creating a new task."""

    # title is required for creation
    pass


class TaskUpdate(BaseSchema):
    """Schema for updating a task."""

    title: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    instance_id: int | None = Field(None, ge=1)
    worktree_id: int | None = Field(None, ge=1)
    due_date: datetime | None = None
    estimated_duration: int | None = Field(None, ge=1)
    actual_duration: int | None = Field(None, ge=1)
    requirements: dict[str, Any] | None = None
    results: dict[str, Any] | None = None
    extra_metadata: dict[str, Any] | None = None


class TaskResponse(TaskBase, TimestampMixin):
    """Schema for task API responses."""

    id: int
    started_at: datetime | None = None
    completed_at: datetime | None = None
    actual_duration: int | None = None
    results: dict[str, Any] = Field(default_factory=dict)


# Worktree schemas
class WorktreeBase(BaseSchema):
    """Base worktree schema with common fields."""

    name: str = Field(..., min_length=1, max_length=255)
    path: str = Field(..., min_length=1, max_length=500)
    branch_name: str = Field(..., min_length=1, max_length=255)
    repository_url: str | None = Field(None, max_length=500)
    status: WorktreeStatus = Field(default=WorktreeStatus.ACTIVE)
    instance_id: int | None = Field(None, ge=1)
    current_commit: str | None = Field(None, min_length=7, max_length=40)
    has_uncommitted_changes: bool = Field(default=False)
    git_config: dict[str, Any] = Field(default_factory=dict)
    extra_metadata: dict[str, Any] = Field(default_factory=dict)


class WorktreeCreate(WorktreeBase):
    """Schema for creating a new worktree."""

    # name, path, and branch_name are required for creation
    pass


class WorktreeUpdate(BaseSchema):
    """Schema for updating a worktree."""

    name: str | None = Field(None, min_length=1, max_length=255)
    status: WorktreeStatus | None = None
    repository_url: str | None = Field(None, max_length=500)
    instance_id: int | None = Field(None, ge=1)
    current_commit: str | None = Field(None, min_length=7, max_length=40)
    has_uncommitted_changes: bool | None = None
    git_config: dict[str, Any] | None = None
    extra_metadata: dict[str, Any] | None = None


class WorktreeResponse(WorktreeBase, TimestampMixin):
    """Schema for worktree API responses."""

    id: int
    last_sync: datetime | None = None


# Configuration schemas
class ConfigurationBase(BaseSchema):
    """Base configuration schema with common fields."""

    key: str = Field(..., min_length=1, max_length=255)
    value: str = Field(..., min_length=1)
    scope: ConfigScope = Field(default=ConfigScope.GLOBAL)
    instance_id: int | None = Field(None, ge=1)
    description: str | None = None
    is_secret: bool = Field(default=False)
    is_readonly: bool = Field(default=False)
    extra_metadata: dict[str, Any] = Field(default_factory=dict)


class ConfigurationCreate(ConfigurationBase):
    """Schema for creating a new configuration."""

    # key and value are required for creation
    pass


class ConfigurationUpdate(BaseSchema):
    """Schema for updating a configuration."""

    value: str | None = Field(None, min_length=1)
    description: str | None = None
    is_secret: bool | None = None
    is_readonly: bool | None = None
    extra_metadata: dict[str, Any] | None = None


class ConfigurationResponse(ConfigurationBase, TimestampMixin):
    """Schema for configuration API responses."""

    id: int


# Health check schemas
class HealthCheckBase(BaseSchema):
    """Base health check schema."""

    instance_id: int = Field(..., ge=1)
    overall_status: HealthStatus
    check_results: str
    duration_ms: float = Field(default=0.0, ge=0)


class HealthCheckCreate(HealthCheckBase):
    """Schema for creating a health check record."""

    check_timestamp: datetime = Field(default_factory=datetime.now)


class HealthCheckResponse(HealthCheckBase, TimestampMixin):
    """Schema for health check API responses."""

    id: int
    check_timestamp: datetime


# Alert schemas
class AlertBase(BaseSchema):
    """Base alert schema."""

    instance_id: int = Field(..., ge=1)
    alert_id: str = Field(..., min_length=1, max_length=255)
    level: AlertLevel
    message: str = Field(..., min_length=1)
    details: str | None = None


class AlertCreate(AlertBase):
    """Schema for creating an alert."""

    timestamp: datetime = Field(default_factory=datetime.now)


class AlertResponse(AlertBase, TimestampMixin):
    """Schema for alert API responses."""

    id: int
    timestamp: datetime


# Recovery attempt schemas
class RecoveryAttemptBase(BaseSchema):
    """Base recovery attempt schema."""

    instance_id: int = Field(..., ge=1)
    strategy: str = Field(..., min_length=1, max_length=50)
    success: bool = Field(default=False)
    error_message: str | None = None
    duration_seconds: float = Field(default=0.0, ge=0)
    details: str | None = None


class RecoveryAttemptCreate(RecoveryAttemptBase):
    """Schema for creating a recovery attempt record."""

    attempt_timestamp: datetime = Field(default_factory=datetime.now)


class RecoveryAttemptResponse(RecoveryAttemptBase, TimestampMixin):
    """Schema for recovery attempt API responses."""

    id: int
    attempt_timestamp: datetime


# Pagination schemas
class PaginationParams(BaseSchema):
    """Schema for pagination parameters."""

    page: int = Field(default=1, ge=1, description="Page number")
    size: int = Field(default=20, ge=1, le=100, description="Items per page")


class PaginatedResponse(BaseSchema):
    """Schema for paginated API responses."""

    items: list[Any]
    total: int = Field(..., ge=0)
    page: int = Field(..., ge=1)
    size: int = Field(..., ge=1)
    pages: int = Field(..., ge=0)


# Filter schemas
class InstanceFilter(BaseSchema):
    """Schema for filtering instances."""

    status: InstanceStatus | None = None
    health_status: HealthStatus | None = None
    branch_name: str | None = None


class TaskFilter(BaseSchema):
    """Schema for filtering tasks."""

    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    instance_id: int | None = Field(None, ge=1)
    worktree_id: int | None = Field(None, ge=1)


class WorktreeFilter(BaseSchema):
    """Schema for filtering worktrees."""

    status: WorktreeStatus | None = None
    branch_name: str | None = None
    instance_id: int | None = Field(None, ge=1)


# API response schemas
class APIResponse(BaseSchema):
    """Standard API response wrapper."""

    success: bool = True
    message: str = "Operation completed successfully"
    data: Any | None = None


class ErrorResponse(BaseSchema):
    """Standard error response schema."""

    success: bool = False
    error: str
    message: str
    details: dict[str, Any] | None = None
