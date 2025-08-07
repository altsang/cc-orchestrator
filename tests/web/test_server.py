"""
Tests for web server startup and configuration.

Tests server configuration loading, environment variable handling, and server startup.
"""

import os
from unittest.mock import Mock, patch

from cc_orchestrator.web.server import get_server_config, main, run_server


class TestServerConfiguration:
    """Test server configuration loading and environment variable handling."""

    @patch("cc_orchestrator.web.server.load_config")
    def test_get_server_config_defaults(self, mock_load_config):
        """Test server configuration with default values."""
        # Mock config with no web-specific attributes (using spec to avoid auto-Mock attributes)
        mock_config = Mock(spec=[])
        mock_load_config.return_value = mock_config

        config = get_server_config()

        # Check default values
        assert config["host"] == "127.0.0.1"
        assert config["port"] == 8080
        assert config["reload"] is False
        assert config["log_level"] == "info"  # Default INFO lowercased
        assert config["workers"] == 1

    @patch("cc_orchestrator.web.server.load_config")
    def test_get_server_config_from_config_object(self, mock_load_config):
        """Test server configuration with values from config object."""
        # Mock config with web-specific attributes
        mock_config = Mock()
        mock_config.web_host = "192.168.1.100"
        mock_config.web_port = 9000
        mock_config.log_level = "DEBUG"
        mock_load_config.return_value = mock_config

        config = get_server_config()

        # Check config object values
        assert config["host"] == "192.168.1.100"
        assert config["port"] == 9000
        assert config["log_level"] == "debug"  # Lowercased
        assert config["reload"] is False  # Still default
        assert config["workers"] == 1  # Still default

    @patch("cc_orchestrator.web.server.load_config")
    def test_get_server_config_environment_overrides(self, mock_load_config):
        """Test server configuration with environment variable overrides."""
        # Mock config with default values
        mock_config = Mock()
        mock_load_config.return_value = mock_config

        # Set environment variables
        env_vars = {
            "CC_WEB_HOST": "0.0.0.0",
            "CC_WEB_PORT": "3000",
            "CC_WEB_RELOAD": "true",
            "CC_WEB_LOG_LEVEL": "WARNING",
            "CC_WEB_WORKERS": "4",
        }

        with patch.dict(os.environ, env_vars):
            config = get_server_config()

        # Check environment overrides
        assert config["host"] == "0.0.0.0"
        assert config["port"] == 3000
        assert config["reload"] is True
        assert config["log_level"] == "WARNING"
        assert config["workers"] == 4

    @patch("cc_orchestrator.web.server.load_config")
    def test_get_server_config_reload_boolean_variations(self, mock_load_config):
        """Test different boolean values for reload environment variable."""
        mock_config = Mock()
        mock_load_config.return_value = mock_config

        # Test different truthy values
        truthy_values = ["true", "1", "yes", "TRUE", "True", "YES"]
        for value in truthy_values:
            with patch.dict(os.environ, {"CC_WEB_RELOAD": value}):
                config = get_server_config()
                assert config["reload"] is True, f"Failed for value: {value}"

        # Test falsy values
        falsy_values = ["false", "0", "no", "FALSE", "False", "NO", "other"]
        for value in falsy_values:
            with patch.dict(os.environ, {"CC_WEB_RELOAD": value}):
                config = get_server_config()
                assert config["reload"] is False, f"Failed for value: {value}"

    @patch("cc_orchestrator.web.server.load_config")
    def test_get_server_config_partial_environment_overrides(self, mock_load_config):
        """Test server configuration with partial environment overrides."""
        # Mock config with some values
        mock_config = Mock()
        mock_config.web_host = "localhost"
        mock_config.web_port = 5000
        mock_config.log_level = "ERROR"
        mock_load_config.return_value = mock_config

        # Override only some values with environment variables
        env_vars = {
            "CC_WEB_PORT": "8888",
            "CC_WEB_RELOAD": "yes",
        }

        with patch.dict(os.environ, env_vars):
            config = get_server_config()

        # Check mixed values
        assert config["host"] == "localhost"  # From config
        assert config["port"] == 8888  # From environment
        assert config["reload"] is True  # From environment
        assert config["log_level"] == "error"  # From config (lowercased)
        assert config["workers"] == 1  # Default


