"""SQLAlchemy database models for cc-orchestrator."""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy import (
    Enum as SQLEnum,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from ..core.enums import InstanceStatus


class Base(DeclarativeBase):
    """Base class for all database models."""

    # Define default table args that can be inherited by all models
    __table_args__ = {}


class HealthStatus(Enum):
    """Health status of an instance."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class TaskStatus(Enum):
    """Status of a task."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPriority(Enum):
    """Priority level of a task."""

    LOW = 1
    MEDIUM = 2
    HIGH = 3
    URGENT = 4


class WorktreeStatus(Enum):
    """Status of a git worktree."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    DIRTY = "dirty"
    ERROR = "error"


class ConfigScope(Enum):
    """Configuration scope."""

    GLOBAL = "global"
    USER = "user"
    PROJECT = "project"
    INSTANCE = "instance"


class Instance(Base):
    """Claude Code instance model."""

    __tablename__ = "instances"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    issue_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    status: Mapped[InstanceStatus] = mapped_column(
        SQLEnum(InstanceStatus), nullable=False, default=InstanceStatus.INITIALIZING
    )
    workspace_path: Mapped[str | None] = mapped_column(String(500))
    branch_name: Mapped[str | None] = mapped_column(String(255))
    tmux_session: Mapped[str | None] = mapped_column(String(255))
    process_id: Mapped[int | None] = mapped_column(Integer)

    # Health monitoring attributes (from Issue #16)
    health_status: Mapped[HealthStatus] = mapped_column(
        SQLEnum(HealthStatus), nullable=False, default=HealthStatus.UNKNOWN
    )
    last_health_check: Mapped[datetime | None] = mapped_column(DateTime)
    health_check_count: Mapped[int] = mapped_column(Integer, default=0)
    healthy_check_count: Mapped[int] = mapped_column(Integer, default=0)
    last_recovery_attempt: Mapped[datetime | None] = mapped_column(DateTime)
    recovery_attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    health_check_details: Mapped[str | None] = mapped_column(Text)

    def __init__(self, **kwargs):
        # Set Python-level defaults for enum fields if not provided
        if "status" not in kwargs:
            kwargs["status"] = InstanceStatus.INITIALIZING
        if "health_status" not in kwargs:
            kwargs["health_status"] = HealthStatus.UNKNOWN
        if "health_check_count" not in kwargs:
            kwargs["health_check_count"] = 0
        if "healthy_check_count" not in kwargs:
            kwargs["healthy_check_count"] = 0
        if "recovery_attempt_count" not in kwargs:
            kwargs["recovery_attempt_count"] = 0
        if "extra_metadata" not in kwargs:
            kwargs["extra_metadata"] = {}
        super().__init__(**kwargs)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now, onupdate=datetime.now
    )
    last_activity: Mapped[datetime | None] = mapped_column(DateTime)

    # JSON metadata for flexible additional data
    extra_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    # Relationships
    tasks: Mapped[list["Task"]] = relationship(
        "Task", back_populates="instance", passive_deletes=True
    )
    worktree: Mapped[Optional["Worktree"]] = relationship(
        "Worktree", back_populates="instance", uselist=False
    )
    configurations: Mapped[list["Configuration"]] = relationship(
        "Configuration", back_populates="instance"
    )

    def __repr__(self) -> str:
        return f"<Instance(id={self.id}, issue_id='{self.issue_id}', status='{self.status.value}')>"


class Task(Base):
    """Task model for work items."""

    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[TaskStatus] = mapped_column(
        SQLEnum(TaskStatus), nullable=False, default=TaskStatus.PENDING
    )
    priority: Mapped[TaskPriority] = mapped_column(
        SQLEnum(TaskPriority), nullable=False, default=TaskPriority.MEDIUM
    )

    # Foreign keys
    instance_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("instances.id", ondelete="SET NULL"), nullable=True
    )
    worktree_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("worktrees.id"), nullable=True
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now, onupdate=datetime.now
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)
    due_date: Mapped[datetime | None] = mapped_column(DateTime)

    # Task properties
    estimated_duration: Mapped[int | None] = mapped_column(Integer)  # minutes
    actual_duration: Mapped[int | None] = mapped_column(Integer)  # minutes

    # JSON fields
    requirements: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    results: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    extra_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    # Relationships
    instance: Mapped[Optional["Instance"]] = relationship(
        "Instance", back_populates="tasks"
    )
    worktree: Mapped[Optional["Worktree"]] = relationship(
        "Worktree", back_populates="tasks"
    )

    def __init__(self, **kwargs):
        # Set Python-level defaults for enum and other fields if not provided
        if "status" not in kwargs:
            kwargs["status"] = TaskStatus.PENDING
        if "priority" not in kwargs:
            kwargs["priority"] = TaskPriority.MEDIUM
        if "requirements" not in kwargs:
            kwargs["requirements"] = {}
        if "results" not in kwargs:
            kwargs["results"] = {}
        if "extra_metadata" not in kwargs:
            kwargs["extra_metadata"] = {}
        super().__init__(**kwargs)

    def __repr__(self) -> str:
        return (
            f"<Task(id={self.id}, title='{self.title}', status='{self.status.value}')>"
        )


class Worktree(Base):
    """Git worktree model."""

    __tablename__ = "worktrees"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    path: Mapped[str] = mapped_column(String(500), nullable=False, unique=True)
    branch_name: Mapped[str] = mapped_column(String(255), nullable=False)
    repository_url: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[WorktreeStatus] = mapped_column(
        SQLEnum(WorktreeStatus), nullable=False, default=WorktreeStatus.ACTIVE
    )

    # Foreign key
    instance_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("instances.id"), nullable=True
    )

    # Git information
    current_commit: Mapped[str | None] = mapped_column(String(40))
    has_uncommitted_changes: Mapped[bool] = mapped_column(Boolean, default=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now, onupdate=datetime.now
    )
    last_sync: Mapped[datetime | None] = mapped_column(DateTime)

    # JSON metadata
    git_config: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    extra_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    # Relationships
    instance: Mapped[Optional["Instance"]] = relationship(
        "Instance", back_populates="worktree"
    )
    tasks: Mapped[list["Task"]] = relationship("Task", back_populates="worktree")

    def __init__(self, **kwargs):
        # Set Python-level defaults for enum and other fields if not provided
        if "status" not in kwargs:
            kwargs["status"] = WorktreeStatus.ACTIVE
        if "has_uncommitted_changes" not in kwargs:
            kwargs["has_uncommitted_changes"] = False
        if "git_config" not in kwargs:
            kwargs["git_config"] = {}
        if "extra_metadata" not in kwargs:
            kwargs["extra_metadata"] = {}
        super().__init__(**kwargs)

    def __repr__(self) -> str:
        return (
            f"<Worktree(id={self.id}, name='{self.name}', branch='{self.branch_name}')>"
        )


class HealthCheck(Base):
    """Health check record model."""

    __tablename__ = "health_checks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    instance_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("instances.id"), nullable=False
    )
    overall_status: Mapped[HealthStatus] = mapped_column(
        SQLEnum(HealthStatus), nullable=False
    )
    check_results: Mapped[str] = mapped_column(Text, nullable=False)  # JSON string
    duration_ms: Mapped[float] = mapped_column(Integer, nullable=False)
    check_timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now, onupdate=datetime.now
    )

    # Relationships
    instance: Mapped["Instance"] = relationship("Instance")

    def __repr__(self) -> str:
        return f"<HealthCheck(id={self.id}, instance_id={self.instance_id}, status='{self.overall_status.value}')>"


class Configuration(Base):
    """Configuration settings model."""

    __tablename__ = "configurations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(255), nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    scope: Mapped[ConfigScope] = mapped_column(
        SQLEnum(ConfigScope), nullable=False, default=ConfigScope.GLOBAL
    )

    # Optional foreign keys for scoped configurations
    instance_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("instances.id"), nullable=True
    )

    # Configuration metadata
    description: Mapped[str | None] = mapped_column(Text)
    is_secret: Mapped[bool] = mapped_column(Boolean, default=False)
    is_readonly: Mapped[bool] = mapped_column(Boolean, default=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now, onupdate=datetime.now
    )

    # JSON metadata
    extra_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    # Relationships
    instance: Mapped[Optional["Instance"]] = relationship(
        "Instance", back_populates="configurations"
    )

    def __init__(self, **kwargs):
        # Set Python-level defaults for enum and other fields if not provided
        if "scope" not in kwargs:
            kwargs["scope"] = ConfigScope.GLOBAL
        if "is_secret" not in kwargs:
            kwargs["is_secret"] = False
        if "is_readonly" not in kwargs:
            kwargs["is_readonly"] = False
        if "extra_metadata" not in kwargs:
            kwargs["extra_metadata"] = {}
        super().__init__(**kwargs)

    def __repr__(self) -> str:
        return f"<Configuration(id={self.id}, key='{self.key}', scope='{self.scope.value}')>"


# Create indexes for performance

# Instance indexes
idx_instances_issue_id = Index("idx_instances_issue_id", Instance.issue_id)
idx_instances_status = Index("idx_instances_status", Instance.status)
idx_instances_created_at = Index("idx_instances_created_at", Instance.created_at)

# Task indexes
idx_tasks_status = Index("idx_tasks_status", Task.status)
idx_tasks_priority = Index("idx_tasks_priority", Task.priority)
idx_tasks_instance_id = Index("idx_tasks_instance_id", Task.instance_id)
idx_tasks_created_at = Index("idx_tasks_created_at", Task.created_at)
idx_tasks_due_date = Index("idx_tasks_due_date", Task.due_date)

# Worktree indexes
idx_worktrees_path = Index("idx_worktrees_path", Worktree.path)
idx_worktrees_branch = Index("idx_worktrees_branch", Worktree.branch_name)
idx_worktrees_status = Index("idx_worktrees_status", Worktree.status)

# Configuration indexes
idx_configurations_key_scope = Index(
    "idx_configurations_key_scope", Configuration.key, Configuration.scope
)
idx_configurations_instance_id = Index(
    "idx_configurations_instance_id", Configuration.instance_id
)

# Health check indexes
idx_health_checks_instance_id = Index(
    "idx_health_checks_instance_id", HealthCheck.instance_id
)
idx_health_checks_timestamp = Index(
    "idx_health_checks_timestamp", HealthCheck.check_timestamp
)
