"""
Unit tests for component-specific logging utilities.

Tests cover:
- Core component logging utilities
- Tmux logging utilities
- Web interface logging utilities
- Integration logging utilities
- Component-specific decorators
"""

from unittest.mock import Mock, patch, call
import pytest

from cc_orchestrator.core.logging_utils import (
    log_orchestrator_start,
    log_orchestrator_shutdown,
    log_instance_lifecycle,
    log_task_assignment,
    log_task_status_change,
    log_database_operation,
    log_resource_usage,
    handle_instance_errors,
    handle_task_errors,
    track_performance
)

from cc_orchestrator.tmux.logging_utils import (
    log_session_operation,
    log_session_list,
    log_session_attach,
    log_session_detach,
    log_layout_setup,
    log_session_cleanup,
    log_orphaned_sessions,
    handle_tmux_errors
)

from cc_orchestrator.web.logging_utils import (
    log_api_request,
    log_api_response,
    log_websocket_connection,
    log_websocket_message,
    log_authentication_attempt,
    log_authorization_check,
    log_real_time_event,
    log_dashboard_access,
    handle_api_errors,
    track_api_performance
)

from cc_orchestrator.integrations.logging_utils import (
    log_github_api_call,
    log_github_sync,
    log_jira_api_call,
    log_jira_sync,
    log_webhook_received,
    log_webhook_processing,
    log_rate_limit_warning,
    log_service_status_change,
    log_integration_configuration,
    log_task_sync_status,
    handle_integration_errors
)


