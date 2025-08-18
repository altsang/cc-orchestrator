"""Focused tests for web exceptions to improve coverage."""

from cc_orchestrator.web.exceptions import (
    AuthenticationError,
    AuthorizationError,
    CCOrchestratorAPIException,
    DatabaseOperationError,
    InstanceNotFoundError,
    InstanceOperationError,
    InvalidInstanceStatusError,
    RateLimitExceededError,
    ValidationError,
    WebSocketConnectionError,
)


class TestCCOrchestratorAPIException:
    """Test base CCOrchestratorAPIException."""

    def test_base_exception_creation(self):
        """Test basic CCOrchestratorAPIException creation."""
        error = CCOrchestratorAPIException("Test message", 400)

        assert isinstance(error, Exception)
        assert error.message == "Test message"
        assert error.status_code == 400
        assert str(error) == "Test message"

    def test_base_exception_default_status(self):
        """Test CCOrchestratorAPIException with default status code."""
        error = CCOrchestratorAPIException("Test message")

        assert error.message == "Test message"
        assert error.status_code == 500


class TestAuthenticationError:
    """Test AuthenticationError exception."""

    def test_authentication_error_basic(self):
        """Test basic AuthenticationError creation."""
        error = AuthenticationError("Invalid credentials")

        assert isinstance(error, CCOrchestratorAPIException)
        assert error.message == "Invalid credentials"
        assert error.status_code == 401

    def test_authentication_error_default_message(self):
        """Test AuthenticationError with default message."""
        error = AuthenticationError()

        assert error.status_code == 401
        assert error.message == "Authentication failed"


class TestAuthorizationError:
    """Test AuthorizationError exception."""

    def test_authorization_error_basic(self):
        """Test basic AuthorizationError creation."""
        error = AuthorizationError("Insufficient permissions")

        assert isinstance(error, CCOrchestratorAPIException)
        assert error.message == "Insufficient permissions"
        assert error.status_code == 403

    def test_authorization_error_default_message(self):
        """Test AuthorizationError with default message."""
        error = AuthorizationError()

        assert error.status_code == 403
        assert error.message == "Insufficient permissions"


class TestValidationError:
    """Test ValidationError exception."""

    def test_validation_error_basic(self):
        """Test basic ValidationError creation."""
        error = ValidationError("email", "Invalid format")

        assert isinstance(error, CCOrchestratorAPIException)
        assert error.status_code == 400
        assert "email" in error.message
        assert "Invalid format" in error.message
        assert error.field == "email"

    def test_validation_error_message_format(self):
        """Test ValidationError message formatting."""
        error = ValidationError("username", "Too short")

        assert "Validation error for 'username': Too short" == error.message


class TestRateLimitExceededError:
    """Test RateLimitExceededError exception."""

    def test_rate_limit_error_basic(self):
        """Test basic RateLimitExceededError creation."""
        error = RateLimitExceededError(60, "minute")

        assert isinstance(error, CCOrchestratorAPIException)
        assert error.status_code == 429
        assert error.limit == 60
        assert error.window == "minute"
        assert "60" in error.message
        assert "minute" in error.message

    def test_rate_limit_error_message_format(self):
        """Test RateLimitExceededError message formatting."""
        error = RateLimitExceededError(100, "hour")

        expected_message = "Rate limit exceeded: 100 requests per hour"
        assert error.message == expected_message


class TestInstanceNotFoundError:
    """Test InstanceNotFoundError exception."""

    def test_instance_not_found_error_basic(self):
        """Test basic InstanceNotFoundError creation."""
        error = InstanceNotFoundError(123)

        assert isinstance(error, CCOrchestratorAPIException)
        assert error.status_code == 404
        assert error.instance_id == 123
        assert "Instance 123 not found" == error.message

    def test_instance_not_found_error_string_id(self):
        """Test InstanceNotFoundError with string ID."""
        error = InstanceNotFoundError("abc-123")

        assert error.status_code == 404
        assert error.instance_id == "abc-123"
        assert "Instance abc-123 not found" == error.message


class TestInstanceOperationError:
    """Test InstanceOperationError exception."""

    def test_instance_operation_error_basic(self):
        """Test basic InstanceOperationError creation."""
        error = InstanceOperationError("Failed to start", 789)

        assert isinstance(error, CCOrchestratorAPIException)
        assert error.status_code == 400
        assert error.message == "Failed to start"
        assert error.instance_id == 789

    def test_instance_operation_error_different_messages(self):
        """Test InstanceOperationError with different messages."""
        test_cases = [
            ("Stop operation failed", 456),
            ("Restart timeout", 789),
            ("Configuration error", 101),
        ]

        for message, instance_id in test_cases:
            error = InstanceOperationError(message, instance_id)
            assert error.message == message
            assert error.instance_id == instance_id


