"""Tests for integration logging utilities."""

from unittest.mock import Mock, patch

from cc_orchestrator.integrations.logging_utils import (
    github_logger,
    handle_integration_errors,
    jira_logger,
    log_github_api_call,
    log_github_sync,
    log_integration_configuration,
    log_integration_operation,
    log_jira_api_call,
    log_jira_sync,
    log_rate_limit_warning,
    log_service_status_change,
    log_task_sync_status,
    log_webhook_processing,
    log_webhook_received,
    webhook_logger,
)


class TestGitHubLogging:
    """Test GitHub API logging functions."""

    def test_log_github_api_call_success(self):
        """Test logging successful GitHub API calls."""
        with patch.object(github_logger, "info") as mock_info:
            log_github_api_call(
                operation="get_issues",
                endpoint="/repos/owner/repo/issues",
                method="GET",
                status_code=200,
                response_time_ms=150.5,
                rate_limit_remaining=4999,
            )

            mock_info.assert_called_once_with(
                "GitHub API get_issues",
                operation="get_issues",
                endpoint="/repos/owner/repo/issues",
                method="GET",
                status_code=200,
                response_time_ms=150.5,
                rate_limit_remaining=4999,
            )

    def test_log_github_api_call_error(self):
        """Test logging GitHub API call errors."""
        with patch.object(github_logger, "warning") as mock_warning:
            log_github_api_call(
                operation="create_issue",
                endpoint="/repos/owner/repo/issues",
                method="POST",
                status_code=422,
                response_time_ms=85.2,
            )

            mock_warning.assert_called_once_with(
                "GitHub API create_issue",
                operation="create_issue",
                endpoint="/repos/owner/repo/issues",
                method="POST",
                status_code=422,
                response_time_ms=85.2,
                rate_limit_remaining=None,
            )

    def test_log_github_sync(self):
        """Test logging GitHub synchronization operations."""
        with patch.object(github_logger, "info") as mock_info:
            log_github_sync(
                repository="owner/repo",
                sync_type="issues",
                items_processed=50,
                items_created=10,
                items_updated=5,
                errors=2,
            )

            mock_info.assert_called_once_with(
                "GitHub issues sync completed",
                repository="owner/repo",
                sync_type="issues",
                items_processed=50,
                items_created=10,
                items_updated=5,
                errors=2,
            )

    def test_log_github_sync_no_errors(self):
        """Test logging GitHub sync without errors."""
        with patch.object(github_logger, "info") as mock_info:
            log_github_sync(
                repository="owner/repo",
                sync_type="pull_requests",
                items_processed=25,
                items_created=3,
                items_updated=1,
            )

            mock_info.assert_called_once_with(
                "GitHub pull_requests sync completed",
                repository="owner/repo",
                sync_type="pull_requests",
                items_processed=25,
                items_created=3,
                items_updated=1,
                errors=0,
            )


class TestJiraLogging:
    """Test Jira API logging functions."""

    def test_log_jira_api_call_success(self):
        """Test logging successful Jira API calls."""
        with patch.object(jira_logger, "info") as mock_info:
            log_jira_api_call(
                operation="get_issues",
                endpoint="/rest/api/3/search",
                method="GET",
                status_code=200,
                response_time_ms=250.7,
                project_key="PROJ",
            )

            mock_info.assert_called_once_with(
                "Jira API get_issues",
                operation="get_issues",
                endpoint="/rest/api/3/search",
                method="GET",
                status_code=200,
                response_time_ms=250.7,
                project_key="PROJ",
            )

    def test_log_jira_api_call_error(self):
        """Test logging Jira API call errors."""
        with patch.object(jira_logger, "warning") as mock_warning:
            log_jira_api_call(
                operation="update_issue",
                endpoint="/rest/api/3/issue/PROJ-123",
                method="PUT",
                status_code=400,
                response_time_ms=120.0,
            )

            mock_warning.assert_called_once_with(
                "Jira API update_issue",
                operation="update_issue",
                endpoint="/rest/api/3/issue/PROJ-123",
                method="PUT",
                status_code=400,
                response_time_ms=120.0,
                project_key=None,
            )

    def test_log_jira_sync(self):
        """Test logging Jira synchronization operations."""
        with patch.object(jira_logger, "info") as mock_info:
            log_jira_sync(
                project_key="PROJ",
                sync_type="issues",
                items_processed=30,
                items_created=8,
                items_updated=3,
                errors=1,
            )

            mock_info.assert_called_once_with(
                "Jira issues sync completed",
                project_key="PROJ",
                sync_type="issues",
                items_processed=30,
                items_created=8,
                items_updated=3,
                errors=1,
            )