class TestServerStartup:
    """Test server startup and parameter handling."""

    @patch("cc_orchestrator.web.server.uvicorn.run")
    @patch("cc_orchestrator.web.server.get_server_config")
    @patch("cc_orchestrator.web.server.logger")
    def test_run_server_with_defaults(self, mock_logger, mock_get_config, mock_uvicorn):
        """Test running server with default configuration."""
        # Mock configuration
        mock_config = {
            "host": "127.0.0.1",
            "port": 8080,
            "reload": False,
            "log_level": "info",
            "workers": 1,
        }
        mock_get_config.return_value = mock_config

        # Run server
        run_server()

        # Verify logging
        mock_logger.info.assert_called_once_with(
            "Starting CC-Orchestrator web server",
            host="127.0.0.1",
            port=8080,
            reload=False,
            log_level="info",
            workers=1,
        )

        # Verify uvicorn.run called with correct parameters
        mock_uvicorn.assert_called_once()
        call_args = mock_uvicorn.call_args[1]
        assert call_args["host"] == "127.0.0.1"
        assert call_args["port"] == 8080
        assert call_args["reload"] is False
        assert call_args["log_level"] == "info"
        assert call_args["workers"] == 1  # Not reload mode
        assert call_args["access_log"] is True

    @patch("cc_orchestrator.web.server.uvicorn.run")
    @patch("cc_orchestrator.web.server.get_server_config")
    @patch("cc_orchestrator.web.server.logger")
    def test_run_server_with_parameter_overrides(
        self, mock_logger, mock_get_config, mock_uvicorn
    ):
        """Test running server with parameter overrides."""
        # Mock configuration
        mock_config = {
            "host": "127.0.0.1",
            "port": 8080,
            "reload": False,
            "log_level": "info",
            "workers": 4,
        }
        mock_get_config.return_value = mock_config

        # Run server with overrides
        run_server(host="0.0.0.0", port=3000, reload=True, log_level="debug")

        # Verify logging shows overridden values
        mock_logger.info.assert_called_once_with(
            "Starting CC-Orchestrator web server",
            host="0.0.0.0",
            port=3000,
            reload=True,
            log_level="debug",
            workers=4,
        )

        # Verify uvicorn.run called with overridden parameters
        mock_uvicorn.assert_called_once()
        call_args = mock_uvicorn.call_args[1]
        assert call_args["host"] == "0.0.0.0"
        assert call_args["port"] == 3000
        assert call_args["reload"] is True
        assert call_args["log_level"] == "debug"
        assert call_args["workers"] == 1  # Forced to 1 because reload=True

    @patch("cc_orchestrator.web.server.uvicorn.run")
    @patch("cc_orchestrator.web.server.get_server_config")
    @patch("cc_orchestrator.web.server.logger")
    def test_run_server_reload_forces_single_worker(
        self, mock_logger, mock_get_config, mock_uvicorn
    ):
        """Test that reload mode forces single worker."""
        # Mock configuration with multiple workers
        mock_config = {
            "host": "127.0.0.1",
            "port": 8080,
            "reload": True,  # Reload enabled
            "log_level": "info",
            "workers": 4,  # Multiple workers configured
        }
        mock_get_config.return_value = mock_config

        # Run server
        run_server()

        # Verify uvicorn.run forced to 1 worker due to reload
        mock_uvicorn.assert_called_once()
        call_args = mock_uvicorn.call_args[1]
        assert call_args["reload"] is True
        assert call_args["workers"] == 1  # Forced to 1 despite config

    @patch("cc_orchestrator.web.server.uvicorn.run")
    @patch("cc_orchestrator.web.server.get_server_config")
    def test_run_server_partial_parameter_overrides(self, mock_get_config, mock_uvicorn):
        """Test running server with partial parameter overrides."""
        # Mock configuration
        mock_config = {
            "host": "192.168.1.100",
            "port": 9000,
            "reload": False,
            "log_level": "warning",
            "workers": 2,
        }
        mock_get_config.return_value = mock_config

        # Run server with only some overrides
        run_server(port=7777, reload=True)  # Only override port and reload

        # Verify uvicorn.run called with mixed values
        mock_uvicorn.assert_called_once()
        call_args = mock_uvicorn.call_args[1]
        assert call_args["host"] == "192.168.1.100"  # From config
        assert call_args["port"] == 7777  # Overridden
        assert call_args["reload"] is True  # Overridden
        assert call_args["log_level"] == "warning"  # From config
        assert call_args["workers"] == 1  # Forced to 1 due to reload=True

    @patch("cc_orchestrator.web.server.run_server")
    def test_main_calls_run_server(self, mock_run_server):
        """Test main function calls run_server with no arguments."""
        main()
        mock_run_server.assert_called_once_with()


