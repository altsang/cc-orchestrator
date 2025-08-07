"""
Tests for web dependencies and dependency injection.

Tests database session management, pagination, authentication, and validation dependencies.
"""

from unittest.mock import Mock

import pytest
from fastapi import HTTPException, Request
from sqlalchemy.orm import Session

from cc_orchestrator.web.dependencies import (
    CurrentUser,
    PaginationParams,
    get_client_ip,
    get_crud,
    get_current_user,
    get_database_manager,
    get_db_session,
    get_pagination_params,
    get_request_id,
    require_permission,
    validate_config_id,
    validate_instance_id,
    validate_task_id,
    validate_worktree_id,
)


class TestDatabaseDependencies:
    """Test database-related dependencies."""

    @pytest.fixture
    def mock_request(self):
        """Create a mock FastAPI request."""
        request = Mock(spec=Request)
        request.app = Mock()
        request.app.state = Mock()
        return request

    @pytest.fixture
    def mock_db_manager(self):
        """Create a mock database manager."""
        manager = Mock()
        manager.session_factory = Mock()
        return manager

    @pytest.fixture
    def mock_session(self):
        """Create a mock database session."""
        session = Mock(spec=Session)
        session.commit = Mock()
        session.rollback = Mock()
        session.close = Mock()
        return session

    @pytest.mark.asyncio
    async def test_get_database_manager_success(self, mock_request, mock_db_manager):
        """Test successful database manager retrieval."""
        mock_request.app.state.db_manager = mock_db_manager

        result = await get_database_manager(mock_request)

        assert result == mock_db_manager

    @pytest.mark.asyncio
    async def test_get_database_manager_not_found(self, mock_request):
        """Test database manager retrieval when not in app state."""
        # No db_manager attribute
        del mock_request.app.state.db_manager
        mock_request.app.state = Mock(spec=[])

        with pytest.raises(HTTPException) as exc_info:
            await get_database_manager(mock_request)

        assert exc_info.value.status_code == 500
        assert "Database connection not available" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_db_session_success(self, mock_db_manager, mock_session):
        """Test successful database session creation and cleanup."""
        mock_db_manager.session_factory.return_value = mock_session

        # Use the async generator
        async_gen = get_db_session(mock_db_manager)
        session = await async_gen.__anext__()

        assert session == mock_session
        mock_db_manager.session_factory.assert_called_once()

        # Test cleanup - simulate the generator finishing
        try:
            await async_gen.__anext__()
        except StopAsyncIteration:
            pass

        # Verify session was committed and closed
        mock_session.commit.assert_called_once()
        mock_session.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_db_session_commit_error(self, mock_db_manager, mock_session):
        """Test database session with commit error."""
        mock_db_manager.session_factory.return_value = mock_session
        mock_session.commit.side_effect = Exception("Commit failed")

        async_gen = get_db_session(mock_db_manager)
        session = await async_gen.__anext__()

        assert session == mock_session

        # Test cleanup with commit error
        with pytest.raises(Exception, match="Commit failed"):
            try:
                await async_gen.__anext__()
            except StopAsyncIteration:
                pass

        # Verify session was rolled back (commit error triggers rollback)
        assert mock_session.rollback.called
        mock_session.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_db_session_http_exception(self, mock_db_manager, mock_session):
        """Test database session with HTTP exception during use."""
        mock_db_manager.session_factory.return_value = mock_session

        async_gen = get_db_session(mock_db_manager)
        await async_gen.__anext__()

        # Simulate HTTP exception during endpoint execution
        http_exc = HTTPException(status_code=409, detail="Conflict")

        try:
            # Simulate the exception being raised in the endpoint
            await async_gen.athrow(http_exc)
        except HTTPException as e:
            assert e.status_code == 409
            assert e.detail == "Conflict"

        # Verify session was rolled back and closed
        mock_session.rollback.assert_called_once()
        mock_session.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_db_session_general_exception(self, mock_db_manager, mock_session):
        """Test database session with general exception."""
        mock_db_manager.session_factory.return_value = mock_session

        async_gen = get_db_session(mock_db_manager)
        await async_gen.__anext__()

        # Simulate general exception during endpoint execution
        general_exc = RuntimeError("Database error")

        try:
            await async_gen.athrow(general_exc)
        except HTTPException as e:
            assert e.status_code == 500
            assert "Database session failed" in e.detail

        # Verify session was rolled back and closed
        mock_session.rollback.assert_called_once()
        mock_session.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_db_session_rollback_error(self, mock_db_manager, mock_session):
        """Test database session with rollback error during exception handling."""
        mock_db_manager.session_factory.return_value = mock_session
        mock_session.rollback.side_effect = Exception("Rollback failed")

        async_gen = get_db_session(mock_db_manager)
        await async_gen.__anext__()

        # Simulate exception that triggers rollback
        general_exc = RuntimeError("Database error")

        try:
            await async_gen.athrow(general_exc)
        except HTTPException as e:
            assert e.status_code == 500

        # Verify rollback was attempted and session was still closed
        mock_session.rollback.assert_called_once()
        mock_session.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_db_session_close_error(self, mock_db_manager, mock_session):
        """Test database session with close error during cleanup."""
        mock_db_manager.session_factory.return_value = mock_session
        mock_session.close.side_effect = Exception("Close failed")

        async_gen = get_db_session(mock_db_manager)
        await async_gen.__anext__()

        # Test cleanup with close error
        try:
            await async_gen.__anext__()
        except StopAsyncIteration:
            pass

        # Verify close was attempted despite error
        mock_session.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_crud(self, mock_session):
        """Test CRUD adapter creation."""
        result = await get_crud(mock_session)

        assert result is not None
        # The CRUDBase should be initialized with the session
        assert result.session == mock_session


