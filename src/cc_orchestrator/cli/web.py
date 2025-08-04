"""Web interface commands."""

import signal
import sys

import click
import psutil

from ..utils.logging import LogContext, get_logger
from ..web.server import run_server

logger = get_logger(__name__, LogContext.CLI)


@click.group()
def web() -> None:
    """Manage the web interface."""
    pass


@web.command()
@click.option(
    "--port", "-p", default=None, type=int, help="Port to run on (default: 8080)"
)
@click.option("--host", "-h", default=None, help="Host to bind to (default: 127.0.0.1)")
@click.option("--reload", is_flag=True, help="Enable auto-reload for development")
@click.option(
    "--log-level", default=None, help="Log level (debug, info, warning, error)"
)
def start(
    port: int | None, host: str | None, reload: bool, log_level: str | None
) -> None:
    """Start the web interface with FastAPI and WebSocket support."""
    try:
        click.echo("🚀 Starting CC-Orchestrator web interface...")

        if reload:
            click.echo("🔄 Development mode enabled with auto-reload")

        # This will block until the server is stopped
        run_server(host=host, port=port, reload=reload, log_level=log_level)

    except KeyboardInterrupt:
        click.echo("\n👋 Shutting down web interface...")
        sys.exit(0)
    except Exception as e:
        logger.error("Failed to start web interface", error=str(e))
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@web.command()
@click.option("--port", "-p", default=8080, help="Port to check (default: 8080)")
def stop(port: int) -> None:
    """Stop the web interface by finding and terminating the process."""
    try:
        # Find processes listening on the specified port
        processes_found = []

        for proc in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                connections = proc.connections()
                for conn in connections:
                    if conn.laddr.port == port and conn.status == psutil.CONN_LISTEN:
                        processes_found.append(proc)
                        break
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

        if not processes_found:
            click.echo(f"No web interface process found on port {port}")
            return

        # Stop the processes
        for proc in processes_found:
            try:
                click.echo(f"🛑 Stopping web interface (PID: {proc.pid})...")
                proc.send_signal(signal.SIGTERM)

                # Wait for graceful shutdown
                try:
                    proc.wait(timeout=5)
                    click.echo("✅ Web interface stopped successfully")
                except psutil.TimeoutExpired:
                    click.echo("⏰ Graceful shutdown timed out, forcing termination...")
                    proc.kill()
                    click.echo("🔥 Web interface forcefully terminated")

            except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                click.echo(f"❌ Could not stop process {proc.pid}: {e}", err=True)

    except Exception as e:
        logger.error("Failed to stop web interface", error=str(e))
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)


@web.command()
@click.option("--port", "-p", default=8080, help="Port to check (default: 8080)")
def status(port: int) -> None:
    """Show web interface status."""
    try:
        import httpx

        # Check if server is responding
        try:
            response = httpx.get(f"http://127.0.0.1:{port}/health", timeout=5.0)
            if response.status_code == 200:
                data = response.json()
                click.echo(f"✅ Web interface is running on port {port}")
                click.echo(f"   Status: {data.get('status', 'unknown')}")
                click.echo(f"   Service: {data.get('service', 'unknown')}")

                # Get WebSocket stats if available
                try:
                    ws_response = httpx.get(
                        f"http://127.0.0.1:{port}/api/v1/websocket/stats", timeout=5.0
                    )
                    if ws_response.status_code == 200:
                        ws_data = ws_response.json()
                        click.echo(
                            f"   Active WebSocket connections: {ws_data.get('active_connections', 0)}"
                        )
                        click.echo(
                            f"   Total connections: {ws_data.get('total_connections', 0)}"
                        )
                        click.echo(
                            f"   Messages sent: {ws_data.get('messages_sent', 0)}"
                        )
                        click.echo(
                            f"   Messages received: {ws_data.get('messages_received', 0)}"
                        )
                except Exception:
                    pass  # WebSocket stats are optional

            else:
                click.echo(
                    f"⚠️  Web interface responded with status {response.status_code}"
                )

        except httpx.ConnectError:
            click.echo(f"❌ Web interface is not running on port {port}")
        except httpx.TimeoutException:
            click.echo(f"⏰ Web interface on port {port} is not responding (timeout)")
        except Exception as e:
            click.echo(f"❌ Error checking web interface: {e}")

        # Check for processes listening on the port
        processes_found = []
        for proc in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                connections = proc.connections()
                for conn in connections:
                    if conn.laddr.port == port and conn.status == psutil.CONN_LISTEN:
                        processes_found.append(proc)
                        break
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

        if processes_found:
            click.echo(f"\n🔍 Processes listening on port {port}:")
            for proc in processes_found:
                try:
                    click.echo(
                        f"   PID {proc.pid}: {proc.name()} - {' '.join(proc.cmdline())}"
                    )
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    click.echo(f"   PID {proc.pid}: (access denied)")
        else:
            click.echo(f"\n🔍 No processes listening on port {port}")

    except Exception as e:
        logger.error("Failed to check web interface status", error=str(e))
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)
