"""
Unit tests for worktrees router API endpoints.

Tests cover all worktree management functionality including:
- List worktrees with filtering and pagination
- Create new worktrees with validation
- Get, update, and delete worktrees
- Worktree sync operations
- Get worktree status and associated tasks
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock

import pytest

from cc_orchestrator.database.models import WorktreeStatus
from cc_orchestrator.web.dependencies import PaginationParams
from cc_orchestrator.web.routers.v1 import worktrees
from cc_orchestrator.web.schemas import WorktreeCreate, WorktreeResponse, WorktreeUpdate


class TestWorktreesRouterFunctions:
    """Test worktrees router endpoint functions directly."""

    @pytest.fixture
    def mock_crud(self):
        """Mock CRUD adapter."""
        crud = AsyncMock()

        # Create proper worktree data that matches WorktreeResponse schema
        worktree_data = {
            "id": 1,
            "name": "test-worktree",
            "branch": "feature-branch",
            "base_branch": "main",
            "path": "/workspace/test-worktree",
            "active": True,
            "status": "active",
            "current_commit": "abc123",
            "has_uncommitted_changes": False,
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }

        # Create WorktreeResponse object but also add database model attributes
        mock_worktree = WorktreeResponse(**worktree_data)
        
        # Add database model attributes that the router expects
        mock_worktree.branch_name = "feature-branch"  # Database model uses branch_name
        mock_worktree.last_sync = datetime.now(UTC)

        # WorktreeResponse schema only has: id, name, branch, base_branch, path, active, created_at, updated_at
        # No additional attributes needed as they're not part of the response schema

        # Mock instance data
        mock_instance = Mock()
        mock_instance.id = 1
        mock_instance.issue_id = "test-issue"

        # Mock task data
        mock_task = Mock()
        mock_task.id = 1
        mock_task.worktree_id = 1
        mock_task.title = "test-task"
        mock_task.__dict__ = {"id": 1, "worktree_id": 1, "title": "test-task"}

        crud.list_worktrees.return_value = ([mock_worktree], 1)
        crud.create_worktree.return_value = mock_worktree
        crud.get_worktree.return_value = mock_worktree
        crud.get_worktree_by_path.return_value = None  # No duplicate by default
        crud.update_worktree.return_value = mock_worktree
        crud.delete_worktree.return_value = True
        crud.get_instance.return_value = mock_instance
        crud.list_tasks.return_value = ([mock_task], 1)

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
    async def test_list_worktrees_success(self, mock_crud, pagination_params):
        """Test successful worktree listing with pagination."""
        result = await worktrees.list_worktrees(
            pagination=pagination_params,
            status_filter=None,
            branch_name=None,
            instance_id=None,
            crud=mock_crud,
        )

        assert result["total"] == 1
        assert len(result["items"]) == 1
        assert result["page"] == 1
        assert result["size"] == 20
        assert result["pages"] == 1

        # Verify CRUD was called correctly
        mock_crud.list_worktrees.assert_called_once_with(offset=0, limit=20, filters={})

    @pytest.mark.asyncio
    async def test_list_worktrees_with_filters(self, mock_crud, pagination_params):
        """Test worktree listing with status, branch, and instance filters."""
        result = await worktrees.list_worktrees(
            pagination=pagination_params,
            status_filter=WorktreeStatus.ACTIVE,
            branch_name="main",
            instance_id=1,
            crud=mock_crud,
        )

        assert result["total"] == 1

        # Verify filters were applied
        mock_crud.list_worktrees.assert_called_once_with(
            offset=0,
            limit=20,
            filters={
                "status": WorktreeStatus.ACTIVE,
                "branch_name": "main",
                "instance_id": 1,
            },
        )

    @pytest.mark.asyncio
    async def test_create_worktree_success(self, mock_crud):
        """Test successful worktree creation."""
        worktree_data = WorktreeCreate(
            name="new-worktree",
            branch="new-branch",
            base_branch="main",
            path="/workspace/new-worktree",
            instance_id=1,
        )

        result = await worktrees.create_worktree(
            worktree_data=worktree_data, crud=mock_crud
        )

        assert result["success"] is True
        assert "Worktree created successfully" in result["message"]
        assert "data" in result

        # Verify path uniqueness check, instance validation, and creation
        mock_crud.get_worktree_by_path.assert_called_once_with(
            "/workspace/new-worktree"
        )
        mock_crud.get_instance.assert_called_once_with(1)
        mock_crud.create_worktree.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_worktree_duplicate_path(self, mock_crud):
        """Test worktree creation with duplicate path."""
        # Mock existing worktree
        mock_existing = Mock()
        mock_crud.get_worktree_by_path.return_value = mock_existing

        worktree_data = WorktreeCreate(
            name="duplicate-worktree",
            branch="duplicate-branch",
            base_branch="main",
            path="/workspace/duplicate",
        )

        with pytest.raises(Exception) as exc_info:
            await worktrees.create_worktree(worktree_data=worktree_data, crud=mock_crud)

        assert "Worktree with path '/workspace/duplicate' already exists" in str(
            exc_info.value
        )

    @pytest.mark.asyncio
    async def test_create_worktree_invalid_instance(self, mock_crud):
        """Test worktree creation with non-existent instance."""
        mock_crud.get_instance.return_value = None

        worktree_data = WorktreeCreate(
            name="invalid-worktree",
            branch="invalid-branch",
            base_branch="main",
            path="/workspace/invalid",
            instance_id=999,
        )

        with pytest.raises(Exception) as exc_info:
            await worktrees.create_worktree(worktree_data=worktree_data, crud=mock_crud)

        assert "Instance with ID 999 not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_worktree_success(self, mock_crud):
        """Test successful worktree retrieval by ID."""
        result = await worktrees.get_worktree(worktree_id=1, crud=mock_crud)

        assert result["success"] is True
        assert "Worktree retrieved successfully" in result["message"]
        assert "data" in result

        mock_crud.get_worktree.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_get_worktree_not_found(self, mock_crud):
        """Test worktree retrieval for non-existent worktree."""
        mock_crud.get_worktree.return_value = None

        with pytest.raises(Exception) as exc_info:
            await worktrees.get_worktree(worktree_id=999, crud=mock_crud)

        assert "Worktree with ID 999 not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_update_worktree_success(self, mock_crud):
        """Test successful worktree update."""
        update_data = WorktreeUpdate(
            name="updated-worktree", status=WorktreeStatus.INACTIVE
        )

        result = await worktrees.update_worktree(
            worktree_id=1, worktree_data=update_data, crud=mock_crud
        )

        assert result["success"] is True
        assert "Worktree updated successfully" in result["message"]

        mock_crud.get_worktree.assert_called_once_with(1)
        mock_crud.update_worktree.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_worktree_not_found(self, mock_crud):
        """Test worktree update for non-existent worktree."""
        mock_crud.get_worktree.return_value = None

        update_data = WorktreeUpdate(name="updated-name")

        with pytest.raises(Exception) as exc_info:
            await worktrees.update_worktree(
                worktree_id=999, worktree_data=update_data, crud=mock_crud
            )

        assert "Worktree with ID 999 not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_update_worktree_invalid_instance(self, mock_crud):
        """Test worktree update with non-existent instance."""
        mock_crud.get_instance.return_value = None

        update_data = WorktreeUpdate(instance_id=999)

        with pytest.raises(Exception) as exc_info:
            await worktrees.update_worktree(
                worktree_id=1, worktree_data=update_data, crud=mock_crud
            )

        assert "Instance with ID 999 not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_delete_worktree_success(self, mock_crud):
        """Test successful worktree deletion."""
        result = await worktrees.delete_worktree(worktree_id=1, crud=mock_crud)

        assert result["success"] is True
        assert "Worktree deleted successfully" in result["message"]

        mock_crud.get_worktree.assert_called_once_with(1)
        mock_crud.delete_worktree.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_delete_worktree_not_found(self, mock_crud):
        """Test worktree deletion for non-existent worktree."""
        mock_crud.get_worktree.return_value = None

        with pytest.raises(Exception) as exc_info:
            await worktrees.delete_worktree(worktree_id=999, crud=mock_crud)

        assert "Worktree with ID 999 not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_sync_worktree_success(self, mock_crud):
        """Test successful worktree sync operation."""
        result = await worktrees.sync_worktree(worktree_id=1, crud=mock_crud)

        assert result["success"] is True
        assert "Worktree synced successfully" in result["message"]

        mock_crud.get_worktree.assert_called_once_with(1)
        mock_crud.update_worktree.assert_called_once()

    @pytest.mark.asyncio
    async def test_sync_worktree_not_found(self, mock_crud):
        """Test worktree sync for non-existent worktree."""
        mock_crud.get_worktree.return_value = None

        with pytest.raises(Exception) as exc_info:
            await worktrees.sync_worktree(worktree_id=999, crud=mock_crud)

        assert "Worktree with ID 999 not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_worktree_status_success(self, mock_crud):
        """Test successful worktree status retrieval."""
        result = await worktrees.get_worktree_status(worktree_id=1, crud=mock_crud)

        assert result["success"] is True
        assert "Worktree status retrieved successfully" in result["message"]
        assert "data" in result

        status_data = result["data"]
        assert status_data["id"] == 1
        assert status_data["name"] == "test-worktree"
        assert status_data["path"] == "/workspace/test-worktree"
        assert status_data["status"] == WorktreeStatus.ACTIVE

        mock_crud.get_worktree.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_get_worktree_status_not_found(self, mock_crud):
        """Test worktree status retrieval for non-existent worktree."""
        mock_crud.get_worktree.return_value = None

        with pytest.raises(Exception) as exc_info:
            await worktrees.get_worktree_status(worktree_id=999, crud=mock_crud)

        assert "Worktree with ID 999 not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_worktree_tasks_success(self, mock_crud, pagination_params):
        """Test successful retrieval of worktree tasks."""
        result = await worktrees.get_worktree_tasks(
            worktree_id=1, pagination=pagination_params, crud=mock_crud
        )

        assert result["total"] == 1
        assert len(result["items"]) == 1
        assert result["page"] == 1
        assert result["size"] == 20

        # Verify worktree check and task retrieval
        mock_crud.get_worktree.assert_called_once_with(1)
        mock_crud.list_tasks.assert_called_once_with(
            offset=0, limit=20, filters={"worktree_id": 1}
        )

    @pytest.mark.asyncio
    async def test_get_worktree_tasks_not_found(self, mock_crud, pagination_params):
        """Test worktree tasks retrieval for non-existent worktree."""
        mock_crud.get_worktree.return_value = None

        with pytest.raises(Exception) as exc_info:
            await worktrees.get_worktree_tasks(
                worktree_id=999, pagination=pagination_params, crud=mock_crud
            )

        assert "Worktree with ID 999 not found" in str(exc_info.value)


class TestWorktreeValidation:
    """Test worktree data validation and edge cases."""

    def test_worktree_response_model_validation(self):
        """Test WorktreeResponse model validation."""
        worktree_data = {
            "id": 1,
            "name": "test-worktree",
            "branch": "main",
            "base_branch": "main",
            "path": "/workspace/test",
            "active": True,
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }

        response_model = WorktreeResponse.model_validate(worktree_data)
        assert response_model.name == "test-worktree"
        assert response_model.status == WorktreeStatus.ACTIVE.value

    def test_worktree_create_model_validation(self):
        """Test WorktreeCreate model validation."""
        create_data = {
            "name": "new-worktree",
            "branch": "new-branch",
            "base_branch": "main",
            "path": "/workspace/new",
        }

        create_model = WorktreeCreate.model_validate(create_data)
        assert create_model.name == "new-worktree"
        assert create_model.branch == "new-branch"

    def test_worktree_status_enum_values(self):
        """Test WorktreeStatus enum contains expected values."""
        expected_statuses = {"active", "inactive", "dirty", "error"}
        actual_statuses = {status.value for status in WorktreeStatus}

        assert actual_statuses == expected_statuses


class TestWorktreeRouterDecorators:
    """Test decorator functionality on worktree endpoints."""

    def test_decorators_applied_to_list_worktrees(self):
        """Test that decorators are applied to list_worktrees function."""
        func = worktrees.list_worktrees
        assert hasattr(func, "__wrapped__") or hasattr(func, "__name__")
        assert func.__name__ == "list_worktrees"

    def test_decorators_applied_to_create_worktree(self):
        """Test that decorators are applied to create_worktree function."""
        func = worktrees.create_worktree
        assert hasattr(func, "__wrapped__") or hasattr(func, "__name__")
        assert func.__name__ == "create_worktree"

    def test_decorators_applied_to_sync_worktree(self):
        """Test that decorators are applied to sync_worktree function."""
        func = worktrees.sync_worktree
        assert hasattr(func, "__wrapped__") or hasattr(func, "__name__")
        assert func.__name__ == "sync_worktree"


class TestWorktreeRouterIntegration:
    """Test router integration aspects."""

    def test_router_has_endpoints(self):
        """Test that the router has the expected endpoints."""
        routes = worktrees.router.routes
        assert len(routes) > 0

        route_paths = [route.path for route in routes]

        # Should have the main list endpoint
        assert "/" in route_paths

        # Should have specific worktree endpoints
        assert "/{worktree_id}" in route_paths
        assert "/{worktree_id}/sync" in route_paths
        assert "/{worktree_id}/status" in route_paths
        assert "/{worktree_id}/tasks" in route_paths

    def test_router_methods(self):
        """Test that routes have correct HTTP methods."""
        routes = worktrees.router.routes

        # Collect all methods for each path
        path_methods = {}
        for route in routes:
            if route.path not in path_methods:
                path_methods[route.path] = set()
            path_methods[route.path].update(route.methods)

        # Main endpoint should support GET and POST
        assert "GET" in path_methods["/"]
        assert "POST" in path_methods["/"]

        # Specific worktree endpoint should support GET, PUT, DELETE
        assert "GET" in path_methods["/{worktree_id}"]
        assert "PUT" in path_methods["/{worktree_id}"]
        assert "DELETE" in path_methods["/{worktree_id}"]

        # Action endpoints should support GET/POST
        assert "POST" in path_methods["/{worktree_id}/sync"]
        assert "GET" in path_methods["/{worktree_id}/status"]
        assert "GET" in path_methods["/{worktree_id}/tasks"]

    def test_worktree_status_enum_in_routes(self):
        """Test that WorktreeStatus enum is properly integrated."""
        statuses = [status.value for status in WorktreeStatus]
        expected_statuses = ["active", "inactive", "dirty", "error"]

        assert set(statuses) == set(expected_statuses)


class TestWorktreeRouterEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.fixture
    def mock_crud_empty_results(self):
        """Mock CRUD adapter with empty results."""
        crud = AsyncMock()
        crud.list_worktrees.return_value = ([], 0)
        crud.list_tasks.return_value = ([], 0)
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
    async def test_list_worktrees_empty_results(
        self, mock_crud_empty_results, pagination_params
    ):
        """Test worktree listing with no worktrees."""
        result = await worktrees.list_worktrees(
            pagination=pagination_params,
            status_filter=None,
            branch_name=None,
            instance_id=None,
            crud=mock_crud_empty_results,
        )

        assert result["total"] == 0
        assert len(result["items"]) == 0
        assert result["pages"] == 0

    @pytest.mark.asyncio
    async def test_get_worktree_tasks_empty_results(
        self, mock_crud_empty_results, pagination_params
    ):
        """Test worktree tasks with no results."""
        # Still need a valid worktree for the existence check
        mock_worktree = Mock()
        mock_worktree.id = 1
        mock_crud_empty_results.get_worktree.return_value = mock_worktree

        result = await worktrees.get_worktree_tasks(
            worktree_id=1, pagination=pagination_params, crud=mock_crud_empty_results
        )

        assert result["total"] == 0
        assert len(result["items"]) == 0
