"""WebSocket connection and message management."""

import json
import uuid
from datetime import datetime
from typing import Any

from fastapi import WebSocket
from fastapi.websockets import WebSocketState

from .logging_utils import log_websocket_connection, log_websocket_message


class WebSocketManager:
    """Manages WebSocket connections and message broadcasting."""

    def __init__(self) -> None:
        self.connections: dict[str, WebSocket] = {}
        self.subscriptions: dict[str, set[str]] = {}  # connection_id -> event_types

    async def connect(self, websocket: WebSocket) -> str:
        """Accept a new WebSocket connection and return connection ID."""
        await websocket.accept()
        connection_id = str(uuid.uuid4())
        self.connections[connection_id] = websocket
        self.subscriptions[connection_id] = set()

        client_info = getattr(websocket, "client", None)
        client_ip = client_info.host if client_info else "unknown"

        log_websocket_connection(client_ip, "connect", connection_id)

        # Send welcome message
        await self.send_to_connection(
            connection_id,
            {
                "type": "connected",
                "connection_id": connection_id,
                "timestamp": self.get_current_timestamp(),
            },
        )

        return connection_id

    async def disconnect(self, connection_id: str) -> None:
        """Remove a WebSocket connection."""
        if connection_id in self.connections:
            websocket = self.connections[connection_id]
            client_info = getattr(websocket, "client", None)
            client_ip = client_info.host if client_info else "unknown"

            log_websocket_connection(client_ip, "disconnect", connection_id)

            del self.connections[connection_id]
            del self.subscriptions[connection_id]

    async def send_to_connection(
        self, connection_id: str, data: dict[str, Any]
    ) -> bool:
        """Send data to a specific connection."""
        if connection_id not in self.connections:
            return False

        websocket = self.connections[connection_id]

        try:
            if websocket.client_state == WebSocketState.CONNECTED:
                message = json.dumps(data)
                await websocket.send_text(message)

                log_websocket_message(
                    connection_id, data.get("type", "unknown"), "outbound", len(message)
                )
                return True
        except Exception:
            # Connection is broken, clean it up
            await self.disconnect(connection_id)

        return False

    async def broadcast_to_all(self, data: dict[str, Any]) -> int:
        """Broadcast data to all connected clients."""
        sent_count = 0
        disconnect_list = []

        for connection_id in list(self.connections.keys()):
            success = await self.send_to_connection(connection_id, data)
            if success:
                sent_count += 1
            else:
                disconnect_list.append(connection_id)

        # Clean up failed connections
        for connection_id in disconnect_list:
            await self.disconnect(connection_id)

        return sent_count

    async def broadcast_to_subscribers(
        self, event_type: str, data: dict[str, Any]
    ) -> int:
        """Broadcast data to clients subscribed to a specific event type."""
        sent_count = 0
        disconnect_list = []

        for connection_id, subscribed_events in self.subscriptions.items():
            if event_type in subscribed_events:
                success = await self.send_to_connection(connection_id, data)
                if success:
                    sent_count += 1
                else:
                    disconnect_list.append(connection_id)

        # Clean up failed connections
        for connection_id in disconnect_list:
            await self.disconnect(connection_id)

        return sent_count

    async def add_subscription(
        self, connection_id: str, event_types: list[str]
    ) -> None:
        """Add event type subscriptions for a connection."""
        if connection_id in self.subscriptions:
            self.subscriptions[connection_id].update(event_types)

    async def remove_subscription(
        self, connection_id: str, event_types: list[str]
    ) -> None:
        """Remove event type subscriptions for a connection."""
        if connection_id in self.subscriptions:
            for event_type in event_types:
                self.subscriptions[connection_id].discard(event_type)

    def get_connection_count(self) -> int:
        """Get the number of active connections."""
        return len(self.connections)

    def get_subscriber_count(self, event_type: str) -> int:
        """Get the number of connections subscribed to an event type."""
        return sum(
            1
            for subscribed_events in self.subscriptions.values()
            if event_type in subscribed_events
        )

    @staticmethod
    def get_current_timestamp() -> str:
        """Get current timestamp in ISO format."""
        return datetime.utcnow().isoformat()

    async def send_heartbeat(self) -> None:
        """Send heartbeat to all connections."""
        await self.broadcast_to_all(
            {
                "type": "heartbeat",
                "timestamp": self.get_current_timestamp(),
                "connections": self.get_connection_count(),
            }
        )
