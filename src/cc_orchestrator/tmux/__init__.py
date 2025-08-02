"""
Tmux session management for Claude Code orchestrator.

This package provides comprehensive tmux session management including:
- Session creation and lifecycle management
- Layout templates and window configuration
- Multi-user session support
- Integration with process management
- Session discovery and cleanup
"""

from .service import (
    LayoutTemplate,
    SessionConfig,
    SessionInfo,
    SessionStatus,
    TmuxError,
    TmuxService,
    cleanup_tmux_service,
    get_tmux_service,
)

__all__ = [
    "LayoutTemplate",
    "SessionConfig",
    "SessionInfo",
    "SessionStatus",
    "TmuxError",
    "TmuxService",
    "cleanup_tmux_service",
    "get_tmux_service",
]
