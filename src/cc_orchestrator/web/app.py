"""FastAPI web application for CC-Orchestrator dashboard."""

import os
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from time import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse

from ..database.connection import DatabaseManager
from .exceptions import CCOrchestratorAPIException
from .routers import auth_router, websocket_router
from .routers.v1 import api_router_v1


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application lifespan events."""
    # Startup
    db_manager = DatabaseManager()
    db_manager.create_tables()
    app.state.db_manager = db_manager  # Store in app state for dependencies
    yield
    # Shutdown - cleanup if needed


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="CC-Orchestrator API",
        description="Claude Code Orchestrator Dashboard API",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Add CORS middleware with environment-based configuration
    debug = os.getenv("DEBUG", "false").lower() == "true"
    if debug:
        # Development origins
        allowed_origins = [
            "http://localhost:3000",
            "http://localhost:5173",
        ]
    else:
        # Production validation - ensure required environment variables are set
        frontend_url = os.getenv("FRONTEND_URL")
        if not frontend_url:
            raise ValueError(
                "FRONTEND_URL must be set when DEBUG=false (production mode)"
            )

        # Validate the frontend URL format
        if not (
            frontend_url.startswith("http://") or frontend_url.startswith("https://")
        ):
            raise ValueError("FRONTEND_URL must be a valid HTTP(S) URL")

        allowed_origins = [frontend_url]

        # Additional production environment validation
        if not os.getenv("JWT_SECRET_KEY"):
            raise ValueError("JWT_SECRET_KEY must be set in production mode")

        # Warn about HTTP in production
        if frontend_url.startswith("http://") and not frontend_url.startswith(
            "http://localhost"
        ):
            import logging

            logging.warning(
                "Using HTTP (not HTTPS) for FRONTEND_URL in production mode. "
                "Consider using HTTPS for security."
            )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", "Accept"],
    )

    # Add request ID and rate limiting middleware
    @app.middleware("http")
    async def add_request_headers(request: Request, call_next):
        """Add request ID and rate limiting headers."""
        # Generate a unique request ID
        request_id = str(uuid.uuid4())

        # Process the request
        response = await call_next(request)

        # Add headers to response
        response.headers["X-Request-ID"] = request_id
        response.headers["X-RateLimit-Limit"] = "1000"
        response.headers["X-RateLimit-Remaining"] = "999"
        response.headers["X-RateLimit-Reset"] = str(int(time()) + 3600)

        return response

    # Add exception handlers
    @app.exception_handler(CCOrchestratorAPIException)
    async def api_exception_handler(
        request: Request, exc: CCOrchestratorAPIException
    ) -> JSONResponse:
        """Handle custom API exceptions."""
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.__class__.__name__,
                "message": exc.message,
                "status_code": exc.status_code,
            },
        )

    # Include routers
    app.include_router(auth_router, prefix="/auth")
    app.include_router(api_router_v1, prefix="/api/v1")
    app.include_router(websocket_router, prefix="/ws")

    @app.get("/", response_class=HTMLResponse)
    async def root() -> str:
        """Serve the dashboard root page."""
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>CC-Orchestrator Dashboard</title>
        </head>
        <body>
            <h1>CC-Orchestrator Dashboard</h1>
            <p>API Documentation: <a href="/docs">/docs</a></p>
            <p>React Frontend will be served here</p>
        </body>
        </html>
        """

    @app.get("/health")
    async def health_check() -> dict[str, str]:
        """Health check endpoint."""
        return {"status": "healthy"}

    @app.get("/ping")
    async def ping() -> dict[str, str]:
        """Ping endpoint for simple health check."""
        return {"status": "ok"}

    return app


# Create the application instance
app = create_app()
