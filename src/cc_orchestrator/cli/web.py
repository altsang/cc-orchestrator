"""Web interface commands."""

import click


@click.group()
def web() -> None:
    """Manage the web interface."""
    pass


@web.command()
@click.option("--port", "-p", default=8000, help="Port to run on")
@click.option("--host", "-h", default="localhost", help="Host to bind to")
def start(port: int, host: str) -> None:
    """Start the web interface."""
    click.echo(f"Starting web interface on {host}:{port} - to be implemented")


@web.command()
def stop() -> None:
    """Stop the web interface."""
    click.echo("Stopping web interface - to be implemented")


@web.command()
def status() -> None:
    """Show web interface status."""
    click.echo("Web interface status - to be implemented")
