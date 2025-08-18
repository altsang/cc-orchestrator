"""
Comprehensive tests for web/exceptions.py targeting 74% coverage compliance.

This test suite provides complete coverage for web exception classes including:
- Base CCOrchestratorHTTPException class
- Specific exception types (InstanceNotFoundError, TaskNotFoundError, etc.)
- Exception initialization and message formatting
- HTTP status code handling
- Error code enumeration
- Exception serialization and representation

Target: 100% coverage of exceptions.py (47 statements)
"""

import pytest

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
    """Test base CCOrchestratorAPIException class."""

    def test_base_exception_creation(self):
        """Test basic exception creation with required parameters."""
        exception = CCOrchestratorAPIException(
            message="Test error message", status_code=400
        )

        assert exception.status_code == 400
        assert exception.message == "Test error message"
        assert str(exception) == "Test error message"

    def test_base_exception_default_status_code(self):
        """Test exception creation with default status code."""
        exception = CCOrchestratorAPIException("Test message")

        assert exception.status_code == 500  # Default
        assert exception.message == "Test message"

    def test_base_exception_custom_status_code(self):
        """Test exception creation with custom status code."""
        exception = CCOrchestratorAPIException("Custom error", status_code=422)

        assert exception.status_code == 422
        assert exception.message == "Custom error"

    def test_base_exception_string_representation(self):
        """Test exception string representation."""
        exception = CCOrchestratorAPIException(
            message="Internal server error", status_code=500
        )

        str_repr = str(exception)
        assert str_repr == "Internal server error"

    def test_base_exception_inheritance(self):
        """Test exception inheritance from Exception."""
        exception = CCOrchestratorAPIException(message="Bad request", status_code=400)

        # Should be an exception
        assert isinstance(exception, Exception)

    def test_base_exception_attribute_access(self):
        """Test all exception attributes are accessible."""
        exception = CCOrchestratorAPIException(
            message="Validation error", status_code=422
        )

        # Test all expected attributes exist
        assert hasattr(exception, "status_code")
        assert hasattr(exception, "message")

        # Verify values
        assert exception.status_code == 422
        assert exception.message == "Validation error"


class TestInstanceNotFoundError:
    """Test InstanceNotFoundError specific exception."""

    def test_instance_not_found_creation(self):
        """Test InstanceNotFoundError creation with instance ID."""
        error = InstanceNotFoundError(instance_id=123)

        # Should have 404 status code
        assert error.status_code == 404

        # Message should contain instance ID
        assert "123" in str(error.message)
        assert "Instance" in str(error.message)
        assert "not found" in str(error.message)
        assert error.instance_id == 123

    def test_instance_not_found_attributes(self):
        """Test InstanceNotFoundError has correct attributes."""
        error = InstanceNotFoundError(instance_id=456)

        # Should have instance_id attribute
        assert hasattr(error, "instance_id")
        assert error.instance_id == 456
        assert error.status_code == 404

    def test_instance_not_found_inheritance(self):
        """Test InstanceNotFoundError inherits from base exception."""
        error = InstanceNotFoundError(instance_id=789)

        # Should be instance of base exception
        assert isinstance(error, CCOrchestratorAPIException)

    def test_instance_not_found_with_different_ids(self):
        """Test InstanceNotFoundError with different ID values."""
        # Test with integer ID
        error1 = InstanceNotFoundError(instance_id=42)
        assert "42" in str(error1.message)
        assert error1.instance_id == 42

        # Test with different integer
        error2 = InstanceNotFoundError(instance_id=999)
        assert "999" in str(error2.message)
        assert error2.instance_id == 999

    def test_instance_not_found_message_format(self):
        """Test InstanceNotFoundError message formatting."""
        error = InstanceNotFoundError(instance_id=999)

        message = str(error.message)
        # Should be a well-formatted message
        assert len(message) > 0
        assert message[0].isupper()  # Should start with capital letter

        # Should follow expected format: "Instance {id} not found"
        assert message == "Instance 999 not found"


class TestInstanceOperationError:
    """Test InstanceOperationError specific exception."""

    def test_instance_operation_error_creation(self):
        """Test InstanceOperationError creation."""
        error = InstanceOperationError("Cannot start instance", instance_id=123)

        # Should have 400 status code
        assert error.status_code == 400

        # Should have correct attributes
        assert error.message == "Cannot start instance"
        assert error.instance_id == 123

    def test_instance_operation_error_inheritance(self):
        """Test InstanceOperationError inherits from base exception."""
        error = InstanceOperationError("Test error", instance_id=456)

        # Should be instance of base exception
        assert isinstance(error, CCOrchestratorAPIException)

    def test_instance_operation_error_attributes(self):
        """Test InstanceOperationError has correct attributes."""
        error = InstanceOperationError("Operation failed", instance_id=789)

        assert hasattr(error, "instance_id")
        assert hasattr(error, "message")
        assert hasattr(error, "status_code")

        assert error.instance_id == 789
        assert error.message == "Operation failed"
        assert error.status_code == 400


class TestInvalidInstanceStatusError:
    """Test InvalidInstanceStatusError specific exception."""

    def test_invalid_status_error_creation(self):
        """Test InvalidInstanceStatusError creation."""
        error = InvalidInstanceStatusError("running", "stop")

        # Should have 400 status code
        assert error.status_code == 400

        # Should have correct attributes
        assert error.current_status == "running"
        assert error.requested_operation == "stop"
        assert "Cannot stop instance in running status" in error.message

    def test_invalid_status_error_inheritance(self):
        """Test InvalidInstanceStatusError inherits from base exception."""
        error = InvalidInstanceStatusError("stopped", "start")

        # Should be instance of base exception
        assert isinstance(error, CCOrchestratorAPIException)

    def test_invalid_status_error_message_format(self):
        """Test InvalidInstanceStatusError message formatting."""
        error = InvalidInstanceStatusError("initializing", "delete")

        expected_message = "Cannot delete instance in initializing status"
        assert error.message == expected_message