class TestRequestDependencies:
    """Test request-related dependencies."""

    def test_get_request_id_exists(self):
        """Test getting request ID when it exists."""
        mock_request = Mock(spec=Request)
        mock_request.state = Mock()
        mock_request.state.request_id = "test-request-123"

        result = get_request_id(mock_request)
        assert result == "test-request-123"

    def test_get_request_id_missing(self):
        """Test getting request ID when it doesn't exist."""
        mock_request = Mock(spec=Request)
        mock_request.state = Mock(spec=[])  # No request_id attribute

        result = get_request_id(mock_request)
        assert result == "unknown"

    def test_get_client_ip_x_forwarded_for(self):
        """Test getting client IP from X-Forwarded-For header."""
        mock_request = Mock(spec=Request)
        mock_request.headers = {"x-forwarded-for": "192.168.1.100, 10.0.0.1"}
        mock_request.client = Mock()
        mock_request.client.host = "127.0.0.1"

        result = get_client_ip(mock_request)
        assert result == "192.168.1.100"  # First IP in forwarded list

    def test_get_client_ip_x_real_ip(self):
        """Test getting client IP from X-Real-IP header."""
        mock_request = Mock(spec=Request)
        mock_request.headers = {"x-real-ip": "203.0.113.45"}
        mock_request.client = Mock()
        mock_request.client.host = "127.0.0.1"

        result = get_client_ip(mock_request)
        assert result == "203.0.113.45"

    def test_get_client_ip_direct(self):
        """Test getting client IP directly from client."""
        mock_request = Mock(spec=Request)
        mock_request.headers = {}
        mock_request.client = Mock()
        mock_request.client.host = "198.51.100.25"

        result = get_client_ip(mock_request)
        assert result == "198.51.100.25"

    def test_get_client_ip_no_client(self):
        """Test getting client IP when no client info available."""
        mock_request = Mock(spec=Request)
        mock_request.headers = {}
        mock_request.client = None

        result = get_client_ip(mock_request)
        assert result == "unknown"

    def test_get_client_ip_precedence(self):
        """Test that X-Forwarded-For takes precedence over X-Real-IP."""
        mock_request = Mock(spec=Request)
        mock_request.headers = {
            "x-forwarded-for": "192.168.1.100",
            "x-real-ip": "203.0.113.45",
        }
        mock_request.client = Mock()
        mock_request.client.host = "127.0.0.1"

        result = get_client_ip(mock_request)
        assert result == "192.168.1.100"  # X-Forwarded-For wins


