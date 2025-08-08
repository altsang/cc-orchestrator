"""Comprehensive tests for WebSocket router functionality."""

import json
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import WebSocket, status
from fastapi.websockets import WebSocketState

from cc_orchestrator.web.routers.websocket import (
    broadcast_instance_metrics,
    broadcast_instance_status_change,
    broadcast_system_event,
    handle_client_message,
    websocket_dashboard,
    ws_manager,
)


class MockWebSocket:
    """Mock WebSocket for testing."""
    
    def __init__(self):
        self.client = Mock()
        self.client.host = "127.0.0.1"
        self.client_state = WebSocketState.CONNECTED
        self.messages_sent = []
        self.messages_received = []
        self.closed = False
        self.close_code = None
        
    async def accept(self):
        """Mock accept method."""
        pass
        
    async def send_json(self, data):
        """Mock send_json method."""
        if self.closed:
            raise Exception("Connection closed")
        self.messages_sent.append(data)
        
    async def send_text(self, text):
        """Mock send_text method."""
        if self.closed:
            raise Exception("Connection closed")
        self.messages_sent.append(text)
        
    async def receive_text(self):
        """Mock receive_text method."""
        if self.messages_received:
            return self.messages_received.pop(0)
        if self.closed:
            raise Exception("Connection closed")
        # Simulate waiting for message
        return '{"type": "ping"}'
        
    async def close(self, code=None, reason=None):
        """Mock close method."""
        self.closed = True
        self.close_code = code
        self.client_state = WebSocketState.DISCONNECTED
        
    def add_message_to_receive(self, message):
        """Add message to receive queue."""
        if isinstance(message, dict):
            message = json.dumps(message)
        self.messages_received.append(message)


