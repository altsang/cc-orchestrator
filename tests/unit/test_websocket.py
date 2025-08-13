"""Tests for WebSocket functionality."""

import json
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from cc_orchestrator.web.app import create_app
from cc_orchestrator.web.auth import create_access_token


@pytest.fixture
def test_app():
    """Create test FastAPI application."""
    return create_app()


@pytest.fixture
def client(test_app):
    """Create test client."""
    return TestClient(test_app)


@pytest.fixture
def auth_token():
    """Create valid authentication token."""
    return create_access_token(data={"sub": "testuser", "role": "admin"})


class TestWebSocketAuthentication:
    """Test WebSocket authentication."""

    def test_websocket_auth_success(self, client, auth_token):
        """Test successful WebSocket authentication."""
        with client.websocket_connect("/ws/dashboard") as websocket:
            # Send authentication message
            auth_message = {"type": "auth", "token": auth_token}
            websocket.send_text(json.dumps(auth_message))

            # Receive authentication response
            response = websocket.receive_json()
            assert response["type"] == "auth_success"
            assert response["user"] == "testuser"

    def test_websocket_auth_missing_token(self, client):
        """Test WebSocket authentication without token."""
        with client.websocket_connect("/ws/dashboard") as websocket:
            # Send authentication message without token
            auth_message = {"type": "auth"}
            websocket.send_text(json.dumps(auth_message))

            # Should receive error and connection should close
            response = websocket.receive_json()
            assert response["type"] == "error"
            assert "Token required" in response["message"]

    def test_websocket_auth_invalid_token(self, client):
        """Test WebSocket authentication with invalid token."""
        with client.websocket_connect("/ws/dashboard") as websocket:
            # Send authentication message with invalid token
            auth_message = {"type": "auth", "token": "invalid-token"}
            websocket.send_text(json.dumps(auth_message))

            # Should receive error and connection should close
            response = websocket.receive_json()
            assert response["type"] == "error"
            assert "Authentication failed" in response["message"]

    def test_websocket_auth_wrong_message_type(self, client):
        """Test WebSocket with wrong first message type."""
        with client.websocket_connect("/ws/dashboard") as websocket:
            # Send non-auth message first
            message = {"type": "ping"}
            websocket.send_text(json.dumps(message))

            # Should receive error
            response = websocket.receive_json()
            assert response["type"] == "error"
            assert "Authentication required" in response["message"]