class TestPaginationDependencies:
    """Test pagination-related dependencies."""

    def test_pagination_params_defaults(self):
        """Test PaginationParams with default values."""
        params = PaginationParams()

        assert params.page == 1
        assert params.size == 20
        assert params.offset == 0

    def test_pagination_params_custom_values(self):
        """Test PaginationParams with custom values."""
        params = PaginationParams(page=3, size=50)

        assert params.page == 3
        assert params.size == 50
        assert params.offset == 100  # (3-1) * 50

    def test_pagination_params_invalid_page(self):
        """Test PaginationParams with invalid page number."""
        with pytest.raises(HTTPException) as exc_info:
            PaginationParams(page=0)

        assert exc_info.value.status_code == 422
        assert "Page number must be >= 1" in exc_info.value.detail

    def test_pagination_params_invalid_size_too_small(self):
        """Test PaginationParams with size too small."""
        with pytest.raises(HTTPException) as exc_info:
            PaginationParams(size=0)

        assert exc_info.value.status_code == 422
        assert "Page size must be between 1 and 100" in exc_info.value.detail

    def test_pagination_params_invalid_size_too_large(self):
        """Test PaginationParams with size too large."""
        with pytest.raises(HTTPException) as exc_info:
            PaginationParams(size=101)

        assert exc_info.value.status_code == 422
        assert "Page size must be between 1 and 100" in exc_info.value.detail

    def test_pagination_params_custom_max_size(self):
        """Test PaginationParams with custom max_size."""
        params = PaginationParams(size=150, max_size=200)

        assert params.size == 150

        with pytest.raises(HTTPException):
            PaginationParams(size=250, max_size=200)

    def test_get_pagination_params_default(self):
        """Test get_pagination_params with default values."""
        params = get_pagination_params()

        assert isinstance(params, PaginationParams)
        assert params.page == 1
        assert params.size == 20

    def test_get_pagination_params_custom(self):
        """Test get_pagination_params with custom values."""
        params = get_pagination_params(page=5, size=10)

        assert params.page == 5
        assert params.size == 10
        assert params.offset == 40


class TestAuthenticationDependencies:
    """Test authentication-related dependencies."""

    def test_current_user_creation(self):
        """Test CurrentUser creation."""
        user = CurrentUser(user_id="test-user")

        assert user.user_id == "test-user"
        assert user.permissions == []

    def test_current_user_with_permissions(self):
        """Test CurrentUser creation with permissions."""
        user = CurrentUser(user_id="admin", permissions=["read", "write", "admin"])

        assert user.user_id == "admin"
        assert user.permissions == ["read", "write", "admin"]

    @pytest.mark.asyncio
    async def test_get_current_user(self):
        """Test get_current_user dependency."""
        mock_request = Mock(spec=Request)

        user = await get_current_user(mock_request)

        assert isinstance(user, CurrentUser)
        assert user.user_id == "default"
        assert "read" in user.permissions
        assert "write" in user.permissions

    @pytest.mark.asyncio
    async def test_require_permission_success(self):
        """Test require_permission with valid permission."""
        user = CurrentUser(user_id="test", permissions=["read", "write"])

        result = await require_permission("read", user)

        assert result == user

    @pytest.mark.asyncio
    async def test_require_permission_denied(self):
        """Test require_permission with missing permission."""
        user = CurrentUser(user_id="test", permissions=["read"])

        with pytest.raises(HTTPException) as exc_info:
            await require_permission("admin", user)

        assert exc_info.value.status_code == 403
        assert "Permission 'admin' required" in exc_info.value.detail


class TestValidationDependencies:
    """Test validation-related dependencies."""

    def test_validate_instance_id_valid(self):
        """Test validate_instance_id with valid ID."""
        result = validate_instance_id(123)
        assert result == 123

    def test_validate_instance_id_invalid(self):
        """Test validate_instance_id with invalid ID."""
        with pytest.raises(HTTPException) as exc_info:
            validate_instance_id(0)

        assert exc_info.value.status_code == 400
        assert "Instance ID must be a positive integer" in exc_info.value.detail

    def test_validate_instance_id_negative(self):
        """Test validate_instance_id with negative ID."""
        with pytest.raises(HTTPException) as exc_info:
            validate_instance_id(-5)

        assert exc_info.value.status_code == 400

    def test_validate_task_id_valid(self):
        """Test validate_task_id with valid ID."""
        result = validate_task_id(456)
        assert result == 456

    def test_validate_task_id_invalid(self):
        """Test validate_task_id with invalid ID."""
        with pytest.raises(HTTPException) as exc_info:
            validate_task_id(0)

        assert exc_info.value.status_code == 400
        assert "Task ID must be a positive integer" in exc_info.value.detail

    def test_validate_worktree_id_valid(self):
        """Test validate_worktree_id with valid ID."""
        result = validate_worktree_id(789)
        assert result == 789

    def test_validate_worktree_id_invalid(self):
        """Test validate_worktree_id with invalid ID."""
        with pytest.raises(HTTPException) as exc_info:
            validate_worktree_id(-1)

        assert exc_info.value.status_code == 400
        assert "Worktree ID must be a positive integer" in exc_info.value.detail

    def test_validate_config_id_valid(self):
        """Test validate_config_id with valid ID."""
        result = validate_config_id(101)
        assert result == 101

    def test_validate_config_id_invalid(self):
        """Test validate_config_id with invalid ID."""
        with pytest.raises(HTTPException) as exc_info:
            validate_config_id(0)

        assert exc_info.value.status_code == 400
        assert "Configuration ID must be a positive integer" in exc_info.value.detail