class TestServerIntegration:
    """Test server integration and edge cases."""

    @patch("cc_orchestrator.web.server.load_config")
    def test_get_server_config_missing_attributes(self, mock_load_config):
        """Test server configuration when config object lacks web attributes."""
        # Mock config without any web-specific attributes
        mock_config = Mock()
        # Remove all attributes using spec to simulate missing attributes
        mock_config = Mock(spec=[])
        mock_load_config.return_value = mock_config

        config = get_server_config()

        # Should use all defaults since config has no web attributes
        assert config["host"] == "127.0.0.1"
        assert config["port"] == 8080
        assert config["reload"] is False
        assert config["log_level"] == "info"  # Default INFO lowercased
        assert config["workers"] == 1

    @patch("cc_orchestrator.web.server.load_config")
    def test_environment_variable_type_conversion(self, mock_load_config):
        """Test proper type conversion for environment variables."""
        mock_config = Mock()
        mock_load_config.return_value = mock_config

        # Test integer conversion
        with patch.dict(os.environ, {"CC_WEB_PORT": "3000", "CC_WEB_WORKERS": "8"}):
            config = get_server_config()
            assert isinstance(config["port"], int)
            assert isinstance(config["workers"], int)
            assert config["port"] == 3000
            assert config["workers"] == 8

    @patch("cc_orchestrator.web.server.uvicorn")
    @patch("cc_orchestrator.web.server.get_server_config")
    def test_uvicorn_import_and_app_reference(self, mock_get_config, mock_uvicorn):
        """Test that uvicorn is properly imported and app is referenced."""
        # Mock configuration
        mock_config = {
            "host": "localhost",
            "port": 8080,
            "reload": False,
            "log_level": "info",
            "workers": 1,
        }
        mock_get_config.return_value = mock_config

        # Import the app to verify it's importable
        from cc_orchestrator.web.server import app

        # Run server
        run_server()

        # Verify uvicorn.run was called with the app
        mock_uvicorn.run.assert_called_once()
        args = mock_uvicorn.run.call_args
        assert args[0][0] == app  # First positional argument should be the app


class TestServerConfigurationEdgeCases:
    """Test edge cases and error handling in server configuration."""

    @patch("cc_orchestrator.web.server.load_config")
    def test_config_without_optional_attributes(self, mock_load_config):
        """Test configuration when config object doesn't have optional web attributes."""
        # Mock config without optional web attributes (using empty spec)
        mock_config = Mock(spec=[])  # No attributes defined
        mock_load_config.return_value = mock_config

        config = get_server_config()

        # Should use defaults when attributes are missing entirely
        assert config["host"] == "127.0.0.1"  # Uses default
        assert config["port"] == 8080  # Uses default
        assert config["log_level"] == "info"  # Uses default INFO -> info
        assert config["reload"] is False  # Always default
        assert config["workers"] == 1  # Always default

    def test_server_module_imports(self):
        """Test that all required modules are properly imported."""
        # Test that we can import all required components
        from cc_orchestrator.web.server import (
            app,
            get_server_config,
            main,
            run_server,
        )

        # Verify functions exist and are callable
        assert callable(get_server_config)
        assert callable(run_server)
        assert callable(main)

        # Verify app is importable
        assert app is not None

