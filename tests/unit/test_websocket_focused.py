"""Focused tests for WebSocket manager to improve coverage."""

import json
from unittest.mock import AsyncMock

import pytest
from fastapi.websockets import WebSocketState

from cc_orchestrator.web.websocket_manager import WebSocketManager


class MockClient:
    """Mock client info for WebSocket."""

    def __init__(self, host="127.0.0.1"):
        self.host = host


class MockWebSocket:
    """Mock WebSocket for testing."""

    def __init__(self, client_ip="127.0.0.1"):
        self.messages_sent = []
        self.closed = False
        self.client_state = WebSocketState.CONNECTED
        self.client = MockClient(client_ip)

    async def accept(self):
        """Mock accept method."""
        pass

    async def send_text(self, data):
        if self.closed:
            raise RuntimeError("WebSocket is closed")
        self.messages_sent.append(data)

    async def send_json(self, data):
        if self.closed:
            raise RuntimeError("WebSocket is closed")
        self.messages_sent.append(json.dumps(data))

    async def close(self):
        self.closed = True
        self.client_state = WebSocketState.DISCONNECTED


@pytest.fixture
def websocket_manager():
    """Create a WebSocket manager for testing."""
    return WebSocketManager()


@pytest.fixture
def mock_websocket():
    """Create a mock WebSocket."""
    return MockWebSocket()


class TestWebSocketManagerBasics:
    """Test basic WebSocket manager functionality."""

    async def test_connect_websocket(self, websocket_manager, mock_websocket):
        """Test connecting a WebSocket."""
        connection_id = await websocket_manager.connect(mock_websocket)

        assert connection_id is not None
        assert connection_id in websocket_manager.connections
        assert websocket_manager.connections[connection_id] == mock_websocket

    async def test_disconnect_websocket(self, websocket_manager, mock_websocket):
        """Test disconnecting a WebSocket."""
        connection_id = await websocket_manager.connect(mock_websocket)

        await websocket_manager.disconnect(connection_id)

        assert connection_id not in websocket_manager.connections

    async def test_disconnect_nonexistent_websocket(self, websocket_manager):
        """Test disconnecting a non-existent WebSocket."""
        # Should not raise an exception
        await websocket_manager.disconnect("nonexistent-id")

    async def test_get_connection_count(self, websocket_manager, mock_websocket):
        """Test getting connection count."""
        assert websocket_manager.get_connection_count() == 0

        await websocket_manager.connect(mock_websocket)
        assert websocket_manager.get_connection_count() == 1

        await websocket_manager.connect(MockWebSocket())
        assert websocket_manager.get_connection_count() == 2


class TestWebSocketMessaging:
    """Test WebSocket messaging functionality."""

    async def test_send_to_connection_success(self, websocket_manager, mock_websocket):
        """Test sending message to specific connection."""
        connection_id = await websocket_manager.connect(mock_websocket)

        message = {"type": "test", "data": {"key": "value"}}
        success = await websocket_manager.send_to_connection(connection_id, message)

        assert success is True
        assert len(mock_websocket.messages_sent) == 2  # Connect message + test message

        # First message should be the connection welcome message
        connect_message = json.loads(mock_websocket.messages_sent[0])
        assert connect_message["type"] == "connected"

        # Second message should be our test message
        sent_message = json.loads(mock_websocket.messages_sent[1])
        assert sent_message["type"] == "test"
        assert sent_message["data"]["key"] == "value"

    async def test_send_to_connection_failure(self, websocket_manager, mock_websocket):
        """Test sending message to connection that fails."""
        connection_id = await websocket_manager.connect(mock_websocket)
        mock_websocket.closed = True  # Simulate closed connection

        message = {"type": "test", "data": {}}
        success = await websocket_manager.send_to_connection(connection_id, message)

        assert success is False
        # Connection should be automatically removed
        assert connection_id not in websocket_manager.connections

    async def test_send_to_nonexistent_connection(self, websocket_manager):
        """Test sending message to non-existent connection."""
        message = {"type": "test", "data": {}}
        success = await websocket_manager.send_to_connection("nonexistent", message)

        assert success is False

    async def test_broadcast_to_all(self, websocket_manager):
        """Test broadcasting message to all connections."""
        ws1 = MockWebSocket()
        ws2 = MockWebSocket()

        await websocket_manager.connect(ws1)
        await websocket_manager.connect(ws2)

        message = {"type": "broadcast", "data": {"message": "hello"}}
        sent_count = await websocket_manager.broadcast_to_all(message)

        assert sent_count == 2
        assert len(ws1.messages_sent) == 2  # Connect + message
        assert len(ws2.messages_sent) == 2  # Connect + message

    async def test_broadcast_with_failed_connections(self, websocket_manager):
        """Test broadcasting with some failed connections."""
        ws1 = MockWebSocket()
        ws2 = MockWebSocket()
        # Connect both websockets first
        await websocket_manager.connect(ws1)
        await websocket_manager.connect(ws2)
        
        # Now close ws2 to make it fail during broadcast
        ws2.closed = True

        message = {"type": "broadcast", "data": {}}
        sent_count = await websocket_manager.broadcast_to_all(message)

        assert sent_count == 1  # Only one successful
        assert len(ws1.messages_sent) == 2  # Connect + message
        assert len(ws2.messages_sent) == 1  # Only connect message (failed to send)


