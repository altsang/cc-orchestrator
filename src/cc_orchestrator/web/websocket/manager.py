"""
WebSocket connection manager for real-time communication.

Handles connection lifecycle, message broadcasting, and client management.
"""

import asyncio
import json
import uuid
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from ..logging_utils import (
    log_real_time_event,
    log_websocket_connection,
    log_websocket_message,
)


class WebSocketMessage(BaseModel):
    """WebSocket message structure."""

    type: str
    data: dict[str, Any]
    timestamp: datetime
    message_id: str = ""

    def __init__(self, **data: Any) -> None:
        if "message_id" not in data:
            data["message_id"] = str(uuid.uuid4())
        if "timestamp" not in data:
            data["timestamp"] = datetime.now()
        super().__init__(**data)


class WebSocketConnection:
    """Represents a WebSocket connection with metadata."""

    def __init__(self, websocket: WebSocket, connection_id: str, client_ip: str):
        self.websocket = websocket
        self.connection_id = connection_id
        self.client_ip = client_ip
        self.connected_at = datetime.now()
        self.last_heartbeat = datetime.now()
        self.subscriptions: set[str] = set()
        self.message_queue: list[WebSocketMessage] = []
        self.is_alive = True


class ConnectionManager:
    """
    Manages WebSocket connections and message broadcasting.

    Features:
    - Connection lifecycle management
    - Message broadcasting with subscriptions
    - Heartbeat monitoring
    - Message queuing for offline clients
    - Event-driven architecture
    """

    def __init__(self) -> None:
        # Active connections by connection ID
        self.connections: dict[str, WebSocketConnection] = {}

        # Subscription groups (topic -> set of connection_ids)
        self.subscriptions: dict[str, set[str]] = defaultdict(set)

        # Message queues for offline connections
        self.message_queues: dict[str, list[WebSocketMessage]] = defaultdict(list)

        # Heartbeat monitoring
        self.heartbeat_interval = 30  # seconds
        self.heartbeat_timeout = 60  # seconds
        self.heartbeat_task: asyncio.Task[None] | None = None

        # Connection stats
        self.total_connections = 0
        self.total_messages_sent = 0
        self.total_messages_received = 0

    async def initialize(self) -> None:
        """Initialize the connection manager."""
        # Start heartbeat monitoring
        self.heartbeat_task = asyncio.create_task(self._heartbeat_monitor())

    async def cleanup(self) -> None:
        """Cleanup resources on shutdown."""
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
            try:
                await self.heartbeat_task
            except asyncio.CancelledError:
                pass

        # Close all connections
        for connection in list(self.connections.values()):
            await self.disconnect(connection.connection_id, "server_shutdown")

    async def connect(self, websocket: WebSocket, client_ip: str) -> str:
        """
        Accept a new WebSocket connection.

        Args:
            websocket: The WebSocket connection
            client_ip: Client IP address

        Returns:
            Connection ID for the new connection
        """
        await websocket.accept()

        connection_id = str(uuid.uuid4())
        connection = WebSocketConnection(websocket, connection_id, client_ip)

        self.connections[connection_id] = connection
        self.total_connections += 1

        log_websocket_connection(
            client_ip=client_ip,
            action="connect",
            connection_id=connection_id,
        )

        # Send queued messages if any exist for this client
        await self._send_queued_messages(connection_id)

        return connection_id

    async def disconnect(
        self, connection_id: str, reason: str = "client_disconnect"
    ) -> None:
        """
        Remove a WebSocket connection.

        Args:
            connection_id: ID of the connection to remove
            reason: Reason for disconnection
        """
        if connection_id not in self.connections:
            return

        connection = self.connections[connection_id]
        connection.is_alive = False

        # Remove from all subscriptions
        for topic in list(connection.subscriptions):
            await self.unsubscribe(connection_id, topic)

        # Close the WebSocket
        try:
            await connection.websocket.close()
        except (RuntimeError, ConnectionError):
            # Connection might already be closed or in invalid state
            pass

        # Remove from connections
        del self.connections[connection_id]

        log_websocket_connection(
            client_ip=connection.client_ip,
            action="disconnect",
            connection_id=connection_id,
            reason=reason,
        )

    async def send_message(
        self,
        connection_id: str,
        message: WebSocketMessage,
        queue_if_offline: bool = True,
    ) -> bool:
        """
        Send a message to a specific connection.

        Args:
            connection_id: Target connection ID
            message: Message to send
            queue_if_offline: Whether to queue message if connection is offline

        Returns:
            True if message was sent successfully, False otherwise
        """
        if connection_id not in self.connections:
            if queue_if_offline:
                self.message_queues[connection_id].append(message)
            return False

        connection = self.connections[connection_id]

        try:
            message_data = message.model_dump_json()
            await connection.websocket.send_text(message_data)

            self.total_messages_sent += 1

            log_websocket_message(
                connection_id=connection_id,
                message_type=message.type,
                direction="outbound",
                message_size=len(message_data),
            )

            return True

        except WebSocketDisconnect:
            await self.disconnect(connection_id, "connection_lost")
            if queue_if_offline:
                self.message_queues[connection_id].append(message)
            return False
        except Exception as e:
            await self.disconnect(connection_id, f"send_error: {str(e)}")
            return False

    async def broadcast_message(
        self,
        message: WebSocketMessage,
        topic: str | None = None,
        exclude_connections: set[str] | None = None,
    ) -> int:
        """
        Broadcast a message to multiple connections.

        Args:
            message: Message to broadcast
            topic: If specified, only send to subscribers of this topic
            exclude_connections: Connection IDs to exclude from broadcast

        Returns:
            Number of connections that received the message
        """
        exclude_connections = exclude_connections or set()
        target_connections = set()

        if topic:
            # Send to topic subscribers
            target_connections = self.subscriptions[topic] - exclude_connections
        else:
            # Send to all connections
            target_connections = set(self.connections.keys()) - exclude_connections

        successful_sends = 0

        for connection_id in target_connections:
            if await self.send_message(connection_id, message):
                successful_sends += 1

        log_real_time_event(
            event_type=message.type,
            target_connections=len(target_connections),
            payload_size=len(message.model_dump_json()),
        )

        return successful_sends

    async def subscribe(self, connection_id: str, topic: str) -> bool:
        """
        Subscribe a connection to a topic.

        Args:
            connection_id: Connection to subscribe
            topic: Topic to subscribe to

        Returns:
            True if subscription was successful
        """
        if connection_id not in self.connections:
            return False

        connection = self.connections[connection_id]
        connection.subscriptions.add(topic)
        self.subscriptions[topic].add(connection_id)

        return True

    async def unsubscribe(self, connection_id: str, topic: str) -> bool:
        """
        Unsubscribe a connection from a topic.

        Args:
            connection_id: Connection to unsubscribe
            topic: Topic to unsubscribe from

        Returns:
            True if unsubscription was successful
        """
        if connection_id not in self.connections:
            return False

        connection = self.connections[connection_id]
        connection.subscriptions.discard(topic)
        self.subscriptions[topic].discard(connection_id)

        # Clean up empty subscription topics
        if not self.subscriptions[topic]:
            del self.subscriptions[topic]

        return True

    async def handle_message(self, connection_id: str, message_data: str) -> None:
        """
        Handle incoming message from a WebSocket connection.

        Args:
            connection_id: Source connection ID
            message_data: Raw message data
        """
        if connection_id not in self.connections:
            return

        connection = self.connections[connection_id]
        connection.last_heartbeat = datetime.now()
        self.total_messages_received += 1

        try:
            data = json.loads(message_data)
            message_type = data.get("type", "unknown")

            log_websocket_message(
                connection_id=connection_id,
                message_type=message_type,
                direction="inbound",
                message_size=len(message_data),
            )

            # Handle different message types
            await self._process_message(connection_id, message_type, data)

        except json.JSONDecodeError:
            # Send error response
            error_message = WebSocketMessage(
                type="error",
                data={"error": "Invalid JSON format"},
            )
            await self.send_message(connection_id, error_message)

    async def get_connection_stats(self) -> dict[str, Any]:
        """Get connection statistics."""
        active_connections = len(self.connections)
        active_subscriptions = len(self.subscriptions)
        queued_messages = sum(len(queue) for queue in self.message_queues.values())

        return {
            "active_connections": active_connections,
            "total_connections": self.total_connections,
            "active_subscriptions": active_subscriptions,
            "queued_messages": queued_messages,
            "messages_sent": self.total_messages_sent,
            "messages_received": self.total_messages_received,
        }

    async def _send_queued_messages(self, connection_id: str) -> None:
        """Send queued messages to a newly connected client."""
        if connection_id not in self.message_queues:
            return

        messages = self.message_queues[connection_id]
        for message in messages:
            await self.send_message(connection_id, message, queue_if_offline=False)

        # Clear the queue
        del self.message_queues[connection_id]

    async def _process_message(
        self, connection_id: str, message_type: str, data: dict[str, Any]
    ) -> None:
        """Process incoming messages based on type."""
        if message_type == "heartbeat":
            # Respond to heartbeat
            response = WebSocketMessage(
                type="heartbeat_ack",
                data={"timestamp": datetime.now().isoformat()},
            )
            await self.send_message(connection_id, response)

        elif message_type == "subscribe":
            topic = data.get("topic")
            if topic:
                success = await self.subscribe(connection_id, topic)
                response = WebSocketMessage(
                    type="subscription_result",
                    data={"topic": topic, "success": success},
                )
                await self.send_message(connection_id, response)

        elif message_type == "unsubscribe":
            topic = data.get("topic")
            if topic:
                success = await self.unsubscribe(connection_id, topic)
                response = WebSocketMessage(
                    type="unsubscription_result",
                    data={"topic": topic, "success": success},
                )
                await self.send_message(connection_id, response)

        elif message_type == "ping":
            # Simple ping-pong for connection testing
            response = WebSocketMessage(
                type="pong",
                data=data.get("data", {}),
            )
            await self.send_message(connection_id, response)

    async def _heartbeat_monitor(self) -> None:
        """Monitor connection health with heartbeats."""
        while True:
            try:
                await asyncio.sleep(self.heartbeat_interval)

                current_time = datetime.now()
                timeout_threshold = current_time - timedelta(
                    seconds=self.heartbeat_timeout
                )

                # Check for timed-out connections
                for connection_id, connection in list(self.connections.items()):
                    if connection.last_heartbeat < timeout_threshold:
                        await self.disconnect(connection_id, "heartbeat_timeout")

            except asyncio.CancelledError:
                break
            except (RuntimeError, ConnectionError, OSError):
                # Continue monitoring despite errors
                continue


# Global connection manager instance
connection_manager = ConnectionManager()