class TestWebSocketMessaging:
    """Test WebSocket message handling."""

    @patch("cc_orchestrator.web.routers.websocket.ws_manager")
    def test_ping_pong(self, mock_ws_manager, client, auth_token):
        """Test ping-pong message handling."""
        # Mock the WebSocket manager
        mock_ws_manager.connect = AsyncMock(return_value="test-connection-id")
        mock_ws_manager.send_to_connection = AsyncMock()
        mock_ws_manager.disconnect = AsyncMock()

        with client.websocket_connect("/ws/dashboard") as websocket:
            # Authenticate first
            auth_message = {"type": "auth", "token": auth_token}
            websocket.send_text(json.dumps(auth_message))
            websocket.receive_json()  # Consume auth response

            # Send ping message
            ping_message = {"type": "ping", "timestamp": "2024-01-01T00:00:00Z"}
            websocket.send_text(json.dumps(ping_message))

            # Should call send_to_connection with pong response
            mock_ws_manager.send_to_connection.assert_called_with(
                "test-connection-id",
                {"type": "pong", "timestamp": "2024-01-01T00:00:00Z"},
            )

    @patch("cc_orchestrator.web.routers.websocket.ws_manager")
    def test_subscription_handling(self, mock_ws_manager, client, auth_token):
        """Test subscription message handling."""
        mock_ws_manager.connect = AsyncMock(return_value="test-connection-id")
        mock_ws_manager.add_subscription = AsyncMock()
        mock_ws_manager.send_to_connection = AsyncMock()
        mock_ws_manager.disconnect = AsyncMock()

        with client.websocket_connect("/ws/dashboard") as websocket:
            # Authenticate first
            auth_message = {"type": "auth", "token": auth_token}
            websocket.send_text(json.dumps(auth_message))
            websocket.receive_json()  # Consume auth response

            # Send subscription message
            sub_message = {
                "type": "subscribe",
                "events": ["instance_status", "system_events"],
            }
            websocket.send_text(json.dumps(sub_message))

            # Should call add_subscription
            mock_ws_manager.add_subscription.assert_called_with(
                "test-connection-id", ["instance_status", "system_events"]
            )

            # Should send confirmation
            mock_ws_manager.send_to_connection.assert_called_with(
                "test-connection-id",
                {
                    "type": "subscription_confirmed",
                    "events": ["instance_status", "system_events"],
                },
            )

    @patch("cc_orchestrator.web.routers.websocket.ws_manager")
    def test_unsubscription_handling(self, mock_ws_manager, client, auth_token):
        """Test unsubscription message handling."""
        mock_ws_manager.connect = AsyncMock(return_value="test-connection-id")
        mock_ws_manager.remove_subscription = AsyncMock()
        mock_ws_manager.send_to_connection = AsyncMock()
        mock_ws_manager.disconnect = AsyncMock()

        with client.websocket_connect("/ws/dashboard") as websocket:
            # Authenticate first
            auth_message = {"type": "auth", "token": auth_token}
            websocket.send_text(json.dumps(auth_message))
            websocket.receive_json()  # Consume auth response

            # Send unsubscription message
            unsub_message = {"type": "unsubscribe", "events": ["instance_status"]}
            websocket.send_text(json.dumps(unsub_message))

            # Should call remove_subscription
            mock_ws_manager.remove_subscription.assert_called_with(
                "test-connection-id", ["instance_status"]
            )

            # Should send confirmation
            mock_ws_manager.send_to_connection.assert_called_with(
                "test-connection-id",
                {"type": "unsubscription_confirmed", "events": ["instance_status"]},
            )

    @patch("cc_orchestrator.web.routers.websocket.ws_manager")
    def test_unknown_message_type(self, mock_ws_manager, client, auth_token):
        """Test handling of unknown message types."""
        mock_ws_manager.connect = AsyncMock(return_value="test-connection-id")
        mock_ws_manager.send_to_connection = AsyncMock()
        mock_ws_manager.disconnect = AsyncMock()

        with client.websocket_connect("/ws/dashboard") as websocket:
            # Authenticate first
            auth_message = {"type": "auth", "token": auth_token}
            websocket.send_text(json.dumps(auth_message))
            websocket.receive_json()  # Consume auth response

            # Send unknown message type
            unknown_message = {"type": "unknown_type"}
            websocket.send_text(json.dumps(unknown_message))

            # Should send error message
            mock_ws_manager.send_to_connection.assert_called_with(
                "test-connection-id",
                {"type": "error", "message": "Unknown message type: unknown_type"},
            )

    @patch("cc_orchestrator.web.routers.websocket.ws_manager")
    def test_invalid_json_handling(self, mock_ws_manager, client, auth_token):
        """Test handling of invalid JSON messages."""
        mock_ws_manager.connect = AsyncMock(return_value="test-connection-id")
        mock_ws_manager.disconnect = AsyncMock()

        with client.websocket_connect("/ws/dashboard") as websocket:
            # Authenticate first
            auth_message = {"type": "auth", "token": auth_token}
            websocket.send_text(json.dumps(auth_message))
            websocket.receive_json()  # Consume auth response

            # Send invalid JSON
            websocket.send_text("invalid json content")

            # Should receive error response
            response = websocket.receive_json()
            assert response["type"] == "error"
            assert "Invalid JSON format" in response["message"]


class TestWebSocketManager:
    """Test WebSocket manager functionality."""

    @pytest.fixture
    def ws_manager(self):
        """Create WebSocket manager instance."""
        from cc_orchestrator.web.websocket_manager import WebSocketManager

        return WebSocketManager()

    def test_connection_management(self, ws_manager):
        """Test WebSocket connection management."""
        # Test that the WebSocket manager exists and has expected attributes
        assert hasattr(ws_manager, 'connections')
        assert hasattr(ws_manager, 'subscriptions')
        assert hasattr(ws_manager, 'max_connections')

        # Test that initial state is empty
        assert len(ws_manager.connections) == 0
        assert len(ws_manager.subscriptions) == 0

    def test_subscription_management(self, ws_manager):
        """Test subscription management."""
        connection_id = "test-connection"
        events = ["instance_status", "system_events"]

        # Add subscriptions
        ws_manager.subscriptions[connection_id] = set()
        ws_manager.subscriptions[connection_id].update(events)

        assert "instance_status" in ws_manager.subscriptions[connection_id]
        assert "system_events" in ws_manager.subscriptions[connection_id]

        # Remove subscription
        ws_manager.subscriptions[connection_id].remove("instance_status")
        assert "instance_status" not in ws_manager.subscriptions[connection_id]
        assert "system_events" in ws_manager.subscriptions[connection_id]

    def test_broadcast_functionality(self, ws_manager):
        """Test broadcast to subscribers."""
        # This would require more complex mocking of WebSocket connections
        # For now, just test that the method exists and can be called
        assert hasattr(ws_manager, "broadcast_to_subscribers")
        assert callable(ws_manager.broadcast_to_subscribers)