class TestInvalidInstanceStatusError:
    """Test InvalidInstanceStatusError exception."""

    def test_invalid_status_error_basic(self):
        """Test basic InvalidInstanceStatusError creation."""
        error = InvalidInstanceStatusError("stopped", "restart")

        assert isinstance(error, CCOrchestratorAPIException)
        assert error.status_code == 400
        assert error.current_status == "stopped"
        assert error.requested_operation == "restart"
        assert "Cannot restart instance in stopped status" == error.message

    def test_invalid_status_error_different_combinations(self):
        """Test InvalidInstanceStatusError with different status combinations."""
        test_cases = [
            ("running", "start", "Cannot start instance in running status"),
            ("error", "stop", "Cannot stop instance in error status"),
            (
                "initializing",
                "restart",
                "Cannot restart instance in initializing status",
            ),
        ]

        for current, operation, expected_message in test_cases:
            error = InvalidInstanceStatusError(current, operation)
            assert error.message == expected_message


class TestDatabaseOperationError:
    """Test DatabaseOperationError exception."""

    def test_database_error_basic(self):
        """Test basic DatabaseOperationError creation."""
        error = DatabaseOperationError("create_user")

        assert isinstance(error, CCOrchestratorAPIException)
        assert error.status_code == 500
        assert error.operation == "create_user"
        assert error.details == ""
        assert "Database operation 'create_user' failed" == error.message

    def test_database_error_with_details(self):
        """Test DatabaseOperationError with details."""
        error = DatabaseOperationError("update_record", "Connection timeout")

        assert error.operation == "update_record"
        assert error.details == "Connection timeout"
        expected_message = (
            "Database operation 'update_record' failed: Connection timeout"
        )
        assert error.message == expected_message

    def test_database_error_empty_details(self):
        """Test DatabaseOperationError with empty details."""
        error = DatabaseOperationError("delete_item", "")

        assert error.details == ""
        assert "Database operation 'delete_item' failed" == error.message


class TestWebSocketConnectionError:
    """Test WebSocketConnectionError exception."""

    def test_websocket_connection_error_basic(self):
        """Test basic WebSocketConnectionError creation."""
        error = WebSocketConnectionError("Authentication failed")

        assert isinstance(error, CCOrchestratorAPIException)
        assert error.status_code == 400
        assert error.reason == "Authentication failed"
        expected_message = "WebSocket connection error: Authentication failed"
        assert error.message == expected_message

    def test_websocket_connection_error_various_reasons(self):
        """Test WebSocketConnectionError with various reasons."""
        reasons = [
            "Protocol mismatch",
            "Connection timeout",
            "Invalid handshake",
            "Rate limit exceeded",
        ]

        for reason in reasons:
            error = WebSocketConnectionError(reason)
            assert error.reason == reason
            assert f"WebSocket connection error: {reason}" == error.message


class TestExceptionInheritance:
    """Test that all custom exceptions inherit from CCOrchestratorAPIException."""

    def test_all_exceptions_inherit_base_exception(self):
        """Test that all custom exceptions inherit from CCOrchestratorAPIException."""
        exceptions = [
            AuthenticationError(),
            AuthorizationError(),
            ValidationError("field", "message"),
            RateLimitExceededError(10, "test"),
            InstanceNotFoundError(1),
            InstanceOperationError("test", 2),
            InvalidInstanceStatusError("status", "operation"),
            DatabaseOperationError("operation"),
            WebSocketConnectionError("reason"),
        ]

        for exc in exceptions:
            assert isinstance(exc, CCOrchestratorAPIException)
            assert hasattr(exc, "message")
            assert hasattr(exc, "status_code")


class TestExceptionStatusCodes:
    """Test that exceptions have correct HTTP status codes."""

    def test_status_codes_are_correct(self):
        """Test that all exceptions have appropriate HTTP status codes."""
        test_cases = [
            (AuthenticationError(), 401),
            (AuthorizationError(), 403),
            (ValidationError("field", "message"), 400),
            (RateLimitExceededError(10, "test"), 429),
            (InstanceNotFoundError(1), 404),
            (InstanceOperationError("test", 2), 400),
            (InvalidInstanceStatusError("status", "operation"), 400),
            (DatabaseOperationError("operation"), 500),
            (WebSocketConnectionError("reason"), 400),
        ]

        for exception, expected_code in test_cases:
            assert exception.status_code == expected_code


class TestExceptionStringRepresentation:
    """Test string representations of exceptions."""

    def test_exception_str_representations(self):
        """Test that exceptions have meaningful string representations."""
        exceptions = [
            (AuthenticationError("test auth"), "test auth"),
            (AuthorizationError("test authz"), "test authz"),
            (
                ValidationError("field", "test validation"),
                "Validation error for 'field': test validation",
            ),
            (
                RateLimitExceededError(10, "test window"),
                "Rate limit exceeded: 10 requests per test window",
            ),
            (InstanceNotFoundError(123), "Instance 123 not found"),
            (InstanceOperationError("test op", 456), "test op"),
            (
                WebSocketConnectionError("test ws"),
                "WebSocket connection error: test ws",
            ),
        ]

        for exc, expected_str in exceptions:
            assert str(exc) == expected_str
