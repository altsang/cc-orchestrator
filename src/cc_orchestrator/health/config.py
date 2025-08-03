"""Configuration management for health monitoring system."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator

from ..utils.logging import LogContext, get_logger

logger = get_logger(__name__, LogContext.HEALTH)


class HealthCheckConfig(BaseModel):
    """Configuration for individual health checks."""

    enabled: bool = True
    timeout: float = Field(default=30.0, gt=0, le=300)  # 5 minutes max


class ProcessHealthCheckConfig(HealthCheckConfig):
    """Configuration for process health checks."""

    cpu_threshold: float = Field(default=90.0, ge=0, le=100)
    memory_threshold_mb: float = Field(default=2048.0, gt=0)  # 2GB


class TmuxHealthCheckConfig(HealthCheckConfig):
    """Configuration for tmux health checks."""

    timeout: float = Field(default=10.0, gt=0, le=60)


class WorkspaceHealthCheckConfig(HealthCheckConfig):
    """Configuration for workspace health checks."""

    timeout: float = Field(default=5.0, gt=0, le=30)
    min_free_space_gb: float = Field(default=1.0, gt=0)


class ResponseHealthCheckConfig(HealthCheckConfig):
    """Configuration for response health checks."""

    timeout: float = Field(default=30.0, gt=0, le=120)
    enabled: bool = False  # Disabled by default as it's intrusive


class RecoveryConfig(BaseModel):
    """Configuration for recovery management."""

    enabled: bool = True
    max_attempts: int = Field(default=3, ge=1, le=10)
    base_delay: float = Field(default=60.0, gt=0)  # seconds
    max_delay: float = Field(default=3600.0, gt=0)  # 1 hour max
    backoff_multiplier: float = Field(default=2.0, gt=1.0, le=5.0)
    time_window_hours: int = Field(default=1, ge=1, le=24)


class AlertConfig(BaseModel):
    """Configuration for alert management."""

    enabled: bool = True
    cooldown_minutes: int = Field(default=5, ge=1, le=60)
    max_history: int = Field(default=1000, ge=100, le=10000)

    # Handler configurations
    log_alerts: bool = True
    file_alerts: bool = False
    file_path: str | None = None
    webhook_alerts: bool = False
    webhook_url: str | None = None
    webhook_timeout: float = Field(default=30.0, gt=0, le=120)
    email_alerts: bool = False
    email_config: dict[str, Any] = Field(default_factory=dict)

    @field_validator("file_path")
    @classmethod
    def validate_file_path(cls, v, info):
        if info.data.get("file_alerts") and not v:
            raise ValueError("file_path required when file_alerts is enabled")
        return v

    @field_validator("webhook_url")
    @classmethod
    def validate_webhook_url(cls, v, info):
        if info.data.get("webhook_alerts") and not v:
            raise ValueError("webhook_url required when webhook_alerts is enabled")
        return v


class MetricsConfig(BaseModel):
    """Configuration for metrics collection."""

    enabled: bool = True
    collection_interval: float = Field(default=30.0, gt=0, le=300)  # 5 minutes max
    max_samples: int = Field(default=1000, ge=100, le=10000)


class HealthMonitoringConfig(BaseModel):
    """Main configuration for health monitoring system."""

    # Global settings
    enabled: bool = True
    check_interval: float = Field(default=60.0, gt=0, le=600)  # 10 minutes max

    # Health check configurations
    process_check: ProcessHealthCheckConfig = Field(
        default_factory=ProcessHealthCheckConfig
    )
    tmux_check: TmuxHealthCheckConfig = Field(default_factory=TmuxHealthCheckConfig)
    workspace_check: WorkspaceHealthCheckConfig = Field(
        default_factory=WorkspaceHealthCheckConfig
    )
    response_check: ResponseHealthCheckConfig = Field(
        default_factory=ResponseHealthCheckConfig
    )

    # Recovery configuration
    recovery: RecoveryConfig = Field(default_factory=RecoveryConfig)

    # Alert configuration
    alerts: AlertConfig = Field(default_factory=AlertConfig)

    # Metrics configuration
    metrics: MetricsConfig = Field(default_factory=MetricsConfig)

    class Config:
        extra = "forbid"  # Don't allow extra fields


@dataclass
class HealthMonitoringSettings:
    """Runtime settings for health monitoring."""

    config: HealthMonitoringConfig
    config_file_path: Path | None = None
    _instance_overrides: dict[str, dict[str, Any]] = field(default_factory=dict)

    def get_check_interval(self, instance_id: str | None = None) -> float:
        """Get health check interval for an instance.

        Args:
            instance_id: Instance identifier (uses global if None)

        Returns:
            Check interval in seconds
        """
        if instance_id and instance_id in self._instance_overrides:
            return self._instance_overrides[instance_id].get(
                "check_interval", self.config.check_interval
            )
        return self.config.check_interval

    def get_recovery_config(self, instance_id: str | None = None) -> RecoveryConfig:
        """Get recovery configuration for an instance.

        Args:
            instance_id: Instance identifier (uses global if None)

        Returns:
            Recovery configuration
        """
        if instance_id and instance_id in self._instance_overrides:
            overrides = self._instance_overrides[instance_id].get("recovery", {})
            if overrides:
                # Create new config with overrides
                config_dict = self.config.recovery.dict()
                config_dict.update(overrides)
                return RecoveryConfig(**config_dict)

        return self.config.recovery

    def set_instance_override(
        self, instance_id: str, setting_path: str, value: Any
    ) -> None:
        """Set an override for a specific instance.

        Args:
            instance_id: Instance identifier
            setting_path: Dot-separated path to setting (e.g., 'recovery.max_attempts')
            value: Value to set
        """
        if instance_id not in self._instance_overrides:
            self._instance_overrides[instance_id] = {}

        # Parse setting path
        parts = setting_path.split(".")
        current = self._instance_overrides[instance_id]

        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]

        current[parts[-1]] = value

        logger.info(
            "Instance override set",
            instance_id=instance_id,
            setting=setting_path,
            value=value,
        )

    def remove_instance_override(self, instance_id: str, setting_path: str) -> None:
        """Remove an override for a specific instance.

        Args:
            instance_id: Instance identifier
            setting_path: Dot-separated path to setting
        """
        if instance_id not in self._instance_overrides:
            return

        parts = setting_path.split(".")
        current = self._instance_overrides[instance_id]

        try:
            for part in parts[:-1]:
                current = current[part]
            del current[parts[-1]]

            logger.info(
                "Instance override removed",
                instance_id=instance_id,
                setting=setting_path,
            )
        except KeyError:
            logger.warning(
                "Instance override not found",
                instance_id=instance_id,
                setting=setting_path,
            )

    def clear_instance_overrides(self, instance_id: str) -> None:
        """Clear all overrides for a specific instance.

        Args:
            instance_id: Instance identifier
        """
        if instance_id in self._instance_overrides:
            del self._instance_overrides[instance_id]
            logger.info("Instance overrides cleared", instance_id=instance_id)


def load_health_monitoring_config(
    config_file: Path | None = None,
) -> HealthMonitoringSettings:
    """Load health monitoring configuration from file or defaults.

    Args:
        config_file: Path to configuration file (uses defaults if None)

    Returns:
        HealthMonitoringSettings instance
    """
    if config_file and config_file.exists():
        try:
            import yaml

            with open(config_file) as f:
                config_data = yaml.safe_load(f)

            # Extract health monitoring config
            health_config_data = config_data.get("health_monitoring", {})
            config = HealthMonitoringConfig(**health_config_data)

            logger.info("Health monitoring config loaded", config_file=str(config_file))

        except Exception as e:
            logger.error(
                "Failed to load health monitoring config, using defaults",
                config_file=str(config_file),
                error=str(e),
            )
            config = HealthMonitoringConfig()
    else:
        logger.info("Using default health monitoring configuration")
        config = HealthMonitoringConfig()

    return HealthMonitoringSettings(config=config, config_file_path=config_file)


def save_health_monitoring_config(
    settings: HealthMonitoringSettings, config_file: Path
) -> bool:
    """Save health monitoring configuration to file.

    Args:
        settings: Health monitoring settings to save
        config_file: Path to configuration file

    Returns:
        True if saved successfully
    """
    try:
        import yaml

        # Load existing config or create new
        config_data = {}
        if config_file.exists():
            with open(config_file) as f:
                config_data = yaml.safe_load(f) or {}

        # Update health monitoring section
        config_data["health_monitoring"] = settings.config.dict()

        # Write config file
        config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(config_file, "w") as f:
            yaml.dump(config_data, f, default_flow_style=False, indent=2)

        logger.info("Health monitoring config saved", config_file=str(config_file))
        return True

    except Exception as e:
        logger.error(
            "Failed to save health monitoring config",
            config_file=str(config_file),
            error=str(e),
        )
        return False


# Global configuration instance
_health_monitoring_settings: HealthMonitoringSettings | None = None


def get_health_monitoring_settings() -> HealthMonitoringSettings:
    """Get the global health monitoring settings.

    Returns:
        HealthMonitoringSettings instance
    """
    global _health_monitoring_settings
    if _health_monitoring_settings is None:
        _health_monitoring_settings = load_health_monitoring_config()
    return _health_monitoring_settings


def set_health_monitoring_settings(settings: HealthMonitoringSettings) -> None:
    """Set the global health monitoring settings.

    Args:
        settings: HealthMonitoringSettings to use
    """
    global _health_monitoring_settings
    _health_monitoring_settings = settings
