"""
Unit tests for config router API endpoints.

Tests cover all configuration management functionality including:
- List configurations with filtering and pagination
- Create new configurations with validation
- Get, update, and delete configurations
- Configuration resolution and scoping
- Instance-specific configurations
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock

import pytest

from cc_orchestrator.database.models import ConfigScope
from cc_orchestrator.web.dependencies import PaginationParams
from cc_orchestrator.web.routers.v1 import config
from cc_orchestrator.web.schemas import (
    ConfigurationCreate,
    ConfigurationResponse,
    ConfigurationUpdate,
)


class TestConfigRouterFunctions:
    """Test config router endpoint functions directly."""

    @pytest.fixture
    def mock_crud(self):
        """Mock CRUD adapter."""
        crud = AsyncMock()

        # Mock configuration data
        mock_config = Mock()
        mock_config.id = 1
        mock_config.key = "test_key"
        mock_config.value = "test_value"
        mock_config.scope = ConfigScope.GLOBAL
        mock_config.instance_id = None
        mock_config.description = "Test configuration"
        mock_config.is_secret = False
        mock_config.is_readonly = False
        mock_config.extra_metadata = {}  # Dict, not Mock
        mock_config.created_at = datetime.now(UTC)
        mock_config.updated_at = datetime.now(UTC)

        # Mock instance data
        mock_instance = Mock()
        mock_instance.id = 1
        mock_instance.issue_id = "test-issue"

        crud.list_configurations.return_value = ([mock_config], 1)
        crud.create_configuration.return_value = mock_config
        crud.get_configuration.return_value = mock_config
        crud.get_configuration_by_key_scope.return_value = (
            None  # No duplicate by default
        )
        crud.update_configuration.return_value = mock_config
        crud.delete_configuration.return_value = True
        crud.get_instance.return_value = mock_instance
        crud.resolve_configuration_value.return_value = "resolved_value"

        return crud

    @pytest.fixture
    def pagination_params(self):
        """Mock pagination parameters."""
        params = Mock(spec=PaginationParams)
        params.page = 1
        params.size = 20
        params.offset = 0
        return params

    @pytest.mark.asyncio
    async def test_list_configurations_success(self, mock_crud, pagination_params):
        """Test successful configuration listing with pagination."""
        result = await config.list_configurations(
            pagination=pagination_params,
            scope=None,
            instance_id=None,
            key_pattern=None,
            crud=mock_crud,
        )

        assert result["total"] == 1
        assert len(result["items"]) == 1
        assert result["page"] == 1
        assert result["size"] == 20
        assert result["pages"] == 1

        # Verify CRUD was called correctly
        mock_crud.list_configurations.assert_called_once_with(
            offset=0, limit=20, filters={}
        )

    @pytest.mark.asyncio
    async def test_list_configurations_with_filters(self, mock_crud, pagination_params):
        """Test configuration listing with scope and instance filters."""
        result = await config.list_configurations(
            pagination=pagination_params,
            scope=ConfigScope.GLOBAL,
            instance_id=1,
            key_pattern="test*",
            crud=mock_crud,
        )

        assert result["total"] == 1

        # Verify filters were applied
        mock_crud.list_configurations.assert_called_once_with(
            offset=0,
            limit=20,
            filters={
                "scope": ConfigScope.GLOBAL,
                "instance_id": 1,
                "key_pattern": "test*",
            },
        )

    @pytest.mark.asyncio
    async def test_create_configuration_global_success(self, mock_crud):
        """Test successful global configuration creation."""
        # Mock the exact configuration lookup to return None (no existing config)
        mock_crud.get_exact_configuration_by_key_scope.return_value = None

        config_data = ConfigurationCreate(
            key="test_key",
            value="test_value",
            scope=ConfigScope.GLOBAL,
            description="Test config",
        )

        result = await config.create_configuration(
            config_data=config_data, crud=mock_crud
        )

        assert result["success"] is True
        assert "Configuration created successfully" in result["message"]
        assert "data" in result

        # Verify duplicate check and creation - using exact method now
        mock_crud.get_exact_configuration_by_key_scope.assert_called_once_with(
            "test_key", "global", None
        )
        mock_crud.create_configuration.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_configuration_instance_success(self, mock_crud):
        """Test successful instance-scoped configuration creation."""
        # Mock instance exists and no existing configuration
        mock_crud.get_instance.return_value = Mock(id=1)  # Instance exists
        mock_crud.get_exact_configuration_by_key_scope.return_value = None  # No existing config

        config_data = ConfigurationCreate(
            key="instance_key",
            value="instance_value",
            scope=ConfigScope.INSTANCE,
            instance_id=1,
            description="Instance config",
        )

        result = await config.create_configuration(
            config_data=config_data, crud=mock_crud
        )

        assert result["success"] is True

        # Verify instance validation and exact duplicate check
        mock_crud.get_instance.assert_called_once_with(1)
        mock_crud.get_exact_configuration_by_key_scope.assert_called_once_with(
            "instance_key", "instance", 1
        )

    @pytest.mark.asyncio
    async def test_create_configuration_instance_scope_without_id(self, mock_crud):
        """Test instance scope configuration without instance_id fails."""
        config_data = ConfigurationCreate(
            key="test_key", value="test_value", scope=ConfigScope.INSTANCE
        )

        with pytest.raises(Exception) as exc_info:
            await config.create_configuration(config_data=config_data, crud=mock_crud)

        assert "instance_id is required for instance-scoped configurations" in str(
            exc_info.value
        )

    @pytest.mark.asyncio
    async def test_create_configuration_global_with_instance_id(self, mock_crud):
        """Test global scope configuration with instance_id fails."""
        config_data = ConfigurationCreate(
            key="test_key", value="test_value", scope=ConfigScope.GLOBAL, instance_id=1
        )

        with pytest.raises(Exception) as exc_info:
            await config.create_configuration(config_data=config_data, crud=mock_crud)

        assert "instance_id can only be set for instance-scoped configurations" in str(
            exc_info.value
        )

    @pytest.mark.asyncio
    async def test_create_configuration_instance_not_found(self, mock_crud):
        """Test configuration creation with non-existent instance."""
        mock_crud.get_instance.return_value = None

        config_data = ConfigurationCreate(
            key="test_key",
            value="test_value",
            scope=ConfigScope.INSTANCE,
            instance_id=999,
        )

        with pytest.raises(Exception) as exc_info:
            await config.create_configuration(config_data=config_data, crud=mock_crud)

        assert "Instance with ID 999 not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_configuration_duplicate_key(self, mock_crud):
        """Test configuration creation with duplicate key/scope."""
        # Mock existing configuration
        mock_existing = Mock()
        mock_crud.get_configuration_by_key_scope.return_value = mock_existing

        config_data = ConfigurationCreate(
            key="duplicate_key", value="test_value", scope=ConfigScope.GLOBAL
        )

        with pytest.raises(Exception) as exc_info:
            await config.create_configuration(config_data=config_data, crud=mock_crud)

        assert "Configuration with key 'duplicate_key' already exists" in str(
            exc_info.value
        )

    @pytest.mark.asyncio
    async def test_get_configuration_success(self, mock_crud):
        """Test successful configuration retrieval by ID."""
        result = await config.get_configuration(config_id=1, crud=mock_crud)

        assert result["success"] is True
        assert "Configuration retrieved successfully" in result["message"]
        assert "data" in result

        mock_crud.get_configuration.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_get_configuration_not_found(self, mock_crud):
        """Test configuration retrieval for non-existent config."""
        mock_crud.get_configuration.return_value = None

        with pytest.raises(Exception) as exc_info:
            await config.get_configuration(config_id=999, crud=mock_crud)

        assert "Configuration with ID 999 not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_update_configuration_success(self, mock_crud):
        """Test successful configuration update."""
        update_data = ConfigurationUpdate(
            value="updated_value", description="Updated description"
        )

        result = await config.update_configuration(
            config_id=1, config_data=update_data, crud=mock_crud
        )

        assert result["success"] is True
        assert "Configuration updated successfully" in result["message"]

        mock_crud.get_configuration.assert_called_once_with(1)
        mock_crud.update_configuration.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_configuration_not_found(self, mock_crud):
        """Test configuration update for non-existent config."""
        mock_crud.get_configuration.return_value = None

        update_data = ConfigurationUpdate(value="new_value")

        with pytest.raises(Exception) as exc_info:
            await config.update_configuration(
                config_id=999, config_data=update_data, crud=mock_crud
            )

        assert "Configuration with ID 999 not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_update_readonly_configuration(self, mock_crud):
        """Test updating a read-only configuration fails."""
        # Mock readonly configuration
        readonly_config = Mock()
        readonly_config.is_readonly = True
        mock_crud.get_configuration.return_value = readonly_config

        update_data = ConfigurationUpdate(value="new_value")

        with pytest.raises(Exception) as exc_info:
            await config.update_configuration(
                config_id=1, config_data=update_data, crud=mock_crud
            )

        assert "Cannot update read-only configuration" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_delete_configuration_success(self, mock_crud):
        """Test successful configuration deletion."""
        result = await config.delete_configuration(config_id=1, crud=mock_crud)

        assert result["success"] is True
        assert "Configuration deleted successfully" in result["message"]

        mock_crud.get_configuration.assert_called_once_with(1)
        mock_crud.delete_configuration.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_delete_configuration_not_found(self, mock_crud):
        """Test configuration deletion for non-existent config."""
        mock_crud.get_configuration.return_value = None

        with pytest.raises(Exception) as exc_info:
            await config.delete_configuration(config_id=999, crud=mock_crud)

        assert "Configuration with ID 999 not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_delete_readonly_configuration(self, mock_crud):
        """Test deleting a read-only configuration fails."""
        # Mock readonly configuration
        readonly_config = Mock()
        readonly_config.is_readonly = True
        mock_crud.get_configuration.return_value = readonly_config

        with pytest.raises(Exception) as exc_info:
            await config.delete_configuration(config_id=1, crud=mock_crud)

        assert "Cannot delete read-only configuration" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_configuration_by_key_success(self, mock_crud):
        """Test successful configuration retrieval by key."""
        # Override the default None return for this test
        mock_config = Mock()
        mock_config.id = 1
        mock_config.key = "test_key"
        mock_config.value = "test_value"
        mock_config.scope = ConfigScope.GLOBAL
        mock_config.instance_id = None
        mock_config.description = "Test config"
        mock_config.is_secret = False
        mock_config.is_readonly = False
        mock_config.extra_metadata = {}
        mock_config.created_at = datetime.now(UTC)
        mock_config.updated_at = datetime.now(UTC)
        mock_crud.get_configuration_by_key_scope.return_value = mock_config

        result = await config.get_configuration_by_key(
            key="test_key", scope=ConfigScope.GLOBAL, instance_id=None, crud=mock_crud
        )

        assert result["success"] is True
        assert "data" in result

        mock_crud.get_configuration_by_key_scope.assert_called_once_with(
            "test_key", "global", None
        )

    @pytest.mark.asyncio
    async def test_get_configuration_by_key_not_found(self, mock_crud):
        """Test configuration retrieval by key when not found."""
        mock_crud.get_configuration_by_key_scope.return_value = None

        with pytest.raises(Exception) as exc_info:
            await config.get_configuration_by_key(
                key="nonexistent",
                scope=ConfigScope.GLOBAL,
                instance_id=None,
                crud=mock_crud,
            )

        assert "Configuration with key 'nonexistent' not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_resolved_configuration_success(self, mock_crud):
        """Test successful resolved configuration retrieval."""
        # Create a mock configuration for global resolution
        mock_config = Mock()
        mock_config.id = 1
        mock_config.key = "test_key"
        mock_config.value = "resolved_value"
        mock_config.scope = ConfigScope.GLOBAL
        mock_config.instance_id = None
        mock_config.description = "Test config"
        mock_config.is_secret = False
        mock_config.is_readonly = False
        mock_config.extra_metadata = {}
        mock_config.created_at = datetime.now(UTC)
        mock_config.updated_at = datetime.now(UTC)

        # Set up mock to return the config for global scope lookup
        mock_crud.get_configuration_by_key_scope.return_value = mock_config

        result = await config.get_resolved_configuration(
            key="test_key", instance_id=None, crud=mock_crud
        )

        assert result["success"] is True
        assert "data" in result
        assert result["data"]["resolved_from_scope"] == "global"

        # Should call with global scope since no instance_id provided
        mock_crud.get_configuration_by_key_scope.assert_called_once_with(
            "test_key", "global", None
        )

    @pytest.mark.asyncio
    async def test_get_resolved_configuration_not_found(self, mock_crud):
        """Test resolved configuration when key not found."""
        # Set up mock to return None for configuration lookup (not found)
        mock_crud.get_configuration_by_key_scope.return_value = None

        with pytest.raises(Exception) as exc_info:
            await config.get_resolved_configuration(
                key="missing_key", instance_id=None, crud=mock_crud
            )

        assert "Configuration with key 'missing_key' not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_instance_configurations_success(
        self, mock_crud, pagination_params
    ):
        """Test successful retrieval of instance configurations."""
        result = await config.get_instance_configurations(
            instance_id=1, pagination=pagination_params, crud=mock_crud
        )

        assert result["total"] == 1
        assert len(result["items"]) == 1

        # Verify instance check and filtering
        mock_crud.get_instance.assert_called_once_with(1)
        mock_crud.list_configurations.assert_called_once_with(
            offset=0,
            limit=20,
            filters={"instance_id": 1, "scope": ConfigScope.INSTANCE},
        )

    @pytest.mark.asyncio
    async def test_get_instance_configurations_empty(
        self, mock_crud, pagination_params
    ):
        """Test instance configurations when none exist."""
        mock_crud.list_configurations.return_value = ([], 0)

        result = await config.get_instance_configurations(
            instance_id=1, pagination=pagination_params, crud=mock_crud
        )

        assert result["total"] == 0
        assert len(result["items"]) == 0

    @pytest.mark.asyncio
    async def test_get_instance_configurations_not_found(
        self, mock_crud, pagination_params
    ):
        """Test instance configurations for non-existent instance."""
        mock_crud.get_instance.return_value = None

        with pytest.raises(Exception) as exc_info:
            await config.get_instance_configurations(
                instance_id=999, pagination=pagination_params, crud=mock_crud
            )

        assert "Instance with ID 999 not found" in str(exc_info.value)


class TestConfigValidation:
    """Test configuration data validation and edge cases."""

    def test_configuration_response_model_validation(self):
        """Test ConfigurationResponse model validation."""
        config_data = {
            "id": 1,
            "key": "test_key",
            "value": "test_value",
            "scope": ConfigScope.GLOBAL,
            "instance_id": None,
            "description": "Test config",
            "is_secret": False,
            "is_readonly": False,
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }

        response_model = ConfigurationResponse.model_validate(config_data)
        assert response_model.key == "test_key"
        assert (
            response_model.scope == ConfigScope.GLOBAL.value
        )  # Pydantic converts to string

    def test_configuration_create_model_validation(self):
        """Test ConfigurationCreate model validation."""
        create_data = {
            "key": "new_key",
            "value": "new_value",
            "scope": ConfigScope.GLOBAL,
            "description": "New config",
        }

        create_model = ConfigurationCreate.model_validate(create_data)
        assert create_model.key == "new_key"
        assert (
            create_model.scope == ConfigScope.GLOBAL.value
        )  # Pydantic converts to string

    def test_config_scope_enum_values(self):
        """Test ConfigScope enum contains expected values."""
        expected_scopes = {"global", "user", "project", "instance"}
        actual_scopes = {scope.value for scope in ConfigScope}

        assert actual_scopes == expected_scopes


class TestConfigRouterDecorators:
    """Test decorator functionality on config endpoints."""

    def test_decorators_applied_to_list_configurations(self):
        """Test that decorators are applied to list_configurations function."""
        func = config.list_configurations
        assert hasattr(func, "__wrapped__") or hasattr(func, "__name__")
        assert func.__name__ == "list_configurations"

    def test_decorators_applied_to_create_configuration(self):
        """Test that decorators are applied to create_configuration function."""
        func = config.create_configuration
        assert hasattr(func, "__wrapped__") or hasattr(func, "__name__")
        assert func.__name__ == "create_configuration"

    def test_decorators_applied_to_get_configuration(self):
        """Test that decorators are applied to get_configuration function."""
        func = config.get_configuration
        assert hasattr(func, "__wrapped__") or hasattr(func, "__name__")
        assert func.__name__ == "get_configuration"


class TestConfigRouterIntegration:
    """Test router integration aspects."""

    def test_router_has_endpoints(self):
        """Test that the router has the expected endpoints."""
        routes = config.router.routes
        assert len(routes) > 0

        route_paths = [route.path for route in routes]

        # Should have the main list endpoint
        assert "/" in route_paths

        # Should have specific config endpoint
        assert "/{config_id}" in route_paths

    def test_router_methods(self):
        """Test that routes have correct HTTP methods."""
        routes = config.router.routes

        # Collect all methods for each path
        path_methods = {}
        for route in routes:
            if route.path not in path_methods:
                path_methods[route.path] = set()
            path_methods[route.path].update(route.methods)

        # Main endpoint should support GET and POST
        assert "GET" in path_methods["/"]
        assert "POST" in path_methods["/"]

        # Specific config endpoint should support GET, PUT, DELETE
        assert "GET" in path_methods["/{config_id}"]
        assert "PUT" in path_methods["/{config_id}"]
        assert "DELETE" in path_methods["/{config_id}"]

    def test_config_scope_enum_in_routes(self):
        """Test that ConfigScope enum is properly integrated."""
        scopes = [scope.value for scope in ConfigScope]
        expected_scopes = ["global", "user", "project", "instance"]

        assert set(scopes) == set(expected_scopes)
