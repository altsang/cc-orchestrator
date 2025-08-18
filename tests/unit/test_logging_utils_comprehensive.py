"""Comprehensive tests for logging utilities."""

from unittest.mock import Mock, patch

from cc_orchestrator.web.logging_utils import (
    api_logger,
    auth_logger,
    handle_api_errors,
    log_api_request,
    log_api_response,
    log_authentication_attempt,
    log_authorization_check,
    log_dashboard_access,
    log_real_time_event,
    log_websocket_connection,
    log_websocket_message,
    track_api_performance,
    websocket_logger,
)


class TestLoggerInstances:
    """Test logger instance creation and configuration."""

    def test_api_logger_creation(self):
        """Test API logger is properly created."""
        assert api_logger is not None
        assert hasattr(api_logger, "info")
        assert hasattr(api_logger, "warning")
        assert hasattr(api_logger, "error")
        assert hasattr(api_logger, "debug")

    def test_websocket_logger_creation(self):
        """Test WebSocket logger is properly created."""
        assert websocket_logger is not None
        assert hasattr(websocket_logger, "info")
        assert hasattr(websocket_logger, "warning")
        assert hasattr(websocket_logger, "error")
        assert hasattr(websocket_logger, "debug")

    def test_auth_logger_creation(self):
        """Test authentication logger is properly created."""
        assert auth_logger is not None
        assert hasattr(auth_logger, "info")
        assert hasattr(auth_logger, "warning")
        assert hasattr(auth_logger, "error")
        assert hasattr(auth_logger, "debug")


class TestAPILogging:
    """Test API logging functions."""

    @patch("cc_orchestrator.web.logging_utils.api_logger")
    def test_log_api_request_basic(self, mock_logger):
        """Test basic API request logging."""
        log_api_request(method="GET", path="/api/v1/instances", client_ip="192.168.1.1")

        mock_logger.info.assert_called_once_with(
            "API request received",
            method="GET",
            path="/api/v1/instances",
            client_ip="192.168.1.1",
            user_agent=None,
            request_id=None,
        )

    @patch("cc_orchestrator.web.logging_utils.api_logger")
    def test_log_api_request_with_optional_params(self, mock_logger):
        """Test API request logging with optional parameters."""
        log_api_request(
            method="POST",
            path="/api/v1/instances",
            client_ip="10.0.0.1",
            user_agent="Mozilla/5.0",
            request_id="req-123",
        )

        mock_logger.info.assert_called_once_with(
            "API request received",
            method="POST",
            path="/api/v1/instances",
            client_ip="10.0.0.1",
            user_agent="Mozilla/5.0",
            request_id="req-123",
        )

    @patch("cc_orchestrator.web.logging_utils.api_logger")
    def test_log_api_response_success(self, mock_logger):
        """Test API response logging for successful responses."""
        log_api_response(
            method="GET",
            path="/api/v1/instances",
            status_code=200,
            response_time_ms=45.7,
        )

        mock_logger.info.assert_called_once_with(
            "API response sent",
            method="GET",
            path="/api/v1/instances",
            status_code=200,
            response_time_ms=45.7,
            request_id=None,
        )

    @patch("cc_orchestrator.web.logging_utils.api_logger")
    def test_log_api_response_error(self, mock_logger):
        """Test API response logging for error responses."""
        log_api_response(
            method="POST",
            path="/api/v1/instances",
            status_code=400,
            response_time_ms=123.4,
            request_id="req-456",
        )

        mock_logger.warning.assert_called_once_with(
            "API response sent",
            method="POST",
            path="/api/v1/instances",
            status_code=400,
            response_time_ms=123.4,
            request_id="req-456",
        )

    @patch("cc_orchestrator.web.logging_utils.api_logger")
    def test_log_api_response_server_error(self, mock_logger):
        """Test API response logging for server errors."""
        log_api_response(
            method="GET",
            path="/api/v1/instances/1",
            status_code=500,
            response_time_ms=1000.0,
        )

        mock_logger.warning.assert_called_once()

    @patch("cc_orchestrator.web.logging_utils.api_logger")
    def test_log_api_response_different_status_codes(self, mock_logger):
        """Test API response logging with different status codes."""
        test_cases = [
            (200, "info"),
            (201, "info"),
            (299, "info"),
            (300, "warning"),
            (400, "warning"),
            (404, "warning"),
            (500, "warning"),
        ]

        for status_code, expected_level in test_cases:
            mock_logger.reset_mock()

            log_api_response("GET", "/test", status_code, 100.0)

            expected_method = getattr(mock_logger, expected_level)
            expected_method.assert_called_once()

    @patch("cc_orchestrator.web.logging_utils.api_logger")
    def test_log_dashboard_access(self, mock_logger):
        """Test dashboard access logging."""
        log_dashboard_access(
            client_ip="192.168.1.1", user_agent="Chrome/90.0", session_id="sess-123"
        )

        mock_logger.info.assert_called_once_with(
            "Dashboard accessed",
            client_ip="192.168.1.1",
            user_agent="Chrome/90.0",
            session_id="sess-123",
        )

    @patch("cc_orchestrator.web.logging_utils.api_logger")
    def test_log_dashboard_access_without_session(self, mock_logger):
        """Test dashboard access logging without session ID."""
        log_dashboard_access(client_ip="10.0.0.1", user_agent="Firefox/88.0")

        mock_logger.info.assert_called_once_with(
            "Dashboard accessed",
            client_ip="10.0.0.1",
            user_agent="Firefox/88.0",
            session_id=None,
        )


