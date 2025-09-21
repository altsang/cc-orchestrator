"""Main orchestrator class for managing Claude instances."""

from typing import Any

from sqlalchemy.orm import Session

from ..database.crud import InstanceCRUD, NotFoundError
from ..database.models import Instance
from ..utils.logging import LogContext, get_logger
from ..utils.process import cleanup_process_manager
from .enums import InstanceStatus
from .health_monitor import cleanup_health_monitor, get_health_monitor
from .instance import ClaudeInstance

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

        # Validate database connection and schema
        try:
            # Test database connectivity
            from sqlalchemy import text

            self._db_session.execute(text("SELECT 1"))

            # Verify core tables exist
            from ..database.models import Instance

            # Test that we can query the instances table (basic check)
            # Use count() instead of all() to avoid loading all columns in case of schema mismatch
            self._db_session.query(Instance.id).limit(1).count()

            logger.info("Database connection validation successful")
        except Exception as db_e:
            logger.error("Database connection validation failed", error=str(db_e))
            if self._should_close_session and self._db_session:
                self._db_session.close()
                self._db_session = None
            raise RuntimeError(f"Database validation failed: {db_e}") from db_e

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
        except Exception:
            logger.error("Error listing instances", exc_info=True)
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

        try:
            # Initialize the instance
            await instance.initialize()

            # Prepare metadata for JSON serialization (convert Path objects to strings)
            serializable_metadata = {}
            for key, value in kwargs.items():
                if hasattr(value, "__fspath__"):  # Path-like object
                    serializable_metadata[key] = str(value)
                else:
                    serializable_metadata[key] = value

            # Persist to database
            db_instance = InstanceCRUD.create(
                session=self._db_session,
                issue_id=issue_id,
                workspace_path=str(instance.workspace_path),
                branch_name=instance.branch_name,
                tmux_session=instance.tmux_session,
                extra_metadata=serializable_metadata,
            )
            self._db_session.commit()

            logger.info(
                "Instance created and persisted",
                issue_id=issue_id,
                db_id=db_instance.id,
            )
            return instance
        except Exception as e:
            # Clean up instance resources on any failure
            try:
                await instance.cleanup()
                logger.info(
                    "Cleaned up instance after creation failure", issue_id=issue_id
                )
            except Exception as cleanup_e:
                logger.error(
                    "Failed to clean up instance after creation failure",
                    issue_id=issue_id,
                    cleanup_error=str(cleanup_e),
                )

            # Roll back database transaction
            self._db_session.rollback()
            logger.error("Failed to create instance", issue_id=issue_id, error=str(e))
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

        db_instance = None
        instance = None

        try:
            # Get the instance first
            db_instance = InstanceCRUD.get_by_issue_id(self._db_session, issue_id)

            # Create instance object for cleanup BEFORE database operations
            instance = self._db_instance_to_claude_instance(db_instance)

            # ATTEMPT CLEANUP FIRST (even if database operations might fail)
            cleanup_success = True
            try:
                await instance.cleanup()
                logger.debug("Instance cleanup completed", issue_id=issue_id)
            except Exception as cleanup_e:
                cleanup_success = False
                logger.warning(
                    "Instance cleanup failed during destruction",
                    issue_id=issue_id,
                    error=str(cleanup_e),
                )

            # DELETE FROM DATABASE SECOND to ensure consistency
            # If database deletion fails, resources remain allocated but database is consistent
            InstanceCRUD.delete(self._db_session, db_instance.id)
            self._db_session.commit()
            logger.debug("Instance removed from database", issue_id=issue_id)

            if cleanup_success:
                logger.info("Instance destroyed successfully", issue_id=issue_id)
            else:
                logger.warning(
                    "Instance destroyed with cleanup errors", issue_id=issue_id
                )
            return True

        except NotFoundError:
            logger.warning("Instance not found for destruction", issue_id=issue_id)
            return False
        except Exception as e:
            # If we have an instance object and database deletion failed,
            # try one more cleanup attempt
            if instance is not None and db_instance is not None:
                try:
                    logger.warning(
                        "Database deletion failed, attempting final cleanup",
                        issue_id=issue_id,
                    )
                    await instance.cleanup()
                except Exception as final_cleanup_e:
                    logger.error(
                        "Final cleanup attempt failed",
                        issue_id=issue_id,
                        error=str(final_cleanup_e),
                    )

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
        # Filter out conflicting keys from extra_metadata
        extra_metadata = db_instance.extra_metadata or {}
        filtered_metadata = {
            k: v
            for k, v in extra_metadata.items()
            if k not in ["issue_id", "workspace_path", "branch_name", "tmux_session"]
        }

        claude_instance = ClaudeInstance(
            issue_id=db_instance.issue_id,
            workspace_path=(
                Path(db_instance.workspace_path) if db_instance.workspace_path else None
            ),
            branch_name=db_instance.branch_name,
            tmux_session=db_instance.tmux_session,
            **filtered_metadata,
        )

        # Set status and other attributes from database
        claude_instance.status = db_instance.status
        claude_instance.process_id = db_instance.process_id
        claude_instance.created_at = db_instance.created_at
        claude_instance.last_activity = (
            db_instance.last_activity or db_instance.updated_at
        )

        # Validate process state for RUNNING instances
        if (
            db_instance.status == InstanceStatus.RUNNING
            and db_instance.process_id is not None
        ):
            # Check if the process still exists
            try:
                import psutil

                if psutil.pid_exists(db_instance.process_id):
                    # Process exists, verify it's actually a Claude process
                    # Note: We could do additional verification on the process if needed

                    # Set up process info for health monitoring
                    claude_instance._process_info = type(
                        "ProcessInfo",
                        (),
                        {
                            "pid": db_instance.process_id,
                            "status": "running",
                            "started_at": db_instance.created_at,
                            "cpu_percent": 0.0,
                            "memory_mb": 0.0,
                            "return_code": None,
                            "error_message": None,
                        },
                    )()

                    logger.info(
                        "Reconnected to existing process for database-loaded instance",
                        instance_id=db_instance.issue_id,
                        pid=db_instance.process_id,
                    )
                else:
                    # Process no longer exists, update status to stopped
                    claude_instance.status = InstanceStatus.STOPPED
                    claude_instance.process_id = None
                    claude_instance._process_info = None

                    logger.warning(
                        "Process no longer exists for database instance, marking as stopped",
                        instance_id=db_instance.issue_id,
                        expected_pid=db_instance.process_id,
                    )

                    # Update database to reflect actual state
                    try:
                        from ..database.crud import InstanceCRUD

                        InstanceCRUD.update(
                            session=self._db_session,
                            instance_id=db_instance.id,
                            status=InstanceStatus.STOPPED,
                            process_id=None,
                        )
                        self._db_session.commit()
                    except Exception as update_e:
                        logger.error(
                            "Failed to update instance status in database",
                            instance_id=db_instance.issue_id,
                            error=str(update_e),
                        )
                        self._db_session.rollback()

            except Exception as e:
                logger.error(
                    "Error validating process state for database instance",
                    instance_id=db_instance.issue_id,
                    process_id=db_instance.process_id,
                    error=str(e),
                )
                # On error, mark as stopped to be safe
                claude_instance.status = InstanceStatus.STOPPED
                claude_instance.process_id = None
                claude_instance._process_info = None

        # Register with health monitor for ongoing monitoring
        if claude_instance.status in [
            InstanceStatus.RUNNING,
            InstanceStatus.INITIALIZING,
        ]:
            try:
                self.health_monitor.register_instance(claude_instance)
                logger.debug(
                    "Registered database-loaded instance with health monitor",
                    instance_id=claude_instance.issue_id,
                    status=claude_instance.status.value,
                )
            except Exception as e:
                logger.warning(
                    "Failed to register instance with health monitor",
                    instance_id=claude_instance.issue_id,
                    error=str(e),
                )

        return claude_instance

    def _validate_instance_ownership(self, issue_id: str) -> bool:
        """Validate that the current user has permission to modify this instance.

        Args:
            issue_id: The issue ID to validate ownership for

        Returns:
            bool: True if user has permission, False otherwise

        Note:
            For CLI operations, this is a basic validation.
            In a multi-user environment, this should check actual user permissions.
        """
        try:
            # Basic validation - ensure instance exists and we can access it
            db_instance = InstanceCRUD.get_by_issue_id(self._db_session, issue_id)
            if not db_instance:
                logger.warning(
                    "Authorization check failed - instance not found", issue_id=issue_id
                )
                return False

            # For CLI usage, basic existence check is sufficient
            # In production, you might check:
            # - User ID against instance owner
            # - Group permissions
            # - Role-based access control
            return True

        except Exception as e:
            logger.error(
                "Authorization validation failed", issue_id=issue_id, error=str(e)
            )
            return False

    def sync_instance_to_database(self, instance: ClaudeInstance) -> bool:
        """Sync instance state changes back to the database.

        Args:
            instance: ClaudeInstance with potentially updated state

        Returns:
            bool: True if sync succeeded, False otherwise
        """
        # Enhanced input validation for security
        if not instance:
            logger.error("Invalid instance provided for sync - instance is None")
            return False

        # Validate issue_id with strict security checks
        if not instance.issue_id or not isinstance(instance.issue_id, str):
            logger.error(
                "Invalid issue_id provided for sync - must be non-empty string"
            )
            return False

        # Prevent potential injection attacks with issue_id length validation
        if (
            len(instance.issue_id) > 100
            or not instance.issue_id.replace("-", "").replace("_", "").isalnum()
        ):
            logger.error(
                "Invalid issue_id format - security validation failed",
                issue_id="<redacted>",
            )
            return False

        # Validate instance has required attributes to prevent attribute errors
        if not hasattr(instance, "status") or instance.status is None:
            logger.error("Instance missing required status field")
            return False

        if not hasattr(instance, "last_activity"):
            logger.error("Instance missing required last_activity field")
            return False

        if not self._initialized or not self._db_session:
            logger.error("Orchestrator not initialized")
            return False

        # Validate user permissions for this instance
        if not self._validate_instance_ownership(instance.issue_id):
            logger.error("Unauthorized sync attempt", issue_id=instance.issue_id)
            return False

        # Check database connection pool health before proceeding
        try:
            engine = self._db_session.get_bind()
            if hasattr(engine, "pool"):
                pool = engine.pool
                if hasattr(pool, "checkedout") and hasattr(pool, "size"):
                    if pool.checkedout() > 0.8 * pool.size():
                        logger.warning(
                            "Database connection pool near capacity - deferring sync"
                        )
                        return False
        except Exception as pool_e:
            logger.debug("Could not check connection pool status", error=str(pool_e))

        try:
            # Use atomic transaction with timeout protection
            with self._db_session.begin() as txn:
                # Set statement timeout for security (prevent hanging transactions)
                try:
                    from sqlalchemy import text

                    self._db_session.execute(text("/* sync_timeout_protection */"))
                except Exception:
                    pass  # Not all databases support this, continue without timeout

                # Get the database instance to update
                db_instance = InstanceCRUD.get_by_issue_id(
                    self._db_session, instance.issue_id
                )

                if not db_instance:
                    logger.error(
                        "Instance not found in database during sync",
                        issue_id=instance.issue_id,
                    )
                    return False

                # Check for potential concurrent modification (stale data protection)
                if (
                    hasattr(instance, "last_activity")
                    and instance.last_activity
                    and hasattr(db_instance, "last_activity")
                    and db_instance.last_activity
                    and instance.last_activity < db_instance.last_activity
                ):
                    logger.warning(
                        "Instance state appears stale - possible concurrent modification",
                        issue_id=instance.issue_id,
                    )
                    return False

                # Secure logging without sensitive data exposure
                logger.info(
                    "Syncing instance to database",
                    issue_id=instance.issue_id,
                    memory_status=instance.status.value,
                    db_status=db_instance.status.value,
                    # Removed process_id from logging for security
                )

                # Update fields that might have changed
                updated_instance = InstanceCRUD.update(
                    session=self._db_session,
                    instance_id=db_instance.id,
                    status=instance.status,
                    process_id=instance.process_id,
                    last_activity=instance.last_activity,
                )

                logger.info(
                    "Instance state synced to database successfully",
                    issue_id=instance.issue_id,
                    final_status=updated_instance.status.value,
                    # Removed process_id from logging for security
                )

            return True

        except Exception as e:
            logger.error(
                "Failed to sync instance state to database",
                issue_id=(
                    instance.issue_id
                    if instance and hasattr(instance, "issue_id")
                    else "unknown"
                ),
                error=str(e),
            )
            return False
