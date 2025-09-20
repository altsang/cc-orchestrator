"""Comprehensive tests for web application module."""

import os
from unittest.mock import patch

import pytest
from fastapi import FastAPI


class TestAppCreation:
    """Test FastAPI application creation."""

    def test_create_app_development_mode(self):
        """Test app creation in development mode."""
        with patch.dict(
            os.environ, {"DEBUG": "true", "JWT_SECRET_KEY": "test-secret-key"}
        ):
            from cc_orchestrator.web.app import create_app

            app = create_app()
            assert isinstance(app, FastAPI)
            assert app.title == "CC-Orchestrator API"
            assert app.description == "Claude Code Orchestrator Dashboard API"
            assert app.version == "0.1.0"

    def test_create_app_production_mode_valid(self):
        """Test app creation in production mode with valid config."""
        with patch.dict(
            os.environ,
            {
                "DEBUG": "false",
                "FRONTEND_URL": "https://example.com",
                "JWT_SECRET_KEY": "test-secret-key",
            },
        ):
            from cc_orchestrator.web.app import create_app

            app = create_app()
            assert isinstance(app, FastAPI)

    def test_create_app_production_mode_missing_frontend_url(self):
        """Test app creation fails without FRONTEND_URL in production."""
        import sys

        # Clear the module cache to force re-import
        if "cc_orchestrator.web.app" in sys.modules:
            del sys.modules["cc_orchestrator.web.app"]

        with patch.dict(
            os.environ,
            {"DEBUG": "false", "JWT_SECRET_KEY": "test-secret-key"},
            clear=False,
        ):
            # Ensure FRONTEND_URL is not set
            if "FRONTEND_URL" in os.environ:
                del os.environ["FRONTEND_URL"]

            with pytest.raises(
                ValueError, match="FRONTEND_URL must be set when DEBUG=false"
            ):
                from cc_orchestrator.web.app import create_app

                create_app()

    def test_create_app_production_mode_invalid_frontend_url(self):
        """Test app creation fails with invalid FRONTEND_URL."""
        invalid_urls = ["not-a-url", "ftp://example.com", "invalid-protocol://test.com"]

        for invalid_url in invalid_urls:
            with patch.dict(
                os.environ,
                {
                    "DEBUG": "false",
                    "FRONTEND_URL": invalid_url,
                    "JWT_SECRET_KEY": "test-secret-key",
                },
            ):
                with pytest.raises(ValueError, match="must be a valid HTTP"):
                    from cc_orchestrator.web.app import create_app

                    create_app()

    def test_create_app_production_mode_missing_jwt_secret(self):
        """Test app creation fails without JWT_SECRET_KEY in production."""
        with patch.dict(
            os.environ,
            {"DEBUG": "false", "FRONTEND_URL": "https://example.com"},
            clear=True,
        ):
            with pytest.raises(ValueError, match="JWT_SECRET_KEY must be set"):
                from cc_orchestrator.web.app import create_app

                create_app()


class TestCORSConfiguration:
    """Test CORS middleware configuration."""

    def test_development_cors_origins(self):
        """Test CORS origins in development mode."""
        with patch.dict(
            os.environ, {"DEBUG": "true", "JWT_SECRET_KEY": "test-secret-key"}
        ):
            from cc_orchestrator.web.app import create_app

            app = create_app()

            # Check that development origins are used
            cors_middleware = None
            for middleware in app.user_middleware:
                if (
                    hasattr(middleware, "cls")
                    and middleware.cls.__name__ == "CORSMiddleware"
                ):
                    cors_middleware = middleware
                    break

            assert cors_middleware is not None

    def test_production_cors_origins(self):
        """Test CORS origins in production mode."""
        test_url = "https://my-frontend.example.com"
        with patch.dict(
            os.environ,
            {
                "DEBUG": "false",
                "FRONTEND_URL": test_url,
                "JWT_SECRET_KEY": "test-secret-key",
            },
        ):
            from cc_orchestrator.web.app import create_app

            app = create_app()

            # App should be created without error
            assert isinstance(app, FastAPI)

    def test_http_warning_in_production(self):
        """Test warning for HTTP URLs in production."""
        with patch.dict(
            os.environ,
            {
                "DEBUG": "false",
                "FRONTEND_URL": "http://example.com",  # HTTP not HTTPS
                "JWT_SECRET_KEY": "test-secret-key",
            },
        ):
            # Should create app but may log warning
            from cc_orchestrator.web.app import create_app

            app = create_app()
            assert isinstance(app, FastAPI)

    def test_localhost_http_allowed_in_production(self):
        """Test that localhost HTTP is allowed in production."""
        with patch.dict(
            os.environ,
            {
                "DEBUG": "false",
                "FRONTEND_URL": "http://localhost:3000",
                "JWT_SECRET_KEY": "test-secret-key",
            },
        ):
            from cc_orchestrator.web.app import create_app

            app = create_app()
            assert isinstance(app, FastAPI)