class TestWebSocketSubscriptions:
    """Test WebSocket subscription functionality."""

    async def test_add_subscription(self, websocket_manager, mock_websocket):
        """Test adding a subscription."""
        connection_id = await websocket_manager.connect(mock_websocket)

        await websocket_manager.add_subscription(connection_id, ["instance_updates"])

        assert connection_id in websocket_manager.subscriptions
        assert "instance_updates" in websocket_manager.subscriptions[connection_id]

    async def test_remove_subscription(self, websocket_manager, mock_websocket):
        """Test removing a subscription."""
        connection_id = await websocket_manager.connect(mock_websocket)

        await websocket_manager.add_subscription(connection_id, ["instance_updates"])
        await websocket_manager.remove_subscription(connection_id, ["instance_updates"])

        # Subscription should be cleaned up
        assert "instance_updates" not in websocket_manager.subscriptions[connection_id]

    async def test_broadcast_to_subscribers(self, websocket_manager):
        """Test broadcasting to subscribers."""
        ws1 = MockWebSocket()
        ws2 = MockWebSocket()
        ws3 = MockWebSocket()  # Not subscribed

        id1 = await websocket_manager.connect(ws1)
        id2 = await websocket_manager.connect(ws2)
        await websocket_manager.connect(ws3)

        await websocket_manager.add_subscription(id1, ["instance_updates"])
        await websocket_manager.add_subscription(id2, ["instance_updates"])

        message = {"type": "instance_update", "data": {"instance_id": "123"}}
        sent_count = await websocket_manager.broadcast_to_subscribers(
            "instance_updates", message
        )

        assert sent_count == 2
        assert len(ws1.messages_sent) == 2  # Connect + message
        assert len(ws2.messages_sent) == 2  # Connect + message
        assert len(ws3.messages_sent) == 1  # Only connect message (not subscribed)

    async def test_cleanup_subscriptions_on_disconnect(
        self, websocket_manager, mock_websocket
    ):
        """Test that subscriptions are cleaned up when connection disconnects."""
        connection_id = await websocket_manager.connect(mock_websocket)

        await websocket_manager.add_subscription(connection_id, ["instance_updates"])
        await websocket_manager.disconnect(connection_id)

        # Connection should be removed entirely
        assert connection_id not in websocket_manager.subscriptions


class TestWebSocketHeartbeat:
    """Test WebSocket heartbeat functionality."""

    async def test_send_heartbeat(self, websocket_manager):
        """Test sending heartbeat to all connections."""
        ws1 = MockWebSocket()
        ws2 = MockWebSocket()

        await websocket_manager.connect(ws1)
        await websocket_manager.connect(ws2)

        await websocket_manager.send_heartbeat()

        assert len(ws1.messages_sent) == 2  # Connect + message
        assert len(ws2.messages_sent) == 2  # Connect + message

        # Check heartbeat message format
        heartbeat_msg = json.loads(ws1.messages_sent[1])  # Second message is heartbeat
        assert heartbeat_msg["type"] == "heartbeat"
        assert "timestamp" in heartbeat_msg

    async def test_heartbeat_with_failed_connections(self, websocket_manager):
        """Test heartbeat with some failed connections."""
        ws1 = MockWebSocket()
        ws2 = MockWebSocket()
        ws2.closed = True

        await websocket_manager.connect(ws1)
        await websocket_manager.connect(ws2)

        await websocket_manager.send_heartbeat()

        # Only healthy connection should receive heartbeat
        assert len(ws1.messages_sent) == 2  # Connect + message
        assert len(ws2.messages_sent) == 1  # Only connect message (failed to send)

        # Failed connection should be removed
        assert websocket_manager.get_connection_count() == 1


