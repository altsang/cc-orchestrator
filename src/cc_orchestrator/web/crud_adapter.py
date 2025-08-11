"""
Async CRUD adapter for FastAPI endpoints.

This module provides an async wrapper around the existing synchronous CRUD operations
to make them compatible with FastAPI's async model.
"""

import asyncio
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from ..database.crud import (
    ConfigurationCRUD,
    HealthCheckCRUD,
    InstanceCRUD,
    TaskCRUD,
    WorktreeCRUD,
)
from ..database.models import (
    Configuration,
    HealthCheck,
    HealthStatus,
    Instance,
    Task,
    Worktree,
)


# Placeholder classes for models that don't exist yet
class Alert:
    """Placeholder Alert model."""

    def __init__(self, **kwargs: Any) -> None:
        for key, value in kwargs.items():
            setattr(self, key, value)
        self.created_at = datetime.now()
        # Ensure required attributes exist
        if not hasattr(self, "id"):
            self.id = kwargs.get("id", 1)
        if not hasattr(self, "level"):
            self.level = kwargs.get("level", "info")


class RecoveryAttempt:
    """Placeholder RecoveryAttempt model."""

    def __init__(self, **kwargs: Any) -> None:
        for key, value in kwargs.items():
            setattr(self, key, value)
        self.created_at = datetime.now()
        # Ensure id attribute exists
        if not hasattr(self, "id"):
            self.id = kwargs.get("id", 1)


