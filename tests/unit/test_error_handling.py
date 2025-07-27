"""
Unit tests for error handling decorators and functionality.

Tests cover:
- handle_errors decorator functionality
- Recovery strategy execution
- log_performance decorator
- audit_log decorator
- Error handling with and without recovery
- Context preservation during error handling
"""

import time
from unittest.mock import Mock, patch, call
import pytest

from cc_orchestrator.utils.logging import (
    handle_errors,
    log_performance,
    audit_log,
    get_logger,
    LogContext,
    CCOrchestratorException,
    InstanceError,
    TaskError
)


class TestHandleErrorsDecorator:
    """Test the handle_errors decorator functionality."""
    
    def test_handle_errors_success_case(self):
        """Test that handle_errors allows successful execution."""
        @handle_errors(log_context=LogContext.INSTANCE)
        def successful_function(value):
            return value * 2
        
        result = successful_function(5)
        assert result == 10
    
    def test_handle_errors_with_cc_orchestrator_exception(self):
        """Test handling of CCOrchestratorException."""
        @handle_errors(log_context=LogContext.INSTANCE, reraise=True)
        def failing_function():
            raise InstanceError("Test instance error", {"instance_id": "test-001"})
        
        with pytest.raises(InstanceError) as exc_info:
            failing_function()
        
        assert exc_info.value.message == "Test instance error"
        assert exc_info.value.context["instance_id"] == "test-001"
    
    def test_handle_errors_with_generic_exception(self):
        """Test handling of generic exceptions."""
        @handle_errors(log_context=LogContext.TASK, reraise=True)
        def failing_function():
            raise ValueError("Generic error")
        
        with pytest.raises(CCOrchestratorException) as exc_info:
            failing_function()
        
        assert "Unexpected error in failing_function: Generic error" in exc_info.value.message
    
    def test_handle_errors_without_reraise(self):
        """Test error handling without reraising exceptions."""
        @handle_errors(log_context=LogContext.WEB, reraise=False)
        def failing_function():
            raise ValueError("Error that should not be reraised")
        
        # Should not raise an exception
        result = failing_function()
        assert result is None
    
    def test_handle_errors_with_recovery_strategy(self):
        """Test error handling with successful recovery strategy."""
        def recovery_function(error, *args, **kwargs):
            return "recovered_value"
        
        @handle_errors(recovery_strategy=recovery_function, reraise=False)
        def failing_function():
            raise InstanceError("Recoverable error")
        
        result = failing_function()
        assert result == "recovered_value"
    
    def test_handle_errors_with_failing_recovery_strategy(self):
        """Test error handling when recovery strategy also fails."""
        def failing_recovery(error, *args, **kwargs):
            raise RuntimeError("Recovery failed")
        
        @handle_errors(recovery_strategy=failing_recovery, reraise=True)
        def failing_function():
            raise InstanceError("Original error")
        
        with pytest.raises(InstanceError):
            failing_function()
    
    @patch('cc_orchestrator.utils.logging.get_logger')
    def test_handle_errors_logging_calls(self, mock_get_logger):
        """Test that error handling makes appropriate logging calls."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        
        @handle_errors(log_context=LogContext.ORCHESTRATOR, reraise=False)
        def test_function():
            raise ValueError("Test error")
        
        test_function()
        
        # Verify logger was obtained and error was logged
        mock_get_logger.assert_called()
        mock_logger.debug.assert_called()
        mock_logger.error.assert_called()
    
    def test_handle_errors_preserves_function_metadata(self):
        """Test that the decorator preserves function metadata."""
        @handle_errors()
        def documented_function():
            """This function has documentation."""
            return "result"
        
        assert documented_function.__name__ == "documented_function"
        assert documented_function.__doc__ == "This function has documentation."
    
    def test_handle_errors_with_function_arguments(self):
        """Test error handling with function arguments."""
        recovery_calls = []
        
        def recovery_strategy(error, *args, **kwargs):
            recovery_calls.append((args, kwargs))
            return "recovered"
        
        @handle_errors(recovery_strategy=recovery_strategy, reraise=False)
        def function_with_args(a, b, c=None):
            raise ValueError("Error with args")
        
        result = function_with_args(1, 2, c=3)
        
        assert result == "recovered"
        assert len(recovery_calls) == 1
        assert recovery_calls[0] == ((1, 2), {"c": 3})


class TestLogPerformanceDecorator:
    """Test the log_performance decorator functionality."""
    
    @patch('cc_orchestrator.utils.logging.get_logger')
    @patch('time.time')
    def test_log_performance_success(self, mock_time, mock_get_logger):
        """Test performance logging for successful function execution."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        
        # Mock time progression
        mock_time.side_effect = [100.0, 100.5]  # 0.5 second execution
        
        @log_performance(LogContext.TASK)
        def timed_function():
            return "success"
        
        result = timed_function()
        
        assert result == "success"
        mock_get_logger.assert_called_with(timed_function.__module__, LogContext.TASK)
        
        # Check that debug and info calls were made
        mock_logger.debug.assert_called()
        mock_logger.info.assert_called()
        
        # Verify the info call includes execution time
        info_call = mock_logger.info.call_args
        assert "completed" in info_call[0][0]
        assert info_call[1]["execution_time"] == 0.5
        assert info_call[1]["status"] == "success"
    
    @patch('cc_orchestrator.utils.logging.get_logger')
    @patch('time.time')
    def test_log_performance_failure(self, mock_time, mock_get_logger):
        """Test performance logging for failed function execution."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        
        # Mock time progression
        mock_time.side_effect = [200.0, 200.3]  # 0.3 second execution before failure
        
        @log_performance(LogContext.INSTANCE)
        def failing_function():
            raise ValueError("Function failed")
        
        with pytest.raises(ValueError):
            failing_function()
        
        # Check that warning was logged for failure
        mock_logger.warning.assert_called()
        
        warning_call = mock_logger.warning.call_args
        assert "failed" in warning_call[0][0]
        # Allow for small floating point differences
        assert abs(warning_call[1]["execution_time"] - 0.3) < 0.01
        assert warning_call[1]["status"] == "error"
        assert warning_call[1]["error"] == "Function failed"
    
    def test_log_performance_preserves_function_metadata(self):
        """Test that log_performance preserves function metadata."""
        @log_performance(LogContext.WEB)
        def performance_tested_function():
            """Function with performance monitoring."""
            return 42
        
        assert performance_tested_function.__name__ == "performance_tested_function"
        assert performance_tested_function.__doc__ == "Function with performance monitoring."


class TestAuditLogDecorator:
    """Test the audit_log decorator functionality."""
    
    @patch('cc_orchestrator.utils.logging.get_logger')
    def test_audit_log_success(self, mock_get_logger):
        """Test audit logging for successful function execution."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        
        @audit_log("critical_operation", LogContext.ORCHESTRATOR)
        def audited_function(param1, param2=None):
            return f"processed {param1}"
        
        result = audited_function("test_data", param2="extra")
        
        assert result == "processed test_data"
        
        # Verify logger was created with audit suffix
        mock_get_logger.assert_called_with(f"{audited_function.__module__}.audit", LogContext.ORCHESTRATOR)
        
        # Check that start and completion were logged
        assert mock_logger.info.call_count == 2
        
        start_call = mock_logger.info.call_args_list[0]
        assert "critical_operation started" in start_call[0][0]
        assert start_call[1]["action"] == "critical_operation"
        
        completion_call = mock_logger.info.call_args_list[1]
        assert "critical_operation completed successfully" in completion_call[0][0]
        assert completion_call[1]["status"] == "success"
    
    @patch('cc_orchestrator.utils.logging.get_logger')
    def test_audit_log_failure(self, mock_get_logger):
        """Test audit logging for failed function execution."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        
        @audit_log("risky_operation", LogContext.DATABASE)
        def failing_audited_function():
            raise RuntimeError("Operation failed")
        
        with pytest.raises(RuntimeError):
            failing_audited_function()
        
        # Check that start and error were logged
        assert mock_logger.info.call_count == 1  # Start only
        assert mock_logger.error.call_count == 1  # Failure
        
        start_call = mock_logger.info.call_args
        assert "risky_operation started" in start_call[0][0]
        
        error_call = mock_logger.error.call_args
        assert "risky_operation failed" in error_call[0][0]
        assert error_call[1]["status"] == "error"
        assert error_call[1]["error"] == "Operation failed"
    
    def test_audit_log_preserves_function_metadata(self):
        """Test that audit_log preserves function metadata."""
        @audit_log("test_action", LogContext.TMUX)
        def audited_function():
            """Function with audit logging."""
            pass
        
        assert audited_function.__name__ == "audited_function"
        assert audited_function.__doc__ == "Function with audit logging."


class TestDecoratorCombinations:
    """Test combinations of decorators working together."""
    
    @patch('cc_orchestrator.utils.logging.get_logger')
    def test_combined_decorators(self, mock_get_logger):
        """Test using multiple decorators together."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        
        def recovery_strategy(error, *args, **kwargs):
            return "recovered"
        
        @handle_errors(recovery_strategy=recovery_strategy, reraise=False)
        @log_performance(LogContext.INSTANCE)
        @audit_log("complex_operation", LogContext.INSTANCE)
        def complex_function():
            raise ValueError("Intentional failure for testing")
        
        result = complex_function()
        
        assert result == "recovered"
        # Multiple loggers should have been created for different aspects
        assert mock_get_logger.call_count >= 2
    
    def test_decorator_order_independence(self):
        """Test that decorator order doesn't break functionality."""
        def recovery_fn(error, *args, **kwargs):
            return "order_test_recovered"
        
        # Test different decorator orders
        @audit_log("test_op", LogContext.TASK)
        @handle_errors(recovery_strategy=recovery_fn, reraise=False)
        @log_performance(LogContext.TASK)
        def function_order_1():
            raise ValueError("Test")
        
        @log_performance(LogContext.TASK)
        @handle_errors(recovery_strategy=recovery_fn, reraise=False)
        @audit_log("test_op", LogContext.TASK)
        def function_order_2():
            raise ValueError("Test")
        
        result1 = function_order_1()
        result2 = function_order_2()
        
        assert result1 == "order_test_recovered"
        assert result2 == "order_test_recovered"


