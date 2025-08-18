"""Comprehensive tests for custom exceptions."""

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
    """Test base exception class."""

    def test_base_exception_creation(self):
        """Test base exception initialization."""
        exc = CCOrchestratorAPIException("Test error")

        assert str(exc) == "Test error"
        assert exc.message == "Test error"
        assert exc.status_code == 500  # default

    def test_base_exception_with_status_code(self):
        """Test base exception with custom status code."""
        exc = CCOrchestratorAPIException("Test error", 418)

        assert str(exc) == "Test error"
        assert exc.message == "Test error"
        assert exc.status_code == 418

    def test_base_exception_inheritance(self):
        """Test base exception inherits from Exception."""
        exc = CCOrchestratorAPIException("Test error")

        assert isinstance(exc, Exception)
        assert isinstance(exc, CCOrchestratorAPIException)


class TestInstanceNotFoundError:
    """Test InstanceNotFoundError exception."""

    def test_instance_not_found_creation(self):
        """Test InstanceNotFoundError initialization."""
        exc = InstanceNotFoundError(123)

        assert str(exc) == "Instance 123 not found"
        assert exc.message == "Instance 123 not found"
        assert exc.status_code == 404
        assert exc.instance_id == 123

    def test_instance_not_found_inheritance(self):
        """Test InstanceNotFoundError inheritance."""
        exc = InstanceNotFoundError(456)

        assert isinstance(exc, CCOrchestratorAPIException)
        assert isinstance(exc, InstanceNotFoundError)

    def test_instance_not_found_different_ids(self):
        """Test InstanceNotFoundError with different instance IDs."""
        exc1 = InstanceNotFoundError(1)
        exc2 = InstanceNotFoundError(999999)

        assert exc1.instance_id == 1
        assert exc2.instance_id == 999999
        assert "Instance 1 not found" in str(exc1)
        assert "Instance 999999 not found" in str(exc2)


class TestInstanceOperationError:
    """Test InstanceOperationError exception."""

    def test_instance_operation_error_creation(self):
        """Test InstanceOperationError initialization."""
        exc = InstanceOperationError("Operation failed", 123)

        assert str(exc) == "Operation failed"
        assert exc.message == "Operation failed"
        assert exc.status_code == 400
        assert exc.instance_id == 123

    def test_instance_operation_error_different_messages(self):
        """Test InstanceOperationError with different messages."""
        exc1 = InstanceOperationError("Start failed", 1)
        exc2 = InstanceOperationError("Stop failed", 2)

        assert str(exc1) == "Start failed"
        assert str(exc2) == "Stop failed"
        assert exc1.instance_id == 1
        assert exc2.instance_id == 2

    def test_instance_operation_error_inheritance(self):
        """Test InstanceOperationError inheritance."""
        exc = InstanceOperationError("Test", 1)

        assert isinstance(exc, CCOrchestratorAPIException)
        assert isinstance(exc, InstanceOperationError)


class TestInvalidInstanceStatusError:
    """Test InvalidInstanceStatusError exception."""

    def test_invalid_status_error_creation(self):
        """Test InvalidInstanceStatusError initialization."""
        exc = InvalidInstanceStatusError("STOPPED", "start")

        expected_message = "Cannot start instance in STOPPED status"
        assert str(exc) == expected_message
        assert exc.message == expected_message
        assert exc.status_code == 400
        assert exc.current_status == "STOPPED"
        assert exc.requested_operation == "start"

    def test_invalid_status_error_different_operations(self):
        """Test InvalidInstanceStatusError with different operations."""
        exc1 = InvalidInstanceStatusError("RUNNING", "start")
        exc2 = InvalidInstanceStatusError("INITIALIZING", "restart")

        assert "Cannot start instance in RUNNING status" in str(exc1)
        assert "Cannot restart instance in INITIALIZING status" in str(exc2)
        assert exc1.current_status == "RUNNING"
        assert exc2.current_status == "INITIALIZING"

    def test_invalid_status_error_inheritance(self):
        """Test InvalidInstanceStatusError inheritance."""
        exc = InvalidInstanceStatusError("TEST", "operation")

        assert isinstance(exc, CCOrchestratorAPIException)
        assert isinstance(exc, InvalidInstanceStatusError)


