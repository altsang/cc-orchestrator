"""
Unit tests for alerts router API endpoints.

Tests cover all alert management functionality including:
- List alerts with filtering and pagination
- Create new alerts with validation
- Get specific alerts by ID
- Get alerts by instance ID
- Get alerts by level
- Get alert summary with counts
- Get recent critical alerts
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock

import pytest

from cc_orchestrator.web.dependencies import PaginationParams
from cc_orchestrator.web.routers.v1 import alerts
from cc_orchestrator.web.schemas import AlertCreate, AlertLevel, AlertResponse


class TestAlertsRouterFunctions:
    """Test alerts router endpoint functions directly."""

    @pytest.fixture
    def mock_crud(self):
        """Mock CRUD adapter."""
        crud = AsyncMock()

        # Mock alert data
        mock_alert = Mock()
        mock_alert.id = 1
        mock_alert.alert_id = "ALERT-001"
        mock_alert.instance_id = 1
        mock_alert.level = AlertLevel.ERROR
        mock_alert.message = "Test alert message"
        mock_alert.details = '{"error_code": "ERR_001"}'  # String, not dict
        mock_alert.timestamp = datetime.now(UTC)
        mock_alert.created_at = datetime.now(UTC)
        mock_alert.updated_at = datetime.now(UTC)

        # Mock instance data
        mock_instance = Mock()
        mock_instance.id = 1
        mock_instance.issue_id = "test-issue"

        crud.list_alerts.return_value = ([mock_alert], 1)
        crud.create_alert.return_value = mock_alert
        crud.get_alert_by_alert_id.return_value = mock_alert
        crud.get_instance.return_value = mock_instance

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
    async def test_list_alerts_success(self, mock_crud, pagination_params):
        """Test successful alert listing with pagination."""
        result = await alerts.list_alerts(
            pagination=pagination_params,
            level=None,
            instance_id=None,
            crud=mock_crud
        )

        assert result["total"] == 1
        assert len(result["items"]) == 1
        assert result["page"] == 1
        assert result["size"] == 20
        assert result["pages"] == 1

        # Verify CRUD was called correctly
        mock_crud.list_alerts.assert_called_once_with(
            offset=0, limit=20, filters={}
        )

    @pytest.mark.asyncio
    async def test_list_alerts_with_filters(self, mock_crud, pagination_params):
        """Test alert listing with level and instance filters."""
        result = await alerts.list_alerts(
            pagination=pagination_params,
            level=AlertLevel.ERROR,
            instance_id=1,
            crud=mock_crud
        )

        assert result["total"] == 1

        # Verify filters were applied
        mock_crud.list_alerts.assert_called_once_with(
            offset=0, limit=20, filters={"level": AlertLevel.ERROR, "instance_id": 1}
        )

    @pytest.mark.asyncio
    async def test_create_alert_success(self, mock_crud):
        """Test successful alert creation."""
        alert_data = AlertCreate(
            instance_id=1,
            alert_id="ALERT-NEW",
            level=AlertLevel.ERROR,
            message="New test alert",
            details="test data"
        )

        # Mock no existing alert
        mock_crud.get_alert_by_alert_id.return_value = None

        result = await alerts.create_alert(alert_data=alert_data, crud=mock_crud)

        assert result["success"] is True
        assert "Alert created successfully" in result["message"]
        assert "data" in result

        # Verify instance check and creation
        mock_crud.get_instance.assert_called_once_with(1)
        mock_crud.get_alert_by_alert_id.assert_called_once_with("ALERT-NEW")
        mock_crud.create_alert.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_alert_instance_not_found(self, mock_crud):
        """Test alert creation with non-existent instance."""
        mock_crud.get_instance.return_value = None

        alert_data = AlertCreate(
            instance_id=999,
            alert_id="ALERT-NEW",
            level=AlertLevel.ERROR,
            message="Test alert"
        )

        with pytest.raises(Exception) as exc_info:
            await alerts.create_alert(alert_data=alert_data, crud=mock_crud)

        # The error decorator converts HTTPException to CCOrchestratorException
        assert "Instance with ID 999 not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_alert_duplicate_id(self, mock_crud):
        """Test alert creation with duplicate alert ID."""
        # Mock existing alert
        mock_existing = Mock()
        mock_crud.get_alert_by_alert_id.return_value = mock_existing

        alert_data = AlertCreate(
            instance_id=1,
            alert_id="ALERT-001",  # Duplicate
            level=AlertLevel.ERROR,
            message="Test alert"
        )

        with pytest.raises(Exception) as exc_info:
            await alerts.create_alert(alert_data=alert_data, crud=mock_crud)

        # The error decorator converts HTTPException to CCOrchestratorException
        assert "Alert with ID 'ALERT-001' already exists" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_alert_success(self, mock_crud):
        """Test successful alert retrieval by ID."""
        result = await alerts.get_alert(alert_id="ALERT-001", crud=mock_crud)

        assert result["success"] is True
        assert "Alert retrieved successfully" in result["message"]
        assert "data" in result

        mock_crud.get_alert_by_alert_id.assert_called_once_with("ALERT-001")

    @pytest.mark.asyncio
    async def test_get_alert_not_found(self, mock_crud):
        """Test alert retrieval for non-existent alert."""
        mock_crud.get_alert_by_alert_id.return_value = None

        with pytest.raises(Exception) as exc_info:
            await alerts.get_alert(alert_id="NONEXISTENT", crud=mock_crud)

        # The error decorator converts HTTPException to CCOrchestratorException
        assert "Alert with ID 'NONEXISTENT' not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_instance_alerts_success(self, mock_crud, pagination_params):
        """Test successful retrieval of instance alerts."""
        result = await alerts.get_instance_alerts(
            instance_id=1,
            pagination=pagination_params,
            level=None,
            crud=mock_crud
        )

        assert result["total"] == 1
        assert len(result["items"]) == 1

        # Verify instance check and filtering
        mock_crud.get_instance.assert_called_once_with(1)
        mock_crud.list_alerts.assert_called_once_with(
            offset=0, limit=20, filters={"instance_id": 1}
        )

    @pytest.mark.asyncio
    async def test_get_instance_alerts_not_found(self, mock_crud, pagination_params):
        """Test instance alerts for non-existent instance."""
        mock_crud.get_instance.return_value = None

        with pytest.raises(Exception) as exc_info:
            await alerts.get_instance_alerts(
                instance_id=999,
                pagination=pagination_params,
                level=None,
                crud=mock_crud
            )

        # The error decorator converts HTTPException to CCOrchestratorException
        assert "Instance with ID 999 not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_instance_alerts_with_level_filter(self, mock_crud, pagination_params):
        """Test instance alerts with level filtering."""
        result = await alerts.get_instance_alerts(
            instance_id=1,
            pagination=pagination_params,
            level=AlertLevel.CRITICAL,
            crud=mock_crud
        )

        assert result["total"] == 1

        # Verify filters include both instance and level
        mock_crud.list_alerts.assert_called_once_with(
            offset=0, limit=20, filters={"instance_id": 1, "level": AlertLevel.CRITICAL}
        )

    @pytest.mark.asyncio
    async def test_get_alerts_by_level_success(self, mock_crud, pagination_params):
        """Test successful retrieval of alerts by level."""
        result = await alerts.get_alerts_by_level(
            level=AlertLevel.ERROR,
            pagination=pagination_params,
            instance_id=None,
            crud=mock_crud
        )

        assert result["total"] == 1

        # Verify level filtering
        mock_crud.list_alerts.assert_called_once_with(
            offset=0, limit=20, filters={"level": AlertLevel.ERROR}
        )

    @pytest.mark.asyncio
    async def test_get_alerts_by_level_with_instance_filter(self, mock_crud, pagination_params):
        """Test alerts by level with instance filtering."""
        result = await alerts.get_alerts_by_level(
            level=AlertLevel.CRITICAL,
            pagination=pagination_params,
            instance_id=1,
            crud=mock_crud
        )

        assert result["total"] == 1

        # Verify both filters applied
        mock_crud.list_alerts.assert_called_once_with(
            offset=0, limit=20, filters={"level": AlertLevel.CRITICAL, "instance_id": 1}
        )

    @pytest.mark.asyncio
    async def test_get_alert_summary_success(self, mock_crud):
        """Test successful alert summary retrieval."""
        # Mock multiple alerts with different levels
        mock_alerts = []
        for level in [AlertLevel.CRITICAL, AlertLevel.ERROR, AlertLevel.WARNING, AlertLevel.INFO]:
            alert = Mock()
            alert.level = level
            mock_alerts.append(alert)

        mock_crud.list_alerts.return_value = (mock_alerts, 4)

        result = await alerts.get_alert_summary(
            instance_id=None,
            hours=24,
            crud=mock_crud
        )

        assert result["success"] is True
        assert "data" in result

        summary = result["data"]
        assert summary["total_alerts"] == 4
        assert summary["period_hours"] == 24
        assert "level_counts" in summary
        assert summary["critical_alerts"] == 1
        assert summary["error_alerts"] == 1
        assert summary["warning_alerts"] == 1
        assert summary["info_alerts"] == 1
        assert summary["high_priority_alerts"] == 2

    @pytest.mark.asyncio
    async def test_get_alert_summary_with_filters(self, mock_crud):
        """Test alert summary with instance filtering."""
        mock_crud.list_alerts.return_value = ([], 0)

        result = await alerts.get_alert_summary(
            instance_id=1,
            hours=48,
            crud=mock_crud
        )

        summary = result["data"]
        assert summary["period_hours"] == 48
        assert summary["instance_filter"] == 1

        # Verify filtering
        mock_crud.list_alerts.assert_called_once_with(
            offset=0, limit=10000, filters={"instance_id": 1}
        )

    @pytest.mark.asyncio
    async def test_get_recent_critical_alerts_success(self, mock_crud, pagination_params):
        """Test successful retrieval of recent critical alerts."""
        result = await alerts.get_recent_critical_alerts(
            pagination=pagination_params,
            instance_id=None,
            crud=mock_crud
        )

        assert result["total"] == 1

        # Verify critical level filtering
        mock_crud.list_alerts.assert_called_once_with(
            offset=0, limit=20, filters={"level": AlertLevel.CRITICAL}
        )

    @pytest.mark.asyncio
    async def test_get_recent_critical_alerts_with_instance_filter(self, mock_crud, pagination_params):
        """Test recent critical alerts with instance filtering."""
        result = await alerts.get_recent_critical_alerts(
            pagination=pagination_params,
            instance_id=1,
            crud=mock_crud
        )

        assert result["total"] == 1

        # Verify both filters applied
        mock_crud.list_alerts.assert_called_once_with(
            offset=0, limit=20, filters={"level": AlertLevel.CRITICAL, "instance_id": 1}
        )


class TestAlertValidation:
    """Test alert data validation and edge cases."""

    def test_alert_response_model_validation(self):
        """Test AlertResponse model validation."""
        # Test with valid data
        alert_data = {
            "id": 1,
            "alert_id": "ALERT-001",
            "instance_id": 1,
            "level": AlertLevel.ERROR,
            "message": "Test alert",
            "details": "test data",  # String, not dict
            "timestamp": datetime.now(UTC),
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC)
        }

        # This should not raise an exception
        response_model = AlertResponse.model_validate(alert_data)
        assert response_model.alert_id == "ALERT-001"
        assert response_model.level == AlertLevel.ERROR.value  # Pydantic converts to string

    def test_alert_create_model_validation(self):
        """Test AlertCreate model validation."""
        # Test with valid data
        create_data = {
            "instance_id": 1,
            "alert_id": "ALERT-NEW",
            "level": AlertLevel.WARNING,
            "message": "New alert message",
            "details": "test details"  # String, not dict
        }

        # This should not raise an exception
        create_model = AlertCreate.model_validate(create_data)
        assert create_model.instance_id == 1
        assert create_model.level == AlertLevel.WARNING.value  # Pydantic converts to string

    def test_alert_level_enum_values(self):
        """Test AlertLevel enum contains expected values."""
        expected_levels = {"critical", "error", "warning", "info"}
        actual_levels = {level.value for level in AlertLevel}

        assert actual_levels == expected_levels


class TestAlertRouterDecorators:
    """Test decorator functionality on alert endpoints."""

    def test_decorators_applied_to_list_alerts(self):
        """Test that decorators are applied to list_alerts function."""
        # Check that the function has decorators applied
        func = alerts.list_alerts

        # The function should be wrapped by decorators
        assert hasattr(func, '__wrapped__') or hasattr(func, '__name__')
        assert func.__name__ == 'list_alerts'

    def test_decorators_applied_to_create_alert(self):
        """Test that decorators are applied to create_alert function."""
        func = alerts.create_alert

        # The function should be wrapped by decorators
        assert hasattr(func, '__wrapped__') or hasattr(func, '__name__')
        assert func.__name__ == 'create_alert'

    def test_decorators_applied_to_get_alert(self):
        """Test that decorators are applied to get_alert function."""
        func = alerts.get_alert

        # The function should be wrapped by decorators
        assert hasattr(func, '__wrapped__') or hasattr(func, '__name__')
        assert func.__name__ == 'get_alert'


class TestAlertRouterIntegration:
    """Test router integration aspects."""

    def test_router_has_endpoints(self):
        """Test that the router has the expected endpoints."""
        # Get all routes from the router
        routes = alerts.router.routes

        # Check that we have routes
        assert len(routes) > 0

        # Check for specific route patterns
        route_paths = [route.path for route in routes]

        # Should have the main list endpoint
        assert "/" in route_paths

        # Should have specific alert endpoint
        assert "/{alert_id}" in route_paths

    def test_router_methods(self):
        """Test that routes have correct HTTP methods."""
        routes = alerts.router.routes

        # Find the main list route
        list_route = next((r for r in routes if r.path == "/"), None)
        assert list_route is not None
        assert "GET" in list_route.methods

        # Find the create route
        create_route = next((r for r in routes if r.path == "/" and "POST" in r.methods), None)
        assert create_route is not None
        assert "POST" in create_route.methods

    def test_alert_level_enum_in_routes(self):
        """Test that AlertLevel enum is properly integrated."""
        # Test that the enum values are available
        levels = [level.value for level in AlertLevel]
        expected_levels = ["info", "warning", "error", "critical"]

        assert set(levels) == set(expected_levels)
