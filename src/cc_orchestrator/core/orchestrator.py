"""Main orchestrator class for managing Claude instances."""

from typing import Optional

from .instance import ClaudeInstance


class Orchestrator:
    """Main orchestrator for managing multiple Claude Code instances."""

    def __init__(self, config_path: Optional[str] = None) -> None:
        """Initialize the orchestrator.

        Args:
            config_path: Path to configuration file
        """
        self.config_path = config_path
        self.instances: dict[str, ClaudeInstance] = {}
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the orchestrator and load configuration."""
        # TODO: Load configuration
        # TODO: Initialize database connection
        # TODO: Set up logging
        self._initialized = True

    def get_instance(self, issue_id: str) -> Optional[ClaudeInstance]:
        """Get a Claude instance by issue ID.

        Args:
            issue_id: GitHub issue ID

        Returns:
            ClaudeInstance if found, None otherwise
        """
        return self.instances.get(issue_id)

    def list_instances(self) -> list[ClaudeInstance]:
        """List all active Claude instances.

        Returns:
            List of active ClaudeInstance objects
        """
        return list(self.instances.values())

    async def create_instance(self, issue_id: str, **kwargs) -> ClaudeInstance:
        """Create a new Claude instance for an issue.

        Args:
            issue_id: GitHub issue ID
            **kwargs: Additional configuration options

        Returns:
            Created ClaudeInstance
        """
        if issue_id in self.instances:
            raise ValueError(f"Instance for issue {issue_id} already exists")

        instance = ClaudeInstance(issue_id=issue_id, **kwargs)
        await instance.initialize()
        self.instances[issue_id] = instance
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
            return True
        return False

    async def cleanup(self) -> None:
        """Clean up all instances and resources."""
        for instance in self.instances.values():
            await instance.cleanup()
        self.instances.clear()