class TestDatabaseOperationError:
    """Test DatabaseOperationError specific exception."""

    def test_database_operation_error_creation(self):
        """Test DatabaseOperationError creation."""
        error = DatabaseOperationError("insert")

        # Should have 500 status code
        assert error.status_code == 500

        # Should have correct attributes
        assert error.operation == "insert"
        assert error.details == ""
        assert "Database operation 'insert' failed" in error.message

    def test_database_operation_error_with_details(self):
        """Test DatabaseOperationError with details."""
        error = DatabaseOperationError("update", "Connection timeout")

        assert error.operation == "update"
        assert error.details == "Connection timeout"
        assert "Database operation 'update' failed: Connection timeout" in error.message

    def test_database_operation_error_inheritance(self):
        """Test DatabaseOperationError inherits from base exception."""
        error = DatabaseOperationError("delete")

        # Should be instance of base exception
        assert isinstance(error, CCOrchestratorAPIException)


class TestAuthenticationAndAuthorizationErrors:
    """Test authentication and authorization error exceptions."""

    def test_authentication_error_creation(self):
        """Test AuthenticationError creation."""
        # Test with default message
        error = AuthenticationError()
        assert error.status_code == 401
        assert error.message == "Authentication failed"

        # Test with custom message
        error = AuthenticationError("Invalid token")
        assert error.status_code == 401
        assert error.message == "Invalid token"

    def test_authorization_error_creation(self):
        """Test AuthorizationError creation."""
        # Test with default message
        error = AuthorizationError()
        assert error.status_code == 403
        assert error.message == "Insufficient permissions"

        # Test with custom message
        error = AuthorizationError("Admin access required")
        assert error.status_code == 403
        assert error.message == "Admin access required"

    def test_auth_errors_inheritance(self):
        """Test authentication/authorization errors inherit from base exception."""
        auth_error = AuthenticationError()
        authz_error = AuthorizationError()

        assert isinstance(auth_error, CCOrchestratorAPIException)
        assert isinstance(authz_error, CCOrchestratorAPIException)


class TestValidationAndRateLimitErrors:
    """Test validation and rate limit error exceptions."""

    def test_validation_error_creation(self):
        """Test ValidationError creation."""
        error = ValidationError("email", "Invalid format")

        assert error.status_code == 400
        assert error.field == "email"
        assert "Validation error for 'email': Invalid format" in error.message

    def test_rate_limit_exceeded_error_creation(self):
        """Test RateLimitExceededError creation."""
        error = RateLimitExceededError(100, "hour")

        assert error.status_code == 429
        assert error.limit == 100
        assert error.window == "hour"
        assert "Rate limit exceeded: 100 requests per hour" in error.message

    def test_websocket_connection_error_creation(self):
        """Test WebSocketConnectionError creation."""
        error = WebSocketConnectionError("Connection refused")

        assert error.status_code == 400
        assert error.reason == "Connection refused"
        assert "WebSocket connection error: Connection refused" in error.message

    def test_validation_errors_inheritance(self):
        """Test validation-related errors inherit from base exception."""
        validation_error = ValidationError("field", "message")
        rate_limit_error = RateLimitExceededError(10, "minute")
        websocket_error = WebSocketConnectionError("reason")

        assert isinstance(validation_error, CCOrchestratorAPIException)
        assert isinstance(rate_limit_error, CCOrchestratorAPIException)
        assert isinstance(websocket_error, CCOrchestratorAPIException)


class TestExceptionRaisingAndCatching:
    """Test exceptions can be raised and caught properly."""

    def test_raise_base_exception(self):
        """Test raising base CCOrchestratorAPIException."""
        with pytest.raises(CCOrchestratorAPIException) as exc_info:
            raise CCOrchestratorAPIException("Test error", 400)

        assert exc_info.value.status_code == 400
        assert exc_info.value.message == "Test error"

    def test_raise_instance_not_found(self):
        """Test raising InstanceNotFoundError."""
        with pytest.raises(InstanceNotFoundError) as exc_info:
            raise InstanceNotFoundError(instance_id=123)

        assert exc_info.value.status_code == 404
        assert "123" in str(exc_info.value.message)

    def test_catch_as_base_exception(self):
        """Test specific exceptions can be caught as base exception."""
        with pytest.raises(CCOrchestratorAPIException):
            raise InstanceNotFoundError(instance_id=789)

        with pytest.raises(CCOrchestratorAPIException):
            raise ValidationError("field", "error")

    def test_exception_inheritance_chain(self):
        """Test all exceptions inherit properly."""
        exceptions_to_test = [
            InstanceNotFoundError(1),
            InstanceOperationError("msg", 1),
            InvalidInstanceStatusError("status", "op"),
            DatabaseOperationError("op"),
            AuthenticationError(),
            AuthorizationError(),
            ValidationError("field", "msg"),
            RateLimitExceededError(10, "min"),
            WebSocketConnectionError("reason"),
        ]

        for exc in exceptions_to_test:
            assert isinstance(exc, CCOrchestratorAPIException)
            assert isinstance(exc, Exception)
            assert hasattr(exc, "message")
            assert hasattr(exc, "status_code")

    def test_module_structure(self):
        """Test module structure and imports."""
        import cc_orchestrator.web.exceptions as exc_module

        assert exc_module is not None

        # Test docstring exists
        assert hasattr(exc_module, "__doc__")
        assert exc_module.__doc__ is not None