class TestCoreLoggingUtils:
    """Test core component logging utilities."""
    
    @patch('cc_orchestrator.core.logging_utils.orchestrator_logger')
    def test_log_orchestrator_start(self, mock_logger):
        """Test logging orchestrator startup."""
        config = {
            "max_instances": 5,
            "tmux_enabled": True,
            "web_enabled": True,
            "log_level": "INFO"
        }
        
        log_orchestrator_start(config)
        
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert "CC-Orchestrator starting up" in call_args[0][0]
        assert call_args[1]["max_instances"] == 5
        assert call_args[1]["tmux_enabled"] is True
    
    @patch('cc_orchestrator.core.logging_utils.orchestrator_logger')
    def test_log_orchestrator_shutdown(self, mock_logger):
        """Test logging orchestrator shutdown."""
        log_orchestrator_shutdown(graceful=True)
        
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert "CC-Orchestrator shutting down" in call_args[0][0]
        assert call_args[1]["graceful"] is True
    
    @patch('cc_orchestrator.core.logging_utils.get_logger')
    def test_log_instance_lifecycle_success(self, mock_get_logger):
        """Test logging successful instance lifecycle events."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        
        log_instance_lifecycle("claude-001", "start", "success", {"port": 8080})
        
        mock_logger.set_instance_id.assert_called_with("claude-001")
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert "Instance start completed" in call_args[0][0]
        assert call_args[1]["action"] == "start"
        assert call_args[1]["details"]["port"] == 8080
    
    @patch('cc_orchestrator.core.logging_utils.get_logger')
    def test_log_instance_lifecycle_error(self, mock_get_logger):
        """Test logging failed instance lifecycle events."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        
        log_instance_lifecycle("claude-002", "stop", "error", {"error": "timeout"})
        
        mock_logger.set_instance_id.assert_called_with("claude-002")
        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args
        assert "Instance stop failed" in call_args[0][0]
        assert call_args[1]["action"] == "stop"
    
    @patch('cc_orchestrator.core.logging_utils.get_logger')
    def test_log_task_assignment(self, mock_get_logger):
        """Test logging task assignment to instance."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        
        task_details = {
            "title": "Implement feature X",
            "priority": "high",
            "source": "github"
        }
        
        log_task_assignment("TASK-123", "claude-001", task_details)
        
        mock_logger.set_task_id.assert_called_with("TASK-123")
        mock_logger.set_instance_id.assert_called_with("claude-001")
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert "Task assigned to instance" in call_args[0][0]
        assert call_args[1]["task_title"] == "Implement feature X"
        assert call_args[1]["task_priority"] == "high"
    
    @patch('cc_orchestrator.core.logging_utils.get_logger')
    def test_log_task_status_change(self, mock_get_logger):
        """Test logging task status changes."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        
        log_task_status_change("TASK-456", "pending", "in_progress", "claude-002")
        
        mock_logger.set_task_id.assert_called_with("TASK-456")
        mock_logger.set_instance_id.assert_called_with("claude-002")
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert "Task status changed" in call_args[0][0]
        assert call_args[1]["old_status"] == "pending"
        assert call_args[1]["new_status"] == "in_progress"
    
    @patch('cc_orchestrator.core.logging_utils.database_logger')
    def test_log_database_operation(self, mock_logger):
        """Test logging database operations."""
        log_database_operation("INSERT", "instances", record_count=1, execution_time=0.05)
        
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert "Database INSERT on instances" in call_args[0][0]
        assert call_args[1]["operation"] == "INSERT"
        assert call_args[1]["table"] == "instances"
        assert call_args[1]["record_count"] == 1
        assert call_args[1]["execution_time"] == 0.05
    
    @patch('cc_orchestrator.core.logging_utils.get_logger')
    def test_log_resource_usage(self, mock_get_logger):
        """Test logging resource usage metrics."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        
        log_resource_usage("claude-001", 45.2, 256.7, 1024.0)
        
        mock_logger.set_instance_id.assert_called_with("claude-001")
        mock_logger.debug.assert_called_once()
        call_args = mock_logger.debug.call_args
        assert "Resource usage update" in call_args[0][0]
        assert call_args[1]["cpu_percent"] == 45.2
        assert call_args[1]["memory_mb"] == 256.7
        assert call_args[1]["disk_usage_mb"] == 1024.0


class TestTmuxLoggingUtils:
    """Test tmux component logging utilities."""
    
    @patch('cc_orchestrator.tmux.logging_utils.tmux_logger')
    def test_log_session_operation_success(self, mock_logger):
        """Test logging successful tmux session operations."""
        log_session_operation("create", "cc-orchestrator-claude-001", "success", {"layout": "main"})
        
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert "Tmux session create completed" in call_args[0][0]
        assert call_args[1]["operation"] == "create"
        assert call_args[1]["session_name"] == "cc-orchestrator-claude-001"
        assert call_args[1]["details"]["layout"] == "main"
    
    @patch('cc_orchestrator.tmux.logging_utils.tmux_logger')
    def test_log_session_operation_error(self, mock_logger):
        """Test logging failed tmux session operations."""
        log_session_operation("attach", "nonexistent-session", "error", {"error": "session not found"})
        
        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args
        assert "Tmux session attach failed" in call_args[0][0]
        assert call_args[1]["operation"] == "attach"
        assert call_args[1]["session_name"] == "nonexistent-session"
    
    @patch('cc_orchestrator.tmux.logging_utils.tmux_logger')
    def test_log_session_list(self, mock_logger):
        """Test logging tmux session list."""
        sessions = [
            {"name": "cc-orchestrator-claude-001"},
            {"name": "cc-orchestrator-claude-002"}
        ]
        
        log_session_list(sessions)
        
        mock_logger.debug.assert_called_once()
        call_args = mock_logger.debug.call_args
        assert "Tmux sessions listed" in call_args[0][0]
        assert call_args[1]["session_count"] == 2
        assert "cc-orchestrator-claude-001" in call_args[1]["sessions"]
    
    @patch('cc_orchestrator.tmux.logging_utils.get_logger')
    def test_log_session_attach(self, mock_get_logger):
        """Test logging session attachment."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        
        log_session_attach("test-session", "claude-001")
        
        mock_logger.set_instance_id.assert_called_with("claude-001")
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert "Attached to tmux session" in call_args[0][0]
        assert call_args[1]["session_name"] == "test-session"
    
    @patch('cc_orchestrator.tmux.logging_utils.tmux_logger')
    def test_log_layout_setup(self, mock_logger):
        """Test logging tmux layout configuration."""
        windows = ["main", "logs", "monitoring"]
        
        log_layout_setup("test-session", "three-pane", windows)
        
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert "Tmux layout configured" in call_args[0][0]
        assert call_args[1]["layout_name"] == "three-pane"
        assert call_args[1]["window_count"] == 3
        assert call_args[1]["windows"] == windows
    
    @patch('cc_orchestrator.tmux.logging_utils.tmux_logger')
    def test_log_orphaned_sessions_found(self, mock_logger):
        """Test logging when orphaned sessions are found."""
        orphaned = ["old-session-1", "old-session-2"]
        
        log_orphaned_sessions(orphaned)
        
        mock_logger.warning.assert_called_once()
        call_args = mock_logger.warning.call_args
        assert "Orphaned tmux sessions detected" in call_args[0][0]
        assert call_args[1]["session_count"] == 2
        assert call_args[1]["sessions"] == orphaned
    
    @patch('cc_orchestrator.tmux.logging_utils.tmux_logger')
    def test_log_orphaned_sessions_none_found(self, mock_logger):
        """Test logging when no orphaned sessions are found."""
        log_orphaned_sessions([])
        
        mock_logger.debug.assert_called_once()
        call_args = mock_logger.debug.call_args
        assert "No orphaned tmux sessions found" in call_args[0][0]


