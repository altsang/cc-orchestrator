"""CLI commands for tmux session management."""

import asyncio
import json
from pathlib import Path

import click

from ..tmux import (
    LayoutTemplate,
    SessionConfig,
    TmuxError,
    get_tmux_service,
)
from .utils import CliError, error_handler, success_message


@click.group()
def tmux() -> None:
    """Manage tmux sessions for Claude Code instances.

    Tmux sessions provide persistent environments for Claude instances,
    allowing them to survive disconnections and providing organized layouts.
    """
    pass


@tmux.command()
@click.argument("session_name")
@click.argument("working_directory", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--instance-id",
    required=True,
    help="Instance ID to associate with this session",
)
@click.option(
    "--layout",
    default="default",
    help="Layout template to use (default, development, claude)",
)
@click.option(
    "--auto-attach",
    is_flag=True,
    help="Automatically attach to session after creation",
)
@click.option(
    "--env",
    multiple=True,
    help="Environment variables (format: KEY=VALUE)",
)
@click.pass_context
@error_handler
def create(
    ctx: click.Context,
    session_name: str,
    working_directory: Path,
    instance_id: str,
    layout: str,
    auto_attach: bool,
    env: tuple[str, ...],
) -> None:
    """Create a new tmux session for a Claude instance.

    SESSION_NAME: Name for the tmux session
    WORKING_DIRECTORY: Directory where Claude will run
    """

    # Parse environment variables
    environment = {}
    for env_var in env:
        if "=" not in env_var:
            raise CliError(f"Invalid environment variable format: {env_var}")
        key, value = env_var.split("=", 1)
        environment[key] = value

    config = SessionConfig(
        session_name=session_name,
        working_directory=working_directory,
        instance_id=instance_id,
        layout_template=layout,
        environment=environment if environment else None,
        auto_attach=auto_attach,
    )

    async def _create_session() -> dict:
        tmux_service = get_tmux_service()
        session_info = await tmux_service.create_session(config)
        return {
            "session_name": session_info.session_name,
            "instance_id": session_info.instance_id,
            "status": session_info.status.value,
            "working_directory": str(session_info.working_directory),
            "layout_template": session_info.layout_template,
            "windows": session_info.windows,
            "created_at": session_info.created_at,
        }

    try:
        result = asyncio.run(_create_session())

        if ctx.obj and ctx.obj.get("json"):
            click.echo(json.dumps(result, indent=2))
        else:
            success_message(f"Created tmux session '{result['session_name']}'")
            click.echo(f"Instance ID: {result['instance_id']}")
            click.echo(f"Layout: {result['layout_template']}")
            click.echo(f"Windows: {', '.join(result['windows'])}")
            if auto_attach:
                click.echo("Session attached automatically")

    except TmuxError as e:
        raise CliError(f"Failed to create tmux session: {e}")


@tmux.command()
@click.argument("session_name")
@click.option(
    "--force",
    is_flag=True,
    help="Force destroy even if clients are attached",
)
@click.pass_context
@error_handler
def destroy(ctx: click.Context, session_name: str, force: bool) -> None:
    """Destroy a tmux session.

    SESSION_NAME: Name of the session to destroy
    """

    async def _destroy_session() -> dict:
        tmux_service = get_tmux_service()
        success = await tmux_service.destroy_session(session_name, force=force)
        return {"success": success, "session_name": session_name}

    try:
        result = asyncio.run(_destroy_session())

        if ctx.obj and ctx.obj.get("json"):
            click.echo(json.dumps(result, indent=2))
        else:
            if result["success"]:
                success_message(f"Destroyed tmux session '{session_name}'")
            else:
                raise CliError(f"Failed to destroy session '{session_name}'")

    except TmuxError as e:
        raise CliError(f"Error destroying session: {e}")


@tmux.command()
@click.argument("session_name")
@click.pass_context
@error_handler
def attach(ctx: click.Context, session_name: str) -> None:
    """Attach to a tmux session.

    SESSION_NAME: Name of the session to attach to
    """

    async def _attach_session() -> dict:
        tmux_service = get_tmux_service()
        success = await tmux_service.attach_session(session_name)
        return {"success": success, "session_name": session_name}

    try:
        result = asyncio.run(_attach_session())

        if ctx.obj and ctx.obj.get("json"):
            click.echo(json.dumps(result, indent=2))
        else:
            if result["success"]:
                success_message(f"Attached to tmux session '{session_name}'")
                click.echo("Use 'Ctrl+b d' to detach from session")
            else:
                raise CliError(f"Failed to attach to session '{session_name}'")

    except TmuxError as e:
        raise CliError(f"Error attaching to session: {e}")


