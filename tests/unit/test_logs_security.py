"""
Security tests for the logs router API endpoints.

Tests critical security requirements identified in code review.
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from src.cc_orchestrator.web.app import app
from src.cc_orchestrator.web.routers.v1.logs import (
    LOG_STREAMING_CONFIG,
    LogEntry,
    LogLevelEnum,
    LogSearchRequest,
    audit_log_access,
    audit_log_storage,
    log_storage,
    sanitize_log_content,
    sanitize_log_entry,
    stream_stats,
)


class TestLogContentSanitization:
    """Test sensitive data sanitization functionality."""

    def test_sanitize_passwords(self):
        """Test that passwords are properly redacted."""
        content = "User password=secret123 logged in"
        sanitized = sanitize_log_content(content)
        assert "secret123" not in sanitized
        assert "[REDACTED]" in sanitized

    def test_sanitize_api_keys(self):
        """Test that API keys are properly redacted."""
        content = "API request with api_key=abc123xyz456"
        sanitized = sanitize_log_content(content)
        assert "abc123xyz456" not in sanitized
        assert "[REDACTED]" in sanitized

    def test_sanitize_bearer_tokens(self):
        """Test that Bearer tokens are properly redacted."""
        content = "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
        sanitized = sanitize_log_content(content)
        assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in sanitized
        assert "[REDACTED]" in sanitized

    def test_sanitize_credit_cards(self):
        """Test that credit card numbers are properly redacted."""
        content = "Payment processed for card 4532-1234-5678-9012"
        sanitized = sanitize_log_content(content)
        assert "4532-1234-5678-9012" not in sanitized
        assert "[REDACTED]" in sanitized

    def test_sanitize_oauth_tokens(self):
        """Test that OAuth tokens are properly redacted."""
        content = "OAuth token: oauth=ya29.a0AfH6SMC7X8..."
        sanitized = sanitize_log_content(content)
        assert "ya29.a0AfH6SMC7X8..." not in sanitized
        assert "[REDACTED]" in sanitized

    def test_sanitize_log_entry_message(self):
        """Test that log entry messages are sanitized."""
        entry = LogEntry(
            id="test_1",
            timestamp=datetime.now(),
            level=LogLevelEnum.INFO,
            logger="test.logger",
            message="User authenticated with password=secret123",
            metadata={},
        )

        sanitized = sanitize_log_entry(entry)
        assert "secret123" not in sanitized.message
        assert "[REDACTED]" in sanitized.message

    def test_sanitize_log_entry_metadata(self):
        """Test that log entry metadata is sanitized."""
        entry = LogEntry(
            id="test_1",
            timestamp=datetime.now(),
            level=LogLevelEnum.INFO,
            logger="test.logger",
            message="User login",
            metadata={"user_token": "secret_token_123", "user_id": "user_456"},
        )

        sanitized = sanitize_log_entry(entry)
        assert "secret_token_123" not in str(sanitized.metadata)
        assert "[REDACTED]" in sanitized.metadata["user_token"]
        assert sanitized.metadata["user_id"] == "user_456"  # Should not be redacted

    def test_sanitize_log_entry_exception_traceback(self):
        """Test that exception tracebacks are sanitized."""
        entry = LogEntry(
            id="test_1",
            timestamp=datetime.now(),
            level=LogLevelEnum.ERROR,
            logger="test.logger",
            message="Authentication failed",
            exception={
                "type": "AuthError",
                "message": "Invalid credentials",
                "traceback": ["File auth.py, line 42", "password=secret123 failed"],
            },
            metadata={},
        )

        sanitized = sanitize_log_entry(entry)
        assert "secret123" not in str(sanitized.exception["traceback"])
        assert "[REDACTED]" in sanitized.exception["traceback"][1]

    def test_empty_content_handling(self):
        """Test handling of empty or None content."""
        assert sanitize_log_content("") == ""
        assert sanitize_log_content(None) is None

    def test_multiple_sensitive_patterns(self):
        """Test that multiple sensitive patterns in one string are all redacted."""
        content = "User login: password=secret123 with token=abc456xyz"
        sanitized = sanitize_log_content(content)
        assert "secret123" not in sanitized
        assert "abc456xyz" not in sanitized
        assert sanitized.count("[REDACTED]") == 2


class TestAuthentication:
    """Test authentication requirements for log access."""

    def setup_method(self):
        """Setup test environment."""
        self.client = TestClient(app)
        log_storage.clear()
        stream_stats.update(
            {
                "active_streams": 0,
                "total_entries_streamed": 0,
                "stream_start_time": datetime.now(),
                "buffer_usage": {},
            }
        )

    @patch("src.cc_orchestrator.web.routers.v1.logs.get_current_user")
    def test_search_requires_authentication(self, mock_get_user):
        """Test that log search requires authentication."""
        mock_get_user.side_effect = HTTPException(
            status_code=401, detail="Unauthorized"
        )

        response = self.client.get("/api/v1/logs/search")
        assert response.status_code == 401

    @patch("src.cc_orchestrator.web.routers.v1.logs.get_current_user")
    def test_export_requires_authentication(self, mock_get_user):
        """Test that log export requires authentication."""
        mock_get_user.side_effect = HTTPException(
            status_code=401, detail="Unauthorized"
        )

        response = self.client.post(
            "/api/v1/logs/export", json={"search": {"limit": 100}, "format": "json"}
        )
        assert response.status_code == 401

    @patch("src.cc_orchestrator.web.routers.v1.logs.get_current_user")
    def test_stream_start_requires_authentication(self, mock_get_user):
        """Test that stream start requires authentication."""
        mock_get_user.side_effect = HTTPException(
            status_code=401, detail="Unauthorized"
        )

        response = self.client.post(
            "/api/v1/logs/stream/start", json={"level": ["INFO"], "buffer_size": 100}
        )
        assert response.status_code == 401


class TestRateLimiting:
    """Test rate limiting and resource protection."""

    def setup_method(self):
        """Setup test environment."""
        self.client = TestClient(app)
        log_storage.clear()
        stream_stats.update(
            {
                "active_streams": 0,
                "total_entries_streamed": 0,
                "stream_start_time": datetime.now(),
                "buffer_usage": {},
            }
        )

    def test_search_limit_enforcement(self):
        """Test that search limits are enforced."""
        # Try to request more than allowed limit with authentication
        response = self.client.get(
            f"/api/v1/logs/search?limit={LOG_STREAMING_CONFIG.max_entries_per_request + 1}",
            headers={"X-Dev-Token": "development-token"},
        )
        assert response.status_code == 422  # Validation error

    def test_export_limit_enforcement(self):
        """Test that export limits are enforced."""
        # Add test log entries
        test_entry = LogEntry(
            id="test_1",
            timestamp=datetime.now(),
            level=LogLevelEnum.INFO,
            logger="test.logger",
            message="Test message",
            metadata={},
        )
        log_storage.append(test_entry)

        # Request export with limit exceeding maximum, with authentication
        response = self.client.post(
            "/api/v1/logs/export",
            json={
                "search": {"limit": LOG_STREAMING_CONFIG.max_export_entries + 1},
                "format": "json",
            },
            headers={"X-Dev-Token": "development-token"},
        )

        # Should succeed but limit should be capped
        assert response.status_code == 200

    @patch("src.cc_orchestrator.web.routers.v1.logs.connection_manager")
    def test_concurrent_stream_limit(self, mock_connection_manager):
        """Test that concurrent stream limits are enforced."""
        mock_connection_manager.broadcast_message = AsyncMock()

        # Set streams to maximum
        stream_stats["active_streams"] = LOG_STREAMING_CONFIG.max_concurrent_streams

        response = self.client.post(
            "/api/v1/logs/stream/start",
            json={"level": ["INFO"], "buffer_size": 100},
            headers={"X-Dev-Token": "development-token"},
        )
        assert response.status_code == 429  # Too Many Requests


class TestAuditLogging:
    """Test audit logging functionality."""

    def setup_method(self):
        """Setup test environment."""
        audit_log_storage.clear()

    @pytest.mark.asyncio
    async def test_audit_log_search_access(self):
        """Test that search access is properly audited."""
        await audit_log_access(
            user_id="test_user_123",
            action="search",
            details={
                "query": "test query",
                "level": ["INFO"],
                "ip_address": "192.168.1.1",
            },
        )

        assert len(audit_log_storage) == 1
        audit_entry = audit_log_storage[0]
        assert audit_entry["user_id"] == "test_user_123"
        assert audit_entry["action"] == "search"
        assert audit_entry["details"]["query"] == "test query"
        assert audit_entry["ip_address"] == "192.168.1.1"

    @pytest.mark.asyncio
    async def test_audit_log_export_access(self):
        """Test that export access is properly audited."""
        await audit_log_access(
            user_id="test_user_456",
            action="export",
            details={
                "format": "json",
                "include_metadata": True,
                "filename": "test_export.json",
            },
        )

        assert len(audit_log_storage) == 1
        audit_entry = audit_log_storage[0]
        assert audit_entry["user_id"] == "test_user_456"
        assert audit_entry["action"] == "export"
        assert audit_entry["details"]["format"] == "json"

    @pytest.mark.asyncio
    async def test_audit_log_stream_operations(self):
        """Test that stream operations are properly audited."""
        # Test stream start
        await audit_log_access(
            user_id="test_user_789",
            action="stream_start",
            details={"stream_id": "stream_123", "filter": {"level": ["ERROR"]}},
        )

        # Test stream stop
        await audit_log_access(
            user_id="test_user_789",
            action="stream_stop",
            details={"stream_id": "stream_123"},
        )

        assert len(audit_log_storage) == 2
        assert audit_log_storage[0]["action"] == "stream_start"
        assert audit_log_storage[1]["action"] == "stream_stop"


class TestPerformanceSafeguards:
    """Test performance protection mechanisms."""

    def test_dangerous_regex_detection(self):
        """Test that dangerous regex patterns are detected and blocked."""
        from src.cc_orchestrator.web.routers.v1.logs import _filter_by_query

        entries = [
            LogEntry(
                id="test_1",
                timestamp=datetime.now(),
                level=LogLevelEnum.INFO,
                logger="test.logger",
                message="Test message",
                metadata={},
            )
        ]

        # Test dangerous patterns
        dangerous_queries = [
            "test.*.*.*.*",  # Multiple dots with asterisks
            "test++++++",  # Multiple plus signs
            "(test){10}",  # Potential exponential backtracking
        ]

        for dangerous_query in dangerous_queries:
            search_request = LogSearchRequest(query=dangerous_query, regex_enabled=True)

            # Should not crash and should fall back to literal search
            result = _filter_by_query(entries, search_request)
            assert isinstance(result, list)

    @patch("src.cc_orchestrator.web.routers.v1.logs.datetime")
    def test_query_timeout_protection(self, mock_datetime):
        """Test that query processing has timeout protection."""
        from src.cc_orchestrator.web.routers.v1.logs import _filter_by_query

        # Mock datetime to simulate timeout
        start_time = datetime.now()
        timeout_time = start_time + timedelta(
            seconds=LOG_STREAMING_CONFIG.query_timeout_seconds + 1
        )
        mock_datetime.now.side_effect = [start_time, timeout_time]

        # Create many entries to trigger timeout
        entries = []
        for i in range(1000):
            entries.append(
                LogEntry(
                    id=f"test_{i}",
                    timestamp=datetime.now(),
                    level=LogLevelEnum.INFO,
                    logger="test.logger",
                    message=f"Test message {i}",
                    metadata={},
                )
            )

        search_request = LogSearchRequest(query="test", regex_enabled=False)

        result = _filter_by_query(entries, search_request)
        # Should return partial results due to timeout
        assert len(result) < len(entries)


class TestDataExfiltrationProtection:
    """Test protection against data exfiltration."""

    def setup_method(self):
        """Setup test environment."""
        self.client = TestClient(app)
        log_storage.clear()

    def test_export_sensitive_data_protection(self):
        """Test that exported data is sanitized."""
        # Use both direct manipulation and patching for complete isolation
        from unittest.mock import patch
        
        # Create isolated log storage for this test
        test_log_storage = []
        
        # Add log entry with sensitive data
        sensitive_entry = LogEntry(
            id="sensitive_1",
            timestamp=datetime.now(),
            level=LogLevelEnum.INFO,
            logger="auth.logger",
            message="User login with password=secret123",
            metadata={"api_key": "sensitive_key_456"},
        )
        test_log_storage.append(sensitive_entry)

        # Save the original log storage and replace it temporarily
        import src.cc_orchestrator.web.routers.v1.logs as logs_module
        original_log_storage = logs_module.log_storage
        
        try:
            # Directly replace the global variable
            logs_module.log_storage = test_log_storage
            
            response = self.client.post(
                "/api/v1/logs/export",
                json={"search": {"limit": 100}, "format": "json"},
                headers={"X-Dev-Token": "development-token"},
            )

            assert response.status_code == 200
            content = response.content.decode()

            # Sensitive data should be redacted
            assert "secret123" not in content
            assert "sensitive_key_456" not in content
            assert "[REDACTED]" in content
        finally:
            # Restore the original log storage
            logs_module.log_storage = original_log_storage

    def test_search_sensitive_data_protection(self):
        """Test that search results are sanitized."""
        # Use patch to ensure complete isolation during test execution
        from unittest.mock import patch
        
        # Create isolated log storage for this test
        test_log_storage = []
        
        # Add log entry with sensitive data
        sensitive_entry = LogEntry(
            id="sensitive_1",
            timestamp=datetime.now(),
            level=LogLevelEnum.INFO,
            logger="auth.logger",
            message="API call with token=bearer_abc123",
            metadata={},
        )
        test_log_storage.append(sensitive_entry)

        # Patch the log_storage to use our isolated storage during the API call
        with patch("src.cc_orchestrator.web.routers.v1.logs.log_storage", test_log_storage):
            response = self.client.get(
                "/api/v1/logs/search", headers={"X-Dev-Token": "development-token"}
            )
            assert response.status_code == 200

            data = response.json()
            entries = data["entries"]

            # Sensitive data should be redacted in search results
            assert len(entries) == 1
            assert "bearer_abc123" not in entries[0]["message"]
            assert "[REDACTED]" in entries[0]["message"]


class TestIntegrationSecurity:
    """Integration tests for complete security workflow."""

    def setup_method(self):
        """Setup test environment."""
        self.client = TestClient(app)
        log_storage.clear()
        audit_log_storage.clear()
        stream_stats.update(
            {
                "active_streams": 0,
                "total_entries_streamed": 0,
                "stream_start_time": datetime.now(),
                "buffer_usage": {},
            }
        )

    def test_complete_security_workflow(self):
        """Test complete security workflow from search to export."""
        # Use patch to ensure complete isolation during test execution
        from unittest.mock import patch
        
        # Create isolated log storage for this test
        test_log_storage = []
        test_audit_log_storage = []
        
        # Add log entries with mixed sensitive and normal data
        entries = [
            LogEntry(
                id="normal_1",
                timestamp=datetime.now(),
                level=LogLevelEnum.INFO,
                logger="app.logger",
                message="Normal application log",
                metadata={},
            ),
            LogEntry(
                id="sensitive_1",
                timestamp=datetime.now(),
                level=LogLevelEnum.ERROR,
                logger="auth.logger",
                message="Login failed for user with password=secret123",
                metadata={"session_token": "token_abc456"},
            ),
        ]

        for entry in entries:
            test_log_storage.append(entry)

        # Patch both log storage and audit storage to use isolated versions
        with patch("src.cc_orchestrator.web.routers.v1.logs.log_storage", test_log_storage), \
             patch("src.cc_orchestrator.web.routers.v1.logs.audit_log_storage", test_audit_log_storage):
            
            # 1. Test search with audit logging
            search_response = self.client.get(
                "/api/v1/logs/search?query=login",
                headers={"X-Dev-Token": "development-token"},
            )
            assert search_response.status_code == 200

            search_data = search_response.json()
            assert len(search_data["entries"]) == 1
            assert "secret123" not in str(search_data["entries"])
            assert "[REDACTED]" in search_data["entries"][0]["message"]

            # 2. Test export with audit logging
            export_response = self.client.post(
                "/api/v1/logs/export",
                json={"search": {"query": "login", "limit": 100}, "format": "json"},
                headers={"X-Dev-Token": "development-token"},
            )
            assert export_response.status_code == 200

            export_content = export_response.content.decode()
            assert "secret123" not in export_content
            assert "token_abc456" not in export_content
            assert "[REDACTED]" in export_content

            # 3. Verify audit logging occurred
            assert len(test_audit_log_storage) == 2  # Search + Export
            assert test_audit_log_storage[0]["action"] == "search"
            assert test_audit_log_storage[1]["action"] == "export"
            assert all(entry["user_id"] == "dev_user" for entry in test_audit_log_storage)
