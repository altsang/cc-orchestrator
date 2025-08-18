"""Configuration loading and management."""

import os
import warnings
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

# Suppress Pydantic serialization warnings globally for config operations
warnings.filterwarnings("ignore", message=".*Pydantic serializer warnings.*")


class ConfigurationError(Exception):
    """Exception for configuration-related errors."""

    pass


class OrchestratorConfig(BaseModel):
    """Configuration model for CC-Orchestrator."""

    # Instance management
    max_instances: int = Field(
        default=5, description="Maximum number of concurrent instances"
    )
    instance_timeout: int = Field(
        default=3600, description="Instance timeout in seconds"
    )

    # Git worktree settings
    worktree_base_path: str = Field(
        default="~/workspace", description="Base path for worktrees"
    )
    auto_cleanup: bool = Field(default=True, description="Auto cleanup stale worktrees")

    # Web interface
    web_host: str = Field(default="localhost", description="Web interface host")
    web_port: int = Field(default=8000, description="Web interface port")

    # GitHub integration
    github_token: str | None = Field(default=None, description="GitHub API token")
    github_org: str | None = Field(default=None, description="GitHub organization")
    github_repo: str | None = Field(default=None, description="GitHub repository")

    # Logging
    log_level: str = Field(default="INFO", description="Logging level")
    log_file: str | None = Field(default=None, description="Log file path")

    # Output formatting
    default_output_format: str = Field(
        default="human", description="Default output format"
    )

    # Performance settings (for testing float and Union types)
    cpu_threshold: float = Field(
        default=80.0, description="CPU usage threshold percentage"
    )
    memory_limit: int | None = Field(
        default=None, description="Memory limit in MB (None for unlimited)"
    )


def find_config_file(custom_path: str | None = None) -> Path | None:
    """Find configuration file in standard locations."""
    if custom_path:
        path = Path(custom_path).expanduser()
        if path.exists():
            return path
        raise FileNotFoundError(f"Config file not found: {custom_path}")

    # Search in standard locations
    search_paths = [
        Path.cwd() / "cc-orchestrator.yaml",
        Path.cwd() / "cc-orchestrator.yml",
        Path.home() / ".config" / "cc-orchestrator" / "config.yaml",
        Path.home() / ".cc-orchestrator.yaml",
    ]

    for path in search_paths:
        if path.exists():
            return path

    return None


def load_config_file(config_path: Path) -> dict[str, Any]:
    """Load configuration from YAML file."""
    try:
        with open(config_path) as f:
            return yaml.safe_load(f) or {}
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in config file {config_path}: {e}")
    except Exception as e:
        raise ValueError(f"Failed to read config file {config_path}: {e}")


def load_env_vars() -> dict[str, Any]:
    """Load configuration from environment variables."""
    config: dict[str, Any] = {}
    prefix = "CC_ORCHESTRATOR_"

    # Map environment variables to config keys
    env_mappings = {
        f"{prefix}MAX_INSTANCES": "max_instances",
        f"{prefix}INSTANCE_TIMEOUT": "instance_timeout",
        f"{prefix}WORKTREE_BASE_PATH": "worktree_base_path",
        f"{prefix}AUTO_CLEANUP": "auto_cleanup",
        f"{prefix}WEB_HOST": "web_host",
        f"{prefix}WEB_PORT": "web_port",
        f"{prefix}GITHUB_TOKEN": "github_token",
        f"{prefix}GITHUB_ORG": "github_org",
        f"{prefix}GITHUB_REPO": "github_repo",
        f"{prefix}LOG_LEVEL": "log_level",
        f"{prefix}LOG_FILE": "log_file",
        f"{prefix}DEFAULT_OUTPUT_FORMAT": "default_output_format",
    }

    for env_var, config_key in env_mappings.items():
        if env_var in os.environ:
            env_value = os.environ[env_var]
            # Convert to appropriate types
            if config_key in ["max_instances", "instance_timeout", "web_port"]:
                try:
                    config[config_key] = int(env_value)
                except ValueError:
                    continue
            elif config_key == "auto_cleanup":
                config[config_key] = env_value.lower() in ("true", "1", "yes", "on")
            else:
                config[config_key] = env_value

    return config


def load_config(
    config_path: str | None = None,
    profile: str | None = None,
    cli_overrides: dict[str, Any] | None = None,
) -> OrchestratorConfig:
    """Load configuration from file and environment variables.

    Precedence order (highest to lowest):
    1. CLI flag overrides
    2. Environment variables
    3. Configuration file (with profile support)
    4. Default values
    """
    config_data = {}

    # Load from file if available
    config_file = find_config_file(config_path)
    if config_file:
        file_data = load_config_file(config_file)

        # Handle profile-specific configuration
        if profile and "profiles" in file_data and profile in file_data["profiles"]:
            # Merge base config with profile-specific overrides
            profile_data = file_data["profiles"][profile]
            # Remove profiles section from base data
            base_data = {k: v for k, v in file_data.items() if k != "profiles"}
            config_data.update(base_data)
            config_data.update(profile_data)
        else:
            # Remove profiles section if present
            config_data.update({k: v for k, v in file_data.items() if k != "profiles"})

    # Override with environment variables
    config_data.update(load_env_vars())

    # Override with CLI flags (highest precedence)
    if cli_overrides:
        config_data.update(cli_overrides)

    # Create and validate configuration
    try:
        return OrchestratorConfig(**config_data)
    except Exception as e:
        raise ValueError(f"Invalid configuration: {e}")


def save_config(config: OrchestratorConfig, config_path: str | None = None) -> Path:
    """Save configuration to file."""
    if config_path:
        path = Path(config_path).expanduser()
    else:
        # Use default location
        config_dir = Path.home() / ".config" / "cc-orchestrator"
        config_dir.mkdir(parents=True, exist_ok=True)
        path = config_dir / "config.yaml"

    # Convert to dict and save as YAML
    # Suppress Pydantic serialization warnings for expected type conversions
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message=".*Pydantic serializer warnings.*")
        config_dict = config.model_dump()
    with open(path, "w") as f:
        yaml.dump(config_dict, f, default_flow_style=False, sort_keys=True)

    return path


# Default configuration values
DEFAULT_CONFIG = {
    "max_instances": 5,
    "instance_timeout": 3600,
    "worktree_base_path": "~/workspace",
    "auto_cleanup": True,
    "web_host": "localhost",
    "web_port": 8000,
    "log_level": "INFO",
    "default_output_format": "human",
    "cpu_threshold": 80.0,
}


class ConfigurationLoader:
    """Helper class for configuration loading operations."""

    def __init__(self, config_path: str | None = None, profile: str | None = None):
        """Initialize configuration loader.

        Args:
            config_path: Path to configuration file
            profile: Configuration profile to use
        """
        self.config_path = config_path
        self.profile = profile

    def load(self, cli_overrides: dict[str, Any] | None = None) -> OrchestratorConfig:
        """Load configuration with current settings.

        Args:
            cli_overrides: CLI parameter overrides

        Returns:
            Loaded and validated configuration
        """
        return load_config(self.config_path, self.profile, cli_overrides)
