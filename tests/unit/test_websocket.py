"""Tests for WebSocket functionality."""

import json
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import WebSocket, WebSocketDisconnect

from cc_orchestrator.web.dependencies import CurrentUser


@pytest.fixture
def mock_websocket():
    """Create mock WebSocket for testing."""
    websocket = Mock(spec=WebSocket)
    websocket.client = Mock()
    websocket.client.host = "127.0.0.1"
    websocket.receive_text = AsyncMock()
    websocket.send_text = AsyncMock()
    websocket.accept = AsyncMock()
    websocket.close = AsyncMock()
    return websocket


@pytest.fixture
def mock_connection_manager():
    """Create mock connection manager with proper async methods."""
    mock_manager = Mock()
    mock_manager.connect = AsyncMock(return_value="test-connection-id")
    mock_manager.send_message = AsyncMock(return_value=True)
    mock_manager.disconnect = AsyncMock()
    mock_manager.subscribe = AsyncMock(return_value=True)
    mock_manager.unsubscribe = AsyncMock(return_value=True)
    mock_manager.handle_message = AsyncMock()
    mock_manager.broadcast_message = AsyncMock(return_value=1)
    return mock_manager


class TestWebSocketAuthentication:
    """Test WebSocket authentication."""

    @pytest.mark.asyncio
    @patch("cc_orchestrator.web.websocket.router.rate_limiter")
    @patch("cc_orchestrator.web.websocket.router.authenticate_websocket_token")
    @patch("cc_orchestrator.web.websocket.router.connection_manager")
    async def test_websocket_auth_success(
        self, mock_manager, mock_auth, mock_rate_limiter, mock_websocket
    ):
        """Test successful WebSocket authentication."""
        # Setup successful authentication
        mock_auth.return_value = CurrentUser(
            user_id="test_user", permissions=["read", "write"]
        )
        mock_rate_limiter.check_websocket_rate_limit.return_value = True
        mock_manager.connect = AsyncMock(return_value="test-connection-id")
        mock_manager.handle_message = AsyncMock()
        mock_manager.disconnect = AsyncMock()

        # Setup websocket to receive one message then disconnect
        mock_websocket.receive_text.side_effect = [
            '{"type": "ping"}',
            WebSocketDisconnect(),
        ]

        from cc_orchestrator.web.websocket.router import websocket_endpoint

        # Execute
        await websocket_endpoint(mock_websocket, token="development-token")

        # Verify authentication flow
        mock_auth.assert_called_once_with("development-token")
        mock_rate_limiter.check_websocket_rate_limit.assert_called_once_with(
            "127.0.0.1"
        )
        mock_manager.connect.assert_called_once_with(mock_websocket, "127.0.0.1")
        mock_manager.handle_message.assert_called_once_with(
            "test-connection-id", '{"type": "ping"}'
        )

    @pytest.mark.asyncio
    @patch("cc_orchestrator.web.websocket.router.authenticate_websocket_token")
    async def test_websocket_auth_missing_token(self, mock_auth, mock_websocket):
        """Test WebSocket authentication without token."""
        # Setup failed authentication (None return means no token or invalid)
        mock_auth.return_value = None

        from cc_orchestrator.web.websocket.router import websocket_endpoint

        # Execute
        await websocket_endpoint(mock_websocket, token=None)

        # Verify connection was closed due to auth failure
        mock_websocket.close.assert_called_once_with(
            code=1008, reason="Authentication required"
        )

    @pytest.mark.asyncio
    @patch("cc_orchestrator.web.websocket.router.authenticate_websocket_token")
    async def test_websocket_auth_invalid_token(self, mock_auth, mock_websocket):
        """Test WebSocket authentication with invalid token."""
        # Setup failed authentication
        mock_auth.return_value = None

        from cc_orchestrator.web.websocket.router import websocket_endpoint

        # Execute
        await websocket_endpoint(mock_websocket, token="invalid-token")

        # Verify authentication was attempted and connection was closed
        mock_auth.assert_called_once_with("invalid-token")
        mock_websocket.close.assert_called_once_with(
            code=1008, reason="Authentication required"
        )

    @pytest.mark.asyncio
    @patch("cc_orchestrator.web.websocket.router.rate_limiter")
    @patch("cc_orchestrator.web.websocket.router.authenticate_websocket_token")
    @patch("cc_orchestrator.web.websocket.router.connection_manager")
    async def test_websocket_auth_wrong_message_type(
        self, mock_manager, mock_auth, mock_rate_limiter, mock_websocket
    ):
        """Test WebSocket with proper authentication but invalid message handling."""
        # Setup successful authentication
        mock_auth.return_value = CurrentUser(
            user_id="test_user", permissions=["read", "write"]
        )
        mock_rate_limiter.check_websocket_rate_limit.return_value = True
        mock_manager.connect = AsyncMock(return_value="test-connection-id")
        mock_manager.handle_message = AsyncMock(
            side_effect=Exception("Invalid message type")
        )
        mock_manager.disconnect = AsyncMock()

        # Setup websocket to receive one invalid message
        mock_websocket.receive_text.side_effect = ['{"type": "invalid_type"}']

        from cc_orchestrator.web.websocket.router import websocket_endpoint

        # Execute
        await websocket_endpoint(mock_websocket, token="development-token")

        # Verify error handling
        mock_manager.handle_message.assert_called_once_with(
            "test-connection-id", '{"type": "invalid_type"}'
        )
        mock_manager.disconnect.assert_called_once_with(
            "test-connection-id", "error: Invalid message type"
        )