class TestWebLoggingUtils:
    """Test web interface logging utilities."""
    
    @patch('cc_orchestrator.web.logging_utils.api_logger')
    def test_log_api_request(self, mock_logger):
        """Test logging API requests."""
        log_api_request("GET", "/api/instances", "192.168.1.100", "Mozilla/5.0", "req-123")
        
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert "API request received" in call_args[0][0]
        assert call_args[1]["method"] == "GET"
        assert call_args[1]["path"] == "/api/instances"
        assert call_args[1]["client_ip"] == "192.168.1.100"
        assert call_args[1]["request_id"] == "req-123"
    
    @patch('cc_orchestrator.web.logging_utils.api_logger')
    def test_log_api_response_success(self, mock_logger):
        """Test logging successful API responses."""
        log_api_response("GET", "/api/instances", 200, 150.5, "req-123")
        
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert "API response sent" in call_args[0][0]
        assert call_args[1]["status_code"] == 200
        assert call_args[1]["response_time_ms"] == 150.5
    
    @patch('cc_orchestrator.web.logging_utils.api_logger')
    def test_log_api_response_error(self, mock_logger):
        """Test logging error API responses."""
        log_api_response("POST", "/api/instances", 500, 75.0, "req-456")
        
        mock_logger.warning.assert_called_once()
        call_args = mock_logger.warning.call_args
        assert "API response sent" in call_args[0][0]
        assert call_args[1]["status_code"] == 500
        assert call_args[1]["response_time_ms"] == 75.0
    
    @patch('cc_orchestrator.web.logging_utils.websocket_logger')
    def test_log_websocket_connection(self, mock_logger):
        """Test logging WebSocket connections."""
        log_websocket_connection("192.168.1.100", "connect", "ws-conn-123")
        
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert "WebSocket connect" in call_args[0][0]
        assert call_args[1]["client_ip"] == "192.168.1.100"
        assert call_args[1]["connection_id"] == "ws-conn-123"
    
    @patch('cc_orchestrator.web.logging_utils.websocket_logger')
    def test_log_websocket_message(self, mock_logger):
        """Test logging WebSocket messages."""
        log_websocket_message("ws-conn-123", "instance_status", "outbound", 256)
        
        mock_logger.debug.assert_called_once()
        call_args = mock_logger.debug.call_args
        assert "WebSocket message outbound" in call_args[0][0]
        assert call_args[1]["connection_id"] == "ws-conn-123"
        assert call_args[1]["message_type"] == "instance_status"
        assert call_args[1]["message_size"] == 256
    
    @patch('cc_orchestrator.web.logging_utils.auth_logger')
    def test_log_authentication_success(self, mock_logger):
        """Test logging successful authentication."""
        log_authentication_attempt("oauth", "192.168.1.100", True, "user123")
        
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert "Authentication successful" in call_args[0][0]
        assert call_args[1]["auth_method"] == "oauth"
        assert call_args[1]["user_id"] == "user123"
    
    @patch('cc_orchestrator.web.logging_utils.auth_logger')
    def test_log_authentication_failure(self, mock_logger):
        """Test logging failed authentication."""
        log_authentication_attempt("token", "192.168.1.100", False, None, "invalid token")
        
        mock_logger.warning.assert_called_once()
        call_args = mock_logger.warning.call_args
        assert "Authentication failed" in call_args[0][0]
        assert call_args[1]["auth_method"] == "token"
        assert call_args[1]["reason"] == "invalid token"
    
    @patch('cc_orchestrator.web.logging_utils.get_logger')
    def test_log_real_time_event(self, mock_get_logger):
        """Test logging real-time event broadcasting."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        
        log_real_time_event("instance_status", 5, 512, "claude-001", "TASK-123")
        
        mock_logger.set_instance_id.assert_called_with("claude-001")
        mock_logger.set_task_id.assert_called_with("TASK-123")
        mock_logger.debug.assert_called_once()
        call_args = mock_logger.debug.call_args
        assert "Real-time event broadcast" in call_args[0][0]
        assert call_args[1]["event_type"] == "instance_status"
        assert call_args[1]["target_connections"] == 5


class TestIntegrationLoggingUtils:
    """Test integration component logging utilities."""
    
    @patch('cc_orchestrator.integrations.logging_utils.github_logger')
    def test_log_github_api_call_success(self, mock_logger):
        """Test logging successful GitHub API calls."""
        log_github_api_call("list_issues", "/repos/owner/repo/issues", "GET", 200, 150.5, 4500)
        
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert "GitHub API list_issues" in call_args[0][0]
        assert call_args[1]["endpoint"] == "/repos/owner/repo/issues"
        assert call_args[1]["status_code"] == 200
        assert call_args[1]["rate_limit_remaining"] == 4500
    
    @patch('cc_orchestrator.integrations.logging_utils.github_logger')
    def test_log_github_api_call_error(self, mock_logger):
        """Test logging failed GitHub API calls."""
        log_github_api_call("create_issue", "/repos/owner/repo/issues", "POST", 422, 200.0, 4499)
        
        mock_logger.warning.assert_called_once()
        call_args = mock_logger.warning.call_args
        assert "GitHub API create_issue" in call_args[0][0]
        assert call_args[1]["status_code"] == 422
    
    @patch('cc_orchestrator.integrations.logging_utils.github_logger')
    def test_log_github_sync(self, mock_logger):
        """Test logging GitHub synchronization operations."""
        log_github_sync("owner/repo", "issues", 50, 5, 10, 1)
        
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert "GitHub issues sync completed" in call_args[0][0]
        assert call_args[1]["repository"] == "owner/repo"
        assert call_args[1]["items_processed"] == 50
        assert call_args[1]["items_created"] == 5
        assert call_args[1]["items_updated"] == 10
        assert call_args[1]["errors"] == 1
    
    @patch('cc_orchestrator.integrations.logging_utils.webhook_logger')
    def test_log_webhook_received(self, mock_logger):
        """Test logging incoming webhook events."""
        log_webhook_received("github", "issues", 1024, True, 50.0)
        
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert "Webhook received" in call_args[0][0]
        assert call_args[1]["source"] == "github"
        assert call_args[1]["event_type"] == "issues"
        assert call_args[1]["payload_size"] == 1024
        assert call_args[1]["signature_valid"] is True
        assert call_args[1]["processing_time_ms"] == 50.0
    
    @patch('cc_orchestrator.integrations.logging_utils.webhook_logger')
    def test_log_webhook_processing(self, mock_logger):
        """Test logging webhook processing results."""
        errors = ["Invalid task format", "Missing required field"]
        log_webhook_processing("github", "issues", 2, 1, errors)
        
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert "Webhook processing completed" in call_args[0][0]
        assert call_args[1]["tasks_created"] == 2
        assert call_args[1]["tasks_updated"] == 1
        assert call_args[1]["errors"] == errors
    
    @patch('cc_orchestrator.integrations.logging_utils.github_logger')
    def test_log_rate_limit_warning(self, mock_logger):
        """Test logging rate limit warnings."""
        log_rate_limit_warning("github", 100, "2025-07-27T12:00:00Z", "list_issues")
        
        mock_logger.warning.assert_called_once()
        call_args = mock_logger.warning.call_args
        assert "github rate limit warning" in call_args[0][0]
        assert call_args[1]["remaining_requests"] == 100
        assert call_args[1]["reset_time"] == "2025-07-27T12:00:00Z"
        assert call_args[1]["operation"] == "list_issues"
    
    @patch('cc_orchestrator.integrations.logging_utils.get_logger')
    def test_log_task_sync_status(self, mock_get_logger):
        """Test logging task synchronization status."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        
        details = {"status_code": 200, "updated_fields": ["status", "assignee"]}
        log_task_sync_status("TASK-123", "456", "github", "to_external", "success", details)
        
        mock_logger.set_task_id.assert_called_with("TASK-123")
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        assert "Task sync to_external" in call_args[0][0]
        assert call_args[1]["external_id"] == "456"
        assert call_args[1]["service"] == "github"
        assert call_args[1]["status"] == "success"