class TestWebSocketStats:
    """Test WebSocket statistics functionality."""

    async def test_get_stats(self, websocket_manager):
        """Test getting WebSocket statistics."""
        ws1 = MockWebSocket()
        ws2 = MockWebSocket()

        await websocket_manager.connect(ws1)
        await websocket_manager.connect(ws2)

        stats = websocket_manager.get_connection_stats()

        assert stats["total_connections"] == 2
        assert stats["max_connections"] == 100  # Default value
        assert "connections_per_ip" in stats
        assert "max_connections_per_ip" in stats

    async def test_stats_after_messaging(self, websocket_manager, mock_websocket):
        """Test stats are updated after messaging."""
        connection_id = await websocket_manager.connect(mock_websocket)

        initial_stats = websocket_manager.get_connection_stats()
        initial_connections = initial_stats["total_connections"]

        message = {"type": "test", "data": {}}
        await websocket_manager.send_to_connection(connection_id, message)

        # Test that connection is still tracked
        updated_stats = websocket_manager.get_connection_stats()
        assert updated_stats["total_connections"] == initial_connections


class TestWebSocketUtilities:
    """Test WebSocket utility functions."""

    def test_get_current_timestamp(self, websocket_manager):
        """Test timestamp generation."""
        timestamp = websocket_manager.get_current_timestamp()

        assert isinstance(timestamp, str)
        assert "T" in timestamp  # ISO format
        # The actual implementation doesn't add Z, just returns isoformat()

    async def test_connection_id_generation(self, websocket_manager, mock_websocket):
        """Test that connection IDs are unique."""
        id1 = await websocket_manager.connect(MockWebSocket())
        id2 = await websocket_manager.connect(MockWebSocket())

        assert id1 != id2
        assert len(id1) > 0
        assert len(id2) > 0


class TestWebSocketCleanup:
    """Test WebSocket cleanup functionality."""

    async def test_cleanup_closed_connections(self, websocket_manager):
        """Test cleaning up closed connections."""
        ws1 = MockWebSocket()
        ws2 = MockWebSocket()

        id1 = await websocket_manager.connect(ws1)
        id2 = await websocket_manager.connect(ws2)

        # Close one connection
        ws2.closed = True

        # Try to send message (should trigger cleanup)
        message = {"type": "test", "data": {}}
        await websocket_manager.broadcast_to_all(message)

        # Closed connection should be removed
        assert id1 in websocket_manager.connections
        assert id2 not in websocket_manager.connections

    async def test_error_handling_in_send(self, websocket_manager, mock_websocket):
        """Test error handling when sending messages."""
        connection_id = await websocket_manager.connect(mock_websocket)

        # Mock send_json to raise exception
        mock_websocket.send_json = AsyncMock(side_effect=Exception("Send failed"))

        message = {"type": "test", "data": {}}
        success = await websocket_manager.send_to_connection(connection_id, message)

        assert success is False
        # Connection should be removed after error
        assert connection_id not in websocket_manager.connections

    async def test_subscription_cleanup_edge_cases(
        self, websocket_manager, mock_websocket
    ):
        """Test subscription cleanup edge cases."""
        connection_id = await websocket_manager.connect(mock_websocket)

        # Add subscription
        await websocket_manager.add_subscription(connection_id, ["test_type"])

        # Remove subscription that doesn't exist
        await websocket_manager.remove_subscription(connection_id, ["nonexistent"])

        # Original subscription should still exist
        assert "test_type" in websocket_manager.subscriptions[connection_id]

        # Remove with nonexistent connection ID
        await websocket_manager.remove_subscription("nonexistent", ["test_type"])

        # Original subscription should still exist
        assert "test_type" in websocket_manager.subscriptions[connection_id]
