"""
Comprehensive test suite for worktrees router targeting 100% coverage.

This test file is specifically designed to cover all 96 statements in the worktrees router
and push coverage from 42% to the highest possible level. It focuses on:

1. All HTTP endpoints for worktree CRUD operations
2. Request/response validation and serialization
3. Database integration via dependency injection
4. Query parameter handling and filtering
5. Worktree lifecycle management
6. Error handling and HTTP status codes
7. All conditional branches and edge cases
8. Path parameter validation
9. JSON body processing
10. Worktree activation/deactivation operations
"""

from contextlib import contextmanager
from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import HTTPException, status

from cc_orchestrator.database.models import WorktreeStatus
from cc_orchestrator.web.dependencies import PaginationParams
from cc_orchestrator.web.routers.v1 import worktrees
from cc_orchestrator.web.schemas import (
    WorktreeCreate,
    WorktreeUpdate,
)


class TestWorktreesRouterComprehensiveCoverage:
    """Comprehensive tests targeting 100% coverage of worktrees router."""

    @contextmanager
    def mock_worktree_response(self, return_value=None):
        """Context manager to mock WorktreeResponse.model_validate."""
        if return_value is None:
            return_value = {
                "id": 1,
                "name": "test-worktree",
                "branch_name": "feature/test",
                "base_branch": "main",
                "path": "/workspace/test-worktree",
                "active": True,
                "created_at": datetime.now(UTC),
                "updated_at": datetime.now(UTC),
            }
        with patch(
            "cc_orchestrator.web.routers.v1.worktrees.WorktreeResponse"
        ) as mock_response:
            mock_response.model_validate.return_value = return_value
            yield mock_response

    @pytest.fixture
    def mock_worktree_data(self):
        """Create a proper worktree response dict that can be validated."""
        return {
            "id": 1,
            "name": "test-worktree",
            "path": "/workspace/test-worktree",
            "branch_name": "feature/test",
            "base_branch": "main",
            "active": True,
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }

    @pytest.fixture
    def mock_worktree_model(self):
        """Create a mock worktree model with all database fields."""
        mock = Mock()
        mock.id = 1
        mock.name = "test-worktree"
        mock.path = "/workspace/test-worktree"
        mock.branch_name = "feature/test"
        mock.status = WorktreeStatus.ACTIVE
        mock.current_commit = "abc123"
        mock.has_uncommitted_changes = False
        mock.last_sync = datetime.now(UTC)
        mock.created_at = datetime.now(UTC)
        mock.updated_at = datetime.now(UTC)
        return mock

    @pytest.fixture
    def mock_task_data(self):
        """Create comprehensive mock task data."""
        task_data = {
            "id": 1,
            "title": "test-task",
            "description": "Test Description",
            "worktree_id": 1,
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }
        # Create a mock that supports dict conversion
        mock = Mock()
        for key, value in task_data.items():
            setattr(mock, key, value)
        mock.__dict__ = task_data
        return mock

    @pytest.fixture
    def mock_instance_data(self):
        """Create mock instance data."""
        return Mock(id=1, issue_id="TEST-001")

    @pytest.fixture
    def mock_crud(self):
        """Create a comprehensive mock CRUD adapter."""
        crud = AsyncMock()
        # Setup default return values
        crud.list_worktrees.return_value = ([], 0)
        crud.get_worktree.return_value = None
        crud.get_worktree_by_path.return_value = None
        crud.get_instance.return_value = None
        crud.create_worktree.return_value = Mock()
        crud.update_worktree.return_value = Mock()
        crud.delete_worktree.return_value = None
        crud.list_tasks.return_value = ([], 0)
        return crud

    @pytest.fixture
    def pagination_params(self):
        """Create pagination parameters."""
        return PaginationParams(page=1, size=20)

    # LIST WORKTREES TESTS - Lines 35-76

    @pytest.mark.asyncio
    async def test_list_worktrees_no_filters(
        self, mock_crud, pagination_params, mock_worktree_model
    ):
        """Test list_worktrees with no filters - covers lines 51-59, 61-75."""
        # Test with no filters applied
        mock_crud.list_worktrees.return_value = ([mock_worktree_model], 1)

        with self.mock_worktree_response():
            result = await worktrees.list_worktrees(
                pagination=pagination_params,
                status_filter=None,
                branch_name=None,
                instance_id=None,
                crud=mock_crud,
            )

        # Verify filters dict is empty
        mock_crud.list_worktrees.assert_called_once_with(offset=0, limit=20, filters={})
        assert result["total"] == 1
        assert result["page"] == 1
        assert result["size"] == 20
        assert result["pages"] == 1

    @pytest.mark.asyncio
    async def test_list_worktrees_with_status_filter(
        self, mock_crud, pagination_params, mock_worktree_model
    ):
        """Test list_worktrees with status filter - covers lines 53-54."""
        mock_crud.list_worktrees.return_value = ([mock_worktree_model], 1)

        with self.mock_worktree_response():
            result = await worktrees.list_worktrees(
                pagination=pagination_params,
                status_filter=WorktreeStatus.ACTIVE,
                branch_name=None,
                instance_id=None,
                crud=mock_crud,
            )

        # Verify status filter is applied
        expected_filters = {"status": WorktreeStatus.ACTIVE}
        mock_crud.list_worktrees.assert_called_once_with(
            offset=0, limit=20, filters=expected_filters
        )

    @pytest.mark.asyncio
    async def test_list_worktrees_with_branch_filter(
        self, mock_crud, pagination_params, mock_worktree_model
    ):
        """Test list_worktrees with branch filter - covers lines 55-56."""
        mock_crud.list_worktrees.return_value = ([mock_worktree_model], 1)

        with self.mock_worktree_response():
            result = await worktrees.list_worktrees(
                pagination=pagination_params,
                status_filter=None,
                branch_name="feature/test",
                instance_id=None,
                crud=mock_crud,
            )

        # Verify branch filter is applied
        expected_filters = {"branch_name": "feature/test"}
        mock_crud.list_worktrees.assert_called_once_with(
            offset=0, limit=20, filters=expected_filters
        )

    @pytest.mark.asyncio
    async def test_list_worktrees_with_instance_id_filter(
        self, mock_crud, pagination_params, mock_worktree_model
    ):
        """Test list_worktrees with instance_id filter - covers lines 57-58."""
        mock_crud.list_worktrees.return_value = ([mock_worktree_model], 1)

        with self.mock_worktree_response():
            result = await worktrees.list_worktrees(
                pagination=pagination_params,
                status_filter=None,
                branch_name=None,
                instance_id=123,
                crud=mock_crud,
            )

        # Verify instance_id filter is applied
        expected_filters = {"instance_id": 123}
        mock_crud.list_worktrees.assert_called_once_with(
            offset=0, limit=20, filters=expected_filters
        )

    @pytest.mark.asyncio
    async def test_list_worktrees_with_all_filters(
        self, mock_crud, pagination_params, mock_worktree_model
    ):
        """Test list_worktrees with all filters - covers all filter lines 53-58."""
        mock_crud.list_worktrees.return_value = ([mock_worktree_model], 1)

        with self.mock_worktree_response():
            result = await worktrees.list_worktrees(
                pagination=pagination_params,
                status_filter=WorktreeStatus.INACTIVE,
                branch_name="main",
                instance_id=456,
                crud=mock_crud,
            )

        # Verify all filters are applied
        expected_filters = {
            "status": WorktreeStatus.INACTIVE,
            "branch_name": "main",
            "instance_id": 456,
        }
        mock_crud.list_worktrees.assert_called_once_with(
            offset=0, limit=20, filters=expected_filters
        )

    @pytest.mark.asyncio
    async def test_list_worktrees_pagination_calculation(
        self, mock_crud, pagination_params
    ):
        """Test pagination calculation edge cases - covers lines 75."""
        # Test with total that doesn't divide evenly
        mock_crud.list_worktrees.return_value = ([], 21)  # 21 items with size 20

        result = await worktrees.list_worktrees(
            pagination=pagination_params,
            status_filter=None,
            branch_name=None,
            instance_id=None,
            crud=mock_crud,
        )

        # Should calculate pages as (21 + 20 - 1) // 20 = 2
        assert result["pages"] == 2

    @pytest.mark.asyncio
    async def test_list_worktrees_zero_total(self, mock_crud, pagination_params):
        """Test with zero total worktrees - covers lines 75."""
        mock_crud.list_worktrees.return_value = ([], 0)

        result = await worktrees.list_worktrees(
            pagination=pagination_params,
            status_filter=None,
            branch_name=None,
            instance_id=None,
            crud=mock_crud,
        )

        # Should calculate pages as (0 + 20 - 1) // 20 = 0
        assert result["pages"] == 0

    # CREATE WORKTREE TESTS - Lines 82-123

    @pytest.mark.asyncio
    async def test_create_worktree_success_no_path(
        self, mock_crud, mock_worktree_model
    ):
        """Test successful worktree creation with no path - covers lines 97-100."""
        worktree_data = WorktreeCreate(
            name="test-worktree",
            branch_name="feature/test",  # Schema uses 'branch_name'
            path=None,  # No path provided
            instance_id=None,
        )

        mock_crud.get_worktree_by_path.return_value = None  # Path doesn't exist
        mock_crud.create_worktree.return_value = mock_worktree_model

        with self.mock_worktree_response():
            result = await worktrees.create_worktree(
                worktree_data=worktree_data,
                crud=mock_crud,
            )

        # Should not call get_worktree_by_path when path is None
        mock_crud.get_worktree_by_path.assert_not_called()
        assert result["success"] is True
        assert result["message"] == "Worktree created successfully"

    @pytest.mark.asyncio
    async def test_create_worktree_success_with_path(
        self, mock_crud, mock_worktree_model
    ):
        """Test successful worktree creation with path - covers lines 97-98."""
        worktree_data = WorktreeCreate(
            name="test-worktree",
            branch_name="feature/test",
            path="/workspace/test",
            instance_id=None,
        )

        mock_crud.get_worktree_by_path.return_value = None  # Path doesn't exist
        mock_crud.create_worktree.return_value = mock_worktree_model

        with self.mock_worktree_response():
            result = await worktrees.create_worktree(
                worktree_data=worktree_data,
                crud=mock_crud,
            )

        # Should check if path exists
        mock_crud.get_worktree_by_path.assert_called_once_with("/workspace/test")
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_create_worktree_path_conflict(self, mock_crud):
        """Test worktree creation with existing path - covers lines 101-105."""
        worktree_data = WorktreeCreate(
            name="test-worktree",
            branch_name="feature/test",
            path="/workspace/existing",
        )

        # Mock existing worktree with same path
        existing_worktree = Mock()
        mock_crud.get_worktree_by_path.return_value = existing_worktree

        with pytest.raises(HTTPException) as exc_info:
            await worktrees.create_worktree(
                worktree_data=worktree_data,
                crud=mock_crud,
            )

        assert exc_info.value.status_code == status.HTTP_409_CONFLICT
        assert "already exists" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_create_worktree_with_valid_instance(
        self, mock_crud, mock_worktree_model, mock_instance_data
    ):
        """Test worktree creation with valid instance - covers lines 108-114."""
        worktree_data = WorktreeCreate(
            name="test-worktree",
            branch_name="feature/test",
            path="/workspace/test",
            instance_id=1,
        )

        mock_crud.get_worktree_by_path.return_value = None
        mock_crud.get_instance.return_value = mock_instance_data  # Instance exists
        mock_crud.create_worktree.return_value = mock_worktree_model

        with self.mock_worktree_response():
            result = await worktrees.create_worktree(
                worktree_data=worktree_data,
                crud=mock_crud,
            )

        mock_crud.get_instance.assert_called_once_with(1)
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_create_worktree_with_invalid_instance(self, mock_crud):
        """Test worktree creation with invalid instance - covers lines 108-114."""
        worktree_data = WorktreeCreate(
            name="test-worktree",
            branch_name="feature/test",
            path="/workspace/test",
            instance_id=999,  # Non-existent instance
        )

        mock_crud.get_worktree_by_path.return_value = None
        mock_crud.get_instance.return_value = None  # Instance doesn't exist

        with pytest.raises(HTTPException) as exc_info:
            await worktrees.create_worktree(
                worktree_data=worktree_data,
                crud=mock_crud,
            )

        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "not found" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_create_worktree_no_instance_id(self, mock_crud, mock_worktree_model):
        """Test worktree creation without instance_id - covers lines 108."""
        worktree_data = WorktreeCreate(
            name="test-worktree",
            branch_name="feature/test",
            path="/workspace/test",
            instance_id=None,  # No instance ID
        )

        mock_crud.get_worktree_by_path.return_value = None
        mock_crud.create_worktree.return_value = mock_worktree_model

        with self.mock_worktree_response():
            result = await worktrees.create_worktree(
                worktree_data=worktree_data,
                crud=mock_crud,
            )

        # Should not validate instance when instance_id is None
        mock_crud.get_instance.assert_not_called()
        assert result["success"] is True

    # GET WORKTREE TESTS - Lines 129-149

    @pytest.mark.asyncio
    async def test_get_worktree_success(self, mock_crud, mock_worktree_data):
        """Test successful worktree retrieval - covers lines 138, 145-148."""
        mock_crud.get_worktree.return_value = mock_worktree_data

        result = await worktrees.get_worktree(
            worktree_id=1,
            crud=mock_crud,
        )

        mock_crud.get_worktree.assert_called_once_with(1)
        assert result["success"] is True
        assert result["message"] == "Worktree retrieved successfully"
        assert "data" in result

    @pytest.mark.asyncio
    async def test_get_worktree_not_found(self, mock_crud):
        """Test worktree not found - covers lines 139-143."""
        mock_crud.get_worktree.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await worktrees.get_worktree(
                worktree_id=999,
                crud=mock_crud,
            )

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in str(exc_info.value.detail)

    # UPDATE WORKTREE TESTS - Lines 155-191

    @pytest.mark.asyncio
    async def test_update_worktree_success(self, mock_crud, mock_worktree_data):
        """Test successful worktree update - covers lines 167, 184-190."""
        update_data = WorktreeUpdate(
            name="updated-name",
            branch_name="updated-branch",
        )

        mock_crud.get_worktree.return_value = mock_worktree_data  # Exists
        mock_crud.update_worktree.return_value = mock_worktree_data

        result = await worktrees.update_worktree(
            worktree_data=update_data,
            worktree_id=1,
            crud=mock_crud,
        )

        mock_crud.get_worktree.assert_called_once_with(1)
        mock_crud.update_worktree.assert_called_once()
        assert result["success"] is True
        assert result["message"] == "Worktree updated successfully"

    @pytest.mark.asyncio
    async def test_update_worktree_not_found(self, mock_crud):
        """Test update worktree not found - covers lines 167-172."""
        update_data = WorktreeUpdate(name="updated-name")

        mock_crud.get_worktree.return_value = None  # Doesn't exist

        with pytest.raises(HTTPException) as exc_info:
            await worktrees.update_worktree(
                worktree_data=update_data,
                worktree_id=999,
                crud=mock_crud,
            )

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_update_worktree_with_valid_instance(
        self, mock_crud, mock_worktree_data, mock_instance_data
    ):
        """Test update worktree with valid instance - covers lines 175-181."""
        update_data = WorktreeUpdate(
            name="updated-name",
            instance_id=1,
        )

        mock_crud.get_worktree.return_value = mock_worktree_data  # Exists
        mock_crud.get_instance.return_value = mock_instance_data  # Instance exists
        mock_crud.update_worktree.return_value = mock_worktree_data

        result = await worktrees.update_worktree(
            worktree_data=update_data,
            worktree_id=1,
            crud=mock_crud,
        )

        mock_crud.get_instance.assert_called_once_with(1)
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_update_worktree_with_invalid_instance(
        self, mock_crud, mock_worktree_data
    ):
        """Test update worktree with invalid instance - covers lines 175-181."""
        update_data = WorktreeUpdate(
            name="updated-name",
            instance_id=999,  # Non-existent
        )

        mock_crud.get_worktree.return_value = mock_worktree_data  # Worktree exists
        mock_crud.get_instance.return_value = None  # Instance doesn't exist

        with pytest.raises(HTTPException) as exc_info:
            await worktrees.update_worktree(
                worktree_data=update_data,
                worktree_id=1,
                crud=mock_crud,
            )

        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "not found" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_update_worktree_no_instance_id(self, mock_crud, mock_worktree_data):
        """Test update worktree without instance_id - covers lines 175."""
        update_data = WorktreeUpdate(
            name="updated-name",
            instance_id=None,  # No instance ID
        )

        mock_crud.get_worktree.return_value = mock_worktree_data
        mock_crud.update_worktree.return_value = mock_worktree_data

        result = await worktrees.update_worktree(
            worktree_data=update_data,
            worktree_id=1,
            crud=mock_crud,
        )

        # Should not validate instance when instance_id is None
        mock_crud.get_instance.assert_not_called()
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_update_worktree_exclude_unset(self, mock_crud, mock_worktree_data):
        """Test update worktree exclude_unset behavior - covers line 184."""
        update_data = WorktreeUpdate(name="updated-name")  # Only name set

        mock_crud.get_worktree.return_value = mock_worktree_data
        mock_crud.update_worktree.return_value = mock_worktree_data

        await worktrees.update_worktree(
            worktree_data=update_data,
            worktree_id=1,
            crud=mock_crud,
        )

        # Check that only set fields are passed to update
        call_args = mock_crud.update_worktree.call_args
        update_dict = call_args[0][1]
        assert "name" in update_dict
        assert "branch_name" not in update_dict  # Should be excluded as unset

    # DELETE WORKTREE TESTS - Lines 197-218

    @pytest.mark.asyncio
    async def test_delete_worktree_success(self, mock_crud, mock_worktree_data):
        """Test successful worktree deletion - covers lines 208, 216-218."""
        mock_crud.get_worktree.return_value = mock_worktree_data  # Exists

        result = await worktrees.delete_worktree(
            worktree_id=1,
            crud=mock_crud,
        )

        mock_crud.get_worktree.assert_called_once_with(1)
        mock_crud.delete_worktree.assert_called_once_with(1)
        assert result["success"] is True
        assert result["message"] == "Worktree deleted successfully"
        assert result["data"] is None

    @pytest.mark.asyncio
    async def test_delete_worktree_not_found(self, mock_crud):
        """Test delete worktree not found - covers lines 208-213."""
        mock_crud.get_worktree.return_value = None  # Doesn't exist

        with pytest.raises(HTTPException) as exc_info:
            await worktrees.delete_worktree(
                worktree_id=999,
                crud=mock_crud,
            )

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in str(exc_info.value.detail)

    # SYNC WORKTREE TESTS - Lines 224-253

    @pytest.mark.asyncio
    async def test_sync_worktree_success(self, mock_crud, mock_worktree_data):
        """Test successful worktree sync - covers lines 234, 243-252."""
        mock_crud.get_worktree.return_value = mock_worktree_data  # Exists
        mock_crud.update_worktree.return_value = mock_worktree_data

        with patch("datetime.datetime") as mock_datetime:
            mock_now = datetime(2023, 1, 1, 12, 0, 0)
            mock_datetime.now.return_value = mock_now

            result = await worktrees.sync_worktree(
                worktree_id=1,
                crud=mock_crud,
            )

        mock_crud.get_worktree.assert_called_once_with(1)
        mock_crud.update_worktree.assert_called_once_with(1, {"last_sync": mock_now})
        assert result["success"] is True
        assert result["message"] == "Worktree synced successfully"

    @pytest.mark.asyncio
    async def test_sync_worktree_not_found(self, mock_crud):
        """Test sync worktree not found - covers lines 234-239."""
        mock_crud.get_worktree.return_value = None  # Doesn't exist

        with pytest.raises(HTTPException) as exc_info:
            await worktrees.sync_worktree(
                worktree_id=999,
                crud=mock_crud,
            )

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in str(exc_info.value.detail)

    # GET WORKTREE STATUS TESTS - Lines 259-290

    @pytest.mark.asyncio
    async def test_get_worktree_status_success(self, mock_crud, mock_worktree_model):
        """Test successful worktree status retrieval - covers lines 268, 275-289."""
        mock_crud.get_worktree.return_value = mock_worktree_model

        result = await worktrees.get_worktree_status(
            worktree_id=1,
            crud=mock_crud,
        )

        mock_crud.get_worktree.assert_called_once_with(1)
        assert result["success"] is True
        assert result["message"] == "Worktree status retrieved successfully"

        # Verify all status fields are included
        status_data = result["data"]
        assert "id" in status_data
        assert "name" in status_data
        assert "path" in status_data
        assert "branch_name" in status_data
        assert "status" in status_data
        assert "current_commit" in status_data
        assert "has_uncommitted_changes" in status_data
        assert "last_sync" in status_data

    @pytest.mark.asyncio
    async def test_get_worktree_status_not_found(self, mock_crud):
        """Test get worktree status not found - covers lines 268-273."""
        mock_crud.get_worktree.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await worktrees.get_worktree_status(
                worktree_id=999,
                crud=mock_crud,
            )

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in str(exc_info.value.detail)

    # GET WORKTREE TASKS TESTS - Lines 296-329

    @pytest.mark.asyncio
    async def test_get_worktree_tasks_success(
        self, mock_crud, mock_worktree_data, mock_task_data, pagination_params
    ):
        """Test successful worktree tasks retrieval - covers lines 309, 317-328."""
        mock_crud.get_worktree.return_value = mock_worktree_data
        mock_crud.list_tasks.return_value = ([mock_task_data], 1)

        result = await worktrees.get_worktree_tasks(
            worktree_id=1,
            pagination=pagination_params,
            crud=mock_crud,
        )

        mock_crud.get_worktree.assert_called_once_with(1)
        mock_crud.list_tasks.assert_called_once_with(
            offset=0,
            limit=20,
            filters={"worktree_id": 1},
        )
        assert result["total"] == 1
        assert result["page"] == 1
        assert result["size"] == 20
        assert len(result["items"]) == 1
        # Verify task is converted to dict via __dict__ (line 324)
        assert isinstance(result["items"][0], dict)

    @pytest.mark.asyncio
    async def test_get_worktree_tasks_not_found(self, mock_crud, pagination_params):
        """Test get worktree tasks not found - covers lines 309-314."""
        mock_crud.get_worktree.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await worktrees.get_worktree_tasks(
                worktree_id=999,
                pagination=pagination_params,
                crud=mock_crud,
            )

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_worktree_tasks_pagination_calculation(
        self, mock_crud, mock_worktree_data, pagination_params
    ):
        """Test worktree tasks pagination calculation - covers line 328."""
        mock_crud.get_worktree.return_value = mock_worktree_data
        mock_crud.list_tasks.return_value = ([], 25)  # 25 items with size 20

        result = await worktrees.get_worktree_tasks(
            worktree_id=1,
            pagination=pagination_params,
            crud=mock_crud,
        )

        # Should calculate pages as (25 + 20 - 1) // 20 = 2
        assert result["pages"] == 2

    # DEPENDENCY AND VALIDATION TESTS

    @pytest.mark.asyncio
    async def test_all_endpoints_use_dependencies(
        self, mock_crud, pagination_params, mock_worktree_model
    ):
        """Test that all endpoints properly use their dependencies."""
        mock_crud.get_worktree.return_value = mock_worktree_model
        mock_crud.list_worktrees.return_value = ([mock_worktree_model], 1)

        # Test that endpoints accept dependency-injected parameters
        # This ensures the Depends() decorators are working

        with self.mock_worktree_response():
            # List endpoint
            await worktrees.list_worktrees(
                pagination=pagination_params,
                status_filter=None,
                branch_name=None,
                instance_id=None,
                crud=mock_crud,
            )

            # Get endpoint
            await worktrees.get_worktree(worktree_id=1, crud=mock_crud)

        # Status endpoint - doesn't need response mocking
        await worktrees.get_worktree_status(worktree_id=1, crud=mock_crud)

        # Tasks endpoint
        mock_crud.list_tasks.return_value = ([], 0)
        await worktrees.get_worktree_tasks(
            worktree_id=1,
            pagination=pagination_params,
            crud=mock_crud,
        )

    # DECORATOR TESTS (track_api_performance and handle_api_errors)

    @pytest.mark.asyncio
    async def test_decorators_applied(self):
        """Test that decorators are applied to all endpoints."""
        # Verify decorators exist on endpoints
        assert hasattr(worktrees.list_worktrees, "__wrapped__")
        assert hasattr(worktrees.create_worktree, "__wrapped__")
        assert hasattr(worktrees.get_worktree, "__wrapped__")
        assert hasattr(worktrees.update_worktree, "__wrapped__")
        assert hasattr(worktrees.delete_worktree, "__wrapped__")
        assert hasattr(worktrees.sync_worktree, "__wrapped__")
        assert hasattr(worktrees.get_worktree_status, "__wrapped__")
        assert hasattr(worktrees.get_worktree_tasks, "__wrapped__")

    # EDGE CASE TESTS

    @pytest.mark.asyncio
    async def test_model_validate_called_properly(self, mock_crud, mock_worktree_model):
        """Test that WorktreeResponse.model_validate is called properly."""
        mock_crud.get_worktree.return_value = mock_worktree_model

        with patch(
            "cc_orchestrator.web.routers.v1.worktrees.WorktreeResponse"
        ) as mock_response:
            mock_response.model_validate.return_value = {"id": 1, "name": "test"}

            result = await worktrees.get_worktree(worktree_id=1, crud=mock_crud)

            mock_response.model_validate.assert_called_once_with(mock_worktree_model)

    @pytest.mark.asyncio
    async def test_create_worktree_model_dump_called(
        self, mock_crud, mock_worktree_model
    ):
        """Test that model_dump is called on create data."""
        worktree_data = WorktreeCreate(
            name="test",
            branch_name="main",
        )

        mock_crud.get_worktree_by_path.return_value = None
        mock_crud.create_worktree.return_value = mock_worktree_model

        with self.mock_worktree_response():
            await worktrees.create_worktree(worktree_data=worktree_data, crud=mock_crud)

        # Verify create_worktree was called with model_dump result
        mock_crud.create_worktree.assert_called_once()
        call_args = mock_crud.create_worktree.call_args[0][0]
        assert isinstance(call_args, dict)  # Should be model_dump result

    @pytest.mark.asyncio
    async def test_comprehensive_coverage_all_branches(
        self, mock_crud, pagination_params
    ):
        """Test comprehensive edge cases to ensure full branch coverage."""

        # Test empty worktree list with various pagination scenarios
        mock_crud.list_worktrees.return_value = ([], 0)

        with self.mock_worktree_response():
            result = await worktrees.list_worktrees(
                pagination=PaginationParams(page=2, size=50),  # Different pagination
                status_filter=WorktreeStatus.ERROR,  # Different status
                branch_name="develop",  # Different branch
                instance_id=999,  # Different instance
                crud=mock_crud,
            )

        assert result["pages"] == 0
        assert result["total"] == 0
        assert result["page"] == 2
        assert result["size"] == 50

    # ERROR RESPONSE FORMAT TESTS

    @pytest.mark.asyncio
    async def test_error_responses_format(self, mock_crud):
        """Test that error responses have correct format and status codes."""
        errors_to_test = [
            # (operation, expected_status, setup_mock)
            (
                lambda: worktrees.get_worktree(worktree_id=1, crud=mock_crud),
                status.HTTP_404_NOT_FOUND,
                lambda: setattr(
                    mock_crud, "get_worktree", AsyncMock(return_value=None)
                ),
            ),
            (
                lambda: worktrees.delete_worktree(worktree_id=1, crud=mock_crud),
                status.HTTP_404_NOT_FOUND,
                lambda: setattr(
                    mock_crud, "get_worktree", AsyncMock(return_value=None)
                ),
            ),
        ]

        for operation, expected_status, setup in errors_to_test:
            setup()
            with pytest.raises(HTTPException) as exc_info:
                await operation()
            assert exc_info.value.status_code == expected_status
            assert isinstance(exc_info.value.detail, str)