class TestWebhookLogging:
    """Test webhook logging functions."""

    def test_log_webhook_received(self):
        """Test logging incoming webhook events."""
        with patch.object(webhook_logger, "info") as mock_info:
            log_webhook_received(
                source="github",
                event_type="issues",
                payload_size=1024,
                signature_valid=True,
                processing_time_ms=45.3,
            )

            mock_info.assert_called_once_with(
                "Webhook received",
                source="github",
                event_type="issues",
                payload_size=1024,
                signature_valid=True,
                processing_time_ms=45.3,
            )

    def test_log_webhook_processing_success(self):
        """Test logging webhook processing results."""
        with patch.object(webhook_logger, "info") as mock_info:
            log_webhook_processing(
                source="jira",
                event_type="issue_updated",
                tasks_created=0,
                tasks_updated=1,
            )

            mock_info.assert_called_once_with(
                "Webhook processing completed",
                source="jira",
                event_type="issue_updated",
                tasks_created=0,
                tasks_updated=1,
                errors=[],
            )

    def test_log_webhook_processing_with_errors(self):
        """Test logging webhook processing with errors."""
        with patch.object(webhook_logger, "info") as mock_info:
            log_webhook_processing(
                source="github",
                event_type="pull_request",
                tasks_created=1,
                tasks_updated=0,
                errors=["Invalid payload format", "Missing required field"],
            )

            mock_info.assert_called_once_with(
                "Webhook processing completed",
                source="github",
                event_type="pull_request",
                tasks_created=1,
                tasks_updated=0,
                errors=["Invalid payload format", "Missing required field"],
            )


class TestServiceLogging:
    """Test service-related logging functions."""

    def test_log_rate_limit_warning(self):
        """Test logging rate limit warnings."""
        with patch.object(github_logger, "warning") as mock_warning:
            log_rate_limit_warning(
                service="GitHub",
                remaining_requests=10,
                reset_time="2025-01-01T12:00:00Z",
                operation="fetch_issues",
            )

            mock_warning.assert_called_once_with(
                "GitHub rate limit warning",
                service="GitHub",
                remaining_requests=10,
                reset_time="2025-01-01T12:00:00Z",
                operation="fetch_issues",
            )

    def test_log_service_status_change_github(self):
        """Test logging GitHub service status changes."""
        with patch.object(github_logger, "info") as mock_info:
            log_service_status_change(
                service="github",
                old_status="degraded",
                new_status="operational",
                reason="Issue resolved",
            )

            mock_info.assert_called_once_with(
                "github status changed",
                service="github",
                old_status="degraded",
                new_status="operational",
                reason="Issue resolved",
            )

    def test_log_service_status_change_jira(self):
        """Test logging Jira service status changes."""
        with patch.object(jira_logger, "info") as mock_info:
            log_service_status_change(
                service="jira",
                old_status="operational",
                new_status="maintenance",
            )

            mock_info.assert_called_once_with(
                "jira status changed",
                service="jira",
                old_status="operational",
                new_status="maintenance",
                reason=None,
            )

    def test_log_integration_configuration_github(self):
        """Test logging GitHub integration configuration."""
        with patch.object(github_logger, "info") as mock_info:
            config = {
                "repository": "owner/repo",
                "token": "secret_token",
                "webhook_url": "https://example.com/webhook",
                "sync_interval": 300,
            }

            log_integration_configuration(
                service="github",
                enabled=True,
                configuration=config,
            )

            # Verify sensitive information is removed
            expected_safe_config = {
                "repository": "owner/repo",
                "webhook_url": "https://example.com/webhook",
                "sync_interval": 300,
            }

            mock_info.assert_called_once_with(
                "github integration configured",
                service="github",
                enabled=True,
                configuration=expected_safe_config,
            )

    def test_log_integration_configuration_jira(self):
        """Test logging Jira integration configuration."""
        with patch.object(jira_logger, "info") as mock_info:
            config = {
                "server_url": "https://company.atlassian.net",
                "project_key": "PROJ",
                "password": "secret_password",
                "username": "user@company.com",
            }

            log_integration_configuration(
                service="jira",
                enabled=False,
                configuration=config,
            )

            expected_safe_config = {
                "server_url": "https://company.atlassian.net",
                "project_key": "PROJ",
                "username": "user@company.com",
            }

            mock_info.assert_called_once_with(
                "jira integration configured",
                service="jira",
                enabled=False,
                configuration=expected_safe_config,
            )


class TestTaskSyncLogging:
    """Test task synchronization logging."""

    @patch("cc_orchestrator.integrations.logging_utils.get_logger")
    def test_log_task_sync_status(self, mock_get_logger):
        """Test logging task synchronization status."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        from cc_orchestrator.utils.logging import LogContext

        log_task_sync_status(
            task_id="task-123",
            external_id="PROJ-456",
            service="jira",
            sync_direction="to_external",
            status="success",
            details={"updated_fields": ["status", "assignee"]},
        )

        mock_get_logger.assert_called_once_with(
            "cc_orchestrator.integrations.logging_utils.jira", LogContext.INTEGRATION
        )
        mock_logger.set_task_id.assert_called_once_with("task-123")
        mock_logger.info.assert_called_once_with(
            "Task sync to_external",
            external_id="PROJ-456",
            service="jira",
            sync_direction="to_external",
            status="success",
            details={"updated_fields": ["status", "assignee"]},
        )

    @patch("cc_orchestrator.integrations.logging_utils.get_logger")
    def test_log_task_sync_status_no_details(self, mock_get_logger):
        """Test logging task sync without details."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        from cc_orchestrator.utils.logging import LogContext

        log_task_sync_status(
            task_id="task-789",
            external_id="ISSUE-123",
            service="github",
            sync_direction="from_external",
            status="error",
        )

        mock_get_logger.assert_called_once_with(
            "cc_orchestrator.integrations.logging_utils.github", LogContext.INTEGRATION
        )
        mock_logger.info.assert_called_once_with(
            "Task sync from_external",
            external_id="ISSUE-123",
            service="github",
            sync_direction="from_external",
            status="error",
            details={},
        )


