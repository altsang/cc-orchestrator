"""FastAPI web application for CC-Orchestrator dashboard."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from ..database.connection import DatabaseManager
from .routers import api_router, websocket_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application lifespan events."""
    # Startup
    db_manager = DatabaseManager()
    db_manager.create_tables()
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

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://localhost:5173",
        ],  # React dev servers
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(api_router, prefix="/api/v1")
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

    return app


# Create the application instance
app = create_app()
