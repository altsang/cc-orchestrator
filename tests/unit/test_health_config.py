"""Tests for health monitoring configuration module."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from cc_orchestrator.health.config import (
    AlertConfig,
    HealthCheckConfig,
    HealthMonitoringConfig,
    HealthMonitoringSettings,
    MetricsConfig,
    ProcessHealthCheckConfig,
    RecoveryConfig,
    ResponseHealthCheckConfig,
    TmuxHealthCheckConfig,
    WorkspaceHealthCheckConfig,
    get_health_monitoring_settings,
    load_health_monitoring_config,
    save_health_monitoring_config,
    set_health_monitoring_settings,
)


class TestHealthCheckConfig:
    """Test HealthCheckConfig base class."""

    def test_default_values(self):
        """Test default configuration values."""
        config = HealthCheckConfig()

        assert config.enabled is True
        assert config.timeout == 30.0

    def test_custom_values(self):
        """Test custom configuration values."""
        config = HealthCheckConfig(enabled=False, timeout=60.0)

        assert config.enabled is False
        assert config.timeout == 60.0

    def test_timeout_validation(self):
        """Test timeout validation constraints."""
        # Valid timeout
        config = HealthCheckConfig(timeout=120.0)
        assert config.timeout == 120.0

        # Invalid timeout (too small)
        with pytest.raises(ValidationError) as exc_info:
            HealthCheckConfig(timeout=0)
        assert "greater than 0" in str(exc_info.value)

        # Invalid timeout (too large)
        with pytest.raises(ValidationError) as exc_info:
            HealthCheckConfig(timeout=400.0)
        assert "less than or equal to 300" in str(exc_info.value)


class TestProcessHealthCheckConfig:
    """Test ProcessHealthCheckConfig class."""

    def test_default_values(self):
        """Test default process health check values."""
        config = ProcessHealthCheckConfig()

        assert config.enabled is True
        assert config.timeout == 30.0
        assert config.cpu_threshold == 90.0
        assert config.memory_threshold_mb == 2048.0

    def test_custom_values(self):
        """Test custom process health check values."""
        config = ProcessHealthCheckConfig(
            cpu_threshold=80.0, memory_threshold_mb=1024.0
        )

        assert config.cpu_threshold == 80.0
        assert config.memory_threshold_mb == 1024.0

    def test_cpu_threshold_validation(self):
        """Test CPU threshold validation."""
        # Valid threshold
        config = ProcessHealthCheckConfig(cpu_threshold=75.5)
        assert config.cpu_threshold == 75.5

        # Invalid threshold (negative)
        with pytest.raises(ValidationError) as exc_info:
            ProcessHealthCheckConfig(cpu_threshold=-5.0)
        assert "greater than or equal to 0" in str(exc_info.value)

        # Invalid threshold (too large)
        with pytest.raises(ValidationError) as exc_info:
            ProcessHealthCheckConfig(cpu_threshold=105.0)
        assert "less than or equal to 100" in str(exc_info.value)

    def test_memory_threshold_validation(self):
        """Test memory threshold validation."""
        # Valid threshold
        config = ProcessHealthCheckConfig(memory_threshold_mb=512.0)
        assert config.memory_threshold_mb == 512.0

        # Invalid threshold (zero or negative)
        with pytest.raises(ValidationError) as exc_info:
            ProcessHealthCheckConfig(memory_threshold_mb=0)
        assert "greater than 0" in str(exc_info.value)


class TestTmuxHealthCheckConfig:
    """Test TmuxHealthCheckConfig class."""

    def test_default_values(self):
        """Test default tmux health check values."""
        config = TmuxHealthCheckConfig()

        assert config.enabled is True
        assert config.timeout == 10.0

    def test_timeout_override(self):
        """Test tmux-specific timeout validation."""
        config = TmuxHealthCheckConfig(timeout=30.0)
        assert config.timeout == 30.0

        # Invalid timeout (too large for tmux)
        with pytest.raises(ValidationError) as exc_info:
            TmuxHealthCheckConfig(timeout=120.0)
        assert "less than or equal to 60" in str(exc_info.value)


class TestWorkspaceHealthCheckConfig:
    """Test WorkspaceHealthCheckConfig class."""

    def test_default_values(self):
        """Test default workspace health check values."""
        config = WorkspaceHealthCheckConfig()

        assert config.enabled is True
        assert config.timeout == 5.0
        assert config.min_free_space_gb == 1.0

    def test_custom_values(self):
        """Test custom workspace health check values."""
        config = WorkspaceHealthCheckConfig(timeout=15.0, min_free_space_gb=5.0)

        assert config.timeout == 15.0
        assert config.min_free_space_gb == 5.0

    def test_free_space_validation(self):
        """Test free space validation."""
        # Valid free space
        config = WorkspaceHealthCheckConfig(min_free_space_gb=0.5)
        assert config.min_free_space_gb == 0.5

        # Invalid free space (zero or negative)
        with pytest.raises(ValidationError) as exc_info:
            WorkspaceHealthCheckConfig(min_free_space_gb=0)
        assert "greater than 0" in str(exc_info.value)


class TestResponseHealthCheckConfig:
    """Test ResponseHealthCheckConfig class."""

    def test_default_values(self):
        """Test default response health check values."""
        config = ResponseHealthCheckConfig()

        assert config.enabled is False  # Disabled by default
        assert config.timeout == 30.0

    def test_timeout_validation(self):
        """Test response check timeout validation."""
        config = ResponseHealthCheckConfig(timeout=60.0)
        assert config.timeout == 60.0

        # Invalid timeout (too large)
        with pytest.raises(ValidationError) as exc_info:
            ResponseHealthCheckConfig(timeout=150.0)
        assert "less than or equal to 120" in str(exc_info.value)


class TestRecoveryConfig:
    """Test RecoveryConfig class."""

    def test_default_values(self):
        """Test default recovery configuration values."""
        config = RecoveryConfig()

        assert config.enabled is True
        assert config.max_attempts == 3
        assert config.base_delay == 60.0
        assert config.max_delay == 3600.0
        assert config.backoff_multiplier == 2.0
        assert config.time_window_hours == 1

    def test_custom_values(self):
        """Test custom recovery configuration values."""
        config = RecoveryConfig(
            max_attempts=5,
            base_delay=30.0,
            max_delay=1800.0,
            backoff_multiplier=1.5,
            time_window_hours=2,
        )

        assert config.max_attempts == 5
        assert config.base_delay == 30.0
        assert config.max_delay == 1800.0
        assert config.backoff_multiplier == 1.5
        assert config.time_window_hours == 2

    def test_validation_constraints(self):
        """Test recovery config validation constraints."""
        # Valid config
        config = RecoveryConfig(max_attempts=1, backoff_multiplier=1.1)
        assert config.max_attempts == 1
        assert config.backoff_multiplier == 1.1

        # Invalid max_attempts (too small)
        with pytest.raises(ValidationError) as exc_info:
            RecoveryConfig(max_attempts=0)
        assert "greater than or equal to 1" in str(exc_info.value)

        # Invalid max_attempts (too large)
        with pytest.raises(ValidationError) as exc_info:
            RecoveryConfig(max_attempts=15)
        assert "less than or equal to 10" in str(exc_info.value)

        # Invalid backoff_multiplier (too small)
        with pytest.raises(ValidationError) as exc_info:
            RecoveryConfig(backoff_multiplier=0.5)
        assert "greater than 1" in str(exc_info.value)

        # Invalid backoff_multiplier (too large)
        with pytest.raises(ValidationError) as exc_info:
            RecoveryConfig(backoff_multiplier=6.0)
        assert "less than or equal to 5" in str(exc_info.value)


class TestAlertConfig:
    """Test AlertConfig class."""

    def test_default_values(self):
        """Test default alert configuration values."""
        config = AlertConfig()

        assert config.enabled is True
        assert config.cooldown_minutes == 5
        assert config.max_history == 1000
        assert config.log_alerts is True
        assert config.file_alerts is False
        assert config.file_path is None
        assert config.webhook_alerts is False
        assert config.webhook_url is None
        assert config.webhook_timeout == 30.0
        assert config.email_alerts is False
        assert config.email_config == {}

    def test_custom_values(self):
        """Test custom alert configuration values."""
        config = AlertConfig(
            cooldown_minutes=10,
            max_history=500,
            log_alerts=False,
            file_alerts=True,
            file_path="/var/log/alerts.log",
            webhook_alerts=True,
            webhook_url="https://hooks.example.com/alerts",
            email_alerts=True,
            email_config={"smtp_host": "smtp.example.com"},
        )

        assert config.cooldown_minutes == 10
        assert config.max_history == 500
        assert config.log_alerts is False
        assert config.file_alerts is True
        assert config.file_path == "/var/log/alerts.log"
        assert config.webhook_alerts is True
        assert config.webhook_url == "https://hooks.example.com/alerts"
        assert config.email_alerts is True
        assert config.email_config["smtp_host"] == "smtp.example.com"

    def test_file_path_validation(self):
        """Test file path validation when file_alerts is enabled."""
        # Valid configuration with file_alerts disabled
        config = AlertConfig(file_alerts=False, file_path=None)
        assert config.file_alerts is False

        # Valid configuration with file_alerts enabled and path provided
        config = AlertConfig(file_alerts=True, file_path="/path/to/alerts.log")
        assert config.file_alerts is True
        assert config.file_path == "/path/to/alerts.log"

        # Invalid configuration: file_alerts enabled but no path
        with pytest.raises(ValidationError) as exc_info:
            AlertConfig(file_alerts=True, file_path=None)
        assert "file_path required when file_alerts is enabled" in str(exc_info.value)

    def test_webhook_url_validation(self):
        """Test webhook URL validation when webhook_alerts is enabled."""
        # Valid configuration with webhook_alerts disabled
        config = AlertConfig(webhook_alerts=False, webhook_url=None)
        assert config.webhook_alerts is False

        # Valid configuration with webhook_alerts enabled and URL provided
        config = AlertConfig(
            webhook_alerts=True, webhook_url="https://hooks.example.com/alerts"
        )
        assert config.webhook_alerts is True
        assert config.webhook_url == "https://hooks.example.com/alerts"

        # Invalid configuration: webhook_alerts enabled but no URL
        with pytest.raises(ValidationError) as exc_info:
            AlertConfig(webhook_alerts=True, webhook_url=None)
        assert "webhook_url required when webhook_alerts is enabled" in str(
            exc_info.value
        )

    def test_validation_constraints(self):
        """Test alert config validation constraints."""
        # Valid cooldown
        config = AlertConfig(cooldown_minutes=30)
        assert config.cooldown_minutes == 30

        # Invalid cooldown (too small)
        with pytest.raises(ValidationError) as exc_info:
            AlertConfig(cooldown_minutes=0)
        assert "greater than or equal to 1" in str(exc_info.value)

        # Invalid cooldown (too large)
        with pytest.raises(ValidationError) as exc_info:
            AlertConfig(cooldown_minutes=120)
        assert "less than or equal to 60" in str(exc_info.value)


class TestMetricsConfig:
    """Test MetricsConfig class."""

    def test_default_values(self):
        """Test default metrics configuration values."""
        config = MetricsConfig()

        assert config.enabled is True
        assert config.collection_interval == 30.0
        assert config.max_samples == 1000

    def test_custom_values(self):
        """Test custom metrics configuration values."""
        config = MetricsConfig(enabled=False, collection_interval=60.0, max_samples=500)

        assert config.enabled is False
        assert config.collection_interval == 60.0
        assert config.max_samples == 500

    def test_validation_constraints(self):
        """Test metrics config validation constraints."""
        # Valid values
        config = MetricsConfig(collection_interval=120.0, max_samples=200)
        assert config.collection_interval == 120.0
        assert config.max_samples == 200

        # Invalid collection_interval (too large)
        with pytest.raises(ValidationError) as exc_info:
            MetricsConfig(collection_interval=400.0)
        assert "less than or equal to 300" in str(exc_info.value)

        # Invalid max_samples (too small)
        with pytest.raises(ValidationError) as exc_info:
            MetricsConfig(max_samples=50)
        assert "greater than or equal to 100" in str(exc_info.value)


class TestHealthMonitoringConfig:
    """Test HealthMonitoringConfig main class."""

    def test_default_configuration(self):
        """Test default health monitoring configuration."""
        config = HealthMonitoringConfig()

        assert config.enabled is True
        assert config.check_interval == 60.0
        assert isinstance(config.process_check, ProcessHealthCheckConfig)
        assert isinstance(config.tmux_check, TmuxHealthCheckConfig)
        assert isinstance(config.workspace_check, WorkspaceHealthCheckConfig)
        assert isinstance(config.response_check, ResponseHealthCheckConfig)
        assert isinstance(config.recovery, RecoveryConfig)
        assert isinstance(config.alerts, AlertConfig)
        assert isinstance(config.metrics, MetricsConfig)

    def test_custom_configuration(self):
        """Test custom health monitoring configuration."""
        config = HealthMonitoringConfig(
            enabled=False,
            check_interval=120.0,
            process_check=ProcessHealthCheckConfig(cpu_threshold=80.0),
            recovery=RecoveryConfig(max_attempts=5),
            alerts=AlertConfig(cooldown_minutes=10),
        )

        assert config.enabled is False
        assert config.check_interval == 120.0
        assert config.process_check.cpu_threshold == 80.0
        assert config.recovery.max_attempts == 5
        assert config.alerts.cooldown_minutes == 10

    def test_check_interval_validation(self):
        """Test check interval validation."""
        # Valid interval
        config = HealthMonitoringConfig(check_interval=300.0)
        assert config.check_interval == 300.0

        # Invalid interval (too large)
        with pytest.raises(ValidationError) as exc_info:
            HealthMonitoringConfig(check_interval=700.0)
        assert "less than or equal to 600" in str(exc_info.value)

    def test_extra_fields_forbidden(self):
        """Test that extra fields are forbidden."""
        with pytest.raises(ValidationError) as exc_info:
            HealthMonitoringConfig(unknown_field="value")
        assert "extra" in str(exc_info.value).lower() and "not permitted" in str(
            exc_info.value
        )


class TestHealthMonitoringSettings:
    """Test HealthMonitoringSettings class."""

    @pytest.fixture
    def settings(self):
        """Create HealthMonitoringSettings instance."""
        config = HealthMonitoringConfig(check_interval=30.0)
        return HealthMonitoringSettings(
            config=config, config_file_path=Path("/etc/config.yaml")
        )

    def test_initialization(self, settings):
        """Test settings initialization."""
        assert isinstance(settings.config, HealthMonitoringConfig)
        assert settings.config_file_path == Path("/etc/config.yaml")
        assert settings._instance_overrides == {}

    def test_get_check_interval_global(self, settings):
        """Test getting global check interval."""
        interval = settings.get_check_interval()
        assert interval == 30.0

    def test_get_check_interval_instance_override(self, settings):
        """Test getting check interval with instance override."""
        settings._instance_overrides["test-instance"] = {"check_interval": 60.0}

        interval = settings.get_check_interval("test-instance")
        assert interval == 60.0

        # Non-overridden instance should get global value
        interval = settings.get_check_interval("other-instance")
        assert interval == 30.0

    def test_get_recovery_config_global(self, settings):
        """Test getting global recovery config."""
        recovery_config = settings.get_recovery_config()
        assert isinstance(recovery_config, RecoveryConfig)
        assert recovery_config.max_attempts == 3  # Default value

    def test_get_recovery_config_instance_override(self, settings):
        """Test getting recovery config with instance override."""
        settings._instance_overrides["test-instance"] = {
            "recovery": {"max_attempts": 5, "base_delay": 120.0}
        }

        recovery_config = settings.get_recovery_config("test-instance")
        assert recovery_config.max_attempts == 5
        assert recovery_config.base_delay == 120.0
        assert recovery_config.backoff_multiplier == 2.0  # Unchanged from global

    def test_set_instance_override_simple(self, settings):
        """Test setting simple instance override."""
        with patch("cc_orchestrator.health.config.logger") as mock_logger:
            settings.set_instance_override("test-instance", "check_interval", 45.0)

        assert settings._instance_overrides["test-instance"]["check_interval"] == 45.0
        mock_logger.info.assert_called_once()

    def test_set_instance_override_nested(self, settings):
        """Test setting nested instance override."""
        with patch("cc_orchestrator.health.config.logger"):
            settings.set_instance_override("test-instance", "recovery.max_attempts", 7)

        assert (
            settings._instance_overrides["test-instance"]["recovery"]["max_attempts"]
            == 7
        )

    def test_remove_instance_override(self, settings):
        """Test removing instance override."""
        # Set an override first
        settings._instance_overrides["test-instance"] = {"check_interval": 45.0}

        with patch("cc_orchestrator.health.config.logger") as mock_logger:
            settings.remove_instance_override("test-instance", "check_interval")

        assert "check_interval" not in settings._instance_overrides["test-instance"]
        mock_logger.info.assert_called_once()

    def test_remove_instance_override_not_found(self, settings):
        """Test removing non-existent instance override."""
        with patch("cc_orchestrator.health.config.logger") as mock_logger:
            settings.remove_instance_override("test-instance", "non_existent")

        mock_logger.warning.assert_called_once()

    def test_clear_instance_overrides(self, settings):
        """Test clearing all instance overrides."""
        settings._instance_overrides["test-instance"] = {
            "check_interval": 45.0,
            "recovery": {"max_attempts": 5},
        }

        with patch("cc_orchestrator.health.config.logger") as mock_logger:
            settings.clear_instance_overrides("test-instance")

        assert "test-instance" not in settings._instance_overrides
        mock_logger.info.assert_called_once()

    def test_clear_instance_overrides_not_found(self, settings):
        """Test clearing overrides for non-existent instance."""
        # Should not raise error
        settings.clear_instance_overrides("non-existent")


class TestConfigLoading:
    """Test configuration loading and saving functions."""

    def test_load_health_monitoring_config_no_file(self):
        """Test loading config when no file exists."""
        with patch("cc_orchestrator.health.config.logger") as mock_logger:
            settings = load_health_monitoring_config(Path("/nonexistent.yaml"))

        assert isinstance(settings, HealthMonitoringSettings)
        assert isinstance(settings.config, HealthMonitoringConfig)
        assert settings.config_file_path == Path("/nonexistent.yaml")
        mock_logger.info.assert_called_with(
            "Using default health monitoring configuration"
        )

    def test_load_health_monitoring_config_valid_file(self):
        """Test loading config from valid YAML file."""
        config_data = {
            "health_monitoring": {
                "enabled": False,
                "check_interval": 120.0,
                "process_check": {"cpu_threshold": 85.0},
                "alerts": {"cooldown_minutes": 10},
            }
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            import yaml

            yaml.dump(config_data, f)
            config_file = Path(f.name)

        try:
            with patch("cc_orchestrator.health.config.logger") as mock_logger:
                settings = load_health_monitoring_config(config_file)

            assert settings.config.enabled is False
            assert settings.config.check_interval == 120.0
            assert settings.config.process_check.cpu_threshold == 85.0
            assert settings.config.alerts.cooldown_minutes == 10
            mock_logger.info.assert_called_with(
                "Health monitoring config loaded", config_file=str(config_file)
            )
        finally:
            config_file.unlink()

    def test_load_health_monitoring_config_invalid_yaml(self):
        """Test loading config from invalid YAML file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("invalid: yaml: content: [")
            config_file = Path(f.name)

        try:
            with patch("cc_orchestrator.health.config.logger") as mock_logger:
                settings = load_health_monitoring_config(config_file)

            # Should fall back to defaults
            assert isinstance(settings.config, HealthMonitoringConfig)
            assert settings.config.enabled is True  # Default value
            mock_logger.error.assert_called_once()
            call_args = mock_logger.error.call_args
            assert (
                "Failed to load health monitoring config, using defaults"
                in call_args[0]
            )
        finally:
            config_file.unlink()

    def test_load_health_monitoring_config_no_health_section(self):
        """Test loading config from YAML without health_monitoring section."""
        config_data = {"other_section": {"setting": "value"}}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            import yaml

            yaml.dump(config_data, f)
            config_file = Path(f.name)

        try:
            settings = load_health_monitoring_config(config_file)

            # Should use defaults when section is missing
            assert isinstance(settings.config, HealthMonitoringConfig)
            assert settings.config.enabled is True  # Default value
        finally:
            config_file.unlink()

    def test_save_health_monitoring_config_new_file(self):
        """Test saving config to new file."""
        config = HealthMonitoringConfig(
            enabled=False, check_interval=90.0, alerts=AlertConfig(cooldown_minutes=15)
        )
        settings = HealthMonitoringSettings(config=config)

        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "new_config.yaml"

            with patch("cc_orchestrator.health.config.logger") as mock_logger:
                result = save_health_monitoring_config(settings, config_file)

            assert result is True
            assert config_file.exists()
            mock_logger.info.assert_called_with(
                "Health monitoring config saved", config_file=str(config_file)
            )

            # Verify saved content
            import yaml

            with open(config_file) as f:
                saved_data = yaml.safe_load(f)

            assert saved_data["health_monitoring"]["enabled"] is False
            assert saved_data["health_monitoring"]["check_interval"] == 90.0
            assert saved_data["health_monitoring"]["alerts"]["cooldown_minutes"] == 15

    def test_save_health_monitoring_config_existing_file(self):
        """Test saving config to existing file with other sections."""
        existing_data = {"other_section": {"setting": "value"}}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            import yaml

            yaml.dump(existing_data, f)
            config_file = Path(f.name)

        try:
            config = HealthMonitoringConfig(check_interval=45.0)
            settings = HealthMonitoringSettings(config=config)

            result = save_health_monitoring_config(settings, config_file)

            assert result is True

            # Verify existing sections are preserved
            with open(config_file) as f:
                saved_data = yaml.safe_load(f)

            assert saved_data["other_section"]["setting"] == "value"
            assert saved_data["health_monitoring"]["check_interval"] == 45.0
        finally:
            config_file.unlink()

    def test_save_health_monitoring_config_error(self):
        """Test saving config with error."""
        config = HealthMonitoringConfig()
        settings = HealthMonitoringSettings(config=config)

        # Use invalid path to force error
        config_file = Path("/invalid/path/config.yaml")

        with patch("cc_orchestrator.health.config.logger") as mock_logger:
            result = save_health_monitoring_config(settings, config_file)

        assert result is False
        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args
        assert "Failed to save health monitoring config" in call_args[0]


