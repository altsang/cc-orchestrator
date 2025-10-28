"""CRUD operations for database entities."""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .models import (
    ConfigScope,
    Configuration,
    HealthCheck,
    HealthStatus,
    Instance,
    InstanceStatus,
    Task,
    TaskPriority,
    TaskStatus,
    Worktree,
    WorktreeStatus,
)


class CRUDError(Exception):
    """Base exception for CRUD operations."""

    pass


class ValidationError(CRUDError):
    """Validation error for CRUD operations."""

    pass


class NotFoundError(CRUDError):
    """Entity not found error."""

    pass


class InstanceCRUD:
    """CRUD operations for Instance entities."""

    @staticmethod
    def create(
        session: Session,
        issue_id: str,
        workspace_path: str | None = None,
        branch_name: str | None = None,
        tmux_session: str | None = None,
        extra_metadata: dict[str, Any] | None = None,
    ) -> Instance:
        """Create a new instance.

        Args:
            session: Database session.
            issue_id: Unique issue identifier.
            workspace_path: Path to workspace.
            branch_name: Git branch name.
            tmux_session: Tmux session name.
            metadata: Additional metadata.

        Returns:
            Created instance.

        Raises:
            ValidationError: If validation fails.
        """
        if not issue_id or not issue_id.strip():
            raise ValidationError("Issue ID is required")

        instance = Instance(
            issue_id=issue_id.strip(),
            workspace_path=workspace_path,
            branch_name=branch_name,
            tmux_session=tmux_session,
            extra_metadata=extra_metadata or {},
        )

        try:
            session.add(instance)
            session.flush()
            return instance
        except IntegrityError as e:
            raise ValidationError(
                f"Instance with issue_id '{issue_id}' already exists"
            ) from e

    @staticmethod
    def get_by_id(session: Session, instance_id: int) -> Instance:
        """Get instance by ID.

        Args:
            session: Database session.
            instance_id: Instance ID.

        Returns:
            Instance object.

        Raises:
            NotFoundError: If instance not found.
        """
        instance = session.get(Instance, instance_id)
        if not instance:
            raise NotFoundError(f"Instance with ID {instance_id} not found")
        return instance

    @staticmethod
    def get_by_issue_id(session: Session, issue_id: str) -> Instance:
        """Get instance by issue ID.

        Args:
            session: Database session.
            issue_id: Issue identifier.

        Returns:
            Instance object.

        Raises:
            NotFoundError: If instance not found.
        """
        instance = session.query(Instance).filter(Instance.issue_id == issue_id).first()
        if not instance:
            raise NotFoundError(f"Instance with issue_id '{issue_id}' not found")
        return instance

    @staticmethod
    def list_all(
        session: Session,
        status: InstanceStatus | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[Instance]:
        """List instances with optional filtering.

        Args:
            session: Database session.
            status: Filter by status.
            limit: Maximum number of results.
            offset: Number of results to skip.

        Returns:
            List of instances.
        """
        query = session.query(Instance)

        if status:
            query = query.filter(Instance.status == status)

        query = query.order_by(Instance.created_at.desc())

        if offset:
            query = query.offset(offset)
        if limit:
            query = query.limit(limit)

        return query.all()

    @staticmethod
    def update(
        session: Session,
        instance_id: int,
        **kwargs: Any,
    ) -> Instance:
        """Update an instance.

        Args:
            session: Database session.
            instance_id: Instance ID.
            **kwargs: Fields to update.

        Returns:
            Updated instance.

        Raises:
            NotFoundError: If instance not found.
        """
        instance = InstanceCRUD.get_by_id(session, instance_id)

        # Update allowed fields
        allowed_fields = {
            "status",
            "workspace_path",
            "branch_name",
            "tmux_session",
            "process_id",
            "last_activity",
            "extra_metadata",
        }

        for field, value in kwargs.items():
            if field in allowed_fields:
                setattr(instance, field, value)

        instance.updated_at = datetime.now()
        session.flush()
        return instance

    @staticmethod
    def delete(session: Session, instance_id: int) -> bool:
        """Delete an instance.

        Args:
            session: Database session.
            instance_id: Instance ID.

        Returns:
            True if deleted successfully.

        Raises:
            NotFoundError: If instance not found.
        """
        instance = InstanceCRUD.get_by_id(session, instance_id)
        session.delete(instance)
        session.flush()
        return True


class TaskCRUD:
    """CRUD operations for Task entities."""

    @staticmethod
    def create(
        session: Session,
        title: str,
        description: str | None = None,
        priority: TaskPriority = TaskPriority.MEDIUM,
        instance_id: int | None = None,
        worktree_id: int | None = None,
        due_date: datetime | None = None,
        estimated_duration: int | None = None,
        requirements: dict[str, Any] | None = None,
        extra_metadata: dict[str, Any] | None = None,
    ) -> Task:
        """Create a new task.

        Args:
            session: Database session.
            title: Task title.
            description: Task description.
            priority: Task priority.
            instance_id: Associated instance ID.
            worktree_id: Associated worktree ID.
            due_date: Task due date.
            estimated_duration: Estimated duration in minutes.
            requirements: Task requirements.
            metadata: Additional metadata.

        Returns:
            Created task.

        Raises:
            ValidationError: If validation fails.
        """
        if not title or not title.strip():
            raise ValidationError("Task title is required")

        task = Task(
            title=title.strip(),
            description=description,
            priority=priority,
            instance_id=instance_id,
            worktree_id=worktree_id,
            due_date=due_date,
            estimated_duration=estimated_duration,
            requirements=requirements or {},
            extra_metadata=extra_metadata or {},
        )

        session.add(task)
        session.flush()
        return task

    @staticmethod
    def get_by_id(session: Session, task_id: int) -> Task:
        """Get task by ID.

        Args:
            session: Database session.
            task_id: Task ID.

        Returns:
            Task object.

        Raises:
            NotFoundError: If task not found.
        """
        task = session.get(Task, task_id)
        if not task:
            raise NotFoundError(f"Task with ID {task_id} not found")
        return task

    @staticmethod
    def list_by_instance(
        session: Session,
        instance_id: int,
        status: TaskStatus | None = None,
    ) -> list[Task]:
        """List tasks for an instance.

        Args:
            session: Database session.
            instance_id: Instance ID.
            status: Filter by status.

        Returns:
            List of tasks.
        """
        query = session.query(Task).filter(Task.instance_id == instance_id)

        if status:
            query = query.filter(Task.status == status)

        # Use CASE to order by priority value (4=URGENT, 3=HIGH, 2=MEDIUM, 1=LOW)
        from sqlalchemy import case

        priority_order = case(
            (Task.priority == TaskPriority.URGENT, 4),
            (Task.priority == TaskPriority.HIGH, 3),
            (Task.priority == TaskPriority.MEDIUM, 2),
            (Task.priority == TaskPriority.LOW, 1),
            else_=0,
        )
        return query.order_by(priority_order.desc(), Task.created_at.asc()).all()

    @staticmethod
    def list_pending(session: Session, limit: int | None = None) -> list[Task]:
        """List pending tasks across all instances.

        Args:
            session: Database session.
            limit: Maximum number of results.

        Returns:
            List of pending tasks.
        """
        query = session.query(Task).filter(Task.status == TaskStatus.PENDING)
        # Use CASE to order by priority value (4=URGENT, 3=HIGH, 2=MEDIUM, 1=LOW)
        from sqlalchemy import case

        priority_order = case(
            (Task.priority == TaskPriority.URGENT, 4),
            (Task.priority == TaskPriority.HIGH, 3),
            (Task.priority == TaskPriority.MEDIUM, 2),
            (Task.priority == TaskPriority.LOW, 1),
            else_=0,
        )
        query = query.order_by(priority_order.desc(), Task.created_at.asc())

        if limit:
            query = query.limit(limit)

        return query.all()

    @staticmethod
    def update_status(
        session: Session,
        task_id: int,
        status: TaskStatus,
    ) -> Task:
        """Update task status.

        Args:
            session: Database session.
            task_id: Task ID.
            status: New status.

        Returns:
            Updated task.
        """
        task = TaskCRUD.get_by_id(session, task_id)
        task.status = status

        # Update timestamps based on status

        now = datetime.now(UTC)
        if status == TaskStatus.IN_PROGRESS and not task.started_at:
            task.started_at = now
        elif status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
            if not task.completed_at:
                task.completed_at = now
            # Calculate actual duration if we have start time
            if task.started_at:
                # Handle both timezone-aware and timezone-naive started_at
                started_at = task.started_at
                if started_at.tzinfo is None:
                    # If started_at is timezone-naive, assume it's UTC
                    started_at = started_at.replace(tzinfo=UTC)
                duration = (now - started_at).total_seconds() / 60
                task.actual_duration = int(duration)

        task.updated_at = now
        session.flush()
        return task

    @staticmethod
    def update(
        session: Session,
        task_id: int,
        **kwargs: Any,
    ) -> Task:
        """Update a task.

        Args:
            session: Database session.
            task_id: Task ID.
            **kwargs: Fields to update.

        Returns:
            Updated task.

        Raises:
            NotFoundError: If task not found.
        """
        task = TaskCRUD.get_by_id(session, task_id)

        # Update allowed fields
        allowed_fields = {
            "title",
            "description",
            "priority",
            "instance_id",
            "worktree_id",
            "due_date",
            "estimated_duration",
            "actual_duration",
            "requirements",
            "results",
            "extra_metadata",
        }

        for field, value in kwargs.items():
            if field in allowed_fields:
                setattr(task, field, value)

        from datetime import datetime

        task.updated_at = datetime.now(UTC)
        session.flush()
        return task


class WorktreeCRUD:
    """CRUD operations for Worktree entities."""

    @staticmethod
    def create(
        session: Session,
        name: str,
        path: str,
        branch_name: str,
        repository_url: str | None = None,
        instance_id: int | None = None,
        git_config: dict[str, Any] | None = None,
        extra_metadata: dict[str, Any] | None = None,
    ) -> Worktree:
        """Create a new worktree.

        Args:
            session: Database session.
            name: Worktree name.
            path: Filesystem path.
            branch_name: Git branch name.
            repository_url: Repository URL.
            instance_id: Associated instance ID.
            git_config: Git configuration.
            metadata: Additional metadata.

        Returns:
            Created worktree.

        Raises:
            ValidationError: If validation fails.
        """
        if not name or not name.strip():
            raise ValidationError("Worktree name is required")
        if not path or not path.strip():
            raise ValidationError("Worktree path is required")
        if not branch_name or not branch_name.strip():
            raise ValidationError("Branch name is required")

        worktree = Worktree(
            name=name.strip(),
            path=path.strip(),
            branch_name=branch_name.strip(),
            repository_url=repository_url,
            instance_id=instance_id,
            git_config=git_config or {},
            extra_metadata=extra_metadata or {},
        )

        try:
            session.add(worktree)
            session.flush()
            return worktree
        except IntegrityError as e:
            raise ValidationError(f"Worktree with path '{path}' already exists") from e

    @staticmethod
    def get_by_path(session: Session, path: str) -> Worktree:
        """Get worktree by path.

        Args:
            session: Database session.
            path: Worktree path.

        Returns:
            Worktree object.

        Raises:
            NotFoundError: If worktree not found.
        """
        worktree = session.query(Worktree).filter(Worktree.path == path).first()
        if not worktree:
            raise NotFoundError(f"Worktree with path '{path}' not found")
        return worktree

    @staticmethod
    def get_by_name(session: Session, name: str) -> Worktree | None:
        """Get worktree by name.

        Args:
            session: Database session.
            name: Worktree name.

        Returns:
            Worktree object or None if not found.
        """
        worktree = session.query(Worktree).filter(Worktree.name == name).first()
        return worktree

    @staticmethod
    def get_by_id(session: Session, worktree_id: int) -> Worktree:
        """Get worktree by ID.

        Args:
            session: Database session.
            worktree_id: Worktree ID.

        Returns:
            Worktree object.

        Raises:
            NotFoundError: If worktree not found.
        """
        worktree = session.get(Worktree, worktree_id)
        if not worktree:
            raise NotFoundError(f"Worktree with ID {worktree_id} not found")
        return worktree

    @staticmethod
    def list_all(session: Session) -> list[Worktree]:
        """List all worktrees.

        Args:
            session: Database session.

        Returns:
            List of all worktrees.
        """
        return session.query(Worktree).order_by(Worktree.created_at).all()

    @staticmethod
    def list_by_status(session: Session, status: WorktreeStatus) -> list[Worktree]:
        """List worktrees by status.

        Args:
            session: Database session.
            status: Worktree status to filter by.

        Returns:
            List of worktrees with the specified status.
        """
        return (
            session.query(Worktree)
            .filter(Worktree.status == status)
            .order_by(Worktree.created_at)
            .all()
        )

    @staticmethod
    def update_status(
        session: Session,
        worktree_id: int,
        status: WorktreeStatus,
        current_commit: str | None = None,
        has_uncommitted_changes: bool | None = None,
    ) -> Worktree:
        """Update worktree status and git information.

        Args:
            session: Database session.
            worktree_id: Worktree ID.
            status: New status.
            current_commit: Current commit SHA.
            has_uncommitted_changes: Whether there are uncommitted changes.

        Returns:
            Updated worktree.

        Raises:
            NotFoundError: If worktree not found.
        """
        worktree = WorktreeCRUD.get_by_id(session, worktree_id)

        worktree.status = status
        if current_commit is not None:
            worktree.current_commit = current_commit
        if has_uncommitted_changes is not None:
            worktree.has_uncommitted_changes = has_uncommitted_changes

        # Update last_sync timestamp
        from datetime import datetime

        worktree.last_sync = datetime.now()

        session.flush()
        return worktree

    @staticmethod
    def delete(session: Session, worktree_id: int) -> bool:
        """Delete a worktree record.

        Args:
            session: Database session.
            worktree_id: Worktree ID.

        Returns:
            True if deleted successfully.

        Raises:
            NotFoundError: If worktree not found.
        """
        worktree = WorktreeCRUD.get_by_id(session, worktree_id)
        session.delete(worktree)
        session.flush()
        return True


class ConfigurationCRUD:
    """CRUD operations for Configuration entities."""

    @staticmethod
    def create(
        session: Session,
        key: str,
        value: str,
        scope: ConfigScope = ConfigScope.GLOBAL,
        instance_id: int | None = None,
        description: str | None = None,
        is_secret: bool = False,
        extra_metadata: dict[str, Any] | None = None,
    ) -> Configuration:
        """Create a new configuration.

        Args:
            session: Database session.
            key: Configuration key.
            value: Configuration value.
            scope: Configuration scope.
            instance_id: Instance ID for instance-scoped configs.
            description: Configuration description.
            is_secret: Whether this is a secret value.
            metadata: Additional metadata.

        Returns:
            Created configuration.

        Raises:
            ValidationError: If validation fails.
        """
        if not key or not key.strip():
            raise ValidationError("Configuration key is required")

        config = Configuration(
            key=key.strip(),
            value=value,
            scope=scope,
            instance_id=instance_id,
            description=description,
            is_secret=is_secret,
            extra_metadata=extra_metadata or {},
        )

        session.add(config)
        session.flush()
        return config

    @staticmethod
    def get_value(
        session: Session,
        key: str,
        scope: ConfigScope = ConfigScope.GLOBAL,
        instance_id: int | None = None,
    ) -> str | None:
        """Get configuration value with scope hierarchy.

        Args:
            session: Database session.
            key: Configuration key.
            scope: Preferred scope.
            instance_id: Instance ID for instance-scoped lookup.

        Returns:
            Configuration value or None if not found.
        """
        # Define scope hierarchy (most specific first)
        scopes_to_check: list[tuple[ConfigScope, int | None]] = []

        if scope == ConfigScope.INSTANCE and instance_id:
            scopes_to_check.append((ConfigScope.INSTANCE, instance_id))
        if scope in (ConfigScope.INSTANCE, ConfigScope.PROJECT):
            scopes_to_check.append((ConfigScope.PROJECT, None))
        if scope in (ConfigScope.INSTANCE, ConfigScope.PROJECT, ConfigScope.USER):
            scopes_to_check.append((ConfigScope.USER, None))
        scopes_to_check.append((ConfigScope.GLOBAL, None))

        for check_scope, check_instance_id in scopes_to_check:
            query = session.query(Configuration).filter(
                Configuration.key == key,
                Configuration.scope == check_scope,
            )

            if check_instance_id:
                query = query.filter(Configuration.instance_id == check_instance_id)
            else:
                query = query.filter(Configuration.instance_id.is_(None))

            config = query.first()
            if config:
                return config.value

        return None

    @staticmethod
    def get_by_key_scope(
        session: Session,
        key: str,
        scope: ConfigScope = ConfigScope.GLOBAL,
        instance_id: int | None = None,
    ) -> Configuration | None:
        """Get configuration object by key and scope with hierarchy.

        Args:
            session: Database session.
            key: Configuration key.
            scope: Preferred scope.
            instance_id: Instance ID for instance-scoped lookup.

        Returns:
            Configuration object or None if not found.
        """
        # Define scope hierarchy (most specific first)
        scopes_to_check: list[tuple[ConfigScope, int | None]] = []

        if scope == ConfigScope.INSTANCE and instance_id:
            scopes_to_check.append((ConfigScope.INSTANCE, instance_id))
        if scope in (ConfigScope.INSTANCE, ConfigScope.PROJECT):
            scopes_to_check.append((ConfigScope.PROJECT, None))
        if scope in (ConfigScope.INSTANCE, ConfigScope.PROJECT, ConfigScope.USER):
            scopes_to_check.append((ConfigScope.USER, None))
        scopes_to_check.append((ConfigScope.GLOBAL, None))

        for check_scope, check_instance_id in scopes_to_check:
            query = session.query(Configuration).filter(
                Configuration.key == key,
                Configuration.scope == check_scope,
            )

            if check_instance_id:
                query = query.filter(Configuration.instance_id == check_instance_id)
            else:
                query = query.filter(Configuration.instance_id.is_(None))

            config = query.first()
            if config:
                return config

        return None

    @staticmethod
    def get_exact_by_key_scope(
        session: Session,
        key: str,
        scope: ConfigScope,
        instance_id: int | None = None,
    ) -> Configuration | None:
        """Get configuration by exact key and scope match (no hierarchy).

        Args:
            session: Database session.
            key: Configuration key.
            scope: Exact scope to match.
            instance_id: Instance ID for instance-scoped configurations.

        Returns:
            Configuration object or None if not found.
        """
        query = session.query(Configuration).filter(
            Configuration.key == key,
            Configuration.scope == scope,
        )

        if scope == ConfigScope.INSTANCE and instance_id:
            query = query.filter(Configuration.instance_id == instance_id)
        elif scope != ConfigScope.INSTANCE:
            query = query.filter(Configuration.instance_id.is_(None))

        return query.first()


class HealthCheckCRUD:
    """CRUD operations for HealthCheck entities."""

    @staticmethod
    def create(
        session: Session,
        instance_id: int,
        overall_status: HealthStatus,
        check_results: str,
        duration_ms: float,
        check_timestamp: datetime,
    ) -> HealthCheck:
        """Create a new health check record.

        Args:
            session: Database session.
            instance_id: Instance ID.
            overall_status: Overall health status.
            check_results: JSON string of check results.
            duration_ms: Duration of check in milliseconds.
            check_timestamp: Timestamp of the check.

        Returns:
            Created health check.
        """
        health_check = HealthCheck(
            instance_id=instance_id,
            overall_status=overall_status,
            check_results=check_results,
            duration_ms=duration_ms,
            check_timestamp=check_timestamp,
        )

        session.add(health_check)
        session.flush()
        return health_check

    @staticmethod
    def list_by_instance(
        session: Session,
        instance_id: int,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[HealthCheck]:
        """List health checks for an instance.

        Args:
            session: Database session.
            instance_id: Instance ID.
            limit: Maximum number of results.
            offset: Number of results to skip.

        Returns:
            List of health checks.
        """
        query = session.query(HealthCheck).filter(
            HealthCheck.instance_id == instance_id
        )
        query = query.order_by(HealthCheck.check_timestamp.desc())

        if offset:
            query = query.offset(offset)
        if limit:
            query = query.limit(limit)

        return query.all()

    @staticmethod
    def count_by_instance(session: Session, instance_id: int) -> int:
        """Count health checks for an instance.

        Args:
            session: Database session.
            instance_id: Instance ID.

        Returns:
            Total count of health checks.
        """
        return (
            session.query(HealthCheck)
            .filter(HealthCheck.instance_id == instance_id)
            .count()
        )
