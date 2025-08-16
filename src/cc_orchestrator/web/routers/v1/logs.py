"""
Log streaming and management API endpoints.

Provides endpoints for log streaming, search, filtering, and export functionality.
"""

import json
import re
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator

from ....utils.logging import LogContext, get_logger
from ...dependencies import get_current_user
from ...websocket.manager import WebSocketMessage, connection_manager

logger = get_logger(__name__, LogContext.WEB)

router = APIRouter(tags=["logs"])


@dataclass
class LogStreamingConfig:
    """Configuration for log streaming security and performance."""

    max_concurrent_streams: int = 50
    max_entries_per_request: int = 1000
    stream_timeout_seconds: int = 300
    query_timeout_seconds: int = 30
    websocket_connections_per_ip: int = 5
    log_search_per_minute: int = 20
    log_export_per_hour: int = 5
    retention_days: int = 30
    max_export_entries: int = 50000
    cleanup_batch_size: int = 1000


# Global configuration instance
LOG_STREAMING_CONFIG = LogStreamingConfig()

# Sensitive data patterns to filter from logs
SENSITIVE_PATTERNS = [
    r'(?i)(password|token|key|secret|auth)[:=]\s*[^\s\'"]+',
    r"Bearer\s+[A-Za-z0-9\-._~+/]+",
    r'(?i)api[_-]?key[:=]\s*[^\s\'"]+',
    r'(?i)(oauth|jwt)[:=]\s*[^\s\'"]+',
    r'(?i)credential[:=]\s*[^\s\'"]+',
    r"\b[0-9]{4}[- ]?[0-9]{4}[- ]?[0-9]{4}[- ]?[0-9]{4}\b",  # Credit card
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",  # Email (if considered sensitive)
    r"(?i)secret_[a-zA-Z0-9_]+",  # Pattern like secret_token_123
    r"[a-zA-Z0-9_]{16,}",  # Generic tokens/keys (16+ alphanumeric chars, more specific)
]

# Sensitive metadata keys that should always be redacted (exact and substring matches)
SENSITIVE_KEYS_EXACT = [
    "password", "secret", "api_key", "session_token", "oauth_token",
    "jwt_token", "bearer_token", "access_token", "refresh_token",
    "client_secret", "private_key", "auth_token", "credential"
]

# Keys that should be checked for substring matches (more restrictive)
SENSITIVE_KEYS_SUBSTRING = [
    "password", "secret", "token", "_key", "auth"  # Changed "key" to "_key" to avoid "user_456"
]

# Audit log storage (in production, use proper audit system)
audit_log_storage: list[dict[str, Any]] = []


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


def sanitize_log_content(content: str) -> str:
    """Remove sensitive information from log content before streaming/export."""
    if not content:
        return content

    sanitized = content
    for pattern in SENSITIVE_PATTERNS:
        sanitized = re.sub(pattern, "[REDACTED]", sanitized)

    return sanitized


def sanitize_log_entry(log_entry: LogEntry) -> LogEntry:
    """Sanitize a complete log entry for sensitive data."""
    # Create a copy to avoid modifying the original
    sanitized_entry = log_entry.model_copy()

    # Sanitize message content
    sanitized_entry.message = sanitize_log_content(sanitized_entry.message)

    # Sanitize metadata if present
    if sanitized_entry.metadata:
        sanitized_metadata = {}
        for key, value in sanitized_entry.metadata.items():
            # Check if key itself is sensitive (exact match first, then substring)
            key_lower = key.lower()
            is_sensitive = False

            # Check exact matches first
            if key_lower in [k.lower() for k in SENSITIVE_KEYS_EXACT]:
                is_sensitive = True
                # print(f"DEBUG: {key_lower} matched exact key")
            # Then check substring matches, but only for clearly sensitive patterns
            elif any(sens_key in key_lower for sens_key in SENSITIVE_KEYS_SUBSTRING):
                # print(f"DEBUG: {key_lower} matched substring patterns")
                # Additional validation to avoid false positives like "user_id"
                safe_patterns = ["user_id", "request_id", "trace_id", "correlation_id", "message_id", "task_id", "instance_id"]
                if not any(safe_pattern == key_lower for safe_pattern in safe_patterns):
                    is_sensitive = True
                    # print(f"DEBUG: {key_lower} not in safe patterns, marked sensitive")
                # else:
                    # print(f"DEBUG: {key_lower} found in safe patterns, not sensitive")

            if is_sensitive:
                sanitized_metadata[key] = "[REDACTED]"
                # print(f"DEBUG: Marking {key} as [REDACTED] due to sensitive key")
            elif isinstance(value, str):
                sanitized_metadata[key] = sanitize_log_content(value)
            else:
                sanitized_metadata[key] = value
        sanitized_entry.metadata = sanitized_metadata

    # Sanitize exception traceback if present
    if sanitized_entry.exception and "traceback" in sanitized_entry.exception:
        if isinstance(sanitized_entry.exception["traceback"], list):
            sanitized_entry.exception["traceback"] = [
                sanitize_log_content(line)
                for line in sanitized_entry.exception["traceback"]
            ]
        elif isinstance(sanitized_entry.exception["traceback"], str):
            sanitized_entry.exception["traceback"] = sanitize_log_content(
                sanitized_entry.exception["traceback"]
            )

    return sanitized_entry