class CRUDBase:
    """Async CRUD operations adapter for FastAPI."""

    def __init__(self, session: Session):
        """Initialize with database session."""
        self.session = session

    # Instance operations
    async def list_instances(
        self, offset: int = 0, limit: int = 20, filters: dict[str, Any] | None = None
    ) -> tuple[list[Instance], int]:
        """List instances with pagination and filtering."""

        def _list_instances() -> tuple[list[Instance], int]:
            # Convert filters to appropriate parameters for InstanceCRUD.list_all
            status = None
            if filters and "status" in filters:
                from ..database.models import InstanceStatus

                # Convert string status to enum if needed
                status_value = filters["status"]
                if isinstance(status_value, str):
                    status = InstanceStatus(status_value)
                else:
                    status = status_value

            instances = InstanceCRUD.list_all(
                self.session, status=status, limit=limit, offset=offset
            )

            # Get total count for pagination
            total_count = len(InstanceCRUD.list_all(self.session, status=status))

            return instances, total_count

        return await asyncio.to_thread(_list_instances)

    async def create_instance(self, instance_data: dict[str, Any]) -> Instance:
        """Create a new instance."""

        def _create_instance() -> Instance:
            # Create the instance first
            instance = InstanceCRUD.create(
                self.session,
                issue_id=instance_data["issue_id"],
                workspace_path=instance_data.get("workspace_path"),
                branch_name=instance_data.get("branch_name"),
                tmux_session=instance_data.get("tmux_session"),
                extra_metadata=instance_data.get("extra_metadata", {}),
            )

            # If status is provided, update it
            if "status" in instance_data:
                status_value = instance_data["status"]
                if isinstance(status_value, str):
                    from ..database.models import InstanceStatus

                    status = InstanceStatus(status_value.lower())
                else:
                    status = status_value
                # Update the instance status
                instance.status = status
                self.session.flush()

            return instance

        return await asyncio.to_thread(_create_instance)

    async def get_instance(self, instance_id: int) -> Instance | None:
        """Get instance by ID."""

        def _get_instance() -> Instance | None:
            try:
                # Check if session is still valid
                if hasattr(self.session, "is_active") and not self.session.is_active:
                    return None
                return InstanceCRUD.get_by_id(self.session, instance_id)
            except Exception:
                # Return None for any exception (including NotFoundError)
                return None

        return await asyncio.to_thread(_get_instance)

    async def get_instance_by_issue_id(self, issue_id: str) -> Instance | None:
        """Get instance by issue ID."""

        def _get_instance_by_issue_id() -> Instance | None:
            try:
                return InstanceCRUD.get_by_issue_id(self.session, issue_id)
            except Exception:
                return None

        return await asyncio.to_thread(_get_instance_by_issue_id)

    async def update_instance(
        self, instance_id: int, update_data: dict[str, Any]
    ) -> Instance:
        """Update an instance."""

        def _update_instance() -> Instance:
            # Convert status string to enum if needed
            if "status" in update_data:
                status_value = update_data["status"]
                if isinstance(status_value, str):
                    from ..database.models import InstanceStatus

                    # The enum values are lowercase, so convert to lowercase
                    status_lower = status_value.lower()
                    update_data["status"] = InstanceStatus(status_lower)

            return InstanceCRUD.update(self.session, instance_id, **update_data)

        return await asyncio.to_thread(_update_instance)

    async def delete_instance(self, instance_id: int) -> None:
        """Delete an instance."""

        def _delete_instance() -> None:
            InstanceCRUD.delete(self.session, instance_id)

        await asyncio.to_thread(_delete_instance)

    # Task operations
    async def list_tasks(
        self, offset: int = 0, limit: int = 20, filters: dict[str, Any] | None = None
    ) -> tuple[list[Task], int]:
        """List tasks with pagination and filtering."""

        def _list_tasks() -> tuple[list[Task], int]:
            # Handle instance_id filter for list_by_instance
            if filters and "instance_id" in filters:
                instance_id = filters["instance_id"]
                status_filter = None
                if "status" in filters:
                    from ..database.models import TaskStatus

                    status_value = filters["status"]
                    if isinstance(status_value, str):
                        status_filter = TaskStatus(status_value)
                    else:
                        status_filter = status_value

                tasks = TaskCRUD.list_by_instance(
                    self.session, instance_id, status=status_filter
                )

                # Apply pagination manually
                total_count = len(tasks)
                start = offset
                end = offset + limit
                paginated_tasks = tasks[start:end]

                return paginated_tasks, total_count
            else:
                # For general task listing, use list_pending
                tasks = TaskCRUD.list_pending(self.session, limit=limit)
                # Skip offset manually since the CRUD doesn't support it
                if offset > 0:
                    tasks = tasks[offset:]
                total_count = len(TaskCRUD.list_pending(self.session))
                return tasks, total_count

        return await asyncio.to_thread(_list_tasks)

    async def create_task(self, task_data: dict[str, Any]) -> Task:
        """Create a new task."""

        def _create_task() -> Task:
            # Convert priority to enum if needed
            priority = task_data.get("priority", 2)  # Default to MEDIUM (2)
            if isinstance(priority, str):
                from ..database.models import TaskPriority

                priority = TaskPriority(priority.upper())
            elif isinstance(priority, int):
                from ..database.models import TaskPriority

                # Map integer values to enum
                priority_map = {
                    1: TaskPriority.LOW,
                    2: TaskPriority.MEDIUM,
                    3: TaskPriority.HIGH,
                    4: TaskPriority.URGENT,
                }
                priority = priority_map.get(priority, TaskPriority.MEDIUM)

            return TaskCRUD.create(
                self.session,
                title=task_data["title"],
                description=task_data.get("description"),
                priority=priority,
                instance_id=task_data.get("instance_id"),
                worktree_id=task_data.get("worktree_id"),
                due_date=task_data.get("due_date"),
                estimated_duration=task_data.get("estimated_duration"),
                requirements=task_data.get("requirements", {}),
                extra_metadata=task_data.get("extra_metadata", {}),
            )

        return await asyncio.to_thread(_create_task)

    async def get_task(self, task_id: int) -> Task | None:
        """Get task by ID."""

        def _get_task() -> Task | None:
            try:
                return TaskCRUD.get_by_id(self.session, task_id)
            except Exception:
                return None

        return await asyncio.to_thread(_get_task)

    async def update_task(self, task_id: int, update_data: dict[str, Any]) -> Task:
        """Update a task."""

        def _update_task() -> Task:
            # Handle status updates with special logic for status transitions
            if "status" in update_data:
                status_value = update_data["status"]
                if isinstance(status_value, str):
                    from ..database.models import TaskStatus

                    status = TaskStatus(status_value.upper())
                else:
                    status = status_value
                # Use update_status for status changes as it handles timestamps
                return TaskCRUD.update_status(self.session, task_id, status)
            else:
                # Use general update for other fields like instance_id
                return TaskCRUD.update(self.session, task_id, **update_data)

        return await asyncio.to_thread(_update_task)

    async def delete_task(self, task_id: int) -> None:
        """Delete a task."""

        def _delete_task() -> None:
            # TaskCRUD doesn't have a delete method, so we'll need to implement it
            # For now, just validate the task exists
            TaskCRUD.get_by_id(self.session, task_id)
            # TODO: Implement task deletion in TaskCRUD

        await asyncio.to_thread(_delete_task)

    # Worktree operations
    async def list_worktrees(
        self, offset: int = 0, limit: int = 20, filters: dict[str, Any] | None = None
    ) -> tuple[list[Worktree], int]:
        """List worktrees with pagination and filtering."""

        def _list_worktrees() -> tuple[list[Worktree], int]:
            # Handle status filter
            if filters and "status" in filters:
                from ..database.models import WorktreeStatus

                status_value = filters["status"]
                if isinstance(status_value, str):
                    status = WorktreeStatus(status_value)
                else:
                    status = status_value
                worktrees = WorktreeCRUD.list_by_status(self.session, status)
            else:
                worktrees = WorktreeCRUD.list_all(self.session)

            # Apply pagination manually
            total_count = len(worktrees)
            start = offset
            end = offset + limit
            paginated_worktrees = worktrees[start:end]

            return paginated_worktrees, total_count

        return await asyncio.to_thread(_list_worktrees)

    async def create_worktree(self, worktree_data: dict[str, Any]) -> Worktree:
        """Create a new worktree."""

        def _create_worktree() -> Worktree:
            return WorktreeCRUD.create(
                self.session,
                name=worktree_data["name"],
                path=worktree_data["path"],
                branch_name=worktree_data["branch_name"],
                repository_url=worktree_data.get("repository_url"),
                instance_id=worktree_data.get("instance_id"),
                git_config=worktree_data.get("git_config", {}),
                extra_metadata=worktree_data.get("extra_metadata", {}),
            )

        return await asyncio.to_thread(_create_worktree)

    async def get_worktree(self, worktree_id: int) -> Worktree | None:
        """Get worktree by ID."""

        def _get_worktree() -> Worktree | None:
            try:
                return WorktreeCRUD.get_by_id(self.session, worktree_id)
            except Exception:
                return None

        return await asyncio.to_thread(_get_worktree)

    async def get_worktree_by_path(self, path: str) -> Worktree | None:
        """Get worktree by path."""

        def _get_worktree_by_path() -> Worktree | None:
            try:
                return WorktreeCRUD.get_by_path(self.session, path)
            except Exception:
                return None

        return await asyncio.to_thread(_get_worktree_by_path)

    async def update_worktree(
        self, worktree_id: int, update_data: dict[str, Any]
    ) -> Worktree:
        """Update a worktree."""

        def _update_worktree() -> Worktree:
            # Check if this is a status update with git info or just git info update
            if (
                "status" in update_data
                or "current_commit" in update_data
                or "has_uncommitted_changes" in update_data
            ):
                # Get current worktree to preserve existing status if not provided
                worktree = WorktreeCRUD.get_by_id(self.session, worktree_id)
                status = worktree.status

                # Update status if provided
                if "status" in update_data:
                    status_value = update_data["status"]
                    if isinstance(status_value, str):
                        from ..database.models import WorktreeStatus

                        status = WorktreeStatus(status_value)
                    else:
                        status = status_value

                return WorktreeCRUD.update_status(
                    self.session,
                    worktree_id,
                    status,
                    current_commit=update_data.get("current_commit"),
                    has_uncommitted_changes=update_data.get("has_uncommitted_changes"),
                )
            else:
                # For other updates, just return the existing worktree
                # TODO: Implement general worktree update in WorktreeCRUD
                return WorktreeCRUD.get_by_id(self.session, worktree_id)

        return await asyncio.to_thread(_update_worktree)

    async def delete_worktree(self, worktree_id: int) -> None:
        """Delete a worktree."""

        def _delete_worktree() -> None:
            WorktreeCRUD.delete(self.session, worktree_id)

        await asyncio.to_thread(_delete_worktree)

    # Configuration operations
    async def list_configurations(
        self, offset: int = 0, limit: int = 20, filters: dict[str, Any] | None = None
    ) -> tuple[list[Configuration], int]:
        """List configurations with pagination and filtering."""

        def _list_configurations() -> tuple[list[Configuration], int]:
            # ConfigurationCRUD doesn't have a list method, so we'll return empty for now
            # TODO: Implement list_all method in ConfigurationCRUD
            return [], 0

        return await asyncio.to_thread(_list_configurations)

    async def create_configuration(self, config_data: dict[str, Any]) -> Configuration:
        """Create a new configuration."""

        def _create_configuration() -> Configuration:
            # Convert scope string to enum if needed
            scope = config_data.get("scope", "global")
            if isinstance(scope, str):
                from ..database.models import ConfigScope

                if scope.lower() == "global":
                    scope = ConfigScope.GLOBAL
                elif scope.lower() == "user":
                    scope = ConfigScope.USER
                elif scope.lower() == "project":
                    scope = ConfigScope.PROJECT
                elif scope.lower() == "instance":
                    scope = ConfigScope.INSTANCE
                else:
                    scope = ConfigScope.GLOBAL

            return ConfigurationCRUD.create(
                self.session,
                key=config_data["key"],
                value=config_data["value"],
                scope=scope,
                instance_id=config_data.get("instance_id"),
                description=config_data.get("description"),
                is_secret=config_data.get("is_secret", False),
                extra_metadata=config_data.get("extra_metadata", {}),
            )

        return await asyncio.to_thread(_create_configuration)

    async def get_configuration(self, config_id: int) -> Configuration | None:
        """Get configuration by ID."""

        def _get_configuration() -> Configuration | None:
            # ConfigurationCRUD doesn't have get_by_id, so we'll return None for now
            # TODO: Implement get_by_id method in ConfigurationCRUD
            return None

        return await asyncio.to_thread(_get_configuration)

    async def get_configuration_by_key_scope(
        self, key: str, scope: Any, instance_id: int | None = None
    ) -> Configuration | None:
        """Get configuration by key and scope."""

        def _get_configuration_by_key_scope() -> Configuration | None:
            # Convert scope to enum if needed
            if isinstance(scope, str):
                from ..database.models import ConfigScope

                if scope.lower() == "global":
                    scope_enum = ConfigScope.GLOBAL
                elif scope.lower() == "user":
                    scope_enum = ConfigScope.USER
                elif scope.lower() == "project":
                    scope_enum = ConfigScope.PROJECT
                elif scope.lower() == "instance":
                    scope_enum = ConfigScope.INSTANCE
                else:
                    scope_enum = ConfigScope.GLOBAL
            else:
                scope_enum = scope

            # Use the new get_by_key_scope method to return the full Configuration object
            try:
                return ConfigurationCRUD.get_by_key_scope(
                    self.session, key, scope_enum, instance_id
                )
            except Exception:
                return None

        return await asyncio.to_thread(_get_configuration_by_key_scope)

    async def get_exact_configuration_by_key_scope(
        self, key: str, scope: Any, instance_id: int | None = None
    ) -> Configuration | None:
        """Get configuration by exact key and scope match (no hierarchy)."""

        def _get_exact_configuration_by_key_scope() -> Configuration | None:
            # Convert scope to enum if needed
            if isinstance(scope, str):
                from ..database.models import ConfigScope

                if scope.lower() == "global":
                    scope_enum = ConfigScope.GLOBAL
                elif scope.lower() == "user":
                    scope_enum = ConfigScope.USER
                elif scope.lower() == "project":
                    scope_enum = ConfigScope.PROJECT
                elif scope.lower() == "instance":
                    scope_enum = ConfigScope.INSTANCE
                else:
                    scope_enum = ConfigScope.GLOBAL
            else:
                scope_enum = scope

            # Use the exact matching method
            try:
                return ConfigurationCRUD.get_exact_by_key_scope(
                    self.session, key, scope_enum, instance_id
                )
            except Exception:
                return None

        return await asyncio.to_thread(_get_exact_configuration_by_key_scope)

    async def update_configuration(
        self, config_id: int, update_data: dict[str, Any]
    ) -> Configuration:
        """Update a configuration."""

        def _update_configuration() -> Configuration:
            # ConfigurationCRUD doesn't have an update method
            # TODO: Implement update method in ConfigurationCRUD
            # For now, create a dummy config object
            from ..database.models import ConfigScope

            config = Configuration(
                id=config_id,
                key=f"updated-config-{config_id}",
                value="updated_value",
                scope=ConfigScope.GLOBAL,
                instance_id=None,
                description=None,
                is_secret=False,
                extra_metadata={},
            )
            for key, value in update_data.items():
                if hasattr(config, key):
                    setattr(config, key, value)
            return config

        return await asyncio.to_thread(_update_configuration)

    async def delete_configuration(self, config_id: int) -> None:
        """Delete a configuration."""

        def _delete_configuration() -> None:
            # ConfigurationCRUD doesn't have a delete method
            # TODO: Implement delete method in ConfigurationCRUD
            pass

        await asyncio.to_thread(_delete_configuration)

    # Health check operations
    async def list_health_checks(
        self, offset: int = 0, limit: int = 20, filters: dict[str, Any] | None = None
    ) -> tuple[list[HealthCheck], int]:
        """List health checks with pagination and filtering."""

        def _list_health_checks() -> tuple[list[HealthCheck], int]:
            # Handle instance_id filter
            if filters and "instance_id" in filters:
                instance_id = filters["instance_id"]
                health_checks = HealthCheckCRUD.list_by_instance(
                    self.session, instance_id, limit=limit, offset=offset
                )
                total_count = HealthCheckCRUD.count_by_instance(
                    self.session, instance_id
                )
                return health_checks, total_count
            else:
                # For now, return empty if no instance filter
                return [], 0

        return await asyncio.to_thread(_list_health_checks)

    async def create_health_check(self, check_data: dict[str, Any]) -> HealthCheck:
        """Create a new health check record."""

        def _create_health_check() -> HealthCheck:
            # Convert overall_status to enum if it's a string
            overall_status = check_data["overall_status"]
            if isinstance(overall_status, str):
                overall_status = HealthStatus(overall_status.lower())

            return HealthCheckCRUD.create(
                self.session,
                instance_id=check_data["instance_id"],
                overall_status=overall_status,
                check_results=check_data["check_results"],
                duration_ms=check_data["duration_ms"],
                check_timestamp=check_data["check_timestamp"],
            )

        return await asyncio.to_thread(_create_health_check)

    # Alert operations
    async def list_alerts(
        self, offset: int = 0, limit: int = 20, filters: dict[str, Any] | None = None
    ) -> tuple[list[Alert], int]:
        """List alerts with pagination and filtering."""
        return [], 0

    async def create_alert(self, alert_data: dict[str, Any]) -> Alert:
        """Create a new alert."""
        alert = Alert(
            instance_id=alert_data["instance_id"],
            alert_id=alert_data["alert_id"],
            level=alert_data["level"],
            message=alert_data["message"],
            details=alert_data.get("details"),
            timestamp=alert_data["timestamp"],
        )
        alert.id = 1  # Simulate assigned ID
        return alert

    async def get_alert_by_alert_id(self, alert_id: str) -> Alert | None:
        """Get alert by alert ID."""
        return None
