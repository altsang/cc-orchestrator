"""CRUD operations for database entities."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, or_, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from .models import (
    Configuration,
    ConfigScope,
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
        workspace_path: Optional[str] = None,
        branch_name: Optional[str] = None,
        tmux_session: Optional[str] = None,
        extra_metadata: Optional[Dict[str, Any]] = None,
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
            raise ValidationError(f"Instance with issue_id '{issue_id}' already exists") from e
    
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
        status: Optional[InstanceStatus] = None,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> List[Instance]:
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
            'status', 'workspace_path', 'branch_name', 'tmux_session',
            'process_id', 'last_activity', 'extra_metadata'
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
        description: Optional[str] = None,
        priority: TaskPriority = TaskPriority.MEDIUM,
        instance_id: Optional[int] = None,
        worktree_id: Optional[int] = None,
        due_date: Optional[datetime] = None,
        estimated_duration: Optional[int] = None,
        requirements: Optional[Dict[str, Any]] = None,
        extra_metadata: Optional[Dict[str, Any]] = None,
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
        status: Optional[TaskStatus] = None,
    ) -> List[Task]:
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
            else_=0
        )
        return query.order_by(priority_order.desc(), Task.created_at.asc()).all()
    
    @staticmethod
    def list_pending(session: Session, limit: Optional[int] = None) -> List[Task]:
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
            else_=0
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
        now = datetime.now()
        if status == TaskStatus.IN_PROGRESS and not task.started_at:
            task.started_at = now
        elif status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
            if not task.completed_at:
                task.completed_at = now
            # Calculate actual duration if we have start time
            if task.started_at:
                duration = (now - task.started_at).total_seconds() / 60
                task.actual_duration = int(duration)
        
        task.updated_at = now
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
        repository_url: Optional[str] = None,
        instance_id: Optional[int] = None,
        git_config: Optional[Dict[str, Any]] = None,
        extra_metadata: Optional[Dict[str, Any]] = None,
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


class ConfigurationCRUD:
    """CRUD operations for Configuration entities."""
    
    @staticmethod
    def create(
        session: Session,
        key: str,
        value: str,
        scope: ConfigScope = ConfigScope.GLOBAL,
        instance_id: Optional[int] = None,
        description: Optional[str] = None,
        is_secret: bool = False,
        extra_metadata: Optional[Dict[str, Any]] = None,
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
        instance_id: Optional[int] = None,
    ) -> Optional[str]:
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
        scopes_to_check = []
        
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