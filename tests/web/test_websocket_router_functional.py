"""
Functional tests for WebSocket router endpoints.

Tests actual WebSocket endpoint behavior, connection handling, and message processing.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import WebSocket, WebSocketDisconnect


class TestWebSocketEndpointsFunctional:
    """Test WebSocket endpoint functionality with mocked connections."""

    @pytest.fixture
    def mock_websocket(self):
        """Create a mock WebSocket for testing."""
        websocket = Mock(spec=WebSocket)
        websocket.client = Mock()
        websocket.client.host = "127.0.0.1"
        websocket.receive_text = AsyncMock()
        websocket.send_text = AsyncMock()
        websocket.accept = AsyncMock()
        websocket.close = AsyncMock()
        return websocket

    @pytest.mark.asyncio
    @patch("cc_orchestrator.web.websocket.router.connection_manager")
    async def test_websocket_endpoint_successful_connection(
        self, mock_manager, mock_websocket
    ):
        """Test successful WebSocket connection flow."""
        # Setup
        mock_manager.connect = AsyncMock(return_value="test-connection-123")
        mock_manager.handle_message = AsyncMock()
        mock_manager.disconnect = AsyncMock()
        mock_manager.subscribe = AsyncMock()
        mock_websocket.receive_text.side_effect = [
            '{"type": "ping"}',
            WebSocketDisconnect(),
        ]

        # Import and test the endpoint
        from cc_orchestrator.web.websocket.router import websocket_endpoint

        # Execute
        await websocket_endpoint(mock_websocket)

        # Verify connection flow
        mock_manager.connect.assert_called_once_with(mock_websocket, "127.0.0.1")
        mock_manager.handle_message.assert_called_once_with(
            "test-connection-123", '{"type": "ping"}'
        )
        mock_manager.disconnect.assert_called_once_with(
            "test-connection-123", "client_disconnect"
        )

    @pytest.mark.asyncio
    @patch("cc_orchestrator.web.websocket.router.connection_manager")
    async def test_websocket_endpoint_unknown_client(self, mock_manager, mock_websocket):
        """Test WebSocket endpoint with unknown client IP."""
        # Setup - no client info
        mock_websocket.client = None
        mock_manager.connect = AsyncMock(return_value="test-connection-456")
        mock_manager.disconnect = AsyncMock()
        mock_websocket.receive_text.side_effect = WebSocketDisconnect()

        from cc_orchestrator.web.websocket.router import websocket_endpoint

        # Execute
        await websocket_endpoint(mock_websocket)

        # Verify unknown client handling
        mock_manager.connect.assert_called_once_with(mock_websocket, "unknown")
        mock_manager.disconnect.assert_called_once_with(
            "test-connection-456", "client_disconnect"
        )

    @pytest.mark.asyncio
    @patch("cc_orchestrator.web.websocket.router.connection_manager")
    async def test_websocket_endpoint_exception_handling(
        self, mock_manager, mock_websocket
    ):
        """Test WebSocket endpoint exception handling."""
        # Setup
        mock_manager.connect = AsyncMock(return_value="test-connection-error")
        mock_manager.disconnect = AsyncMock()
        mock_websocket.receive_text.side_effect = RuntimeError("Test error")

        from cc_orchestrator.web.websocket.router import websocket_endpoint

        # Execute
        await websocket_endpoint(mock_websocket)

        # Verify error handling
        mock_manager.connect.assert_called_once()
        mock_manager.disconnect.assert_called_once_with(
            "test-connection-error", "error: Test error"
        )

    @pytest.mark.asyncio
    @patch("cc_orchestrator.web.websocket.router.connection_manager")
    async def test_instance_websocket_endpoint(self, mock_manager, mock_websocket):
        """Test instance-specific WebSocket endpoint."""
        # Setup
        mock_manager.connect = AsyncMock(return_value="instance-connection-123")
        mock_manager.subscribe = AsyncMock()
        mock_manager.handle_message = AsyncMock()
        mock_manager.disconnect = AsyncMock()
        mock_websocket.receive_text.side_effect = [
            '{"type": "status_request"}',
            WebSocketDisconnect(),
        ]

        from cc_orchestrator.web.websocket.router import instance_websocket

        # Execute
        await instance_websocket(mock_websocket, "test-instance-456")

        # Verify instance-specific behavior
        mock_manager.connect.assert_called_once_with(mock_websocket, "127.0.0.1")
        mock_manager.subscribe.assert_called_once_with(
            "instance-connection-123", "instance:test-instance-456"
        )
        mock_manager.handle_message.assert_called_once_with(
            "instance-connection-123", '{"type": "status_request"}'
        )
        mock_manager.disconnect.assert_called_once_with(
            "instance-connection-123", "client_disconnect"
        )

    @pytest.mark.asyncio
    @patch("cc_orchestrator.web.websocket.router.connection_manager")
    async def test_task_websocket_endpoint(self, mock_manager, mock_websocket):
        """Test task-specific WebSocket endpoint."""
        # Setup
        mock_manager.connect = AsyncMock(return_value="task-connection-789")
        mock_manager.subscribe = AsyncMock()
        mock_manager.handle_message = AsyncMock()
        mock_manager.disconnect = AsyncMock()
        mock_websocket.receive_text.side_effect = [
            '{"type": "task_update"}',
            WebSocketDisconnect(),
        ]

        from cc_orchestrator.web.websocket.router import task_websocket

        # Execute
        await task_websocket(mock_websocket, "task-789")

        # Verify task-specific behavior
        mock_manager.connect.assert_called_once_with(mock_websocket, "127.0.0.1")
        mock_manager.subscribe.assert_called_once_with(
            "task-connection-789", "task:task-789"
        )
        mock_manager.handle_message.assert_called_once_with(
            "task-connection-789", '{"type": "task_update"}'
        )
        mock_manager.disconnect.assert_called_once_with(
            "task-connection-789", "client_disconnect"
        )

    @pytest.mark.asyncio
    @patch("cc_orchestrator.web.websocket.router.connection_manager")
    async def test_logs_websocket_endpoint(self, mock_manager, mock_websocket):
        """Test logs WebSocket endpoint."""
        # Setup
        mock_manager.connect = AsyncMock(return_value="logs-connection-111")
        mock_manager.subscribe = AsyncMock()
        mock_manager.handle_message = AsyncMock()
        mock_manager.disconnect = AsyncMock()
        mock_websocket.receive_text.side_effect = [
            '{"type": "log_level", "data": {"level": "info"}}',
            WebSocketDisconnect(),
        ]

        from cc_orchestrator.web.websocket.router import logs_websocket

        # Execute
        await logs_websocket(mock_websocket)

        # Verify logs-specific behavior
        mock_manager.connect.assert_called_once_with(mock_websocket, "127.0.0.1")
        mock_manager.subscribe.assert_called_once_with("logs-connection-111", "logs")
        mock_manager.handle_message.assert_called_once_with(
            "logs-connection-111", '{"type": "log_level", "data": {"level": "info"}}'
        )
        mock_manager.disconnect.assert_called_once_with(
            "logs-connection-111", "client_disconnect"
        )

    @pytest.mark.asyncio
    @patch("cc_orchestrator.web.websocket.router.connection_manager")
    async def test_dashboard_websocket_endpoint(self, mock_manager, mock_websocket):
        """Test dashboard WebSocket endpoint with multiple subscriptions."""
        # Setup
        mock_manager.connect = AsyncMock(return_value="dashboard-connection-222")
        mock_manager.subscribe = AsyncMock()
        mock_manager.handle_message = AsyncMock()
        mock_manager.disconnect = AsyncMock()
        mock_websocket.receive_text.side_effect = [
            '{"type": "dashboard_init"}',
            '{"type": "refresh"}',
            WebSocketDisconnect(),
        ]

        from cc_orchestrator.web.websocket.router import dashboard_websocket

        # Execute
        await dashboard_websocket(mock_websocket)

        # Verify dashboard-specific behavior
        mock_manager.connect.assert_called_once_with(mock_websocket, "127.0.0.1")

        # Should subscribe to multiple dashboard topics
        expected_subscriptions = [
            ("dashboard-connection-222", "dashboard"),
            ("dashboard-connection-222", "instances"),
            ("dashboard-connection-222", "tasks"),
            ("dashboard-connection-222", "system_status"),
            ("dashboard-connection-222", "alerts"),
        ]

        assert mock_manager.subscribe.call_count == 5
        for expected_call in expected_subscriptions:
            mock_manager.subscribe.assert_any_call(*expected_call)

        # Should handle multiple messages
        assert mock_manager.handle_message.call_count == 2
        mock_manager.handle_message.assert_any_call(
            "dashboard-connection-222", '{"type": "dashboard_init"}'
        )
        mock_manager.handle_message.assert_any_call(
            "dashboard-connection-222", '{"type": "refresh"}'
        )

        mock_manager.disconnect.assert_called_once_with(
            "dashboard-connection-222", "client_disconnect"
        )

    @pytest.mark.asyncio
    @patch("cc_orchestrator.web.websocket.router.connection_manager")
    async def test_multiple_messages_before_disconnect(
        self, mock_manager, mock_websocket
    ):
        """Test handling multiple messages before disconnection."""
        # Setup
        mock_manager.connect = AsyncMock(return_value="multi-msg-connection")
        mock_manager.handle_message = AsyncMock()
        mock_manager.disconnect = AsyncMock()
        messages = [
            '{"type": "auth", "token": "abc123"}',
            '{"type": "subscribe", "topic": "instances"}',
            '{"type": "ping"}',
            WebSocketDisconnect(),
        ]
        mock_websocket.receive_text.side_effect = messages

        from cc_orchestrator.web.websocket.router import websocket_endpoint

        # Execute
        await websocket_endpoint(mock_websocket)

        # Verify all messages were handled
        assert mock_manager.handle_message.call_count == 3
        expected_calls = [
            ("multi-msg-connection", '{"type": "auth", "token": "abc123"}'),
            ("multi-msg-connection", '{"type": "subscribe", "topic": "instances"}'),
            ("multi-msg-connection", '{"type": "ping"}'),
        ]

        for expected_call in expected_calls:
            mock_manager.handle_message.assert_any_call(*expected_call)

    @pytest.mark.asyncio
    @patch("cc_orchestrator.web.websocket.router.connection_manager")
    async def test_endpoint_error_after_messages(self, mock_manager, mock_websocket):
        """Test error handling after processing some messages."""
        # Setup
        mock_manager.connect = AsyncMock(return_value="error-after-msg")
        mock_manager.handle_message = AsyncMock()
        mock_manager.disconnect = AsyncMock()
        mock_websocket.receive_text.side_effect = [
            '{"type": "valid_message"}',
            RuntimeError("Connection lost"),
        ]

        from cc_orchestrator.web.websocket.router import websocket_endpoint

        # Execute
        await websocket_endpoint(mock_websocket)

        # Verify message was processed before error
        mock_manager.handle_message.assert_called_once_with(
            "error-after-msg", '{"type": "valid_message"}'
        )
        mock_manager.disconnect.assert_called_once_with(
            "error-after-msg", "error: Connection lost"
        )


class TestWebSocketEndpointVariations:
    """Test WebSocket endpoint variations and edge cases."""

    @pytest.fixture
    def mock_websocket_no_client(self):
        """Create a mock WebSocket with no client info."""
        websocket = Mock(spec=WebSocket)
        websocket.client = None
        websocket.receive_text = AsyncMock()
        return websocket

    @pytest.mark.asyncio
    @patch("cc_orchestrator.web.websocket.router.connection_manager")
    async def test_all_endpoints_handle_no_client(
        self, mock_manager, mock_websocket_no_client
    ):
        """Test that all endpoints handle missing client info."""
        mock_manager.connect = AsyncMock(return_value="no-client-connection")
        mock_manager.disconnect = AsyncMock()
        mock_manager.subscribe = AsyncMock()
        mock_websocket_no_client.receive_text.side_effect = WebSocketDisconnect()

        # Import all endpoint functions
        from cc_orchestrator.web.websocket.router import (
            dashboard_websocket,
            instance_websocket,
            logs_websocket,
            task_websocket,
            websocket_endpoint,
        )

        endpoints = [
            (websocket_endpoint, ()),
            (instance_websocket, ("test-instance",)),
            (task_websocket, ("test-task",)),
            (logs_websocket, ()),
            (dashboard_websocket, ()),
        ]

        for endpoint_func, args in endpoints:
            # Reset mock for each test
            mock_manager.reset_mock()
            mock_manager.connect = AsyncMock(return_value=f"no-client-{endpoint_func.__name__}")
            mock_manager.disconnect = AsyncMock()
            mock_manager.subscribe = AsyncMock()

            # Execute endpoint
            await endpoint_func(mock_websocket_no_client, *args)

            # Verify unknown client IP handling
            mock_manager.connect.assert_called_once_with(
                mock_websocket_no_client, "unknown"
            )
            mock_manager.disconnect.assert_called_once()

    @pytest.fixture
    def mock_websocket(self):
        """Create a mock WebSocket for testing."""
        websocket = Mock(spec=WebSocket)
        websocket.client = Mock()
        websocket.client.host = "127.0.0.1"
        websocket.receive_text = AsyncMock()
        websocket.send_text = AsyncMock()
        websocket.accept = AsyncMock()
        websocket.close = AsyncMock()
        return websocket

    @pytest.mark.asyncio
    @patch("cc_orchestrator.web.websocket.router.connection_manager")
    async def test_different_exception_types(self, mock_manager, mock_websocket):
        """Test handling of different exception types."""
        mock_websocket.client.host = "192.168.1.100"
        mock_manager.connect = AsyncMock(return_value="exception-test")
        mock_manager.disconnect = AsyncMock()

        from cc_orchestrator.web.websocket.router import websocket_endpoint

        # Test different exception types
        exception_types = [
            ValueError("Invalid value"),
            ConnectionError("Connection failed"),
            RuntimeError("Runtime error"),
            Exception("Generic exception"),
        ]

        for exception in exception_types:
            # Reset for each test
            mock_manager.reset_mock()
            mock_manager.connect = AsyncMock(return_value=f"exception-{type(exception).__name__}")
            mock_manager.disconnect = AsyncMock()
            mock_websocket.receive_text.side_effect = exception

            # Execute
            await websocket_endpoint(mock_websocket)

            # Verify error is properly formatted
            expected_error = f"error: {str(exception)}"
            mock_manager.disconnect.assert_called_once()
            disconnect_call = mock_manager.disconnect.call_args[0]
            assert disconnect_call[1] == expected_error

