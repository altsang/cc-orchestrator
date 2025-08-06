"""
FastAPI application with WebSocket support for CC-Orchestrator.

This module provides:
- REST API endpoints for orchestrator operations
- WebSocket endpoints for real-time updates
- Connection management and message broadcasting
- Health monitoring and status reporting
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import router as api_router
from .websocket import router as websocket_router
from .websocket.manager import WebSocketConfig, connection_manager


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Manage application lifespan events.

    Handles startup and shutdown tasks for the FastAPI application.
    """
    # Startup
    await connection_manager.initialize()

    yield

    # Shutdown
    await connection_manager.cleanup()


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.

    Returns:
        Configured FastAPI application instance
    """
    app = FastAPI(
        title="CC-Orchestrator API",
        description="REST API and WebSocket interface for Claude Code orchestration",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # Add CORS middleware with configurable origins
    websocket_config = WebSocketConfig.from_environment()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=websocket_config.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(api_router, prefix="/api/v1")
    app.include_router(websocket_router, prefix="/ws")

    @app.get("/health")
    async def health_check() -> dict[str, str]:
        """Health check endpoint."""
        return {"status": "healthy", "service": "cc-orchestrator"}

    return app


# Application instance
app = create_app()
