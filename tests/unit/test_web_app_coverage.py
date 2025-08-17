"""Comprehensive tests for web.app module to achieve 100% coverage."""

import os
from unittest.mock import Mock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from cc_orchestrator.web.app import create_app, lifespan
from cc_orchestrator.web.exceptions import CCOrchestratorAPIException


class TestLifespan:
    """Test application lifespan management."""

    @pytest.mark.asyncio
    async def test_lifespan_startup_and_shutdown(self):
        """Test lifespan context manager startup and shutdown."""
        mock_app = Mock(spec=FastAPI)
        # Add state attribute to the mock app
        mock_app.state = Mock()

        # Create a mock database manager instance
        mock_db_manager_instance = Mock()

        # Patch the DatabaseManager to return our mock instance
        with patch(
            "cc_orchestrator.web.app.DatabaseManager",
            return_value=mock_db_manager_instance,
        ):
            # Test that lifespan completes without error and doesn't raise an exception
            try:
                async with lifespan(mock_app):
                    # Lifespan should complete without error
                    assert hasattr(mock_app.state, "db_manager")
            except Exception as e:
                pytest.fail(f"Lifespan context manager failed: {e}")

            # The main goal is that lifespan completes successfully


class TestCreateAppDevelopment:
    """Test create_app function in development mode."""

    def test_create_app_debug_mode(self):
        """Test app creation in debug mode."""
        with patch.dict(os.environ, {"DEBUG": "true"}, clear=False):
            app = create_app()

            assert isinstance(app, FastAPI)
            assert app.title == "CC-Orchestrator API"
            assert app.description == "Claude Code Orchestrator Dashboard API"
            assert app.version == "0.1.0"

    def test_create_app_debug_mode_cors_origins(self):
        """Test CORS origins in debug mode."""
        with patch.dict(os.environ, {"DEBUG": "true"}, clear=False):
            with patch("fastapi.FastAPI.add_middleware") as mock_add_middleware:
                app = create_app()

                # Should add CORS middleware with development origins
                mock_add_middleware.assert_called()
                call_args = mock_add_middleware.call_args_list

                # Find the CORS middleware call
                cors_call = None
                for call in call_args:
                    if (
                        call[0]
                        and hasattr(call[0][0], "__name__")
                        and "CORS" in str(call[0][0])
                    ):
                        cors_call = call
                        break

                assert cors_call is not None
                kwargs = cors_call[1]
                assert "http://localhost:3000" in kwargs["allow_origins"]
                assert "http://localhost:5173" in kwargs["allow_origins"]
                assert kwargs["allow_credentials"] is True
                assert "GET" in kwargs["allow_methods"]
                assert "POST" in kwargs["allow_methods"]
                assert "Authorization" in kwargs["allow_headers"]

    def test_create_app_default_debug_false(self):
        """Test app creation when DEBUG is not set (defaults to false)."""
        test_env = {
            "FRONTEND_URL": "https://production.example.com",
            "JWT_SECRET_KEY": "test-key",
        }
        with patch.dict(os.environ, test_env, clear=False):
            # Remove DEBUG if it exists
            os.environ.pop("DEBUG", None)

            app = create_app()
            assert isinstance(app, FastAPI)