class TestDependencyIntegration:
    """Test integration scenarios and edge cases."""

    @pytest.mark.asyncio
    async def test_database_session_lifecycle_integration(self):
        """Test complete database session lifecycle in realistic scenario."""
        mock_db_manager = Mock()
        mock_session = Mock(spec=Session)
        mock_db_manager.session_factory.return_value = mock_session

        # Simulate normal request flow
        async_gen = get_db_session(mock_db_manager)

        # Get session
        session = await async_gen.__anext__()
        assert session == mock_session

        # Simulate successful endpoint execution (no exceptions)
        try:
            await async_gen.__anext__()
        except StopAsyncIteration:
            pass

        # Verify proper cleanup
        mock_session.commit.assert_called_once()
        mock_session.close.assert_called_once()
        mock_session.rollback.assert_not_called()

    def test_pagination_edge_cases(self):
        """Test pagination edge cases and boundary conditions."""
        # Test maximum allowed page size
        params = PaginationParams(page=1, size=100)
        assert params.size == 100

        # Test large page number
        params = PaginationParams(page=1000, size=1)
        assert params.offset == 999

        # Test minimum values
        params = PaginationParams(page=1, size=1)
        assert params.page == 1
        assert params.size == 1
        assert params.offset == 0

    def test_client_ip_header_variations(self):
        """Test client IP extraction with various header formats."""
        mock_request = Mock(spec=Request)
        mock_request.client = Mock()
        mock_request.client.host = "fallback-ip"

        # Test multiple IPs in X-Forwarded-For with spaces
        mock_request.headers = {"x-forwarded-for": " 192.168.1.1 , 10.0.0.1 , 172.16.0.1 "}
        result = get_client_ip(mock_request)
        assert result == "192.168.1.1"

        # Test single IP in X-Forwarded-For
        mock_request.headers = {"x-forwarded-for": "203.0.113.45"}
        result = get_client_ip(mock_request)
        assert result == "203.0.113.45"

        # Test empty X-Forwarded-For
        mock_request.headers = {"x-forwarded-for": ""}
        result = get_client_ip(mock_request)
        assert result == "fallback-ip"  # Falls back to client.host

    @pytest.mark.asyncio
    async def test_permission_system_integration(self):
        """Test permission system with various user configurations."""
        # Test user with multiple permissions
        admin_user = CurrentUser(
            user_id="admin", permissions=["read", "write", "admin", "delete"]
        )

        # Should succeed for any required permission
        await require_permission("read", admin_user)
        await require_permission("admin", admin_user)

        # Test user with limited permissions
        readonly_user = CurrentUser(user_id="readonly", permissions=["read"])

        # Should succeed for read
        await require_permission("read", readonly_user)

        # Should fail for write
        with pytest.raises(HTTPException) as exc_info:
            await require_permission("write", readonly_user)
        assert exc_info.value.status_code == 403

    def test_all_validation_functions_consistency(self):
        """Test that all validation functions behave consistently."""
        validators = [
            validate_instance_id,
            validate_task_id,
            validate_worktree_id,
            validate_config_id,
        ]

        for validator in validators:
            # Should accept positive integers
            assert validator(1) == 1
            assert validator(100) == 100
            assert validator(999999) == 999999

            # Should reject zero and negative
            with pytest.raises(HTTPException) as exc_info:
                validator(0)
            assert exc_info.value.status_code == 400

            with pytest.raises(HTTPException) as exc_info:
                validator(-1)
            assert exc_info.value.status_code == 400

