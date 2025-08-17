"""WebSocket connection and message management."""

import asyncio
import json
import time
import uuid
from collections import defaultdict
from datetime import datetime
from typing import Any

from fastapi import WebSocket
from fastapi.websockets import WebSocketState

from .exceptions import RateLimitExceededError
from .logging_utils import log_websocket_connection, log_websocket_message


class WebSocketManager:
    """Manages WebSocket connections and message broadcasting."""

    def __init__(
        self, max_connections: int = 100, max_connections_per_ip: int = 5
    ) -> None:
        self.connections: dict[str, WebSocket] = {}
        self.subscriptions: dict[str, set[str]] = {}  # connection_id -> event_types
        self.connection_timestamps: dict[str, float] = {}  # connection_id -> time
        self.connections_per_ip: dict[str, int] = defaultdict(int)  # ip -> count
        self.connection_ip_map: dict[str, str] = {}  # connection_id -> ip

        # Configuration
        self.max_connections = max_connections
        self.max_connections_per_ip = max_connections_per_ip
        self.cleanup_task: asyncio.Task[None] | None = None
        self._cleanup_started = False

    async def connect(self, websocket: WebSocket) -> str:
        """Accept a new WebSocket connection and return connection ID."""
        client_info = getattr(websocket, "client", None)
        client_ip = client_info.host if client_info else "unknown"

        # Check connection limits
        if len(self.connections) >= self.max_connections:
            await websocket.close(
                code=1013, reason="Server overloaded - too many connections"
            )
            raise RateLimitExceededError(self.max_connections, "total connections")

        if self.connections_per_ip[client_ip] >= self.max_connections_per_ip:
            await websocket.close(code=1013, reason="Too many connections from this IP")
            raise RateLimitExceededError(
                self.max_connections_per_ip, "connections per IP"
            )

        # Only accept if not already connected (router may have already done this)
        if websocket.client_state == WebSocketState.CONNECTING:
            await websocket.accept()
        connection_id = str(uuid.uuid4())
        current_time = time.time()

        # Store connection info
        self.connections[connection_id] = websocket
        self.subscriptions[connection_id] = set()
        self.connection_timestamps[connection_id] = current_time
        self.connections_per_ip[client_ip] += 1
        self.connection_ip_map[connection_id] = client_ip

        # Start cleanup task on first connection
        if not self._cleanup_started:
            self._start_cleanup_task()
            self._cleanup_started = True

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

            # Clean up all connection data
            del self.connections[connection_id]
            del self.subscriptions[connection_id]

            if connection_id in self.connection_timestamps:
                del self.connection_timestamps[connection_id]

            if connection_id in self.connection_ip_map:
                ip = self.connection_ip_map[connection_id]
                del self.connection_ip_map[connection_id]

                # Decrement IP connection count
                if self.connections_per_ip[ip] > 0:
                    self.connections_per_ip[ip] -= 1
                    if self.connections_per_ip[ip] == 0:
                        del self.connections_per_ip[ip]

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

    def _start_cleanup_task(self) -> None:
        """Start the periodic cleanup task."""
        try:
            if self.cleanup_task is None or self.cleanup_task.done():
                self.cleanup_task = asyncio.create_task(self._periodic_cleanup())
        except RuntimeError:
            # No event loop running, will start later
            pass

    async def _periodic_cleanup(self) -> None:
        """Periodic cleanup of stale connections."""
        while True:
            try:
                await asyncio.sleep(300)  # Run every 5 minutes
                await self.cleanup_stale_connections()
            except asyncio.CancelledError:
                break
            except Exception as e:
                # Log error but continue cleanup loop
                import logging

                logger = logging.getLogger(__name__)
                logger.error(f"Error during cleanup task: {e}")

    async def cleanup_stale_connections(self, max_age_seconds: int = 3600) -> int:
        """Clean up connections that have been idle too long."""
        current_time = time.time()
        stale_connections = []

        for connection_id, timestamp in self.connection_timestamps.items():
            if current_time - timestamp > max_age_seconds:
                websocket = self.connections.get(connection_id)
                if websocket and websocket.client_state != WebSocketState.CONNECTED:
                    stale_connections.append(connection_id)

        # Clean up stale connections
        for connection_id in stale_connections:
            await self.disconnect(connection_id)

        return len(stale_connections)

    def get_connection_stats(self) -> dict[str, Any]:
        """Get connection statistics."""
        return {
            "total_connections": len(self.connections),
            "max_connections": self.max_connections,
            "connections_per_ip": dict(self.connections_per_ip),
            "max_connections_per_ip": self.max_connections_per_ip,
            "oldest_connection_age": (
                time.time() - min(self.connection_timestamps.values())
                if self.connection_timestamps
                else 0
            ),
        }

    async def shutdown(self) -> None:
        """Shutdown the WebSocket manager and cleanup resources."""
        # Cancel cleanup task
        if self.cleanup_task and not self.cleanup_task.done():
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass

        # Close all connections
        for connection_id in list(self.connections.keys()):
            await self.disconnect(connection_id)


class ConnectionManager:
    """Alias/wrapper for WebSocketManager for compatibility."""

    def __init__(self, max_connections: int = 100, max_connections_per_ip: int = 5):
        """Initialize connection manager.

        Args:
            max_connections: Maximum total connections
            max_connections_per_ip: Maximum connections per IP
        """
        self._manager = WebSocketManager(max_connections, max_connections_per_ip)

    async def connect(self, websocket: WebSocket) -> str:
        """Accept a new WebSocket connection."""
        return await self._manager.connect(websocket)

    async def disconnect(self, connection_id: str) -> None:
        """Disconnect a WebSocket connection."""
        await self._manager.disconnect(connection_id)

    async def send_message(self, connection_id: str, message: dict[str, Any]) -> None:
        """Send message to a specific connection."""
        await self._manager.send_to_connection(connection_id, message)

    def get_connection_count(self) -> int:
        """Get total number of active connections."""
        return self._manager.get_connection_count()
