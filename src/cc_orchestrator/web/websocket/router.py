"""
WebSocket router for real-time communication endpoints.

Provides WebSocket endpoints for different types of real-time updates.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from .manager import connection_manager

router = APIRouter()


@router.websocket("/connect")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """
    Main WebSocket endpoint for client connections.

    Handles the full connection lifecycle including:
    - Connection establishment
    - Message processing
    - Graceful disconnection
    """
    # Get client IP (handle proxy headers)
    client_ip = websocket.client.host if websocket.client else "unknown"

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
async def instance_websocket(websocket: WebSocket, instance_id: str) -> None:
    """
    WebSocket endpoint for instance-specific updates.

    Automatically subscribes to updates for a specific instance.
    """
    client_ip = websocket.client.host if websocket.client else "unknown"
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
async def task_websocket(websocket: WebSocket, task_id: str) -> None:
    """
    WebSocket endpoint for task-specific updates.

    Automatically subscribes to updates for a specific task.
    """
    client_ip = websocket.client.host if websocket.client else "unknown"
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
async def logs_websocket(websocket: WebSocket) -> None:
    """
    WebSocket endpoint for streaming logs.

    Provides real-time log streaming functionality.
    """
    client_ip = websocket.client.host if websocket.client else "unknown"
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
async def dashboard_websocket(websocket: WebSocket) -> None:
    """
    WebSocket endpoint for dashboard updates.

    Provides comprehensive real-time updates for the web dashboard.
    """
    client_ip = websocket.client.host if websocket.client else "unknown"
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