class TestWebSocketLogging:
    """Test WebSocket logging functions."""

    @patch("cc_orchestrator.web.logging_utils.websocket_logger")
    def test_log_websocket_connection_connect(self, mock_logger):
        """Test WebSocket connection logging."""
        log_websocket_connection(
            client_ip="192.168.1.1", action="connect", connection_id="conn-123"
        )

        mock_logger.info.assert_called_once_with(
            "WebSocket connect",
            action="connect",
            client_ip="192.168.1.1",
            connection_id="conn-123",
            reason=None,
        )

    @patch("cc_orchestrator.web.logging_utils.websocket_logger")
    def test_log_websocket_connection_disconnect(self, mock_logger):
        """Test WebSocket disconnection logging."""
        log_websocket_connection(
            client_ip="192.168.1.1",
            action="disconnect",
            connection_id="conn-123",
            reason="Client closed connection",
        )

        mock_logger.info.assert_called_once_with(
            "WebSocket disconnect",
            action="disconnect",
            client_ip="192.168.1.1",
            connection_id="conn-123",
            reason="Client closed connection",
        )

    @patch("cc_orchestrator.web.logging_utils.websocket_logger")
    def test_log_websocket_message_inbound(self, mock_logger):
        """Test WebSocket inbound message logging."""
        log_websocket_message(
            connection_id="conn-456",
            message_type="status_update",
            direction="inbound",
            message_size=1024,
        )

        mock_logger.debug.assert_called_once_with(
            "WebSocket message inbound",
            connection_id="conn-456",
            message_type="status_update",
            direction="inbound",
            message_size=1024,
        )

    @patch("cc_orchestrator.web.logging_utils.websocket_logger")
    def test_log_websocket_message_outbound(self, mock_logger):
        """Test WebSocket outbound message logging."""
        log_websocket_message(
            connection_id="conn-789",
            message_type="heartbeat",
            direction="outbound",
            message_size=64,
        )

        mock_logger.debug.assert_called_once_with(
            "WebSocket message outbound",
            connection_id="conn-789",
            message_type="heartbeat",
            direction="outbound",
            message_size=64,
        )

    @patch("cc_orchestrator.web.logging_utils.get_logger")
    def test_log_real_time_event_basic(self, mock_get_logger):
        """Test basic real-time event logging."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        log_real_time_event(
            event_type="instance_status_changed", target_connections=5, payload_size=512
        )

        mock_logger.debug.assert_called_once_with(
            "Real-time event broadcast",
            event_type="instance_status_changed",
            target_connections=5,
            payload_size=512,
        )

    @patch("cc_orchestrator.web.logging_utils.get_logger")
    def test_log_real_time_event_with_ids(self, mock_get_logger):
        """Test real-time event logging with instance and task IDs."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        log_real_time_event(
            event_type="task_completed",
            target_connections=3,
            payload_size=256,
            instance_id="inst-123",
            task_id="task-456",
        )

        # Verify logger context was set
        mock_logger.set_instance_id.assert_called_once_with("inst-123")
        mock_logger.set_task_id.assert_called_once_with("task-456")

        mock_logger.debug.assert_called_once_with(
            "Real-time event broadcast",
            event_type="task_completed",
            target_connections=3,
            payload_size=256,
        )

    @patch("cc_orchestrator.web.logging_utils.get_logger")
    def test_log_real_time_event_only_instance_id(self, mock_get_logger):
        """Test real-time event logging with only instance ID."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        log_real_time_event(
            event_type="instance_created",
            target_connections=10,
            payload_size=128,
            instance_id="inst-789",
        )

        mock_logger.set_instance_id.assert_called_once_with("inst-789")
        # set_task_id should not be called
        mock_logger.set_task_id.assert_not_called()


class TestAuthenticationLogging:
    """Test authentication and authorization logging functions."""

    @patch("cc_orchestrator.web.logging_utils.auth_logger")
    def test_log_authentication_attempt_success(self, mock_logger):
        """Test successful authentication attempt logging."""
        log_authentication_attempt(
            auth_method="jwt", client_ip="192.168.1.1", success=True, user_id="user123"
        )

        mock_logger.info.assert_called_once_with(
            "Authentication successful",
            auth_method="jwt",
            client_ip="192.168.1.1",
            user_id="user123",
        )

    @patch("cc_orchestrator.web.logging_utils.auth_logger")
    def test_log_authentication_attempt_failure(self, mock_logger):
        """Test failed authentication attempt logging."""
        log_authentication_attempt(
            auth_method="jwt",
            client_ip="10.0.0.1",
            success=False,
            reason="Invalid token",
        )

        mock_logger.warning.assert_called_once_with(
            "Authentication failed",
            auth_method="jwt",
            client_ip="10.0.0.1",
            reason="Invalid token",
        )

    @patch("cc_orchestrator.web.logging_utils.auth_logger")
    def test_log_authentication_attempt_success_without_user_id(self, mock_logger):
        """Test authentication success without user ID."""
        log_authentication_attempt(
            auth_method="basic", client_ip="127.0.0.1", success=True
        )

        mock_logger.info.assert_called_once_with(
            "Authentication successful",
            auth_method="basic",
            client_ip="127.0.0.1",
            user_id=None,
        )

    @patch("cc_orchestrator.web.logging_utils.auth_logger")
    def test_log_authorization_check_allowed(self, mock_logger):
        """Test authorization check logging when allowed."""
        log_authorization_check(
            user_id="user123", resource="/api/v1/instances", action="read", allowed=True
        )

        mock_logger.debug.assert_called_once_with(
            "Authorization granted",
            user_id="user123",
            resource="/api/v1/instances",
            action="read",
        )

    @patch("cc_orchestrator.web.logging_utils.auth_logger")
    def test_log_authorization_check_denied(self, mock_logger):
        """Test authorization check logging when denied."""
        log_authorization_check(
            user_id="user456",
            resource="/api/v1/admin",
            action="write",
            allowed=False,
            reason="Insufficient permissions",
        )

        mock_logger.warning.assert_called_once_with(
            "Authorization denied",
            user_id="user456",
            resource="/api/v1/admin",
            action="write",
            reason="Insufficient permissions",
        )

    @patch("cc_orchestrator.web.logging_utils.auth_logger")
    def test_log_authorization_check_denied_without_reason(self, mock_logger):
        """Test authorization denial without specific reason."""
        log_authorization_check(
            user_id="user789", resource="/api/v1/secret", action="delete", allowed=False
        )

        mock_logger.warning.assert_called_once_with(
            "Authorization denied",
            user_id="user789",
            resource="/api/v1/secret",
            action="delete",
            reason=None,
        )


class TestLoggingDecorators:
    """Test logging decorator functions."""

    def test_handle_api_errors_decorator(self):
        """Test API error handling decorator."""
        # Test that handle_api_errors returns a decorator function
        result = handle_api_errors()
        assert callable(result)

        # Test that the decorator returns a wrapper function
        @result
        def test_func():
            return "success"

        wrapper = result(test_func)
        assert callable(wrapper)
        assert wrapper() == "success"

    def test_handle_api_errors_decorator_with_recovery(self):
        """Test API error handling decorator with recovery strategy."""
        recovery_func = Mock(return_value="recovered")

        # Test that handle_api_errors with recovery returns a decorator function
        result = handle_api_errors(recovery_strategy=recovery_func)
        assert callable(result)

        # Test that the decorator returns a wrapper function
        @result
        def test_func():
            raise ValueError("test error")

        wrapper = result(test_func)
        assert callable(wrapper)

        # Test that recovery function is called on exception
        recovered_result = wrapper()
        assert recovered_result == "recovered"

    def test_track_api_performance_decorator(self):
        """Test API performance tracking decorator."""
        # Test that track_api_performance returns a decorator function
        result = track_api_performance()
        assert callable(result)

        # Test that the decorator returns a wrapper function
        @result
        def test_func():
            return "success"

        wrapper = result(test_func)
        assert callable(wrapper)
        assert wrapper() == "success"


class TestLoggingEdgeCases:
    """Test edge cases and error conditions in logging."""

    @patch("cc_orchestrator.web.logging_utils.api_logger")
    def test_logging_with_none_values(self, mock_logger):
        """Test logging functions with None values."""
        log_api_request(method=None, path=None, client_ip=None)

        mock_logger.info.assert_called_once_with(
            "API request received",
            method=None,
            path=None,
            client_ip=None,
            user_agent=None,
            request_id=None,
        )

    @patch("cc_orchestrator.web.logging_utils.api_logger")
    def test_logging_with_empty_strings(self, mock_logger):
        """Test logging functions with empty strings."""
        log_api_request(method="", path="", client_ip="")

        mock_logger.info.assert_called_once_with(
            "API request received",
            method="",
            path="",
            client_ip="",
            user_agent=None,
            request_id=None,
        )

    @patch("cc_orchestrator.web.logging_utils.websocket_logger")
    def test_logging_with_special_characters(self, mock_logger):
        """Test logging with special characters."""
        log_websocket_connection(
            client_ip="192.168.1.1",
            action="connect",
            connection_id="conn-ñ-中文-🚀",
            reason="Special chars test",
        )

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert "conn-ñ-中文-🚀" in call_args[1].values()

    @patch("cc_orchestrator.web.logging_utils.auth_logger")
    def test_logging_with_very_long_strings(self, mock_logger):
        """Test logging with very long strings."""
        long_string = "A" * 10000

        log_authentication_attempt(
            auth_method=long_string,
            client_ip="192.168.1.1",
            success=True,
            user_id=long_string,
        )

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert long_string in call_args[1].values()

    @patch("cc_orchestrator.web.logging_utils.api_logger")
    def test_logging_with_numeric_edge_cases(self, mock_logger):
        """Test logging with numeric edge cases."""
        log_api_response(
            method="GET", path="/test", status_code=0, response_time_ms=-1.0
        )

        mock_logger.warning.assert_called_once_with(
            "API response sent",
            method="GET",
            path="/test",
            status_code=0,
            response_time_ms=-1.0,
            request_id=None,
        )

    @patch("cc_orchestrator.web.logging_utils.websocket_logger")
    def test_logging_with_zero_message_size(self, mock_logger):
        """Test WebSocket message logging with zero size."""
        log_websocket_message(
            connection_id="conn-test",
            message_type="empty",
            direction="inbound",
            message_size=0,
        )

        mock_logger.debug.assert_called_once_with(
            "WebSocket message inbound",
            connection_id="conn-test",
            message_type="empty",
            direction="inbound",
            message_size=0,
        )

    @patch("cc_orchestrator.web.logging_utils.get_logger")
    def test_real_time_event_with_zero_connections(self, mock_get_logger):
        """Test real-time event logging with zero target connections."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        log_real_time_event(
            event_type="no_subscribers", target_connections=0, payload_size=100
        )

        mock_logger.debug.assert_called_once_with(
            "Real-time event broadcast",
            event_type="no_subscribers",
            target_connections=0,
            payload_size=100,
        )


