"""Main orchestrator class for managing Claude instances."""

from typing import Any

from sqlalchemy.orm import Session

from ..database.crud import InstanceCRUD, NotFoundError
from ..database.models import Instance
from ..database.models import InstanceStatus as DBInstanceStatus
from ..utils.logging import LogContext, get_logger
from ..utils.process import cleanup_process_manager
from .health_monitor import cleanup_health_monitor, get_health_monitor
from .instance import ClaudeInstance, InstanceStatus

logger = get_logger(__name__, LogContext.ORCHESTRATOR)


class Orchestrator:
    """Main orchestrator for managing multiple Claude Code instances."""

    def __init__(
        self, config_path: str | None = None, db_session: Session | None = None
    ) -> None:
        """Initialize the orchestrator.

        Args:
            config_path: Path to configuration file
            db_session: Database session (optional, will create one if not provided)
        """
        self.config_path = config_path
        self._db_session = db_session
        self._should_close_session = db_session is None
        self._initialized = False
        self.health_monitor = get_health_monitor()

    async def initialize(self) -> None:
        """Initialize the orchestrator and load configuration."""
        logger.info("Initializing orchestrator")

        # Initialize database connection if not provided
        if self._db_session is None:
            from ..database.connection import get_database_manager

            db_manager = get_database_manager()
            self._db_session = db_manager.create_session()
            self._should_close_session = True

        # TODO: Load configuration
        # TODO: Set up logging

        # Start health monitoring
        logger.info("Starting health monitoring")
        await self.health_monitor.start()

        self._initialized = True
        logger.info("Orchestrator initialized successfully")

    def get_instance(self, issue_id: str) -> ClaudeInstance | None:
        """Get a Claude instance by issue ID.

        Args:
            issue_id: GitHub issue ID

        Returns:
            ClaudeInstance if found, None otherwise
        """
        if not self._initialized or not self._db_session:
            logger.error("Orchestrator not initialized")
            return None

        try:
            db_instance = InstanceCRUD.get_by_issue_id(self._db_session, issue_id)
            return self._db_instance_to_claude_instance(db_instance)
        except NotFoundError:
            return None
        except Exception as e:
            logger.error("Error getting instance", issue_id=issue_id, error=str(e))
            return None

    def list_instances(self) -> list[ClaudeInstance]:
        """List all active Claude instances.

        Returns:
            List of active ClaudeInstance objects
        """
        if not self._initialized or not self._db_session:
            logger.error("Orchestrator not initialized")
            return []

        try:
            db_instances = InstanceCRUD.list_all(self._db_session)
            return [
                self._db_instance_to_claude_instance(db_inst)
                for db_inst in db_instances
            ]
        except Exception as e:
            logger.error("Error listing instances", error=str(e), exc_info=True)
            return []

    async def create_instance(self, issue_id: str, **kwargs: Any) -> ClaudeInstance:
        """Create a new Claude instance for an issue.

        Args:
            issue_id: GitHub issue ID
            **kwargs: Additional configuration options

        Returns:
            Created ClaudeInstance
        """
        if not self._initialized or not self._db_session:
            raise RuntimeError("Orchestrator not initialized")

        logger.info("Creating instance", issue_id=issue_id)

        # Check if instance already exists
        existing = self.get_instance(issue_id)
        if existing:
            raise ValueError(f"Instance for issue {issue_id} already exists")

        # Create ClaudeInstance object
        instance = ClaudeInstance(issue_id=issue_id, **kwargs)
        await instance.initialize()

        # Persist to database immediately
        try:
            db_instance = InstanceCRUD.create(
                session=self._db_session,
                issue_id=issue_id,
                workspace_path=str(instance.workspace_path),
                branch_name=instance.branch_name,
                tmux_session=instance.tmux_session,
                extra_metadata=kwargs,
            )
            self._db_session.commit()

            logger.info(
                "Instance created and persisted",
                issue_id=issue_id,
                db_id=db_instance.id,
            )
            return instance
        except Exception as e:
            self._db_session.rollback()
            logger.error("Failed to persist instance", issue_id=issue_id, error=str(e))
            raise

    async def destroy_instance(self, issue_id: str) -> bool:
        """Destroy a Claude instance.

        Args:
            issue_id: GitHub issue ID

        Returns:
            True if instance was destroyed, False if not found
        """
        if not self._initialized or not self._db_session:
            raise RuntimeError("Orchestrator not initialized")

        logger.info("Destroying instance", issue_id=issue_id)

        try:
            # Get the instance first
            db_instance = InstanceCRUD.get_by_issue_id(self._db_session, issue_id)
            instance = self._db_instance_to_claude_instance(db_instance)

            # Clean up the Claude instance (stop processes, etc.)
            await instance.cleanup()

            # Remove from database
            InstanceCRUD.delete(self._db_session, db_instance.id)
            self._db_session.commit()

            logger.info("Instance destroyed successfully", issue_id=issue_id)
            return True
        except NotFoundError:
            logger.warning("Instance not found for destruction", issue_id=issue_id)
            return False
        except Exception as e:
            self._db_session.rollback()
            logger.error("Error destroying instance", issue_id=issue_id, error=str(e))
            return False

    async def cleanup(self) -> None:
        """Clean up all instances and resources."""
        logger.info("Cleaning up orchestrator")

        # Stop health monitoring first
        await self.health_monitor.stop()

        # Clean up all instances
        instances = self.list_instances()
        logger.info("Cleaning up instances", instance_count=len(instances))
        for instance in instances:
            await instance.cleanup()

        # Close database session if we created it
        if self._should_close_session and self._db_session:
            self._db_session.close()
            self._db_session = None

        # Clean up global managers
        await cleanup_process_manager()
        await cleanup_health_monitor()

        logger.info("Orchestrator cleanup completed")

    def _db_instance_to_claude_instance(self, db_instance: Instance) -> ClaudeInstance:
        """Convert database Instance to ClaudeInstance.

        Args:
            db_instance: Database instance object

        Returns:
            ClaudeInstance object
        """
        from pathlib import Path

        # Create ClaudeInstance with database data
        claude_instance = ClaudeInstance(
            issue_id=db_instance.issue_id,
            workspace_path=(
                Path(db_instance.workspace_path) if db_instance.workspace_path else None
            ),
            branch_name=db_instance.branch_name,
            tmux_session=db_instance.tmux_session,
            **(db_instance.extra_metadata or {}),
        )

        # Set status and other attributes from database
        claude_instance.status = self._db_status_to_instance_status(db_instance.status)
        claude_instance.process_id = db_instance.process_id
        claude_instance.created_at = db_instance.created_at
        claude_instance.last_activity = (
            db_instance.last_activity or db_instance.updated_at
        )

        return claude_instance

    def _db_status_to_instance_status(
        self, db_status: DBInstanceStatus
    ) -> InstanceStatus:
        """Convert database status to instance status.

        Args:
            db_status: Database instance status

        Returns:
            InstanceStatus enum value
        """
        status_mapping = {
            DBInstanceStatus.INITIALIZING: InstanceStatus.INITIALIZING,
            DBInstanceStatus.RUNNING: InstanceStatus.RUNNING,
            DBInstanceStatus.STOPPED: InstanceStatus.STOPPED,
            DBInstanceStatus.ERROR: InstanceStatus.ERROR,
        }
        return status_mapping.get(db_status, InstanceStatus.STOPPED)

    def _instance_status_to_db_status(
        self, instance_status: InstanceStatus
    ) -> DBInstanceStatus:
        """Convert instance status to database status.

        Args:
            instance_status: ClaudeInstance status

        Returns:
            Database InstanceStatus enum value
        """
        status_mapping = {
            InstanceStatus.INITIALIZING: DBInstanceStatus.INITIALIZING,
            InstanceStatus.RUNNING: DBInstanceStatus.RUNNING,
            InstanceStatus.STOPPED: DBInstanceStatus.STOPPED,
            InstanceStatus.ERROR: DBInstanceStatus.ERROR,
        }
        return status_mapping.get(instance_status, DBInstanceStatus.STOPPED)
