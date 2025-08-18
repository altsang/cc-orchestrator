#!/usr/bin/env python3
"""
Custom test runner for auth tests that bypasses coverage requirements.
"""

import os
import subprocess
import sys
import tempfile


def run_auth_tests():
    """Run auth tests without coverage requirements."""

    # Create a temporary pytest config without coverage requirements
    temp_config = """
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py", "*_test.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = [
    "--strict-markers",
    "-v"
]
markers = [
    "unit: Unit tests",
    "integration: Integration tests",
    "slow: Slow running tests",
    "auth: Authentication module tests",
]
asyncio_mode = "auto"
"""

    # Get the failing auth tests
    auth_tests = [
        "tests/unit/test_web_auth.py::TestTokenFunctions::test_create_access_token_default_expiry",
        "tests/unit/test_web_auth.py::TestTokenFunctions::test_create_access_token_custom_expiry",
        "tests/unit/test_web_auth.py::TestGetCurrentUser::test_get_current_user_no_exp_claim",
        "tests/unit/test_web_auth.py::TestModuleConstants::test_secret_key_from_environment",
        "tests/unit/test_web_auth_coverage.py::TestTokenOperations::test_create_access_token_default_expiry",
        "tests/unit/test_web_auth_coverage.py::TestTokenOperations::test_create_access_token_custom_expiry",
        "tests/unit/test_web_auth_coverage.py::TestTokenOperations::test_create_access_token_no_expiry_delta",
        "tests/unit/test_web_auth_coverage.py::TestGetCurrentUser::test_get_current_user_expired_token",
        "tests/unit/test_web_auth_coverage.py::TestGetCurrentUser::test_get_current_user_no_exp_claim",
    ]

    print("Running auth tests without coverage requirements...")

    # Create temporary config file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
        f.write(temp_config)
        temp_config_path = f.name

    try:
        # Run pytest with the temporary config
        cmd = [
            sys.executable,
            "-m",
            "pytest",
            "-c",
            temp_config_path,
            "-xvs",
        ] + auth_tests

        result = subprocess.run(cmd, capture_output=False)
        return result.returncode

    finally:
        # Clean up temporary config
        os.unlink(temp_config_path)


if __name__ == "__main__":
    sys.exit(run_auth_tests())
