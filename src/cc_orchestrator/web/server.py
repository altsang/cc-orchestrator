"""
Web server startup script for CC-Orchestrator.

Provides utilities for starting the FastAPI server with proper configuration.
"""

import os
from typing import Any

import uvicorn

from ..config.loader import load_config
from ..utils.logging import LogContext, get_logger
from .app import app

logger = get_logger(__name__, LogContext.WEB)


def get_server_config() -> dict[str, Any]:
    """
    Get server configuration from environment and config files.

    Returns:
        Dictionary containing server configuration
    """
    # Load orchestrator configuration
    config = load_config()

    # Use configuration values with defaults
    server_config = {
        "host": getattr(config, "web_host", "127.0.0.1"),
        "port": getattr(config, "web_port", 8080),
        "reload": False,  # Default to False for production
        "log_level": getattr(config, "log_level", "INFO").lower(),
        "workers": 1,  # Default to 1 worker
    }

    # Override with environment variables if present
    if "CC_WEB_HOST" in os.environ:
        server_config["host"] = os.environ["CC_WEB_HOST"]
    if "CC_WEB_PORT" in os.environ:
        server_config["port"] = int(os.environ["CC_WEB_PORT"])
    if "CC_WEB_RELOAD" in os.environ:
        server_config["reload"] = os.environ["CC_WEB_RELOAD"].lower() in (
            "true",
            "1",
            "yes",
        )
    if "CC_WEB_LOG_LEVEL" in os.environ:
        server_config["log_level"] = os.environ["CC_WEB_LOG_LEVEL"]
    if "CC_WEB_WORKERS" in os.environ:
        server_config["workers"] = int(os.environ["CC_WEB_WORKERS"])

    return server_config


def run_server(
    host: str | None = None,
    port: int | None = None,
    reload: bool | None = None,
    log_level: str | None = None,
) -> None:
    """
    Run the FastAPI server with specified or default configuration.

    Args:
        host: Host to bind to (overrides config)
        port: Port to bind to (overrides config)
        reload: Enable auto-reload (overrides config)
        log_level: Log level (overrides config)
    """
    config = get_server_config()

    # Override with provided parameters
    if host is not None:
        config["host"] = host
    if port is not None:
        config["port"] = port
    if reload is not None:
        config["reload"] = reload
    if log_level is not None:
        config["log_level"] = log_level

    logger.info(
        "Starting CC-Orchestrator web server",
        host=config["host"],
        port=config["port"],
        reload=config["reload"],
        log_level=config["log_level"],
        workers=config["workers"],
    )

    # Run the server
    uvicorn.run(
        app,
        host=config["host"],
        port=config["port"],
        reload=config["reload"],
        log_level=config["log_level"],
        workers=(
            config["workers"] if not config["reload"] else 1
        ),  # Reload requires single worker
        access_log=True,
    )


def main() -> None:
    """Main entry point for web server script."""
    run_server()


if __name__ == "__main__":
    main()
