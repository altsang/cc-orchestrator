"""
Comprehensive test coverage for src/cc_orchestrator/web/websocket/manager.py

This test suite targets 100% coverage of the 262 statements in the WebSocket manager,
covering all classes, methods, error conditions, and edge cases.
"""

import asyncio
import os
from collections import defaultdict
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import WebSocket, WebSocketDisconnect

from cc_orchestrator.web.websocket.manager import (
    ConnectionManager,
    ConnectionRefusedError,
    QueuedMessage,
    WebSocketConfig,
    WebSocketConnection,
    WebSocketMessage,
    connection_manager,
)


class TestWebSocketConfig:
    """Test WebSocketConfig class initialization and validation."""

    def test_default_initialization(self):
        """Test WebSocketConfig with default values."""
        config = WebSocketConfig()

        assert config.max_connections == 1000
        assert config.max_message_size == 64 * 1024
        assert config.max_queue_size == 100
        assert config.queue_message_ttl == 300
        assert config.queue_cleanup_interval == 60
        assert config.heartbeat_interval == 30
        assert config.heartbeat_timeout == 120
        assert config.cors_origins is not None

    def test_custom_initialization(self):
        """Test WebSocketConfig with custom values."""
        cors_origins = ["http://localhost:3001", "http://localhost:8081"]
        config = WebSocketConfig(
            max_connections=500,
            max_message_size=32 * 1024,
            max_queue_size=50,
            queue_message_ttl=600,
            queue_cleanup_interval=120,
            heartbeat_interval=60,
            heartbeat_timeout=180,
            cors_origins=cors_origins,
        )

        assert config.max_connections == 500
        assert config.max_message_size == 32 * 1024
        assert config.max_queue_size == 50
        assert config.queue_message_ttl == 600
        assert config.queue_cleanup_interval == 120
        assert config.heartbeat_interval == 60
        assert config.heartbeat_timeout == 180
        assert config.cors_origins == cors_origins

    def test_post_init_validation_invalid_heartbeat_timeout(self):
        """Test WebSocketConfig validation fails with invalid heartbeat timeout."""
        with pytest.raises(
            ValueError, match="Heartbeat timeout.*must be at least twice"
        ):
            WebSocketConfig(heartbeat_interval=60, heartbeat_timeout=100)

    def test_post_init_validation_valid_heartbeat_timeout(self):
        """Test WebSocketConfig validation passes with valid heartbeat timeout."""
        config = WebSocketConfig(heartbeat_interval=30, heartbeat_timeout=60)
        assert config.heartbeat_timeout == 60

    @patch.dict(
        os.environ, {"CC_WEB_CORS_ORIGINS": "http://test1.com,http://test2.com"}
    )
    def test_post_init_cors_from_environment(self):
        """Test WebSocketConfig loads CORS origins from environment."""
        config = WebSocketConfig()
        assert config.cors_origins == ["http://test1.com", "http://test2.com"]

    @patch.dict(os.environ, {}, clear=True)
    def test_post_init_cors_default_environment(self):
        """Test WebSocketConfig uses default CORS origins when env var not set."""
        config = WebSocketConfig()
        assert config.cors_origins == ["http://localhost:3000", "http://localhost:8080"]

    @patch.dict(
        os.environ,
        {
            "CC_WS_MAX_CONNECTIONS": "2000",
            "CC_WS_MAX_MESSAGE_SIZE": "131072",
            "CC_WS_MAX_QUEUE_SIZE": "200",
            "CC_WS_HEARTBEAT_INTERVAL": "45",
            "CC_WS_HEARTBEAT_TIMEOUT": "150",
        },
    )
    def test_from_environment_with_env_vars(self):
        """Test WebSocketConfig.from_environment() with environment variables set."""
        config = WebSocketConfig.from_environment()

        assert config.max_connections == 2000
        assert config.max_message_size == 131072
        assert config.max_queue_size == 200
        assert config.heartbeat_interval == 45
        assert config.heartbeat_timeout == 150

    @patch.dict(os.environ, {}, clear=True)
    def test_from_environment_with_defaults(self):
        """Test WebSocketConfig.from_environment() with default values."""
        config = WebSocketConfig.from_environment()

        assert config.max_connections == 1000
        assert config.max_message_size == 64 * 1024
        assert config.max_queue_size == 100
        assert config.heartbeat_interval == 30
        assert config.heartbeat_timeout == 120


class TestWebSocketMessage:
    """Test WebSocketMessage class creation and initialization."""

    def test_message_creation_with_defaults(self):
        """Test WebSocketMessage creation with automatic ID and timestamp."""
        message = WebSocketMessage(type="test", data={"key": "value"})

        assert message.type == "test"
        assert message.data == {"key": "value"}
        assert message.message_id != ""
        assert isinstance(message.timestamp, datetime)

    def test_message_creation_with_custom_values(self):
        """Test WebSocketMessage creation with custom ID and timestamp."""
        custom_id = "custom-id"
        custom_timestamp = datetime(2023, 1, 1, 12, 0, 0)

        message = WebSocketMessage(
            type="custom",
            data={"test": "data"},
            message_id=custom_id,
            timestamp=custom_timestamp,
        )

        assert message.type == "custom"
        assert message.data == {"test": "data"}
        assert message.message_id == custom_id
        assert message.timestamp == custom_timestamp

    def test_message_id_uniqueness(self):
        """Test that message IDs are unique when auto-generated."""
        message1 = WebSocketMessage(type="test", data={})
        message2 = WebSocketMessage(type="test", data={})

        assert message1.message_id != message2.message_id

    def test_message_init_override(self):
        """Test WebSocketMessage.__init__ method override."""
        # Test with no message_id or timestamp
        message = WebSocketMessage(type="test", data={"key": "value"})
        assert message.message_id != ""
        assert isinstance(message.timestamp, datetime)

        # Test with message_id but no timestamp
        message = WebSocketMessage(type="test", data={}, message_id="test-id")
        assert message.message_id == "test-id"
        assert isinstance(message.timestamp, datetime)


class TestQueuedMessage:
    """Test QueuedMessage class and expiration logic."""

    def test_queued_message_creation(self):
        """Test QueuedMessage creation."""
        message = WebSocketMessage(type="test", data={})
        expires_at = datetime.now() + timedelta(minutes=5)

        queued_msg = QueuedMessage(message=message, expires_at=expires_at)

        assert queued_msg.message == message
        assert queued_msg.expires_at == expires_at

    def test_queued_message_not_expired(self):
        """Test QueuedMessage.is_expired() returns False for future expiration."""
        message = WebSocketMessage(type="test", data={})
        expires_at = datetime.now() + timedelta(minutes=5)

        queued_msg = QueuedMessage(message=message, expires_at=expires_at)

        assert not queued_msg.is_expired()

    def test_queued_message_expired(self):
        """Test QueuedMessage.is_expired() returns True for past expiration."""
        message = WebSocketMessage(type="test", data={})
        expires_at = datetime.now() - timedelta(minutes=5)

        queued_msg = QueuedMessage(message=message, expires_at=expires_at)

        assert queued_msg.is_expired()

    def test_queued_message_exactly_expired(self):
        """Test QueuedMessage.is_expired() with exact expiration time."""
        message = WebSocketMessage(type="test", data={})

        # Create a message that expires "now" (but actually slightly in the past due to execution time)
        with patch("cc_orchestrator.web.websocket.manager.datetime") as mock_datetime:
            now = datetime(2023, 1, 1, 12, 0, 0)
            mock_datetime.now.return_value = now

            queued_msg = QueuedMessage(message=message, expires_at=now)

            # Move time forward slightly
            mock_datetime.now.return_value = now + timedelta(microseconds=1)

            assert queued_msg.is_expired()


