"""
FastAPI application for CC-Orchestrator with REST API and WebSocket support.

This module provides:
- REST API endpoints for orchestrator operations
- WebSocket endpoints for real-time updates (ready for Issue #19)
- Connection management and database integration
- Health monitoring and status reporting
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from ..database.connection import DatabaseManager
from .logging_utils import api_logger
from .middleware import (
    LoggingMiddleware,
    RateLimitMiddleware,
    RequestIDMiddleware,
)
from .routers import alerts, config, health, instances, tasks, worktrees
from .routers.v1 import api_router_v1


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application startup and shutdown events."""
    # Startup
    api_logger.info("Starting CC-Orchestrator API server")

    # Initialize database connection (only if not already set for testing)
    if not hasattr(app.state, "db_manager"):
        try:
            db_manager = DatabaseManager()
            app.state.db_manager = db_manager
            api_logger.info("Database connection initialized")
        except Exception as e:
            api_logger.error("Failed to initialize database", error=str(e))
            # For testing/development, create a mock db_manager
            app.state.db_manager = None

    api_logger.info("CC-Orchestrator API server started successfully")

    yield

    # Shutdown
    api_logger.info("Shutting down CC-Orchestrator API server")

    # Close database connections
    if hasattr(app.state, "db_manager") and app.state.db_manager:
        await app.state.db_manager.close()
        api_logger.info("Database connections closed")

    api_logger.info("CC-Orchestrator API server shutdown complete")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="CC-Orchestrator API",
        description="REST API for managing Claude Code instances, tasks, and worktrees",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure based on environment
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add custom middleware
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(RateLimitMiddleware, requests_per_minute=60)

    # Include routers
    app.include_router(api_router_v1, prefix="/api/v1")

    # Legacy routers (will be deprecated)
    app.include_router(instances.router, prefix="/instances", tags=["instances"])
    app.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
    app.include_router(worktrees.router, prefix="/worktrees", tags=["worktrees"])
    app.include_router(config.router, prefix="/config", tags=["config"])
    app.include_router(health.router, prefix="/health", tags=["health"])
    app.include_router(alerts.router, prefix="/alerts", tags=["alerts"])

    # Root endpoint
    @app.get("/", summary="API Health Check")
    async def root() -> dict[str, str]:
        """Check if the API is running."""
        return {
            "message": "CC-Orchestrator API",
            "status": "running",
            "version": "1.0.0",
            "docs": "/docs",
        }

    # Health check endpoint
    @app.get("/ping", summary="Simple Health Check")
    async def ping() -> dict[str, str]:
        """Simple health check endpoint."""
        return {"status": "ok"}

    # Global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        """Handle unexpected exceptions."""
        api_logger.error(
            "Unhandled exception",
            path=str(request.url.path),
            method=request.method,
            error=str(exc),
        )
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "message": "An unexpected error occurred",
            },
        )

    return app


# Create the FastAPI app instance
app = create_app()