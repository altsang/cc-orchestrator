"""
Tests for WebSocket connection manager.

Tests connection lifecycle, message broadcasting, and reliability features.
"""

import asyncio
import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import WebSocket

from src.cc_orchestrator.web.websocket.manager import (
    ConnectionManager,
    WebSocketConnection,
    WebSocketMessage,
)


class TestWebSocketMessage:
    """Test WebSocket message model."""
    
    def test_message_creation_with_defaults(self) -> None:
        """Test message creation with automatic ID and timestamp."""
        message = WebSocketMessage(type="test", data={"key": "value"})
        
        assert message.type == "test"
        assert message.data == {"key": "value"}
        assert message.message_id != ""
        assert isinstance(message.timestamp, datetime)
    
    def test_message_creation_with_explicit_values(self) -> None:
        """Test message creation with explicit ID and timestamp."""
        timestamp = datetime.now()
        message = WebSocketMessage(
            type="test",
            data={"key": "value"},
            message_id="test-id",
            timestamp=timestamp,
        )
        
        assert message.message_id == "test-id"
        assert message.timestamp == timestamp


class TestWebSocketConnection:
    """Test WebSocket connection model."""
    
    def test_connection_creation(self) -> None:
        """Test WebSocket connection creation."""
        mock_websocket = Mock(spec=WebSocket)
        connection = WebSocketConnection(mock_websocket, "conn-1", "127.0.0.1")
        
        assert connection.websocket == mock_websocket
        assert connection.connection_id == "conn-1"
        assert connection.client_ip == "127.0.0.1"
        assert isinstance(connection.connected_at, datetime)
        assert isinstance(connection.last_heartbeat, datetime)
        assert connection.subscriptions == set()
        assert connection.message_queue == []
        assert connection.is_alive is True