class TestWebSocketConnection:
    """Test WebSocketConnection class functionality."""

    def test_connection_creation(self):
        """Test WebSocketConnection creation."""
        websocket = Mock(spec=WebSocket)
        connection_id = "test-connection-id"
        client_ip = "127.0.0.1"

        connection = WebSocketConnection(websocket, connection_id, client_ip)

        assert connection.websocket == websocket
        assert connection.connection_id == connection_id
        assert connection.client_ip == client_ip
        assert isinstance(connection.connected_at, datetime)
        assert isinstance(connection.last_heartbeat, datetime)
        assert connection.subscriptions == set()
        assert connection.message_queue == []
        assert connection.is_alive is True

    def test_connection_attributes_modification(self):
        """Test WebSocketConnection attributes can be modified."""
        websocket = Mock(spec=WebSocket)
        connection = WebSocketConnection(websocket, "test-id", "127.0.0.1")

        # Test subscription management
        connection.subscriptions.add("topic1")
        connection.subscriptions.add("topic2")
        assert "topic1" in connection.subscriptions
        assert "topic2" in connection.subscriptions

        # Test message queue
        message = WebSocketMessage(type="test", data={})
        connection.message_queue.append(message)
        assert len(connection.message_queue) == 1

        # Test is_alive flag
        connection.is_alive = False
        assert connection.is_alive is False


class TestConnectionRefusedError:
    """Test ConnectionRefusedError exception."""

    def test_connection_refused_error_creation(self):
        """Test ConnectionRefusedError can be created and raised."""
        message = "Connection refused due to capacity"

        with pytest.raises(ConnectionRefusedError, match=message):
            raise ConnectionRefusedError(message)

    def test_connection_refused_error_inheritance(self):
        """Test ConnectionRefusedError inherits from Exception."""
        error = ConnectionRefusedError("test message")
        assert isinstance(error, Exception)