@pytest.mark.asyncio
class TestWebSocketDashboard:
    """Test WebSocket dashboard endpoint."""

    async def test_websocket_authentication_success(self):
        """Test successful WebSocket authentication."""
        websocket = MockWebSocket()
        auth_message = {"type": "auth", "token": "valid-token"}
        websocket.add_message_to_receive(auth_message)
        
        with patch('cc_orchestrator.web.routers.websocket.verify_token') as mock_verify, \
             patch.object(ws_manager, 'connect') as mock_connect, \
             patch.object(ws_manager, 'disconnect') as mock_disconnect:
            
            mock_verify.return_value = {"sub": "testuser"}
            mock_connect.return_value = "conn-123"
            
            # Simulate disconnect to end the loop
            websocket.client_state = WebSocketState.DISCONNECTED
            
            await websocket_dashboard(websocket)
            
            # Verify authentication success message was sent
            sent_messages = websocket.messages_sent
            assert len(sent_messages) >= 1
            auth_success = sent_messages[0]
            assert auth_success["type"] == "auth_success"
            assert auth_success["user"] == "testuser"

    async def test_websocket_authentication_missing_type(self):
        """Test WebSocket authentication with missing type."""
        websocket = MockWebSocket()
        invalid_message = {"token": "valid-token"}  # Missing type
        websocket.add_message_to_receive(invalid_message)
        
        with patch('cc_orchestrator.web.routers.websocket.verify_token'):
            await websocket_dashboard(websocket)
            
            # Verify error message was sent
            sent_messages = websocket.messages_sent
            assert len(sent_messages) >= 1
            error_message = sent_messages[0]
            assert error_message["type"] == "error"
            assert "Authentication required" in error_message["message"]
            
            # Verify connection was closed
            assert websocket.closed
            assert websocket.close_code == status.WS_1008_POLICY_VIOLATION

    async def test_websocket_authentication_missing_token(self):
        """Test WebSocket authentication with missing token."""
        websocket = MockWebSocket()
        invalid_message = {"type": "auth"}  # Missing token
        websocket.add_message_to_receive(invalid_message)
        
        with patch('cc_orchestrator.web.routers.websocket.verify_token'):
            await websocket_dashboard(websocket)
            
            # Verify error message was sent
            sent_messages = websocket.messages_sent
            assert len(sent_messages) >= 1
            error_message = sent_messages[0]
            assert error_message["type"] == "error"
            assert "Token required" in error_message["message"]
            
            # Verify connection was closed
            assert websocket.closed

    async def test_websocket_authentication_invalid_token(self):
        """Test WebSocket authentication with invalid token."""
        websocket = MockWebSocket()
        auth_message = {"type": "auth", "token": "invalid-token"}
        websocket.add_message_to_receive(auth_message)
        
        with patch('cc_orchestrator.web.routers.websocket.verify_token') as mock_verify:
            mock_verify.side_effect = Exception("Invalid token")
            
            await websocket_dashboard(websocket)
            
            # Verify error message was sent
            sent_messages = websocket.messages_sent
            assert len(sent_messages) >= 1
            error_message = sent_messages[0]
            assert error_message["type"] == "error"
            assert "Authentication failed" in error_message["message"]
            
            # Verify connection was closed
            assert websocket.closed

    async def test_websocket_malformed_json_in_auth(self):
        """Test WebSocket with malformed JSON in auth message."""
        websocket = MockWebSocket()
        websocket.add_message_to_receive("invalid-json{")
        
        with patch('cc_orchestrator.web.routers.websocket.verify_token'):
            await websocket_dashboard(websocket)
            
            # Should handle JSON decode error gracefully
            assert websocket.closed

    async def test_websocket_connection_and_disconnect(self):
        """Test WebSocket connection establishment and disconnection."""
        websocket = MockWebSocket()
        auth_message = {"type": "auth", "token": "valid-token"}
        websocket.add_message_to_receive(auth_message)
        
        with patch('cc_orchestrator.web.routers.websocket.verify_token') as mock_verify, \
             patch.object(ws_manager, 'connect') as mock_connect, \
             patch.object(ws_manager, 'disconnect') as mock_disconnect, \
             patch('cc_orchestrator.web.routers.websocket.log_websocket_connection') as mock_log:
            
            mock_verify.return_value = {"sub": "testuser"}
            mock_connect.return_value = "conn-123"
            
            # Simulate immediate disconnect
            websocket.client_state = WebSocketState.DISCONNECTED
            
            await websocket_dashboard(websocket)
            
            # Verify connection was established and then cleaned up
            mock_connect.assert_called_once_with(websocket)
            mock_disconnect.assert_called_once_with("conn-123")

    async def test_websocket_message_handling_loop(self):
        """Test WebSocket message handling loop."""
        websocket = MockWebSocket()
        auth_message = {"type": "auth", "token": "valid-token"}
        client_message = {"type": "ping", "timestamp": "2024-01-01T00:00:00Z"}
        
        websocket.add_message_to_receive(auth_message)
        websocket.add_message_to_receive(client_message)
        
        with patch('cc_orchestrator.web.routers.websocket.verify_token') as mock_verify, \
             patch.object(ws_manager, 'connect') as mock_connect, \
             patch.object(ws_manager, 'disconnect') as mock_disconnect, \
             patch('cc_orchestrator.web.routers.websocket.handle_client_message') as mock_handle, \
             patch('cc_orchestrator.web.routers.websocket.log_websocket_message') as mock_log:
            
            mock_verify.return_value = {"sub": "testuser"}
            mock_connect.return_value = "conn-123"
            
            # Set up to disconnect after processing one message
            call_count = 0
            original_state = websocket.client_state
            
            def check_disconnect(*args):
                nonlocal call_count
                call_count += 1
                if call_count >= 1:
                    websocket.client_state = WebSocketState.DISCONNECTED
            
            mock_handle.side_effect = check_disconnect
            
            await websocket_dashboard(websocket)
            
            # Verify message was handled
            mock_handle.assert_called_once_with("conn-123", client_message)
            mock_log.assert_called_once()

    async def test_websocket_invalid_json_message_handling(self):
        """Test WebSocket handling of invalid JSON messages."""
        websocket = MockWebSocket()
        auth_message = {"type": "auth", "token": "valid-token"}
        
        websocket.add_message_to_receive(auth_message)
        websocket.add_message_to_receive("invalid-json{")  # Invalid JSON
        
        with patch('cc_orchestrator.web.routers.websocket.verify_token') as mock_verify, \
             patch.object(ws_manager, 'connect') as mock_connect, \
             patch.object(ws_manager, 'disconnect') as mock_disconnect:
            
            mock_verify.return_value = {"sub": "testuser"}
            mock_connect.return_value = "conn-123"
            
            # Set up to disconnect after processing invalid message
            call_count = 0
            
            async def mock_receive_text():
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    return json.dumps(auth_message)
                elif call_count == 2:
                    return "invalid-json{"
                else:
                    websocket.client_state = WebSocketState.DISCONNECTED
                    return ""
            
            websocket.receive_text = mock_receive_text
            
            await websocket_dashboard(websocket)
            
            # Verify error message was sent for invalid JSON
            error_messages = [msg for msg in websocket.messages_sent if msg.get("type") == "error"]
            assert len(error_messages) >= 1
            assert any("Invalid JSON format" in msg["message"] for msg in error_messages)