class TestWebSocketMessaging:
    """Test WebSocket message handling."""

    @pytest.mark.asyncio
    @patch("cc_orchestrator.web.websocket.router.rate_limiter")
    @patch("cc_orchestrator.web.websocket.router.authenticate_websocket_token")
    @patch("cc_orchestrator.web.websocket.router.connection_manager")
    async def test_ping_pong(
        self, mock_manager, mock_auth, mock_rate_limiter, mock_websocket
    ):
        """Test ping-pong message handling."""
        # Setup successful authentication and rate limiting
        mock_auth.return_value = CurrentUser(
            user_id="test_user", permissions=["read", "write"]
        )
        mock_rate_limiter.check_websocket_rate_limit.return_value = True
        mock_manager.connect = AsyncMock(return_value="test-connection-id")
        mock_manager.handle_message = AsyncMock()
        mock_manager.disconnect = AsyncMock()

        # Setup websocket to receive ping message then disconnect
        ping_message = {"type": "ping", "data": {"test": "value"}}
        mock_websocket.receive_text.side_effect = [
            json.dumps(ping_message),
            WebSocketDisconnect(),
        ]

        from cc_orchestrator.web.websocket.router import websocket_endpoint

        # Execute
        await websocket_endpoint(mock_websocket, token="development-token")

        # Verify message handling
        mock_manager.handle_message.assert_called_once_with(
            "test-connection-id", json.dumps(ping_message)
        )

    @pytest.mark.asyncio
    @patch("cc_orchestrator.web.websocket.router.rate_limiter")
    @patch("cc_orchestrator.web.websocket.router.authenticate_websocket_token")
    @patch("cc_orchestrator.web.websocket.router.connection_manager")
    async def test_subscription_handling(
        self, mock_manager, mock_auth, mock_rate_limiter, mock_websocket
    ):
        """Test subscription message handling."""
        # Setup successful authentication and rate limiting
        mock_auth.return_value = CurrentUser(
            user_id="test_user", permissions=["read", "write"]
        )
        mock_rate_limiter.check_websocket_rate_limit.return_value = True
        mock_manager.connect = AsyncMock(return_value="test-connection-id")
        mock_manager.handle_message = AsyncMock()
        mock_manager.disconnect = AsyncMock()

        # Setup websocket to receive subscription message then disconnect
        sub_message = {"type": "subscribe", "topic": "instance_status"}
        mock_websocket.receive_text.side_effect = [
            json.dumps(sub_message),
            WebSocketDisconnect(),
        ]

        from cc_orchestrator.web.websocket.router import websocket_endpoint

        # Execute
        await websocket_endpoint(mock_websocket, token="development-token")

        # Verify subscription handling
        mock_manager.handle_message.assert_called_once_with(
            "test-connection-id", json.dumps(sub_message)
        )

    @pytest.mark.asyncio
    @patch("cc_orchestrator.web.websocket.router.rate_limiter")
    @patch("cc_orchestrator.web.websocket.router.authenticate_websocket_token")
    @patch("cc_orchestrator.web.websocket.router.connection_manager")
    async def test_unsubscription_handling(
        self, mock_manager, mock_auth, mock_rate_limiter, mock_websocket
    ):
        """Test unsubscription message handling."""
        # Setup successful authentication and rate limiting
        mock_auth.return_value = CurrentUser(
            user_id="test_user", permissions=["read", "write"]
        )
        mock_rate_limiter.check_websocket_rate_limit.return_value = True
        mock_manager.connect = AsyncMock(return_value="test-connection-id")
        mock_manager.handle_message = AsyncMock()
        mock_manager.disconnect = AsyncMock()

        # Setup websocket to receive unsubscription message then disconnect
        unsub_message = {"type": "unsubscribe", "topic": "instance_status"}
        mock_websocket.receive_text.side_effect = [
            json.dumps(unsub_message),
            WebSocketDisconnect(),
        ]

        from cc_orchestrator.web.websocket.router import websocket_endpoint

        # Execute
        await websocket_endpoint(mock_websocket, token="development-token")

        # Verify unsubscription handling
        mock_manager.handle_message.assert_called_once_with(
            "test-connection-id", json.dumps(unsub_message)
        )

    @pytest.mark.asyncio
    @patch("cc_orchestrator.web.websocket.router.rate_limiter")
    @patch("cc_orchestrator.web.websocket.router.authenticate_websocket_token")
    @patch("cc_orchestrator.web.websocket.router.connection_manager")
    async def test_unknown_message_type(
        self, mock_manager, mock_auth, mock_rate_limiter, mock_websocket
    ):
        """Test handling of unknown message types."""
        # Setup successful authentication and rate limiting
        mock_auth.return_value = CurrentUser(
            user_id="test_user", permissions=["read", "write"]
        )
        mock_rate_limiter.check_websocket_rate_limit.return_value = True
        mock_manager.connect = AsyncMock(return_value="test-connection-id")
        mock_manager.handle_message = AsyncMock()
        mock_manager.disconnect = AsyncMock()

        # Setup websocket to receive unknown message then disconnect
        unknown_message = {"type": "unknown_type"}
        mock_websocket.receive_text.side_effect = [
            json.dumps(unknown_message),
            WebSocketDisconnect(),
        ]

        from cc_orchestrator.web.websocket.router import websocket_endpoint

        # Execute
        await websocket_endpoint(mock_websocket, token="development-token")

        # Verify unknown message handling
        mock_manager.handle_message.assert_called_once_with(
            "test-connection-id", json.dumps(unknown_message)
        )

    @pytest.mark.asyncio
    @patch("cc_orchestrator.web.websocket.router.rate_limiter")
    @patch("cc_orchestrator.web.websocket.router.authenticate_websocket_token")
    @patch("cc_orchestrator.web.websocket.router.connection_manager")
    async def test_invalid_json_handling(
        self, mock_manager, mock_auth, mock_rate_limiter, mock_websocket
    ):
        """Test handling of invalid JSON messages."""
        # Setup successful authentication and rate limiting
        mock_auth.return_value = CurrentUser(
            user_id="test_user", permissions=["read", "write"]
        )
        mock_rate_limiter.check_websocket_rate_limit.return_value = True
        mock_manager.connect = AsyncMock(return_value="test-connection-id")
        mock_manager.handle_message = AsyncMock()
        mock_manager.disconnect = AsyncMock()

        # Setup websocket to receive invalid JSON then disconnect
        mock_websocket.receive_text.side_effect = [
            "invalid json content",
            WebSocketDisconnect(),
        ]

        from cc_orchestrator.web.websocket.router import websocket_endpoint

        # Execute
        await websocket_endpoint(mock_websocket, token="development-token")

        # Verify invalid JSON handling
        mock_manager.handle_message.assert_called_once_with(
            "test-connection-id", "invalid json content"
        )


