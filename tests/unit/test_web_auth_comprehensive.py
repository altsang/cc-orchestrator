"""Comprehensive tests for web authentication module."""

import os
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import jwt
import pytest
from fastapi import HTTPException
from passlib.context import CryptContext


class TestAuthenticationCore:
    """Test core authentication functions."""

    def test_password_hashing_and_verification(self):
        """Test password hashing and verification."""
        from cc_orchestrator.web.auth import get_password_hash, verify_password

        password = "test-password-123"
        hashed = get_password_hash(password)

        # Hash should not equal original password (unless in testing mode with plaintext)
        testing_mode = os.getenv("TESTING", "false").lower() == "true"
        if not testing_mode:
            assert hashed != password

        # Should verify correctly
        assert verify_password(password, hashed)

        # Should fail with wrong password
        assert not verify_password("wrong-password", hashed)

        # Different calls should produce different hashes (unless in testing mode with plaintext)
        hash2 = get_password_hash(password)
        if not testing_mode:
            assert hashed != hash2
        assert verify_password(password, hash2)

    def test_jwt_token_creation_and_verification(self):
        """Test JWT token creation and verification."""
        with patch.dict(os.environ, {"JWT_SECRET_KEY": "test-secret-key-for-testing"}):
            import importlib

            from cc_orchestrator.web import auth

            importlib.reload(auth)

            # Test basic token creation
            data = {"sub": "testuser", "role": "admin"}
            token = auth.create_access_token(data)

            assert token is not None
            assert isinstance(token, str)

            # Test token verification
            payload = auth.verify_token(token)
            assert payload["sub"] == "testuser"
            assert payload["role"] == "admin"
            assert "exp" in payload

    def test_jwt_token_expiration(self):
        """Test JWT token expiration handling."""
        with patch.dict(os.environ, {"JWT_SECRET_KEY": "test-secret-key-for-testing"}):
            import importlib

            from cc_orchestrator.web import auth

            importlib.reload(auth)

            # Create token with custom expiration
            data = {"sub": "testuser"}
            expires_delta = timedelta(seconds=1)
            token = auth.create_access_token(data, expires_delta)

            # Should work immediately
            payload = auth.verify_token(token)
            assert payload["sub"] == "testuser"

            # Test expired token detection in get_current_user
            # Create an already expired token
            past_time = datetime.now(UTC) - timedelta(seconds=10)
            expired_data = {"sub": "testuser", "exp": past_time.timestamp()}
            expired_token = jwt.encode(
                expired_data, "test-secret-key-for-testing", algorithm="HS256"
            )

            from fastapi.security import HTTPAuthorizationCredentials

            creds = HTTPAuthorizationCredentials(
                scheme="Bearer", credentials=expired_token
            )

            # This should raise an exception due to expired token
            import asyncio

            async def test_expired():
                with pytest.raises(HTTPException) as exc_info:
                    await auth.get_current_user(creds)
                assert exc_info.value.status_code == 401
                # JWT library may throw different error for expired tokens
                assert "Could not validate credentials" in str(
                    exc_info.value.detail
                ) or "Token expired" in str(exc_info.value.detail)

            asyncio.run(test_expired())

    def test_invalid_jwt_tokens(self):
        """Test handling of invalid JWT tokens."""
        with patch.dict(os.environ, {"JWT_SECRET_KEY": "test-secret-key-for-testing"}):
            import importlib

            from cc_orchestrator.web import auth

            importlib.reload(auth)

            # Test malformed token
            with pytest.raises(HTTPException) as exc_info:
                auth.verify_token("invalid.token.here")
            assert exc_info.value.status_code == 401

            # Test token with wrong signature
            wrong_token = jwt.encode({"sub": "test"}, "wrong-secret", algorithm="HS256")
            with pytest.raises(HTTPException) as exc_info:
                auth.verify_token(wrong_token)
            assert exc_info.value.status_code == 401

            # Test empty token
            with pytest.raises(HTTPException):
                auth.verify_token("")