class TestDecoratorFunctions:
    """Test decorator functions for integration operations."""

    @patch("cc_orchestrator.integrations.logging_utils.handle_errors")
    def test_handle_integration_errors(self, mock_handle_errors):
        """Test integration error handling decorator."""
        from cc_orchestrator.utils.logging import LogContext

        mock_recovery = Mock()
        mock_handle_errors.return_value = Mock()  # Return a decorator function

        handle_integration_errors(
            service="github",
            recovery_strategy=mock_recovery,
        )

        mock_handle_errors.assert_called_once_with(
            recovery_strategy=mock_recovery,
            log_context=LogContext.INTEGRATION,
            reraise=True,
        )

    @patch("cc_orchestrator.integrations.logging_utils.handle_errors")
    def test_handle_integration_errors_no_recovery(self, mock_handle_errors):
        """Test integration error handling without recovery strategy."""
        from cc_orchestrator.utils.logging import LogContext

        mock_handle_errors.return_value = Mock()  # Return a decorator function
        handle_integration_errors(service="jira")

        mock_handle_errors.assert_called_once_with(
            recovery_strategy=None,
            log_context=LogContext.INTEGRATION,
            reraise=True,
        )

    @patch("cc_orchestrator.integrations.logging_utils.audit_log")
    def test_log_integration_operation(self, mock_audit_log):
        """Test integration operation logging decorator."""
        from cc_orchestrator.utils.logging import LogContext

        mock_audit_log.return_value = Mock()  # Return a decorator function
        log_integration_operation("github", "sync_issues")

        mock_audit_log.assert_called_once_with(
            "github_sync_issues", LogContext.INTEGRATION
        )


class TestLoggerInstances:
    """Test logger instance creation."""

    def test_github_logger_created(self):
        """Test GitHub logger instance exists."""
        assert github_logger is not None
        assert hasattr(github_logger, "info")
        assert hasattr(github_logger, "warning")
        assert hasattr(github_logger, "error")

    def test_jira_logger_created(self):
        """Test Jira logger instance exists."""
        assert jira_logger is not None
        assert hasattr(jira_logger, "info")
        assert hasattr(jira_logger, "warning")
        assert hasattr(jira_logger, "error")

    def test_webhook_logger_created(self):
        """Test webhook logger instance exists."""
        assert webhook_logger is not None
        assert hasattr(webhook_logger, "info")
        assert hasattr(webhook_logger, "warning")
        assert hasattr(webhook_logger, "error")


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_log_github_api_call_boundary_status_codes(self):
        """Test boundary status codes for log level determination."""
        # Test 199 (should use warning)
        with patch.object(github_logger, "warning") as mock_warning:
            log_github_api_call("test", "/api", "GET", 199, 100.0)
            mock_warning.assert_called_once()

        # Test 200 (should use info)
        with patch.object(github_logger, "info") as mock_info:
            log_github_api_call("test", "/api", "GET", 200, 100.0)
            mock_info.assert_called_once()

        # Test 399 (should use info)
        with patch.object(github_logger, "info") as mock_info:
            log_github_api_call("test", "/api", "GET", 399, 100.0)
            mock_info.assert_called_once()

        # Test 400 (should use warning)
        with patch.object(github_logger, "warning") as mock_warning:
            log_github_api_call("test", "/api", "GET", 400, 100.0)
            mock_warning.assert_called_once()

    def test_log_jira_api_call_boundary_status_codes(self):
        """Test boundary status codes for Jira API calls."""
        # Test 199 (should use warning)
        with patch.object(jira_logger, "warning") as mock_warning:
            log_jira_api_call("test", "/api", "GET", 199, 100.0)
            mock_warning.assert_called_once()

        # Test 200 (should use info)
        with patch.object(jira_logger, "info") as mock_info:
            log_jira_api_call("test", "/api", "GET", 200, 100.0)
            mock_info.assert_called_once()

    def test_configuration_security_filtering(self):
        """Test that sensitive configuration keys are properly filtered."""
        sensitive_keys = ["token", "secret", "password"]

        for sensitive_key in sensitive_keys:
            with patch.object(github_logger, "info") as mock_info:
                config = {
                    "safe_key": "safe_value",
                    sensitive_key: "sensitive_value",
                    "another_safe_key": "another_safe_value",
                }

                log_integration_configuration("github", True, config)

                # Verify the sensitive key was filtered out
                called_config = mock_info.call_args[1]["configuration"]
                assert sensitive_key not in called_config
                assert "safe_key" in called_config
                assert "another_safe_key" in called_config
