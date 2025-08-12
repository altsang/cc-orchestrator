"""
Tests for the logs router API endpoints.
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from src.cc_orchestrator.web.app import app
from src.cc_orchestrator.web.routers.v1.logs import (
    LogEntry,
    LogEntryType,
    LogExportFormat,
    LogLevelEnum,
    LogSearchRequest,
    LogStreamFilter,
    _filter_by_query,
    _filter_log_entries,
    _generate_export_content,
    add_log_entry,
    log_storage,
    stream_stats,
)


class TestLogsRouter:
    """Test suite for logs router endpoints."""

    def setup_method(self):
        """Setup test environment before each test."""
        # Clear log storage and stats
        global log_storage
        log_storage.clear()
        stream_stats.update(
            {
                "active_streams": 0,
                "total_entries_streamed": 0,
                "stream_start_time": datetime.now(),
                "buffer_usage": {},
            }
        )

        # Create test client
        self.client = TestClient(app)

        # Add sample log entries
        self.sample_logs = [
            LogEntry(
                id="log_1",
                timestamp=datetime.now() - timedelta(minutes=5),
                level=LogLevelEnum.INFO,
                logger="test.logger",
                message="Test info message",
                module="test_module",
                function="test_function",
                line=42,
                context=LogEntryType.SYSTEM,
                metadata={"test": "data"},
            ),
            LogEntry(
                id="log_2",
                timestamp=datetime.now() - timedelta(minutes=3),
                level=LogLevelEnum.ERROR,
                logger="error.logger",
                message="Test error message with exception",
                context=LogEntryType.WEB,
                instance_id="instance_123",
                exception={
                    "type": "ValueError",
                    "message": "Test exception",
                    "traceback": ["Traceback line 1", "Traceback line 2"],
                },
            ),
        ]

        log_storage.extend(self.sample_logs)

    def test_search_logs_basic(self):
        """Test basic log search functionality."""
        response = self.client.get("/api/v1/logs/search")
        assert response.status_code == 200

        data = response.json()
        assert "entries" in data
        assert "total_count" in data
        assert data["total_count"] == 2

    def test_search_logs_with_query(self):
        """Test log search with text query."""
        response = self.client.get("/api/v1/logs/search?query=error")
        assert response.status_code == 200

        data = response.json()
        assert data["total_count"] == 1
        assert "error" in data["entries"][0]["message"].lower()

    def test_get_log_levels(self):
        """Test getting available log levels."""
        response = self.client.get("/api/v1/logs/levels")
        assert response.status_code == 200

        levels = response.json()
        assert isinstance(levels, list)
        assert "DEBUG" in levels
        assert "INFO" in levels
        assert "ERROR" in levels

    def test_get_log_contexts(self):
        """Test getting available log contexts."""
        response = self.client.get("/api/v1/logs/contexts")
        assert response.status_code == 200

        contexts = response.json()
        assert isinstance(contexts, list)
        assert "system" in contexts
        assert "web" in contexts

    def test_get_log_stats(self):
        """Test getting log streaming statistics."""
        response = self.client.get("/api/v1/logs/stats")
        assert response.status_code == 200

        stats = response.json()
        assert "active_streams" in stats
        assert stats["active_streams"] == 0

    @patch("src.cc_orchestrator.web.routers.v1.logs.connection_manager")
    def test_start_log_stream(self, mock_connection_manager):
        """Test starting a log stream."""
        mock_connection_manager.broadcast_message = AsyncMock()

        stream_filter = {
            "level": ["ERROR"],
            "buffer_size": 50,
        }

        response = self.client.post("/api/v1/logs/stream/start", json=stream_filter)
        assert response.status_code == 200

        data = response.json()
        assert "stream_id" in data
        assert data["status"] == "started"

    @pytest.mark.asyncio
    async def test_add_log_entry_function(self):
        """Test the add_log_entry helper function."""
        initial_count = len(log_storage)

        with patch(
            "src.cc_orchestrator.web.routers.v1.logs.connection_manager"
        ) as mock_cm:
            mock_cm.broadcast_message = AsyncMock()

            await add_log_entry(
                level=LogLevelEnum.WARNING,
                logger_name="test.async.logger",
                message="Async test message",
                context=LogEntryType.INTEGRATION,
                instance_id="async_instance",
                metadata={"async": True},
            )

        # Verify log was added
        assert len(log_storage) == initial_count + 1

        new_log = log_storage[-1]
        assert new_log.level == LogLevelEnum.WARNING
        assert new_log.logger == "test.async.logger"

    def test_search_logs_value_error(self):
        """Test search_logs with invalid parameters that raise ValueError."""
        # Test with query too long
        long_query = "x" * 1001
        response = self.client.get(f"/api/v1/logs/search?query={long_query}")
        assert response.status_code == 400
        assert "Search query too long" in response.json()["detail"]

    def test_search_logs_limit_validation_error(self):
        """Test search_logs with invalid limit values."""
        # Test with limit too high
        response = self.client.get("/api/v1/logs/search?limit=20000")
        assert response.status_code == 400
        assert "Limit must be between 1 and 10000" in response.json()["detail"]

        # Test with limit too low
        response = self.client.get("/api/v1/logs/search?limit=0")
        assert response.status_code == 400

    @patch("src.cc_orchestrator.web.routers.v1.logs._filter_log_entries")
    def test_search_logs_generic_exception(self, mock_filter):
        """Test search_logs with generic exception handling."""
        mock_filter.side_effect = RuntimeError("Database connection failed")

        response = self.client.get("/api/v1/logs/search")
        assert response.status_code == 500
        assert response.json()["detail"] == "Log search failed"

    def test_search_logs_with_time_range(self):
        """Test search_logs with start_time and end_time filters."""
        # Add log entries with specific timestamps
        now = datetime.now()
        old_entry = LogEntry(
            id="old_log",
            timestamp=now - timedelta(hours=2),
            level=LogLevelEnum.DEBUG,
            logger="old.logger",
            message="Old message",
        )
        recent_entry = LogEntry(
            id="recent_log",
            timestamp=now - timedelta(minutes=30),
            level=LogLevelEnum.INFO,
            logger="recent.logger",
            message="Recent message",
        )
        log_storage.extend([old_entry, recent_entry])

        # Test with start_time filter
        start_time = (now - timedelta(hours=1)).isoformat()
        response = self.client.get(f"/api/v1/logs/search?start_time={start_time}")
        assert response.status_code == 200
        data = response.json()
        # Should find recent_entry plus the 2 original sample logs
        assert data["total_count"] >= 1

        # Test with end_time filter
        end_time = (now - timedelta(hours=1, minutes=30)).isoformat()
        response = self.client.get(f"/api/v1/logs/search?end_time={end_time}")
        assert response.status_code == 200

    def test_search_logs_with_multiple_levels(self):
        """Test search_logs with multiple log level filters."""
        response = self.client.get("/api/v1/logs/search?level=ERROR&level=WARNING")
        assert response.status_code == 200
        data = response.json()
        # Should find only ERROR entries from sample data
        assert data["total_count"] >= 1

    def test_search_logs_with_multiple_contexts(self):
        """Test search_logs with multiple context filters."""
        response = self.client.get("/api/v1/logs/search?context=system&context=web")
        assert response.status_code == 200
        data = response.json()
        # Should find entries with SYSTEM and WEB contexts
        assert data["total_count"] >= 2

    def test_search_logs_with_instance_id(self):
        """Test search_logs with instance_id filter."""
        response = self.client.get("/api/v1/logs/search?instance_id=instance_123")
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 1
        assert data["entries"][0]["instance_id"] == "instance_123"

    def test_search_logs_with_task_id(self):
        """Test search_logs with task_id filter."""
        # Add entry with task_id
        task_entry = LogEntry(
            id="task_log",
            timestamp=datetime.now(),
            level=LogLevelEnum.INFO,
            logger="task.logger",
            message="Task message",
            task_id="task_456",
        )
        log_storage.append(task_entry)

        response = self.client.get("/api/v1/logs/search?task_id=task_456")
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 1
        assert data["entries"][0]["task_id"] == "task_456"

    def test_search_logs_with_regex(self):
        """Test search_logs with regex_enabled."""
        response = self.client.get(
            "/api/v1/logs/search?query=Test.*message&regex_enabled=true"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] >= 1

    def test_search_logs_case_sensitive(self):
        """Test search_logs with case_sensitive option."""
        response = self.client.get("/api/v1/logs/search?query=TEST&case_sensitive=true")
        assert response.status_code == 200
        data = response.json()
        # Should find no matches since all sample messages use "Test" not "TEST"
        assert data["total_count"] == 0

    def test_search_logs_pagination(self):
        """Test search_logs pagination with offset and limit."""
        # Add more log entries for pagination testing
        for i in range(10):
            entry = LogEntry(
                id=f"pagination_log_{i}",
                timestamp=datetime.now(),
                level=LogLevelEnum.INFO,
                logger="pagination.logger",
                message=f"Pagination message {i}",
            )
            log_storage.append(entry)

        # Test first page
        response = self.client.get("/api/v1/logs/search?limit=5&offset=0")
        assert response.status_code == 200
        data = response.json()
        assert len(data["entries"]) == 5
        assert data["has_more"] is True

        # Test second page
        response = self.client.get("/api/v1/logs/search?limit=5&offset=5")
        assert response.status_code == 200
        data = response.json()
        assert len(data["entries"]) == 5

    def test_export_logs_json_format(self):
        """Test log export in JSON format."""
        export_request = {
            "search": {
                "query": None,
                "limit": 1000,
                "offset": 0,
            },
            "format": "json",
            "include_metadata": True,
            "filename": "test_export.json",
        }

        response = self.client.post("/api/v1/logs/export", json=export_request)
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"
        assert "attachment" in response.headers["content-disposition"]

    def test_export_logs_csv_format(self):
        """Test log export in CSV format."""
        export_request = {
            "search": {"limit": 1000, "offset": 0},
            "format": "csv",
            "include_metadata": False,
        }

        response = self.client.post("/api/v1/logs/export", json=export_request)
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv; charset=utf-8"

    def test_export_logs_text_format(self):
        """Test log export in TEXT format."""
        export_request = {"search": {"limit": 1000, "offset": 0}, "format": "text"}

        response = self.client.post("/api/v1/logs/export", json=export_request)
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/plain; charset=utf-8"

    def test_export_logs_auto_filename(self):
        """Test log export with auto-generated filename."""
        export_request = {"search": {"limit": 1000, "offset": 0}, "format": "json"}

        response = self.client.post("/api/v1/logs/export", json=export_request)
        assert response.status_code == 200
        # Should have auto-generated filename in header
        assert "cc_orchestrator_logs_" in response.headers["content-disposition"]
        assert ".json" in response.headers["content-disposition"]

    @patch("src.cc_orchestrator.web.routers.v1.logs._filter_log_entries")
    def test_export_logs_exception(self, mock_filter):
        """Test export_logs with exception handling."""
        mock_filter.side_effect = RuntimeError("Export failed")

        export_request = {"search": {"limit": 1000, "offset": 0}, "format": "json"}
        response = self.client.post("/api/v1/logs/export", json=export_request)
        assert response.status_code == 500
        assert response.json()["detail"] == "Log export failed"

    @patch("src.cc_orchestrator.web.routers.v1.logs.connection_manager")
    def test_start_log_stream_exception(self, mock_connection_manager):
        """Test start_log_stream exception handling."""
        mock_connection_manager.broadcast_message.side_effect = RuntimeError(
            "Broadcast failed"
        )

        stream_filter = {"level": ["ERROR"], "buffer_size": 50}
        response = self.client.post("/api/v1/logs/stream/start", json=stream_filter)
        assert response.status_code == 500
        assert response.json()["detail"] == "Failed to start log stream"

    @patch("src.cc_orchestrator.web.routers.v1.logs.connection_manager")
    def test_stop_log_stream_success(self, mock_connection_manager):
        """Test successful log stream stop."""
        mock_connection_manager.broadcast_message = AsyncMock()

        # First start a stream
        stream_filter = {"level": ["ERROR"], "buffer_size": 50}
        start_response = self.client.post(
            "/api/v1/logs/stream/start", json=stream_filter
        )
        assert start_response.status_code == 200
        stream_id = start_response.json()["stream_id"]

        # Then stop it
        response = self.client.post(f"/api/v1/logs/stream/{stream_id}/stop")
        assert response.status_code == 200
        data = response.json()
        assert data["stream_id"] == stream_id
        assert data["status"] == "stopped"

    def test_stop_log_stream_not_found(self):
        """Test stop_log_stream with non-existent stream ID."""
        response = self.client.post("/api/v1/logs/stream/nonexistent_stream/stop")
        assert response.status_code == 404
        assert response.json()["detail"] == "Stream not found"

    @patch("src.cc_orchestrator.web.routers.v1.logs.connection_manager")
    def test_stop_log_stream_exception(self, mock_connection_manager):
        """Test stop_log_stream exception handling."""
        # Add a stream to buffer_usage to pass the initial check
        stream_stats["buffer_usage"]["test_stream"] = 100
        mock_connection_manager.broadcast_message.side_effect = RuntimeError(
            "Broadcast failed"
        )

        response = self.client.post("/api/v1/logs/stream/test_stream/stop")
        assert response.status_code == 500
        assert response.json()["detail"] == "Failed to stop log stream"

    def test_cleanup_logs_success(self):
        """Test successful log cleanup."""
        # Add old and recent log entries
        now = datetime.now()
        old_entry = LogEntry(
            id="old_cleanup",
            timestamp=now - timedelta(hours=48),  # Older than 24 hours
            level=LogLevelEnum.INFO,
            logger="cleanup.logger",
            message="Old entry to be cleaned",
        )
        recent_entry = LogEntry(
            id="recent_cleanup",
            timestamp=now - timedelta(hours=1),  # Recent entry
            level=LogLevelEnum.INFO,
            logger="cleanup.logger",
            message="Recent entry to keep",
        )
        log_storage.extend([old_entry, recent_entry])
        initial_count = len(log_storage)

        response = self.client.delete("/api/v1/logs/cleanup?older_than_hours=24")
        assert response.status_code == 200

        data = response.json()
        assert "deleted_count" in data
        assert "remaining_count" in data
        assert data["deleted_count"] >= 1  # Should delete at least the old entry
        assert data["remaining_count"] < initial_count

    def test_cleanup_logs_custom_hours(self):
        """Test log cleanup with custom hours parameter."""
        response = self.client.delete("/api/v1/logs/cleanup?older_than_hours=48")
        assert response.status_code == 200

    @patch(
        "src.cc_orchestrator.web.routers.v1.logs.log_storage",
        new_callable=lambda: MagicMock(),
    )
    def test_cleanup_logs_exception(self, mock_storage):
        """Test cleanup_logs exception handling."""
        mock_storage.__len__.side_effect = RuntimeError("Storage error")

        response = self.client.delete("/api/v1/logs/cleanup")
        assert response.status_code == 500
        assert response.json()["detail"] == "Log cleanup failed"

    def test_filter_log_entries_time_range(self):
        """Test _filter_log_entries with time range filters."""
        now = datetime.now()
        entries = [
            LogEntry(
                id="entry1",
                timestamp=now - timedelta(hours=2),
                level=LogLevelEnum.INFO,
                logger="test",
                message="Old entry",
            ),
            LogEntry(
                id="entry2",
                timestamp=now,
                level=LogLevelEnum.INFO,
                logger="test",
                message="New entry",
            ),
        ]

        search_request = LogSearchRequest(
            start_time=now - timedelta(hours=1),
            end_time=now + timedelta(hours=1),
        )

        filtered = _filter_log_entries(entries, search_request)
        assert len(filtered) == 1
        assert filtered[0].id == "entry2"

    def test_filter_log_entries_levels(self):
        """Test _filter_log_entries with level filters."""
        entries = [
            LogEntry(
                id="1",
                timestamp=datetime.now(),
                level=LogLevelEnum.INFO,
                logger="test",
                message="Info",
            ),
            LogEntry(
                id="2",
                timestamp=datetime.now(),
                level=LogLevelEnum.ERROR,
                logger="test",
                message="Error",
            ),
            LogEntry(
                id="3",
                timestamp=datetime.now(),
                level=LogLevelEnum.DEBUG,
                logger="test",
                message="Debug",
            ),
        ]

        search_request = LogSearchRequest(level=[LogLevelEnum.INFO, LogLevelEnum.ERROR])
        filtered = _filter_log_entries(entries, search_request)
        assert len(filtered) == 2
        assert all(
            entry.level in [LogLevelEnum.INFO, LogLevelEnum.ERROR] for entry in filtered
        )

    def test_filter_log_entries_contexts(self):
        """Test _filter_log_entries with context filters."""
        entries = [
            LogEntry(
                id="1",
                timestamp=datetime.now(),
                level=LogLevelEnum.INFO,
                logger="test",
                message="System",
                context=LogEntryType.SYSTEM,
            ),
            LogEntry(
                id="2",
                timestamp=datetime.now(),
                level=LogLevelEnum.INFO,
                logger="test",
                message="Web",
                context=LogEntryType.WEB,
            ),
            LogEntry(
                id="3",
                timestamp=datetime.now(),
                level=LogLevelEnum.INFO,
                logger="test",
                message="No context",
                context=None,
            ),
        ]

        search_request = LogSearchRequest(context=[LogEntryType.SYSTEM])
        filtered = _filter_log_entries(entries, search_request)
        assert len(filtered) == 1
        assert filtered[0].context == LogEntryType.SYSTEM

    def test_filter_log_entries_instance_and_task_id(self):
        """Test _filter_log_entries with instance_id and task_id filters."""
        entries = [
            LogEntry(
                id="1",
                timestamp=datetime.now(),
                level=LogLevelEnum.INFO,
                logger="test",
                message="Entry 1",
                instance_id="inst1",
                task_id="task1",
            ),
            LogEntry(
                id="2",
                timestamp=datetime.now(),
                level=LogLevelEnum.INFO,
                logger="test",
                message="Entry 2",
                instance_id="inst2",
                task_id="task2",
            ),
        ]

        # Test instance_id filter
        search_request = LogSearchRequest(instance_id="inst1")
        filtered = _filter_log_entries(entries, search_request)
        assert len(filtered) == 1
        assert filtered[0].instance_id == "inst1"

        # Test task_id filter
        search_request = LogSearchRequest(task_id="task2")
        filtered = _filter_log_entries(entries, search_request)
        assert len(filtered) == 1
        assert filtered[0].task_id == "task2"

    def test_filter_by_query_regex_enabled(self):
        """Test _filter_by_query with regex enabled."""
        entries = [
            LogEntry(
                id="1",
                timestamp=datetime.now(),
                level=LogLevelEnum.INFO,
                logger="test",
                message="Test message 123",
            ),
            LogEntry(
                id="2",
                timestamp=datetime.now(),
                level=LogLevelEnum.INFO,
                logger="test",
                message="Another message",
            ),
        ]

        # Test valid regex
        search_request = LogSearchRequest(query=r"Test.*\d+", regex_enabled=True)
        filtered = _filter_by_query(entries, search_request)
        assert len(filtered) == 1
        assert filtered[0].message == "Test message 123"

    def test_filter_by_query_invalid_regex(self):
        """Test _filter_by_query with invalid regex fallback to literal search."""
        entries = [
            LogEntry(
                id="1",
                timestamp=datetime.now(),
                level=LogLevelEnum.INFO,
                logger="test",
                message="Test [invalid regex",
            ),
            LogEntry(
                id="2",
                timestamp=datetime.now(),
                level=LogLevelEnum.INFO,
                logger="test",
                message="Another message",
            ),
        ]

        # Test invalid regex - should fall back to literal search
        search_request = LogSearchRequest(query="[invalid", regex_enabled=True)
        filtered = _filter_by_query(entries, search_request)
        assert len(filtered) == 1
        assert "[invalid" in filtered[0].message

    def test_filter_by_query_case_sensitivity(self):
        """Test _filter_by_query case sensitivity."""
        entries = [
            LogEntry(
                id="1",
                timestamp=datetime.now(),
                level=LogLevelEnum.INFO,
                logger="test",
                message="TEST MESSAGE",
            ),
            LogEntry(
                id="2",
                timestamp=datetime.now(),
                level=LogLevelEnum.INFO,
                logger="test",
                message="test message",
            ),
        ]

        # Case sensitive search
        search_request = LogSearchRequest(query="TEST", case_sensitive=True)
        filtered = _filter_by_query(entries, search_request)
        assert len(filtered) == 1
        assert filtered[0].message == "TEST MESSAGE"

        # Case insensitive search
        search_request = LogSearchRequest(query="TEST", case_sensitive=False)
        filtered = _filter_by_query(entries, search_request)
        assert len(filtered) == 2

    def test_filter_by_query_searches_multiple_fields(self):
        """Test _filter_by_query searches in message, logger, module, and function."""
        entry = LogEntry(
            id="1",
            timestamp=datetime.now(),
            level=LogLevelEnum.INFO,
            logger="my_logger",
            message="Some message",
            module="my_module",
            function="my_function",
        )

        search_request = LogSearchRequest(query="my_logger")
        filtered = _filter_by_query([entry], search_request)
        assert len(filtered) == 1

        search_request = LogSearchRequest(query="my_module")
        filtered = _filter_by_query([entry], search_request)
        assert len(filtered) == 1

        search_request = LogSearchRequest(query="my_function")
        filtered = _filter_by_query([entry], search_request)
        assert len(filtered) == 1

    def test_filter_by_query_no_query(self):
        """Test _filter_by_query with no query returns all entries."""
        entries = [
            LogEntry(
                id="1",
                timestamp=datetime.now(),
                level=LogLevelEnum.INFO,
                logger="test",
                message="Message 1",
            ),
            LogEntry(
                id="2",
                timestamp=datetime.now(),
                level=LogLevelEnum.INFO,
                logger="test",
                message="Message 2",
            ),
        ]

        search_request = LogSearchRequest(query=None)
        filtered = _filter_by_query(entries, search_request)
        assert len(filtered) == 2

    @pytest.mark.asyncio
    async def test_generate_export_content_json(self):
        """Test _generate_export_content for JSON format."""
        entries = [
            LogEntry(
                id="1",
                timestamp=datetime.now(),
                level=LogLevelEnum.INFO,
                logger="test",
                message="Test message",
                metadata={"key": "value"},
            ),
        ]

        content_generator = _generate_export_content(
            entries, LogExportFormat.JSON, True
        )
        content = ""
        async for chunk in content_generator:
            content += chunk

        assert content.startswith("[\n")
        assert content.endswith("\n]")
        assert "Test message" in content
        assert "metadata" in content

    @pytest.mark.asyncio
    async def test_generate_export_content_json_no_metadata(self):
        """Test _generate_export_content for JSON format without metadata."""
        entries = [
            LogEntry(
                id="1",
                timestamp=datetime.now(),
                level=LogLevelEnum.INFO,
                logger="test",
                message="Test message",
                metadata={"key": "value"},
            ),
        ]

        content_generator = _generate_export_content(
            entries, LogExportFormat.JSON, False
        )
        content = ""
        async for chunk in content_generator:
            content += chunk

        assert "Test message" in content
        assert "metadata" not in content

    @pytest.mark.asyncio
    async def test_generate_export_content_csv(self):
        """Test _generate_export_content for CSV format."""
        entries = [
            LogEntry(
                id="1",
                timestamp=datetime.now(),
                level=LogLevelEnum.INFO,
                logger="test",
                message='Test message with "quotes"',
                metadata={"key": "value"},
            ),
        ]

        content_generator = _generate_export_content(entries, LogExportFormat.CSV, True)
        content = ""
        async for chunk in content_generator:
            content += chunk

        lines = content.strip().split("\n")
        assert len(lines) >= 2  # Header + at least 1 data row
        assert "id,timestamp,level" in lines[0]  # Header
        assert "metadata" in lines[0]  # metadata column included
        assert '"Test message with ""quotes"""' in content  # Quotes properly escaped

    @pytest.mark.asyncio
    async def test_generate_export_content_csv_no_metadata(self):
        """Test _generate_export_content for CSV format without metadata."""
        entries = [
            LogEntry(
                id="1",
                timestamp=datetime.now(),
                level=LogLevelEnum.INFO,
                logger="test",
                message="Test message",
            ),
        ]

        content_generator = _generate_export_content(
            entries, LogExportFormat.CSV, False
        )
        content = ""
        async for chunk in content_generator:
            content += chunk

        lines = content.strip().split("\n")
        assert "metadata" not in lines[0]  # metadata column not included

    @pytest.mark.asyncio
    async def test_generate_export_content_text(self):
        """Test _generate_export_content for TEXT format."""
        entries = [
            LogEntry(
                id="1",
                timestamp=datetime.now(),
                level=LogLevelEnum.INFO,
                logger="test",
                message="Test message",
                context=LogEntryType.SYSTEM,
                instance_id="inst1",
                task_id="task1",
            ),
        ]

        content_generator = _generate_export_content(
            entries, LogExportFormat.TEXT, True
        )
        content = ""
        async for chunk in content_generator:
            content += chunk

        assert "INFO test: Test message" in content
        assert "(context: system)" in content
        assert "(instance: inst1)" in content
        assert "(task: task1)" in content

    @pytest.mark.asyncio
    async def test_generate_export_content_empty_entries(self):
        """Test _generate_export_content with empty entries list."""
        content_generator = _generate_export_content([], LogExportFormat.JSON, True)
        content = ""
        async for chunk in content_generator:
            content += chunk

        assert content == "[\n\n]"

    def test_log_search_request_validation(self):
        """Test LogSearchRequest model validations."""
        # Test query length validation
        with pytest.raises(ValidationError) as exc_info:
            LogSearchRequest(query="x" * 1001)
        assert "Search query too long" in str(exc_info.value)

        # Test limit validation - too high
        with pytest.raises(ValidationError) as exc_info:
            LogSearchRequest(limit=20000)
        assert "Limit must be between 1 and 10000" in str(exc_info.value)

        # Test limit validation - too low
        with pytest.raises(ValidationError) as exc_info:
            LogSearchRequest(limit=0)
        assert "Limit must be between 1 and 10000" in str(exc_info.value)

    def test_log_stream_filter_validation(self):
        """Test LogStreamFilter model validations."""
        # Test buffer_size validation - too high
        with pytest.raises(ValidationError) as exc_info:
            LogStreamFilter(buffer_size=2000)
        assert "Buffer size must be between 10 and 1000" in str(exc_info.value)

        # Test buffer_size validation - too low
        with pytest.raises(ValidationError) as exc_info:
            LogStreamFilter(buffer_size=5)
        assert "Buffer size must be between 10 and 1000" in str(exc_info.value)

    def test_valid_log_search_request(self):
        """Test valid LogSearchRequest creation."""
        request = LogSearchRequest(
            query="test query",
            level=[LogLevelEnum.INFO, LogLevelEnum.ERROR],
            context=[LogEntryType.SYSTEM],
            limit=500,
        )
        assert request.query == "test query"
        assert len(request.level) == 2
        assert request.limit == 500

    def test_valid_log_stream_filter(self):
        """Test valid LogStreamFilter creation."""
        filter_obj = LogStreamFilter(
            level=[LogLevelEnum.ERROR], context=[LogEntryType.WEB], buffer_size=200
        )
        assert len(filter_obj.level) == 1
        assert filter_obj.buffer_size == 200
