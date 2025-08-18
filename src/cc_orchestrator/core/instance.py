"""Claude Code instance management."""

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from ..utils.logging import LogContext, get_logger
from ..utils.process import (
    ProcessError,
    ProcessInfo,
    get_process_manager,
)

logger = get_logger(__name__, LogContext.INSTANCE)


class InstanceError(Exception):
    """Base exception for instance-related operations."""

    pass


class InstanceStatus(Enum):
    """Status of a Claude Code instance."""

    INITIALIZING = "initializing"
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"


# Alias for compatibility
InstanceState = InstanceStatus


class ClaudeInstance:
    """Represents a single Claude Code instance working on an issue."""

    def __init__(
        self,
        issue_id: str,
        workspace_path: Path | None = None,
        branch_name: str | None = None,
        tmux_session: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize a Claude instance.

        Args:
            issue_id: GitHub issue ID
            workspace_path: Path to the git worktree
            branch_name: Git branch name for this instance
            tmux_session: Tmux session name
            **kwargs: Additional configuration
        """
        self.issue_id = issue_id
        self.workspace_path = workspace_path or Path(
            f"../cc-orchestrator-issue-{issue_id}"
        )
        self.branch_name = branch_name or f"feature/issue-{issue_id}"
        self.tmux_session = tmux_session or f"claude-issue-{issue_id}"

        self.status = InstanceStatus.INITIALIZING
        self.created_at = datetime.now()
        self.last_activity = self.created_at
        self.process_id: int | None = None
        self.metadata: dict[str, Any] = kwargs

        # Process management
        self._process_manager = get_process_manager()
        self._process_info: ProcessInfo | None = None

    async def initialize(self) -> None:
        """Initialize the Claude instance."""
        logger.info("Initializing Claude instance", instance_id=self.issue_id)

        try:
            # TODO: Create git worktree if not exists
            # TODO: Create tmux session if not exists

            # For now, just mark as initialized without starting the process
            # The process will be started when start() is called
            self.status = InstanceStatus.STOPPED
            self.last_activity = datetime.now()

            logger.info(
                "Claude instance initialized successfully", instance_id=self.issue_id
            )
        except Exception as e:
            logger.error(
                "Failed to initialize Claude instance",
                instance_id=self.issue_id,
                error=str(e),
            )
            self.status = InstanceStatus.ERROR
            raise e

    async def start(self) -> bool:
        """Start the Claude Code process.

        Returns:
            True if started successfully, False otherwise
        """
        if self.status == InstanceStatus.RUNNING:
            logger.info("Claude instance already running", instance_id=self.issue_id)
            return True

        logger.info("Starting Claude instance", instance_id=self.issue_id)

        try:
            # Spawn Claude process using the process manager
            self._process_info = await self._process_manager.spawn_claude_process(
                instance_id=self.issue_id,
                working_directory=self.workspace_path,
                tmux_session=self.tmux_session,
                environment=self._get_environment_variables(),
            )

            # Update instance state
            self.process_id = self._process_info.pid
            self.status = InstanceStatus.RUNNING
            self.last_activity = datetime.now()

            logger.info(
                "Claude instance started successfully",
                instance_id=self.issue_id,
                pid=self.process_id,
            )
            return True

        except ProcessError as e:
            logger.error(
                "Failed to start Claude instance",
                instance_id=self.issue_id,
                error=str(e),
            )
            self.status = InstanceStatus.ERROR
            return False
        except Exception as e:
            logger.error(
                "Unexpected error starting Claude instance",
                instance_id=self.issue_id,
                error=str(e),
            )
            self.status = InstanceStatus.ERROR
            return False

    async def stop(self) -> bool:
        """Stop the Claude Code process.

        Returns:
            True if stopped successfully, False otherwise
        """
        if self.status == InstanceStatus.STOPPED:
            logger.info("Claude instance already stopped", instance_id=self.issue_id)
            return True

        logger.info("Stopping Claude instance", instance_id=self.issue_id)

        try:
            # Terminate process using the process manager
            success = await self._process_manager.terminate_process(self.issue_id)

            if success:
                self.status = InstanceStatus.STOPPED
                self.process_id = None
                self._process_info = None

                logger.info(
                    "Claude instance stopped successfully", instance_id=self.issue_id
                )
                return True
            else:
                logger.error(
                    "Failed to stop Claude instance", instance_id=self.issue_id
                )
                return False

        except Exception as e:
            logger.error(
                "Error stopping Claude instance",
                instance_id=self.issue_id,
                error=str(e),
            )
            return False

    def is_running(self) -> bool:
        """Check if the instance is currently running.

        Returns:
            True if running, False otherwise
        """
        return self.status == InstanceStatus.RUNNING

    async def get_process_status(self) -> ProcessInfo | None:
        """Get detailed process status information.

        Returns:
            ProcessInfo if process exists, None otherwise
        """
        if not self._process_info:
            return None

        # Get updated process info from manager
        return await self._process_manager.get_process_info(self.issue_id)

    def get_info(self) -> dict[str, Any]:
        """Get instance information.

        Returns:
            Dictionary containing instance details
        """
        info = {
            "issue_id": self.issue_id,
            "status": self.status.value,
            "workspace_path": str(self.workspace_path),
            "branch_name": self.branch_name,
            "tmux_session": self.tmux_session,
            "created_at": self.created_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "process_id": self.process_id,
            "metadata": self.metadata,
        }

        # Add process information if available
        if self._process_info:
            process_info: dict[str, Any] = {
                "process_status": self._process_info.status.value,
                "cpu_percent": self._process_info.cpu_percent,
                "memory_mb": self._process_info.memory_mb,
                "started_at": self._process_info.started_at,
                "return_code": self._process_info.return_code,
                "error_message": self._process_info.error_message,
            }
            info.update(process_info)

        return info

    async def cleanup(self) -> None:
        """Clean up instance resources."""
        logger.info("Cleaning up Claude instance", instance_id=self.issue_id)
        await self.stop()
        # TODO: Additional cleanup if needed (git worktree, tmux session)

    def _get_environment_variables(self) -> dict[str, str]:
        """Get environment variables for the Claude process.

        Returns:
            Dictionary of environment variables
        """
        env = {}

        # Set Claude-specific environment variables
        env["CLAUDE_INSTANCE_ID"] = self.issue_id
        env["CLAUDE_WORKSPACE"] = str(self.workspace_path)
        env["CLAUDE_BRANCH"] = self.branch_name
        env["CLAUDE_TMUX_SESSION"] = self.tmux_session

        # Add any custom environment variables from metadata
        if "environment" in self.metadata:
            env.update(self.metadata["environment"])

        return env