@pytest.mark.asyncio
class TestHandleClientMessage:
    """Test client message handling functionality."""

    async def test_handle_ping_message(self):
        """Test handling ping messages."""
        connection_id = "conn-test"
        message = {"type": "ping", "timestamp": "2024-01-01T00:00:00Z"}
        
        with patch.object(ws_manager, 'send_to_connection') as mock_send:
            await handle_client_message(connection_id, message)
            
            mock_send.assert_called_once_with(
                connection_id,
                {"type": "pong", "timestamp": "2024-01-01T00:00:00Z"}
            )

    async def test_handle_subscribe_message(self):
        """Test handling subscription messages."""
        connection_id = "conn-test"
        message = {"type": "subscribe", "events": ["instance_status", "metrics"]}
        
        with patch.object(ws_manager, 'add_subscription') as mock_subscribe, \
             patch.object(ws_manager, 'send_to_connection') as mock_send:
            
            await handle_client_message(connection_id, message)
            
            mock_subscribe.assert_called_once_with(connection_id, ["instance_status", "metrics"])
            mock_send.assert_called_once_with(
                connection_id,
                {"type": "subscription_confirmed", "events": ["instance_status", "metrics"]}
            )

    async def test_handle_unsubscribe_message(self):
        """Test handling unsubscription messages."""
        connection_id = "conn-test"
        message = {"type": "unsubscribe", "events": ["instance_status"]}
        
        with patch.object(ws_manager, 'remove_subscription') as mock_unsubscribe, \
             patch.object(ws_manager, 'send_to_connection') as mock_send:
            
            await handle_client_message(connection_id, message)
            
            mock_unsubscribe.assert_called_once_with(connection_id, ["instance_status"])
            mock_send.assert_called_once_with(
                connection_id,
                {"type": "unsubscription_confirmed", "events": ["instance_status"]}
            )

    async def test_handle_unknown_message_type(self):
        """Test handling unknown message types."""
        connection_id = "conn-test"
        message = {"type": "unknown_type", "data": "test"}
        
        with patch.object(ws_manager, 'send_to_connection') as mock_send:
            await handle_client_message(connection_id, message)
            
            mock_send.assert_called_once_with(
                connection_id,
                {"type": "error", "message": "Unknown message type: unknown_type"}
            )

    async def test_handle_subscribe_with_empty_events(self):
        """Test handling subscription with empty events list."""
        connection_id = "conn-test"
        message = {"type": "subscribe", "events": []}
        
        with patch.object(ws_manager, 'add_subscription') as mock_subscribe, \
             patch.object(ws_manager, 'send_to_connection') as mock_send:
            
            await handle_client_message(connection_id, message)
            
            mock_subscribe.assert_called_once_with(connection_id, [])
            mock_send.assert_called_once_with(
                connection_id,
                {"type": "subscription_confirmed", "events": []}
            )

    async def test_handle_subscribe_without_events(self):
        """Test handling subscription without events field."""
        connection_id = "conn-test"
        message = {"type": "subscribe"}  # No events field
        
        with patch.object(ws_manager, 'add_subscription') as mock_subscribe, \
             patch.object(ws_manager, 'send_to_connection') as mock_send:
            
            await handle_client_message(connection_id, message)
            
            mock_subscribe.assert_called_once_with(connection_id, [])
            mock_send.assert_called_once_with(
                connection_id,
                {"type": "subscription_confirmed", "events": []}
            )

    async def test_handle_ping_without_timestamp(self):
        """Test handling ping without timestamp."""
        connection_id = "conn-test"
        message = {"type": "ping"}  # No timestamp
        
        with patch.object(ws_manager, 'send_to_connection') as mock_send:
            await handle_client_message(connection_id, message)
            
            mock_send.assert_called_once_with(
                connection_id,
                {"type": "pong", "timestamp": None}
            )


