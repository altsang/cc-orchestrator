"""Shared enums for cc-orchestrator."""

from enum import Enum


class InstanceStatus(Enum):
    """Status of a Claude Code instance."""

    INITIALIZING = "initializing"
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"


# Alias for compatibility
InstanceState = InstanceStatus
