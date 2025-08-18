"""Global pytest configuration and fixtures."""

import os
import pytest


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Set up test environment variables automatically."""
    # Set required environment variables for authentication tests
    os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-testing-only"
    os.environ["ENABLE_DEMO_USERS"] = "true"
    
    yield
    
    # Clean up after tests
    os.environ.pop("JWT_SECRET_KEY", None)
    os.environ.pop("ENABLE_DEMO_USERS", None)


@pytest.fixture(scope="function", autouse=True) 
def reset_global_state():
    """Reset global state between tests to avoid interference."""
    # Reset rate limiter state
    try:
        from cc_orchestrator.web.middlewares.rate_limiter import rate_limiter
        if hasattr(rate_limiter, 'ip_buckets'):
            rate_limiter.ip_buckets.clear()
        if hasattr(rate_limiter, 'websocket_ip_buckets'):
            rate_limiter.websocket_ip_buckets.clear()
    except (ImportError, AttributeError):
        pass
    
    # Reset log storage
    try:
        from cc_orchestrator.web.routers.v1.logs import log_storage, audit_log_storage, stream_stats
        log_storage.clear()
        audit_log_storage.clear()
        from datetime import datetime
        stream_stats.update({
            "active_streams": 0,
            "total_entries_streamed": 0,
            "stream_start_time": datetime.now(),
            "buffer_usage": {},
        })
    except (ImportError, AttributeError):
        pass
    
    yield