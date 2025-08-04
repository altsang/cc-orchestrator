"""
WebSocket statistics API endpoints.

Provides REST endpoints for WebSocket connection monitoring and statistics.
"""

from typing import Any

from fastapi import APIRouter

from ..websocket.manager import connection_manager

router = APIRouter()


@router.get("/stats")
async def get_websocket_stats() -> dict[str, Any]:
    """
    Get WebSocket connection statistics.

    Returns:
        Dictionary containing connection statistics
    """
    return await connection_manager.get_connection_stats()


@router.get("/connections")
async def get_active_connections() -> dict[str, Any]:
    """
    Get information about active WebSocket connections.

    Returns:
        Dictionary containing active connection details
    """
    connections = []

    for conn_id, connection in connection_manager.connections.items():
        connections.append(
            {
                "connection_id": conn_id,
                "client_ip": connection.client_ip,
                "connected_at": connection.connected_at.isoformat(),
                "last_heartbeat": connection.last_heartbeat.isoformat(),
                "subscriptions": list(connection.subscriptions),
                "queued_messages": len(connection.message_queue),
                "is_alive": connection.is_alive,
            }
        )

    return {
        "active_connections": len(connections),
        "connections": connections,
    }


@router.get("/subscriptions")
async def get_subscription_info() -> dict[str, Any]:
    """
    Get information about active subscriptions.

    Returns:
        Dictionary containing subscription information
    """
    subscriptions = {}

    for topic, connection_ids in connection_manager.subscriptions.items():
        subscriptions[topic] = {
            "subscriber_count": len(connection_ids),
            "connection_ids": list(connection_ids),
        }

    return {
        "total_topics": len(subscriptions),
        "subscriptions": subscriptions,
    }


@router.post("/broadcast")
async def broadcast_test_message(
    message_type: str = "test", data: dict[str, Any] | None = None
) -> dict[str, Any]:
    """
    Broadcast a test message to all connected clients.

    Args:
        message_type: Type of message to send
        data: Message data payload

    Returns:
        Broadcast result information
    """
    from ..websocket.manager import WebSocketMessage

    if data is None:
        data = {"test": "This is a test broadcast message"}

    message = WebSocketMessage(
        type=message_type,
        data=data,
    )

    successful_sends = await connection_manager.broadcast_message(message)

    return {
        "message_sent": True,
        "message_type": message_type,
        "successful_sends": successful_sends,
        "total_connections": len(connection_manager.connections),
    }
