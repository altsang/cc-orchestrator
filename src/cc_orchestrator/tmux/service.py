"""
Tmux session management service.

This module provides comprehensive tmux session management for Claude Code instances,
including session creation, lifecycle management, layout templates, and multi-user support.
"""

import asyncio
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

import libtmux

from .logging_utils import (
    log_layout_setup,
    log_orphaned_sessions,
    log_session_attach,
    log_session_cleanup,
    log_session_detach,
    log_session_list,
    log_session_operation,
    tmux_logger,
)


class SessionStatus(Enum):
    """Status of a tmux session."""

    CREATING = "creating"
    ACTIVE = "active"
    DETACHED = "detached"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class SessionConfig:
    """Configuration for tmux session creation."""

    session_name: str
    working_directory: Path
    instance_id: str
    layout_template: str = "default"
    environment: dict[str, str] | None = None
    window_configs: list[dict[str, Any]] | None = None
    auto_attach: bool = False
    persist_after_exit: bool = True


@dataclass
class SessionInfo:
    """Information about a tmux session."""

    session_name: str
    instance_id: str
    status: SessionStatus
    working_directory: Path
    layout_template: str
    created_at: float
    windows: list[str]
    current_window: str | None = None
    last_activity: float | None = None
    attached_clients: int = 0
    environment: dict[str, str] | None = None


class LayoutTemplate:
    """Tmux layout template definition."""

    def __init__(
        self,
        name: str,
        description: str,
        windows: list[dict[str, Any]],
        default_pane_command: str = "bash",
    ):
        """Initialize layout template.

        Args:
            name: Template name
            description: Template description
            windows: List of window configurations
            default_pane_command: Default command for new panes
        """
        self.name = name
        self.description = description
        self.windows = windows
        self.default_pane_command = default_pane_command