@tmux.command()
@click.argument("session_name")
@click.pass_context
@error_handler
def detach(ctx: click.Context, session_name: str) -> None:
    """Detach from a tmux session.

    SESSION_NAME: Name of the session to detach from
    """

    async def _detach_session() -> dict:
        tmux_service = get_tmux_service()
        success = await tmux_service.detach_session(session_name)
        return {"success": success, "session_name": session_name}

    try:
        result = asyncio.run(_detach_session())

        if ctx.obj and ctx.obj.get("json"):
            click.echo(json.dumps(result, indent=2))
        else:
            if result["success"]:
                success_message(f"Detached from tmux session '{session_name}'")
            else:
                raise CliError(f"Failed to detach from session '{session_name}'")

    except TmuxError as e:
        raise CliError(f"Error detaching from session: {e}")


@tmux.command()
@click.option(
    "--include-orphaned",
    is_flag=True,
    help="Include orphaned sessions not managed by orchestrator",
)
@click.pass_context
@error_handler
def list(ctx: click.Context, include_orphaned: bool) -> None:
    """List all tmux sessions."""

    async def _list_sessions() -> list[dict]:
        tmux_service = get_tmux_service()
        sessions = await tmux_service.list_sessions(include_orphaned=include_orphaned)
        return [
            {
                "session_name": s.session_name,
                "instance_id": s.instance_id,
                "status": s.status.value,
                "working_directory": str(s.working_directory),
                "layout_template": s.layout_template,
                "windows": s.windows,
                "current_window": s.current_window,
                "attached_clients": s.attached_clients,
                "created_at": s.created_at,
            }
            for s in sessions
        ]

    try:
        sessions = asyncio.run(_list_sessions())

        if ctx.obj and ctx.obj.get("json"):
            click.echo(json.dumps(sessions, indent=2))
        else:
            if not sessions:
                click.echo("No tmux sessions found")
                return

            for session in sessions:
                status_indicator = "●" if session["status"] == "active" else "○"
                click.echo(f"{status_indicator} {session['session_name']}")
                click.echo(f"  Instance: {session['instance_id']}")
                click.echo(f"  Status: {session['status']}")
                click.echo(f"  Layout: {session['layout_template']}")
                click.echo(f"  Windows: {', '.join(session['windows'])}")
                if session["current_window"]:
                    click.echo(f"  Current: {session['current_window']}")
                if session["attached_clients"] > 0:
                    click.echo(f"  Clients: {session['attached_clients']}")
                click.echo()

    except TmuxError as e:
        raise CliError(f"Error listing sessions: {e}")


@tmux.command()
@click.argument("session_name")
@click.pass_context
@error_handler
def info(ctx: click.Context, session_name: str) -> None:
    """Get detailed information about a tmux session.

    SESSION_NAME: Name of the session to inspect
    """

    async def _get_session_info() -> dict | None:
        tmux_service = get_tmux_service()
        session_info = await tmux_service.get_session_info(session_name)
        if session_info:
            return {
                "session_name": session_info.session_name,
                "instance_id": session_info.instance_id,
                "status": session_info.status.value,
                "working_directory": str(session_info.working_directory),
                "layout_template": session_info.layout_template,
                "windows": session_info.windows,
                "current_window": session_info.current_window,
                "attached_clients": session_info.attached_clients,
                "created_at": session_info.created_at,
                "last_activity": session_info.last_activity,
                "environment": session_info.environment,
            }
        return None

    try:
        info_data = asyncio.run(_get_session_info())

        if not info_data:
            raise CliError(f"Session '{session_name}' not found")

        if ctx.obj and ctx.obj.get("json"):
            click.echo(json.dumps(info_data, indent=2))
        else:
            click.echo(f"Session: {info_data['session_name']}")
            click.echo(f"Instance ID: {info_data['instance_id']}")
            click.echo(f"Status: {info_data['status']}")
            click.echo(f"Working Directory: {info_data['working_directory']}")
            click.echo(f"Layout Template: {info_data['layout_template']}")
            click.echo(f"Windows: {', '.join(info_data['windows'])}")
            if info_data["current_window"]:
                click.echo(f"Current Window: {info_data['current_window']}")
            click.echo(f"Attached Clients: {info_data['attached_clients']}")

            if info_data["environment"]:
                click.echo("Environment Variables:")
                for key, value in info_data["environment"].items():
                    click.echo(f"  {key}={value}")

    except TmuxError as e:
        raise CliError(f"Error getting session info: {e}")