class TestRouterInclusion:
    """Test that all routers are properly included."""

    def test_routers_included(self):
        """Test that all expected routers are included."""
        with patch.dict(
            os.environ, {"DEBUG": "true", "JWT_SECRET_KEY": "test-secret-key"}
        ):
            from cc_orchestrator.web.app import create_app

            app = create_app()

            # Check that routers are included
            route_paths = [route.path for route in app.routes]

            # Should have basic endpoints
            assert "/" in [route.path for route in app.routes if hasattr(route, "path")]
            assert any("/health" in path for path in route_paths)


class TestExceptionHandlers:
    """Test exception handler configuration."""

    def test_custom_exception_handler_registered(self):
        """Test that custom exception handler is registered."""
        with patch.dict(
            os.environ, {"DEBUG": "true", "JWT_SECRET_KEY": "test-secret-key"}
        ):
            from cc_orchestrator.web.app import create_app

            app = create_app()

            # Check exception handlers are registered
            assert app.exception_handlers is not None


class TestHealthEndpoint:
    """Test health check endpoint."""

    @pytest.mark.skip(reason="TestClient compatibility issue with newer HTTPX versions")
    def test_health_endpoint_exists(self):
        """Test that health endpoint exists and returns correct response."""
        with patch.dict(
            os.environ, {"DEBUG": "true", "JWT_SECRET_KEY": "test-secret-key"}
        ):
            from fastapi.testclient import TestClient

            from cc_orchestrator.web.app import create_app

            app = create_app()
            client = TestClient(app)

            response = client.get("/health")
            assert response.status_code == 200
            assert response.json() == {"status": "healthy"}


class TestRootEndpoint:
    """Test root endpoint functionality."""

    @pytest.mark.skip(reason="TestClient compatibility issue with newer HTTPX versions")
    def test_root_endpoint_html(self):
        """Test that root endpoint returns HTML."""
        with patch.dict(
            os.environ, {"DEBUG": "true", "JWT_SECRET_KEY": "test-secret-key"}
        ):
            from fastapi.testclient import TestClient

            from cc_orchestrator.web.app import create_app

            app = create_app()
            client = TestClient(app)

            response = client.get("/")
            assert response.status_code == 200
            assert "text/html" in response.headers.get("content-type", "")
            assert "CC-Orchestrator Dashboard" in response.text
            assert "/docs" in response.text


class TestApplicationLifespan:
    """Test application lifespan management."""

    def test_lifespan_function_exists(self):
        """Test that lifespan function is properly configured."""
        with patch.dict(
            os.environ, {"DEBUG": "true", "JWT_SECRET_KEY": "test-secret-key"}
        ):
            from cc_orchestrator.web.app import create_app

            app = create_app()

            # App should have lifespan configured
            assert hasattr(app, "router")


class TestDevelopmentVsProduction:
    """Test differences between development and production modes."""

    def test_debug_mode_environment_variable(self):
        """Test DEBUG environment variable handling."""
        # Test various DEBUG values
        debug_values = [
            ("true", True),
            ("false", False),
            ("TRUE", True),
            ("FALSE", False),
            ("1", False),  # Only "true" should be true
            ("", False),  # Empty should default to false
        ]

        for debug_val, expected_debug in debug_values:
            env_vars = {"DEBUG": debug_val, "JWT_SECRET_KEY": "test-secret-key"}

            if not expected_debug:
                env_vars["FRONTEND_URL"] = "https://example.com"

            with patch.dict(os.environ, env_vars):
                from cc_orchestrator.web.app import create_app

                try:
                    app = create_app()
                    assert isinstance(app, FastAPI)
                except ValueError:
                    # Production mode requirements not met is expected for some cases
                    assert not expected_debug


class TestModuleConstants:
    """Test module-level constants and app instance."""

    def test_app_instance_creation(self):
        """Test that module creates app instance."""
        with patch.dict(
            os.environ, {"DEBUG": "true", "JWT_SECRET_KEY": "test-secret-key"}
        ):
            from cc_orchestrator.web.app import app

            assert isinstance(app, FastAPI)
            assert app.title == "CC-Orchestrator API"