class TmuxService:
    """Comprehensive tmux session management service."""

    def __init__(self):
        """Initialize tmux service."""
        self._server = libtmux.Server()
        self._sessions: dict[str, SessionInfo] = {}
        self._layout_templates: dict[str, LayoutTemplate] = {}
        self._session_prefix = "cc-orchestrator"
        self._init_default_templates()
        tmux_logger.info("Tmux service initialized")

    async def create_session(self, config: SessionConfig) -> SessionInfo:
        """Create a new tmux session.

        Args:
            config: Session configuration

        Returns:
            SessionInfo object with session details

        Raises:
            TmuxError: If session creation fails
        """
        session_name = self._normalize_session_name(config.session_name)

        if await self.session_exists(session_name):
            raise TmuxError(f"Session {session_name} already exists")

        log_session_operation("create", session_name, "starting")

        try:
            # Ensure working directory exists
            config.working_directory.mkdir(parents=True, exist_ok=True)

            # Create tmux session
            session = self._server.new_session(
                session_name=session_name,
                start_directory=str(config.working_directory),
                detach=True,  # Always create detached
            )

            # Configure environment if provided
            if config.environment:
                for key, value in config.environment.items():
                    session.set_environment(key, value)

            # Apply layout template
            layout_template = self._layout_templates.get(
                config.layout_template, self._layout_templates["default"]
            )
            await self._apply_layout_template(session, layout_template)

            # Create session info
            session_info = SessionInfo(
                session_name=session_name,
                instance_id=config.instance_id,
                status=SessionStatus.ACTIVE,
                working_directory=config.working_directory,
                layout_template=config.layout_template,
                created_at=asyncio.get_event_loop().time(),
                windows=[w.name for w in session.windows],
                current_window=session.windows[0].name if session.windows else None,
                environment=config.environment,
            )

            # Store session info
            self._sessions[session_name] = session_info

            # Auto-attach if requested
            if config.auto_attach:
                await self.attach_session(session_name)

            log_session_operation("create", session_name, "success")
            tmux_logger.info(
                "Tmux session created successfully",
                session_name=session_name,
                instance_id=config.instance_id,
                layout_template=config.layout_template,
            )

            return session_info

        except Exception as e:
            log_session_operation("create", session_name, "error", {"error": str(e)})
            raise TmuxError(f"Failed to create session {session_name}: {e}")

    async def destroy_session(self, session_name: str, force: bool = False) -> bool:
        """Destroy a tmux session.

        Args:
            session_name: Name of session to destroy
            force: Force destruction even if clients are attached

        Returns:
            True if session was destroyed successfully
        """
        session_name = self._normalize_session_name(session_name)

        if not await self.session_exists(session_name):
            tmux_logger.warning(f"Session {session_name} does not exist")
            return False

        log_session_cleanup(session_name, force, "manual")

        try:
            session = self._server.sessions.get(session_name=session_name)
            if not session:
                return False

            # Check for attached clients
            if not force and session.attached:
                raise TmuxError(
                    f"Session {session_name} has attached clients. Use force=True to destroy anyway."
                )

            # Kill session
            session.kill()

            # Remove from tracking
            if session_name in self._sessions:
                del self._sessions[session_name]

            log_session_operation("destroy", session_name, "success")
            tmux_logger.info("Tmux session destroyed", session_name=session_name)

            return True

        except Exception as e:
            log_session_operation("destroy", session_name, "error", {"error": str(e)})
            tmux_logger.error(
                "Failed to destroy session", session_name=session_name, error=str(e)
            )
            return False

    async def attach_session(self, session_name: str) -> bool:
        """Attach to a tmux session.

        Args:
            session_name: Name of session to attach to

        Returns:
            True if attachment was successful
        """
        session_name = self._normalize_session_name(session_name)

        if not await self.session_exists(session_name):
            tmux_logger.error(f"Cannot attach to non-existent session {session_name}")
            return False

        try:
            session = self._server.sessions.get(session_name=session_name)
            if not session:
                return False

            # Update session info
            if session_name in self._sessions:
                self._sessions[session_name].status = SessionStatus.ACTIVE
                self._sessions[session_name].last_activity = (
                    asyncio.get_event_loop().time()
                )

            # Log attachment
            instance_id = None
            if session_name in self._sessions:
                instance_id = self._sessions[session_name].instance_id

            log_session_attach(session_name, instance_id)
            return True

        except Exception as e:
            tmux_logger.error(
                "Failed to attach to session", session_name=session_name, error=str(e)
            )
            return False

    async def detach_session(self, session_name: str) -> bool:
        """Detach from a tmux session.

        Args:
            session_name: Name of session to detach from

        Returns:
            True if detachment was successful
        """
        session_name = self._normalize_session_name(session_name)

        try:
            session = self._server.sessions.get(session_name=session_name)
            if not session:
                return False

            # Detach all clients
            session.detach()

            # Update session info
            if session_name in self._sessions:
                self._sessions[session_name].status = SessionStatus.DETACHED
                self._sessions[session_name].last_activity = (
                    asyncio.get_event_loop().time()
                )

            # Log detachment
            instance_id = None
            if session_name in self._sessions:
                instance_id = self._sessions[session_name].instance_id

            log_session_detach(session_name, instance_id)
            return True

        except Exception as e:
            tmux_logger.error(
                "Failed to detach from session", session_name=session_name, error=str(e)
            )
            return False

    async def session_exists(self, session_name: str) -> bool:
        """Check if a tmux session exists.

        Args:
            session_name: Name of session to check

        Returns:
            True if session exists
        """
        session_name = self._normalize_session_name(session_name)
        try:
            session = self._server.sessions.get(session_name=session_name)
            return session is not None
        except Exception:
            return False

    async def list_sessions(self, include_orphaned: bool = False) -> list[SessionInfo]:
        """List all tmux sessions.

        Args:
            include_orphaned: Include sessions not managed by this service

        Returns:
            List of SessionInfo objects
        """
        sessions = []

        try:
            # Get all tmux sessions
            tmux_sessions = self._server.sessions

            # Process managed sessions
            for session in tmux_sessions:
                if session.name.startswith(self._session_prefix):
                    session_info = await self._get_session_info(session)
                    if session_info:
                        sessions.append(session_info)

            # Detect orphaned sessions if requested
            if include_orphaned:
                orphaned = await self._detect_orphaned_sessions()
                log_orphaned_sessions(orphaned)

            log_session_list([{"name": s.session_name} for s in sessions])
            return sessions

        except Exception as e:
            tmux_logger.error("Failed to list sessions", error=str(e))
            return []

    async def get_session_info(self, session_name: str) -> SessionInfo | None:
        """Get information about a specific session.

        Args:
            session_name: Name of session

        Returns:
            SessionInfo object or None if session doesn't exist
        """
        session_name = self._normalize_session_name(session_name)

        if session_name in self._sessions:
            return self._sessions[session_name]

        # Try to get info from tmux directly
        try:
            session = self._server.sessions.get(session_name=session_name)
            if session:
                return await self._get_session_info(session)
        except Exception as e:
            tmux_logger.debug(f"Could not get session info for {session_name}: {e}")

        return None

    async def cleanup_sessions(
        self, instance_id: str | None = None, force: bool = False
    ) -> int:
        """Clean up tmux sessions.

        Args:
            instance_id: Optional instance ID to filter sessions
            force: Force cleanup even if clients are attached

        Returns:
            Number of sessions cleaned up
        """
        cleaned_up = 0

        try:
            sessions_to_cleanup = []

            if instance_id:
                # Clean up sessions for specific instance
                for session_name, session_info in self._sessions.items():
                    if session_info.instance_id == instance_id:
                        sessions_to_cleanup.append(session_name)
            else:
                # Clean up all managed sessions
                sessions_to_cleanup = list(self._sessions.keys())

            for session_name in sessions_to_cleanup:
                if await self.destroy_session(session_name, force=force):
                    cleaned_up += 1

            tmux_logger.info(
                "Session cleanup completed",
                cleaned_up=cleaned_up,
                instance_id=instance_id,
                force=force,
            )

            return cleaned_up

        except Exception as e:
            tmux_logger.error("Session cleanup failed", error=str(e))
            return cleaned_up

    def add_layout_template(self, template: LayoutTemplate) -> None:
        """Add a custom layout template.

        Args:
            template: LayoutTemplate object
        """
        self._layout_templates[template.name] = template
        tmux_logger.info(
            "Layout template added",
            template_name=template.name,
            description=template.description,
        )

    def get_layout_templates(self) -> dict[str, LayoutTemplate]:
        """Get all available layout templates.

        Returns:
            Dictionary mapping template names to LayoutTemplate objects
        """
        return self._layout_templates.copy()

    def _normalize_session_name(self, session_name: str) -> str:
        """Normalize session name with prefix.

        Args:
            session_name: Original session name

        Returns:
            Normalized session name with prefix
        """
        if not session_name.startswith(self._session_prefix):
            return f"{self._session_prefix}-{session_name}"
        return session_name

    def _init_default_templates(self) -> None:
        """Initialize default layout templates."""
        # Default template - single window
        default_template = LayoutTemplate(
            name="default",
            description="Single window with default shell",
            windows=[
                {
                    "name": "main",
                    "command": "bash",
                    "panes": [{"command": "bash"}],
                }
            ],
        )

        # Development template - multiple windows
        dev_template = LayoutTemplate(
            name="development",
            description="Development layout with editor, terminal, and monitoring",
            windows=[
                {
                    "name": "editor",
                    "command": "bash",
                    "panes": [{"command": "bash"}],
                },
                {
                    "name": "terminal",
                    "command": "bash",
                    "panes": [{"command": "bash"}],
                },
                {
                    "name": "monitoring",
                    "command": "bash",
                    "panes": [
                        {"command": "top"},
                        {"command": "tail -f /var/log/syslog", "split": "horizontal"},
                    ],
                },
            ],
        )

        # Claude template - optimized for Claude Code usage
        claude_template = LayoutTemplate(
            name="claude",
            description="Claude Code optimized layout",
            windows=[
                {
                    "name": "claude",
                    "command": "claude --continue",
                    "panes": [{"command": "claude --continue"}],
                },
                {
                    "name": "shell",
                    "command": "bash",
                    "panes": [{"command": "bash"}],
                },
            ],
        )

        self._layout_templates.update(
            {
                "default": default_template,
                "development": dev_template,
                "claude": claude_template,
            }
        )

    async def _apply_layout_template(
        self, session: libtmux.Session, template: LayoutTemplate
    ) -> None:
        """Apply a layout template to a session.

        Args:
            session: Tmux session object
            template: Layout template to apply
        """
        try:
            # Remove default window if it exists and we have custom windows
            if template.windows and session.windows:
                default_window = session.windows[0]
                if default_window and len(template.windows) > 0:
                    default_window.kill()

            # Create windows from template
            for i, window_config in enumerate(template.windows):
                window_name = window_config.get("name", f"window-{i}")
                window_command = window_config.get(
                    "command", template.default_pane_command
                )

                # Create window
                if i == 0 and not session.windows:
                    # First window - use session's default window
                    window = session.new_window(
                        window_name=window_name,
                        start_directory=session.start_directory,
                        attach=False,
                    )
                else:
                    window = session.new_window(
                        window_name=window_name,
                        start_directory=session.start_directory,
                        attach=False,
                    )

                # Configure panes
                panes_config = window_config.get("panes", [{"command": window_command}])
                for j, pane_config in enumerate(panes_config):
                    pane_command = pane_config.get(
                        "command", template.default_pane_command
                    )

                    if j == 0:
                        # First pane - use existing pane
                        if window.panes:
                            pane = window.panes[0]
                            pane.send_keys(pane_command)
                    else:
                        # Additional panes - split existing panes
                        split_direction = pane_config.get("split", "vertical")
                        if split_direction == "horizontal":
                            pane = window.split_window(vertical=False, attach=False)
                        else:
                            pane = window.split_window(vertical=True, attach=False)
                        pane.send_keys(pane_command)

            log_layout_setup(
                session.name,
                template.name,
                [w.get("name", f"window-{i}") for i, w in enumerate(template.windows)],
            )

        except Exception as e:
            tmux_logger.error(
                "Failed to apply layout template",
                session_name=session.name,
                template_name=template.name,
                error=str(e),
            )
            raise TmuxError(f"Failed to apply layout template {template.name}: {e}")

    async def _get_session_info(self, session: libtmux.Session) -> SessionInfo | None:
        """Get session info from tmux session object.

        Args:
            session: Tmux session object

        Returns:
            SessionInfo object or None
        """
        try:
            # Try to get from our tracking first
            if session.name in self._sessions:
                session_info = self._sessions[session.name]
                # Update dynamic info
                session_info.windows = [w.name for w in session.windows]
                session_info.current_window = (
                    session.active_window.name if session.active_window else None
                )
                session_info.attached_clients = (
                    len(session.clients) if hasattr(session, "clients") else 0
                )
                return session_info

            # Create basic info from tmux session
            instance_id = self._extract_instance_id(session.name)
            return SessionInfo(
                session_name=session.name,
                instance_id=instance_id,
                status=(
                    SessionStatus.ACTIVE if session.attached else SessionStatus.DETACHED
                ),
                working_directory=Path(session.start_directory or "/"),
                layout_template="unknown",
                created_at=0.0,  # Not available from tmux
                windows=[w.name for w in session.windows],
                current_window=(
                    session.active_window.name if session.active_window else None
                ),
                attached_clients=(
                    len(session.clients) if hasattr(session, "clients") else 0
                ),
            )

        except Exception as e:
            tmux_logger.debug(f"Error getting session info: {e}")
            return None

    def _extract_instance_id(self, session_name: str) -> str:
        """Extract instance ID from session name.

        Args:
            session_name: Tmux session name

        Returns:
            Instance ID
        """
        # Remove prefix and use remainder as instance ID
        if session_name.startswith(self._session_prefix):
            return session_name[len(self._session_prefix) + 1 :]
        return session_name

    async def _detect_orphaned_sessions(self) -> list[str]:
        """Detect orphaned tmux sessions.

        Returns:
            List of orphaned session names
        """
        orphaned = []
        try:
            all_sessions = self._server.sessions
            for session in all_sessions:
                if (
                    session.name.startswith(self._session_prefix)
                    and session.name not in self._sessions
                ):
                    orphaned.append(session.name)
        except Exception as e:
            tmux_logger.debug(f"Error detecting orphaned sessions: {e}")

        return orphaned


class TmuxError(Exception):
    """Exception raised for tmux operation errors."""

    def __init__(self, message: str, session_name: str | None = None):
        """Initialize TmuxError.

        Args:
            message: Error message
            session_name: Optional session name
        """
        super().__init__(message)
        self.session_name = session_name


# Global tmux service instance
_tmux_service: TmuxService | None = None


def get_tmux_service() -> TmuxService:
    """Get the global tmux service instance.

    Returns:
        TmuxService instance
    """
    global _tmux_service
    if _tmux_service is None:
        _tmux_service = TmuxService()
    return _tmux_service


async def cleanup_tmux_service() -> None:
    """Clean up the global tmux service."""
    global _tmux_service
    if _tmux_service is not None:
        await _tmux_service.cleanup_sessions(force=True)
        _tmux_service = None