class TestComponentDecoratorFunctionality:
    """Test component-specific decorator functions."""
    
    def test_handle_instance_errors_decorator(self):
        """Test instance error handling decorator."""
        from cc_orchestrator.utils.logging import InstanceError
        
        @handle_instance_errors()
        def instance_function():
            raise InstanceError("Test instance error")
        
        with pytest.raises(InstanceError):
            instance_function()
    
    def test_handle_task_errors_decorator(self):
        """Test task error handling decorator."""
        from cc_orchestrator.utils.logging import TaskError
        
        @handle_task_errors()
        def task_function():
            raise TaskError("Test task error")
        
        with pytest.raises(TaskError):
            task_function()
    
    def test_track_performance_decorator(self):
        """Test performance tracking decorator for core operations."""
        @track_performance("test_operation")
        def timed_operation():
            return "completed"
        
        result = timed_operation()
        assert result == "completed"
    
    def test_handle_api_errors_decorator(self):
        """Test API error handling decorator."""
        @handle_api_errors()
        def api_function():
            raise ValueError("API error")
        
        with pytest.raises(Exception):  # Should convert to CCOrchestratorException
            api_function()
    
    def test_track_api_performance_decorator(self):
        """Test API performance tracking decorator."""
        @track_api_performance()
        def api_operation():
            return {"status": "ok"}
        
        result = api_operation()
        assert result["status"] == "ok"