class TestErrorHandlingEdgeCases:
    """Test edge cases in error handling."""
    
    def test_handle_errors_with_none_recovery_strategy(self):
        """Test that None recovery strategy is handled properly."""
        @handle_errors(recovery_strategy=None, reraise=False)
        def function_with_none_recovery():
            raise ValueError("No recovery")
        
        result = function_with_none_recovery()
        assert result is None
    
    def test_handle_errors_with_empty_args(self):
        """Test error handling with functions that take no arguments."""
        @handle_errors(reraise=True)
        def no_args_function():
            raise TaskError("No args error")
        
        with pytest.raises(TaskError):
            no_args_function()
    
    def test_recovery_strategy_with_modified_args(self):
        """Test recovery strategy that modifies arguments."""
        def modifying_recovery(error, *args, **kwargs):
            # Return modified arguments
            return f"recovered with args: {args}, kwargs: {kwargs}"
        
        @handle_errors(recovery_strategy=modifying_recovery, reraise=False)
        def function_with_args(a, b, c=10):
            raise ValueError("Will be recovered")
        
        result = function_with_args(1, 2, c=20)
        assert "args: (1, 2)" in result
        assert "kwargs: {'c': 20}" in result
    
    def test_exception_context_preservation(self):
        """Test that exception context is preserved through error handling."""
        original_context = {"key": "value", "number": 42}
        
        @handle_errors(reraise=True)
        def context_preserving_function():
            raise InstanceError("Context test", original_context)
        
        with pytest.raises(InstanceError) as exc_info:
            context_preserving_function()
        
        assert exc_info.value.context == original_context