@pytest.mark.asyncio
class TestBroadcastFunctions:
    """Test broadcast convenience functions."""

    async def test_broadcast_instance_status_change(self):
        """Test broadcasting instance status changes."""
        with patch.object(ws_manager, 'broadcast_to_subscribers') as mock_broadcast, \
             patch.object(ws_manager, 'get_current_timestamp') as mock_timestamp:
            
            mock_timestamp.return_value = "2024-01-01T00:00:00Z"
            
            await broadcast_instance_status_change(
                instance_id=123,
                old_status="INITIALIZING",
                new_status="RUNNING"
            )
            
            mock_broadcast.assert_called_once_with(
                "instance_status",
                {
                    "type": "instance_status_change",
                    "instance_id": 123,
                    "old_status": "INITIALIZING",
                    "new_status": "RUNNING",
                    "timestamp": "2024-01-01T00:00:00Z",
                },
            )

    async def test_broadcast_instance_metrics(self):
        """Test broadcasting instance metrics."""
        metrics = {
            "cpu_usage": 45.6,
            "memory_usage": 67.8,
            "disk_usage": 23.4
        }
        
        with patch.object(ws_manager, 'broadcast_to_subscribers') as mock_broadcast, \
             patch.object(ws_manager, 'get_current_timestamp') as mock_timestamp:
            
            mock_timestamp.return_value = "2024-01-01T00:00:00Z"
            
            await broadcast_instance_metrics(instance_id=456, metrics=metrics)
            
            mock_broadcast.assert_called_once_with(
                "instance_metrics",
                {
                    "type": "instance_metrics",
                    "instance_id": 456,
                    "metrics": metrics,
                    "timestamp": "2024-01-01T00:00:00Z",
                },
            )

    async def test_broadcast_system_event(self):
        """Test broadcasting system events."""
        event = {
            "severity": "warning",
            "message": "High memory usage detected",
            "source": "system_monitor"
        }
        
        with patch.object(ws_manager, 'broadcast_to_subscribers') as mock_broadcast, \
             patch.object(ws_manager, 'get_current_timestamp') as mock_timestamp:
            
            mock_timestamp.return_value = "2024-01-01T00:00:00Z"
            
            await broadcast_system_event(event)
            
            expected_payload = {
                "type": "system_event",
                "severity": "warning",
                "message": "High memory usage detected",
                "source": "system_monitor",
                "timestamp": "2024-01-01T00:00:00Z",
            }
            
            mock_broadcast.assert_called_once_with("system_events", expected_payload)

    async def test_broadcast_instance_status_change_with_different_statuses(self):
        """Test broadcasting different status transitions."""
        status_transitions = [
            ("INITIALIZING", "RUNNING"),
            ("RUNNING", "STOPPED"),
            ("STOPPED", "RUNNING"),
            ("RUNNING", "ERROR"),
            ("ERROR", "INITIALIZING"),
        ]
        
        for old_status, new_status in status_transitions:
            with patch.object(ws_manager, 'broadcast_to_subscribers') as mock_broadcast, \
                 patch.object(ws_manager, 'get_current_timestamp') as mock_timestamp:
                
                mock_timestamp.return_value = "2024-01-01T00:00:00Z"
                
                await broadcast_instance_status_change(
                    instance_id=1,
                    old_status=old_status,
                    new_status=new_status
                )
                
                # Verify broadcast was called with correct parameters
                call_args = mock_broadcast.call_args
                assert call_args[0][0] == "instance_status"
                payload = call_args[0][1]
                assert payload["old_status"] == old_status
                assert payload["new_status"] == new_status

    async def test_broadcast_empty_metrics(self):
        """Test broadcasting empty metrics."""
        empty_metrics = {}
        
        with patch.object(ws_manager, 'broadcast_to_subscribers') as mock_broadcast, \
             patch.object(ws_manager, 'get_current_timestamp') as mock_timestamp:
            
            mock_timestamp.return_value = "2024-01-01T00:00:00Z"
            
            await broadcast_instance_metrics(instance_id=789, metrics=empty_metrics)
            
            mock_broadcast.assert_called_once()
            call_args = mock_broadcast.call_args
            payload = call_args[0][1]
            assert payload["metrics"] == {}

    async def test_broadcast_system_event_minimal(self):
        """Test broadcasting minimal system event."""
        minimal_event = {"message": "Test event"}
        
        with patch.object(ws_manager, 'broadcast_to_subscribers') as mock_broadcast, \
             patch.object(ws_manager, 'get_current_timestamp') as mock_timestamp:
            
            mock_timestamp.return_value = "2024-01-01T00:00:00Z"
            
            await broadcast_system_event(minimal_event)
            
            expected_payload = {
                "type": "system_event",
                "message": "Test event",
                "timestamp": "2024-01-01T00:00:00Z",
            }
            
            mock_broadcast.assert_called_once_with("system_events", expected_payload)


