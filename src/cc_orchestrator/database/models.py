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


class Base(DeclarativeBase):
    """Base class for all database models."""

    pass


class InstanceStatus(Enum):
    """Status of a Claude Code instance."""

    INITIALIZING = "initializing"
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"


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


class HealthStatus(Enum):
    """Health status of an instance."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class AlertLevel(Enum):
    """Alert severity levels."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


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

    # Health monitoring fields
    health_status: Mapped[HealthStatus] = mapped_column(
        SQLEnum(HealthStatus), nullable=False, default=HealthStatus.UNKNOWN
    )
    last_health_check: Mapped[datetime | None] = mapped_column(DateTime)
    health_check_count: Mapped[int] = mapped_column(Integer, default=0)
    healthy_check_count: Mapped[int] = mapped_column(Integer, default=0)
    last_recovery_attempt: Mapped[datetime | None] = mapped_column(DateTime)
    recovery_attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    health_check_details: Mapped[str | None] = mapped_column(Text)

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
        "Task", back_populates="instance", cascade="all, delete-orphan"
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
        Integer, ForeignKey("instances.id"), nullable=True
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

    def __repr__(self) -> str:
        return (
            f"<Worktree(id={self.id}, name='{self.name}', branch='{self.branch_name}')>"
        )


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

    def __repr__(self) -> str:
        return f"<Configuration(id={self.id}, key='{self.key}', scope='{self.scope.value}')>"


# Create indexes for performance

# Instance indexes
Index("idx_instances_issue_id", Instance.issue_id)
Index("idx_instances_status", Instance.status)
Index("idx_instances_created_at", Instance.created_at)

# Task indexes
Index("idx_tasks_status", Task.status)
Index("idx_tasks_priority", Task.priority)
Index("idx_tasks_instance_id", Task.instance_id)
Index("idx_tasks_created_at", Task.created_at)
Index("idx_tasks_due_date", Task.due_date)

# Worktree indexes
Index("idx_worktrees_path", Worktree.path)
Index("idx_worktrees_branch", Worktree.branch_name)
Index("idx_worktrees_status", Worktree.status)

# Configuration indexes
Index("idx_configurations_key_scope", Configuration.key, Configuration.scope)
Index("idx_configurations_instance_id", Configuration.instance_id)


class HealthCheck(Base):
    """Health check history model."""

    __tablename__ = "health_checks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    instance_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("instances.id"), nullable=False
    )
    check_timestamp: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now
    )
    overall_status: Mapped[HealthStatus] = mapped_column(
        SQLEnum(HealthStatus), nullable=False
    )
    check_results: Mapped[str] = mapped_column(Text, nullable=False)
    duration_ms: Mapped[float] = mapped_column(Integer, default=0)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now
    )

    # Relationships
    instance: Mapped["Instance"] = relationship("Instance")

    def __repr__(self) -> str:
        return f"<HealthCheck(id={self.id}, instance_id={self.instance_id}, status='{self.overall_status.value}')>"


class RecoveryAttempt(Base):
    """Recovery attempt history model."""

    __tablename__ = "recovery_attempts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    instance_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("instances.id"), nullable=False
    )
    attempt_timestamp: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now
    )
    strategy: Mapped[str] = mapped_column(String(50), nullable=False)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    error_message: Mapped[str | None] = mapped_column(Text)
    duration_seconds: Mapped[float] = mapped_column(Integer, default=0)
    details: Mapped[str | None] = mapped_column(Text)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now
    )

    # Relationships
    instance: Mapped["Instance"] = relationship("Instance")

    def __repr__(self) -> str:
        return f"<RecoveryAttempt(id={self.id}, instance_id={self.instance_id}, strategy='{self.strategy}', success={self.success})>"


class Alert(Base):
    """Alert history model."""

    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    instance_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("instances.id"), nullable=False
    )
    alert_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    level: Mapped[AlertLevel] = mapped_column(SQLEnum(AlertLevel), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[str | None] = mapped_column(Text)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now
    )

    # Relationships
    instance: Mapped["Instance"] = relationship("Instance")

    def __repr__(self) -> str:
        return f"<Alert(id={self.id}, instance_id={self.instance_id}, level='{self.level.value}', alert_id='{self.alert_id}')>"


# Health monitoring indexes
Index("idx_instances_health_status", Instance.health_status)
Index("idx_instances_last_health_check", Instance.last_health_check)

# Health check indexes
Index("idx_health_checks_instance_id", HealthCheck.instance_id)
Index("idx_health_checks_timestamp", HealthCheck.check_timestamp)
Index("idx_health_checks_status", HealthCheck.overall_status)

# Recovery attempt indexes
Index("idx_recovery_attempts_instance_id", RecoveryAttempt.instance_id)
Index("idx_recovery_attempts_timestamp", RecoveryAttempt.attempt_timestamp)
Index("idx_recovery_attempts_success", RecoveryAttempt.success)

# Alert indexes
Index("idx_alerts_instance_id", Alert.instance_id)
Index("idx_alerts_level", Alert.level)
Index("idx_alerts_timestamp", Alert.timestamp)
Index("idx_alerts_alert_id", Alert.alert_id)
