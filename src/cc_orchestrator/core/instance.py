"""Claude Code instance management."""

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional


class InstanceStatus(Enum):
    """Status of a Claude Code instance."""

    INITIALIZING = "initializing"
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"


class ClaudeInstance:
    """Represents a single Claude Code instance working on an issue."""

    def __init__(
        self,
        issue_id: str,
        workspace_path: Optional[Path] = None,
        branch_name: Optional[str] = None,
        tmux_session: Optional[str] = None,
        **kwargs,
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
        self.process_id: Optional[int] = None
        self.metadata: dict[str, Any] = kwargs

    async def initialize(self) -> None:
        """Initialize the Claude instance."""
        try:
            # TODO: Create git worktree if not exists
            # TODO: Create tmux session if not exists
            # TODO: Start Claude Code process
            # TODO: Set up monitoring

            self.status = InstanceStatus.RUNNING
            self.last_activity = datetime.now()
        except Exception as e:
            self.status = InstanceStatus.ERROR
            raise e

    async def start(self) -> bool:
        """Start the Claude Code process.

        Returns:
            True if started successfully, False otherwise
        """
        if self.status == InstanceStatus.RUNNING:
            return True

        try:
            # TODO: Execute claude --continue in tmux session
            # TODO: Set process_id

            self.status = InstanceStatus.RUNNING
            self.last_activity = datetime.now()
            return True
        except Exception:
            self.status = InstanceStatus.ERROR
            return False

    async def stop(self) -> bool:
        """Stop the Claude Code process.

        Returns:
            True if stopped successfully, False otherwise
        """
        if self.status == InstanceStatus.STOPPED:
            return True

        try:
            # TODO: Gracefully stop Claude process
            # TODO: Save session state

            self.status = InstanceStatus.STOPPED
            self.process_id = None
            return True
        except Exception:
            return False

    def is_running(self) -> bool:
        """Check if the instance is currently running.

        Returns:
            True if running, False otherwise
        """
        return self.status == InstanceStatus.RUNNING

    def get_info(self) -> dict[str, Any]:
        """Get instance information.

        Returns:
            Dictionary containing instance details
        """
        return {
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

    async def cleanup(self) -> None:
        """Clean up instance resources."""
        await self.stop()
        # TODO: Additional cleanup if needed