@pytest.mark.asyncio
class TestWebSocketRouterEdgeCases:
    """Test edge cases and error conditions."""

    async def test_websocket_manager_connection_failure(self):
        """Test handling of WebSocket manager connection failures."""
        websocket = MockWebSocket()
        auth_message = {"type": "auth", "token": "valid-token"}
        websocket.add_message_to_receive(auth_message)
        
        with patch('cc_orchestrator.web.routers.websocket.verify_token') as mock_verify, \
             patch.object(ws_manager, 'connect') as mock_connect, \
             patch.object(ws_manager, 'disconnect') as mock_disconnect:
            
            mock_verify.return_value = {"sub": "testuser"}
            mock_connect.side_effect = Exception("Connection limit reached")
            
            # Should handle connection failure gracefully
            try:
                await websocket_dashboard(websocket)
            except Exception:
                pytest.fail("Should handle connection failures gracefully")

    async def test_websocket_manager_send_failure(self):
        """Test handling of send failures."""
        connection_id = "conn-test"
        message = {"type": "ping", "timestamp": "test"}
        
        with patch.object(ws_manager, 'send_to_connection') as mock_send:
            mock_send.side_effect = Exception("Connection closed")
            
            # Should handle send failures gracefully
            try:
                await handle_client_message(connection_id, message)
            except Exception:
                pytest.fail("Should handle send failures gracefully")

    async def test_websocket_manager_subscription_failure(self):
        """Test handling of subscription failures."""
        connection_id = "conn-test"
        message = {"type": "subscribe", "events": ["test"]}
        
        with patch.object(ws_manager, 'add_subscription') as mock_subscribe, \
             patch.object(ws_manager, 'send_to_connection') as mock_send:
            
            mock_subscribe.side_effect = Exception("Subscription failed")
            
            # Should handle subscription failures gracefully
            try:
                await handle_client_message(connection_id, message)
            except Exception:
                pytest.fail("Should handle subscription failures gracefully")

    async def test_broadcast_with_manager_failure(self):
        """Test broadcast functions with manager failures."""
        with patch.object(ws_manager, 'broadcast_to_subscribers') as mock_broadcast:
            mock_broadcast.side_effect = Exception("Broadcast failed")
            
            # Should handle broadcast failures gracefully
            try:
                await broadcast_instance_status_change(1, "OLD", "NEW")
                await broadcast_instance_metrics(1, {})
                await broadcast_system_event({})
            except Exception:
                pytest.fail("Should handle broadcast failures gracefully")

    async def test_websocket_with_none_message_fields(self):
        """Test handling messages with None fields."""
        connection_id = "conn-test"
        
        messages_to_test = [
            {"type": None},
            {"type": "subscribe", "events": None},
            {"type": "ping", "timestamp": None},
        ]
        
        for message in messages_to_test:
            with patch.object(ws_manager, 'send_to_connection') as mock_send, \
                 patch.object(ws_manager, 'add_subscription') as mock_subscribe:
                
                # Should handle None values gracefully
                await handle_client_message(connection_id, message)
                
                # At least one operation should have been called
                assert mock_send.called or mock_subscribe.called

    async def test_websocket_large_message_handling(self):
        """Test handling of large messages."""
        connection_id = "conn-test"
        large_events_list = ["event"] * 1000  # Large events list
        message = {"type": "subscribe", "events": large_events_list}
        
        with patch.object(ws_manager, 'add_subscription') as mock_subscribe, \
             patch.object(ws_manager, 'send_to_connection') as mock_send:
            
            await handle_client_message(connection_id, message)
            
            # Should handle large payloads
            mock_subscribe.assert_called_once_with(connection_id, large_events_list)
            mock_send.assert_called_once()