class TestDemoUserSystem:
    """Test demo user system functionality."""

    def test_demo_user_authentication_success(self):
        """Test successful demo user authentication."""
        with patch.dict(
            os.environ,
            {
                "JWT_SECRET_KEY": "test-secret",
                "ENABLE_DEMO_USERS": "true",
                "DEMO_ADMIN_PASSWORD": "secure-demo-pass",
            },
        ):
            import importlib

            from cc_orchestrator.web import auth

            importlib.reload(auth)

            user = auth.authenticate_user("admin", "secure-demo-pass")
            assert user is not None
            assert user["username"] == "admin"
            assert user["role"] == "admin"
            assert "hashed_password" in user

    def test_demo_user_authentication_failure(self):
        """Test demo user authentication with wrong password."""
        with patch.dict(
            os.environ,
            {
                "JWT_SECRET_KEY": "test-secret",
                "ENABLE_DEMO_USERS": "true",
                "DEMO_ADMIN_PASSWORD": "secure-demo-pass",
            },
        ):
            import importlib

            from cc_orchestrator.web import auth

            importlib.reload(auth)

            # Wrong password
            user = auth.authenticate_user("admin", "wrong-password")
            assert user is None

            # Non-existent user
            user = auth.authenticate_user("nonexistent", "any-password")
            assert user is None

    def test_demo_users_disabled_in_production(self):
        """Test that demo users are disabled when ENABLE_DEMO_USERS=false."""
        with patch.dict(
            os.environ, {"JWT_SECRET_KEY": "test-secret", "ENABLE_DEMO_USERS": "false"}
        ):
            import importlib

            from cc_orchestrator.web import auth

            importlib.reload(auth)

            with pytest.raises(HTTPException) as exc_info:
                auth.authenticate_user("admin", "any-password")

            assert exc_info.value.status_code == 501
            assert "Demo users disabled" in str(exc_info.value.detail)

    def test_demo_users_empty_when_disabled(self):
        """Test that DEMO_USERS dict is empty when disabled."""
        with patch.dict(
            os.environ, {"JWT_SECRET_KEY": "test-secret", "ENABLE_DEMO_USERS": "false"}
        ):
            import importlib

            from cc_orchestrator.web import auth

            importlib.reload(auth)

            assert auth.DEMO_USERS == {}


class TestGetCurrentUser:
    """Test get_current_user function."""

    async def test_get_current_user_success(self):
        """Test successful user retrieval from token."""
        with patch.dict(os.environ, {"JWT_SECRET_KEY": "test-secret-key-for-testing"}):
            import importlib

            from cc_orchestrator.web import auth

            importlib.reload(auth)

            # Create a valid token
            data = {"sub": "testuser", "role": "admin"}
            token = auth.create_access_token(data)

            from fastapi.security import HTTPAuthorizationCredentials

            creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

            user = await auth.get_current_user(creds)
            assert user["sub"] == "testuser"
            assert user["role"] == "admin"

    async def test_get_current_user_invalid_token(self):
        """Test get_current_user with invalid token."""
        with patch.dict(os.environ, {"JWT_SECRET_KEY": "test-secret-key-for-testing"}):
            import importlib

            from cc_orchestrator.web import auth

            importlib.reload(auth)

            from fastapi.security import HTTPAuthorizationCredentials

            creds = HTTPAuthorizationCredentials(
                scheme="Bearer", credentials="invalid-token"
            )

            with pytest.raises(HTTPException) as exc_info:
                await auth.get_current_user(creds)
            assert exc_info.value.status_code == 401


class TestPasswordContext:
    """Test password context configuration."""

    def test_bcrypt_configuration(self):
        """Test that bcrypt is properly configured."""
        from cc_orchestrator.web.auth import pwd_context

        assert isinstance(pwd_context, CryptContext)

        # Test that it uses bcrypt (or plaintext in testing mode)
        password = "test-password"
        hashed = pwd_context.hash(password)

        # bcrypt hashes start with $2b$ (unless in testing mode with plaintext)
        testing_mode = os.getenv("TESTING", "false").lower() == "true"
        if not testing_mode:
            assert hashed.startswith("$2b$")

        # Test verification
        assert pwd_context.verify(password, hashed)
        assert not pwd_context.verify("wrong-password", hashed)


class TestSecurityConfiguration:
    """Test security configuration constants."""

    def test_algorithm_constant(self):
        """Test JWT algorithm constant."""
        from cc_orchestrator.web.auth import ALGORITHM

        assert ALGORITHM == "HS256"

    def test_token_expire_constant(self):
        """Test access token expiration constant."""
        from cc_orchestrator.web.auth import ACCESS_TOKEN_EXPIRE_MINUTES

        assert ACCESS_TOKEN_EXPIRE_MINUTES == 30
        assert isinstance(ACCESS_TOKEN_EXPIRE_MINUTES, int)