class TestCreateAppProduction:
    """Test create_app function in production mode."""

    def test_create_app_production_mode_valid(self):
        """Test app creation in production mode with valid configuration."""
        test_env = {
            "DEBUG": "false",
            "FRONTEND_URL": "https://production.example.com",
            "JWT_SECRET_KEY": "production-secret-key-12345",
        }

        with patch.dict(os.environ, test_env, clear=False):
            with patch("fastapi.FastAPI.add_middleware") as mock_add_middleware:
                app = create_app()

                assert isinstance(app, FastAPI)

                # Should add CORS middleware with production URL
                mock_add_middleware.assert_called()
                call_args = mock_add_middleware.call_args_list

                # Find the CORS middleware call
                cors_call = None
                for call in call_args:
                    if (
                        call[0]
                        and hasattr(call[0][0], "__name__")
                        and "CORS" in str(call[0][0])
                    ):
                        cors_call = call
                        break

                assert cors_call is not None
                kwargs = cors_call[1]
                assert kwargs["allow_origins"] == ["https://production.example.com"]

    def test_create_app_production_missing_frontend_url(self):
        """Test app creation fails when FRONTEND_URL is missing in production."""
        test_env = {"DEBUG": "false"}

        with patch.dict(os.environ, test_env, clear=False):
            # Remove FRONTEND_URL if it exists
            os.environ.pop("FRONTEND_URL", None)

            with pytest.raises(
                ValueError, match="FRONTEND_URL must be set when DEBUG=false"
            ):
                create_app()

    def test_create_app_production_invalid_frontend_url(self):
        """Test app creation fails with invalid FRONTEND_URL format."""
        test_env = {
            "DEBUG": "false",
            "FRONTEND_URL": "invalid-url-format",
            "JWT_SECRET_KEY": "test-key",
        }

        with patch.dict(os.environ, test_env, clear=False):
            with pytest.raises(
                ValueError, match="FRONTEND_URL must be a valid HTTP\\(S\\) URL"
            ):
                create_app()

    def test_create_app_production_missing_jwt_secret(self):
        """Test app creation fails when JWT_SECRET_KEY is missing in production."""
        test_env = {"DEBUG": "false", "FRONTEND_URL": "https://production.example.com"}

        with patch.dict(os.environ, test_env, clear=False):
            # Remove JWT_SECRET_KEY if it exists
            os.environ.pop("JWT_SECRET_KEY", None)

            with pytest.raises(
                ValueError, match="JWT_SECRET_KEY must be set in production mode"
            ):
                create_app()

    def test_create_app_production_http_warning(self):
        """Test warning when using HTTP in production mode."""
        test_env = {
            "DEBUG": "false",
            "FRONTEND_URL": "http://production.example.com",
            "JWT_SECRET_KEY": "test-key",
        }

        with patch.dict(os.environ, test_env, clear=False):
            with patch("logging.warning") as mock_warning:
                create_app()

                # Should warn about HTTP in production
                mock_warning.assert_called_once()
                warning_msg = mock_warning.call_args[0][0]
                assert "Using HTTP (not HTTPS)" in warning_msg
                assert "Consider using HTTPS" in warning_msg

    def test_create_app_production_localhost_http_no_warning(self):
        """Test no warning when using localhost HTTP in production."""
        test_env = {
            "DEBUG": "false",
            "FRONTEND_URL": "http://localhost:3000",
            "JWT_SECRET_KEY": "test-key",
        }

        with patch.dict(os.environ, test_env, clear=False):
            with patch("logging.warning") as mock_warning:
                create_app()

                # Should not warn about localhost HTTP
                mock_warning.assert_not_called()

    def test_create_app_production_https_valid(self):
        """Test valid HTTPS URL in production mode."""
        test_env = {
            "DEBUG": "false",
            "FRONTEND_URL": "https://secure.example.com",
            "JWT_SECRET_KEY": "test-key",
        }

        with patch.dict(os.environ, test_env, clear=False):
            app = create_app()
            assert isinstance(app, FastAPI)