@pytest.mark.asyncio  
class TestWebSocketRouterIntegration:
    """Test WebSocket router integration scenarios."""

    async def test_complete_websocket_session_flow(self):
        """Test complete WebSocket session from auth to disconnect."""
        websocket = MockWebSocket()
        
        # Prepare message sequence
        auth_message = {"type": "auth", "token": "valid-token"}
        subscribe_message = {"type": "subscribe", "events": ["instance_status"]}
        ping_message = {"type": "ping", "timestamp": "2024-01-01T00:00:00Z"}
        unsubscribe_message = {"type": "unsubscribe", "events": ["instance_status"]}
        
        websocket.add_message_to_receive(auth_message)
        websocket.add_message_to_receive(subscribe_message)
        websocket.add_message_to_receive(ping_message)
        websocket.add_message_to_receive(unsubscribe_message)
        
        with patch('cc_orchestrator.web.routers.websocket.verify_token') as mock_verify, \
             patch.object(ws_manager, 'connect') as mock_connect, \
             patch.object(ws_manager, 'disconnect') as mock_disconnect, \
             patch.object(ws_manager, 'send_to_connection') as mock_send, \
             patch.object(ws_manager, 'add_subscription') as mock_subscribe, \
             patch.object(ws_manager, 'remove_subscription') as mock_unsubscribe:
            
            mock_verify.return_value = {"sub": "testuser"}
            mock_connect.return_value = "conn-integration"
            
            # Set up message handling counter
            message_count = 0
            
            async def count_messages(*args):
                nonlocal message_count
                message_count += 1
                if message_count >= 3:  # After 3 client messages, disconnect
                    websocket.client_state = WebSocketState.DISCONNECTED
            
            mock_send.side_effect = count_messages
            
            await websocket_dashboard(websocket)
            
            # Verify complete flow
            mock_verify.assert_called_once()
            mock_connect.assert_called_once()
            mock_disconnect.assert_called_once()
            
            # Verify operations were called
            assert mock_send.call_count >= 3  # Auth success + confirmations + pong
            mock_subscribe.assert_called()
            mock_unsubscribe.assert_called()

    async def test_broadcast_integration_with_subscriptions(self):
        """Test broadcast integration with actual subscription handling."""
        connection_id = "conn-broadcast-test"
        
        # First, subscribe to events
        subscribe_message = {"type": "subscribe", "events": ["instance_status", "instance_metrics"]}
        
        with patch.object(ws_manager, 'add_subscription') as mock_subscribe, \
             patch.object(ws_manager, 'send_to_connection') as mock_send, \
             patch.object(ws_manager, 'broadcast_to_subscribers') as mock_broadcast, \
             patch.object(ws_manager, 'get_current_timestamp') as mock_timestamp:
            
            mock_timestamp.return_value = "2024-01-01T00:00:00Z"
            
            # Handle subscription
            await handle_client_message(connection_id, subscribe_message)
            
            # Now broadcast events
            await broadcast_instance_status_change(1, "STOPPED", "RUNNING")
            await broadcast_instance_metrics(1, {"cpu": 50.0})
            
            # Verify subscription and broadcasts
            mock_subscribe.assert_called_once()
            assert mock_broadcast.call_count == 2
            
            # Verify broadcast calls were for correct event types
            broadcast_calls = mock_broadcast.call_args_list
            event_types = [call[0][0] for call in broadcast_calls]
            assert "instance_status" in event_types
            assert "instance_metrics" in event_types