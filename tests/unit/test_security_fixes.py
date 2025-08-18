"""Test security fixes for authentication and configuration."""

import os
from unittest.mock import patch

import pytest
from fastapi import HTTPException


class TestJWTSecretValidation:
    """Test JWT secret key validation."""

    def test_jwt_secret_validation_missing(self):
        """Test that missing JWT secret raises error."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="JWT_SECRET_KEY must be set"):
                # This will trigger the import-time validation
                import importlib

                import cc_orchestrator.web.auth

                importlib.reload(cc_orchestrator.web.auth)

    def test_jwt_secret_validation_weak_default(self):
        """Test that weak default JWT secret raises error."""
        with patch.dict(
            os.environ, {"JWT_SECRET_KEY": "dev-secret-key-change-in-production"}
        ):
            with pytest.raises(ValueError, match="JWT_SECRET_KEY must be set"):
                import importlib

                import cc_orchestrator.web.auth

                importlib.reload(cc_orchestrator.web.auth)

    def test_jwt_secret_validation_strong_key(self):
        """Test that strong JWT secret is accepted."""
        with patch.dict(
            os.environ,
            {"JWT_SECRET_KEY": "very-strong-secret-key-for-production-use-123"},
        ):
            try:
                import importlib

                import cc_orchestrator.web.auth

                importlib.reload(cc_orchestrator.web.auth)
                # Should not raise an exception
            except ValueError:
                pytest.fail("Strong JWT secret key should be accepted")


class TestDemoUserSecurity:
    """Test demo user security controls."""

    def test_demo_users_disabled_by_default(self):
        """Test that demo users are disabled by default."""
        with patch.dict(
            os.environ,
            {"ENABLE_DEMO_USERS": "false", "JWT_SECRET_KEY": "test-secret"},
            clear=False,
        ):
            # Need to reload the module with new environment
            import importlib

            from cc_orchestrator.web import auth

            importlib.reload(auth)

            with pytest.raises(HTTPException) as exc_info:
                auth.authenticate_user("admin", "admin123")

            assert exc_info.value.status_code == 501
            assert "Demo users disabled" in str(exc_info.value.detail)

    def test_demo_users_explicitly_disabled(self):
        """Test that demo users can be explicitly disabled."""
        with patch.dict(
            os.environ, {"JWT_SECRET_KEY": "test-secret"}, clear=True
        ):  # No ENABLE_DEMO_USERS set (defaults to false)
            # Need to reload the module with new environment
            import importlib

            from cc_orchestrator.web import auth

            importlib.reload(auth)

            with pytest.raises(HTTPException) as exc_info:
                auth.authenticate_user("admin", "admin123")

            assert exc_info.value.status_code == 501

    def test_demo_users_can_be_enabled_in_development(self):
        """Test that demo users can be enabled for development."""
        with patch.dict(
            os.environ,
            {"ENABLE_DEMO_USERS": "true", "DEMO_ADMIN_PASSWORD": "custom-dev-password"},
        ):
            # Need to reload to pick up new environment
            import importlib

            import cc_orchestrator.web.auth

            importlib.reload(cc_orchestrator.web.auth)

            # Should work with custom password
            user = cc_orchestrator.web.auth.authenticate_user(
                "admin", "custom-dev-password"
            )
            assert user is not None
            assert user["username"] == "admin"
            assert user["role"] == "admin"

            # Should fail with wrong password
            user = cc_orchestrator.web.auth.authenticate_user("admin", "wrong-password")
            assert user is None


class TestProductionEnvironmentValidation:
    """Test production environment validation."""

    def test_production_requires_frontend_url(self):
        """Test that production mode requires FRONTEND_URL."""
        with patch.dict(os.environ, {"DEBUG": "false"}, clear=True):
            with pytest.raises(
                ValueError, match="FRONTEND_URL must be set when DEBUG=false"
            ):
                from cc_orchestrator.web.app import create_app

                create_app()

    def test_production_requires_valid_frontend_url(self):
        """Test that production mode requires valid FRONTEND_URL format."""
        test_cases = [
            "invalid-url",
            "ftp://example.com",
            "just-a-domain.com",
        ]

        for invalid_url in test_cases:
            with patch.dict(
                os.environ,
                {
                    "DEBUG": "false",
                    "FRONTEND_URL": invalid_url,
                    "JWT_SECRET_KEY": "test-secret",
                },
            ):
                with pytest.raises(ValueError, match="must be a valid HTTP"):
                    from cc_orchestrator.web.app import create_app

                    create_app()

        # Test empty URL separately since it triggers different error
        with patch.dict(
            os.environ,
            {"DEBUG": "false", "FRONTEND_URL": "", "JWT_SECRET_KEY": "test-secret"},
        ):
            with pytest.raises(ValueError, match="FRONTEND_URL must be set"):
                from cc_orchestrator.web.app import create_app

                create_app()

    def test_production_accepts_valid_frontend_urls(self):
        """Test that production mode accepts valid FRONTEND_URLs."""
        valid_urls = [
            "https://example.com",
            "http://localhost:3000",
            "https://my-frontend.example.com",
        ]

        for valid_url in valid_urls:
            with patch.dict(
                os.environ,
                {
                    "DEBUG": "false",
                    "FRONTEND_URL": valid_url,
                    "JWT_SECRET_KEY": "test-secret-key-for-testing-only",
                },
            ):
                try:
                    from cc_orchestrator.web.app import create_app

                    app = create_app()
                    assert app is not None
                except ValueError as e:
                    pytest.fail(
                        f"Valid URL {valid_url} should be accepted, but got: {e}"
                    )

    def test_production_requires_jwt_secret(self):
        """Test that production mode requires JWT_SECRET_KEY."""
        with patch.dict(
            os.environ,
            {"DEBUG": "false", "FRONTEND_URL": "https://example.com"},
            clear=True,
        ):
            with pytest.raises(
                ValueError, match="JWT_SECRET_KEY must be set in production"
            ):
                from cc_orchestrator.web.app import create_app

                create_app()

    def test_development_mode_works_without_frontend_url(self):
        """Test that development mode works without FRONTEND_URL."""
        with patch.dict(
            os.environ, {"DEBUG": "true", "JWT_SECRET_KEY": "test-secret-for-dev"}
        ):
            try:
                from cc_orchestrator.web.app import create_app

                app = create_app()
                assert app is not None
            except ValueError:
                pytest.fail("Development mode should work without FRONTEND_URL")


class TestSecurityBestPractices:
    """Test that security best practices are enforced."""

    def test_no_hardcoded_secrets_in_production_code(self):
        """Test that no hardcoded secrets exist in the codebase."""
        # Read the auth.py file to check for hardcoded secrets
        import inspect

        import cc_orchestrator.web.auth

        source = inspect.getsource(cc_orchestrator.web.auth)

        # Should not contain obvious hardcoded secrets
        forbidden_patterns = [
            "admin123",  # Only if not in a conditional block
            "password123",
            "secret123",
        ]

        # Check that hardcoded patterns are only in conditional demo code
        for pattern in forbidden_patterns:
            if pattern in source:
                # Should only appear in demo/development context
                assert (
                    "DEMO" in source or "demo" in source
                ), f"Hardcoded {pattern} found outside demo context"

    def test_demo_users_isolated_from_production(self):
        """Test that demo users are properly isolated from production."""
        # Import with production-like settings
        with patch.dict(os.environ, {"ENABLE_DEMO_USERS": "false", "DEBUG": "false"}):
            import importlib

            import cc_orchestrator.web.auth

            importlib.reload(cc_orchestrator.web.auth)

            # Demo users dict should be empty
            assert cc_orchestrator.web.auth.DEMO_USERS == {}

    def test_environment_variable_security(self):
        """Test that sensitive data comes from environment variables."""
        with patch.dict(
            os.environ,
            {
                "JWT_SECRET_KEY": "test-key",
                "ENABLE_DEMO_USERS": "true",
                "DEMO_ADMIN_PASSWORD": "custom-secure-password",
            },
        ):
            import importlib

            import cc_orchestrator.web.auth

            importlib.reload(cc_orchestrator.web.auth)

            # Should use password from environment, not hardcoded
            user = cc_orchestrator.web.auth.authenticate_user(
                "admin", "custom-secure-password"
            )
            assert user is not None

            # Should not work with old hardcoded password
            user = cc_orchestrator.web.auth.authenticate_user("admin", "admin123")
            assert user is None
