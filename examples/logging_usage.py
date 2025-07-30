#!/usr/bin/env python3
"""
Example usage of the CC-Orchestrator logging and error handling system.

This file demonstrates:
- Basic logging setup and configuration
- Using contextual loggers
- Error handling with recovery strategies
- Performance tracking
- Audit logging
- Structured logging output
"""

import random
import sys
import time
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cc_orchestrator.core.logging_utils import (
    log_instance_lifecycle,
    log_orchestrator_shutdown,
    log_orchestrator_start,
    log_resource_usage,
    log_task_assignment,
    log_task_status_change,
    track_performance,
)
from cc_orchestrator.utils.logging import (
    ConfigurationError,
    InstanceError,
    LogContext,
    LogLevel,
    TaskError,
    audit_log,
    get_logger,
    handle_errors,
    log_performance,
    setup_logging,
)


def main():
    """Demonstrate the logging system functionality."""

    # Setup logging with both console and file output
    log_file = Path("logs/cc-orchestrator.log")
    setup_logging(
        log_level=LogLevel.DEBUG,
        log_file=log_file,
        enable_structured=True,
        enable_console=True,
    )

    print("🔍 CC-Orchestrator Logging System Demo")
    print("=" * 50)

    # Demonstrate basic logging
    demonstrate_basic_logging()

    # Demonstrate contextual logging
    demonstrate_contextual_logging()

    # Demonstrate error handling
    demonstrate_error_handling()

    # Demonstrate performance tracking
    demonstrate_performance_tracking()

    # Demonstrate audit logging
    demonstrate_audit_logging()

    # Demonstrate orchestrator operations
    demonstrate_orchestrator_operations()

    print(f"\n📁 Logs written to: {log_file}")
    print("✅ Demo completed successfully!")


def demonstrate_basic_logging():
    """Show basic logging functionality."""
    print("\n1. Basic Logging:")

    logger = get_logger(__name__, LogContext.ORCHESTRATOR)

    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    logger.critical("This is a critical message")


def demonstrate_contextual_logging():
    """Show contextual logging with instance and task IDs."""
    print("\n2. Contextual Logging:")

    logger = get_logger(__name__, LogContext.INSTANCE)
    logger.set_instance_id("claude-demo-001")
    logger.set_task_id("TASK-123")

    logger.info(
        "Starting instance with task assignment",
        task_title="Demo Task",
        priority="high",
    )

    logger.debug("Instance health check passed", cpu_usage=45.2, memory_usage=128.5)


def demonstrate_error_handling():
    """Show error handling with recovery strategies."""
    print("\n3. Error Handling with Recovery:")

    def recovery_strategy(error, *args, **kwargs):
        """Example recovery strategy."""
        print(f"  🔄 Recovery attempted for: {error}")
        return "recovered_result"

    @handle_errors(recovery_strategy=recovery_strategy, reraise=False)
    def potentially_failing_function():
        """Function that might fail."""
        if random.choice([True, False]):
            raise InstanceError(
                "Simulated instance failure", context={"instance_id": "claude-demo-001"}
            )
        return "success"

    # Try the function multiple times to show both success and recovery
    for i in range(3):
        result = potentially_failing_function()
        print(f"  Attempt {i+1}: {result}")


def demonstrate_performance_tracking():
    """Show performance tracking decorators."""
    print("\n4. Performance Tracking:")

    @track_performance("demo_operation")
    def slow_operation():
        """Simulate a slow operation."""
        time.sleep(0.1)  # Simulate work
        return "operation_completed"

    @log_performance(LogContext.TASK)
    def quick_operation():
        """Simulate a quick operation."""
        time.sleep(0.01)  # Simulate work
        return "quick_result"

    slow_result = slow_operation()
    quick_result = quick_operation()
    print(f"  Results: {slow_result}, {quick_result}")


def demonstrate_audit_logging():
    """Show audit logging for important operations."""
    print("\n5. Audit Logging:")

    @audit_log("critical_system_change", LogContext.ORCHESTRATOR)
    def update_system_configuration(config_name: str, new_value: str):
        """Simulate a critical system change."""
        print(f"  Updating {config_name} to {new_value}")
        return f"Updated {config_name}"

    result = update_system_configuration("max_instances", "10")
    print(f"  Result: {result}")


def demonstrate_orchestrator_operations():
    """Show orchestrator-specific logging operations."""
    print("\n6. Orchestrator Operations:")

    # Simulate orchestrator startup
    config = {
        "max_instances": 5,
        "tmux_enabled": True,
        "web_enabled": True,
        "log_level": "INFO",
    }
    log_orchestrator_start(config)

    # Simulate instance lifecycle
    instance_id = "claude-demo-002"
    log_instance_lifecycle(
        instance_id, "create", "success", {"worktree": "/tmp/worktree-002"}
    )

    # Simulate task assignment
    task_details = {
        "title": "Implement feature X",
        "priority": "high",
        "source": "github",
    }
    log_task_assignment("TASK-456", instance_id, task_details)

    # Simulate task status change
    log_task_status_change("TASK-456", "pending", "in_progress", instance_id)

    # Simulate resource usage monitoring
    log_resource_usage(instance_id, 62.3, 256.7, 1024.0)

    # Simulate orchestrator shutdown
    log_orchestrator_shutdown(graceful=True)


def demonstrate_exception_types():
    """Show different exception types."""
    print("\n7. Custom Exception Types:")

    exceptions = [
        InstanceError(
            "Instance failed to start",
            context={"instance_id": "claude-001", "port": 8080},
        ),
        TaskError(
            "Task validation failed",
            context={"task_id": "TASK-789", "validation_errors": ["missing_title"]},
        ),
        ConfigurationError(
            "Invalid configuration file",
            context={"file_path": "/config/settings.yaml", "line": 15},
        ),
    ]

    logger = get_logger(__name__, LogContext.ORCHESTRATOR)

    for exc in exceptions:
        logger.error(
            f"Exception demo: {exc.message}",
            exception=exc,
            exception_type=type(exc).__name__,
            exception_context=exc.context,
        )


if __name__ == "__main__":
    # Create logs directory
    Path("logs").mkdir(exist_ok=True)

    # Run the demo
    main()

    # Also demonstrate exception types
    demonstrate_exception_types()
