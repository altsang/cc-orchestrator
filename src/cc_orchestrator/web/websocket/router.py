"""
WebSocket router for real-time communication endpoints.

Provides WebSocket endpoints for different types of real-time updates.
"""

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from ..dependencies import CurrentUser
from ..middlewares.rate_limiter import rate_limiter
from .manager import connection_manager

router = APIRouter()


async def authenticate_websocket_token(token: str | None) -> CurrentUser | None:
    """
    Authenticate WebSocket connection using token parameter.

    Args:
        token: Authentication token from query parameter

    Returns:
        CurrentUser if authentication successful, None otherwise
    """
    if not token:
        return None

    # TODO: Implement actual token validation
    # For now, use basic validation for development
    if token == "development-token":
        return CurrentUser(user_id="websocket_user", permissions=["read", "write"])

    # In production, validate JWT token, API key, etc.
    # This is a placeholder implementation
    return None


@router.websocket("/connect")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(..., description="Authentication token")) -> None:
    """
    Main WebSocket endpoint for client connections.

    Handles the full connection lifecycle including:
    - Connection establishment with authentication
    - Message processing
    - Graceful disconnection
    """
    # Authenticate WebSocket connection
    user = await authenticate_websocket_token(token)
    if not user:
        await websocket.close(code=1008, reason="Authentication required")
        return

    # Get client IP (handle proxy headers)
    client_ip = websocket.client.host if websocket.client else "unknown"

    # Check WebSocket rate limiting
    if not rate_limiter.check_websocket_rate_limit(client_ip):
        await websocket.close(code=1008, reason="Rate limit exceeded")
        return

    # Accept connection and get connection ID
    connection_id = await connection_manager.connect(websocket, client_ip)

    try:
        while True:
            # Wait for incoming messages
            message = await websocket.receive_text()
            await connection_manager.handle_message(connection_id, message)

    except WebSocketDisconnect:
        await connection_manager.disconnect(connection_id, "client_disconnect")
    except Exception as e:
        await connection_manager.disconnect(connection_id, f"error: {str(e)}")


@router.websocket("/instances/{instance_id}")
async def instance_websocket(websocket: WebSocket, instance_id: str, token: str = Query(..., description="Authentication token")) -> None:
    """
    WebSocket endpoint for instance-specific updates.

    Automatically subscribes to updates for a specific instance.
    """
    # Authenticate WebSocket connection
    user = await authenticate_websocket_token(token)
    if not user:
        await websocket.close(code=1008, reason="Authentication required")
        return

    client_ip = websocket.client.host if websocket.client else "unknown"

    # Check WebSocket rate limiting
    if not rate_limiter.check_websocket_rate_limit(client_ip):
        await websocket.close(code=1008, reason="Rate limit exceeded")
        return

    connection_id = await connection_manager.connect(websocket, client_ip)

    # Auto-subscribe to instance updates
    await connection_manager.subscribe(connection_id, f"instance:{instance_id}")

    try:
        while True:
            message = await websocket.receive_text()
            await connection_manager.handle_message(connection_id, message)

    except WebSocketDisconnect:
        await connection_manager.disconnect(connection_id, "client_disconnect")
    except Exception as e:
        await connection_manager.disconnect(connection_id, f"error: {str(e)}")


@router.websocket("/tasks/{task_id}")
async def task_websocket(websocket: WebSocket, task_id: str, token: str = Query(..., description="Authentication token")) -> None:
    """
    WebSocket endpoint for task-specific updates.

    Automatically subscribes to updates for a specific task.
    """
    # Authenticate WebSocket connection
    user = await authenticate_websocket_token(token)
    if not user:
        await websocket.close(code=1008, reason="Authentication required")
        return

    client_ip = websocket.client.host if websocket.client else "unknown"

    # Check WebSocket rate limiting
    if not rate_limiter.check_websocket_rate_limit(client_ip):
        await websocket.close(code=1008, reason="Rate limit exceeded")
        return

    connection_id = await connection_manager.connect(websocket, client_ip)

    # Auto-subscribe to task updates
    await connection_manager.subscribe(connection_id, f"task:{task_id}")

    try:
        while True:
            message = await websocket.receive_text()
            await connection_manager.handle_message(connection_id, message)

    except WebSocketDisconnect:
        await connection_manager.disconnect(connection_id, "client_disconnect")
    except Exception as e:
        await connection_manager.disconnect(connection_id, f"error: {str(e)}")


@router.websocket("/logs")
async def logs_websocket(websocket: WebSocket, token: str = Query(..., description="Authentication token")) -> None:
    """
    WebSocket endpoint for streaming logs.

    Provides real-time log streaming functionality.
    """
    # Authenticate WebSocket connection
    user = await authenticate_websocket_token(token)
    if not user:
        await websocket.close(code=1008, reason="Authentication required")
        return

    client_ip = websocket.client.host if websocket.client else "unknown"

    # Check WebSocket rate limiting
    if not rate_limiter.check_websocket_rate_limit(client_ip):
        await websocket.close(code=1008, reason="Rate limit exceeded")
        return

    connection_id = await connection_manager.connect(websocket, client_ip)

    # Auto-subscribe to log updates
    await connection_manager.subscribe(connection_id, "logs")

    try:
        while True:
            message = await websocket.receive_text()
            await connection_manager.handle_message(connection_id, message)

    except WebSocketDisconnect:
        await connection_manager.disconnect(connection_id, "client_disconnect")
    except Exception as e:
        await connection_manager.disconnect(connection_id, f"error: {str(e)}")


@router.websocket("/dashboard")
async def dashboard_websocket(websocket: WebSocket, token: str = Query(..., description="Authentication token")) -> None:
    """
    WebSocket endpoint for dashboard updates.

    Provides comprehensive real-time updates for the web dashboard.
    """
    # Authenticate WebSocket connection
    user = await authenticate_websocket_token(token)
    if not user:
        await websocket.close(code=1008, reason="Authentication required")
        return

    client_ip = websocket.client.host if websocket.client else "unknown"

    # Check WebSocket rate limiting
    if not rate_limiter.check_websocket_rate_limit(client_ip):
        await websocket.close(code=1008, reason="Rate limit exceeded")
        return

    connection_id = await connection_manager.connect(websocket, client_ip)

    # Auto-subscribe to dashboard updates
    dashboard_topics = [
        "dashboard",
        "instances",
        "tasks",
        "system_status",
        "alerts",
    ]

    for topic in dashboard_topics:
        await connection_manager.subscribe(connection_id, topic)

    try:
        while True:
            message = await websocket.receive_text()
            await connection_manager.handle_message(connection_id, message)

    except WebSocketDisconnect:
        await connection_manager.disconnect(connection_id, "client_disconnect")
    except Exception as e:
        await connection_manager.disconnect(connection_id, f"error: {str(e)}")