class TestGlobalSettings:
    """Test global settings management."""

    def test_get_health_monitoring_settings_initial(self):
        """Test getting global settings initially."""
        # Reset global state
        import cc_orchestrator.health.config

        cc_orchestrator.health.config._health_monitoring_settings = None

        settings = get_health_monitoring_settings()

        assert isinstance(settings, HealthMonitoringSettings)
        assert isinstance(settings.config, HealthMonitoringConfig)

    def test_set_health_monitoring_settings(self):
        """Test setting global settings."""
        custom_config = HealthMonitoringConfig(check_interval=45.0)
        custom_settings = HealthMonitoringSettings(config=custom_config)

        set_health_monitoring_settings(custom_settings)

        retrieved_settings = get_health_monitoring_settings()
        assert retrieved_settings.config.check_interval == 45.0

    def test_get_health_monitoring_settings_cached(self):
        """Test that global settings are cached."""
        # Set custom settings
        custom_config = HealthMonitoringConfig(check_interval=75.0)
        custom_settings = HealthMonitoringSettings(config=custom_config)
        set_health_monitoring_settings(custom_settings)

        # Get settings twice
        settings1 = get_health_monitoring_settings()
        settings2 = get_health_monitoring_settings()

        # Should be the same instance (cached)
        assert settings1 is settings2
        assert settings1.config.check_interval == 75.0
