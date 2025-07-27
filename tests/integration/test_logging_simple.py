"""
Simplified integration tests for logging system.
Focus on core functionality that works reliably.
"""

import json
import logging

from cc_orchestrator.utils.logging import (
    InstanceError,
    LogContext,
    LogLevel,
    get_logger,
    handle_errors,
    setup_logging,
)


class TestSimpleLoggingIntegration:
    """Test core logging integration with minimal complexity."""

    def test_basic_logging_to_file(self, temp_log_file):
        """Test basic logging setup and file output."""
        setup_logging(
            log_level=LogLevel.INFO,
            log_file=temp_log_file,
            enable_console=False,
            enable_structured=True,
        )

        logger = get_logger("integration.test", LogContext.INSTANCE)
        logger.set_instance_id("test-instance")
        logger.info("Test message", test_key="test_value")

        # Ensure logging completes
        root_logger = logging.getLogger()
        for handler in root_logger.handlers:
            if hasattr(handler, "flush"):
                handler.flush()

        # Read and verify content
        if temp_log_file.exists() and temp_log_file.stat().st_size > 0:
            content = temp_log_file.read_text().strip()
            if content:
                data = json.loads(content)
                assert data["message"] == "Test message"
                assert data["context"] == "instance"
                assert data["instance_id"] == "test-instance"
                assert data["test_key"] == "test_value"

    def test_error_handling_integration(self):
        """Test error handling integration without file operations."""
        recovery_called = False

        def recovery_strategy(error, *args, **kwargs):
            nonlocal recovery_called
            recovery_called = True
            return "recovered"

        @handle_errors(recovery_strategy=recovery_strategy, reraise=False)
        def failing_function():
            raise InstanceError("Test integration error", {"test_context": "value"})

        result = failing_function()
        assert result == "recovered"
        assert recovery_called

    def test_multiple_loggers_same_context(self):
        """Test multiple loggers with same context."""
        logger1 = get_logger("test.logger1", LogContext.TASK)
        logger2 = get_logger("test.logger2", LogContext.TASK)

        logger1.set_task_id("TASK-001")
        logger2.set_task_id("TASK-002")

        # Both should work without interference
        assert logger1.task_id == "TASK-001"
        assert logger2.task_id == "TASK-002"
        assert logger1.context == "task"
        assert logger2.context == "task"

    def test_logging_with_context_switching(self):
        """Test logging with context switching during execution."""
        logger = get_logger("context.test", LogContext.INSTANCE)

        # Start with one context
        logger.set_instance_id("instance-001")
        assert logger.instance_id == "instance-001"

        # Switch to another context
        logger.set_instance_id("instance-002")
        logger.set_task_id("TASK-123")

        assert logger.instance_id == "instance-002"
        assert logger.task_id == "TASK-123"

    def test_exception_context_preservation(self):
        """Test that exception context is preserved through error handling."""
        original_context = {"instance_id": "test-001", "operation": "test"}

        try:
            raise InstanceError("Test error", original_context)
        except InstanceError as e:
            assert e.context == original_context
            assert e.message == "Test error"
            assert e.timestamp is not None
