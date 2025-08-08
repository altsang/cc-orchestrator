"""WebSocket endpoints for real-time communication."""

import json
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.websockets import WebSocketState

from ..logging_utils import log_websocket_connection, log_websocket_message
from ..websocket_manager import WebSocketManager

router = APIRouter(tags=["websocket"])

# Global WebSocket manager
ws_manager = WebSocketManager()


@router.websocket("/dashboard")
async def websocket_dashboard(websocket: WebSocket) -> None:
    """WebSocket endpoint for dashboard real-time updates."""
    connection_id = await ws_manager.connect(websocket)

    try:
        while websocket.client_state == WebSocketState.CONNECTED:
            # Receive messages from client
            data = await websocket.receive_text()
            log_websocket_message(connection_id, "client_message", "inbound", len(data))

            try:
                message = json.loads(data)
                await handle_client_message(connection_id, message)
            except json.JSONDecodeError:
                await websocket.send_json(
                    {"type": "error", "message": "Invalid JSON format"}
                )

    except WebSocketDisconnect:
        client_info = getattr(websocket, "client", None)
        client_ip = client_info.host if client_info else "unknown"
        log_websocket_connection(
            client_ip, "disconnect", connection_id, "client_disconnect"
        )
    finally:
        await ws_manager.disconnect(connection_id)


async def handle_client_message(connection_id: str, message: dict[str, Any]) -> None:
    """Handle incoming client messages."""
    message_type = message.get("type")

    if message_type == "ping":
        await ws_manager.send_to_connection(
            connection_id, {"type": "pong", "timestamp": message.get("timestamp")}
        )
    elif message_type == "subscribe":
        # Handle subscription requests
        event_types = message.get("events", [])
        await ws_manager.add_subscription(connection_id, event_types)
        await ws_manager.send_to_connection(
            connection_id, {"type": "subscription_confirmed", "events": event_types}
        )
    elif message_type == "unsubscribe":
        # Handle unsubscription requests
        event_types = message.get("events", [])
        await ws_manager.remove_subscription(connection_id, event_types)
        await ws_manager.send_to_connection(
            connection_id, {"type": "unsubscription_confirmed", "events": event_types}
        )
    else:
        await ws_manager.send_to_connection(
            connection_id,
            {"type": "error", "message": f"Unknown message type: {message_type}"},
        )


# Convenience functions for broadcasting events
async def broadcast_instance_status_change(
    instance_id: int, old_status: str, new_status: str
) -> None:
    """Broadcast instance status change to subscribed clients."""
    await ws_manager.broadcast_to_subscribers(
        "instance_status",
        {
            "type": "instance_status_change",
            "instance_id": instance_id,
            "old_status": old_status,
            "new_status": new_status,
            "timestamp": ws_manager.get_current_timestamp(),
        },
    )


async def broadcast_instance_metrics(instance_id: int, metrics: dict[str, Any]) -> None:
    """Broadcast instance metrics to subscribed clients."""
    await ws_manager.broadcast_to_subscribers(
        "instance_metrics",
        {
            "type": "instance_metrics",
            "instance_id": instance_id,
            "metrics": metrics,
            "timestamp": ws_manager.get_current_timestamp(),
        },
    )


async def broadcast_system_event(event: dict[str, Any]) -> None:
    """Broadcast system-wide events."""
    await ws_manager.broadcast_to_subscribers(
        "system_events",
        {
            "type": "system_event",
            **event,
            "timestamp": ws_manager.get_current_timestamp(),
        },
    )
