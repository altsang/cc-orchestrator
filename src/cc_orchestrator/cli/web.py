"""Web interface commands."""

import sys

import click
import uvicorn


@click.group()
def web() -> None:
    """Manage the web interface."""
    pass


@web.command()
@click.option("--port", "-p", default=8000, help="Port to run on")
@click.option("--host", "-h", default="127.0.0.1", help="Host to bind to")
@click.option("--reload", is_flag=True, help="Enable auto-reload for development")
def start(port: int, host: str, reload: bool) -> None:
    """Start the web interface."""
    click.echo(f"Starting CC-Orchestrator web interface on {host}:{port}")

    if reload:
        click.echo("Development mode: auto-reload enabled")

    try:
        uvicorn.run(
            "cc_orchestrator.web.app:app",
            host=host,
            port=port,
            reload=reload,
            log_level="info",
        )
    except KeyboardInterrupt:
        click.echo("\nShutting down web interface...")
    except Exception as e:
        click.echo(f"Failed to start web interface: {e}")
        sys.exit(1)


@web.command()
def stop() -> None:
    """Stop the web interface."""
    click.echo("Stopping web interface - manual stop required (Ctrl+C)")
    click.echo("Process management for web server to be implemented")


@web.command()
def status() -> None:
    """Show web interface status."""
    click.echo("Web interface status check - to be implemented")
    click.echo("Process detection and health check to be added")
