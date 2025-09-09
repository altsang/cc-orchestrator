# CC-Orchestrator Logging and Error Handling System

## Overview

This comprehensive logging and error handling framework provides structured logging, contextual information, custom exception handling, and audit trails for the CC-Orchestrator system.

## Features

### ✅ Structured JSON Logging
- **Timestamp**: ISO 8601 formatted timestamps
- **Context**: Component-specific context (orchestrator, instance, task, etc.)
- **Instance/Task IDs**: Automatic correlation of logs with specific instances and tasks
- **Exception Details**: Full exception tracking with stack traces

### ✅ Custom Exception Classes
- `InstanceError`: Claude instance management errors
- `WorktreeError`: Git worktree operation errors
- `TaskError`: Task management and coordination errors
- `ConfigurationError`: Configuration and setup errors
- `IntegrationError`: External integration errors (GitHub, Jira)
- `DatabaseError`: Database operation errors
- `TmuxError`: Tmux session management errors

### ✅ Error Handling Framework
- **Automatic Recovery**: Configurable recovery strategies for different error types
- **Context Preservation**: Error context captured and logged
- **Graceful Degradation**: Continue operation when possible
- **Audit Trail**: Complete tracking of error occurrences and recovery attempts

### ✅ Performance Monitoring
- **Execution Time Tracking**: Automatic timing of operations
- **Resource Usage Logging**: CPU, memory, and disk usage monitoring
- **Performance Metrics**: Function-level performance analysis

### ✅ Component-Specific Utilities
- **Core Operations**: Instance lifecycle, task coordination, database operations
- **Tmux Integration**: Session management, layout configuration, cleanup
- **Web Interface**: API requests/responses, WebSocket connections, authentication
- **External Integrations**: GitHub/Jira API calls, webhook processing, rate limiting

## Usage Examples

### Basic Setup

```python
from cc_orchestrator.utils.logging import setup_logging, LogLevel
from pathlib import Path

# Setup logging with both console and file output
setup_logging(
    log_level=LogLevel.INFO,
    log_file=Path("logs/cc-orchestrator.log"),
    enable_structured=True,
    enable_console=True
)
```

### Contextual Logging

```python
from cc_orchestrator.utils.logging import get_logger, LogContext

# Create a logger with specific context
logger = get_logger(__name__, LogContext.INSTANCE)
logger.set_instance_id("claude-001")
logger.set_task_id("TASK-123")

# Log with automatic context injection
logger.info("Starting task execution",
            task_title="Implement feature X",
            priority="high")
```

### Error Handling with Recovery

```python
from cc_orchestrator.utils.logging import handle_errors, InstanceError

def recovery_strategy(error, *args, **kwargs):
    """Restart instance on failure."""
    return restart_instance(args[0])

@handle_errors(recovery_strategy=recovery_strategy)
def start_instance(instance_id: str):
    # Instance startup logic that might fail
    if not check_port_available():
        raise InstanceError("Port already in use",
                          context={"instance_id": instance_id})
```

### Performance Tracking

```python
from cc_orchestrator.utils.logging import log_performance, LogContext

@log_performance(LogContext.TASK)
def process_large_task(task_data):
    # Heavy processing work
    return processed_result
```

### Component-Specific Logging

```python
from cc_orchestrator.core.logging_utils import (
    log_instance_lifecycle,
    log_task_assignment,
    log_resource_usage
)

# Instance operations
log_instance_lifecycle("claude-001", "create", "success",
                      {"worktree": "/tmp/worktree-001"})

# Task operations
task_details = {"title": "Fix bug", "priority": "high", "source": "github"}
log_task_assignment("TASK-456", "claude-001", task_details)

# Resource monitoring
log_resource_usage("claude-001", cpu_percent=45.2,
                  memory_mb=256.7, disk_usage_mb=1024.0)
```

## Log Output Format

### Structured JSON Format
```json
{
  "timestamp": "2025-07-27T07:49:00.117127",
  "level": "INFO",
  "logger": "cc_orchestrator.core.instance_manager",
  "message": "Instance started successfully",
  "module": "instance_manager",
  "function": "start_instance",
  "line": 45,
  "context": "instance",
  "instance_id": "claude-001",
  "task_id": "TASK-123"
}
```

### Error Logging with Exception Details
```json
{
  "timestamp": "2025-07-27T07:49:00.118000",
  "level": "ERROR",
  "logger": "cc_orchestrator.core.instance_manager",
  "message": "Instance startup failed",
  "context": "instance",
  "instance_id": "claude-001",
  "exception": {
    "type": "InstanceError",
    "message": "Port already in use",
    "traceback": ["Traceback (most recent call last):", "..."]
  }
}
```

## Integration with Components

### Core Orchestrator
- Instance lifecycle management
- Task coordination and assignment
- Database operations and queries
- Resource usage monitoring

### Tmux Sessions
- Session creation and cleanup
- Layout management
- Orphaned session detection
- Multi-user session handling

### Web Interface
- API request/response logging
- WebSocket connection management
- Authentication and authorization
- Real-time event broadcasting

### External Integrations
- GitHub/Jira API operations
- Webhook processing
- Rate limit monitoring
- Service status tracking

## Configuration Options

### Log Levels
- `DEBUG`: Detailed debugging information
- `INFO`: General operational information
- `WARNING`: Warning conditions
- `ERROR`: Error conditions
- `CRITICAL`: Critical error conditions

### Output Destinations
- **Console**: Real-time output to stdout
- **File**: Persistent logging to file system
- **Structured**: JSON format for log aggregation
- **Human-readable**: Traditional text format

### Context Categories
- `ORCHESTRATOR`: Main orchestration logic
- `INSTANCE`: Claude instance operations
- `TASK`: Task management and coordination
- `WORKTREE`: Git worktree operations
- `WEB`: Web interface operations
- `CLI`: Command-line interface
- `TMUX`: Session management
- `INTEGRATION`: External service integrations
- `DATABASE`: Database operations
- `PROCESS`: Process management

## Testing

Run the logging system test:

```bash
python examples/logging_usage.py
```

This will demonstrate all logging features and create sample log files showing:
- Structured JSON output
- Contextual logging with instance/task IDs
- Error handling with recovery
- Performance tracking
- Audit logging
- Component-specific operations

## Files Structure

```
src/cc_orchestrator/utils/
├── logging.py              # Core logging framework
├── README.md              # This documentation

src/cc_orchestrator/*/
├── logging_utils.py       # Component-specific utilities

examples/
├── logging_usage.py       # Comprehensive demo
└── logs/                  # Generated log files
```

## Next Steps

This logging system is ready for integration with:
1. **CLI Framework** - Add command-level logging
2. **Web Interface** - API and WebSocket logging
3. **Instance Management** - Detailed lifecycle tracking
4. **Task Coordination** - Assignment and status logging
5. **External Integrations** - GitHub/Jira API logging

The system provides the foundation for comprehensive monitoring, debugging, and audit trails across the entire CC-Orchestrator platform.