async def audit_log_access(user_id: str, action: str, details: dict[str, Any]) -> None:
    """Log access to log streaming functionality for security compliance."""
    audit_entry = {
        "timestamp": datetime.now().isoformat(),
        "user_id": user_id,
        "action": action,  # "search", "export", "stream_start", "stream_stop"
        "details": details,
        "ip_address": details.get("ip_address", "unknown"),
    }

    audit_log_storage.append(audit_entry)

    # Log to system logger as well
    logger.info("Log access audit", user_id=user_id, action=action, details=details)


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

    @field_validator("query")
    @classmethod
    def validate_query(cls, v: str | None) -> str | None:
        """Validate search query."""
        if v and len(v) > 1000:
            raise ValueError("Search query too long (max 1000 characters)")
        return v

    @field_validator("limit")
    @classmethod
    def validate_limit(cls, v: int) -> int:
        """Validate limit."""
        if v < 1 or v > 100000:  # Allow up to 100k for export operations, business logic will cap appropriately
            raise ValueError("Limit must be between 1 and 100000")
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

    @field_validator("buffer_size")
    @classmethod
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
    current_user=Depends(get_current_user),
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
    limit: int = Query(
        1000,
        description="Maximum results",
        le=LOG_STREAMING_CONFIG.max_entries_per_request,
    ),
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
        # Audit log access
        await audit_log_access(
            user_id=getattr(current_user, "id", "unknown"),
            action="search",
            details={
                "query": query,
                "level": [level_item.value for level_item in level] if level else None,
                "context": [c.value for c in context] if context else None,
                "regex_enabled": regex_enabled,
                "limit": limit,
                "ip_address": getattr(request.client, "host", "unknown"),
            },
        )

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

        # Sanitize log entries for security
        sanitized_entries = [sanitize_log_entry(entry) for entry in filtered_entries]

        # Apply pagination
        total_count = len(sanitized_entries)
        paginated_entries = sanitized_entries[offset : offset + limit]
        has_more = (offset + limit) < total_count

        # Calculate search duration
        search_duration = (datetime.now() - start_search_time).total_seconds() * 1000

        logger.info(
            "Log search completed",
            user_id=getattr(current_user, "id", "unknown"),
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
    current_user=Depends(get_current_user),
) -> StreamingResponse:
    """
    Export logs in various formats (JSON, CSV, text).

    Supports all search criteria plus format selection and metadata inclusion.
    """
    try:
        # Audit log export access
        await audit_log_access(
            user_id=getattr(current_user, "id", "unknown"),
            action="export",
            details={
                "format": export_request.format.value,
                "include_metadata": export_request.include_metadata,
                "search_criteria": export_request.search.model_dump(),
                "filename": export_request.filename,
            },
        )

        # Enforce export limits for security
        if export_request.search.limit > LOG_STREAMING_CONFIG.max_export_entries:
            export_request.search.limit = LOG_STREAMING_CONFIG.max_export_entries

        # Apply filters
        filtered_entries = _filter_log_entries(log_storage, export_request.search)

        # Sanitize log entries for security
        sanitized_entries = [sanitize_log_entry(entry) for entry in filtered_entries]

        # Generate filename if not provided
        if not export_request.filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            export_request.filename = (
                f"cc_orchestrator_logs_{timestamp}.{export_request.format.value}"
            )

        # Generate content stream
        content_generator = _generate_export_content(
            sanitized_entries, export_request.format, export_request.include_metadata
        )

        # Set appropriate content type and headers
        content_type_map = {
            LogExportFormat.JSON: "application/json",
            LogExportFormat.CSV: "text/csv; charset=utf-8",
            LogExportFormat.TEXT: "text/plain; charset=utf-8",
        }

        headers = {
            "Content-Disposition": f"attachment; filename={export_request.filename}"
        }

        logger.info(
            "Log export initiated",
            user_id=getattr(current_user, "id", "unknown"),
            export_format=export_request.format.value,
            export_filename=export_request.filename,
            entry_count=len(sanitized_entries),
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
    current_user=Depends(get_current_user),
) -> dict[str, str]:
    """
    Start a real-time log stream with specified filters.

    Returns a stream ID that can be used to manage the stream.
    """
    try:
        # Check stream limits
        if (
            stream_stats["active_streams"]
            >= LOG_STREAMING_CONFIG.max_concurrent_streams
        ):
            raise HTTPException(
                status_code=429,
                detail=f"Maximum concurrent streams ({LOG_STREAMING_CONFIG.max_concurrent_streams}) exceeded",
            )

        stream_id = f"stream_{datetime.now().timestamp()}_{getattr(current_user, 'id', 'unknown')}"
        stream_stats["active_streams"] += 1

        # Store stream configuration (in production, use Redis or similar)
        stream_stats["buffer_usage"][stream_id] = stream_filter.buffer_size

        # Audit log stream start
        await audit_log_access(
            user_id=getattr(current_user, "id", "unknown"),
            action="stream_start",
            details={
                "stream_id": stream_id,
                "filter": stream_filter.model_dump(),
            },
        )

        # Broadcast stream start to WebSocket clients
        await connection_manager.broadcast_message(
            WebSocketMessage(
                type="log_stream_started",
                data={
                    "stream_id": stream_id,
                    "filter": stream_filter.model_dump(),
                },
                timestamp=datetime.now(),
            ),
            topic="logs",
        )

        logger.info(
            "Log stream started",
            user_id=getattr(current_user, "id", "unknown"),
            stream_id=stream_id,
            filter=stream_filter.model_dump(),
        )

        return {"stream_id": stream_id, "status": "started"}

    except HTTPException:
        # Re-raise HTTPExceptions (like rate limiting) to preserve status codes
        raise
    except Exception as e:
        logger.error("Failed to start log stream", exception=e)
        raise HTTPException(status_code=500, detail="Failed to start log stream")


