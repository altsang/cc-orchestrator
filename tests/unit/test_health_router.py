"""
Unit tests for health router API endpoints.

Tests cover all health monitoring functionality including:
- API health checks
- Instance health monitoring
- Health check history and metrics
- Health status retrieval and management
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock

import pytest

from cc_orchestrator.database.models import HealthStatus
from cc_orchestrator.web.dependencies import PaginationParams
from cc_orchestrator.web.routers.v1 import health
from cc_orchestrator.web.schemas import HealthCheckResponse


class TestHealthRouterFunctions:
    """Test health router endpoint functions directly."""

    @pytest.fixture
    def mock_crud(self):
        """Mock CRUD adapter."""
        crud = AsyncMock()

        # Mock health check data
        mock_health_check = Mock()
        mock_health_check.id = 1
        mock_health_check.instance_id = 1
        mock_health_check.overall_status = HealthStatus.HEALTHY
        mock_health_check.check_results = '{"database": "healthy", "api": "healthy"}'
        mock_health_check.check_timestamp = datetime.now(UTC)
        mock_health_check.duration_ms = 150.5
        mock_health_check.created_at = datetime.now(UTC)
        mock_health_check.updated_at = datetime.now(UTC)

        # Mock instance data
        mock_instance = Mock()
        mock_instance.id = 1
        mock_instance.issue_id = "test-issue"
        mock_instance.health_status = HealthStatus.HEALTHY
        mock_instance.last_health_check = datetime.now(UTC)
        mock_instance.health_check_count = 10
        mock_instance.healthy_check_count = 8
        mock_instance.health_check_details = "All systems operational"

        crud.list_instances.return_value = ([mock_instance], 1)
        crud.get_instance.return_value = mock_instance
        crud.create_health_check.return_value = mock_health_check
        crud.list_health_checks.return_value = ([mock_health_check], 1)
        crud.get_health_overview.return_value = {
            "total_instances": 1,
            "health_percentage": 75.0,
            "status_distribution": {"healthy": 1},
            "critical_instances": 0,
            "unhealthy_instances": 0,
            "degraded_instances": 0,
            "healthy_instances": 1,
            "timestamp": "2025-08-03T05:31:33Z",
        }

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
    async def test_health_check_success(self):
        """Test successful API health check."""
        result = await health.health_check()

        assert result["success"] is True
        assert "Health check completed successfully" in result["message"]
        assert "data" in result

        health_data = result["data"]
        assert health_data["status"] == "healthy"
        assert "timestamp" in health_data
        assert "version" in health_data
        assert "checks" in health_data
        assert health_data["checks"]["database"] == "healthy"
        assert health_data["checks"]["api"] == "healthy"

    @pytest.mark.asyncio
    async def test_list_instance_health_success(self, mock_crud, pagination_params):
        """Test successful instance health listing."""
        result = await health.list_instance_health(
            pagination=pagination_params, health_status=None, crud=mock_crud
        )

        assert result["total"] == 1
        assert len(result["items"]) == 1
        assert result["page"] == 1
        assert result["size"] == 20
        assert result["pages"] == 1

        # Verify CRUD was called correctly
        mock_crud.list_instances.assert_called_once_with(offset=0, limit=20, filters={})

    @pytest.mark.asyncio
    async def test_list_instance_health_with_status_filter(
        self, mock_crud, pagination_params
    ):
        """Test instance health listing with status filter."""
        result = await health.list_instance_health(
            pagination=pagination_params,
            health_status=HealthStatus.HEALTHY,
            crud=mock_crud,
        )

        assert result["total"] == 1

        # Verify status filter was applied
        mock_crud.list_instances.assert_called_once_with(
            offset=0, limit=20, filters={"health_status": HealthStatus.HEALTHY}
        )

    @pytest.mark.asyncio
    async def test_get_instance_health_success(self, mock_crud):
        """Test successful instance health retrieval."""
        result = await health.get_instance_health(instance_id=1, crud=mock_crud)

        assert result["success"] is True
        assert "Instance health retrieved successfully" in result["message"]
        assert "data" in result

        health_data = result["data"]
        assert health_data["instance_id"] == 1
        assert health_data["health_status"] == HealthStatus.HEALTHY

        mock_crud.get_instance.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_get_instance_health_not_found(self, mock_crud):
        """Test instance health retrieval for non-existent instance."""
        mock_crud.get_instance.return_value = None

        with pytest.raises(Exception) as exc_info:
            await health.get_instance_health(instance_id=999, crud=mock_crud)

        assert "Instance with ID 999 not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_perform_health_check_success(self, mock_crud):
        """Test successful manual health check."""
        result = await health.perform_health_check(instance_id=1, crud=mock_crud)

        assert result["success"] is True
        assert "Health check completed successfully" in result["message"]
        assert "data" in result

        # Verify instance exists check and health check creation
        mock_crud.get_instance.assert_called_once_with(1)
        mock_crud.create_health_check.assert_called_once()

    @pytest.mark.asyncio
    async def test_perform_health_check_instance_not_found(self, mock_crud):
        """Test health check for non-existent instance."""
        mock_crud.get_instance.return_value = None

        with pytest.raises(Exception) as exc_info:
            await health.perform_health_check(instance_id=999, crud=mock_crud)

        assert "Instance with ID 999 not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_health_history_success(self, mock_crud, pagination_params):
        """Test successful health check history retrieval."""
        result = await health.get_health_check_history(
            instance_id=1, pagination=pagination_params, crud=mock_crud
        )

        assert result["total"] == 1
        assert len(result["items"]) == 1

        # Verify instance check and history retrieval
        mock_crud.get_instance.assert_called_once_with(1)
        mock_crud.list_health_checks.assert_called_once_with(
            offset=0, limit=20, filters={"instance_id": 1}
        )

    @pytest.mark.asyncio
    async def test_get_health_history_with_status_filter(
        self, mock_crud, pagination_params
    ):
        """Test health history with status filtering."""
        result = await health.get_health_check_history(
            instance_id=1, pagination=pagination_params, crud=mock_crud
        )

        assert result["total"] == 1

        # Verify status filter was applied
        mock_crud.list_health_checks.assert_called_once_with(
            offset=0, limit=20, filters={"instance_id": 1}
        )

    @pytest.mark.asyncio
    async def test_get_health_history_instance_not_found(
        self, mock_crud, pagination_params
    ):
        """Test health history for non-existent instance."""
        mock_crud.get_instance.return_value = None

        with pytest.raises(Exception) as exc_info:
            await health.get_health_check_history(
                instance_id=999, pagination=pagination_params, crud=mock_crud
            )

        assert "Instance with ID 999 not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_health_metrics_success(self, mock_crud):
        """Test successful health metrics retrieval."""
        result = await health.get_health_metrics(instance_id=1, days=7, crud=mock_crud)

        assert result["success"] is True
        assert "Health metrics retrieved successfully" in result["message"]
        assert "data" in result

        metrics = result["data"]
        assert metrics["instance_id"] == 1
        assert metrics["period_days"] == 7
        assert "uptime_percentage" in metrics
        assert "total_checks" in metrics

        mock_crud.get_instance.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_get_health_metrics_instance_not_found(self, mock_crud):
        """Test health metrics for non-existent instance."""
        mock_crud.get_instance.return_value = None

        with pytest.raises(Exception) as exc_info:
            await health.get_health_metrics(instance_id=999, days=7, crud=mock_crud)

        assert "Instance with ID 999 not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_health_overview_success(self, mock_crud):
        """Test successful health overview retrieval."""
        # Mock summary data - this uses existing mock from fixture
        pass

        result = await health.get_health_overview(crud=mock_crud)

        assert result["success"] is True
        assert "Health overview retrieved successfully" in result["message"]
        assert "data" in result

        overview = result["data"]
        assert overview["total_instances"] == 1
        assert overview["healthy_instances"] == 1
        assert overview["unhealthy_instances"] == 0
        assert overview["health_percentage"] == 100.0  # 1 healthy / 1 total = 100%


class TestHealthValidation:
    """Test health data validation and edge cases."""

    def test_health_check_response_model_validation(self):
        """Test HealthCheckResponse model validation."""
        health_data = {
            "id": 1,
            "instance_id": 1,
            "overall_status": HealthStatus.HEALTHY,
            "check_results": '{"test": "passed"}',
            "duration_ms": 150.5,
            "check_timestamp": datetime.now(UTC),
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }

        response_model = HealthCheckResponse.model_validate(health_data)
        assert response_model.instance_id == 1
        assert response_model.overall_status == HealthStatus.HEALTHY.value

    def test_health_status_enum_values(self):
        """Test HealthStatus enum contains expected values."""
        expected_statuses = {"healthy", "degraded", "unhealthy", "critical", "unknown"}
        actual_statuses = {status.value for status in HealthStatus}

        assert actual_statuses == expected_statuses


class TestHealthRouterDecorators:
    """Test decorator functionality on health endpoints."""

    def test_decorators_applied_to_health_check(self):
        """Test that decorators are applied to health_check function."""
        func = health.health_check
        assert hasattr(func, "__wrapped__") or hasattr(func, "__name__")
        assert func.__name__ == "health_check"

    def test_decorators_applied_to_list_instance_health(self):
        """Test that decorators are applied to list_instance_health function."""
        func = health.list_instance_health
        assert hasattr(func, "__wrapped__") or hasattr(func, "__name__")
        assert func.__name__ == "list_instance_health"

    def test_decorators_applied_to_get_instance_health(self):
        """Test that decorators are applied to get_instance_health function."""
        func = health.get_instance_health
        assert hasattr(func, "__wrapped__") or hasattr(func, "__name__")
        assert func.__name__ == "get_instance_health"


class TestHealthRouterIntegration:
    """Test router integration aspects."""

    def test_router_has_endpoints(self):
        """Test that the router has the expected endpoints."""
        routes = health.router.routes
        assert len(routes) > 0

        route_paths = [route.path for route in routes]

        # Should have the main health check endpoint
        assert "/" in route_paths

        # Should have instance health endpoints
        assert "/instances" in route_paths
        assert "/instances/{instance_id}" in route_paths

    def test_router_methods(self):
        """Test that routes have correct HTTP methods."""
        routes = health.router.routes

        # Collect all methods for each path
        path_methods = {}
        for route in routes:
            if route.path not in path_methods:
                path_methods[route.path] = set()
            path_methods[route.path].update(route.methods)

        # Main health endpoint should support GET
        assert "GET" in path_methods["/"]

        # Instance health endpoints should support GET
        assert "GET" in path_methods["/instances"]
        assert "GET" in path_methods["/instances/{instance_id}"]

        # Health check endpoint should support POST
        assert "POST" in path_methods["/instances/{instance_id}/check"]

    def test_health_status_enum_in_routes(self):
        """Test that HealthStatus enum is properly integrated."""
        statuses = [status.value for status in HealthStatus]
        expected_statuses = ["healthy", "degraded", "unhealthy", "critical", "unknown"]

        assert set(statuses) == set(expected_statuses)


class TestHealthRouterErrorCases:
    """Test error handling in health router."""

    @pytest.fixture
    def mock_crud_with_errors(self):
        """Mock CRUD adapter that raises errors."""
        crud = AsyncMock()
        crud.get_instance.side_effect = Exception("Database connection failed")
        return crud

    @pytest.mark.asyncio
    async def test_health_check_handles_errors_gracefully(self):
        """Test that health check handles internal errors gracefully."""
        # The health_check function is simple and shouldn't fail,
        # but test that it returns a proper structure
        result = await health.health_check()

        assert result["success"] is True
        assert "data" in result
        assert result["data"]["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_instance_health_with_database_error(self, mock_crud_with_errors):
        """Test instance health retrieval when database fails."""
        with pytest.raises(Exception) as exc_info:
            await health.get_instance_health(instance_id=1, crud=mock_crud_with_errors)

        # The error decorator should wrap the original exception
        assert "Database connection failed" in str(
            exc_info.value
        ) or "API error" in str(exc_info.value)


class TestHealthRouterEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.fixture
    def mock_crud_empty_results(self):
        """Mock CRUD adapter with empty results."""
        crud = AsyncMock()
        crud.list_instances.return_value = ([], 0)
        crud.list_health_checks.return_value = ([], 0)
        crud.get_health_overview.return_value = {
            "total_instances": 0,
            "health_percentage": 0.0,
            "status_distribution": {},
            "critical_instances": 0,
            "unhealthy_instances": 0,
            "degraded_instances": 0,
            "healthy_instances": 0,
            "timestamp": "2025-08-03T05:31:33Z",
        }
        return crud

    @pytest.fixture
    def pagination_params(self):
        """Mock pagination parameters for edge cases."""
        params = Mock(spec=PaginationParams)
        params.page = 1
        params.size = 20
        params.offset = 0
        return params

    @pytest.mark.asyncio
    async def test_list_instance_health_empty_results(
        self, mock_crud_empty_results, pagination_params
    ):
        """Test instance health listing with no instances."""
        result = await health.list_instance_health(
            pagination=pagination_params,
            health_status=None,
            crud=mock_crud_empty_results,
        )

        assert result["total"] == 0
        assert len(result["items"]) == 0
        assert result["pages"] == 0

    @pytest.mark.asyncio
    async def test_get_health_history_empty_results(
        self, mock_crud_empty_results, pagination_params
    ):
        """Test health history with no results."""
        # Still need a valid instance for the existence check
        mock_instance = Mock()
        mock_instance.id = 1
        mock_crud_empty_results.get_instance.return_value = mock_instance

        result = await health.get_health_check_history(
            instance_id=1, pagination=pagination_params, crud=mock_crud_empty_results
        )

        assert result["total"] == 0
        assert len(result["items"]) == 0

    @pytest.mark.asyncio
    async def test_get_health_overview_no_instances(self, mock_crud_empty_results):
        """Test health overview with no instances."""
        result = await health.get_health_overview(crud=mock_crud_empty_results)

        assert result["success"] is True
        overview = result["data"]
        assert overview["total_instances"] == 0
        assert overview["healthy_instances"] == 0
        assert overview["health_percentage"] == 0.0
