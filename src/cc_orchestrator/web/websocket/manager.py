"""
WebSocket connection manager for real-time communication.

Handles connection lifecycle, message broadcasting, and client management.
"""

import asyncio
import json
import os
import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from threading import RLock
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from ..logging_utils import (
    log_real_time_event,
    log_websocket_connection,
    log_websocket_message,
)


class ConnectionRefusedError(Exception):
    """Raised when a WebSocket connection is refused due to server constraints."""

    pass


@dataclass
class QueuedMessage:
    """A message with expiration time for queue management."""

    message: "WebSocketMessage"
    expires_at: datetime

    def is_expired(self) -> bool:
        return datetime.now() > self.expires_at


@dataclass
class WebSocketConfig:
    """Configuration for WebSocket connections."""

    # Connection management
    max_connections: int = 1000
    max_message_size: int = 64 * 1024  # 64KB
    max_queue_size: int = 100  # Maximum queued messages per connection

    # Message queue settings
    queue_message_ttl: int = 300  # TTL for queued messages in seconds (5 minutes)
    queue_cleanup_interval: int = 60  # Cleanup expired messages every 60 seconds

    # Heartbeat settings
    heartbeat_interval: int = 30  # seconds
    heartbeat_timeout: int = 120  # seconds (increased from 60 for reliability)

    # CORS settings
    cors_origins: list[str] = None

    def __post_init__(self):
        """Validate configuration after initialization."""
        if self.heartbeat_timeout < (2 * self.heartbeat_interval):
            raise ValueError(
                f"Heartbeat timeout ({self.heartbeat_timeout}s) must be at least "
                f"twice the interval ({self.heartbeat_interval}s)"
            )

        # Load CORS origins from environment if not provided
        if self.cors_origins is None:
            cors_env = os.getenv(
                "CC_WEB_CORS_ORIGINS", "http://localhost:3000,http://localhost:8080"
            )
            self.cors_origins = [origin.strip() for origin in cors_env.split(",")]

    @classmethod
    def from_environment(cls) -> "WebSocketConfig":
        """Create configuration from environment variables."""
        return cls(
            max_connections=int(os.getenv("CC_WS_MAX_CONNECTIONS", "1000")),
            max_message_size=int(os.getenv("CC_WS_MAX_MESSAGE_SIZE", str(64 * 1024))),
            max_queue_size=int(os.getenv("CC_WS_MAX_QUEUE_SIZE", "100")),
            heartbeat_interval=int(os.getenv("CC_WS_HEARTBEAT_INTERVAL", "30")),
            heartbeat_timeout=int(os.getenv("CC_WS_HEARTBEAT_TIMEOUT", "120")),
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

    def __init__(self, config: WebSocketConfig | None = None) -> None:
        # Configuration
        self.config = config or WebSocketConfig.from_environment()

        # Thread safety lock for connection management
        self._connection_lock = RLock()

        # Active connections by connection ID
        self.connections: dict[str, WebSocketConnection] = {}

        # Subscription groups (topic -> set of connection_ids)
        self.subscriptions: dict[str, set[str]] = defaultdict(set)

        # Message queues for offline connections with TTL
        self.message_queues: dict[str, list[QueuedMessage]] = defaultdict(list)

        # Heartbeat monitoring
        self.heartbeat_task: asyncio.Task[None] | None = None

        # Queue cleanup task
        self.queue_cleanup_task: asyncio.Task[None] | None = None

        # Connection stats
        self.total_connections = 0
        self.total_messages_sent = 0
        self.total_messages_received = 0

    async def initialize(self) -> None:
        """Initialize the connection manager."""
        # Start heartbeat monitoring
        self.heartbeat_task = asyncio.create_task(self._heartbeat_monitor())

        # Start queue cleanup task
        self.queue_cleanup_task = asyncio.create_task(self._queue_cleanup_monitor())

    async def cleanup(self) -> None:
        """Cleanup resources on shutdown."""
        # Cancel heartbeat monitoring
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
            try:
                await self.heartbeat_task
            except asyncio.CancelledError:
                pass

        # Cancel queue cleanup task
        if self.queue_cleanup_task:
            self.queue_cleanup_task.cancel()
            try:
                await self.queue_cleanup_task
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

        Raises:
            ConnectionRefusedError: If server is at capacity
        """
        # Check connection limits before accepting (thread-safe)
        with self._connection_lock:
            if len(self.connections) >= self.config.max_connections:
                await websocket.close(code=1008, reason="Server at capacity")
                raise ConnectionRefusedError(
                    f"Maximum connections ({self.config.max_connections}) exceeded"
                )

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
        with self._connection_lock:
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
            except (RuntimeError, ConnectionError, OSError):
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

        Raises:
            ValueError: If message exceeds maximum size limit
        """
        message_data = message.model_dump_json()

        # Validate message size
        if len(message_data) > self.config.max_message_size:
            raise ValueError(
                f"Message size ({len(message_data)} bytes) exceeds limit "
                f"({self.config.max_message_size} bytes)"
            )

        if connection_id not in self.connections:
            if queue_if_offline:
                with self._connection_lock:
                    # Check queue size limit before adding
                    current_queue_size = len(self.message_queues[connection_id])
                    if current_queue_size >= self.config.max_queue_size:
                        # Remove oldest message to make room
                        self.message_queues[connection_id].pop(0)

                    # Create queued message with TTL
                    expires_at = datetime.now() + timedelta(
                        seconds=self.config.queue_message_ttl
                    )
                    queued_message = QueuedMessage(
                        message=message, expires_at=expires_at
                    )
                    self.message_queues[connection_id].append(queued_message)
            return False

        connection = self.connections[connection_id]

        try:
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
                with self._connection_lock:
                    # Check queue size limit before adding
                    current_queue_size = len(self.message_queues[connection_id])
                    if current_queue_size >= self.config.max_queue_size:
                        # Remove oldest message to make room
                        self.message_queues[connection_id].pop(0)

                    # Create queued message with TTL
                    expires_at = datetime.now() + timedelta(
                        seconds=self.config.queue_message_ttl
                    )
                    queued_message = QueuedMessage(
                        message=message, expires_at=expires_at
                    )
                    self.message_queues[connection_id].append(queued_message)
            return False
        except (ConnectionError, OSError) as e:
            await self.disconnect(connection_id, f"network_error: {str(e)}")
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

        # Send messages concurrently for better performance
        send_tasks = [
            self.send_message(connection_id, message)
            for connection_id in target_connections
        ]

        if send_tasks:
            results = await asyncio.gather(*send_tasks, return_exceptions=True)
            successful_sends = sum(1 for result in results if result is True)
        else:
            successful_sends = 0

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

        # Validate incoming message size
        if len(message_data) > self.config.max_message_size:
            error_message = WebSocketMessage(
                type="error",
                data={
                    "error": f"Message size ({len(message_data)} bytes) exceeds limit "
                    f"({self.config.max_message_size} bytes)"
                },
            )
            await self.send_message(
                connection_id, error_message, queue_if_offline=False
            )
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
            await self.send_message(
                connection_id, error_message, queue_if_offline=False
            )

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

        with self._connection_lock:
            queued_messages = self.message_queues[connection_id]

            # Send only non-expired messages
            for queued_msg in queued_messages:
                if not queued_msg.is_expired():
                    await self.send_message(
                        connection_id, queued_msg.message, queue_if_offline=False
                    )

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
                await asyncio.sleep(self.config.heartbeat_interval)

                current_time = datetime.now()
                timeout_threshold = current_time - timedelta(
                    seconds=self.config.heartbeat_timeout
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

    async def _queue_cleanup_monitor(self) -> None:
        """Monitor and cleanup expired messages from queues."""
        while True:
            try:
                await asyncio.sleep(self.config.queue_cleanup_interval)

                # Clean up expired messages from all queues
                with self._connection_lock:
                    for connection_id in list(self.message_queues.keys()):
                        queue = self.message_queues[connection_id]

                        # Remove expired messages
                        self.message_queues[connection_id] = [
                            queued_msg
                            for queued_msg in queue
                            if not queued_msg.is_expired()
                        ]

                        # Remove empty queues for disconnected clients
                        if (
                            not self.message_queues[connection_id]
                            and connection_id not in self.connections
                        ):
                            del self.message_queues[connection_id]

            except asyncio.CancelledError:
                break
            except (RuntimeError, ConnectionError, OSError):
                # Continue monitoring despite errors
                continue


# Global connection manager instance
connection_manager = ConnectionManager()
