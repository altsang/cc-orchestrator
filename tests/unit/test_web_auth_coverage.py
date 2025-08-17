"""Comprehensive tests for web.auth module to achieve 100% coverage."""

import os
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import jwt
import pytest
from fastapi import HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials

from cc_orchestrator.web.auth import (
    ALGORITHM,
    SECRET_KEY,
    authenticate_user,
    create_access_token,
    get_current_user,
    get_password_hash,
    verify_password,
    verify_token,
)


class TestPasswordOperations:
    """Test password hashing and verification."""

    def test_get_password_hash(self):
        """Test password hashing."""
        password = "test_password_123"
        hashed = get_password_hash(password)

        assert isinstance(hashed, str)
        assert len(hashed) > 20  # Bcrypt hashes are long
        assert hashed != password  # Should be different from plain text
        assert hashed.startswith("$2b$")  # Bcrypt format

    def test_verify_password_correct(self):
        """Test password verification with correct password."""
        password = "correct_password"
        hashed = get_password_hash(password)

        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Test password verification with incorrect password."""
        password = "correct_password"
        wrong_password = "wrong_password"
        hashed = get_password_hash(password)

        assert verify_password(wrong_password, hashed) is False

    def test_verify_password_empty_strings(self):
        """Test password verification with empty strings."""
        assert verify_password("", "") is False

    def test_verify_password_exception_handling(self):
        """Test password verification with malformed hash that triggers exception."""
        # Test with invalid hash format that causes bcrypt to raise an exception
        invalid_hash = "invalid_hash_format"
        result = verify_password("any_password", invalid_hash)
        assert result is False

        # Test with None hash (edge case)
        result = verify_password("password", None)
        assert result is False

        # Test with whitespace-only hash
        result = verify_password("password", "   ")
        assert result is False

    def test_password_hash_uniqueness(self):
        """Test that same password produces different hashes (salt)."""
        password = "same_password"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)

        # Should be different due to salt
        assert hash1 != hash2
        # But both should verify correctly
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True


class TestTokenOperations:
    """Test JWT token creation and verification."""

    @pytest.mark.auth
    def test_create_access_token_default_expiry(self):
        """Test token creation with default expiry."""
        data = {"sub": "test_user", "role": "admin"}
        token = create_access_token(data)

        assert isinstance(token, str)
        assert len(token) > 50  # JWT tokens are long

        # Decode to verify content
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert payload["sub"] == "test_user"
        assert payload["role"] == "admin"
        assert "exp" in payload

    @pytest.mark.auth
    def test_create_access_token_custom_expiry(self):
        """Test token creation with custom expiry."""
        data = {"sub": "test_user"}
        expires_delta = timedelta(minutes=60)

        # Don't patch datetime to avoid JWT validation issues
        token = create_access_token(data, expires_delta)

        # Decode and verify the token structure without time validation
        payload = jwt.decode(
            token, SECRET_KEY, algorithms=[ALGORITHM], options={"verify_exp": False}
        )
        assert payload["sub"] == "test_user"
        assert "exp" in payload

    @pytest.mark.auth
    def test_create_access_token_no_expiry_delta(self):
        """Test token creation with no custom expiry (uses default 15 min)."""
        data = {"sub": "test_user"}

        # Don't patch datetime to avoid JWT validation issues
        token = create_access_token(data)

        # Decode and verify the token structure without time validation
        payload = jwt.decode(
            token, SECRET_KEY, algorithms=[ALGORITHM], options={"verify_exp": False}
        )
        assert payload["sub"] == "test_user"
        assert "exp" in payload

    def test_verify_token_valid(self):
        """Test token verification with valid token."""
        data = {"sub": "test_user", "role": "admin"}
        token = create_access_token(data)

        payload = verify_token(token)

        assert payload["sub"] == "test_user"
        assert payload["role"] == "admin"
        assert "exp" in payload

    def test_verify_token_invalid(self):
        """Test token verification with invalid token."""
        invalid_token = "invalid.jwt.token"

        with pytest.raises(HTTPException) as exc_info:
            verify_token(invalid_token)

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Could not validate credentials" in exc_info.value.detail
        assert exc_info.value.headers == {"WWW-Authenticate": "Bearer"}

    def test_verify_token_malformed(self):
        """Test token verification with malformed token."""
        # Create a token with wrong secret
        data = {"sub": "test_user"}
        malformed_token = jwt.encode(data, "wrong_secret", algorithm=ALGORITHM)

        with pytest.raises(HTTPException) as exc_info:
            verify_token(malformed_token)

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Could not validate credentials" in exc_info.value.detail

    def test_verify_token_expired(self):
        """Test token verification with expired token."""
        data = {"sub": "test_user"}
        # Create expired token
        past_time = datetime.now(UTC) - timedelta(hours=1)
        data["exp"] = past_time.timestamp()
        expired_token = jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)

        with pytest.raises(HTTPException) as exc_info:
            verify_token(expired_token)

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED


class TestGetCurrentUser:
    """Test get_current_user function."""

    @pytest.mark.asyncio
    async def test_get_current_user_valid_token(self):
        """Test get_current_user with valid non-expired token."""
        # Create valid token
        data = {"sub": "test_user", "role": "admin"}
        token = create_access_token(data, timedelta(minutes=30))

        # Create credentials
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        with patch("cc_orchestrator.web.auth.datetime") as mock_datetime:
            # Set current time to be before token expiry
            mock_now = datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC)
            mock_datetime.now.return_value = mock_now

            user = await get_current_user(credentials)

            assert user["sub"] == "test_user"
            assert user["role"] == "admin"

    @pytest.mark.asyncio
    @pytest.mark.auth
    async def test_get_current_user_expired_token(self):
        """Test get_current_user with expired token."""
        # Create an expired token directly using jwt.encode with past expiration
        data = {"sub": "test_user"}
        past_time = datetime.now(UTC) - timedelta(minutes=30)
        expired_payload = data.copy()
        expired_payload["exp"] = past_time.timestamp()

        expired_token = jwt.encode(expired_payload, SECRET_KEY, algorithm=ALGORITHM)
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials=expired_token
        )

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials)

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Token expired" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_current_user_expired_token_runtime_check(self):
        """Test get_current_user with token that becomes expired during runtime check."""
        # Create token that will pass JWT decode but fail runtime expiration check
        data = {"sub": "test_user"}
        # Create token with expiration just in the past for runtime check
        past_time = datetime.now(UTC) - timedelta(seconds=1)
        expired_payload = data.copy()
        expired_payload["exp"] = past_time.timestamp()

        # Use verify=False to bypass JWT library expiration check
        # and test the manual expiration check in get_current_user
        token = jwt.encode(expired_payload, SECRET_KEY, algorithm=ALGORITHM)
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        # Mock verify_token to return payload without expiration checking
        with patch("cc_orchestrator.web.auth.verify_token") as mock_verify:
            mock_verify.return_value = expired_payload

            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(credentials)

            assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
            assert "Token expired" in exc_info.value.detail
            assert exc_info.value.headers == {"WWW-Authenticate": "Bearer"}

    @pytest.mark.asyncio
    @pytest.mark.auth
    async def test_get_current_user_no_exp_claim(self):
        """Test get_current_user with token that has no exp claim."""
        # Create token manually without exp claim
        data = {"sub": "test_user", "role": "admin"}
        token = jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)

        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        user = await get_current_user(credentials)

        assert user["sub"] == "test_user"
        assert user["role"] == "admin"

    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token(self):
        """Test get_current_user with invalid token."""
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials="invalid_token"
        )

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials)

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Could not validate credentials" in exc_info.value.detail


class TestAuthenticateUser:
    """Test user authentication."""

    def test_authenticate_user_demo_disabled(self):
        """Test authentication when demo users are disabled."""
        with patch("cc_orchestrator.web.auth._demo_enabled", False):
            with pytest.raises(HTTPException) as exc_info:
                authenticate_user("admin", "password")

            assert exc_info.value.status_code == status.HTTP_501_NOT_IMPLEMENTED
            assert "Demo users disabled" in exc_info.value.detail

    def test_authenticate_user_valid_credentials(self):
        """Test authentication with valid credentials."""
        with patch("cc_orchestrator.web.auth._demo_enabled", True):
            with patch(
                "cc_orchestrator.web.auth.DEMO_USERS",
                {
                    "admin": {
                        "username": "admin",
                        "hashed_password": get_password_hash("admin123"),
                        "role": "admin",
                    }
                },
            ):
                user = authenticate_user("admin", "admin123")

                assert user is not None
                assert user["username"] == "admin"
                assert user["role"] == "admin"
                assert "hashed_password" in user

    def test_authenticate_user_invalid_username(self):
        """Test authentication with invalid username."""
        with patch("cc_orchestrator.web.auth._demo_enabled", True):
            with patch(
                "cc_orchestrator.web.auth.DEMO_USERS",
                {
                    "admin": {
                        "username": "admin",
                        "hashed_password": get_password_hash("admin123"),
                        "role": "admin",
                    }
                },
            ):
                user = authenticate_user("nonexistent", "admin123")

                assert user is None

    def test_authenticate_user_invalid_password(self):
        """Test authentication with invalid password."""
        with patch("cc_orchestrator.web.auth._demo_enabled", True):
            with patch(
                "cc_orchestrator.web.auth.DEMO_USERS",
                {
                    "admin": {
                        "username": "admin",
                        "hashed_password": get_password_hash("admin123"),
                        "role": "admin",
                    }
                },
            ):
                user = authenticate_user("admin", "wrong_password")

                assert user is None

    def test_authenticate_user_empty_credentials(self):
        """Test authentication with empty credentials."""
        with patch("cc_orchestrator.web.auth._demo_enabled", True):
            with patch("cc_orchestrator.web.auth.DEMO_USERS", {}):
                user = authenticate_user("", "")

                assert user is None


class TestModuleInitialization:
    """Test module-level initialization and configuration."""

    def test_secret_key_exists(self):
        """Test that SECRET_KEY is properly set."""
        # The SECRET_KEY should be set from environment or raise ValueError
        assert isinstance(SECRET_KEY, str)
        assert len(SECRET_KEY) > 0

    def test_algorithm_constant(self):
        """Test that ALGORITHM constant is set correctly."""
        assert ALGORITHM == "HS256"

    def test_demo_enabled_flag_default_isolated(self):
        """Test _demo_enabled flag with default value in clean environment."""
        # This test runs before any reload operations to test true default
        import os

        # Clear any existing environment variable for this test
        with patch.dict(os.environ, {}, clear=False):
            # Remove ENABLE_DEMO_USERS if it exists
            if "ENABLE_DEMO_USERS" in os.environ:
                del os.environ["ENABLE_DEMO_USERS"]

            # Import fresh module to test default behavior
            import importlib

            import cc_orchestrator.web.auth

            importlib.reload(cc_orchestrator.web.auth)

            # Default should be False when env var is not set
            assert cc_orchestrator.web.auth._demo_enabled is False

    def test_demo_users_initialization_enabled(self):
        """Test DEMO_USERS initialization when demo is enabled."""
        with patch.dict(
            os.environ, {"ENABLE_DEMO_USERS": "true", "DEMO_ADMIN_PASSWORD": "test123"}
        ):
            # Re-import to trigger initialization
            import importlib

            import cc_orchestrator.web.auth

            importlib.reload(cc_orchestrator.web.auth)

            # Should have demo users
            assert hasattr(cc_orchestrator.web.auth, "DEMO_USERS")

    def test_demo_users_initialization_disabled(self):
        """Test DEMO_USERS initialization when demo is disabled."""
        with patch.dict(os.environ, {"ENABLE_DEMO_USERS": "false"}, clear=False):
            # Re-import to trigger initialization
            import importlib

            import cc_orchestrator.web.auth

            importlib.reload(cc_orchestrator.web.auth)

            # Should have empty demo users
            assert cc_orchestrator.web.auth.DEMO_USERS == {}

    def test_demo_enabled_flag_true(self):
        """Test _demo_enabled flag when environment variable is true."""
        with patch.dict(os.environ, {"ENABLE_DEMO_USERS": "true"}):
            import importlib

            import cc_orchestrator.web.auth

            importlib.reload(cc_orchestrator.web.auth)

            assert cc_orchestrator.web.auth._demo_enabled is True

    def test_demo_enabled_flag_false(self):
        """Test _demo_enabled flag when environment variable is false."""
        with patch.dict(os.environ, {"ENABLE_DEMO_USERS": "false"}):
            import importlib

            import cc_orchestrator.web.auth

            importlib.reload(cc_orchestrator.web.auth)

            assert cc_orchestrator.web.auth._demo_enabled is False


class TestSecretKeyValidation:
    """Test SECRET_KEY validation during module import."""

    def test_secret_key_validation_empty(self):
        """Test that empty SECRET_KEY raises ValueError."""
        import importlib

        import cc_orchestrator.web.auth

        # Store original state
        original_secret_key = getattr(cc_orchestrator.web.auth, "SECRET_KEY", None)

        try:
            with patch.dict(os.environ, {"JWT_SECRET_KEY": ""}):
                with pytest.raises(ValueError, match="JWT_SECRET_KEY must be set"):
                    importlib.reload(cc_orchestrator.web.auth)
        finally:
            # Restore original state by reloading with original environment
            if "JWT_SECRET_KEY" in os.environ:
                importlib.reload(cc_orchestrator.web.auth)
            # Ensure the SECRET_KEY is restored to original value
            if original_secret_key is not None:
                cc_orchestrator.web.auth.SECRET_KEY = original_secret_key

    def test_secret_key_validation_default_dev_key(self):
        """Test that default dev key raises ValueError."""
        import importlib

        import cc_orchestrator.web.auth

        # Store original state
        original_secret_key = getattr(cc_orchestrator.web.auth, "SECRET_KEY", None)

        try:
            with patch.dict(
                os.environ, {"JWT_SECRET_KEY": "dev-secret-key-change-in-production"}
            ):
                with pytest.raises(ValueError, match="JWT_SECRET_KEY must be set"):
                    importlib.reload(cc_orchestrator.web.auth)
        finally:
            # Restore original state by reloading with original environment
            if "JWT_SECRET_KEY" in os.environ:
                importlib.reload(cc_orchestrator.web.auth)
            # Ensure the SECRET_KEY is restored to original value
            if original_secret_key is not None:
                cc_orchestrator.web.auth.SECRET_KEY = original_secret_key

    def test_secret_key_validation_missing(self):
        """Test that missing SECRET_KEY raises ValueError."""
        import importlib

        import cc_orchestrator.web.auth

        # Store original state
        original_secret_key = getattr(cc_orchestrator.web.auth, "SECRET_KEY", None)
        original_jwt_secret = os.environ.get("JWT_SECRET_KEY")

        try:
            # Remove JWT_SECRET_KEY from environment
            with patch.dict(os.environ, {}, clear=True):
                os.environ.pop("JWT_SECRET_KEY", None)

                with pytest.raises(ValueError, match="JWT_SECRET_KEY must be set"):
                    importlib.reload(cc_orchestrator.web.auth)
        finally:
            # Restore original environment and state
            if original_jwt_secret is not None:
                os.environ["JWT_SECRET_KEY"] = original_jwt_secret
                importlib.reload(cc_orchestrator.web.auth)
            # Ensure the SECRET_KEY is restored to original value
            if original_secret_key is not None:
                cc_orchestrator.web.auth.SECRET_KEY = original_secret_key


class TestEdgeCasesAndIntegration:
    """Test edge cases and integration scenarios."""

    def test_token_roundtrip(self):
        """Test complete token creation and verification cycle."""
        # Create user data
        user_data = {
            "sub": "user123",
            "username": "testuser",
            "role": "user",
            "permissions": ["read", "write"],
        }

        # Create token
        token = create_access_token(user_data, timedelta(minutes=30))

        # Verify token
        payload = verify_token(token)

        # Verify all data preserved
        assert payload["sub"] == user_data["sub"]
        assert payload["username"] == user_data["username"]
        assert payload["role"] == user_data["role"]
        assert payload["permissions"] == user_data["permissions"]
        assert "exp" in payload

    @pytest.mark.asyncio
    async def test_full_auth_flow(self):
        """Test complete authentication flow."""
        with patch("cc_orchestrator.web.auth._demo_enabled", True):
            with patch(
                "cc_orchestrator.web.auth.DEMO_USERS",
                {
                    "testuser": {
                        "username": "testuser",
                        "hashed_password": get_password_hash("testpass"),
                        "role": "user",
                    }
                },
            ):
                # Authenticate user
                user = authenticate_user("testuser", "testpass")
                assert user is not None

                # Create token for user
                token_data = {"sub": user["username"], "role": user["role"]}
                token = create_access_token(token_data, timedelta(minutes=30))

                # Use token to get current user
                credentials = HTTPAuthorizationCredentials(
                    scheme="Bearer", credentials=token
                )
                current_user = await get_current_user(credentials)

                assert current_user["sub"] == "testuser"
                assert current_user["role"] == "user"

    def test_password_security_properties(self):
        """Test password security properties."""
        passwords = [
            "simple",
            "Complex123!",
            "very_long_password_with_special_chars@#$%",
        ]

        for password in passwords:
            hashed = get_password_hash(password)

            # Hash should be different from password
            assert hashed != password

            # Hash should verify correctly
            assert verify_password(password, hashed) is True

            # Hash should not verify with wrong password
            assert verify_password(password + "wrong", hashed) is False

            # Hash should be consistent format
            assert hashed.startswith("$2b$")

    def test_jwt_security_properties(self):
        """Test JWT security properties."""
        data = {"sub": "user", "role": "admin"}

        # Create multiple tokens with slight time difference
        token1 = create_access_token(data)
        import time

        time.sleep(0.001)  # Small delay to ensure different timestamps
        token2 = create_access_token(data)

        # Tokens should be different (due to timestamps) or same if created at exact same time
        # Both are valid JWT tokens
        assert isinstance(token1, str)
        assert isinstance(token2, str)

        # Both should verify to same data
        payload1 = verify_token(token1)
        payload2 = verify_token(token2)

        assert payload1["sub"] == payload2["sub"]
        assert payload1["role"] == payload2["role"]
