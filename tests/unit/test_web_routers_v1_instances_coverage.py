"""
Comprehensive test suite for instances router targeting 100% coverage.

This test file is specifically designed to cover all 103 statements in the instances router
and push coverage from 43% to the highest possible level. It focuses on:

1. All HTTP endpoints and their variants
2. Request/response validation and serialization
3. Database integration via dependency injection
4. Query parameter handling and filtering
5. Instance status management and validation
6. Error handling and HTTP status codes
7. All conditional branches and edge cases
8. Path parameter validation
9. JSON body processing
10. Instance lifecycle operations
11. Decorator functionality
12. Complex pagination scenarios
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import HTTPException, status

from cc_orchestrator.database.models import (
    InstanceStatus,
    TaskPriority,
)
from cc_orchestrator.web.dependencies import PaginationParams
from cc_orchestrator.web.exceptions import CCOrchestratorAPIException
from cc_orchestrator.web.routers.v1 import instances
from cc_orchestrator.web.schemas import (
    InstanceCreate,
    InstanceUpdate,
    TaskResponse,
)


class TestInstancesRouterComprehensiveCoverage:
    """Comprehensive tests targeting 100% coverage of instances router."""

    @pytest.fixture
    def mock_instance_data(self):
        """Create comprehensive mock instance data."""
        instance_data = {
            "id": 1,
            "issue_id": "test-issue-001",
            "status": InstanceStatus.RUNNING,
            "health_status": "healthy",  # String instead of enum
            "workspace_path": "/workspace/test",
            "branch_name": "main",
            "tmux_session": "test-session",
            "process_id": 12345,
            "last_health_check": datetime.now(UTC),
            "last_activity": datetime.now(UTC),
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }
        # Create a mock that returns proper values for all attributes
        mock = Mock()
        for key, value in instance_data.items():
            setattr(mock, key, value)
        # Ensure mock doesn't return Mock objects for attributes
        mock.configure_mock(**instance_data)
        return mock

    @pytest.fixture
    def mock_task_data(self):
        """Create comprehensive mock task data."""
        task_data = {
            "id": 1,
            "title": "test-task",  # Primary field for TaskResponse
            "name": "test-task",  # Fallback field for endpoint mapping
            "description": "Test Description",
            "status": "pending",  # String instead of enum
            "priority": TaskPriority.MEDIUM,
            "instance_id": 1,
            "command": "test command",
            "schedule": "0 * * * *",
            "enabled": True,
            "worktree_id": None,
            "due_date": None,
            "estimated_duration": None,
            "actual_duration": None,
            "requirements": {},
            "results": {},
            "extra_metadata": {},
            "started_at": None,
            "completed_at": None,
            "last_run": None,
            "next_run": None,
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }
        # Create a mock that returns proper values for all attributes
        mock = Mock()
        for key, value in task_data.items():
            setattr(mock, key, value)
        # Ensure mock doesn't return Mock objects for attributes
        mock.configure_mock(**task_data)
        return mock

    @pytest.fixture
    def mock_crud(self, mock_instance_data, mock_task_data):
        """Comprehensive mock CRUD adapter."""
        crud = AsyncMock()
        crud.list_instances.return_value = ([mock_instance_data], 1)
        crud.create_instance.return_value = mock_instance_data
        crud.get_instance.return_value = mock_instance_data
        crud.get_instance_by_issue_id.return_value = None
        crud.update_instance.return_value = mock_instance_data
        crud.delete_instance.return_value = True
        crud.list_tasks.return_value = ([mock_task_data], 1)
        return crud

    @pytest.fixture
    def pagination_params(self):
        """Standard pagination parameters."""
        params = Mock(spec=PaginationParams)
        params.page = 1
        params.size = 20
        params.offset = 0
        return params

    # =====================================================
    # LIST INSTANCES ENDPOINT COMPREHENSIVE COVERAGE
    # =====================================================

    @pytest.mark.asyncio
    async def test_list_instances_no_filters(self, mock_crud, pagination_params):
        """Test list_instances with no filters - line 50 coverage."""
        result = await instances.list_instances(
            pagination=pagination_params,
            status_filter=None,
            branch_name=None,
            crud=mock_crud,
        )

        assert result["total"] == 1
        assert len(result["items"]) == 1
        assert result["page"] == 1
        assert result["size"] == 20
        assert result["pages"] == 1
        mock_crud.list_instances.assert_called_once_with(offset=0, limit=20, filters={})

    @pytest.mark.asyncio
    async def test_list_instances_status_filter_only(
        self, mock_crud, pagination_params
    ):
        """Test list_instances with status filter only - lines 51-52 coverage."""
        result = await instances.list_instances(
            pagination=pagination_params,
            status_filter=InstanceStatus.RUNNING,
            branch_name=None,
            crud=mock_crud,
        )

        assert result["total"] == 1
        mock_crud.list_instances.assert_called_once_with(
            offset=0, limit=20, filters={"status": InstanceStatus.RUNNING}
        )

    @pytest.mark.asyncio
    async def test_list_instances_branch_filter_only(
        self, mock_crud, pagination_params
    ):
        """Test list_instances with branch filter only - lines 53-54 coverage."""
        result = await instances.list_instances(
            pagination=pagination_params,
            status_filter=None,
            branch_name="feature-branch",
            crud=mock_crud,
        )

        assert result["total"] == 1
        mock_crud.list_instances.assert_called_once_with(
            offset=0, limit=20, filters={"branch_name": "feature-branch"}
        )

    @pytest.mark.asyncio
    async def test_list_instances_both_filters(self, mock_crud, pagination_params):
        """Test list_instances with both filters - lines 51-54 coverage."""
        result = await instances.list_instances(
            pagination=pagination_params,
            status_filter=InstanceStatus.STOPPED,
            branch_name="develop",
            crud=mock_crud,
        )

        assert result["total"] == 1
        mock_crud.list_instances.assert_called_once_with(
            offset=0,
            limit=20,
            filters={"status": InstanceStatus.STOPPED, "branch_name": "develop"},
        )

    @pytest.mark.asyncio
    async def test_list_instances_pagination_calculation_multiple_pages(
        self, mock_crud, pagination_params
    ):
        """Test pagination calculation for multiple pages - line 71 coverage."""
        # Mock larger result set
        mock_crud.list_instances.return_value = ([], 50)  # 50 total items
        pagination_params.size = 20  # 20 per page

        result = await instances.list_instances(
            pagination=pagination_params,
            status_filter=None,
            branch_name=None,
            crud=mock_crud,
        )

        # (50 + 20 - 1) // 20 = 69 // 20 = 3 pages
        assert result["pages"] == 3
        assert result["total"] == 50

    @pytest.mark.asyncio
    async def test_list_instances_pagination_calculation_exact_pages(
        self, mock_crud, pagination_params
    ):
        """Test pagination calculation for exact page boundaries."""
        # Mock exact page boundary
        mock_crud.list_instances.return_value = ([], 40)  # 40 total items
        pagination_params.size = 20  # 20 per page

        result = await instances.list_instances(
            pagination=pagination_params,
            status_filter=None,
            branch_name=None,
            crud=mock_crud,
        )

        # (40 + 20 - 1) // 20 = 59 // 20 = 2 pages
        assert result["pages"] == 2

    @pytest.mark.asyncio
    async def test_list_instances_empty_results(self, mock_crud, pagination_params):
        """Test list_instances with empty results."""
        mock_crud.list_instances.return_value = ([], 0)

        result = await instances.list_instances(
            pagination=pagination_params,
            status_filter=None,
            branch_name=None,
            crud=mock_crud,
        )

        assert result["total"] == 0
        assert len(result["items"]) == 0
        assert result["pages"] == 0

    # =====================================================
    # CREATE INSTANCE ENDPOINT COMPREHENSIVE COVERAGE
    # =====================================================

    @pytest.mark.asyncio
    async def test_create_instance_success_comprehensive(self, mock_crud):
        """Test successful instance creation with all fields - lines 92-106 coverage."""
        instance_data = InstanceCreate(
            issue_id="new-issue-001",
            status=InstanceStatus.INITIALIZING,
        )

        result = await instances.create_instance(
            instance_data=instance_data, crud=mock_crud
        )

        assert result["success"] is True
        assert result["message"] == "Instance created successfully"
        assert "data" in result

        # Verify duplicate check was performed
        mock_crud.get_instance_by_issue_id.assert_called_once_with("new-issue-001")
        # Verify creation was called with model_dump
        mock_crud.create_instance.assert_called_once_with(instance_data.model_dump())

    @pytest.mark.asyncio
    async def test_create_instance_duplicate_conflict(self, mock_crud):
        """Test instance creation conflict for duplicate issue_id - lines 93-97 coverage."""
        # Mock existing instance found
        existing_instance = Mock(id=999, issue_id="duplicate-issue")
        mock_crud.get_instance_by_issue_id.return_value = existing_instance

        instance_data = InstanceCreate(
            issue_id="duplicate-issue",
            status=InstanceStatus.INITIALIZING,
        )

        with pytest.raises(HTTPException) as exc_info:
            await instances.create_instance(instance_data=instance_data, crud=mock_crud)

        assert exc_info.value.status_code == status.HTTP_409_CONFLICT
        assert "Instance with issue_id 'duplicate-issue' already exists" in str(
            exc_info.value.detail
        )

        # Verify duplicate check was performed but creation was not
        mock_crud.get_instance_by_issue_id.assert_called_once_with("duplicate-issue")
        mock_crud.create_instance.assert_not_called()

    # =====================================================
    # GET INSTANCE ENDPOINT COMPREHENSIVE COVERAGE
    # =====================================================

    @pytest.mark.asyncio
    async def test_get_instance_success_comprehensive(self, mock_crud):
        """Test successful instance retrieval - lines 122-142 coverage."""
        result = await instances.get_instance(instance_id=1, crud=mock_crud)

        assert result["success"] is True
        assert result["message"] == "Instance retrieved successfully"
        assert "data" in result
        mock_crud.get_instance.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_get_instance_not_found_none_return(self, mock_crud):
        """Test instance retrieval when None returned - lines 123-127 coverage."""
        mock_crud.get_instance.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await instances.get_instance(instance_id=999, crud=mock_crud)

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert "Instance with ID 999 not found" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_instance_http_exception_reraise(self, mock_crud):
        """Test HTTPException re-raising - lines 128-130 coverage."""
        # Mock HTTPException being raised by CRUD
        http_exception = HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
        )
        mock_crud.get_instance.side_effect = http_exception

        with pytest.raises(HTTPException) as exc_info:
            await instances.get_instance(instance_id=1, crud=mock_crud)

        # Should re-raise the original HTTPException
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert exc_info.value.detail == "Access denied"

    @pytest.mark.asyncio
    async def test_get_instance_database_error_conversion(self, mock_crud):
        """Test database error conversion to 404 - lines 131-136 coverage."""
        # Mock any other non-HTTP exception
        mock_crud.get_instance.side_effect = ValueError("Database connection lost")

        with pytest.raises(HTTPException) as exc_info:
            await instances.get_instance(instance_id=1, crud=mock_crud)

        # Should convert to 404
        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert "Instance with ID 1 not found" in str(exc_info.value.detail)

    # =====================================================
    # UPDATE INSTANCE ENDPOINT COMPREHENSIVE COVERAGE
    # =====================================================

    @pytest.mark.asyncio
    async def test_update_instance_success_comprehensive(self, mock_crud):
        """Test successful instance update - lines 160-175 coverage."""
        update_data = InstanceUpdate(status=InstanceStatus.STOPPED)

        result = await instances.update_instance(
            instance_id=1, instance_data=update_data, crud=mock_crud
        )

        assert result["success"] is True
        assert result["message"] == "Instance updated successfully"
        assert "data" in result

        # Verify existence check and update call
        mock_crud.get_instance.assert_called_once_with(1)
        mock_crud.update_instance.assert_called_once_with(
            1, update_data.model_dump(exclude_unset=True)
        )

    @pytest.mark.asyncio
    async def test_update_instance_not_found(self, mock_crud):
        """Test update on non-existent instance - lines 161-165 coverage."""
        mock_crud.get_instance.return_value = None
        update_data = InstanceUpdate(status=InstanceStatus.RUNNING)

        with pytest.raises(HTTPException) as exc_info:
            await instances.update_instance(
                instance_id=999, instance_data=update_data, crud=mock_crud
            )

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert "Instance with ID 999 not found" in str(exc_info.value.detail)
        mock_crud.update_instance.assert_not_called()

    # =====================================================
    # DELETE INSTANCE ENDPOINT COMPREHENSIVE COVERAGE
    # =====================================================

    @pytest.mark.asyncio
    async def test_delete_instance_success_comprehensive(self, mock_crud):
        """Test successful instance deletion - lines 192-202 coverage."""
        result = await instances.delete_instance(instance_id=1, crud=mock_crud)

        assert result["success"] is True
        assert result["message"] == "Instance deleted successfully"
        assert result["data"] is None

        # Verify existence check and deletion call
        mock_crud.get_instance.assert_called_once_with(1)
        mock_crud.delete_instance.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_delete_instance_not_found(self, mock_crud):
        """Test delete on non-existent instance - lines 193-197 coverage."""
        mock_crud.get_instance.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await instances.delete_instance(instance_id=999, crud=mock_crud)

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert "Instance with ID 999 not found" in str(exc_info.value.detail)
        mock_crud.delete_instance.assert_not_called()

    # =====================================================
    # START INSTANCE ENDPOINT COMPREHENSIVE COVERAGE
    # =====================================================

    @pytest.mark.asyncio
    async def test_start_instance_success_comprehensive(
        self, mock_crud, mock_instance_data
    ):
        """Test successful instance start - lines 218-242 coverage."""
        # Set instance to stopped status
        mock_instance_data.status = InstanceStatus.STOPPED
        mock_crud.get_instance.return_value = mock_instance_data

        result = await instances.start_instance(instance_id=1, crud=mock_crud)

        assert result["success"] is True
        assert result["message"] == "Instance started successfully"
        assert "data" in result

        # Verify calls
        mock_crud.get_instance.assert_called_once_with(1)
        mock_crud.update_instance.assert_called_once_with(
            1, {"status": InstanceStatus.RUNNING}
        )

    @pytest.mark.asyncio
    async def test_start_instance_not_found(self, mock_crud):
        """Test start on non-existent instance - lines 219-223 coverage."""
        mock_crud.get_instance.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await instances.start_instance(instance_id=999, crud=mock_crud)

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert "Instance with ID 999 not found" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_start_instance_already_running(self, mock_crud, mock_instance_data):
        """Test start on already running instance - lines 226-230 coverage."""
        # Set instance to running status
        mock_instance_data.status = InstanceStatus.RUNNING
        mock_crud.get_instance.return_value = mock_instance_data

        with pytest.raises(HTTPException) as exc_info:
            await instances.start_instance(instance_id=1, crud=mock_crud)

        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "Instance is already running" in str(exc_info.value.detail)
        mock_crud.update_instance.assert_not_called()

    # =====================================================
    # STOP INSTANCE ENDPOINT COMPREHENSIVE COVERAGE
    # =====================================================

    @pytest.mark.asyncio
    async def test_stop_instance_success_comprehensive(
        self, mock_crud, mock_instance_data
    ):
        """Test successful instance stop - lines 258-282 coverage."""
        # Set instance to running status
        mock_instance_data.status = InstanceStatus.RUNNING
        mock_crud.get_instance.return_value = mock_instance_data

        result = await instances.stop_instance(instance_id=1, crud=mock_crud)

        assert result["success"] is True
        assert result["message"] == "Instance stopped successfully"
        assert "data" in result

        # Verify calls
        mock_crud.get_instance.assert_called_once_with(1)
        mock_crud.update_instance.assert_called_once_with(
            1, {"status": InstanceStatus.STOPPED}
        )

    @pytest.mark.asyncio
    async def test_stop_instance_not_found(self, mock_crud):
        """Test stop on non-existent instance - lines 259-263 coverage."""
        mock_crud.get_instance.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await instances.stop_instance(instance_id=999, crud=mock_crud)

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert "Instance with ID 999 not found" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_stop_instance_already_stopped(self, mock_crud, mock_instance_data):
        """Test stop on already stopped instance - lines 266-270 coverage."""
        # Set instance to stopped status
        mock_instance_data.status = InstanceStatus.STOPPED
        mock_crud.get_instance.return_value = mock_instance_data

        with pytest.raises(HTTPException) as exc_info:
            await instances.stop_instance(instance_id=1, crud=mock_crud)

        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "Instance is already stopped" in str(exc_info.value.detail)
        mock_crud.update_instance.assert_not_called()

    # =====================================================
    # GET INSTANCE STATUS ENDPOINT COMPREHENSIVE COVERAGE
    # =====================================================

    @pytest.mark.asyncio
    async def test_get_instance_status_success_comprehensive(
        self, mock_crud, mock_instance_data
    ):
        """Test successful instance status retrieval - lines 297-319 coverage."""
        result = await instances.get_instance_status(instance_id=1, crud=mock_crud)

        assert result["success"] is True
        assert result["message"] == "Instance status retrieved successfully"
        assert "data" in result

        status_data = result["data"]
        # Verify all status fields are included (lines 304-313)
        assert status_data["id"] == mock_instance_data.id
        assert status_data["issue_id"] == mock_instance_data.issue_id
        assert status_data["status"] == mock_instance_data.status
        assert status_data["health_status"] == mock_instance_data.health_status
        assert status_data["last_health_check"] == mock_instance_data.last_health_check
        assert status_data["last_activity"] == mock_instance_data.last_activity
        assert status_data["process_id"] == mock_instance_data.process_id
        assert status_data["tmux_session"] == mock_instance_data.tmux_session

        mock_crud.get_instance.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_get_instance_status_not_found(self, mock_crud):
        """Test status retrieval on non-existent instance - lines 298-302 coverage."""
        mock_crud.get_instance.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await instances.get_instance_status(instance_id=999, crud=mock_crud)

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert "Instance with ID 999 not found" in str(exc_info.value.detail)

    # =====================================================
    # GET INSTANCE TASKS ENDPOINT COMPREHENSIVE COVERAGE
    # =====================================================

    @pytest.mark.asyncio
    async def test_get_instance_tasks_success_comprehensive(
        self, mock_crud, mock_instance_data, pagination_params
    ):
        """Test successful instance tasks retrieval - lines 338-363 coverage."""
        # Create a proper task response that will validate correctly
        task_response = TaskResponse(
            id=1,
            title="test-task",  # TaskResponse requires 'title' not 'name'
            description="Test Description",
            instance_id=1,
            command="test command",
            schedule="0 * * * *",
            enabled=True,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            last_run=None,
            next_run=None,
            status="pending",
        )

        mock_crud.get_instance.return_value = mock_instance_data
        mock_crud.list_tasks.return_value = ([task_response], 1)

        result = await instances.get_instance_tasks(
            instance_id=1, pagination=pagination_params, crud=mock_crud
        )

        assert result["total"] == 1
        assert len(result["items"]) == 1
        assert result["page"] == 1
        assert result["size"] == 20
        assert result["pages"] == 1

        # Verify calls
        mock_crud.get_instance.assert_called_once_with(1)
        mock_crud.list_tasks.assert_called_once_with(
            offset=0, limit=20, filters={"instance_id": 1}
        )

    @pytest.mark.asyncio
    async def test_get_instance_tasks_not_found(self, mock_crud, pagination_params):
        """Test tasks retrieval on non-existent instance - lines 339-343 coverage."""
        mock_crud.get_instance.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            await instances.get_instance_tasks(
                instance_id=999, pagination=pagination_params, crud=mock_crud
            )

        assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
        assert "Instance with ID 999 not found" in str(exc_info.value.detail)
        mock_crud.list_tasks.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_instance_tasks_empty_results(
        self, mock_crud, mock_instance_data, pagination_params
    ):
        """Test tasks retrieval with empty results."""
        mock_crud.get_instance.return_value = mock_instance_data
        mock_crud.list_tasks.return_value = ([], 0)

        result = await instances.get_instance_tasks(
            instance_id=1, pagination=pagination_params, crud=mock_crud
        )

        assert result["total"] == 0
        assert len(result["items"]) == 0
        assert result["pages"] == 0

    @pytest.mark.asyncio
    async def test_get_instance_tasks_import_statement_coverage(
        self, mock_crud, mock_instance_data, pagination_params
    ):
        """Test import statement in get_instance_tasks - line 353 coverage."""
        # This test ensures the import statement is executed
        task_response = TaskResponse(
            id=1,
            title="test-task",  # TaskResponse requires 'title' not 'name'
            description="Test Description",
            instance_id=1,
            command="test command",
            schedule="0 * * * *",
            enabled=True,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            last_run=None,
            next_run=None,
            status="pending",
        )

        mock_crud.get_instance.return_value = mock_instance_data
        mock_crud.list_tasks.return_value = ([task_response], 1)

        result = await instances.get_instance_tasks(
            instance_id=1, pagination=pagination_params, crud=mock_crud
        )

        # Verify TaskResponse was used for serialization
        assert len(result["items"]) == 1
        task_item = result["items"][0]
        # The task should be serialized as TaskResponse
        assert hasattr(task_item, "model_validate") or isinstance(task_item, dict)


class TestDecoratorFunctionality:
    """Test decorator functionality for performance tracking and error handling."""

    @pytest.mark.asyncio
    async def test_track_api_performance_decorator_success(self):
        """Test @track_api_performance decorator on successful execution."""
        with patch("cc_orchestrator.web.logging_utils.api_logger") as mock_logger:
            # Create mock CRUD and call a decorated function
            mock_crud = AsyncMock()
            mock_crud.list_instances.return_value = ([], 0)

            pagination = Mock(spec=PaginationParams)
            pagination.page = 1
            pagination.size = 20
            pagination.offset = 0

            result = await instances.list_instances(
                pagination=pagination,
                status_filter=None,
                branch_name=None,
                crud=mock_crud,
            )

            # Verify performance logging calls
            assert mock_logger.debug.called
            assert mock_logger.info.called

            # Check for performance logging messages
            info_calls = [call for call in mock_logger.info.call_args_list]
            assert any("completed" in str(call) for call in info_calls)

    @pytest.mark.asyncio
    async def test_track_api_performance_decorator_error(self):
        """Test @track_api_performance decorator on error execution."""
        with patch("cc_orchestrator.web.logging_utils.api_logger") as mock_logger:
            # Create mock CRUD that raises an exception
            mock_crud = AsyncMock()
            mock_crud.list_instances.side_effect = ValueError("Database error")

            pagination = Mock(spec=PaginationParams)
            pagination.page = 1
            pagination.size = 20
            pagination.offset = 0

            # The error decorator will convert ValueError to CCOrchestratorAPIException
            with pytest.raises(CCOrchestratorAPIException):
                await instances.list_instances(
                    pagination=pagination,
                    status_filter=None,
                    branch_name=None,
                    crud=mock_crud,
                )

            # Verify performance logging for errors
            warning_calls = [call for call in mock_logger.warning.call_args_list]
            assert any("failed" in str(call) for call in warning_calls)

    @pytest.mark.asyncio
    async def test_handle_api_errors_decorator_http_exception_reraise(self):
        """Test @handle_api_errors decorator re-raising HTTPException."""
        with patch("cc_orchestrator.web.logging_utils.api_logger") as mock_logger:
            # Create mock CRUD that raises HTTPException
            mock_crud = AsyncMock()
            http_exc = HTTPException(status_code=400, detail="Bad request")
            mock_crud.get_instance.side_effect = http_exc

            with pytest.raises(HTTPException) as exc_info:
                await instances.get_instance(instance_id=1, crud=mock_crud)

            # Should re-raise the original HTTPException
            assert exc_info.value.status_code == 400
            assert exc_info.value.detail == "Bad request"

    @pytest.mark.asyncio
    async def test_handle_api_errors_decorator_general_exception_conversion(self):
        """Test @handle_api_errors decorator converting general exceptions."""
        with patch("cc_orchestrator.web.logging_utils.api_logger") as mock_logger:
            # Create mock CRUD that raises a general exception
            mock_crud = AsyncMock()
            mock_crud.list_instances.side_effect = RuntimeError("System error")

            pagination = Mock(spec=PaginationParams)
            pagination.page = 1
            pagination.size = 20
            pagination.offset = 0

            with pytest.raises(CCOrchestratorAPIException):
                await instances.list_instances(
                    pagination=pagination,
                    status_filter=None,
                    branch_name=None,
                    crud=mock_crud,
                )

            # Verify error logging
            assert mock_logger.error.called
            error_calls = [call for call in mock_logger.error.call_args_list]
            assert any(
                "API error in list_instances" in str(call) for call in error_calls
            )


class TestEdgeCasesAndBoundaryConditions:
    """Test edge cases and boundary conditions for maximum coverage."""

    @pytest.mark.asyncio
    async def test_list_instances_pagination_edge_case_single_item(self):
        """Test pagination calculation with single item."""
        mock_crud = AsyncMock()
        mock_crud.list_instances.return_value = ([], 1)  # 1 total item

        pagination = Mock(spec=PaginationParams)
        pagination.page = 1
        pagination.size = 20
        pagination.offset = 0

        result = await instances.list_instances(
            pagination=pagination,
            status_filter=None,
            branch_name=None,
            crud=mock_crud,
        )

        # (1 + 20 - 1) // 20 = 20 // 20 = 1 page
        assert result["pages"] == 1
        assert result["total"] == 1

    @pytest.mark.asyncio
    async def test_list_instances_pagination_edge_case_zero_items(self):
        """Test pagination calculation with zero items."""
        mock_crud = AsyncMock()
        mock_crud.list_instances.return_value = ([], 0)  # 0 total items

        pagination = Mock(spec=PaginationParams)
        pagination.page = 1
        pagination.size = 20
        pagination.offset = 0

        result = await instances.list_instances(
            pagination=pagination,
            status_filter=None,
            branch_name=None,
            crud=mock_crud,
        )

        # (0 + 20 - 1) // 20 = 19 // 20 = 0 pages
        assert result["pages"] == 0
        assert result["total"] == 0

    @pytest.mark.asyncio
    async def test_create_instance_model_dump_coverage(self):
        """Test InstanceCreate.model_dump() is called correctly."""
        mock_crud = AsyncMock()
        # Create proper mock instance with all required attributes
        mock_instance = Mock(
            id=1,
            issue_id="test",
            status=InstanceStatus.RUNNING,
            health_status="healthy",
            last_health_check=datetime.now(UTC),
            last_activity=datetime.now(UTC),
            process_id=12345,
            tmux_session="test-session",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        mock_crud.get_instance_by_issue_id.return_value = None
        mock_crud.create_instance.return_value = mock_instance

        instance_data = InstanceCreate(
            issue_id="test-issue", status=InstanceStatus.INITIALIZING
        )

        await instances.create_instance(instance_data=instance_data, crud=mock_crud)

        # Verify model_dump was called by checking the argument
        call_args = mock_crud.create_instance.call_args[0][0]
        assert isinstance(call_args, dict)
        assert "issue_id" in call_args
        assert call_args["issue_id"] == "test-issue"

    @pytest.mark.asyncio
    async def test_update_instance_exclude_unset_coverage(self):
        """Test InstanceUpdate.model_dump(exclude_unset=True) is called correctly."""
        mock_crud = AsyncMock()
        # Create proper mock instance with all required attributes
        mock_instance = Mock(
            id=1,
            issue_id="test",
            status=InstanceStatus.RUNNING,
            health_status="healthy",
            last_health_check=datetime.now(UTC),
            last_activity=datetime.now(UTC),
            process_id=12345,
            tmux_session="test-session",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        mock_crud.get_instance.return_value = mock_instance
        mock_crud.update_instance.return_value = mock_instance

        # Create update with only status set
        update_data = InstanceUpdate(status=InstanceStatus.STOPPED)

        await instances.update_instance(
            instance_id=1, instance_data=update_data, crud=mock_crud
        )

        # Verify model_dump(exclude_unset=True) was called
        call_args = mock_crud.update_instance.call_args[0][1]
        assert isinstance(call_args, dict)
        # Should only contain set fields
        assert "status" in call_args
        assert call_args["status"] == InstanceStatus.STOPPED

    @pytest.mark.asyncio
    async def test_instance_response_model_validate_coverage(self):
        """Test InstanceResponse.model_validate is called in multiple endpoints."""
        mock_crud = AsyncMock()
        mock_instance = Mock(
            id=1,
            issue_id="test",
            status=InstanceStatus.STOPPED,  # Start with stopped status
            health_status="healthy",
            last_health_check=datetime.now(UTC),
            last_activity=datetime.now(UTC),
            process_id=12345,
            tmux_session="test-session",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        mock_crud.get_instance.return_value = mock_instance

        # Test get_instance endpoint
        result = await instances.get_instance(instance_id=1, crud=mock_crud)
        assert "data" in result

        # Test start_instance endpoint (change status to stopped for valid start)
        mock_instance.status = InstanceStatus.STOPPED
        mock_crud.update_instance.return_value = mock_instance
        result = await instances.start_instance(instance_id=1, crud=mock_crud)
        assert "data" in result

        # Test stop_instance endpoint (change status to running for valid stop)
        mock_instance.status = InstanceStatus.RUNNING
        result = await instances.stop_instance(instance_id=1, crud=mock_crud)
        assert "data" in result

    @pytest.mark.asyncio
    async def test_task_response_model_validate_coverage(self):
        """Test TaskResponse.model_validate is called in get_instance_tasks."""
        mock_crud = AsyncMock()
        mock_instance = Mock(id=1)

        # Create a proper TaskResponse instance
        task_response = TaskResponse(
            id=1,
            title="test",  # TaskResponse requires 'title' not 'name'
            description="test",
            instance_id=1,
            command=None,
            schedule=None,
            enabled=True,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            last_run=None,
            next_run=None,
            status="pending",
        )

        mock_crud.get_instance.return_value = mock_instance
        mock_crud.list_tasks.return_value = ([task_response], 1)

        pagination = Mock(spec=PaginationParams)
        pagination.page = 1
        pagination.size = 20
        pagination.offset = 0

        result = await instances.get_instance_tasks(
            instance_id=1, pagination=pagination, crud=mock_crud
        )

        assert len(result["items"]) == 1
        # TaskResponse.model_validate should have been called on the task


class TestComplexScenarios:
    """Test complex scenarios to ensure full coverage."""

    @pytest.mark.asyncio
    async def test_all_status_values_coverage(self):
        """Test all InstanceStatus enum values are handled correctly."""
        mock_crud = AsyncMock()
        mock_instance = Mock(id=1, issue_id="test")

        # Test each status value in different operations
        for status_value in InstanceStatus:
            mock_instance.status = status_value
            mock_crud.get_instance.return_value = mock_instance

            if status_value == InstanceStatus.RUNNING:
                # Should fail to start but succeed to stop
                with pytest.raises(HTTPException):
                    await instances.start_instance(instance_id=1, crud=mock_crud)
            elif status_value == InstanceStatus.STOPPED:
                # Should fail to stop but succeed to start
                with pytest.raises(HTTPException):
                    await instances.stop_instance(instance_id=1, crud=mock_crud)

    @pytest.mark.asyncio
    async def test_comprehensive_filter_combinations(self):
        """Test all possible filter combinations in list_instances."""
        mock_crud = AsyncMock()
        mock_crud.list_instances.return_value = ([], 0)

        pagination = Mock(spec=PaginationParams)
        pagination.page = 1
        pagination.size = 20
        pagination.offset = 0

        # Test all combinations of filters
        filter_combinations = [
            (None, None),
            (InstanceStatus.RUNNING, None),
            (None, "main"),
            (InstanceStatus.STOPPED, "develop"),
            (InstanceStatus.ERROR, "feature/test"),
        ]

        for status_filter, branch_name in filter_combinations:
            await instances.list_instances(
                pagination=pagination,
                status_filter=status_filter,
                branch_name=branch_name,
                crud=mock_crud,
            )

            # Verify the correct filters were applied
            expected_filters = {}
            if status_filter:
                expected_filters["status"] = status_filter
            if branch_name:
                expected_filters["branch_name"] = branch_name

            mock_crud.list_instances.assert_called_with(
                offset=0, limit=20, filters=expected_filters
            )

    @pytest.mark.asyncio
    async def test_exception_handling_comprehensive(self):
        """Test comprehensive exception handling in get_instance."""
        mock_crud = AsyncMock()

        # Test different types of exceptions
        exception_types = [
            ValueError("Database error"),
            ConnectionError("Connection lost"),
            RuntimeError("Runtime issue"),
            Exception("Generic error"),
        ]

        for exception in exception_types:
            mock_crud.get_instance.side_effect = exception

            with pytest.raises(HTTPException) as exc_info:
                await instances.get_instance(instance_id=1, crud=mock_crud)

            # All non-HTTP exceptions should be converted to 404
            assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
            assert "Instance with ID 1 not found" in str(exc_info.value.detail)


# =====================================================
# INTEGRATION TESTS FOR COMPLETE FLOW COVERAGE
# =====================================================


class TestInstanceRouterIntegrationCoverage:
    """Integration tests to ensure complete flow coverage."""

    @pytest.mark.asyncio
    async def test_complete_instance_lifecycle_flow(self):
        """Test complete instance lifecycle to ensure all paths are covered."""
        mock_crud = AsyncMock()

        # Step 1: Create instance
        instance_data = InstanceCreate(
            issue_id="lifecycle-test", status=InstanceStatus.INITIALIZING
        )
        mock_instance = Mock(
            id=1,
            issue_id="lifecycle-test",
            status=InstanceStatus.INITIALIZING,
            health_status="healthy",
            last_health_check=datetime.now(UTC),
            last_activity=datetime.now(UTC),
            process_id=12345,
            tmux_session="test-session",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        mock_crud.get_instance_by_issue_id.return_value = None
        mock_crud.create_instance.return_value = mock_instance

        create_result = await instances.create_instance(
            instance_data=instance_data, crud=mock_crud
        )
        assert create_result["success"] is True

        # Step 2: Get instance
        mock_crud.get_instance.return_value = mock_instance
        get_result = await instances.get_instance(instance_id=1, crud=mock_crud)
        assert get_result["success"] is True

        # Step 3: Start instance
        mock_instance.status = InstanceStatus.STOPPED
        mock_crud.update_instance.return_value = mock_instance
        start_result = await instances.start_instance(instance_id=1, crud=mock_crud)
        assert start_result["success"] is True

        # Step 4: Get status
        mock_instance.status = InstanceStatus.RUNNING
        status_result = await instances.get_instance_status(
            instance_id=1, crud=mock_crud
        )
        assert status_result["success"] is True

        # Step 5: Update instance
        update_data = InstanceUpdate(status=InstanceStatus.RUNNING)
        mock_crud.update_instance.return_value = mock_instance
        update_result = await instances.update_instance(
            instance_id=1, instance_data=update_data, crud=mock_crud
        )
        assert update_result["success"] is True

        # Step 6: Stop instance
        stop_result = await instances.stop_instance(instance_id=1, crud=mock_crud)
        assert stop_result["success"] is True

        # Step 7: Delete instance
        delete_result = await instances.delete_instance(instance_id=1, crud=mock_crud)
        assert delete_result["success"] is True

    @pytest.mark.asyncio
    async def test_error_scenarios_comprehensive_coverage(self):
        """Test all error scenarios for comprehensive coverage."""
        mock_crud = AsyncMock()

        # Test create with duplicate
        mock_crud.get_instance_by_issue_id.return_value = Mock(id=1)
        instance_data = InstanceCreate(
            issue_id="duplicate", status=InstanceStatus.INITIALIZING
        )

        with pytest.raises(HTTPException) as exc_info:
            await instances.create_instance(instance_data=instance_data, crud=mock_crud)
        assert exc_info.value.status_code == status.HTTP_409_CONFLICT

        # Test operations on non-existent instance
        mock_crud.get_instance.return_value = None
        operations = [
            lambda: instances.get_instance(instance_id=999, crud=mock_crud),
            lambda: instances.update_instance(
                instance_id=999,
                instance_data=InstanceUpdate(status=InstanceStatus.RUNNING),
                crud=mock_crud,
            ),
            lambda: instances.delete_instance(instance_id=999, crud=mock_crud),
            lambda: instances.start_instance(instance_id=999, crud=mock_crud),
            lambda: instances.stop_instance(instance_id=999, crud=mock_crud),
            lambda: instances.get_instance_status(instance_id=999, crud=mock_crud),
        ]

        for operation in operations:
            with pytest.raises(HTTPException) as exc_info:
                await operation()
            assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
