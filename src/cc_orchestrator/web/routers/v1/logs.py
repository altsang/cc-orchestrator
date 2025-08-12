"""
Log streaming and management API endpoints.

Provides endpoints for log streaming, search, filtering, and export functionality.
"""

import json
import re
from collections.abc import AsyncGenerator
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, validator

from ....utils.logging import LogContext, get_logger
from ...websocket.manager import WebSocketMessage, connection_manager

logger = get_logger(__name__, LogContext.WEB)

router = APIRouter(tags=["logs"])


class LogLevelEnum(str, Enum):
    """Log level enumeration."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogEntryType(str, Enum):
    """Log entry type enumeration."""

    SYSTEM = "system"
    INSTANCE = "instance"
    TASK = "task"
    WORKTREE = "worktree"
    WEB = "web"
    CLI = "cli"
    TMUX = "tmux"
    INTEGRATION = "integration"
    DATABASE = "database"
    PROCESS = "process"


class LogExportFormat(str, Enum):
    """Log export format enumeration."""

    JSON = "json"
    CSV = "csv"
    TEXT = "text"


class LogEntry(BaseModel):
    """Log entry model."""

    id: str = Field(..., description="Unique log entry ID")
    timestamp: datetime = Field(..., description="Log entry timestamp")
    level: LogLevelEnum = Field(..., description="Log level")
    logger: str = Field(..., description="Logger name")
    message: str = Field(..., description="Log message")
    module: str | None = Field(None, description="Source module")
    function: str | None = Field(None, description="Source function")
    line: int | None = Field(None, description="Source line number")
    context: LogEntryType | None = Field(None, description="Log context")
    instance_id: str | None = Field(None, description="Related instance ID")
    task_id: str | None = Field(None, description="Related task ID")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )
    exception: dict[str, Any] | None = Field(None, description="Exception information")


class LogSearchRequest(BaseModel):
    """Log search request model."""

    query: str | None = Field(None, description="Search query (supports regex)")
    level: list[LogLevelEnum] | None = Field(None, description="Filter by log levels")
    context: list[LogEntryType] | None = Field(
        None, description="Filter by context types"
    )
    instance_id: str | None = Field(None, description="Filter by instance ID")
    task_id: str | None = Field(None, description="Filter by task ID")
    start_time: datetime | None = Field(None, description="Start time for filtering")
    end_time: datetime | None = Field(None, description="End time for filtering")
    regex_enabled: bool = Field(False, description="Enable regex search")
    case_sensitive: bool = Field(False, description="Case sensitive search")
    limit: int = Field(1000, description="Maximum results to return")
    offset: int = Field(0, description="Results offset for pagination")

    @validator("query")
    def validate_query(cls, v: str | None) -> str | None:
        """Validate search query."""
        if v and len(v) > 1000:
            raise ValueError("Search query too long (max 1000 characters)")
        return v

    @validator("limit")
    def validate_limit(cls, v: int) -> int:
        """Validate limit."""
        if v < 1 or v > 10000:
            raise ValueError("Limit must be between 1 and 10000")
        return v


class LogExportRequest(BaseModel):
    """Log export request model."""

    search: LogSearchRequest = Field(
        default=LogSearchRequest(
            query=None,
            level=None,
            context=None,
            instance_id=None,
            task_id=None,
            start_time=None,
            end_time=None,
            regex_enabled=False,
            case_sensitive=False,
            limit=1000,
            offset=0,
        ),
        description="Search criteria",
    )
    format: LogExportFormat = Field(LogExportFormat.JSON, description="Export format")
    include_metadata: bool = Field(True, description="Include metadata in export")
    filename: str | None = Field(None, description="Custom filename for export")


class LogStreamFilter(BaseModel):
    """Log stream filter model."""

    level: list[LogLevelEnum] | None = Field(None, description="Filter by log levels")
    context: list[LogEntryType] | None = Field(
        None, description="Filter by context types"
    )
    instance_id: str | None = Field(None, description="Filter by instance ID")
    task_id: str | None = Field(None, description="Filter by task ID")
    buffer_size: int = Field(100, description="Client buffer size")

    @validator("buffer_size")
    def validate_buffer_size(cls, v: int) -> int:
        """Validate buffer size."""
        if v < 10 or v > 1000:
            raise ValueError("Buffer size must be between 10 and 1000")
        return v


class LogSearchResponse(BaseModel):
    """Log search response model."""

    entries: list[LogEntry] = Field(..., description="Log entries")
    total_count: int = Field(..., description="Total matching entries")
    has_more: bool = Field(..., description="Whether more results are available")
    search_duration_ms: int = Field(
        ..., description="Search execution time in milliseconds"
    )


class LogStreamStats(BaseModel):
    """Log stream statistics model."""

    active_streams: int = Field(..., description="Number of active streams")
    total_entries_streamed: int = Field(..., description="Total entries streamed")
    stream_start_time: datetime = Field(..., description="Stream start time")
    buffer_usage: dict[str, int] = Field(
        default_factory=dict, description="Buffer usage stats"
    )


# Global log storage (in production, this would be a database or log storage system)
log_storage: list[LogEntry] = []
stream_stats: dict[str, Any] = {
    "active_streams": 0,
    "total_entries_streamed": 0,
    "stream_start_time": datetime.now(),
    "buffer_usage": {},
}


@router.get("/search", response_model=LogSearchResponse)
async def search_logs(
    request: Request,
    query: str | None = Query(None, description="Search query"),
    level: list[LogLevelEnum] | None = Query(None, description="Filter by log levels"),
    context: list[LogEntryType] | None = Query(
        None, description="Filter by context types"
    ),
    instance_id: str | None = Query(None, description="Filter by instance ID"),
    task_id: str | None = Query(None, description="Filter by task ID"),
    start_time: datetime | None = Query(None, description="Start time filter"),
    end_time: datetime | None = Query(None, description="End time filter"),
    regex_enabled: bool = Query(False, description="Enable regex search"),
    case_sensitive: bool = Query(False, description="Case sensitive search"),
    limit: int = Query(1000, description="Maximum results"),
    offset: int = Query(0, description="Results offset"),
) -> LogSearchResponse:
    """
    Search and filter log entries with advanced criteria.

    Supports:
    - Text search with optional regex
    - Multi-level filtering
    - Context-based filtering
    - Time range filtering
    - Pagination
    """
    start_search_time = datetime.now()

    try:
        # Build search criteria
        search_request = LogSearchRequest(
            query=query,
            level=level,
            context=context,
            instance_id=instance_id,
            task_id=task_id,
            start_time=start_time,
            end_time=end_time,
            regex_enabled=regex_enabled,
            case_sensitive=case_sensitive,
            limit=limit,
            offset=offset,
        )

        # Apply filters
        filtered_entries = _filter_log_entries(log_storage, search_request)

        # Apply pagination
        total_count = len(filtered_entries)
        paginated_entries = filtered_entries[offset : offset + limit]
        has_more = (offset + limit) < total_count

        # Calculate search duration
        search_duration = (datetime.now() - start_search_time).total_seconds() * 1000

        logger.info(
            "Log search completed",
            query=query,
            total_results=total_count,
            returned_results=len(paginated_entries),
            search_duration_ms=int(search_duration),
        )

        return LogSearchResponse(
            entries=paginated_entries,
            total_count=total_count,
            has_more=has_more,
            search_duration_ms=int(search_duration),
        )

    except ValueError as e:
        logger.error("Invalid search parameters", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Log search failed", exception=e)
        raise HTTPException(status_code=500, detail="Log search failed")


@router.post("/export")
async def export_logs(
    export_request: LogExportRequest,
) -> StreamingResponse:
    """
    Export logs in various formats (JSON, CSV, text).

    Supports all search criteria plus format selection and metadata inclusion.
    """
    try:
        # Apply filters
        filtered_entries = _filter_log_entries(log_storage, export_request.search)

        # Generate filename if not provided
        if not export_request.filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            export_request.filename = (
                f"cc_orchestrator_logs_{timestamp}.{export_request.format.value}"
            )

        # Generate content stream
        content_generator = _generate_export_content(
            filtered_entries, export_request.format, export_request.include_metadata
        )

        # Set appropriate content type and headers
        content_type_map = {
            LogExportFormat.JSON: "application/json",
            LogExportFormat.CSV: "text/csv",
            LogExportFormat.TEXT: "text/plain",
        }

        headers = {
            "Content-Disposition": f"attachment; filename={export_request.filename}"
        }

        logger.info(
            "Log export initiated",
            export_format=export_request.format.value,
            export_filename=export_request.filename,
            entry_count=len(filtered_entries),
        )

        return StreamingResponse(
            content_generator,
            media_type=content_type_map[export_request.format],
            headers=headers,
        )

    except Exception as e:
        logger.error("Log export failed", exception=e)
        raise HTTPException(status_code=500, detail="Log export failed")


@router.get("/levels", response_model=list[str])
async def get_log_levels() -> list[str]:
    """Get available log levels."""
    return [level.value for level in LogLevelEnum]


@router.get("/contexts", response_model=list[str])
async def get_log_contexts() -> list[str]:
    """Get available log context types."""
    return [context.value for context in LogEntryType]


@router.get("/stats", response_model=LogStreamStats)
async def get_log_stats() -> LogStreamStats:
    """Get log streaming statistics."""
    return LogStreamStats(
        active_streams=stream_stats["active_streams"],
        total_entries_streamed=stream_stats["total_entries_streamed"],
        stream_start_time=stream_stats["stream_start_time"],
        buffer_usage=stream_stats["buffer_usage"],
    )


@router.post("/stream/start")
async def start_log_stream(
    stream_filter: LogStreamFilter,
) -> dict[str, str]:
    """
    Start a real-time log stream with specified filters.

    Returns a stream ID that can be used to manage the stream.
    """
    try:
        stream_id = f"stream_{datetime.now().timestamp()}"
        stream_stats["active_streams"] += 1

        # Store stream configuration (in production, use Redis or similar)
        stream_stats["buffer_usage"][stream_id] = stream_filter.buffer_size

        # Broadcast stream start to WebSocket clients
        await connection_manager.broadcast_message(
            WebSocketMessage(
                type="log_stream_started",
                data={
                    "stream_id": stream_id,
                    "filter": stream_filter.dict(),
                },
                timestamp=datetime.now(),
            ),
            topic="logs",
        )

        logger.info(
            "Log stream started", stream_id=stream_id, filter=stream_filter.dict()
        )

        return {"stream_id": stream_id, "status": "started"}

    except Exception as e:
        logger.error("Failed to start log stream", exception=e)
        raise HTTPException(status_code=500, detail="Failed to start log stream")


@router.post("/stream/{stream_id}/stop")
async def stop_log_stream(
    stream_id: str,
) -> dict[str, str]:
    """
    Stop a real-time log stream.
    """
    try:
        if stream_id in stream_stats["buffer_usage"]:
            del stream_stats["buffer_usage"][stream_id]
            stream_stats["active_streams"] = max(0, stream_stats["active_streams"] - 1)

            # Broadcast stream stop to WebSocket clients
            await connection_manager.broadcast_message(
                WebSocketMessage(
                    type="log_stream_stopped",
                    data={"stream_id": stream_id},
                    timestamp=datetime.now(),
                ),
                topic="logs",
            )

            logger.info("Log stream stopped", stream_id=stream_id)
            return {"stream_id": stream_id, "status": "stopped"}
        else:
            raise HTTPException(status_code=404, detail="Stream not found")

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to stop log stream", exception=e)
        raise HTTPException(status_code=500, detail="Failed to stop log stream")


@router.delete("/cleanup")
async def cleanup_logs(
    older_than_hours: int = Query(
        24, description="Delete logs older than specified hours"
    ),
) -> dict[str, int]:
    """
    Clean up old log entries to manage storage.
    """
    global log_storage
    try:
        cutoff_time = datetime.now() - timedelta(hours=older_than_hours)
        initial_count = len(log_storage)

        # Remove old entries
        log_storage = [entry for entry in log_storage if entry.timestamp > cutoff_time]

        deleted_count = initial_count - len(log_storage)

        logger.info(
            "Log cleanup completed",
            deleted_count=deleted_count,
            remaining_count=len(log_storage),
            cutoff_hours=older_than_hours,
        )

        return {
            "deleted_count": deleted_count,
            "remaining_count": len(log_storage),
        }

    except Exception as e:
        logger.error("Log cleanup failed", exception=e)
        raise HTTPException(status_code=500, detail="Log cleanup failed")


def _filter_log_entries(
    entries: list[LogEntry], search_request: LogSearchRequest
) -> list[LogEntry]:
    """Filter log entries based on search criteria."""
    filtered = entries

    # Filter by time range
    if search_request.start_time:
        filtered = [e for e in filtered if e.timestamp >= search_request.start_time]
    if search_request.end_time:
        filtered = [e for e in filtered if e.timestamp <= search_request.end_time]

    # Filter by log levels
    if search_request.level:
        level_values = [level.value for level in search_request.level]
        filtered = [e for e in filtered if e.level.value in level_values]

    # Filter by context types
    if search_request.context:
        context_values = [ctx.value for ctx in search_request.context]
        filtered = [
            e for e in filtered if e.context and e.context.value in context_values
        ]

    # Filter by instance ID
    if search_request.instance_id:
        filtered = [e for e in filtered if e.instance_id == search_request.instance_id]

    # Filter by task ID
    if search_request.task_id:
        filtered = [e for e in filtered if e.task_id == search_request.task_id]

    # Filter by query
    if search_request.query:
        filtered = _filter_by_query(filtered, search_request)

    # Sort by timestamp (newest first)
    filtered.sort(key=lambda x: x.timestamp, reverse=True)

    return filtered


def _filter_by_query(
    entries: list[LogEntry], search_request: LogSearchRequest
) -> list[LogEntry]:
    """Filter entries by text query with optional regex support."""
    if not search_request.query:
        return entries

    query = search_request.query
    if not search_request.case_sensitive:
        query = query.lower()

    filtered = []

    for entry in entries:
        # Search in message and logger name
        search_text = f"{entry.message} {entry.logger}"
        if entry.module:
            search_text += f" {entry.module}"
        if entry.function:
            search_text += f" {entry.function}"

        if not search_request.case_sensitive:
            search_text = search_text.lower()

        try:
            if search_request.regex_enabled:
                pattern = re.compile(
                    query, re.IGNORECASE if not search_request.case_sensitive else 0
                )
                if pattern.search(search_text):
                    filtered.append(entry)
            else:
                if query in search_text:
                    filtered.append(entry)
        except re.error:
            # Invalid regex, fall back to literal search
            if query in search_text:
                filtered.append(entry)

    return filtered


async def _generate_export_content(
    entries: list[LogEntry], export_format: LogExportFormat, include_metadata: bool
) -> AsyncGenerator[str, None]:
    """Generate export content in specified format."""
    if export_format == LogExportFormat.JSON:
        yield "[\n"
        for i, entry in enumerate(entries):
            if i > 0:
                yield ",\n"
            entry_dict = entry.dict()
            if not include_metadata:
                entry_dict.pop("metadata", None)
            yield json.dumps(entry_dict, default=str, indent=2)
        yield "\n]"

    elif export_format == LogExportFormat.CSV:
        # CSV header
        headers = [
            "id",
            "timestamp",
            "level",
            "logger",
            "message",
            "module",
            "function",
            "line",
            "context",
            "instance_id",
            "task_id",
        ]
        if include_metadata:
            headers.append("metadata")
        yield ",".join(headers) + "\n"

        # CSV data
        for entry in entries:
            row = [
                entry.id,
                entry.timestamp.isoformat(),
                entry.level.value,
                entry.logger,
                '"' + entry.message.replace('"', '""') + '"',  # Escape quotes
                entry.module or "",
                entry.function or "",
                str(entry.line) if entry.line else "",
                entry.context.value if entry.context else "",
                entry.instance_id or "",
                entry.task_id or "",
            ]
            if include_metadata:
                metadata_str = json.dumps(entry.metadata) if entry.metadata else ""
                row.append('"' + metadata_str.replace('"', '""') + '"')
            yield ",".join(row) + "\n"

    elif export_format == LogExportFormat.TEXT:
        for entry in entries:
            line = f"[{entry.timestamp.isoformat()}] {entry.level.value} {entry.logger}: {entry.message}"
            if entry.context:
                line += f" (context: {entry.context.value})"
            if entry.instance_id:
                line += f" (instance: {entry.instance_id})"
            if entry.task_id:
                line += f" (task: {entry.task_id})"
            yield line + "\n"


async def add_log_entry(
    level: LogLevelEnum,
    logger_name: str,
    message: str,
    context: LogEntryType | None = None,
    instance_id: str | None = None,
    task_id: str | None = None,
    metadata: dict[str, Any] | None = None,
    exception: dict[str, Any] | None = None,
) -> None:
    """Add a log entry and broadcast to WebSocket clients."""
    entry = LogEntry(
        id=f"log_{datetime.now().timestamp()}_{len(log_storage)}",
        timestamp=datetime.now(),
        level=level,
        logger=logger_name,
        message=message,
        module=None,
        function=None,
        line=None,
        context=context,
        instance_id=instance_id,
        task_id=task_id,
        metadata=metadata or {},
        exception=exception,
    )

    # Add to storage
    log_storage.append(entry)
    stream_stats["total_entries_streamed"] += 1

    # Broadcast to WebSocket clients
    await connection_manager.broadcast_message(
        WebSocketMessage(
            type="log_entry",
            data=entry.dict(),
            timestamp=datetime.now(),
        ),
        topic="logs",
    )
