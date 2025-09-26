"""Main orchestrator class for managing Claude instances."""

from typing import Any

from ..database.connection import get_database_manager, get_db_session
from ..database.crud import InstanceCRUD, NotFoundError
from ..database.models import InstanceStatus as DBInstanceStatus
from ..utils.logging import LogContext, get_logger
from ..utils.process import cleanup_process_manager
from .instance import ClaudeInstance, InstanceStatus

logger = get_logger(__name__, LogContext.ORCHESTRATOR)


class DatabaseSyncError(Exception):
    """Exception raised when database synchronization fails."""
    pass


class Orchestrator:
    """Main orchestrator for managing multiple Claude Code instances."""

    def __init__(self, config_path: str | None = None) -> None:
        """Initialize the orchestrator.

        Args:
            config_path: Path to configuration file
        """
        self.config_path = config_path
        self.instances: dict[str, ClaudeInstance] = {}
        self._initialized = False
        self._db_manager = None

    async def initialize(self, lazy_load: bool = True) -> None:
        """Initialize the orchestrator and optionally load instances.

        Args:
            lazy_load: If True, don't load all instances immediately (performance optimization).
                      Instances will be loaded on-demand when accessed.
        """
        logger.info("Initializing orchestrator", config_path=self.config_path, lazy_load=lazy_load)

        try:
            # Initialize database connection
            self._db_manager = get_database_manager()
            await self._db_manager.initialize()
            logger.info("Database connection initialized")

            if not lazy_load:
                # Load existing instances from database (for operations that need all instances)
                await self._load_instances_from_database()
                logger.info("All instances loaded from database", instance_count=len(self.instances))
            else:
                # Lazy loading - only load instances when needed
                logger.info("Lazy loading enabled - instances will be loaded on demand")

            # TODO: Load configuration
            # TODO: Set up logging

            self._initialized = True
            logger.info("Orchestrator initialization completed")

        except Exception as e:
            logger.error("Failed to initialize orchestrator", error=str(e))
            self._initialized = False
            raise

    async def get_instance(self, issue_id: str) -> ClaudeInstance | None:
        """Get a Claude instance by issue ID (with lazy loading).

        Args:
            issue_id: GitHub issue ID

        Returns:
            ClaudeInstance if found, None otherwise
        """
        # Check if already loaded in memory
        if issue_id in self.instances:
            return self.instances[issue_id]

        # Lazy load from database if not in memory
        await self._load_specific_instance_from_database(issue_id)
        return self.instances.get(issue_id)

    async def list_instances(self, load_all: bool = True) -> list[ClaudeInstance]:
        """List all active Claude instances.

        Args:
            load_all: If True, ensure all instances are loaded from database.

        Returns:
            List of active ClaudeInstance objects
        """
        if load_all and len(self.instances) == 0:
            # Load all instances from database for comprehensive listing
            await self._load_instances_from_database()

        return list(self.instances.values())

    async def create_instance(self, issue_id: str, **kwargs: Any) -> ClaudeInstance:
        """Create a new Claude instance for an issue.

        Args:
            issue_id: GitHub issue ID
            **kwargs: Additional configuration options

        Returns:
            Created ClaudeInstance
        """
        if issue_id in self.instances:
            raise ValueError(f"Instance for issue {issue_id} already exists")

        # Create the instance object
        instance = ClaudeInstance(issue_id=issue_id, **kwargs)
        await instance.initialize()

        # Save to database
        await self._sync_instance_to_database(instance)

        # Add to memory
        self.instances[issue_id] = instance

        logger.info("Instance created and persisted", instance_id=issue_id)
        return instance

    async def destroy_instance(self, issue_id: str) -> bool:
        """Destroy a Claude instance.

        Args:
            issue_id: GitHub issue ID

        Returns:
            True if instance was destroyed, False if not found
        """
        instance = self.instances.pop(issue_id, None)
        if instance:
            await instance.cleanup()

            # Remove from database
            try:
                with get_db_session() as session:
                    db_instance = InstanceCRUD.get_by_issue_id(session, issue_id)
                    InstanceCRUD.delete(session, db_instance.id)
                    logger.info("Instance removed from database", instance_id=issue_id)
            except NotFoundError:
                logger.warning(
                    "Instance not found in database during destroy",
                    instance_id=issue_id,
                )
            except Exception as e:
                logger.error(
                    "Failed to remove instance from database",
                    instance_id=issue_id,
                    error=str(e),
                )

            return True
        return False

    async def cleanup(self) -> None:
        """Clean up all instances and resources."""
        logger.info("Cleaning up orchestrator", instance_count=len(self.instances))

        # Clean up all instances
        for instance in self.instances.values():
            await instance.cleanup()
        self.instances.clear()

        # Clean up the global process manager
        await cleanup_process_manager()

        logger.info("Orchestrator cleanup completed")

    async def _load_instances_from_database(self) -> None:
        """Load existing instances from database into memory."""
        try:
            with get_db_session() as session:
                db_instances = InstanceCRUD.list_all(session)
                logger.info("Loading instances from database", count=len(db_instances))

                for db_instance in db_instances:
                    # Create ClaudeInstance object from database data
                    instance = ClaudeInstance(
                        issue_id=db_instance.issue_id,
                        workspace_path=db_instance.workspace_path,
                        branch_name=db_instance.branch_name,
                        tmux_session=db_instance.tmux_session,
                        **db_instance.extra_metadata or {},
                    )

                    # Set instance state from database
                    saved_status = self._db_status_to_instance_status(
                        db_instance.status
                    )
                    instance.process_id = db_instance.process_id
                    instance.created_at = db_instance.created_at
                    instance.last_activity = (
                        db_instance.last_activity or db_instance.updated_at
                    )

                    # Initialize without starting the process
                    await instance.initialize()

                    # Restore the database status (initialize() sets it to STOPPED)
                    instance.status = saved_status

                    # Add to memory
                    self.instances[db_instance.issue_id] = instance

                logger.info(
                    "Instances loaded from database", loaded_count=len(self.instances)
                )

        except Exception as e:
            logger.error("Failed to load instances from database", error=str(e))
            # Don't raise - allow orchestrator to work with empty state
            self.instances = {}

    async def _load_specific_instance_from_database(self, issue_id: str) -> None:
        """Load a specific instance from database into memory (lazy loading)."""
        try:
            with get_db_session() as session:
                try:
                    db_instance = InstanceCRUD.get_by_issue_id(session, issue_id)
                    logger.debug("Loading specific instance from database", instance_id=issue_id)

                    # Create ClaudeInstance object from database data
                    instance = ClaudeInstance(
                        issue_id=db_instance.issue_id,
                        workspace_path=db_instance.workspace_path,
                        branch_name=db_instance.branch_name,
                        tmux_session=db_instance.tmux_session,
                        **db_instance.extra_metadata or {}
                    )

                    # Set instance state from database
                    saved_status = self._db_status_to_instance_status(db_instance.status)
                    instance.process_id = db_instance.process_id
                    instance.created_at = db_instance.created_at
                    instance.last_activity = db_instance.last_activity or db_instance.updated_at

                    # Initialize without starting the process
                    await instance.initialize()

                    # Restore the database status (initialize() sets it to STOPPED)
                    instance.status = saved_status

                    # Add to memory
                    self.instances[db_instance.issue_id] = instance

                    logger.debug("Specific instance loaded from database", instance_id=issue_id)

                except NotFoundError:
                    logger.debug("Instance not found in database", instance_id=issue_id)

        except Exception as e:
            logger.error("Failed to load specific instance from database", instance_id=issue_id, error=str(e))
            # Don't raise - this is non-critical lazy loading

    async def _sync_instance_to_database(self, instance: ClaudeInstance) -> None:
        """Sync instance state to database with explicit transaction management."""
        max_retries = 3
        retry_delay = 0.1  # 100ms

        for attempt in range(max_retries):
            try:
                with get_db_session() as session:
                    # Begin explicit transaction scope
                    try:
                        # Try to get existing instance
                        db_instance = InstanceCRUD.get_by_issue_id(
                            session, instance.issue_id
                        )
                        # Update existing instance in single operation
                        InstanceCRUD.update(
                            session,
                            db_instance.id,
                            status=self._instance_status_to_db_status(instance.status),
                            workspace_path=str(instance.workspace_path),
                            branch_name=instance.branch_name,
                            tmux_session=instance.tmux_session,
                            process_id=instance.process_id,
                            last_activity=instance.last_activity,
                            extra_metadata=instance.metadata,
                        )
                        # Explicit flush to ensure database constraints are checked
                        session.flush()
                        logger.debug(
                            "Updated existing instance in database",
                            instance_id=instance.issue_id
                        )

                    except NotFoundError:
                        # Create new instance with all fields in single transaction
                        db_instance = InstanceCRUD.create(
                            session,
                            issue_id=instance.issue_id,
                            workspace_path=str(instance.workspace_path),
                            branch_name=instance.branch_name,
                            tmux_session=instance.tmux_session,
                            extra_metadata=instance.metadata,
                        )
                        # Update with current status and other fields atomically
                        InstanceCRUD.update(
                            session,
                            db_instance.id,
                            status=self._instance_status_to_db_status(instance.status),
                            process_id=instance.process_id,
                            last_activity=instance.last_activity,
                        )
                        # Explicit flush to ensure all operations complete
                        session.flush()
                        logger.debug(
                            "Created new instance in database",
                            instance_id=instance.issue_id
                        )

                    # Transaction commits automatically on successful exit from context
                    return  # Success - exit retry loop

            except Exception as e:
                logger.warning(
                    "Database sync attempt failed",
                    instance_id=instance.issue_id,
                    attempt=attempt + 1,
                    max_retries=max_retries,
                    error=str(e),
                )

                if attempt == max_retries - 1:
                    # Final attempt failed - raise the error
                    logger.error(
                        "Failed to sync instance state to database after all retries",
                        instance_id=instance.issue_id,
                        error=str(e),
                    )
                    raise DatabaseSyncError(
                        f"Failed to sync instance {instance.issue_id} to database: {e}"
                    ) from e

                # Wait before retry
                import asyncio
                await asyncio.sleep(retry_delay * (2 ** attempt))  # Exponential backoff

    def _instance_status_to_db_status(self, status: InstanceStatus) -> DBInstanceStatus:
        """Convert instance status to database status."""
        status_mapping = {
            InstanceStatus.INITIALIZING: DBInstanceStatus.INITIALIZING,
            InstanceStatus.RUNNING: DBInstanceStatus.RUNNING,
            InstanceStatus.STOPPED: DBInstanceStatus.STOPPED,
            InstanceStatus.ERROR: DBInstanceStatus.ERROR,
        }
        return status_mapping[status]

    def _db_status_to_instance_status(
        self, db_status: DBInstanceStatus
    ) -> InstanceStatus:
        """Convert database status to instance status."""
        status_mapping = {
            DBInstanceStatus.INITIALIZING: InstanceStatus.INITIALIZING,
            DBInstanceStatus.RUNNING: InstanceStatus.RUNNING,
            DBInstanceStatus.STOPPED: InstanceStatus.STOPPED,
            DBInstanceStatus.ERROR: InstanceStatus.ERROR,
        }
        return status_mapping[db_status]

    async def sync_instance_state(self, issue_id: str) -> None:
        """Sync specific instance state to database."""
        instance = self.instances.get(issue_id)
        if instance:
            await self._sync_instance_to_database(instance)
        else:
            logger.warning(
                "Attempted to sync non-existent instance", instance_id=issue_id
            )