class TestLoggingIntegration:
    """Test logging integration scenarios."""

    @patch("cc_orchestrator.web.logging_utils.api_logger")
    def test_request_response_pair_logging(self, mock_logger):
        """Test logging request/response pairs."""
        request_id = "req-integration-test"

        # Log request
        log_api_request(
            method="POST",
            path="/api/v1/instances",
            client_ip="192.168.1.1",
            request_id=request_id,
        )

        # Log response
        log_api_response(
            method="POST",
            path="/api/v1/instances",
            status_code=201,
            response_time_ms=156.7,
            request_id=request_id,
        )

        # Verify both calls were made
        assert mock_logger.info.call_count == 2

        # Verify request_id was preserved
        all_calls = mock_logger.info.call_args_list
        for call in all_calls:
            assert call[1]["request_id"] == request_id

    @patch("cc_orchestrator.web.logging_utils.auth_logger")
    def test_authentication_authorization_flow(self, mock_logger):
        """Test authentication followed by authorization logging."""
        user_id = "test-user"

        # Successful authentication
        log_authentication_attempt(
            auth_method="jwt", client_ip="192.168.1.1", success=True, user_id=user_id
        )

        # Successful authorization
        log_authorization_check(
            user_id=user_id, resource="/api/v1/instances", action="read", allowed=True
        )

        # Verify calls
        mock_logger.info.assert_called_once()
        mock_logger.debug.assert_called_once()

        # Verify user_id consistency
        info_call = mock_logger.info.call_args[1]
        debug_call = mock_logger.debug.call_args[1]
        assert info_call["user_id"] == debug_call["user_id"] == user_id
