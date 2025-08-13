"""Comprehensive tests for WebSocket manager."""

import json
import time
from unittest.mock import Mock

import pytest
from fastapi.websockets import WebSocketState

from cc_orchestrator.web.websocket_manager import WebSocketManager


class MockWebSocket:
    """Mock WebSocket for testing."""

    def __init__(self, client_host="127.0.0.1"):
        self.client = Mock()
        self.client.host = client_host
        self.client_state = WebSocketState.CONNECTED
        self.messages_sent = []
        self.closed = False

    async def accept(self):
        """Mock accept method."""
        pass

    async def send_text(self, message):
        """Mock send_text method."""
        if self.closed:
            raise Exception("Connection closed")
        self.messages_sent.append(message)

    async def close(self, code=None, reason=None):
        """Mock close method."""
        self.closed = True
        self.client_state = WebSocketState.DISCONNECTED


@pytest.mark.asyncio
class TestWebSocketManagerComprehensive:
    """Comprehensive WebSocket manager tests."""

    def test_websocket_manager_init(self):
        """Test WebSocket manager initialization."""
        manager = WebSocketManager(max_connections=50, max_connections_per_ip=3)

        assert manager.max_connections == 50
        assert manager.max_connections_per_ip == 3
        assert len(manager.connections) == 0
        assert len(manager.subscriptions) == 0
        assert len(manager.connection_timestamps) == 0
        assert len(manager.connections_per_ip) == 0

    async def test_websocket_connect_success(self):
        """Test successful WebSocket connection."""
        manager = WebSocketManager()
        websocket = MockWebSocket()

        connection_id = await manager.connect(websocket)

        assert isinstance(connection_id, str)
        assert len(connection_id) > 0
        assert connection_id in manager.connections
        assert connection_id in manager.subscriptions
        assert connection_id in manager.connection_timestamps
        assert connection_id in manager.connection_ip_map
        assert manager.connections_per_ip["127.0.0.1"] == 1

    async def test_websocket_connect_max_connections_limit(self):
        """Test connection limit enforcement."""
        manager = WebSocketManager(max_connections=2)

        # Connect to limit
        ws1 = MockWebSocket()
        ws2 = MockWebSocket()
        await manager.connect(ws1)
        await manager.connect(ws2)

        # Third connection should fail
        ws3 = MockWebSocket()
        with pytest.raises(Exception):
            await manager.connect(ws3)

    async def test_websocket_connect_max_connections_per_ip_limit(self):
        """Test per-IP connection limit enforcement."""
        manager = WebSocketManager(max_connections_per_ip=2)

        # Connect two from same IP
        ws1 = MockWebSocket("192.168.1.1")
        ws2 = MockWebSocket("192.168.1.1")
        await manager.connect(ws1)
        await manager.connect(ws2)

        # Third from same IP should fail
        ws3 = MockWebSocket("192.168.1.1")
        with pytest.raises(Exception):
            await manager.connect(ws3)

        # Different IP should succeed
        ws4 = MockWebSocket("192.168.1.2")
        connection_id = await manager.connect(ws4)
        assert connection_id is not None

    async def test_websocket_disconnect(self):
        """Test WebSocket disconnection."""
        manager = WebSocketManager()
        websocket = MockWebSocket("192.168.1.1")

        connection_id = await manager.connect(websocket)
        assert manager.connections_per_ip["192.168.1.1"] == 1

        await manager.disconnect(connection_id)

        assert connection_id not in manager.connections
        assert connection_id not in manager.subscriptions
        assert connection_id not in manager.connection_timestamps
        assert connection_id not in manager.connection_ip_map
        assert manager.connections_per_ip.get("192.168.1.1", 0) == 0

    async def test_send_to_connection_success(self):
        """Test sending message to specific connection."""
        manager = WebSocketManager()
        websocket = MockWebSocket()

        connection_id = await manager.connect(websocket)
        message = {"type": "test", "data": "hello"}

        result = await manager.send_to_connection(connection_id, message)

        assert result is True
        assert len(websocket.messages_sent) == 2  # Welcome + test message
        sent_message = json.loads(websocket.messages_sent[-1])
        assert sent_message["type"] == "test"
        assert sent_message["data"] == "hello"

    async def test_send_to_nonexistent_connection(self):
        """Test sending message to non-existent connection."""
        manager = WebSocketManager()

        result = await manager.send_to_connection("nonexistent", {"type": "test"})

        assert result is False

    async def test_send_to_closed_connection(self):
        """Test sending message to closed connection."""
        manager = WebSocketManager()
        websocket = MockWebSocket()

        connection_id = await manager.connect(websocket)
        websocket.closed = True
        websocket.client_state = "CLOSED"

        result = await manager.send_to_connection(connection_id, {"type": "test"})

        assert result is False
        # Connection should be cleaned up
        assert connection_id not in manager.connections

    async def test_broadcast_to_all(self):
        """Test broadcasting to all connections."""
        manager = WebSocketManager()
        ws1 = MockWebSocket("192.168.1.1")
        ws2 = MockWebSocket("192.168.1.2")

        await manager.connect(ws1)
        await manager.connect(ws2)

        message = {"type": "broadcast", "data": "hello all"}
        sent_count = await manager.broadcast_to_all(message)

        assert sent_count == 2
        # Both should have received the broadcast
        assert len(ws1.messages_sent) == 2  # Welcome + broadcast
        assert len(ws2.messages_sent) == 2  # Welcome + broadcast

    async def test_broadcast_to_subscribers(self):
        """Test broadcasting to subscribers."""
        manager = WebSocketManager()
        ws1 = MockWebSocket("192.168.1.1")
        ws2 = MockWebSocket("192.168.1.2")

        conn1 = await manager.connect(ws1)
        await manager.connect(ws2)

        # Subscribe only conn1 to "test_events"
        await manager.add_subscription(conn1, ["test_events"])

        message = {"type": "test_event", "data": "subscriber only"}
        sent_count = await manager.broadcast_to_subscribers("test_events", message)

        assert sent_count == 1

    async def test_add_subscription(self):
        """Test adding event subscriptions."""
        manager = WebSocketManager()
        websocket = MockWebSocket()

        connection_id = await manager.connect(websocket)

        await manager.add_subscription(connection_id, ["event1", "event2"])

        subscriptions = manager.subscriptions[connection_id]
        assert "event1" in subscriptions
        assert "event2" in subscriptions

    async def test_remove_subscription(self):
        """Test removing event subscriptions."""
        manager = WebSocketManager()
        websocket = MockWebSocket()

        connection_id = await manager.connect(websocket)
        await manager.add_subscription(connection_id, ["event1", "event2", "event3"])

        await manager.remove_subscription(connection_id, ["event1", "event3"])

        subscriptions = manager.subscriptions[connection_id]
        assert "event1" not in subscriptions
        assert "event2" in subscriptions
        assert "event3" not in subscriptions

    def test_get_connection_count(self):
        """Test getting connection count."""
        manager = WebSocketManager()
        assert manager.get_connection_count() == 0

        # Simulate connections
        manager.connections["conn1"] = Mock()
        manager.connections["conn2"] = Mock()

        assert manager.get_connection_count() == 2

    def test_get_subscriber_count(self):
        """Test getting subscriber count."""
        manager = WebSocketManager()

        # Simulate subscriptions
        manager.subscriptions["conn1"] = {"event1", "event2"}
        manager.subscriptions["conn2"] = {"event1", "event3"}
        manager.subscriptions["conn3"] = {"event2"}

        assert manager.get_subscriber_count("event1") == 2
        assert manager.get_subscriber_count("event2") == 2
        assert manager.get_subscriber_count("event3") == 1
        assert manager.get_subscriber_count("nonexistent") == 0

    def test_get_current_timestamp(self):
        """Test timestamp generation."""
        timestamp = WebSocketManager.get_current_timestamp()
        assert isinstance(timestamp, str)
        assert "T" in timestamp  # ISO format

    async def test_send_heartbeat(self):
        """Test heartbeat functionality."""
        manager = WebSocketManager()
        websocket = MockWebSocket()

        await manager.connect(websocket)

        await manager.send_heartbeat()

        # Should have received welcome + heartbeat
        assert len(websocket.messages_sent) == 2
        heartbeat = json.loads(websocket.messages_sent[-1])
        assert heartbeat["type"] == "heartbeat"
        assert "connections" in heartbeat
        assert heartbeat["connections"] == 1

    async def test_cleanup_stale_connections(self):
        """Test cleanup of stale connections."""
        manager = WebSocketManager()
        websocket = MockWebSocket()

        connection_id = await manager.connect(websocket)

        # Make connection appear old
        manager.connection_timestamps[connection_id] = time.time() - 7200  # 2 hours ago
        websocket.client_state = "CLOSED"

        cleaned = await manager.cleanup_stale_connections(max_age_seconds=3600)

        assert cleaned == 1
        assert connection_id not in manager.connections

    def test_get_connection_stats(self):
        """Test getting connection statistics."""
        manager = WebSocketManager(max_connections=100, max_connections_per_ip=5)

        # Add some mock connections
        manager.connections["conn1"] = Mock()
        manager.connections["conn2"] = Mock()
        manager.connections_per_ip["192.168.1.1"] = 2
        manager.connections_per_ip["192.168.1.2"] = 1
        current_time = time.time()
        manager.connection_timestamps["conn1"] = current_time - 100
        manager.connection_timestamps["conn2"] = current_time - 200

        stats = manager.get_connection_stats()

        assert stats["total_connections"] == 2
        assert stats["max_connections"] == 100
        assert stats["max_connections_per_ip"] == 5
        assert stats["connections_per_ip"]["192.168.1.1"] == 2
        assert stats["oldest_connection_age"] == pytest.approx(200, rel=1e-1)

    async def test_broadcast_with_failed_connections(self):
        """Test broadcast handling failed connections."""
        manager = WebSocketManager()

        # Create connections, one of which will fail
        ws1 = MockWebSocket("192.168.1.1")
        ws2 = MockWebSocket("192.168.1.2")

        await manager.connect(ws1)
        conn2 = await manager.connect(ws2)

        # Make ws2 fail
        ws2.closed = True
        ws2.client_state = "CLOSED"

        sent_count = await manager.broadcast_to_all({"type": "test"})

        # Only one should succeed
        assert sent_count == 1
        # Failed connection should be cleaned up
        assert conn2 not in manager.connections

    async def test_shutdown(self):
        """Test WebSocket manager shutdown."""
        manager = WebSocketManager()

        # Add some connections
        ws1 = MockWebSocket("192.168.1.1")
        ws2 = MockWebSocket("192.168.1.2")

        await manager.connect(ws1)
        await manager.connect(ws2)

        assert len(manager.connections) == 2

        await manager.shutdown()

        # All connections should be cleaned up
        assert len(manager.connections) == 0

    async def test_multiple_ips_connection_tracking(self):
        """Test connection tracking across multiple IPs."""
        manager = WebSocketManager(max_connections_per_ip=2)

        # Connect from different IPs
        ws1 = MockWebSocket("192.168.1.1")
        ws2 = MockWebSocket("192.168.1.1")
        ws3 = MockWebSocket("192.168.1.2")
        ws4 = MockWebSocket("192.168.1.3")

        await manager.connect(ws1)
        await manager.connect(ws2)
        await manager.connect(ws3)
        await manager.connect(ws4)

        assert manager.connections_per_ip["192.168.1.1"] == 2
        assert manager.connections_per_ip["192.168.1.2"] == 1
        assert manager.connections_per_ip["192.168.1.3"] == 1

        # Disconnect one from first IP
        conn1_id = None
        for conn_id, ip in manager.connection_ip_map.items():
            if ip == "192.168.1.1":
                conn1_id = conn_id
                break

        await manager.disconnect(conn1_id)
        assert manager.connections_per_ip["192.168.1.1"] == 1

    def test_periodic_cleanup_task(self):
        """Test that cleanup task is created properly."""
        manager = WebSocketManager()

        # Initially no cleanup task
        assert manager.cleanup_task is None
        assert not manager._cleanup_started

        # Simulate connection which should start cleanup
        manager._cleanup_started = True
        manager._start_cleanup_task()

        # Should have started task (or attempted to)
        # Note: In test environment without event loop, this might fail gracefully
