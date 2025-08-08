"""Integration tests for web API and WebSocket functionality."""

import asyncio
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from cc_orchestrator.database.connection import Base, get_db_session
from cc_orchestrator.database.crud import InstanceCRUD
from cc_orchestrator.database.models import InstanceStatus
from cc_orchestrator.web.app import create_app
from cc_orchestrator.web.auth import create_access_token, get_password_hash


@pytest.fixture(scope="function")
def test_db():
    """Create a test database."""
    # Create in-memory SQLite database for testing
    engine = create_engine(
        "sqlite:///./test.db",
        connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    def override_get_db():
        try:
            db = TestingSessionLocal()
            yield db
        finally:
            db.close()
    
    yield override_get_db
    
    # Cleanup
    if os.path.exists("./test.db"):
        os.remove("./test.db")


@pytest.fixture
def test_app(test_db):
    """Create test FastAPI application with test database."""
    app = create_app()
    app.dependency_overrides[get_db_session] = test_db
    return app


@pytest.fixture
def client(test_app):
    """Create test client."""
    return TestClient(test_app)


@pytest.fixture
def auth_token():
    """Create valid authentication token."""
    return create_access_token(data={"sub": "testuser", "role": "admin"})


@pytest.fixture
def auth_headers(auth_token):
    """Create authentication headers."""
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture
def sample_instance(test_db):
    """Create a sample instance in the database."""
    db = next(test_db())
    instance = InstanceCRUD.create(db, issue_id="test-123")
    db.commit()
    yield instance
    db.close()


class TestWebAPIIntegration:
    """Integration tests for the web API."""

    def test_authentication_flow(self, client):
        """Test complete authentication flow."""
        # Test login
        response = client.post(
            "/auth/login",
            json={"username": "admin", "password": "admin123"}
        )
        assert response.status_code == 200
        token_data = response.json()
        assert "access_token" in token_data
        assert token_data["token_type"] == "bearer"
        
        # Test using token to access protected endpoint
        headers = {"Authorization": f"Bearer {token_data['access_token']}"}
        response = client.get("/auth/me", headers=headers)
        assert response.status_code == 200
        user_data = response.json()
        assert user_data["username"] == "admin"

    def test_instance_crud_operations(self, client, auth_headers, sample_instance):
        """Test complete CRUD operations for instances."""
        # Get all instances
        response = client.get("/api/v1/instances", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "instances" in data
        assert len(data["instances"]) >= 1
        
        # Get specific instance
        instance_id = sample_instance.id
        response = client.get(f"/api/v1/instances/{instance_id}", headers=auth_headers)
        assert response.status_code == 200
        instance_data = response.json()
        assert instance_data["id"] == instance_id
        
        # Create new instance
        response = client.post(
            "/api/v1/instances",
            json={"issue_id": "new-test-456"},
            headers=auth_headers
        )
        assert response.status_code == 200
        new_instance = response.json()
        assert new_instance["issue_id"] == "new-test-456"
        new_instance_id = new_instance["id"]
        
        # Start instance
        response = client.post(
            f"/api/v1/instances/{new_instance_id}/start",
            headers=auth_headers
        )
        assert response.status_code == 200
        result = response.json()
        assert "message" in result
        assert "instance_id" in result
        
        # Stop instance
        response = client.post(
            f"/api/v1/instances/{new_instance_id}/stop",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        # Restart instance
        response = client.post(
            f"/api/v1/instances/{new_instance_id}/restart",
            headers=auth_headers
        )
        assert response.status_code == 200

    def test_instance_health_and_logs(self, client, auth_headers, sample_instance):
        """Test health and logs endpoints."""
        instance_id = sample_instance.id
        
        # Get health
        response = client.get(
            f"/api/v1/instances/{instance_id}/health",
            headers=auth_headers
        )
        assert response.status_code == 200
        health_data = response.json()
        assert "instance_id" in health_data
        assert "status" in health_data
        assert "health" in health_data
        
        # Get logs
        response = client.get(
            f"/api/v1/instances/{instance_id}/logs",
            headers=auth_headers
        )
        assert response.status_code == 200
        logs_data = response.json()
        assert "instance_id" in logs_data
        assert "logs" in logs_data

    def test_authentication_required(self, client, sample_instance):
        """Test that endpoints require authentication."""
        instance_id = sample_instance.id
        
        endpoints_to_test = [
            ("GET", "/api/v1/instances"),
            ("GET", f"/api/v1/instances/{instance_id}"),
            ("POST", "/api/v1/instances"),
            ("POST", f"/api/v1/instances/{instance_id}/start"),
            ("POST", f"/api/v1/instances/{instance_id}/stop"),
            ("GET", f"/api/v1/instances/{instance_id}/health"),
        ]
        
        for method, endpoint in endpoints_to_test:
            if method == "GET":
                response = client.get(endpoint)
            else:
                response = client.post(endpoint, json={})
            
            assert response.status_code == 403, f"Endpoint {method} {endpoint} should require auth"

    def test_rate_limiting(self, client, auth_headers):
        """Test rate limiting functionality."""
        # Make many requests quickly to trigger rate limit
        responses = []
        for i in range(35):  # More than the 30/min limit
            response = client.get("/api/v1/instances", headers=auth_headers)
            responses.append(response)
        
        # Should have some rate limited responses
        rate_limited_count = sum(1 for r in responses if r.status_code == 429)
        assert rate_limited_count > 0, "Rate limiting should be triggered"

    def test_error_handling(self, client, auth_headers):
        """Test error handling with specific exception types."""
        # Test getting non-existent instance
        response = client.get("/api/v1/instances/99999", headers=auth_headers)
        assert response.status_code == 404
        error_data = response.json()
        assert "error" in error_data
        assert "InstanceNotFoundError" in error_data["error"]
        
        # Test starting non-existent instance
        response = client.post("/api/v1/instances/99999/start", headers=auth_headers)
        assert response.status_code == 400
        error_data = response.json()
        assert "error" in error_data

    def test_health_endpoints(self, client):
        """Test health and status endpoints."""
        # Test health check (no auth required)
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        
        # Test root endpoint
        response = client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]


class TestWebSocketIntegration:
    """Integration tests for WebSocket functionality."""

    def test_websocket_authentication_flow(self, client, auth_token):
        """Test WebSocket authentication flow."""
        with client.websocket_connect("/ws/dashboard") as websocket:
            # Send authentication
            auth_message = {"type": "auth", "token": auth_token}
            websocket.send_text(json.dumps(auth_message))
            
            # Should receive auth success
            response = websocket.receive_json()
            assert response["type"] == "auth_success"
            assert "user" in response

    def test_websocket_messaging_flow(self, client, auth_token):
        """Test complete WebSocket messaging flow."""
        with client.websocket_connect("/ws/dashboard") as websocket:
            # Authenticate
            auth_message = {"type": "auth", "token": auth_token}
            websocket.send_text(json.dumps(auth_message))
            websocket.receive_json()  # Consume auth response
            
            # Test ping-pong
            ping_message = {"type": "ping", "timestamp": "2024-01-01T00:00:00Z"}
            websocket.send_text(json.dumps(ping_message))
            
            # Should receive welcome message first (from connection)
            welcome_msg = websocket.receive_json()
            assert welcome_msg["type"] == "connected"
            
            # Test subscription
            sub_message = {"type": "subscribe", "events": ["instance_status"]}
            websocket.send_text(json.dumps(sub_message))
            
            # Should receive subscription confirmation
            response = websocket.receive_json()
            assert response["type"] == "subscription_confirmed"
            assert response["events"] == ["instance_status"]

    def test_websocket_connection_limits(self, client, auth_token):
        """Test WebSocket connection limits."""
        connections = []
        
        try:
            # Try to create many connections from same "IP" (will be localhost in tests)
            for i in range(10):  # Try more than the limit
                try:
                    ws = client.websocket_connect("/ws/dashboard")
                    websocket = ws.__enter__()
                    connections.append((ws, websocket))
                    
                    # Authenticate each connection
                    auth_message = {"type": "auth", "token": auth_token}
                    websocket.send_text(json.dumps(auth_message))
                    websocket.receive_json()  # Consume auth response
                    websocket.receive_json()  # Consume welcome message
                    
                except Exception:
                    # Connection should be rejected at some point
                    break
            
            # Should not be able to create unlimited connections
            assert len(connections) <= 6, "Connection limits should be enforced"
            
        finally:
            # Clean up connections
            for ws_context, websocket in connections:
                try:
                    ws_context.__exit__(None, None, None)
                except:
                    pass


class TestDatabaseIntegration:
    """Integration tests for database operations."""

    def test_instance_crud_with_database(self, test_db):
        """Test CRUD operations with real database."""
        db = next(test_db())
        
        try:
            # Create instance
            instance = InstanceCRUD.create(db, issue_id="db-test-123")
            db.commit()
            assert instance.id is not None
            assert instance.issue_id == "db-test-123"
            assert instance.status == InstanceStatus.INITIALIZING
            
            # Read instance
            retrieved = InstanceCRUD.get_by_id(db, instance.id)
            assert retrieved.id == instance.id
            assert retrieved.issue_id == instance.issue_id
            
            # Update instance
            updated = InstanceCRUD.update(db, instance.id, status=InstanceStatus.RUNNING)
            db.commit()
            assert updated.status == InstanceStatus.RUNNING
            
            # List instances
            instances = InstanceCRUD.list_all(db)
            assert len(instances) >= 1
            assert any(i.id == instance.id for i in instances)
            
            # List with status filter
            running_instances = InstanceCRUD.list_all(db, status=InstanceStatus.RUNNING)
            assert any(i.id == instance.id for i in running_instances)
            
        finally:
            db.close()

    def test_database_error_handling(self, test_db):
        """Test database error scenarios."""
        db = next(test_db())
        
        try:
            # Test getting non-existent instance
            with pytest.raises(Exception):
                InstanceCRUD.get_by_id(db, 99999)
            
            # Test updating non-existent instance
            with pytest.raises(Exception):
                InstanceCRUD.update(db, 99999, status=InstanceStatus.RUNNING)
                
        finally:
            db.close()


class TestSecurityFeatures:
    """Integration tests for security features."""

    def test_jwt_token_lifecycle(self, client):
        """Test JWT token creation, validation, and expiration."""
        # Login to get token
        response = client.post(
            "/auth/login",
            json={"username": "admin", "password": "admin123"}
        )
        assert response.status_code == 200
        token_data = response.json()
        token = token_data["access_token"]
        
        # Use token immediately (should work)
        headers = {"Authorization": f"Bearer {token}"}
        response = client.get("/auth/me", headers=headers)
        assert response.status_code == 200
        
        # Test with invalid token
        invalid_headers = {"Authorization": "Bearer invalid-token"}
        response = client.get("/auth/me", headers=invalid_headers)
        assert response.status_code == 401

    def test_cors_configuration(self, client):
        """Test CORS configuration."""
        # Test preflight request
        response = client.options(
            "/api/v1/instances",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "Authorization"
            }
        )
        # Should not fail (exact response depends on configuration)
        assert response.status_code in [200, 204, 405]  # Different servers handle OPTIONS differently

    def test_error_response_format(self, client, auth_headers):
        """Test that errors return proper JSON format."""
        # Test various error scenarios
        response = client.get("/api/v1/instances/99999", headers=auth_headers)
        assert response.status_code == 404
        
        error_data = response.json()
        assert "error" in error_data
        assert "message" in error_data
        assert "status_code" in error_data
        assert error_data["status_code"] == 404