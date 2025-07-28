"""Configuration loading and management."""

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


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
    config = {}
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
            value = os.environ[env_var]
            # Convert to appropriate types
            if config_key in ["max_instances", "instance_timeout", "web_port"]:
                try:
                    value = int(value)
                except ValueError:
                    continue
            elif config_key == "auto_cleanup":
                value = value.lower() in ("true", "1", "yes", "on")

            config[config_key] = value

    return config


def load_config(config_path: str | None = None) -> OrchestratorConfig:
    """Load configuration from file and environment variables.

    Precedence order (highest to lowest):
    1. Environment variables
    2. Configuration file
    3. Default values
    """
    config_data = {}

    # Load from file if available
    config_file = find_config_file(config_path)
    if config_file:
        config_data.update(load_config_file(config_file))

    # Override with environment variables
    config_data.update(load_env_vars())

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
    config_dict = config.model_dump()
    with open(path, "w") as f:
        yaml.dump(config_dict, f, default_flow_style=False, sort_keys=True)

    return path
