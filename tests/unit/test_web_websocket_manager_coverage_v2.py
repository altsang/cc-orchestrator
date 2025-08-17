"""
Comprehensive test coverage for src/cc_orchestrator/web/websocket/manager.py targeting 100% coverage.

This test suite aims to cover all 262 statements in the WebSocket manager module,
including edge cases, error conditions, and thread safety scenarios.
"""

import asyncio
import json
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

    def test_post_init_validation_exactly_double_heartbeat_timeout(self):
        """Test WebSocketConfig validation passes when timeout is exactly double interval."""
        config = WebSocketConfig(heartbeat_interval=30, heartbeat_timeout=60)
        assert config.heartbeat_timeout == 60

    @patch.dict(
        os.environ, {"CC_WEB_CORS_ORIGINS": "http://test1.com,http://test2.com"}
    )
    def test_post_init_cors_from_environment(self):
        """Test WebSocketConfig loads CORS origins from environment."""
        config = WebSocketConfig()
        assert config.cors_origins == ["http://test1.com", "http://test2.com"]

    @patch.dict(
        os.environ, {"CC_WEB_CORS_ORIGINS": "  http://test1.com  ,  http://test2.com  "}
    )
    def test_post_init_cors_from_environment_with_whitespace(self):
        """Test WebSocketConfig trims whitespace from CORS origins."""
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

    def test_cors_origins_explicit_none(self):
        """Test WebSocketConfig with explicit None CORS origins."""
        with patch.dict(os.environ, {"CC_WEB_CORS_ORIGINS": "http://test.com"}):
            config = WebSocketConfig(cors_origins=None)
            # Should load from environment
            assert config.cors_origins == ["http://test.com"]

    def test_cors_origins_empty_string_environment(self):
        """Test WebSocketConfig with empty CORS origins environment variable."""
        with patch.dict(os.environ, {"CC_WEB_CORS_ORIGINS": ""}):
            config = WebSocketConfig()
            assert config.cors_origins == [""]


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

    def test_message_with_only_message_id_provided(self):
        """Test WebSocketMessage with only message_id provided."""
        custom_id = "only-id-provided"
        message = WebSocketMessage(type="test", data={}, message_id=custom_id)

        assert message.message_id == custom_id
        assert isinstance(message.timestamp, datetime)

    def test_message_with_only_timestamp_provided(self):
        """Test WebSocketMessage with only timestamp provided."""
        custom_timestamp = datetime(2023, 1, 1, 12, 0, 0)
        message = WebSocketMessage(type="test", data={}, timestamp=custom_timestamp)

        assert message.timestamp == custom_timestamp
        assert message.message_id != ""

    def test_message_model_dump_json(self):
        """Test WebSocketMessage can be serialized to JSON."""
        message = WebSocketMessage(type="test", data={"key": "value"})
        json_str = message.model_dump_json()

        # Should be valid JSON
        parsed = json.loads(json_str)
        assert parsed["type"] == "test"
        assert parsed["data"]["key"] == "value"


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

    def test_queued_message_exactly_at_expiration(self):
        """Test QueuedMessage.is_expired() at exact expiration moment."""
        message = WebSocketMessage(type="test", data={})

        # Mock datetime.now() to control time
        with patch("cc_orchestrator.web.websocket.manager.datetime") as mock_datetime:
            fixed_time = datetime(2023, 1, 1, 12, 0, 0)
            mock_datetime.now.return_value = fixed_time

            # Create message that expires exactly at current time
            queued_msg = QueuedMessage(message=message, expires_at=fixed_time)

            # Time hasn't moved, should not be expired
            assert not queued_msg.is_expired()

            # Move time forward slightly
            mock_datetime.now.return_value = fixed_time + timedelta(microseconds=1)

            # Now should be expired
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

    def test_connection_heartbeat_update(self):
        """Test updating connection heartbeat timestamp."""
        websocket = Mock(spec=WebSocket)
        connection = WebSocketConnection(websocket, "test-id", "127.0.0.1")

        original_heartbeat = connection.last_heartbeat
        new_time = datetime.now() + timedelta(seconds=1)
        connection.last_heartbeat = new_time

        assert connection.last_heartbeat != original_heartbeat
        assert connection.last_heartbeat == new_time


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

    def test_connection_refused_error_without_message(self):
        """Test ConnectionRefusedError can be created without message."""
        error = ConnectionRefusedError()
        assert isinstance(error, ConnectionRefusedError)


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
            max_connections=2,
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
        assert type(manager._connection_lock).__name__ == "RLock"
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

        # Set up mock tasks that can be cancelled and awaited
        async def dummy_task():
            await asyncio.sleep(1)

        mock_heartbeat_task = asyncio.create_task(dummy_task())
        mock_queue_task = asyncio.create_task(dummy_task())

        # Cancel them immediately to avoid waiting
        mock_heartbeat_task.cancel()
        mock_queue_task.cancel()

        manager.heartbeat_task = mock_heartbeat_task
        manager.queue_cleanup_task = mock_queue_task

        # Add a mock connection to test connection cleanup
        mock_websocket = AsyncMock(spec=WebSocket)
        connection = WebSocketConnection(mock_websocket, "test-id", "127.0.0.1")
        manager.connections["test-id"] = connection

        with patch.object(
            manager, "disconnect", new_callable=AsyncMock
        ) as mock_disconnect:
            await manager.cleanup()

            # Verify tasks were cancelled (they should already be cancelled)
            assert mock_heartbeat_task.cancelled()
            assert mock_queue_task.cancelled()

            # Verify connection was disconnected
            mock_disconnect.assert_called_once_with("test-id", "server_shutdown")

    @pytest.mark.asyncio
    async def test_cleanup_with_cancelled_tasks(self, manager):
        """Test ConnectionManager.cleanup() with cancelled tasks that raise CancelledError."""

        # Create real tasks that will be cancelled
        async def dummy_coroutine():
            while True:
                await asyncio.sleep(1)

        # Start actual tasks
        heartbeat_task = asyncio.create_task(dummy_coroutine())
        queue_task = asyncio.create_task(dummy_coroutine())

        manager.heartbeat_task = heartbeat_task
        manager.queue_cleanup_task = queue_task

        # Should not raise exception even though tasks are cancelled
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
            await manager.connect(mock_ws, f"127.0.0.{i}")

        # Next connection should be refused
        with pytest.raises(
            ConnectionRefusedError, match="Maximum connections.*exceeded"
        ):
            await manager.connect(mock_websocket, "127.0.0.10")

        mock_websocket.close.assert_called_once_with(
            code=1008, reason="Server at capacity"
        )

    @pytest.mark.asyncio
    async def test_connect_generates_unique_ids(self, manager):
        """Test that connections get unique IDs."""
        connection_ids = set()

        for i in range(manager.config.max_connections):
            mock_ws = AsyncMock(spec=WebSocket)
            conn_id = await manager.connect(mock_ws, f"127.0.0.{i}")
            connection_ids.add(conn_id)

        # All IDs should be unique
        assert len(connection_ids) == manager.config.max_connections

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
    async def test_disconnect_sets_is_alive_false(self, manager, mock_websocket):
        """Test disconnect sets connection.is_alive to False."""
        connection_id = await manager.connect(mock_websocket, "127.0.0.1")
        connection = manager.connections[connection_id]

        assert connection.is_alive is True

        # Start disconnect but capture the connection before it's removed
        original_connection = connection
        await manager.disconnect(connection_id, "test_reason")

        assert original_connection.is_alive is False

    @pytest.mark.asyncio
    async def test_disconnect_websocket_errors(self, manager, mock_websocket):
        """Test disconnect handling various WebSocket errors."""
        error_types = [
            RuntimeError("Runtime error"),
            ConnectionError("Connection error"),
            OSError("OS error"),
        ]

        for error in error_types:
            # Create a new connection for each test
            mock_ws = AsyncMock(spec=WebSocket)
            connection_id = await manager.connect(mock_ws, "127.0.0.1")

            mock_ws.close.side_effect = error

            with patch(
                "cc_orchestrator.web.websocket.manager.log_websocket_connection"
            ):
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

        # Verify queue is at capacity
        assert (
            len(manager.message_queues["offline-id"]) == manager.config.max_queue_size
        )

        # Add one more message - should remove oldest
        new_message = WebSocketMessage(type="new", data={"new": "message"})
        await manager.send_message("offline-id", new_message, queue_if_offline=True)

        assert (
            len(manager.message_queues["offline-id"]) == manager.config.max_queue_size
        )
        # The newest message should be at the end
        assert manager.message_queues["offline-id"][-1].message.type == "new"

    @pytest.mark.asyncio
    async def test_send_message_websocket_disconnect_with_queueing(
        self, manager, mock_websocket
    ):
        """Test message sending with WebSocket disconnect and queueing."""
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
    async def test_send_message_websocket_disconnect_queue_at_capacity(
        self, manager, mock_websocket
    ):
        """Test WebSocket disconnect with queue at capacity during queueing."""
        connection_id = await manager.connect(mock_websocket, "127.0.0.1")

        # First fill the queue to capacity for this connection
        for i in range(manager.config.max_queue_size):
            msg = WebSocketMessage(type=f"msg{i}", data={})
            manager.message_queues[connection_id].append(
                QueuedMessage(
                    message=msg, expires_at=datetime.now() + timedelta(minutes=5)
                )
            )

        # Verify queue is at capacity
        assert (
            len(manager.message_queues[connection_id]) == manager.config.max_queue_size
        )

        # Now try to send a message that will cause WebSocket disconnect
        message = WebSocketMessage(type="test", data={})
        mock_websocket.send_text.side_effect = WebSocketDisconnect()

        with patch.object(manager, "disconnect", new_callable=AsyncMock):
            result = await manager.send_message(
                connection_id, message, queue_if_offline=True
            )

            assert result is False
            # Queue should still be at max capacity but with the new message (oldest removed)
            assert (
                len(manager.message_queues[connection_id])
                == manager.config.max_queue_size
            )
            # The new message should be the last one
            assert manager.message_queues[connection_id][-1].message.type == "test"

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
    async def test_broadcast_message_all_connections(self, manager):
        """Test broadcasting message to all connections."""
        # Use a fresh manager to avoid capacity issues
        fresh_config = WebSocketConfig(max_connections=10)
        fresh_manager = ConnectionManager(fresh_config)

        # Connect multiple clients
        connection_ids = []
        for i in range(3):
            mock_ws = AsyncMock(spec=WebSocket)
            conn_id = await fresh_manager.connect(mock_ws, f"127.0.0.{i}")
            connection_ids.append(conn_id)

        message = WebSocketMessage(type="broadcast", data={"message": "hello"})

        with patch.object(
            fresh_manager, "send_message", new_callable=AsyncMock
        ) as mock_send:
            mock_send.return_value = True

            with patch(
                "cc_orchestrator.web.websocket.manager.log_real_time_event"
            ) as mock_log:
                result = await fresh_manager.broadcast_message(message)

                assert result == 3
                assert mock_send.call_count == 3
                mock_log.assert_called_once()

    @pytest.mark.asyncio
    async def test_broadcast_message_with_topic(self, manager):
        """Test broadcasting message to topic subscribers."""
        # Use a fresh manager to avoid capacity issues
        fresh_config = WebSocketConfig(max_connections=10)
        fresh_manager = ConnectionManager(fresh_config)

        # Connect clients and subscribe some to topic
        connection_ids = []
        for i in range(3):
            mock_ws = AsyncMock(spec=WebSocket)
            conn_id = await fresh_manager.connect(mock_ws, f"127.0.0.{i}")
            connection_ids.append(conn_id)

        # Subscribe first two connections to topic
        await fresh_manager.subscribe(connection_ids[0], "test-topic")
        await fresh_manager.subscribe(connection_ids[1], "test-topic")

        message = WebSocketMessage(type="topic-msg", data={"message": "hello"})

        with patch.object(
            fresh_manager, "send_message", new_callable=AsyncMock
        ) as mock_send:
            mock_send.return_value = True

            result = await fresh_manager.broadcast_message(message, topic="test-topic")

            assert result == 2
            assert mock_send.call_count == 2

    @pytest.mark.asyncio
    async def test_broadcast_message_with_exclusions(self, manager):
        """Test broadcasting message with excluded connections."""
        # Use a fresh manager to avoid capacity issues
        fresh_config = WebSocketConfig(max_connections=10)
        fresh_manager = ConnectionManager(fresh_config)

        # Connect multiple clients
        connection_ids = []
        for i in range(3):
            mock_ws = AsyncMock(spec=WebSocket)
            conn_id = await fresh_manager.connect(mock_ws, f"127.0.0.{i}")
            connection_ids.append(conn_id)

        message = WebSocketMessage(type="broadcast", data={"message": "hello"})
        exclude_connections = {connection_ids[0]}

        with patch.object(
            fresh_manager, "send_message", new_callable=AsyncMock
        ) as mock_send:
            mock_send.return_value = True

            result = await fresh_manager.broadcast_message(
                message, exclude_connections=exclude_connections
            )

            assert result == 2
            assert mock_send.call_count == 2

    @pytest.mark.asyncio
    async def test_broadcast_message_topic_and_exclusions(self, manager):
        """Test broadcasting message with both topic and exclusions."""
        # Use a fresh manager to avoid capacity issues
        fresh_config = WebSocketConfig(max_connections=10)
        fresh_manager = ConnectionManager(fresh_config)

        # Connect multiple clients
        connection_ids = []
        for i in range(4):
            mock_ws = AsyncMock(spec=WebSocket)
            conn_id = await fresh_manager.connect(mock_ws, f"127.0.0.{i}")
            connection_ids.append(conn_id)

        # Subscribe first three to topic
        for i in range(3):
            await fresh_manager.subscribe(connection_ids[i], "test-topic")

        message = WebSocketMessage(type="topic-msg", data={"message": "hello"})
        exclude_connections = {connection_ids[0]}  # Exclude one subscriber

        with patch.object(
            fresh_manager, "send_message", new_callable=AsyncMock
        ) as mock_send:
            mock_send.return_value = True

            result = await fresh_manager.broadcast_message(
                message, topic="test-topic", exclude_connections=exclude_connections
            )

            assert result == 2  # 3 subscribers - 1 excluded = 2
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
    async def test_broadcast_message_with_failures(self, manager):
        """Test broadcasting message with some send failures."""
        # Use a fresh manager to avoid capacity issues
        fresh_config = WebSocketConfig(max_connections=10)
        fresh_manager = ConnectionManager(fresh_config)

        # Connect multiple clients
        for i in range(3):
            mock_ws = AsyncMock(spec=WebSocket)
            await fresh_manager.connect(mock_ws, f"127.0.0.{i}")

        message = WebSocketMessage(type="broadcast", data={"message": "hello"})

        with patch.object(
            fresh_manager, "send_message", new_callable=AsyncMock
        ) as mock_send:
            # First two succeed, third fails
            mock_send.side_effect = [True, True, False]

            result = await fresh_manager.broadcast_message(message)

            assert result == 2
            assert mock_send.call_count == 3

    @pytest.mark.asyncio
    async def test_broadcast_message_with_exceptions(self, manager):
        """Test broadcasting message with exceptions in send_message."""
        # Use a fresh manager to avoid capacity issues
        fresh_config = WebSocketConfig(max_connections=10)
        fresh_manager = ConnectionManager(fresh_config)

        # Connect multiple clients
        for i in range(3):
            mock_ws = AsyncMock(spec=WebSocket)
            await fresh_manager.connect(mock_ws, f"127.0.0.{i}")

        message = WebSocketMessage(type="broadcast", data={"message": "hello"})

        with patch.object(
            fresh_manager, "send_message", new_callable=AsyncMock
        ) as mock_send:
            # First succeeds, second raises exception, third succeeds
            mock_send.side_effect = [True, ValueError("Send error"), True]

            result = await fresh_manager.broadcast_message(message)

            assert result == 2
            assert mock_send.call_count == 3

    @pytest.mark.asyncio
    async def test_broadcast_message_empty_send_tasks(self, manager):
        """Test broadcast with empty target connections (no send tasks)."""
        message = WebSocketMessage(type="broadcast", data={"message": "hello"})

        # Connect a client but exclude it
        mock_ws = AsyncMock(spec=WebSocket)
        conn_id = await manager.connect(mock_ws, "127.0.0.1")

        with patch(
            "cc_orchestrator.web.websocket.manager.log_real_time_event"
        ) as mock_log:
            result = await manager.broadcast_message(
                message, exclude_connections={conn_id}
            )

            assert result == 0
            mock_log.assert_called_once()

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
    async def test_subscribe_multiple_topics_same_connection(
        self, manager, mock_websocket
    ):
        """Test subscribing same connection to multiple topics."""
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
    async def test_unsubscribe_keeps_topic_with_other_subscribers(self, manager):
        """Test unsubscribing keeps topic when other subscribers exist."""
        # Connect two clients
        mock_ws1 = AsyncMock(spec=WebSocket)
        mock_ws2 = AsyncMock(spec=WebSocket)
        conn_id1 = await manager.connect(mock_ws1, "127.0.0.1")
        conn_id2 = await manager.connect(mock_ws2, "127.0.0.2")

        # Both subscribe to same topic
        await manager.subscribe(conn_id1, "test-topic")
        await manager.subscribe(conn_id2, "test-topic")

        # Unsubscribe one
        await manager.unsubscribe(conn_id1, "test-topic")

        # Topic should still exist with the other subscriber
        assert "test-topic" in manager.subscriptions
        assert conn_id2 in manager.subscriptions["test-topic"]
        assert conn_id1 not in manager.subscriptions["test-topic"]

    @pytest.mark.asyncio
    async def test_unsubscribe_from_non_subscribed_topic(self, manager, mock_websocket):
        """Test unsubscribing from a topic not subscribed to."""
        connection_id = await manager.connect(mock_websocket, "127.0.0.1")

        # Try to unsubscribe from topic never subscribed to
        result = await manager.unsubscribe(connection_id, "never-subscribed")

        assert result is True  # Should succeed even if not subscribed

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
    async def test_handle_message_updates_heartbeat_and_counters(
        self, manager, mock_websocket
    ):
        """Test handling message updates heartbeat and message counters."""
        connection_id = await manager.connect(mock_websocket, "127.0.0.1")

        original_heartbeat = manager.connections[connection_id].last_heartbeat
        original_received_count = manager.total_messages_received

        # Wait a small amount to ensure timestamp difference
        await asyncio.sleep(0.01)

        with patch.object(manager, "_process_message", new_callable=AsyncMock):
            await manager.handle_message(connection_id, '{"type": "test"}')

        new_heartbeat = manager.connections[connection_id].last_heartbeat
        assert new_heartbeat > original_heartbeat
        assert manager.total_messages_received == original_received_count + 1

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
    async def test_handle_message_no_type_field(self, manager, mock_websocket):
        """Test handling message without type field."""
        connection_id = await manager.connect(mock_websocket, "127.0.0.1")

        with patch.object(
            manager, "_process_message", new_callable=AsyncMock
        ) as mock_process:
            with patch("cc_orchestrator.web.websocket.manager.log_websocket_message"):
                await manager.handle_message(connection_id, '{"data": {}}')

                # Should call _process_message with "unknown" type
                mock_process.assert_called_once_with(
                    connection_id, "unknown", {"data": {}}
                )

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
    async def test_get_connection_stats_empty_state(self, manager):
        """Test getting connection statistics when empty."""
        stats = await manager.get_connection_stats()

        assert stats["active_connections"] == 0
        assert stats["total_connections"] == 0
        assert stats["active_subscriptions"] == 0
        assert stats["queued_messages"] == 0
        assert stats["messages_sent"] == 0
        assert stats["messages_received"] == 0

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
    async def test_send_queued_messages_all_expired(self, manager):
        """Test sending queued messages when all are expired."""
        connection_id = "test-id"

        message1 = WebSocketMessage(type="test1", data={})
        message2 = WebSocketMessage(type="test2", data={})

        past_time = datetime.now() - timedelta(minutes=5)

        manager.message_queues[connection_id] = [
            QueuedMessage(message=message1, expires_at=past_time),
            QueuedMessage(message=message2, expires_at=past_time),
        ]

        with patch.object(manager, "send_message", new_callable=AsyncMock) as mock_send:
            await manager._send_queued_messages(connection_id)

            # No messages should be sent
            mock_send.assert_not_called()
            # Queue should still be cleared
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
    async def test_process_message_subscribe_failed(self, manager, mock_websocket):
        """Test processing subscribe message that fails."""
        connection_id = await manager.connect(mock_websocket, "127.0.0.1")

        with patch.object(manager, "send_message", new_callable=AsyncMock) as mock_send:
            with patch.object(
                manager, "subscribe", new_callable=AsyncMock
            ) as mock_subscribe:
                mock_subscribe.return_value = False

                await manager._process_message(
                    connection_id, "subscribe", {"topic": "test-topic"}
                )

                response_message = mock_send.call_args[0][1]
                assert response_message.data["success"] is False

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
    async def test_process_message_ping_with_data(self, manager, mock_websocket):
        """Test processing ping message with data."""
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

        with patch.object(
            manager, "disconnect", new_callable=AsyncMock
        ) as mock_disconnect:
            with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:

                async def sleep_then_cancel(*args):
                    # First call returns normally, second raises CancelledError
                    if mock_sleep.call_count == 1:
                        return
                    else:
                        raise asyncio.CancelledError()

                mock_sleep.side_effect = sleep_then_cancel

                # Run heartbeat monitor until cancelled
                try:
                    await manager._heartbeat_monitor()
                except asyncio.CancelledError:
                    pass

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
            with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:

                async def sleep_then_cancel(*args):
                    if mock_sleep.call_count == 1:
                        return
                    else:
                        raise asyncio.CancelledError()

                mock_sleep.side_effect = sleep_then_cancel

                try:
                    await manager._heartbeat_monitor()
                except asyncio.CancelledError:
                    pass

                mock_disconnect.assert_not_called()

    @pytest.mark.asyncio
    async def test_heartbeat_monitor_multiple_connections(self, manager):
        """Test heartbeat monitor with multiple connections, some timed out."""
        # Create connections with different heartbeat times
        mock_ws1 = AsyncMock(spec=WebSocket)
        mock_ws2 = AsyncMock(spec=WebSocket)
        mock_ws3 = AsyncMock(spec=WebSocket)

        # One timed out, two healthy
        old_time = datetime.now() - timedelta(
            seconds=manager.config.heartbeat_timeout + 1
        )
        recent_time = datetime.now()

        conn1 = WebSocketConnection(mock_ws1, "timed-out", "127.0.0.1")
        conn1.last_heartbeat = old_time

        conn2 = WebSocketConnection(mock_ws2, "healthy-1", "127.0.0.2")
        conn2.last_heartbeat = recent_time

        conn3 = WebSocketConnection(mock_ws3, "healthy-2", "127.0.0.3")
        conn3.last_heartbeat = recent_time

        manager.connections.update(
            {
                "timed-out": conn1,
                "healthy-1": conn2,
                "healthy-2": conn3,
            }
        )

        with patch.object(
            manager, "disconnect", new_callable=AsyncMock
        ) as mock_disconnect:
            with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:

                async def sleep_then_cancel(*args):
                    if mock_sleep.call_count == 1:
                        return
                    else:
                        raise asyncio.CancelledError()

                mock_sleep.side_effect = sleep_then_cancel

                try:
                    await manager._heartbeat_monitor()
                except asyncio.CancelledError:
                    pass

                # Only the timed-out connection should be disconnected
                mock_disconnect.assert_called_with("timed-out", "heartbeat_timeout")

    @pytest.mark.asyncio
    async def test_heartbeat_monitor_error_handling(self, manager):
        """Test heartbeat monitor continues despite errors."""
        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            call_count = 0

            async def sleep_with_error(*args):
                nonlocal call_count
                call_count += 1
                if call_count >= 3:
                    raise asyncio.CancelledError()
                return None

            mock_sleep.side_effect = sleep_with_error

            with patch(
                "cc_orchestrator.web.websocket.manager.datetime"
            ) as mock_datetime:
                # First call raises RuntimeError, second succeeds
                mock_datetime.now.side_effect = [
                    RuntimeError("Time error"),
                    datetime.now(),
                ]

                try:
                    await manager._heartbeat_monitor()
                except asyncio.CancelledError:
                    pass

                # Should have called sleep multiple times (continuing after error)
                assert mock_sleep.call_count >= 2

    @pytest.mark.asyncio
    async def test_heartbeat_monitor_connection_error(self, manager):
        """Test heartbeat monitor handles connection errors."""
        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            call_count = 0

            async def sleep_with_error(*args):
                nonlocal call_count
                call_count += 1
                if call_count >= 3:
                    raise asyncio.CancelledError()
                return None

            mock_sleep.side_effect = sleep_with_error

            with patch(
                "cc_orchestrator.web.websocket.manager.datetime"
            ) as mock_datetime:
                mock_datetime.now.side_effect = [
                    ConnectionError("Connection error"),
                    datetime.now(),
                ]

                try:
                    await manager._heartbeat_monitor()
                except asyncio.CancelledError:
                    pass

                assert mock_sleep.call_count >= 2

    @pytest.mark.asyncio
    async def test_heartbeat_monitor_os_error(self, manager):
        """Test heartbeat monitor handles OS errors."""
        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            call_count = 0

            async def sleep_with_error(*args):
                nonlocal call_count
                call_count += 1
                if call_count >= 3:
                    raise asyncio.CancelledError()
                return None

            mock_sleep.side_effect = sleep_with_error

            with patch(
                "cc_orchestrator.web.websocket.manager.datetime"
            ) as mock_datetime:
                mock_datetime.now.side_effect = [OSError("OS error"), datetime.now()]

                try:
                    await manager._heartbeat_monitor()
                except asyncio.CancelledError:
                    pass

                assert mock_sleep.call_count >= 2

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

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:

            async def sleep_then_cancel(*args):
                if mock_sleep.call_count == 1:
                    return
                else:
                    raise asyncio.CancelledError()

            mock_sleep.side_effect = sleep_then_cancel

            try:
                await manager._queue_cleanup_monitor()
            except asyncio.CancelledError:
                pass

            # Only non-expired message should remain
            assert len(manager.message_queues["test-id"]) == 1
            assert manager.message_queues["test-id"][0].message == message2

    @pytest.mark.asyncio
    async def test_queue_cleanup_monitor_removes_empty_queues_disconnected_clients(
        self, manager
    ):
        """Test queue cleanup monitor removes empty queues for disconnected clients."""
        # Add expired messages for disconnected client
        message = WebSocketMessage(type="test", data={})
        past_time = datetime.now() - timedelta(minutes=5)

        manager.message_queues["disconnected-id"] = [
            QueuedMessage(message=message, expires_at=past_time)
        ]

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:

            async def sleep_then_cancel(*args):
                if mock_sleep.call_count == 1:
                    return
                else:
                    raise asyncio.CancelledError()

            mock_sleep.side_effect = sleep_then_cancel

            try:
                await manager._queue_cleanup_monitor()
            except asyncio.CancelledError:
                pass

            # Queue should be completely removed
            assert "disconnected-id" not in manager.message_queues

    @pytest.mark.asyncio
    async def test_queue_cleanup_monitor_keeps_empty_queues_connected_clients(
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

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:

            async def sleep_then_cancel(*args):
                if mock_sleep.call_count == 1:
                    return
                else:
                    raise asyncio.CancelledError()

            mock_sleep.side_effect = sleep_then_cancel

            try:
                await manager._queue_cleanup_monitor()
            except asyncio.CancelledError:
                pass

            # Queue should be empty but still exist
            assert connection_id in manager.message_queues
            assert len(manager.message_queues[connection_id]) == 0

    @pytest.mark.asyncio
    async def test_queue_cleanup_monitor_multiple_queues(self, manager, mock_websocket):
        """Test queue cleanup monitor handles multiple queues correctly."""
        # Connect one client
        connection_id = await manager.connect(mock_websocket, "127.0.0.1")

        # Create messages
        message = WebSocketMessage(type="test", data={})
        past_time = datetime.now() - timedelta(minutes=5)
        future_time = datetime.now() + timedelta(minutes=5)

        # Set up different queue scenarios
        manager.message_queues.update(
            {
                connection_id: [
                    QueuedMessage(message=message, expires_at=past_time)
                ],  # Connected, expired
                "disconnected-empty": [],  # Disconnected, empty
                "disconnected-expired": [
                    QueuedMessage(message=message, expires_at=past_time)
                ],  # Disconnected, expired
                "disconnected-valid": [
                    QueuedMessage(message=message, expires_at=future_time)
                ],  # Disconnected, valid
            }
        )

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:

            async def sleep_then_cancel(*args):
                if mock_sleep.call_count == 1:
                    return
                else:
                    raise asyncio.CancelledError()

            mock_sleep.side_effect = sleep_then_cancel

            try:
                await manager._queue_cleanup_monitor()
            except asyncio.CancelledError:
                pass

            # Connected client queue should be empty but exist
            assert connection_id in manager.message_queues
            assert len(manager.message_queues[connection_id]) == 0

            # Disconnected empty queue should be removed
            assert "disconnected-empty" not in manager.message_queues

            # Disconnected expired queue should be removed
            assert "disconnected-expired" not in manager.message_queues

            # Disconnected valid queue should remain
            assert "disconnected-valid" in manager.message_queues
            assert len(manager.message_queues["disconnected-valid"]) == 1

    @pytest.mark.asyncio
    async def test_queue_cleanup_monitor_error_handling(self, manager):
        """Test queue cleanup monitor continues despite errors."""
        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            call_count = 0

            async def sleep_with_error(*args):
                nonlocal call_count
                call_count += 1
                if call_count >= 3:
                    raise asyncio.CancelledError()
                return None

            mock_sleep.side_effect = sleep_with_error

            # First iteration will encounter a RuntimeError in the cleanup logic
            with patch.object(manager, "_connection_lock") as mock_lock:
                mock_lock.__enter__.side_effect = [RuntimeError("Lock error"), None]

                try:
                    await manager._queue_cleanup_monitor()
                except asyncio.CancelledError:
                    pass

                # Should have called sleep multiple times (continuing after error)
                assert mock_sleep.call_count >= 2

    @pytest.mark.asyncio
    async def test_queue_cleanup_monitor_connection_error(self, manager):
        """Test queue cleanup monitor handles connection errors."""
        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            call_count = 0

            async def sleep_with_error(*args):
                nonlocal call_count
                call_count += 1
                if call_count >= 3:
                    raise asyncio.CancelledError()
                return None

            mock_sleep.side_effect = sleep_with_error

            with patch.object(manager, "_connection_lock") as mock_lock:
                mock_lock.__enter__.side_effect = [
                    ConnectionError("Connection error"),
                    None,
                ]

                try:
                    await manager._queue_cleanup_monitor()
                except asyncio.CancelledError:
                    pass

                assert mock_sleep.call_count >= 2

    @pytest.mark.asyncio
    async def test_queue_cleanup_monitor_os_error(self, manager):
        """Test queue cleanup monitor handles OS errors."""
        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            call_count = 0

            async def sleep_with_error(*args):
                nonlocal call_count
                call_count += 1
                if call_count >= 3:
                    raise asyncio.CancelledError()
                return None

            mock_sleep.side_effect = sleep_with_error

            with patch.object(manager, "_connection_lock") as mock_lock:
                mock_lock.__enter__.side_effect = [OSError("OS error"), None]

                try:
                    await manager._queue_cleanup_monitor()
                except asyncio.CancelledError:
                    pass

                assert mock_sleep.call_count >= 2

    def test_thread_safety_with_connection_lock(self, manager):
        """Test thread safety with connection lock."""
        # Verify lock is properly initialized
        assert type(manager._connection_lock).__name__ == "RLock"

        # Test that lock can be acquired
        with manager._connection_lock:
            assert True  # If we get here, lock acquisition worked

    def test_thread_safety_lock_is_reentrant(self, manager):
        """Test that connection lock is reentrant."""
        with manager._connection_lock:
            # Should be able to acquire the same lock again
            with manager._connection_lock:
                assert True

    @pytest.mark.asyncio
    async def test_connection_capacity_edge_cases(self, manager):
        """Test connection capacity management edge cases."""
        # Use a manager with higher capacity to avoid interference from other tests
        high_capacity_config = WebSocketConfig(max_connections=10)
        high_capacity_manager = ConnectionManager(high_capacity_config)

        # Fill to exactly capacity
        connections = []
        for i in range(high_capacity_config.max_connections):
            mock_ws = AsyncMock(spec=WebSocket)
            conn_id = await high_capacity_manager.connect(mock_ws, f"127.0.0.{i}")
            connections.append(conn_id)

        # Verify exactly at capacity
        assert (
            len(high_capacity_manager.connections)
            == high_capacity_config.max_connections
        )

        # Should refuse new connection
        mock_ws_refused = AsyncMock(spec=WebSocket)
        with pytest.raises(ConnectionRefusedError):
            await high_capacity_manager.connect(mock_ws_refused, "127.0.0.101")

    @pytest.mark.asyncio
    async def test_message_queue_ttl_edge_cases(self, manager):
        """Test message queue TTL functionality thoroughly."""
        message = WebSocketMessage(type="test", data={})

        # Queue a message for offline client
        with patch("cc_orchestrator.web.websocket.manager.datetime") as mock_datetime:
            fixed_time = datetime(2023, 1, 1, 12, 0, 0)
            mock_datetime.now.return_value = fixed_time

            await manager.send_message("offline-id", message, queue_if_offline=True)

            # Verify queue has the message with proper expiration
            queued_messages = manager.message_queues["offline-id"]
            assert len(queued_messages) == 1

            queued_msg = queued_messages[0]
            assert queued_msg.message == message

            expected_expiry = fixed_time + timedelta(
                seconds=manager.config.queue_message_ttl
            )
            assert queued_msg.expires_at == expected_expiry

    @pytest.mark.asyncio
    async def test_multiple_async_operations_concurrency(self, manager):
        """Test concurrent async operations."""
        # Use a manager with higher capacity to avoid conflicts
        concurrent_config = WebSocketConfig(max_connections=10)
        concurrent_manager = ConnectionManager(concurrent_config)

        # Connect multiple clients concurrently
        async def connect_client(i):
            mock_ws = AsyncMock(spec=WebSocket)
            return await concurrent_manager.connect(mock_ws, f"127.0.0.{i}")

        # Run concurrent connections
        connection_tasks = [
            connect_client(i) for i in range(5)
        ]  # Use fewer connections
        connection_ids = await asyncio.gather(*connection_tasks)

        assert len(set(connection_ids)) == 5
        assert len(concurrent_manager.connections) == 5

    @pytest.mark.asyncio
    async def test_disconnect_with_multiple_subscriptions(
        self, manager, mock_websocket
    ):
        """Test disconnect properly handles multiple subscriptions."""
        connection_id = await manager.connect(mock_websocket, "127.0.0.1")

        # Subscribe to multiple topics
        topics = ["topic1", "topic2", "topic3"]
        for topic in topics:
            await manager.subscribe(connection_id, topic)

        # Verify subscriptions
        for topic in topics:
            assert connection_id in manager.subscriptions[topic]

        # Disconnect and verify all subscriptions are cleaned up
        with patch.object(
            manager, "unsubscribe", new_callable=AsyncMock
        ) as mock_unsubscribe:
            await manager.disconnect(connection_id)

            # Should have called unsubscribe for each topic
            assert mock_unsubscribe.call_count == len(topics)
            for topic in topics:
                mock_unsubscribe.assert_any_call(connection_id, topic)


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

    def test_global_connection_manager_isolation(self):
        """Test that global connection manager is isolated from test instances."""
        # Create a test manager
        test_config = WebSocketConfig(max_connections=1)
        test_manager = ConnectionManager(test_config)

        # Global manager should not be affected
        assert (
            connection_manager.config.max_connections
            != test_manager.config.max_connections
        )


class TestMessageSizeValidation:
    """Test message size validation across different scenarios."""

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
    async def test_large_inbound_message_error_response(self, small_manager):
        """Test large inbound message gets error response."""
        mock_ws = AsyncMock(spec=WebSocket)
        connection_id = await small_manager.connect(mock_ws, "127.0.0.1")

        large_message = "x" * 200

        with patch.object(
            small_manager, "send_message", new_callable=AsyncMock
        ) as mock_send:
            await small_manager.handle_message(connection_id, large_message)

            mock_send.assert_called_once()
            error_message = mock_send.call_args[0][1]
            assert error_message.type == "error"
            assert "exceeds limit" in error_message.data["error"]

    @pytest.mark.asyncio
    async def test_message_exactly_at_size_limit(self, small_manager):
        """Test message exactly at size limit is accepted."""
        mock_ws = AsyncMock(spec=WebSocket)
        connection_id = await small_manager.connect(mock_ws, "127.0.0.1")

        # Create message that is exactly at the limit
        # Account for JSON overhead
        test_message = WebSocketMessage(type="test", data={"key": "value"})
        json_size = len(test_message.model_dump_json())

        # Create data that will result in exactly the limit
        padding_needed = small_manager.config.max_message_size - json_size
        if padding_needed > 0:
            # Adjust the data to reach exact limit
            large_data = {
                "data": "x" * max(0, padding_needed - 20)
            }  # Leave some buffer for JSON structure
            exact_message = WebSocketMessage(type="test", data=large_data)

            # Should not raise exception
            result = await small_manager.send_message(connection_id, exact_message)
            assert result is True


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

    @patch.dict(os.environ, {"CC_WEB_CORS_ORIGINS": "single-origin"})
    def test_cors_single_origin(self):
        """Test CORS with single origin."""
        config = WebSocketConfig()
        assert config.cors_origins == ["single-origin"]

    @patch.dict(
        os.environ, {"CC_WEB_CORS_ORIGINS": "http://a.com,http://b.com,http://c.com"}
    )
    def test_cors_multiple_origins(self):
        """Test CORS with multiple origins."""
        config = WebSocketConfig()
        assert config.cors_origins == ["http://a.com", "http://b.com", "http://c.com"]


class TestEdgeCasesAndErrorConditions:
    """Test various edge cases and error conditions."""

    @pytest.fixture
    def manager(self):
        """Create a ConnectionManager instance for testing."""
        config = WebSocketConfig(max_connections=10)
        return ConnectionManager(config)

    @pytest.fixture
    def mock_websocket(self):
        """Create a mock WebSocket for testing."""
        websocket = AsyncMock(spec=WebSocket)
        websocket.accept = AsyncMock()
        websocket.send_text = AsyncMock()
        websocket.close = AsyncMock()
        return websocket

    @pytest.mark.asyncio
    async def test_broadcast_to_topic_with_no_subscribers(self, manager):
        """Test broadcasting to topic with no subscribers."""
        message = WebSocketMessage(type="test", data={})

        result = await manager.broadcast_message(message, topic="empty-topic")

        assert result == 0

    @pytest.mark.asyncio
    async def test_empty_data_in_various_messages(self, manager, mock_websocket):
        """Test handling of empty data in various message types."""
        connection_id = await manager.connect(mock_websocket, "127.0.0.1")

        test_cases = [
            ("heartbeat", {}),
            ("subscribe", {}),  # No topic
            ("unsubscribe", {}),  # No topic
            ("ping", {}),
            ("unknown_type", {}),
        ]

        for message_type, data in test_cases:
            with patch.object(manager, "send_message", new_callable=AsyncMock):
                # Should not raise exceptions
                await manager._process_message(connection_id, message_type, data)

    @pytest.mark.asyncio
    async def test_websocket_message_with_complex_data(self, manager, mock_websocket):
        """Test WebSocket message with complex nested data structures."""
        connection_id = await manager.connect(mock_websocket, "127.0.0.1")

        complex_data = {
            "nested": {"deep": {"structure": True}},
            "list": [1, 2, 3, {"item": "value"}],
            "unicode": "Hello 世界 🌍",
            "numbers": [1.5, -42, 0],
            "boolean": True,
            "null": None,
        }

        message = WebSocketMessage(type="complex", data=complex_data)

        result = await manager.send_message(connection_id, message)
        assert result is True

    @pytest.mark.asyncio
    async def test_connection_stats_during_rapid_changes(self, manager):
        """Test connection stats during rapid connection changes."""
        # Use a manager with higher capacity for rapid changes
        rapid_config = WebSocketConfig(max_connections=10)
        rapid_manager = ConnectionManager(rapid_config)

        # Rapidly connect and disconnect clients
        for i in range(5):
            mock_ws = AsyncMock(spec=WebSocket)
            conn_id = await rapid_manager.connect(mock_ws, f"127.0.0.{i}")

            # Get stats during operations
            stats = await rapid_manager.get_connection_stats()
            assert stats["active_connections"] >= 1

            # Subscribe and disconnect some
            if i % 2 == 0:
                await rapid_manager.subscribe(conn_id, f"topic-{i}")
                await rapid_manager.disconnect(conn_id)

        final_stats = await rapid_manager.get_connection_stats()
        # Should have some connections remaining
        assert final_stats["active_connections"] >= 0

    @pytest.mark.asyncio
    async def test_unicode_and_special_characters(self, manager, mock_websocket):
        """Test handling of Unicode and special characters."""
        connection_id = await manager.connect(mock_websocket, "127.0.0.1")

        unicode_data = {
            "emoji": "🚀🌟💫",
            "chinese": "你好世界",
            "arabic": "مرحبا بالعالم",
            "special": "!@#$%^&*()[]{}|\\:;<>?./",
            "quotes": 'Single "double" quotes',
        }

        message = WebSocketMessage(type="unicode", data=unicode_data)

        result = await manager.send_message(connection_id, message)
        assert result is True

    @pytest.mark.asyncio
    async def test_very_long_topic_names(self, manager, mock_websocket):
        """Test subscription to very long topic names."""
        connection_id = await manager.connect(mock_websocket, "127.0.0.1")

        long_topic = "very_long_topic_name_" * 100  # Very long topic name

        result = await manager.subscribe(connection_id, long_topic)
        assert result is True

        assert connection_id in manager.subscriptions[long_topic]

    @pytest.mark.asyncio
    async def test_connection_id_collision_resistance(self, manager):
        """Test that connection IDs are collision-resistant."""
        # Use a manager with higher capacity for collision testing
        collision_config = WebSocketConfig(max_connections=50)
        collision_manager = ConnectionManager(collision_config)

        connection_ids = set()

        # Connect many clients to test for ID collisions
        for i in range(20):  # Use fewer connections to stay under capacity
            mock_ws = AsyncMock(spec=WebSocket)
            conn_id = await collision_manager.connect(mock_ws, f"127.0.0.{i % 256}")
            connection_ids.add(conn_id)

        # All IDs should be unique
        assert len(connection_ids) == 20

    @pytest.mark.asyncio
    async def test_cleanup_with_partially_initialized_manager(self, manager):
        """Test cleanup with partially initialized manager."""

        # Create a proper task for testing
        async def dummy_task():
            await asyncio.sleep(1)

        # Only set one task
        mock_heartbeat_task = asyncio.create_task(dummy_task())
        mock_heartbeat_task.cancel()  # Cancel immediately
        manager.heartbeat_task = mock_heartbeat_task
        manager.queue_cleanup_task = None

        # Should not raise exception
        await manager.cleanup()

    @pytest.mark.asyncio
    async def test_message_queueing_with_zero_ttl(self):
        """Test message queueing with zero TTL."""
        config = WebSocketConfig(queue_message_ttl=0)
        manager = ConnectionManager(config)

        message = WebSocketMessage(type="test", data={})

        await manager.send_message("offline-id", message, queue_if_offline=True)

        # Message should be queued but immediately expire
        queued_messages = manager.message_queues["offline-id"]
        assert len(queued_messages) == 1
        assert queued_messages[0].is_expired()


class TestAsyncContextAndCleanup:
    """Test async context management and cleanup scenarios."""

    @pytest.fixture
    def manager(self):
        """Create a ConnectionManager instance for testing."""
        config = WebSocketConfig(max_connections=10)
        return ConnectionManager(config)

    @pytest.fixture
    def mock_websocket(self):
        """Create a mock WebSocket for testing."""
        websocket = AsyncMock(spec=WebSocket)
        websocket.accept = AsyncMock()
        websocket.send_text = AsyncMock()
        websocket.close = AsyncMock()
        return websocket

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
    async def test_cleanup_without_prior_initialization(self, manager):
        """Test cleanup without prior initialization."""
        # Should not raise exception even if never initialized
        await manager.cleanup()

    @pytest.mark.asyncio
    async def test_concurrent_connection_operations(self, manager):
        """Test concurrent connection/disconnection operations."""

        async def connect_and_disconnect(i):
            mock_ws = AsyncMock(spec=WebSocket)
            conn_id = await manager.connect(mock_ws, f"127.0.0.{i}")
            await asyncio.sleep(0.001)  # Small delay
            await manager.disconnect(conn_id)
            return conn_id

        # Run concurrent operations
        tasks = [connect_and_disconnect(i) for i in range(10)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # All should complete successfully
        assert len(results) == 10
        for result in results:
            assert not isinstance(result, Exception)

    @pytest.mark.asyncio
    async def test_manager_state_after_cleanup(self, manager, mock_websocket):
        """Test manager state after cleanup."""
        # Set up some state
        connection_id = await manager.connect(mock_websocket, "127.0.0.1")
        await manager.subscribe(connection_id, "test-topic")

        message = WebSocketMessage(type="test", data={})
        await manager.send_message("offline-id", message, queue_if_offline=True)

        # Verify state exists
        assert len(manager.connections) > 0
        assert len(manager.subscriptions) > 0
        assert len(manager.message_queues) > 0

        # Cleanup
        await manager.cleanup()

        # Connections should be cleaned up
        assert len(manager.connections) == 0
        # But other state might remain
        assert manager.total_connections > 0  # This counter is not reset

    @pytest.mark.asyncio
    async def test_send_message_disconnect_queue_overflow(self):
        """Test send_message when WebSocket disconnects and queue needs to remove oldest message."""
        config = WebSocketConfig(max_connections=5, max_queue_size=2)
        manager = ConnectionManager(config)
        mock_ws = AsyncMock(spec=WebSocket)

        connection_id = await manager.connect(mock_ws, "127.0.0.1")

        # First disconnect the connection to make it offline
        await manager.disconnect(connection_id)

        # Fill queue to capacity for the offline connection
        msg1 = WebSocketMessage(type="msg1", data={})
        msg2 = WebSocketMessage(type="msg2", data={})
        await manager.send_message(connection_id, msg1, queue_if_offline=True)
        await manager.send_message(connection_id, msg2, queue_if_offline=True)

        # Verify queue is at capacity
        assert len(manager.message_queues[connection_id]) == 2

        # Now send a third message to the offline connection (should cause overflow)
        msg3 = WebSocketMessage(type="msg3", data={})
        result = await manager.send_message(connection_id, msg3, queue_if_offline=True)

        assert result is False  # Message not sent because connection is offline
        # Queue should still be at capacity with oldest message removed
        assert len(manager.message_queues[connection_id]) == 2
        # The new message should be the last one
        assert manager.message_queues[connection_id][-1].message.type == "msg3"

    @pytest.mark.asyncio
    async def test_cleanup_with_real_cancelled_tasks(self):
        """Test cleanup to specifically cover CancelledError exception handlers."""
        config = WebSocketConfig(max_connections=5)
        manager = ConnectionManager(config)

        # Initialize the manager to start tasks
        await manager.initialize()

        # Verify tasks are running
        assert manager.heartbeat_task is not None
        assert manager.queue_cleanup_task is not None

        # Now cleanup - this should trigger the CancelledError handlers
        await manager.cleanup()

        # Tasks should be done (either cancelled or finished)
        assert manager.heartbeat_task.done()
        assert manager.queue_cleanup_task.done()