class TestDatabaseOperationError:
    """Test DatabaseOperationError exception."""

    def test_database_error_creation(self):
        """Test DatabaseOperationError initialization."""
        exc = DatabaseOperationError("insert")

        expected_message = "Database operation 'insert' failed"
        assert str(exc) == expected_message
        assert exc.message == expected_message
        assert exc.status_code == 500
        assert exc.operation == "insert"
        assert exc.details == ""

    def test_database_error_with_details(self):
        """Test DatabaseOperationError with details."""
        exc = DatabaseOperationError("update", "connection timeout")

        expected_message = "Database operation 'update' failed: connection timeout"
        assert str(exc) == expected_message
        assert exc.message == expected_message
        assert exc.operation == "update"
        assert exc.details == "connection timeout"

    def test_database_error_empty_details(self):
        """Test DatabaseOperationError with empty details."""
        exc = DatabaseOperationError("delete", "")

        expected_message = "Database operation 'delete' failed"
        assert str(exc) == expected_message
        assert exc.details == ""

    def test_database_error_inheritance(self):
        """Test DatabaseOperationError inheritance."""
        exc = DatabaseOperationError("test")

        assert isinstance(exc, CCOrchestratorAPIException)
        assert isinstance(exc, DatabaseOperationError)


class TestAuthenticationError:
    """Test AuthenticationError exception."""

    def test_authentication_error_default(self):
        """Test AuthenticationError with default message."""
        exc = AuthenticationError()

        assert str(exc) == "Authentication failed"
        assert exc.message == "Authentication failed"
        assert exc.status_code == 401

    def test_authentication_error_custom_message(self):
        """Test AuthenticationError with custom message."""
        exc = AuthenticationError("Invalid token")

        assert str(exc) == "Invalid token"
        assert exc.message == "Invalid token"
        assert exc.status_code == 401

    def test_authentication_error_inheritance(self):
        """Test AuthenticationError inheritance."""
        exc = AuthenticationError()

        assert isinstance(exc, CCOrchestratorAPIException)
        assert isinstance(exc, AuthenticationError)


class TestAuthorizationError:
    """Test AuthorizationError exception."""

    def test_authorization_error_default(self):
        """Test AuthorizationError with default message."""
        exc = AuthorizationError()

        assert str(exc) == "Insufficient permissions"
        assert exc.message == "Insufficient permissions"
        assert exc.status_code == 403

    def test_authorization_error_custom_message(self):
        """Test AuthorizationError with custom message."""
        exc = AuthorizationError("Admin required")

        assert str(exc) == "Admin required"
        assert exc.message == "Admin required"
        assert exc.status_code == 403

    def test_authorization_error_inheritance(self):
        """Test AuthorizationError inheritance."""
        exc = AuthorizationError()

        assert isinstance(exc, CCOrchestratorAPIException)
        assert isinstance(exc, AuthorizationError)


class TestValidationError:
    """Test ValidationError exception."""

    def test_validation_error_creation(self):
        """Test ValidationError initialization."""
        exc = ValidationError("email", "Invalid format")

        expected_message = "Validation error for 'email': Invalid format"
        assert str(exc) == expected_message
        assert exc.message == expected_message
        assert exc.status_code == 400
        assert exc.field == "email"

    def test_validation_error_different_fields(self):
        """Test ValidationError with different fields."""
        exc1 = ValidationError("username", "Too short")
        exc2 = ValidationError("password", "Missing special character")

        assert "Validation error for 'username': Too short" in str(exc1)
        assert "Validation error for 'password': Missing special character" in str(exc2)
        assert exc1.field == "username"
        assert exc2.field == "password"

    def test_validation_error_inheritance(self):
        """Test ValidationError inheritance."""
        exc = ValidationError("field", "message")

        assert isinstance(exc, CCOrchestratorAPIException)
        assert isinstance(exc, ValidationError)