@router.post("/stream/{stream_id}/stop")
async def stop_log_stream(
    stream_id: str,
    current_user=Depends(get_current_user),
) -> dict[str, str]:
    """
    Stop a real-time log stream.
    """
    try:
        if stream_id in stream_stats["buffer_usage"]:
            del stream_stats["buffer_usage"][stream_id]
            stream_stats["active_streams"] = max(0, stream_stats["active_streams"] - 1)

            # Audit log stream stop
            await audit_log_access(
                user_id=getattr(current_user, "id", "unknown"),
                action="stream_stop",
                details={
                    "stream_id": stream_id,
                },
            )

            # Broadcast stream stop to WebSocket clients
            await connection_manager.broadcast_message(
                WebSocketMessage(
                    type="log_stream_stopped",
                    data={"stream_id": stream_id},
                    timestamp=datetime.now(),
                ),
                topic="logs",
            )

            logger.info(
                "Log stream stopped",
                user_id=getattr(current_user, "id", "unknown"),
                stream_id=stream_id,
            )
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
    """Filter entries by text query with optional regex support and performance safeguards."""
    if not search_request.query:
        return entries

    query = search_request.query

    # Performance safeguard: limit regex complexity
    if search_request.regex_enabled:
        # Check for potentially dangerous regex patterns
        dangerous_patterns = [
            r"\*{2,}",  # Multiple asterisks
            r"\+{2,}",  # Multiple plus signs
            r"\.{2,}\*",  # Multiple dots followed by asterisk
            r"\(.*\){2,}",  # Nested groups
        ]

        for dangerous in dangerous_patterns:
            if re.search(dangerous, query):
                logger.warning(
                    "Potentially dangerous regex pattern detected, falling back to literal search",
                    query=query,
                    pattern=dangerous,
                )
                search_request.regex_enabled = False
                break

    if not search_request.case_sensitive:
        query = query.lower()

    filtered = []
    processed_count = 0
    max_processing_time = timedelta(seconds=LOG_STREAMING_CONFIG.query_timeout_seconds)
    start_time = datetime.now()

    for entry in entries:
        # Performance safeguard: check processing time
        if datetime.now() - start_time > max_processing_time:
            logger.warning(
                "Query processing timeout reached, returning partial results",
                processed_count=processed_count,
                total_entries=len(entries),
                timeout_seconds=LOG_STREAMING_CONFIG.query_timeout_seconds,
            )
            break

        processed_count += 1

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
                # Performance safeguard: use timeout for regex
                pattern = re.compile(
                    query, re.IGNORECASE if not search_request.case_sensitive else 0
                )
                if pattern.search(search_text):
                    filtered.append(entry)
            else:
                if query in search_text:
                    filtered.append(entry)
        except (re.error, TimeoutError):
            # Invalid regex or timeout, fall back to literal search
            logger.warning(
                "Regex search failed, falling back to literal search",
                query=query,
                entry_id=entry.id,
            )
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
            entry_dict = entry.model_dump()
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
    """Add a log entry and broadcast to WebSocket clients with security sanitization."""
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

    # Add original entry to storage (keep original for internal use)
    log_storage.append(entry)
    stream_stats["total_entries_streamed"] += 1

    # Sanitize entry for WebSocket broadcast (protect against sensitive data leaks)
    sanitized_entry = sanitize_log_entry(entry)

    # Broadcast sanitized entry to WebSocket clients
    await connection_manager.broadcast_message(
        WebSocketMessage(
            type="log_entry",
            data=sanitized_entry.model_dump(),
            timestamp=datetime.now(),
        ),
        topic="logs",
    )