class TestWebSocketManager:
    """Test WebSocket manager functionality."""

    @pytest.fixture
    def connection_manager(self):
        """Create connection manager instance."""
        from cc_orchestrator.web.websocket.manager import ConnectionManager

        return ConnectionManager()

    def test_connection_management(self, connection_manager):
        """Test WebSocket connection management."""
        # Test that the connection manager exists and has expected attributes
        assert hasattr(connection_manager, "connections")
        assert hasattr(connection_manager, "subscriptions")
        assert hasattr(connection_manager, "config")

        # Test that initial state is empty
        assert len(connection_manager.connections) == 0
        assert len(connection_manager.subscriptions) == 0

    def test_subscription_management(self, connection_manager):
        """Test subscription management."""
        connection_id = "test-connection"
        topic = "instance_status"

        # Test subscription structure
        assert isinstance(connection_manager.subscriptions, dict)

        # Test that we can add to subscriptions manually for testing
        connection_manager.subscriptions[topic] = {connection_id}

        assert connection_id in connection_manager.subscriptions[topic]

    def test_broadcast_functionality(self, connection_manager):
        """Test broadcast to subscribers."""
        # Test that the method exists and can be called
        assert hasattr(connection_manager, "broadcast_message")
        assert callable(connection_manager.broadcast_message)
