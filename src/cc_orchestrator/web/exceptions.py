"""Custom exceptions for the web API."""


class CCOrchestratorAPIException(Exception):
    """Base exception for CC-Orchestrator API."""

    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class InstanceNotFoundError(CCOrchestratorAPIException):
    """Raised when an instance is not found."""

    def __init__(self, instance_id: int):
        super().__init__(f"Instance {instance_id} not found", 404)
        self.instance_id = instance_id


class InstanceOperationError(CCOrchestratorAPIException):
    """Raised when an instance operation fails."""

    def __init__(self, message: str, instance_id: int):
        super().__init__(message, 400)
        self.instance_id = instance_id


class InvalidInstanceStatusError(CCOrchestratorAPIException):
    """Raised when trying to perform an invalid status transition."""

    def __init__(self, current_status: str, requested_operation: str):
        message = f"Cannot {requested_operation} instance in {current_status} status"
        super().__init__(message, 400)
        self.current_status = current_status
        self.requested_operation = requested_operation


class DatabaseOperationError(CCOrchestratorAPIException):
    """Raised when a database operation fails."""

    def __init__(self, operation: str, details: str = ""):
        message = f"Database operation '{operation}' failed"
        if details:
            message += f": {details}"
        super().__init__(message, 500)
        self.operation = operation
        self.details = details


class AuthenticationError(CCOrchestratorAPIException):
    """Raised when authentication fails."""

    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, 401)


class AuthorizationError(CCOrchestratorAPIException):
    """Raised when authorization fails."""

    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(message, 403)


class ValidationError(CCOrchestratorAPIException):
    """Raised when request validation fails."""

    def __init__(self, field: str, message: str):
        super().__init__(f"Validation error for '{field}': {message}", 400)
        self.field = field


class RateLimitExceededError(CCOrchestratorAPIException):
    """Raised when rate limit is exceeded."""

    def __init__(self, limit: int, window: str):
        message = f"Rate limit exceeded: {limit} requests per {window}"
        super().__init__(message, 429)
        self.limit = limit
        self.window = window


class WebSocketConnectionError(CCOrchestratorAPIException):
    """Raised when WebSocket connection fails."""

    def __init__(self, reason: str):
        super().__init__(f"WebSocket connection error: {reason}", 400)
        self.reason = reason
