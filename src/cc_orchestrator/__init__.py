"""CC-Orchestrator: Claude Code orchestrator for managing multiple instances."""

__version__ = "0.1.0"
__author__ = "CC-Orchestrator Team"
__email__ = "team@cc-orchestrator.dev"

from .core.orchestrator import Orchestrator
from .core.instance import ClaudeInstance

__all__ = ["Orchestrator", "ClaudeInstance", "__version__"]