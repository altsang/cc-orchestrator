"""Tests for configuration management enhancements."""

import json
import tempfile
from pathlib import Path

import yaml
from click.testing import CliRunner

from cc_orchestrator.cli.main import main
from cc_orchestrator.config.loader import load_config


class TestConfigTypeConversion:
    """Test configuration type conversion functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    def test_config_set_integer_value(self):
        """Test setting integer configuration values."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / "test-config.yaml"

            # Initialize config
            result = self.runner.invoke(
                main, ["config", "init", "--path", str(config_path)]
            )
            assert result.exit_code == 0

            # Set integer value
            result = self.runner.invoke(
                main,
                ["--config", str(config_path), "config", "set", "max_instances", "10"],
            )
            assert result.exit_code == 0
            assert "Configuration updated: max_instances=10" in result.output

            # Verify the value is correctly loaded as integer
            config = load_config(str(config_path))
            assert config.max_instances == 10
            assert isinstance(config.max_instances, int)

    def test_config_set_boolean_value(self):
        """Test setting boolean configuration values."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / "test-config.yaml"

            # Initialize config
            result = self.runner.invoke(
                main, ["config", "init", "--path", str(config_path)]
            )
            assert result.exit_code == 0

            # Test various boolean representations
            boolean_tests = [
                ("true", True),
                ("false", False),
                ("True", True),
                ("False", False),
                ("1", True),
                ("0", False),
                ("yes", True),
                ("no", False),
                ("on", True),
                ("off", False),
            ]

            for input_val, expected in boolean_tests:
                result = self.runner.invoke(
                    main,
                    [
                        "--config",
                        str(config_path),
                        "config",
                        "set",
                        "auto_cleanup",
                        input_val,
                    ],
                )
                assert result.exit_code == 0

                config = load_config(str(config_path))
                assert config.auto_cleanup == expected
                assert isinstance(config.auto_cleanup, bool)

    def test_config_set_invalid_integer(self):
        """Test setting invalid integer values fails gracefully."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / "test-config.yaml"

            # Initialize config
            result = self.runner.invoke(
                main, ["config", "init", "--path", str(config_path)]
            )
            assert result.exit_code == 0

            # Try to set invalid integer
            result = self.runner.invoke(
                main,
                [
                    "--config",
                    str(config_path),
                    "config",
                    "set",
                    "max_instances",
                    "invalid",
                ],
            )
            assert result.exit_code == 1
            assert "Invalid integer value" in result.output

    def test_config_set_unknown_key(self):
        """Test setting unknown configuration key fails."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / "test-config.yaml"

            # Initialize config
            result = self.runner.invoke(
                main, ["config", "init", "--path", str(config_path)]
            )
            assert result.exit_code == 0

            # Try to set unknown key
            result = self.runner.invoke(
                main,
                ["--config", str(config_path), "config", "set", "unknown_key", "value"],
            )
            assert result.exit_code == 1
            assert "Unknown configuration key" in result.output

    def test_config_module_imports(self):
        """Test that config module properly exports expected components."""
        from cc_orchestrator.config import (
            OrchestratorConfig,
            find_config_file,
            load_config,
            save_config,
        )

        # Test that all expected components are importable
        assert OrchestratorConfig is not None
        assert load_config is not None
        assert save_config is not None
        assert find_config_file is not None

        # Test that we can create a config instance
        config = OrchestratorConfig()
        assert config.max_instances == 5  # default value
        assert config.web_port == 8000  # default value

    def test_config_set_float_value(self):
        """Test setting float configuration values."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / "test-config.yaml"

            # Initialize config
            result = self.runner.invoke(
                main, ["config", "init", "--path", str(config_path)]
            )
            assert result.exit_code == 0

            # Set float value
            result = self.runner.invoke(
                main,
                [
                    "--config",
                    str(config_path),
                    "config",
                    "set",
                    "cpu_threshold",
                    "95.5",
                ],
            )
            assert result.exit_code == 0
            assert "Configuration updated: cpu_threshold=95.5" in result.output

            # Verify the value is correctly loaded as float
            config = load_config(str(config_path))
            assert config.cpu_threshold == 95.5
            assert isinstance(config.cpu_threshold, float)

    def test_config_set_union_type_value(self):
        """Test setting Union type configuration values."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / "test-config.yaml"

            # Initialize config
            result = self.runner.invoke(
                main, ["config", "init", "--path", str(config_path)]
            )
            assert result.exit_code == 0

            # Set Union type value (int | None)
            result = self.runner.invoke(
                main,
                ["--config", str(config_path), "config", "set", "memory_limit", "2048"],
            )
            assert result.exit_code == 0
            assert "Configuration updated: memory_limit=2048" in result.output

            # Verify the value is correctly loaded as integer
            config = load_config(str(config_path))
            assert config.memory_limit == 2048
            assert isinstance(config.memory_limit, int)

    def test_cli_flag_overrides(self):
        """Test CLI flag overrides work correctly."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / "test-config.yaml"

            # Initialize config
            result = self.runner.invoke(
                main, ["config", "init", "--path", str(config_path)]
            )
            assert result.exit_code == 0

            # Test CLI flag overrides
            result = self.runner.invoke(
                main,
                [
                    "--config",
                    str(config_path),
                    "--max-instances",
                    "15",
                    "--cpu-threshold",
                    "90.5",
                    "--memory-limit",
                    "4096",
                    "--json",
                    "config",
                    "show",
                ],
            )
            assert result.exit_code == 0

            # Parse JSON output to verify values
            output_data = json.loads(result.output)
            assert output_data["configuration"]["max_instances"] == 15
            assert output_data["configuration"]["cpu_threshold"] == 90.5
            assert output_data["configuration"]["memory_limit"] == 4096

    def test_configuration_profiles(self):
        """Test configuration profiles functionality."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / "profiles-config.yaml"

            # Create config with profiles
            profile_config = {
                "max_instances": 5,
                "web_port": 8000,
                "log_level": "INFO",
                "profiles": {
                    "development": {
                        "max_instances": 10,
                        "log_level": "DEBUG",
                        "web_port": 8080,
                    },
                    "production": {
                        "max_instances": 20,
                        "log_level": "WARNING",
                        "web_port": 80,
                    },
                },
            }

            with open(config_path, "w") as f:
                yaml.dump(profile_config, f)

            # Test base configuration (no profile)
            result = self.runner.invoke(
                main, ["--config", str(config_path), "--json", "config", "show"]
            )
            assert result.exit_code == 0
            output_data = json.loads(result.output)
            assert output_data["configuration"]["max_instances"] == 5
            assert output_data["configuration"]["log_level"] == "INFO"

            # Test development profile
            result = self.runner.invoke(
                main,
                [
                    "--config",
                    str(config_path),
                    "--profile",
                    "development",
                    "--json",
                    "config",
                    "show",
                ],
            )
            assert result.exit_code == 0
            output_data = json.loads(result.output)
            assert output_data["configuration"]["max_instances"] == 10
            assert output_data["configuration"]["log_level"] == "DEBUG"
            assert output_data["configuration"]["web_port"] == 8080

            # Test CLI overrides with profile (CLI should win)
            result = self.runner.invoke(
                main,
                [
                    "--config",
                    str(config_path),
                    "--profile",
                    "production",
                    "--max-instances",
                    "50",
                    "--json",
                    "config",
                    "show",
                ],
            )
            assert result.exit_code == 0
            output_data = json.loads(result.output)
            assert output_data["configuration"]["max_instances"] == 50  # CLI override
            assert (
                output_data["configuration"]["log_level"] == "WARNING"
            )  # Profile value

    def test_profile_listing(self):
        """Test listing available profiles."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            config_path = Path(tmp_dir) / "profiles-config.yaml"

            # Create config with profiles
            profile_config = {
                "max_instances": 5,
                "profiles": {
                    "dev": {"max_instances": 10},
                    "prod": {"max_instances": 20},
                    "test": {"max_instances": 2},
                },
            }

            with open(config_path, "w") as f:
                yaml.dump(profile_config, f)

            # Test profiles listing
            result = self.runner.invoke(
                main, ["--config", str(config_path), "--json", "config", "profiles"]
            )
            assert result.exit_code == 0
            output_data = json.loads(result.output)
            assert set(output_data["profiles"]) == {"dev", "prod", "test"}