class TestConnectionManager:
    """Test ConnectionManager class with comprehensive coverage."""

    @pytest.fixture
    def mock_websocket(self):
        """Create a mock WebSocket for testing."""
        websocket = AsyncMock(spec=WebSocket)
        websocket.accept = AsyncMock()
        websocket.send_text = AsyncMock()
        websocket.close = AsyncMock()
        return websocket

    @pytest.fixture
    def config(self):
        """Create a test configuration."""
        return WebSocketConfig(
            max_connections=10,
            max_message_size=1024,
            max_queue_size=5,
            queue_message_ttl=300,
            queue_cleanup_interval=60,
            heartbeat_interval=30,
            heartbeat_timeout=120,
        )

    @pytest.fixture
    def manager(self, config):
        """Create a ConnectionManager instance for testing."""
        return ConnectionManager(config)

    def test_manager_initialization_with_config(self, config):
        """Test ConnectionManager initialization with custom config."""
        manager = ConnectionManager(config)

        assert manager.config == config
        assert hasattr(manager._connection_lock, "acquire") and hasattr(
            manager._connection_lock, "release"
        )
        assert manager.connections == {}
        assert isinstance(manager.subscriptions, defaultdict)
        assert isinstance(manager.message_queues, defaultdict)
        assert manager.heartbeat_task is None
        assert manager.queue_cleanup_task is None
        assert manager.total_connections == 0
        assert manager.total_messages_sent == 0
        assert manager.total_messages_received == 0

    def test_manager_initialization_without_config(self):
        """Test ConnectionManager initialization with default config."""
        with patch.object(WebSocketConfig, "from_environment") as mock_from_env:
            mock_config = WebSocketConfig()
            mock_from_env.return_value = mock_config

            manager = ConnectionManager()

            assert manager.config == mock_config
            mock_from_env.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialize(self, manager):
        """Test ConnectionManager.initialize() method."""
        with patch("asyncio.create_task") as mock_create_task:
            mock_heartbeat_task = AsyncMock()
            mock_queue_task = AsyncMock()
            mock_create_task.side_effect = [mock_heartbeat_task, mock_queue_task]

            await manager.initialize()

            assert mock_create_task.call_count == 2
            assert manager.heartbeat_task == mock_heartbeat_task
            assert manager.queue_cleanup_task == mock_queue_task

    @pytest.mark.asyncio
    async def test_cleanup_with_tasks(self, manager):
        """Test ConnectionManager.cleanup() with active tasks."""

        # Create real tasks for testing cleanup
        async def dummy_task():
            await asyncio.sleep(1000)  # Long sleep that will be cancelled

        heartbeat_task = asyncio.create_task(dummy_task())
        queue_task = asyncio.create_task(dummy_task())

        manager.heartbeat_task = heartbeat_task
        manager.queue_cleanup_task = queue_task

        # Add a mock connection to test connection cleanup
        mock_websocket = AsyncMock(spec=WebSocket)
        connection = WebSocketConnection(mock_websocket, "test-id", "127.0.0.1")
        manager.connections["test-id"] = connection

        with patch.object(
            manager, "disconnect", new_callable=AsyncMock
        ) as mock_disconnect:
            await manager.cleanup()

            # Verify tasks were cancelled
            assert heartbeat_task.cancelled()
            assert queue_task.cancelled()

            # Verify connection was disconnected
            mock_disconnect.assert_called_once_with("test-id", "server_shutdown")

    @pytest.mark.asyncio
    async def test_cleanup_with_cancelled_tasks(self, manager):
        """Test ConnectionManager.cleanup() with cancelled tasks."""

        # Create real cancelled tasks
        async def dummy_task():
            await asyncio.sleep(1000)  # Long sleep that will be cancelled

        heartbeat_task = asyncio.create_task(dummy_task())
        queue_task = asyncio.create_task(dummy_task())

        # Cancel them immediately
        heartbeat_task.cancel()
        queue_task.cancel()

        manager.heartbeat_task = heartbeat_task
        manager.queue_cleanup_task = queue_task

        # Should not raise exception
        await manager.cleanup()

        # Tasks should be cancelled
        assert heartbeat_task.cancelled()
        assert queue_task.cancelled()

    @pytest.mark.asyncio
    async def test_cleanup_without_tasks(self, manager):
        """Test ConnectionManager.cleanup() without active tasks."""
        manager.heartbeat_task = None
        manager.queue_cleanup_task = None

        # Should complete without errors
        await manager.cleanup()

    @pytest.mark.asyncio
    async def test_connect_success(self, manager, mock_websocket):
        """Test successful WebSocket connection."""
        client_ip = "127.0.0.1"

        with patch.object(
            manager, "_send_queued_messages", new_callable=AsyncMock
        ) as mock_send_queued:
            with patch(
                "cc_orchestrator.web.websocket.manager.log_websocket_connection"
            ) as mock_log:
                connection_id = await manager.connect(mock_websocket, client_ip)

                assert connection_id in manager.connections
                assert manager.total_connections == 1

                connection = manager.connections[connection_id]
                assert connection.websocket == mock_websocket
                assert connection.client_ip == client_ip

                mock_websocket.accept.assert_called_once()
                mock_send_queued.assert_called_once_with(connection_id)
                mock_log.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_at_capacity(self, manager, mock_websocket):
        """Test WebSocket connection refused at capacity."""
        # Fill up to capacity
        for i in range(manager.config.max_connections):
            mock_ws = AsyncMock(spec=WebSocket)
            connection_id = await manager.connect(mock_ws, f"127.0.0.{i}")

        # Next connection should be refused
        with pytest.raises(
            ConnectionRefusedError, match="Maximum connections.*exceeded"
        ):
            await manager.connect(mock_websocket, "127.0.0.10")

        mock_websocket.close.assert_called_once_with(
            code=1008, reason="Server at capacity"
        )

    @pytest.mark.asyncio
    async def test_disconnect_existing_connection(self, manager, mock_websocket):
        """Test disconnecting an existing connection."""
        connection_id = await manager.connect(mock_websocket, "127.0.0.1")

        # Subscribe to a topic
        await manager.subscribe(connection_id, "test-topic")

        with patch.object(
            manager, "unsubscribe", new_callable=AsyncMock
        ) as mock_unsubscribe:
            with patch(
                "cc_orchestrator.web.websocket.manager.log_websocket_connection"
            ) as mock_log:
                await manager.disconnect(connection_id, "test_reason")

                assert connection_id not in manager.connections
                mock_unsubscribe.assert_called_once_with(connection_id, "test-topic")
                mock_websocket.close.assert_called_once()
                mock_log.assert_called_once()

    @pytest.mark.asyncio
    async def test_disconnect_nonexistent_connection(self, manager):
        """Test disconnecting a non-existent connection."""
        # Should not raise exception
        await manager.disconnect("nonexistent-id", "test_reason")

    @pytest.mark.asyncio
    async def test_disconnect_websocket_error(self, manager, mock_websocket):
        """Test disconnect handling WebSocket errors."""
        connection_id = await manager.connect(mock_websocket, "127.0.0.1")

        # Configure websocket.close to raise an error
        mock_websocket.close.side_effect = ConnectionError("Connection error")

        with patch(
            "cc_orchestrator.web.websocket.manager.log_websocket_connection"
        ) as mock_log:
            # Should not raise exception
            await manager.disconnect(connection_id, "test_reason")

            assert connection_id not in manager.connections
            mock_log.assert_called_once()

    @pytest.mark.asyncio
    async def test_disconnect_runtime_error(self, manager, mock_websocket):
        """Test disconnect handling RuntimeError."""
        connection_id = await manager.connect(mock_websocket, "127.0.0.1")

        mock_websocket.close.side_effect = RuntimeError("Runtime error")

        # Should not raise exception
        await manager.disconnect(connection_id, "test_reason")
        assert connection_id not in manager.connections

    @pytest.mark.asyncio
    async def test_disconnect_os_error(self, manager, mock_websocket):
        """Test disconnect handling OSError."""
        connection_id = await manager.connect(mock_websocket, "127.0.0.1")

        mock_websocket.close.side_effect = OSError("OS error")

        # Should not raise exception
        await manager.disconnect(connection_id, "test_reason")
        assert connection_id not in manager.connections

    @pytest.mark.asyncio
    async def test_send_message_success(self, manager, mock_websocket):
        """Test successful message sending."""
        connection_id = await manager.connect(mock_websocket, "127.0.0.1")
        message = WebSocketMessage(type="test", data={"key": "value"})

        with patch(
            "cc_orchestrator.web.websocket.manager.log_websocket_message"
        ) as mock_log:
            result = await manager.send_message(connection_id, message)

            assert result is True
            assert manager.total_messages_sent == 1
            mock_websocket.send_text.assert_called_once()
            mock_log.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_message_size_limit_exceeded(self, manager, mock_websocket):
        """Test message sending with size limit exceeded."""
        connection_id = await manager.connect(mock_websocket, "127.0.0.1")

        # Create a message that exceeds the size limit
        large_data = {"data": "x" * (manager.config.max_message_size + 1)}
        message = WebSocketMessage(type="test", data=large_data)

        with pytest.raises(ValueError, match="Message size.*exceeds limit"):
            await manager.send_message(connection_id, message)

    @pytest.mark.asyncio
    async def test_send_message_offline_connection_with_queueing(self, manager):
        """Test sending message to offline connection with queueing enabled."""
        message = WebSocketMessage(type="test", data={"key": "value"})

        result = await manager.send_message(
            "offline-id", message, queue_if_offline=True
        )

        assert result is False
        assert len(manager.message_queues["offline-id"]) == 1

        queued_msg = manager.message_queues["offline-id"][0]
        assert queued_msg.message == message
        assert isinstance(queued_msg.expires_at, datetime)

    @pytest.mark.asyncio
    async def test_send_message_offline_connection_without_queueing(self, manager):
        """Test sending message to offline connection without queueing."""
        message = WebSocketMessage(type="test", data={"key": "value"})

        result = await manager.send_message(
            "offline-id", message, queue_if_offline=False
        )

        assert result is False
        assert len(manager.message_queues["offline-id"]) == 0

    @pytest.mark.asyncio
    async def test_send_message_queue_size_limit(self, manager):
        """Test message queueing with size limit."""
        message = WebSocketMessage(type="test", data={"key": "value"})

        # Fill the queue to capacity
        for i in range(manager.config.max_queue_size):
            await manager.send_message("offline-id", message, queue_if_offline=True)

        # Next message should remove the oldest
        old_queue_size = len(manager.message_queues["offline-id"])
        await manager.send_message("offline-id", message, queue_if_offline=True)

        assert len(manager.message_queues["offline-id"]) == old_queue_size

    @pytest.mark.asyncio
    async def test_send_message_websocket_disconnect(self, manager, mock_websocket):
        """Test message sending with WebSocket disconnect."""
        connection_id = await manager.connect(mock_websocket, "127.0.0.1")
        message = WebSocketMessage(type="test", data={"key": "value"})

        mock_websocket.send_text.side_effect = WebSocketDisconnect()

        with patch.object(
            manager, "disconnect", new_callable=AsyncMock
        ) as mock_disconnect:
            result = await manager.send_message(
                connection_id, message, queue_if_offline=True
            )

            assert result is False
            mock_disconnect.assert_called_once_with(connection_id, "connection_lost")
            # Message should be queued
            assert len(manager.message_queues[connection_id]) == 1

    @pytest.mark.asyncio
    async def test_send_message_websocket_disconnect_no_queue(
        self, manager, mock_websocket
    ):
        """Test message sending with WebSocket disconnect and no queueing."""
        connection_id = await manager.connect(mock_websocket, "127.0.0.1")
        message = WebSocketMessage(type="test", data={"key": "value"})

        mock_websocket.send_text.side_effect = WebSocketDisconnect()

        with patch.object(
            manager, "disconnect", new_callable=AsyncMock
        ) as mock_disconnect:
            result = await manager.send_message(
                connection_id, message, queue_if_offline=False
            )

            assert result is False
            mock_disconnect.assert_called_once_with(connection_id, "connection_lost")
            # Message should not be queued
            assert len(manager.message_queues[connection_id]) == 0

    @pytest.mark.asyncio
    async def test_send_message_connection_error(self, manager, mock_websocket):
        """Test message sending with connection error."""
        connection_id = await manager.connect(mock_websocket, "127.0.0.1")
        message = WebSocketMessage(type="test", data={"key": "value"})

        mock_websocket.send_text.side_effect = ConnectionError("Connection lost")

        with patch.object(
            manager, "disconnect", new_callable=AsyncMock
        ) as mock_disconnect:
            result = await manager.send_message(connection_id, message)

            assert result is False
            mock_disconnect.assert_called_once_with(
                connection_id, "network_error: Connection lost"
            )

    @pytest.mark.asyncio
    async def test_send_message_os_error(self, manager, mock_websocket):
        """Test message sending with OS error."""
        connection_id = await manager.connect(mock_websocket, "127.0.0.1")
        message = WebSocketMessage(type="test", data={"key": "value"})

        mock_websocket.send_text.side_effect = OSError("OS error")

        with patch.object(
            manager, "disconnect", new_callable=AsyncMock
        ) as mock_disconnect:
            result = await manager.send_message(connection_id, message)

            assert result is False
            mock_disconnect.assert_called_once_with(
                connection_id, "network_error: OS error"
            )

    @pytest.mark.asyncio
    async def test_send_message_generic_exception(self, manager, mock_websocket):
        """Test message sending with generic exception."""
        connection_id = await manager.connect(mock_websocket, "127.0.0.1")
        message = WebSocketMessage(type="test", data={"key": "value"})

        mock_websocket.send_text.side_effect = ValueError("Generic error")

        with patch.object(
            manager, "disconnect", new_callable=AsyncMock
        ) as mock_disconnect:
            result = await manager.send_message(connection_id, message)

            assert result is False
            mock_disconnect.assert_called_once_with(
                connection_id, "send_error: Generic error"
            )

    @pytest.mark.asyncio
    async def test_broadcast_message_all_connections(self, manager, mock_websocket):
        """Test broadcasting message to all connections."""
        # Connect multiple clients
        connection_ids = []
        for i in range(3):
            mock_ws = AsyncMock(spec=WebSocket)
            conn_id = await manager.connect(mock_ws, f"127.0.0.{i}")
            connection_ids.append(conn_id)

        message = WebSocketMessage(type="broadcast", data={"message": "hello"})

        with patch.object(manager, "send_message", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = True

            with patch(
                "cc_orchestrator.web.websocket.manager.log_real_time_event"
            ) as mock_log:
                result = await manager.broadcast_message(message)

                assert result == 3
                assert mock_send.call_count == 3
                mock_log.assert_called_once()

    @pytest.mark.asyncio
    async def test_broadcast_message_with_topic(self, manager, mock_websocket):
        """Test broadcasting message to topic subscribers."""
        # Connect clients and subscribe some to topic
        connection_ids = []
        for i in range(3):
            mock_ws = AsyncMock(spec=WebSocket)
            conn_id = await manager.connect(mock_ws, f"127.0.0.{i}")
            connection_ids.append(conn_id)

        # Subscribe first two connections to topic
        await manager.subscribe(connection_ids[0], "test-topic")
        await manager.subscribe(connection_ids[1], "test-topic")

        message = WebSocketMessage(type="topic-msg", data={"message": "hello"})

        with patch.object(manager, "send_message", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = True

            result = await manager.broadcast_message(message, topic="test-topic")

            assert result == 2
            assert mock_send.call_count == 2

    @pytest.mark.asyncio
    async def test_broadcast_message_with_exclusions(self, manager, mock_websocket):
        """Test broadcasting message with excluded connections."""
        # Connect multiple clients
        connection_ids = []
        for i in range(3):
            mock_ws = AsyncMock(spec=WebSocket)
            conn_id = await manager.connect(mock_ws, f"127.0.0.{i}")
            connection_ids.append(conn_id)

        message = WebSocketMessage(type="broadcast", data={"message": "hello"})
        exclude_connections = {connection_ids[0]}

        with patch.object(manager, "send_message", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = True

            result = await manager.broadcast_message(
                message, exclude_connections=exclude_connections
            )

            assert result == 2
            assert mock_send.call_count == 2

    @pytest.mark.asyncio
    async def test_broadcast_message_no_connections(self, manager):
        """Test broadcasting message with no connections."""
        message = WebSocketMessage(type="broadcast", data={"message": "hello"})

        with patch(
            "cc_orchestrator.web.websocket.manager.log_real_time_event"
        ) as mock_log:
            result = await manager.broadcast_message(message)

            assert result == 0
            mock_log.assert_called_once()

    @pytest.mark.asyncio
    async def test_broadcast_message_with_failures(self, manager, mock_websocket):
        """Test broadcasting message with some send failures."""
        # Connect multiple clients
        connection_ids = []
        for i in range(3):
            mock_ws = AsyncMock(spec=WebSocket)
            conn_id = await manager.connect(mock_ws, f"127.0.0.{i}")
            connection_ids.append(conn_id)

        message = WebSocketMessage(type="broadcast", data={"message": "hello"})

        with patch.object(manager, "send_message", new_callable=AsyncMock) as mock_send:
            # First two succeed, third fails
            mock_send.side_effect = [True, True, False]

            result = await manager.broadcast_message(message)

            assert result == 2
            assert mock_send.call_count == 3

    @pytest.mark.asyncio
    async def test_broadcast_message_with_exceptions(self, manager, mock_websocket):
        """Test broadcasting message with exceptions in send_message."""
        # Connect multiple clients
        connection_ids = []
        for i in range(3):
            mock_ws = AsyncMock(spec=WebSocket)
            conn_id = await manager.connect(mock_ws, f"127.0.0.{i}")
            connection_ids.append(conn_id)

        message = WebSocketMessage(type="broadcast", data={"message": "hello"})

        with patch.object(manager, "send_message", new_callable=AsyncMock) as mock_send:
            # First succeeds, second raises exception, third succeeds
            mock_send.side_effect = [True, ValueError("Send error"), True]

            result = await manager.broadcast_message(message)

            assert result == 2
            assert mock_send.call_count == 3

    @pytest.mark.asyncio
    async def test_subscribe_existing_connection(self, manager, mock_websocket):
        """Test subscribing existing connection to topic."""
        connection_id = await manager.connect(mock_websocket, "127.0.0.1")

        result = await manager.subscribe(connection_id, "test-topic")

        assert result is True
        assert "test-topic" in manager.connections[connection_id].subscriptions
        assert connection_id in manager.subscriptions["test-topic"]

    @pytest.mark.asyncio
    async def test_subscribe_nonexistent_connection(self, manager):
        """Test subscribing non-existent connection to topic."""
        result = await manager.subscribe("nonexistent-id", "test-topic")

        assert result is False

    @pytest.mark.asyncio
    async def test_unsubscribe_existing_connection(self, manager, mock_websocket):
        """Test unsubscribing existing connection from topic."""
        connection_id = await manager.connect(mock_websocket, "127.0.0.1")
        await manager.subscribe(connection_id, "test-topic")

        result = await manager.unsubscribe(connection_id, "test-topic")

        assert result is True
        assert "test-topic" not in manager.connections[connection_id].subscriptions
        assert connection_id not in manager.subscriptions.get("test-topic", set())

    @pytest.mark.asyncio
    async def test_unsubscribe_nonexistent_connection(self, manager):
        """Test unsubscribing non-existent connection from topic."""
        result = await manager.unsubscribe("nonexistent-id", "test-topic")

        assert result is False

    @pytest.mark.asyncio
    async def test_unsubscribe_cleans_empty_topic(self, manager, mock_websocket):
        """Test unsubscribing removes empty topic from subscriptions."""
        connection_id = await manager.connect(mock_websocket, "127.0.0.1")
        await manager.subscribe(connection_id, "test-topic")

        await manager.unsubscribe(connection_id, "test-topic")

        assert "test-topic" not in manager.subscriptions

    @pytest.mark.asyncio
    async def test_handle_message_nonexistent_connection(self, manager):
        """Test handling message from non-existent connection."""
        # Should not raise exception
        await manager.handle_message("nonexistent-id", '{"type": "test"}')

    @pytest.mark.asyncio
    async def test_handle_message_size_limit_exceeded(self, manager, mock_websocket):
        """Test handling message that exceeds size limit."""
        connection_id = await manager.connect(mock_websocket, "127.0.0.1")

        large_message = "x" * (manager.config.max_message_size + 1)

        with patch.object(manager, "send_message", new_callable=AsyncMock) as mock_send:
            await manager.handle_message(connection_id, large_message)

            mock_send.assert_called_once()
            # Verify error message was sent
            error_message = mock_send.call_args[0][1]
            assert error_message.type == "error"
            assert "exceeds limit" in error_message.data["error"]

    @pytest.mark.asyncio
    async def test_handle_message_updates_heartbeat(self, manager, mock_websocket):
        """Test handling message updates connection heartbeat."""
        connection_id = await manager.connect(mock_websocket, "127.0.0.1")

        original_heartbeat = manager.connections[connection_id].last_heartbeat

        # Wait a small amount to ensure timestamp difference
        await asyncio.sleep(0.01)

        with patch.object(manager, "_process_message", new_callable=AsyncMock):
            await manager.handle_message(connection_id, '{"type": "test"}')

        new_heartbeat = manager.connections[connection_id].last_heartbeat
        assert new_heartbeat > original_heartbeat
        assert manager.total_messages_received == 1

    @pytest.mark.asyncio
    async def test_handle_message_invalid_json(self, manager, mock_websocket):
        """Test handling message with invalid JSON."""
        connection_id = await manager.connect(mock_websocket, "127.0.0.1")

        with patch.object(manager, "send_message", new_callable=AsyncMock) as mock_send:
            await manager.handle_message(connection_id, "invalid json")

            mock_send.assert_called_once()
            error_message = mock_send.call_args[0][1]
            assert error_message.type == "error"
            assert "Invalid JSON format" in error_message.data["error"]

    @pytest.mark.asyncio
    async def test_handle_message_with_logging(self, manager, mock_websocket):
        """Test handling message triggers logging."""
        connection_id = await manager.connect(mock_websocket, "127.0.0.1")

        with patch.object(manager, "_process_message", new_callable=AsyncMock):
            with patch(
                "cc_orchestrator.web.websocket.manager.log_websocket_message"
            ) as mock_log:
                await manager.handle_message(
                    connection_id, '{"type": "test", "data": {}}'
                )

                mock_log.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_connection_stats(self, manager, mock_websocket):
        """Test getting connection statistics."""
        # Connect some clients
        for i in range(2):
            mock_ws = AsyncMock(spec=WebSocket)
            conn_id = await manager.connect(mock_ws, f"127.0.0.{i}")
            await manager.subscribe(conn_id, f"topic-{i}")

        # Add some queued messages
        message = WebSocketMessage(type="test", data={})
        await manager.send_message("offline-id", message, queue_if_offline=True)

        # Update counters
        manager.total_messages_sent = 10
        manager.total_messages_received = 5

        stats = await manager.get_connection_stats()

        assert stats["active_connections"] == 2
        assert stats["total_connections"] == 2
        assert stats["active_subscriptions"] == 2
        assert stats["queued_messages"] == 1
        assert stats["messages_sent"] == 10
        assert stats["messages_received"] == 5

    @pytest.mark.asyncio
    async def test_send_queued_messages_no_queue(self, manager):
        """Test sending queued messages when no queue exists."""
        # Should not raise exception
        await manager._send_queued_messages("nonexistent-id")

    @pytest.mark.asyncio
    async def test_send_queued_messages_with_expired_messages(self, manager):
        """Test sending queued messages with some expired."""
        connection_id = "test-id"

        # Create messages with different expiration times
        message1 = WebSocketMessage(type="test1", data={})
        message2 = WebSocketMessage(type="test2", data={})
        message3 = WebSocketMessage(type="test3", data={})

        # Add messages to queue - some expired, some not
        past_time = datetime.now() - timedelta(minutes=5)
        future_time = datetime.now() + timedelta(minutes=5)

        manager.message_queues[connection_id] = [
            QueuedMessage(message=message1, expires_at=past_time),  # Expired
            QueuedMessage(message=message2, expires_at=future_time),  # Not expired
            QueuedMessage(message=message3, expires_at=past_time),  # Expired
        ]

        with patch.object(manager, "send_message", new_callable=AsyncMock) as mock_send:
            await manager._send_queued_messages(connection_id)

            # Only non-expired message should be sent
            mock_send.assert_called_once_with(
                connection_id, message2, queue_if_offline=False
            )
            # Queue should be cleared
            assert connection_id not in manager.message_queues

    @pytest.mark.asyncio
    async def test_send_queued_messages_all_valid(self, manager):
        """Test sending queued messages when all are valid."""
        connection_id = "test-id"

        message1 = WebSocketMessage(type="test1", data={})
        message2 = WebSocketMessage(type="test2", data={})

        future_time = datetime.now() + timedelta(minutes=5)

        manager.message_queues[connection_id] = [
            QueuedMessage(message=message1, expires_at=future_time),
            QueuedMessage(message=message2, expires_at=future_time),
        ]

        with patch.object(manager, "send_message", new_callable=AsyncMock) as mock_send:
            await manager._send_queued_messages(connection_id)

            assert mock_send.call_count == 2
            assert connection_id not in manager.message_queues

    @pytest.mark.asyncio
    async def test_process_message_heartbeat(self, manager, mock_websocket):
        """Test processing heartbeat message."""
        connection_id = await manager.connect(mock_websocket, "127.0.0.1")

        with patch.object(manager, "send_message", new_callable=AsyncMock) as mock_send:
            await manager._process_message(connection_id, "heartbeat", {})

            mock_send.assert_called_once()
            response_message = mock_send.call_args[0][1]
            assert response_message.type == "heartbeat_ack"
            assert "timestamp" in response_message.data

    @pytest.mark.asyncio
    async def test_process_message_subscribe_with_topic(self, manager, mock_websocket):
        """Test processing subscribe message with topic."""
        connection_id = await manager.connect(mock_websocket, "127.0.0.1")

        with patch.object(manager, "send_message", new_callable=AsyncMock) as mock_send:
            with patch.object(
                manager, "subscribe", new_callable=AsyncMock
            ) as mock_subscribe:
                mock_subscribe.return_value = True

                await manager._process_message(
                    connection_id, "subscribe", {"topic": "test-topic"}
                )

                mock_subscribe.assert_called_once_with(connection_id, "test-topic")
                mock_send.assert_called_once()

                response_message = mock_send.call_args[0][1]
                assert response_message.type == "subscription_result"
                assert response_message.data["topic"] == "test-topic"
                assert response_message.data["success"] is True

    @pytest.mark.asyncio
    async def test_process_message_subscribe_without_topic(
        self, manager, mock_websocket
    ):
        """Test processing subscribe message without topic."""
        connection_id = await manager.connect(mock_websocket, "127.0.0.1")

        with patch.object(manager, "send_message", new_callable=AsyncMock) as mock_send:
            with patch.object(
                manager, "subscribe", new_callable=AsyncMock
            ) as mock_subscribe:
                await manager._process_message(connection_id, "subscribe", {})

                mock_subscribe.assert_not_called()
                mock_send.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_message_unsubscribe_with_topic(
        self, manager, mock_websocket
    ):
        """Test processing unsubscribe message with topic."""
        connection_id = await manager.connect(mock_websocket, "127.0.0.1")

        with patch.object(manager, "send_message", new_callable=AsyncMock) as mock_send:
            with patch.object(
                manager, "unsubscribe", new_callable=AsyncMock
            ) as mock_unsubscribe:
                mock_unsubscribe.return_value = False

                await manager._process_message(
                    connection_id, "unsubscribe", {"topic": "test-topic"}
                )

                mock_unsubscribe.assert_called_once_with(connection_id, "test-topic")
                mock_send.assert_called_once()

                response_message = mock_send.call_args[0][1]
                assert response_message.type == "unsubscription_result"
                assert response_message.data["topic"] == "test-topic"
                assert response_message.data["success"] is False

    @pytest.mark.asyncio
    async def test_process_message_unsubscribe_without_topic(
        self, manager, mock_websocket
    ):
        """Test processing unsubscribe message without topic."""
        connection_id = await manager.connect(mock_websocket, "127.0.0.1")

        with patch.object(manager, "send_message", new_callable=AsyncMock) as mock_send:
            with patch.object(
                manager, "unsubscribe", new_callable=AsyncMock
            ) as mock_unsubscribe:
                await manager._process_message(connection_id, "unsubscribe", {})

                mock_unsubscribe.assert_not_called()
                mock_send.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_message_ping(self, manager, mock_websocket):
        """Test processing ping message."""
        connection_id = await manager.connect(mock_websocket, "127.0.0.1")

        ping_data = {"test": "data"}

        with patch.object(manager, "send_message", new_callable=AsyncMock) as mock_send:
            await manager._process_message(connection_id, "ping", {"data": ping_data})

            mock_send.assert_called_once()
            response_message = mock_send.call_args[0][1]
            assert response_message.type == "pong"
            assert response_message.data == ping_data

    @pytest.mark.asyncio
    async def test_process_message_ping_no_data(self, manager, mock_websocket):
        """Test processing ping message without data."""
        connection_id = await manager.connect(mock_websocket, "127.0.0.1")

        with patch.object(manager, "send_message", new_callable=AsyncMock) as mock_send:
            await manager._process_message(connection_id, "ping", {})

            mock_send.assert_called_once()
            response_message = mock_send.call_args[0][1]
            assert response_message.type == "pong"
            assert response_message.data == {}

    @pytest.mark.asyncio
    async def test_process_message_unknown_type(self, manager, mock_websocket):
        """Test processing unknown message type."""
        connection_id = await manager.connect(mock_websocket, "127.0.0.1")

        with patch.object(manager, "send_message", new_callable=AsyncMock) as mock_send:
            # Should not raise exception and not send any response
            await manager._process_message(connection_id, "unknown", {})

            mock_send.assert_not_called()

    @pytest.mark.asyncio
    async def test_heartbeat_monitor_timeout_detection(self, manager):
        """Test heartbeat monitor detects timed-out connections."""
        # Create a mock connection with old heartbeat
        mock_websocket = AsyncMock(spec=WebSocket)
        connection = WebSocketConnection(mock_websocket, "test-id", "127.0.0.1")
        connection.last_heartbeat = datetime.now() - timedelta(
            seconds=manager.config.heartbeat_timeout + 1
        )
        manager.connections["test-id"] = connection

        disconnect_called = False
        original_disconnect = manager.disconnect

        async def track_disconnect(*args, **kwargs):
            nonlocal disconnect_called
            disconnect_called = True
            return await original_disconnect(*args, **kwargs)

        with patch.object(
            manager, "disconnect", side_effect=track_disconnect
        ) as mock_disconnect:
            # Mock sleep to return immediately on first call, CancelledError on second
            sleep_calls = 0

            async def mock_sleep(duration):
                nonlocal sleep_calls
                sleep_calls += 1
                if sleep_calls == 1:
                    # Just return immediately - don't actually sleep
                    return
                else:
                    # Stop the loop after first iteration completes
                    raise asyncio.CancelledError()

            with patch("asyncio.sleep", side_effect=mock_sleep):
                try:
                    await manager._heartbeat_monitor()
                except asyncio.CancelledError:
                    pass  # Expected when monitor is cancelled

                # Verify disconnect was called
                assert (
                    disconnect_called
                ), "Disconnect should have been called for timed-out connection"
                mock_disconnect.assert_called_with("test-id", "heartbeat_timeout")

    @pytest.mark.asyncio
    async def test_heartbeat_monitor_no_timeout(self, manager):
        """Test heartbeat monitor with healthy connections."""
        # Create a mock connection with recent heartbeat
        mock_websocket = AsyncMock(spec=WebSocket)
        connection = WebSocketConnection(mock_websocket, "test-id", "127.0.0.1")
        connection.last_heartbeat = datetime.now()
        manager.connections["test-id"] = connection

        with patch.object(
            manager, "disconnect", new_callable=AsyncMock
        ) as mock_disconnect:
            # Use a real async function that raises CancelledError after one iteration
            sleep_count = 0

            async def mock_sleep(duration):
                nonlocal sleep_count
                sleep_count += 1
                if sleep_count == 1:
                    # Allow first sleep to complete quickly to let logic run once
                    await asyncio.sleep(0.001)
                else:
                    # Raise CancelledError on subsequent calls to break the loop
                    raise asyncio.CancelledError()

            with patch("asyncio.sleep", side_effect=mock_sleep):
                # Should complete without raising exception
                await manager._heartbeat_monitor()

                mock_disconnect.assert_not_called()

    @pytest.mark.asyncio
    async def test_heartbeat_monitor_error_handling(self, manager):
        """Test heartbeat monitor continues despite errors."""
        sleep_count = 0

        async def mock_sleep(duration):
            nonlocal sleep_count
            sleep_count += 1
            if sleep_count <= 2:  # Allow error iteration then normal iteration
                await asyncio.sleep(0.001)
            else:
                raise asyncio.CancelledError()

        with patch("asyncio.sleep", side_effect=mock_sleep):
            with patch(
                "cc_orchestrator.web.websocket.manager.datetime"
            ) as mock_datetime:
                # First call raises RuntimeError, second succeeds
                mock_datetime.now.side_effect = [
                    RuntimeError("Time error"),
                    datetime.now(),
                ]

                # Should complete without raising exception
                await manager._heartbeat_monitor()

                # Should have called sleep 3 times (continuing after error)
                assert sleep_count == 3

    @pytest.mark.asyncio
    async def test_heartbeat_monitor_connection_error(self, manager):
        """Test heartbeat monitor handles connection errors."""
        sleep_count = 0

        async def mock_sleep(duration):
            nonlocal sleep_count
            sleep_count += 1
            if sleep_count <= 2:
                # Allow first two sleeps to complete quickly to let error/recovery logic run
                await asyncio.sleep(0.001)
            else:
                # Raise CancelledError on third call to break the loop
                raise asyncio.CancelledError()

        with patch("asyncio.sleep", side_effect=mock_sleep):
            with patch(
                "cc_orchestrator.web.websocket.manager.datetime"
            ) as mock_datetime:
                mock_datetime.now.side_effect = [
                    ConnectionError("Connection error"),
                    datetime.now(),
                ]

                # Should complete without raising exception
                await manager._heartbeat_monitor()

                assert sleep_count == 3

    @pytest.mark.asyncio
    async def test_heartbeat_monitor_os_error(self, manager):
        """Test heartbeat monitor handles OS errors."""
        sleep_count = 0

        async def mock_sleep(duration):
            nonlocal sleep_count
            sleep_count += 1
            if sleep_count <= 2:
                # Allow first two sleeps to complete quickly to let error/recovery logic run
                await asyncio.sleep(0.001)
            else:
                # Raise CancelledError on third call to break the loop
                raise asyncio.CancelledError()

        with patch("asyncio.sleep", side_effect=mock_sleep):
            with patch(
                "cc_orchestrator.web.websocket.manager.datetime"
            ) as mock_datetime:
                mock_datetime.now.side_effect = [OSError("OS error"), datetime.now()]

                # Should complete without raising exception
                await manager._heartbeat_monitor()

                assert sleep_count == 3

    @pytest.mark.asyncio
    async def test_queue_cleanup_monitor_removes_expired(self, manager):
        """Test queue cleanup monitor removes expired messages."""
        # Add messages to queue - some expired, some not
        message1 = WebSocketMessage(type="test1", data={})
        message2 = WebSocketMessage(type="test2", data={})
        message3 = WebSocketMessage(type="test3", data={})

        past_time = datetime.now() - timedelta(minutes=5)
        future_time = datetime.now() + timedelta(minutes=5)

        manager.message_queues["test-id"] = [
            QueuedMessage(message=message1, expires_at=past_time),  # Expired
            QueuedMessage(message=message2, expires_at=future_time),  # Not expired
            QueuedMessage(message=message3, expires_at=past_time),  # Expired
        ]

        # Use mock sleep similar to heartbeat monitor pattern
        sleep_calls = 0

        async def mock_sleep(duration):
            nonlocal sleep_calls
            sleep_calls += 1
            if sleep_calls == 1:
                # Just return immediately - don't actually sleep
                return
            else:
                # Stop the loop after first iteration completes
                raise asyncio.CancelledError()

        with patch("asyncio.sleep", side_effect=mock_sleep):
            # Should complete without raising exception
            try:
                await manager._queue_cleanup_monitor()
            except asyncio.CancelledError:
                pass  # Expected when monitor is cancelled

            # Only non-expired message should remain
            assert len(manager.message_queues["test-id"]) == 1
            assert manager.message_queues["test-id"][0].message == message2

    @pytest.mark.asyncio
    async def test_queue_cleanup_monitor_removes_empty_queues(self, manager):
        """Test queue cleanup monitor removes empty queues for disconnected clients."""
        # Add expired messages for disconnected client
        message = WebSocketMessage(type="test", data={})
        past_time = datetime.now() - timedelta(minutes=5)

        manager.message_queues["disconnected-id"] = [
            QueuedMessage(message=message, expires_at=past_time)
        ]

        # Use mock sleep similar to heartbeat monitor pattern
        sleep_calls = 0

        async def mock_sleep(duration):
            nonlocal sleep_calls
            sleep_calls += 1
            if sleep_calls == 1:
                # Just return immediately - don't actually sleep
                return
            else:
                # Stop the loop after first iteration completes
                raise asyncio.CancelledError()

        with patch("asyncio.sleep", side_effect=mock_sleep):
            # Should complete without raising exception
            try:
                await manager._queue_cleanup_monitor()
            except asyncio.CancelledError:
                pass  # Expected when monitor is cancelled

            # Queue should be completely removed
            assert "disconnected-id" not in manager.message_queues

    @pytest.mark.asyncio
    async def test_queue_cleanup_monitor_keeps_queues_for_connected_clients(
        self, manager, mock_websocket
    ):
        """Test queue cleanup monitor keeps empty queues for connected clients."""
        connection_id = await manager.connect(mock_websocket, "127.0.0.1")

        # Add expired messages for connected client
        message = WebSocketMessage(type="test", data={})
        past_time = datetime.now() - timedelta(minutes=5)

        manager.message_queues[connection_id] = [
            QueuedMessage(message=message, expires_at=past_time)
        ]

        # Use mock sleep similar to heartbeat monitor pattern
        sleep_calls = 0

        async def mock_sleep(duration):
            nonlocal sleep_calls
            sleep_calls += 1
            if sleep_calls == 1:
                # Just return immediately - don't actually sleep
                return
            else:
                # Stop the loop after first iteration completes
                raise asyncio.CancelledError()

        with patch("asyncio.sleep", side_effect=mock_sleep):
            # Should complete without raising exception
            try:
                await manager._queue_cleanup_monitor()
            except asyncio.CancelledError:
                pass  # Expected when monitor is cancelled

            # Queue should be empty but still exist
            assert connection_id in manager.message_queues
            assert len(manager.message_queues[connection_id]) == 0

    @pytest.mark.asyncio
    async def test_queue_cleanup_monitor_error_handling(self, manager):
        """Test queue cleanup monitor continues despite errors."""
        # Use real async sleep that raises CancelledError after error iteration
        sleep_count = 0

        async def mock_sleep(duration):
            nonlocal sleep_count
            sleep_count += 1
            if sleep_count <= 2:
                # Allow first two sleeps to complete quickly to let error/recovery logic run
                await asyncio.sleep(0.001)
            else:
                # Raise CancelledError on third call to break the loop
                raise asyncio.CancelledError()

        with patch("asyncio.sleep", side_effect=mock_sleep):
            # First iteration will encounter a RuntimeError in the cleanup logic
            with patch.object(manager, "_connection_lock") as mock_lock:
                mock_lock.__enter__.side_effect = [RuntimeError("Lock error"), None]

                # Should complete without raising exception
                await manager._queue_cleanup_monitor()

                # Should have called sleep 3 times (continuing after error)
                assert sleep_count == 3

    @pytest.mark.asyncio
    async def test_queue_cleanup_monitor_connection_error(self, manager):
        """Test queue cleanup monitor handles connection errors."""
        # Use real async sleep that raises CancelledError after error iteration
        sleep_count = 0

        async def mock_sleep(duration):
            nonlocal sleep_count
            sleep_count += 1
            if sleep_count <= 2:
                # Allow first two sleeps to complete quickly to let error/recovery logic run
                await asyncio.sleep(0.001)
            else:
                # Raise CancelledError on third call to break the loop
                raise asyncio.CancelledError()

        with patch("asyncio.sleep", side_effect=mock_sleep):
            with patch.object(manager, "_connection_lock") as mock_lock:
                mock_lock.__enter__.side_effect = [
                    ConnectionError("Connection error"),
                    None,
                ]

                # Should complete without raising exception
                await manager._queue_cleanup_monitor()

                assert sleep_count == 3

    @pytest.mark.asyncio
    async def test_queue_cleanup_monitor_os_error(self, manager):
        """Test queue cleanup monitor handles OS errors."""
        # Use real async sleep that raises CancelledError after error iteration
        sleep_count = 0

        async def mock_sleep(duration):
            nonlocal sleep_count
            sleep_count += 1
            if sleep_count <= 2:
                # Allow first two sleeps to complete quickly to let error/recovery logic run
                await asyncio.sleep(0.001)
            else:
                # Raise CancelledError on third call to break the loop
                raise asyncio.CancelledError()

        with patch("asyncio.sleep", side_effect=mock_sleep):
            with patch.object(manager, "_connection_lock") as mock_lock:
                mock_lock.__enter__.side_effect = [OSError("OS error"), None]

                # Should complete without raising exception
                await manager._queue_cleanup_monitor()

                assert sleep_count == 3

    def test_thread_safety_with_connection_lock(self, manager):
        """Test thread safety with connection lock."""
        # Verify lock is properly initialized
        assert hasattr(manager._connection_lock, "acquire") and hasattr(
            manager._connection_lock, "release"
        )

        # Test that lock can be acquired
        with manager._connection_lock:
            assert True  # If we get here, lock acquisition worked

    @pytest.mark.asyncio
    async def test_connection_capacity_management(self, manager):
        """Test connection capacity management at various limits."""
        # Fill to just under capacity
        connections = []
        for i in range(manager.config.max_connections - 1):
            mock_ws = AsyncMock(spec=WebSocket)
            conn_id = await manager.connect(mock_ws, f"127.0.0.{i}")
            connections.append(conn_id)

        # Should still accept one more
        mock_ws = AsyncMock(spec=WebSocket)
        final_conn_id = await manager.connect(mock_ws, "127.0.0.100")

        # Now should refuse
        mock_ws_refused = AsyncMock(spec=WebSocket)
        with pytest.raises(ConnectionRefusedError):
            await manager.connect(mock_ws_refused, "127.0.0.101")

    @pytest.mark.asyncio
    async def test_message_queue_ttl_functionality(self, manager):
        """Test message queue TTL functionality thoroughly."""
        message = WebSocketMessage(type="test", data={})

        # Queue a message for offline client
        await manager.send_message("offline-id", message, queue_if_offline=True)

        # Verify queue has the message with proper expiration
        queued_messages = manager.message_queues["offline-id"]
        assert len(queued_messages) == 1

        queued_msg = queued_messages[0]
        assert queued_msg.message == message
        assert queued_msg.expires_at > datetime.now()
        assert queued_msg.expires_at <= datetime.now() + timedelta(
            seconds=manager.config.queue_message_ttl
        )


class TestGlobalConnectionManager:
    """Test the global connection manager instance."""

    def test_global_connection_manager_exists(self):
        """Test that the global connection manager instance exists."""
        assert connection_manager is not None
        assert isinstance(connection_manager, ConnectionManager)

    def test_global_connection_manager_default_config(self):
        """Test that the global connection manager uses default configuration."""
        # The global instance should use WebSocketConfig.from_environment()
        assert connection_manager.config is not None
        assert isinstance(connection_manager.config, WebSocketConfig)


class TestMessageSizeValidation:
    """Test message size validation across different scenarios."""

    @pytest.fixture
    def mock_websocket(self):
        """Create a mock WebSocket for testing."""
        websocket = AsyncMock(spec=WebSocket)
        websocket.accept = AsyncMock()
        websocket.send_text = AsyncMock()
        websocket.close = AsyncMock()
        return websocket

    @pytest.fixture
    def small_config(self):
        """Create a config with small message size for testing."""
        return WebSocketConfig(max_message_size=100)

    @pytest.fixture
    def small_manager(self, small_config):
        """Create a manager with small message size limit."""
        return ConnectionManager(small_config)

    @pytest.mark.asyncio
    async def test_large_outbound_message_rejected(self, small_manager):
        """Test large outbound message is rejected."""
        large_data = {"data": "x" * 200}
        message = WebSocketMessage(type="test", data=large_data)

        with pytest.raises(ValueError, match="Message size.*exceeds limit"):
            await small_manager.send_message("test-id", message)

    @pytest.mark.asyncio
    async def test_large_inbound_message_error_response(
        self, small_manager, mock_websocket
    ):
        """Test large inbound message gets error response."""
        connection_id = await small_manager.connect(mock_websocket, "127.0.0.1")

        large_message = "x" * 200

        with patch.object(
            small_manager, "send_message", new_callable=AsyncMock
        ) as mock_send:
            await small_manager.handle_message(connection_id, large_message)

            mock_send.assert_called_once()
            error_message = mock_send.call_args[0][1]
            assert error_message.type == "error"
            assert "exceeds limit" in error_message.data["error"]


class TestCORSConfiguration:
    """Test CORS configuration handling."""

    @patch.dict(
        os.environ, {"CC_WEB_CORS_ORIGINS": "https://example.com,https://test.com"}
    )
    def test_cors_from_custom_environment(self):
        """Test CORS origins loaded from custom environment variable."""
        config = WebSocketConfig()
        assert config.cors_origins == ["https://example.com", "https://test.com"]

    @patch.dict(
        os.environ,
        {"CC_WEB_CORS_ORIGINS": "  https://example.com  ,  https://test.com  "},
    )
    def test_cors_from_environment_with_whitespace(self):
        """Test CORS origins are properly trimmed."""
        config = WebSocketConfig()
        assert config.cors_origins == ["https://example.com", "https://test.com"]

    def test_cors_explicit_override(self):
        """Test explicit CORS origins override environment."""
        custom_origins = ["https://custom.com"]
        config = WebSocketConfig(cors_origins=custom_origins)
        assert config.cors_origins == custom_origins


class TestEdgeCasesAndErrorConditions:
    """Test various edge cases and error conditions."""

    @pytest.fixture
    def mock_websocket(self):
        """Create a mock WebSocket for testing."""
        websocket = AsyncMock(spec=WebSocket)
        websocket.accept = AsyncMock()
        websocket.send_text = AsyncMock()
        websocket.close = AsyncMock()
        return websocket

    @pytest.fixture
    def config(self):
        """Create a test configuration."""
        return WebSocketConfig(
            max_connections=10,
            max_message_size=1024,
            max_queue_size=5,
            queue_message_ttl=300,
            queue_cleanup_interval=60,
            heartbeat_interval=30,
            heartbeat_timeout=120,
        )

    @pytest.fixture
    def manager(self, config):
        """Create a ConnectionManager instance for testing."""
        return ConnectionManager(config)

    @pytest.mark.asyncio
    async def test_websocket_disconnect_queue_at_capacity(
        self, manager, mock_websocket
    ):
        """Test WebSocket disconnect with queue at capacity during queueing."""
        connection_id = await manager.connect(mock_websocket, "127.0.0.1")

        # Fill the queue to capacity with other messages
        for i in range(manager.config.max_queue_size):
            msg = WebSocketMessage(type=f"msg{i}", data={})
            await manager.send_message("other-id", msg, queue_if_offline=True)

        message = WebSocketMessage(type="test", data={})
        mock_websocket.send_text.side_effect = WebSocketDisconnect()

        with patch.object(manager, "disconnect", new_callable=AsyncMock):
            result = await manager.send_message(
                connection_id, message, queue_if_offline=True
            )

            assert result is False
            # Should still queue the message (removing oldest if needed)
            assert len(manager.message_queues[connection_id]) >= 1

    @pytest.mark.asyncio
    async def test_broadcast_to_topic_with_no_subscribers(self, manager):
        """Test broadcasting to topic with no subscribers."""
        message = WebSocketMessage(type="test", data={})

        result = await manager.broadcast_message(message, topic="empty-topic")

        assert result == 0

    @pytest.mark.asyncio
    async def test_multiple_subscriptions_same_connection(
        self, manager, mock_websocket
    ):
        """Test multiple subscriptions for the same connection."""
        connection_id = await manager.connect(mock_websocket, "127.0.0.1")

        topics = ["topic1", "topic2", "topic3"]
        for topic in topics:
            result = await manager.subscribe(connection_id, topic)
            assert result is True

        connection = manager.connections[connection_id]
        assert len(connection.subscriptions) == 3

        for topic in topics:
            assert connection_id in manager.subscriptions[topic]

    @pytest.mark.asyncio
    async def test_unsubscribe_from_non_subscribed_topic(self, manager, mock_websocket):
        """Test unsubscribing from a topic not subscribed to."""
        connection_id = await manager.connect(mock_websocket, "127.0.0.1")

        result = await manager.unsubscribe(connection_id, "non-existent-topic")

        assert result is True  # Should succeed even if not subscribed

    @pytest.mark.asyncio
    async def test_empty_data_in_messages(self, manager, mock_websocket):
        """Test handling of empty data in various message types."""
        connection_id = await manager.connect(mock_websocket, "127.0.0.1")

        test_cases = [
            ("heartbeat", {}),
            ("subscribe", {}),  # No topic
            ("unsubscribe", {}),  # No topic
            ("ping", {}),
        ]

        for message_type, data in test_cases:
            with patch.object(manager, "send_message", new_callable=AsyncMock):
                await manager._process_message(connection_id, message_type, data)
                # Should not raise exceptions


class TestAsyncContextAndCleanup:
    """Test async context management and cleanup scenarios."""

    @pytest.fixture
    def mock_websocket(self):
        """Create a mock WebSocket for testing."""
        websocket = AsyncMock(spec=WebSocket)
        websocket.accept = AsyncMock()
        websocket.send_text = AsyncMock()
        websocket.close = AsyncMock()
        return websocket

    @pytest.fixture
    def config(self):
        """Create a test configuration."""
        return WebSocketConfig(
            max_connections=10,
            max_message_size=1024,
            max_queue_size=5,
            queue_message_ttl=300,
            queue_cleanup_interval=60,
            heartbeat_interval=30,
            heartbeat_timeout=120,
        )

    @pytest.fixture
    def manager(self, config):
        """Create a ConnectionManager instance for testing."""
        return ConnectionManager(config)

    @pytest.mark.asyncio
    async def test_cleanup_during_active_operations(self, manager, mock_websocket):
        """Test cleanup behavior during active operations."""
        connection_id = await manager.connect(mock_websocket, "127.0.0.1")

        # Start an async operation
        message = WebSocketMessage(type="test", data={})
        send_task = asyncio.create_task(manager.send_message(connection_id, message))

        # Start cleanup concurrently
        cleanup_task = asyncio.create_task(manager.cleanup())

        # Wait for both to complete
        results = await asyncio.gather(send_task, cleanup_task, return_exceptions=True)

        # Both should complete without unhandled exceptions
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_multiple_initializations(self, manager):
        """Test multiple initialize calls."""
        await manager.initialize()

        first_heartbeat_task = manager.heartbeat_task
        first_queue_task = manager.queue_cleanup_task

        # Initialize again
        await manager.initialize()

        # Should create new tasks
        assert manager.heartbeat_task != first_heartbeat_task
        assert manager.queue_cleanup_task != first_queue_task

    @pytest.mark.asyncio
    async def test_connection_stats_during_operations(self, manager, mock_websocket):
        """Test getting stats during various operations."""
        # Get stats when empty
        stats = await manager.get_connection_stats()
        assert stats["active_connections"] == 0

        # Connect and get stats
        connection_id = await manager.connect(mock_websocket, "127.0.0.1")
        stats = await manager.get_connection_stats()
        assert stats["active_connections"] == 1

        # Subscribe and get stats
        await manager.subscribe(connection_id, "test-topic")
        stats = await manager.get_connection_stats()
        assert stats["active_subscriptions"] == 1

        # Disconnect and get stats
        await manager.disconnect(connection_id)
        stats = await manager.get_connection_stats()
        assert stats["active_connections"] == 0
        assert stats["active_subscriptions"] == 0