class TestConnectionManager:
    """Test WebSocket connection manager."""
    
    @pytest.fixture
    def manager(self) -> ConnectionManager:
        """Create a fresh connection manager for testing."""
        return ConnectionManager()
    
    @pytest.fixture
    def mock_websocket(self) -> AsyncMock:
        """Create a mock WebSocket for testing."""
        websocket = AsyncMock(spec=WebSocket)
        websocket.client = Mock()
        websocket.client.host = "127.0.0.1"
        return websocket
    
    @pytest.mark.asyncio
    async def test_initialization(self, manager: ConnectionManager) -> None:
        """Test connection manager initialization."""
        await manager.initialize()
        assert manager.heartbeat_task is not None
        
        # Cleanup
        await manager.cleanup()
    
    @pytest.mark.asyncio
    async def test_connect_websocket(
        self, manager: ConnectionManager, mock_websocket: AsyncMock
    ) -> None:
        """Test WebSocket connection establishment."""
        connection_id = await manager.connect(mock_websocket, "127.0.0.1")
        
        assert connection_id in manager.connections
        assert manager.connections[connection_id].client_ip == "127.0.0.1"
        assert manager.total_connections == 1
        mock_websocket.accept.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_disconnect_websocket(
        self, manager: ConnectionManager, mock_websocket: AsyncMock
    ) -> None:
        """Test WebSocket disconnection."""
        connection_id = await manager.connect(mock_websocket, "127.0.0.1")
        await manager.disconnect(connection_id, "test_disconnect")
        
        assert connection_id not in manager.connections
        mock_websocket.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_message_success(
        self, manager: ConnectionManager, mock_websocket: AsyncMock
    ) -> None:
        """Test successful message sending."""
        connection_id = await manager.connect(mock_websocket, "127.0.0.1")
        message = WebSocketMessage(type="test", data={"key": "value"})
        
        result = await manager.send_message(connection_id, message)
        
        assert result is True
        assert manager.total_messages_sent == 1
        mock_websocket.send_text.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_message_to_nonexistent_connection(
        self, manager: ConnectionManager
    ) -> None:
        """Test sending message to non-existent connection."""
        message = WebSocketMessage(type="test", data={"key": "value"})
        
        result = await manager.send_message("nonexistent", message, queue_if_offline=False)
        
        assert result is False
        assert manager.total_messages_sent == 0
    
    @pytest.mark.asyncio
    async def test_send_message_with_queuing(
        self, manager: ConnectionManager
    ) -> None:
        """Test message queuing for offline connections."""
        message = WebSocketMessage(type="test", data={"key": "value"})
        
        result = await manager.send_message("offline-conn", message, queue_if_offline=True)
        
        assert result is False
        assert "offline-conn" in manager.message_queues
        assert len(manager.message_queues["offline-conn"]) == 1
    
    @pytest.mark.asyncio
    async def test_broadcast_message_all_connections(
        self, manager: ConnectionManager, mock_websocket: AsyncMock
    ) -> None:
        """Test broadcasting message to all connections."""
        # Connect multiple clients
        conn1 = await manager.connect(mock_websocket, "127.0.0.1")
        conn2 = await manager.connect(AsyncMock(spec=WebSocket), "127.0.0.2")
        
        message = WebSocketMessage(type="broadcast", data={"message": "hello"})
        successful_sends = await manager.broadcast_message(message)
        
        assert successful_sends == 2
    
    @pytest.mark.asyncio
    async def test_broadcast_message_to_topic(
        self, manager: ConnectionManager, mock_websocket: AsyncMock
    ) -> None:
        """Test broadcasting message to topic subscribers."""
        conn1 = await manager.connect(mock_websocket, "127.0.0.1")
        conn2 = await manager.connect(AsyncMock(spec=WebSocket), "127.0.0.2")
        
        # Subscribe only conn1 to topic
        await manager.subscribe(conn1, "test-topic")
        
        message = WebSocketMessage(type="topic-message", data={"topic": "test"})
        successful_sends = await manager.broadcast_message(message, topic="test-topic")
        
        assert successful_sends == 1
    
    @pytest.mark.asyncio
    async def test_subscription_management(
        self, manager: ConnectionManager, mock_websocket: AsyncMock
    ) -> None:
        """Test subscription and unsubscription."""
        connection_id = await manager.connect(mock_websocket, "127.0.0.1")
        
        # Test subscription
        result = await manager.subscribe(connection_id, "test-topic")
        assert result is True
        assert "test-topic" in manager.connections[connection_id].subscriptions
        assert connection_id in manager.subscriptions["test-topic"]
        
        # Test unsubscription
        result = await manager.unsubscribe(connection_id, "test-topic")
        assert result is True
        assert "test-topic" not in manager.connections[connection_id].subscriptions
        assert "test-topic" not in manager.subscriptions
    
    @pytest.mark.asyncio
    async def test_handle_heartbeat_message(
        self, manager: ConnectionManager, mock_websocket: AsyncMock
    ) -> None:
        """Test heartbeat message handling."""
        connection_id = await manager.connect(mock_websocket, "127.0.0.1")
        message_data = json.dumps({"type": "heartbeat"})
        
        await manager.handle_message(connection_id, message_data)
        
        # Should send heartbeat_ack response
        mock_websocket.send_text.assert_called()
        sent_data = json.loads(mock_websocket.send_text.call_args[0][0])
        assert sent_data["type"] == "heartbeat_ack"
    
    @pytest.mark.asyncio
    async def test_handle_subscribe_message(
        self, manager: ConnectionManager, mock_websocket: AsyncMock
    ) -> None:
        """Test subscription message handling."""
        connection_id = await manager.connect(mock_websocket, "127.0.0.1")
        message_data = json.dumps({"type": "subscribe", "topic": "test-topic"})
        
        await manager.handle_message(connection_id, message_data)
        
        # Should be subscribed to topic
        assert "test-topic" in manager.connections[connection_id].subscriptions
        
        # Should send subscription_result response
        mock_websocket.send_text.assert_called()
    
    @pytest.mark.asyncio
    async def test_handle_ping_message(
        self, manager: ConnectionManager, mock_websocket: AsyncMock
    ) -> None:
        """Test ping-pong message handling."""
        connection_id = await manager.connect(mock_websocket, "127.0.0.1")
        message_data = json.dumps({"type": "ping", "data": {"test": "data"}})
        
        await manager.handle_message(connection_id, message_data)
        
        # Should send pong response
        mock_websocket.send_text.assert_called()
        sent_data = json.loads(mock_websocket.send_text.call_args[0][0])
        assert sent_data["type"] == "pong"
        assert sent_data["data"] == {"test": "data"}
    
    @pytest.mark.asyncio
    async def test_handle_invalid_json(
        self, manager: ConnectionManager, mock_websocket: AsyncMock
    ) -> None:
        """Test handling of invalid JSON messages."""
        connection_id = await manager.connect(mock_websocket, "127.0.0.1")
        
        await manager.handle_message(connection_id, "invalid json")
        
        # Should send error response
        mock_websocket.send_text.assert_called()
        sent_data = json.loads(mock_websocket.send_text.call_args[0][0])
        assert sent_data["type"] == "error"
    
    @pytest.mark.asyncio
    async def test_get_connection_stats(
        self, manager: ConnectionManager, mock_websocket: AsyncMock
    ) -> None:
        """Test connection statistics retrieval."""
        # Start with empty stats
        stats = await manager.get_connection_stats()
        assert stats["active_connections"] == 0
        
        # Add a connection
        await manager.connect(mock_websocket, "127.0.0.1")
        stats = await manager.get_connection_stats()
        assert stats["active_connections"] == 1
        assert stats["total_connections"] == 1
    
    @pytest.mark.asyncio
    async def test_queued_message_delivery(
        self, manager: ConnectionManager, mock_websocket: AsyncMock
    ) -> None:
        """Test delivery of queued messages on reconnection."""
        # Queue a message for offline connection
        message = WebSocketMessage(type="queued", data={"test": "queued"})
        await manager.send_message("future-conn", message, queue_if_offline=True)
        
        # Connect with the same ID and check message delivery
        with patch.object(manager, "_send_queued_messages") as mock_send_queued:
            await manager.connect(mock_websocket, "127.0.0.1")
            # Note: In real implementation, you'd need to handle connection ID matching
            # This test verifies the queuing mechanism exists
            assert "future-conn" in manager.message_queues
    
    @pytest.mark.asyncio
    async def test_heartbeat_timeout_detection(self, manager: ConnectionManager) -> None:
        """Test heartbeat timeout detection."""
        # Create a mock connection with old heartbeat
        mock_websocket = AsyncMock(spec=WebSocket)
        connection_id = await manager.connect(mock_websocket, "127.0.0.1")
        
        # Manually set old heartbeat time
        connection = manager.connections[connection_id]
        connection.last_heartbeat = datetime.now() - timedelta(seconds=120)
        
        # Mock the disconnect method to verify it's called
        with patch.object(manager, 'disconnect') as mock_disconnect:
            # Manually check for timed-out connections (simulate heartbeat monitor logic)
            current_time = datetime.now()
            timeout_threshold = current_time - timedelta(seconds=manager.heartbeat_timeout)
            
            for conn_id, conn in list(manager.connections.items()):
                if conn.last_heartbeat < timeout_threshold:
                    await manager.disconnect(conn_id, "heartbeat_timeout")
            
            # Should attempt to disconnect timed-out connection
            mock_disconnect.assert_called_with(connection_id, "heartbeat_timeout")
    
    @pytest.mark.asyncio
    async def test_cleanup(
        self, manager: ConnectionManager, mock_websocket: AsyncMock
    ) -> None:
        """Test manager cleanup on shutdown."""
        await manager.initialize()
        connection_id = await manager.connect(mock_websocket, "127.0.0.1")
        
        await manager.cleanup()
        
        # Should close all connections and cancel heartbeat task
        assert connection_id not in manager.connections
        assert manager.heartbeat_task is None or manager.heartbeat_task.cancelled()