class TestRateLimitExceededError:
    """Test RateLimitExceededError exception."""

    def test_rate_limit_error_creation(self):
        """Test RateLimitExceededError initialization."""
        exc = RateLimitExceededError(30, "60s")

        expected_message = "Rate limit exceeded: 30 requests per 60s"
        assert str(exc) == expected_message
        assert exc.message == expected_message
        assert exc.status_code == 429
        assert exc.limit == 30
        assert exc.window == "60s"

    def test_rate_limit_error_different_limits(self):
        """Test RateLimitExceededError with different limits."""
        exc1 = RateLimitExceededError(10, "1min")
        exc2 = RateLimitExceededError(100, "1hour")

        assert "10 requests per 1min" in str(exc1)
        assert "100 requests per 1hour" in str(exc2)
        assert exc1.limit == 10
        assert exc2.limit == 100

    def test_rate_limit_error_inheritance(self):
        """Test RateLimitExceededError inheritance."""
        exc = RateLimitExceededError(5, "test")

        assert isinstance(exc, CCOrchestratorAPIException)
        assert isinstance(exc, RateLimitExceededError)


class TestWebSocketConnectionError:
    """Test WebSocketConnectionError exception."""

    def test_websocket_error_creation(self):
        """Test WebSocketConnectionError initialization."""
        exc = WebSocketConnectionError("Connection refused")

        expected_message = "WebSocket connection error: Connection refused"
        assert str(exc) == expected_message
        assert exc.message == expected_message
        assert exc.status_code == 400
        assert exc.reason == "Connection refused"

    def test_websocket_error_different_reasons(self):
        """Test WebSocketConnectionError with different reasons."""
        exc1 = WebSocketConnectionError("Timeout")
        exc2 = WebSocketConnectionError("Authentication failed")

        assert "WebSocket connection error: Timeout" in str(exc1)
        assert "WebSocket connection error: Authentication failed" in str(exc2)
        assert exc1.reason == "Timeout"
        assert exc2.reason == "Authentication failed"

    def test_websocket_error_inheritance(self):
        """Test WebSocketConnectionError inheritance."""
        exc = WebSocketConnectionError("test")

        assert isinstance(exc, CCOrchestratorAPIException)
        assert isinstance(exc, WebSocketConnectionError)


class TestExceptionEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_string_parameters(self):
        """Test exceptions with empty string parameters."""
        exc1 = AuthenticationError("")
        exc2 = ValidationError("", "")
        exc3 = DatabaseOperationError("")
        exc4 = WebSocketConnectionError("")

        assert exc1.message == ""
        assert exc2.field == ""
        assert exc3.operation == ""
        assert exc4.reason == ""

    def test_very_long_messages(self):
        """Test exceptions with very long messages."""
        long_message = "A" * 1000

        exc1 = CCOrchestratorAPIException(long_message)
        exc2 = AuthenticationError(long_message)
        exc3 = ValidationError("field", long_message)

        assert len(exc1.message) == 1000
        assert len(exc2.message) == 1000
        assert long_message in exc3.message

    def test_special_characters_in_messages(self):
        """Test exceptions with special characters."""
        special_message = "Error with ñ, 中文, emoji 🚀, and symbols !@#$%"

        exc = CCOrchestratorAPIException(special_message)

        assert exc.message == special_message
        assert str(exc) == special_message

    def test_numeric_parameters(self):
        """Test exceptions with various numeric parameters."""
        exc1 = InstanceNotFoundError(0)
        exc2 = InstanceNotFoundError(-1)
        exc3 = InstanceNotFoundError(999999999)
        exc4 = RateLimitExceededError(0, "test")
        exc5 = RateLimitExceededError(9999, "test")

        assert exc1.instance_id == 0
        assert exc2.instance_id == -1
        assert exc3.instance_id == 999999999
        assert exc4.limit == 0
        assert exc5.limit == 9999

    def test_exception_chaining(self):
        """Test exception chaining behavior."""
        try:
            raise ValueError("Original error")
        except ValueError as e:
            # Chain exceptions
            new_exc = DatabaseOperationError("Wrapped error", str(e))

            assert new_exc.operation == "Wrapped error"
            assert new_exc.details == "Original error"

    def test_exception_equality(self):
        """Test exception equality comparisons."""
        exc1 = InstanceNotFoundError(123)
        exc2 = InstanceNotFoundError(123)
        exc3 = InstanceNotFoundError(456)

        # Different instances should not be equal even with same parameters
        assert exc1 is not exc2
        assert exc1.instance_id == exc2.instance_id
        assert exc1.instance_id != exc3.instance_id

    def test_exception_str_vs_repr(self):
        """Test string representation vs repr."""
        exc = ValidationError("test_field", "test_message")

        str_repr = str(exc)
        # Should contain the formatted message
        assert "Validation error for 'test_field': test_message" in str_repr