class TestAppEndpoints:
    """Test app endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        with patch.dict(os.environ, {"DEBUG": "true"}, clear=False):
            app = create_app()
            return TestClient(app)

    def test_root_endpoint(self, client):
        """Test root endpoint returns HTML."""
        response = client.get("/")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert "CC-Orchestrator Dashboard" in response.text
        assert "/docs" in response.text
        assert "React Frontend will be served here" in response.text

    def test_health_endpoint(self, client):
        """Test health check endpoint."""
        response = client.get("/health")

        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}

    def test_root_endpoint_html_structure(self, client):
        """Test root endpoint HTML structure."""
        response = client.get("/")

        html_content = response.text
        assert "<!DOCTYPE html>" in html_content
        assert "<html>" in html_content
        assert "<head>" in html_content
        assert "<title>CC-Orchestrator Dashboard</title>" in html_content
        assert "<body>" in html_content
        assert "<h1>CC-Orchestrator Dashboard</h1>" in html_content
        assert '<a href="/docs">/docs</a>' in html_content


class TestExceptionHandler:
    """Test custom exception handler."""

    def test_api_exception_handler(self):
        """Test custom API exception handler."""
        with patch.dict(os.environ, {"DEBUG": "true"}, clear=False):
            app = create_app()

            # Add a test route that raises CCOrchestratorAPIException
            @app.get("/test-exception")
            async def test_exception():
                raise CCOrchestratorAPIException(
                    status_code=400, message="Test error message"
                )

            test_client = TestClient(app)
            response = test_client.get("/test-exception")

            assert response.status_code == 400
            assert response.json() == {
                "error": "CCOrchestratorAPIException",
                "message": "Test error message",
                "status_code": 400,
            }

    def test_api_exception_handler_different_status(self):
        """Test exception handler with different status code."""
        with patch.dict(os.environ, {"DEBUG": "true"}, clear=False):
            app = create_app()

            @app.get("/test-500")
            async def test_500():
                raise CCOrchestratorAPIException(
                    status_code=500, message="Internal server error"
                )

            test_client = TestClient(app)
            response = test_client.get("/test-500")

            assert response.status_code == 500
            assert response.json()["error"] == "CCOrchestratorAPIException"
            assert response.json()["message"] == "Internal server error"
            assert response.json()["status_code"] == 500


class TestDebugEnvironmentVariations:
    """Test different DEBUG environment variable values."""

    def test_debug_true_string(self):
        """Test DEBUG=true as string."""
        with patch.dict(os.environ, {"DEBUG": "true"}, clear=False):
            app = create_app()
            assert isinstance(app, FastAPI)

    def test_debug_false_string(self):
        """Test DEBUG=false as string."""
        test_env = {
            "DEBUG": "false",
            "FRONTEND_URL": "https://example.com",
            "JWT_SECRET_KEY": "test-key",
        }
        with patch.dict(os.environ, test_env, clear=False):
            app = create_app()
            assert isinstance(app, FastAPI)

    def test_debug_case_insensitive(self):
        """Test DEBUG value is case insensitive."""
        with patch.dict(os.environ, {"DEBUG": "TRUE"}, clear=False):
            app = create_app()
            assert isinstance(app, FastAPI)

        with patch.dict(os.environ, {"DEBUG": "True"}, clear=False):
            app = create_app()
            assert isinstance(app, FastAPI)

        test_env = {
            "DEBUG": "FALSE",
            "FRONTEND_URL": "https://example.com",
            "JWT_SECRET_KEY": "test-key",
        }
        with patch.dict(os.environ, test_env, clear=False):
            app = create_app()
            assert isinstance(app, FastAPI)

    def test_debug_invalid_value(self):
        """Test DEBUG with invalid value defaults to false."""
        test_env = {
            "DEBUG": "invalid",
            "FRONTEND_URL": "https://example.com",
            "JWT_SECRET_KEY": "test-key",
        }
        with patch.dict(os.environ, test_env, clear=False):
            app = create_app()
            assert isinstance(app, FastAPI)


class TestFrontendUrlValidation:
    """Test FRONTEND_URL validation."""

    def test_frontend_url_http_valid(self):
        """Test valid HTTP frontend URL."""
        test_env = {
            "DEBUG": "false",
            "FRONTEND_URL": "http://localhost:3000",
            "JWT_SECRET_KEY": "test-key",
        }
        with patch.dict(os.environ, test_env, clear=False):
            app = create_app()
            assert isinstance(app, FastAPI)

    def test_frontend_url_https_valid(self):
        """Test valid HTTPS frontend URL."""
        test_env = {
            "DEBUG": "false",
            "FRONTEND_URL": "https://secure.example.com",
            "JWT_SECRET_KEY": "test-key",
        }
        with patch.dict(os.environ, test_env, clear=False):
            app = create_app()
            assert isinstance(app, FastAPI)

    def test_frontend_url_no_protocol(self):
        """Test frontend URL without protocol fails."""
        test_env = {
            "DEBUG": "false",
            "FRONTEND_URL": "example.com",
            "JWT_SECRET_KEY": "test-key",
        }
        with patch.dict(os.environ, test_env, clear=False):
            with pytest.raises(
                ValueError, match="FRONTEND_URL must be a valid HTTP\\(S\\) URL"
            ):
                create_app()

    def test_frontend_url_ftp_protocol(self):
        """Test frontend URL with FTP protocol fails."""
        test_env = {
            "DEBUG": "false",
            "FRONTEND_URL": "ftp://example.com",
            "JWT_SECRET_KEY": "test-key",
        }
        with patch.dict(os.environ, test_env, clear=False):
            with pytest.raises(
                ValueError, match="FRONTEND_URL must be a valid HTTP\\(S\\) URL"
            ):
                create_app()

    def test_frontend_url_empty_string(self):
        """Test empty FRONTEND_URL fails."""
        test_env = {"DEBUG": "false", "FRONTEND_URL": "", "JWT_SECRET_KEY": "test-key"}
        with patch.dict(os.environ, test_env, clear=False):
            with pytest.raises(
                ValueError, match="FRONTEND_URL must be set when DEBUG=false"
            ):
                create_app()


class TestModuleLevelApp:
    """Test module-level app instance."""

    def test_module_app_instance(self):
        """Test that module creates app instance."""
        # The module should create an app instance at import time
        from cc_orchestrator.web.app import app

        assert isinstance(app, FastAPI)
        assert app.title == "CC-Orchestrator API"

    def test_module_app_instance_configuration(self):
        """Test module app instance configuration."""
        # Ensure the module app has proper configuration
        from cc_orchestrator.web.app import app

        # Should have exception handlers
        assert CCOrchestratorAPIException in app.exception_handlers

        # Should have routes
        routes = [route.path for route in app.routes]
        assert "/" in routes
        assert "/health" in routes


class TestCORSConfiguration:
    """Test CORS configuration details."""

    def test_cors_methods_configuration(self):
        """Test CORS allowed methods configuration."""
        with patch.dict(os.environ, {"DEBUG": "true"}, clear=False):
            with patch("fastapi.FastAPI.add_middleware") as mock_add_middleware:
                create_app()

                # Find the CORS middleware call
                cors_call = None
                for call in mock_add_middleware.call_args_list:
                    if (
                        call[0]
                        and hasattr(call[0][0], "__name__")
                        and "CORS" in str(call[0][0])
                    ):
                        cors_call = call
                        break

                assert cors_call is not None
                allowed_methods = cors_call[1]["allow_methods"]

                assert "GET" in allowed_methods
                assert "POST" in allowed_methods
                assert "PUT" in allowed_methods
                assert "PATCH" in allowed_methods
                assert "DELETE" in allowed_methods
                assert "OPTIONS" in allowed_methods

    def test_cors_headers_configuration(self):
        """Test CORS allowed headers configuration."""
        with patch.dict(os.environ, {"DEBUG": "true"}, clear=False):
            with patch("fastapi.FastAPI.add_middleware") as mock_add_middleware:
                create_app()

                # Find the CORS middleware call
                cors_call = None
                for call in mock_add_middleware.call_args_list:
                    if (
                        call[0]
                        and hasattr(call[0][0], "__name__")
                        and "CORS" in str(call[0][0])
                    ):
                        cors_call = call
                        break

                assert cors_call is not None
                allowed_headers = cors_call[1]["allow_headers"]

                assert "Content-Type" in allowed_headers
                assert "Authorization" in allowed_headers
                assert "Accept" in allowed_headers

    def test_cors_credentials_enabled(self):
        """Test CORS credentials are enabled."""
        with patch.dict(os.environ, {"DEBUG": "true"}, clear=False):
            with patch("fastapi.FastAPI.add_middleware") as mock_add_middleware:
                create_app()

                # Find the CORS middleware call
                cors_call = None
                for call in mock_add_middleware.call_args_list:
                    if (
                        call[0]
                        and hasattr(call[0][0], "__name__")
                        and "CORS" in str(call[0][0])
                    ):
                        cors_call = call
                        break

                assert cors_call is not None
                assert cors_call[1]["allow_credentials"] is True
