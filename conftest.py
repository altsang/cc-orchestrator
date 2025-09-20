"""Global pytest configuration and fixtures."""

import os

import pytest


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Set up test environment variables automatically."""
    # Set required environment variables for authentication tests
    os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-testing-only"
    os.environ["ENABLE_DEMO_USERS"] = "true"
    # Set very high rate limits for testing (not disabled, just permissive)
    os.environ["TEST_RATE_LIMIT_PER_MINUTE"] = "10000"  # Very high limit for tests

    yield

    # Clean up after tests
    os.environ.pop("JWT_SECRET_KEY", None)
    os.environ.pop("ENABLE_DEMO_USERS", None)
    os.environ.pop("TEST_RATE_LIMIT_PER_MINUTE", None)


@pytest.fixture(scope="function", autouse=True)
def reset_global_state():
    """Reset global state between tests to avoid interference."""
    # Reset rate limiter state at the start
    try:
        from src.cc_orchestrator.web.rate_limiter import rate_limiter

        # Clear the request history to reset rate limiting
        rate_limiter.request_history.clear()
    except (ImportError, AttributeError):
        pass

    # Don't reset log storage automatically - let tests manage their own state
    # This prevents interference with tests that need to set up and use log storage
    try:
        from datetime import datetime

        from src.cc_orchestrator.web.routers.v1.logs import stream_stats

        stream_stats.update(
            {
                "active_streams": 0,
                "total_entries_streamed": 0,
                "stream_start_time": datetime.now(),
                "buffer_usage": {},
            }
        )
    except (ImportError, AttributeError):
        pass

    yield