@tmux.command()
@click.option(
    "--instance-id",
    help="Clean up sessions for specific instance only",
)
@click.option(
    "--force",
    is_flag=True,
    help="Force cleanup even if clients are attached",
)
@click.pass_context
@error_handler
def cleanup(ctx: click.Context, instance_id: str | None, force: bool) -> None:
    """Clean up tmux sessions.

    Removes sessions that are no longer needed or orphaned.
    """

    async def _cleanup_sessions() -> dict:
        tmux_service = get_tmux_service()
        cleaned_up = await tmux_service.cleanup_sessions(
            instance_id=instance_id, force=force
        )
        return {"cleaned_up": cleaned_up, "instance_id": instance_id}

    try:
        result = asyncio.run(_cleanup_sessions())

        if ctx.obj and ctx.obj.get("json"):
            click.echo(json.dumps(result, indent=2))
        else:
            count = result["cleaned_up"]
            if count > 0:
                target = f" for instance {instance_id}" if instance_id else ""
                success_message(f"Cleaned up {count} session(s){target}")
            else:
                click.echo("No sessions to clean up")

    except TmuxError as e:
        raise CliError(f"Error during cleanup: {e}")


@tmux.command()
@click.pass_context
@error_handler
def templates(ctx: click.Context) -> None:
    """List available layout templates."""

    tmux_service = get_tmux_service()
    templates = tmux_service.get_layout_templates()

    if ctx.obj and ctx.obj.get("json"):
        template_data = {}
        for name, template in templates.items():
            template_data[name] = {
                "name": template.name,
                "description": template.description,
                "windows": template.windows,
                "default_pane_command": template.default_pane_command,
            }
        click.echo(json.dumps(template_data, indent=2))
    else:
        if not templates:
            click.echo("No layout templates available")
            return

        click.echo("Available Layout Templates:")
        click.echo()

        for name, template in templates.items():
            click.echo(f"● {name}")
            click.echo(f"  {template.description}")
            click.echo(f"  Windows: {len(template.windows)}")
            window_names = [
                w.get("name", f"window-{i}") for i, w in enumerate(template.windows)
            ]
            click.echo(f"  Layout: {', '.join(window_names)}")
            click.echo()


@tmux.command()
@click.argument("template_name")
@click.argument("template_description")
@click.option(
    "--window",
    multiple=True,
    help="Window configuration (format: name:command)",
)
@click.pass_context
@error_handler
def add_template(
    ctx: click.Context,
    template_name: str,
    template_description: str,
    window: tuple[str, ...],
) -> None:
    """Add a custom layout template.

    TEMPLATE_NAME: Name for the new template
    TEMPLATE_DESCRIPTION: Description of the template
    """

    # Parse window configurations
    windows = []
    for win_config in window:
        if ":" in win_config:
            name, command = win_config.split(":", 1)
        else:
            name = win_config
            command = "bash"

        windows.append(
            {
                "name": name,
                "command": command,
                "panes": [{"command": command}],
            }
        )

    # Use default window if none specified
    if not windows:
        windows = [
            {
                "name": "main",
                "command": "bash",
                "panes": [{"command": "bash"}],
            }
        ]

    template = LayoutTemplate(
        name=template_name,
        description=template_description,
        windows=windows,
    )

    tmux_service = get_tmux_service()
    tmux_service.add_layout_template(template)

    if ctx.obj and ctx.obj.get("json"):
        result = {
            "template_name": template_name,
            "description": template_description,
            "windows": windows,
        }
        click.echo(json.dumps(result, indent=2))
    else:
        success_message(f"Added layout template '{template_name}'")
        click.echo(f"Description: {template_description}")
        click.echo(f"Windows: {len(windows)}")
