"""End-to-end tests for complete workflows."""

import asyncio
import json
import os
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from cc_orchestrator.database.connection import Base, get_db_session
from cc_orchestrator.database.crud import InstanceCRUD
from cc_orchestrator.database.models import InstanceStatus
from cc_orchestrator.web.app import create_app


@pytest.fixture(scope="function")
def test_db():
    """Create a test database."""
    # Create in-memory SQLite database for testing
    test_db_path = "./test_e2e.db"
    engine = create_engine(
        f"sqlite:///{test_db_path}",
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
    if os.path.exists(test_db_path):
        os.remove(test_db_path)


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


class TestCompleteUserWorkflows:
    """Test complete user workflows from start to finish."""

    def test_complete_authentication_and_instance_management_flow(self, client):
        """Test complete flow: login → create instance → manage → logout."""
        
        # Step 1: Login
        login_response = client.post(
            "/auth/login",
            json={"username": "admin", "password": "admin123"}
        )
        assert login_response.status_code == 200
        token_data = login_response.json()
        token = token_data["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Step 2: Verify authentication works
        me_response = client.get("/auth/me", headers=headers)
        assert me_response.status_code == 200
        assert me_response.json()["username"] == "admin"
        
        # Step 3: Get initial instances list (should be empty)
        instances_response = client.get("/api/v1/instances", headers=headers)
        assert instances_response.status_code == 200
        initial_data = instances_response.json()
        assert initial_data["total"] == 0
        
        # Step 4: Create new instance
        create_response = client.post(
            "/api/v1/instances",
            json={"issue_id": "e2e-test-123"},
            headers=headers
        )
        assert create_response.status_code == 200
        instance = create_response.json()
        instance_id = instance["id"]
        assert instance["issue_id"] == "e2e-test-123"
        assert instance["status"] == InstanceStatus.INITIALIZING.value
        
        # Step 5: Verify instance appears in list
        instances_response = client.get("/api/v1/instances", headers=headers)
        assert instances_response.status_code == 200
        data = instances_response.json()
        assert data["total"] == 1
        assert any(i["id"] == instance_id for i in data["instances"])
        
        # Step 6: Get specific instance details
        detail_response = client.get(f"/api/v1/instances/{instance_id}", headers=headers)
        assert detail_response.status_code == 200
        detail_data = detail_response.json()
        assert detail_data["id"] == instance_id
        
        # Step 7: Start the instance
        start_response = client.post(f"/api/v1/instances/{instance_id}/start", headers=headers)
        assert start_response.status_code == 200
        start_result = start_response.json()
        assert "message" in start_result
        assert start_result["instance_id"] == str(instance_id)
        
        # Step 8: Verify instance status changed
        detail_response = client.get(f"/api/v1/instances/{instance_id}", headers=headers)
        assert detail_response.status_code == 200
        updated_instance = detail_response.json()
        assert updated_instance["status"] == InstanceStatus.RUNNING.value
        
        # Step 9: Check instance health
        health_response = client.get(f"/api/v1/instances/{instance_id}/health", headers=headers)
        assert health_response.status_code == 200
        health_data = health_response.json()
        assert health_data["instance_id"] == instance_id
        assert health_data["status"] == InstanceStatus.RUNNING.value
        assert "health" in health_data
        
        # Step 10: Get instance logs
        logs_response = client.get(f"/api/v1/instances/{instance_id}/logs", headers=headers)
        assert logs_response.status_code == 200
        logs_data = logs_response.json()
        assert logs_data["instance_id"] == instance_id
        assert "logs" in logs_data
        
        # Step 11: Restart the instance
        restart_response = client.post(f"/api/v1/instances/{instance_id}/restart", headers=headers)
        assert restart_response.status_code == 200
        
        # Step 12: Stop the instance
        stop_response = client.post(f"/api/v1/instances/{instance_id}/stop", headers=headers)
        assert stop_response.status_code == 200
        
        # Step 13: Verify instance is stopped
        detail_response = client.get(f"/api/v1/instances/{instance_id}", headers=headers)
        assert detail_response.status_code == 200
        final_instance = detail_response.json()
        assert final_instance["status"] == InstanceStatus.STOPPED.value

    def test_multiple_instance_management_workflow(self, client):
        """Test managing multiple instances simultaneously."""
        
        # Login
        login_response = client.post(
            "/auth/login",
            json={"username": "admin", "password": "admin123"}
        )
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Create multiple instances
        instances = []
        for i in range(3):
            response = client.post(
                "/api/v1/instances",
                json={"issue_id": f"multi-test-{i}"},
                headers=headers
            )
            assert response.status_code == 200
            instances.append(response.json())
        
        # Verify all instances exist
        list_response = client.get("/api/v1/instances", headers=headers)
        assert list_response.status_code == 200
        data = list_response.json()
        assert data["total"] == 3
        
        # Start all instances
        for instance in instances:
            start_response = client.post(
                f"/api/v1/instances/{instance['id']}/start", 
                headers=headers
            )
            assert start_response.status_code == 200
        
        # Verify all are running
        for instance in instances:
            detail_response = client.get(f"/api/v1/instances/{instance['id']}", headers=headers)
            instance_data = detail_response.json()
            assert instance_data["status"] == InstanceStatus.RUNNING.value
        
        # Stop specific instances
        client.post(f"/api/v1/instances/{instances[0]['id']}/stop", headers=headers)
        client.post(f"/api/v1/instances/{instances[2]['id']}/stop", headers=headers)
        
        # Verify mixed states
        detail_0 = client.get(f"/api/v1/instances/{instances[0]['id']}", headers=headers).json()
        detail_1 = client.get(f"/api/v1/instances/{instances[1]['id']}", headers=headers).json()
        detail_2 = client.get(f"/api/v1/instances/{instances[2]['id']}", headers=headers).json()
        
        assert detail_0["status"] == InstanceStatus.STOPPED.value
        assert detail_1["status"] == InstanceStatus.RUNNING.value
        assert detail_2["status"] == InstanceStatus.STOPPED.value

    def test_error_handling_workflow(self, client):
        """Test error scenarios and recovery."""
        
        # Login
        login_response = client.post(
            "/auth/login",
            json={"username": "admin", "password": "admin123"}
        )
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Try to access non-existent instance
        response = client.get("/api/v1/instances/99999", headers=headers)
        assert response.status_code == 404
        error_data = response.json()
        assert "error" in error_data
        assert "InstanceNotFoundError" in error_data["error"]
        
        # Try to control non-existent instance
        response = client.post("/api/v1/instances/99999/start", headers=headers)
        assert response.status_code == 400
        error_data = response.json()
        assert "error" in error_data
        
        # Create instance and test valid operations
        create_response = client.post(
            "/api/v1/instances",
            json={"issue_id": "error-test"},
            headers=headers
        )
        assert create_response.status_code == 200
        instance_id = create_response.json()["id"]
        
        # Valid operations should work after errors
        start_response = client.post(f"/api/v1/instances/{instance_id}/start", headers=headers)
        assert start_response.status_code == 200

    def test_authentication_token_lifecycle(self, client):
        """Test complete token lifecycle."""
        
        # Login and get token
        login_response = client.post(
            "/auth/login",
            json={"username": "admin", "password": "admin123"}
        )
        assert login_response.status_code == 200
        token_data = login_response.json()
        token = token_data["access_token"]
        
        # Use token successfully
        headers = {"Authorization": f"Bearer {token}"}
        response = client.get("/auth/me", headers=headers)
        assert response.status_code == 200
        
        # Use token for API operations
        response = client.get("/api/v1/instances", headers=headers)
        assert response.status_code == 200
        
        # Test with invalid token
        bad_headers = {"Authorization": "Bearer invalid-token"}
        response = client.get("/auth/me", headers=bad_headers)
        assert response.status_code == 401
        
        # Test without token
        response = client.get("/auth/me")
        assert response.status_code == 403

    def test_rate_limiting_workflow(self, client):
        """Test rate limiting in realistic usage."""
        
        # Login
        login_response = client.post(
            "/auth/login",
            json={"username": "admin", "password": "admin123"}
        )
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Make requests at normal rate (should succeed)
        for i in range(5):
            response = client.get("/api/v1/instances", headers=headers)
            assert response.status_code == 200
            time.sleep(0.1)  # Small delay
        
        # Make requests rapidly (should eventually hit rate limit)
        responses = []
        for i in range(35):  # More than 30/min limit
            response = client.get("/api/v1/instances", headers=headers)
            responses.append(response)
        
        # Should have some rate limited responses
        rate_limited = [r for r in responses if r.status_code == 429]
        assert len(rate_limited) > 0, "Rate limiting should be triggered"

    def test_websocket_integration_workflow(self, client):
        """Test WebSocket connectivity and messaging."""
        
        # Login to get token
        login_response = client.post(
            "/auth/login",
            json={"username": "admin", "password": "admin123"}
        )
        token = login_response.json()["access_token"]
        
        # Test WebSocket connection
        with client.websocket_connect("/ws/dashboard") as websocket:
            # Authenticate
            auth_message = {"type": "auth", "token": token}
            websocket.send_text(json.dumps(auth_message))
            
            # Should receive auth success
            response = websocket.receive_json()
            assert response["type"] == "auth_success"
            
            # Should receive welcome message
            welcome = websocket.receive_json()
            assert welcome["type"] == "connected"
            assert "connection_id" in welcome
            
            # Test subscription
            sub_message = {"type": "subscribe", "events": ["instance_status"]}
            websocket.send_text(json.dumps(sub_message))
            
            # Should receive subscription confirmation
            response = websocket.receive_json()
            assert response["type"] == "subscription_confirmed"
            
            # Test ping-pong
            ping_message = {"type": "ping", "timestamp": "2024-01-01T00:00:00Z"}
            websocket.send_text(json.dumps(ping_message))
            
            # Note: The actual pong response would depend on implementation


class TestConcurrencyAndScale:
    """Test concurrent operations and scaling scenarios."""

    def test_concurrent_instance_operations(self, client):
        """Test concurrent operations on instances."""
        
        # Login
        login_response = client.post(
            "/auth/login",
            json={"username": "admin", "password": "admin123"}
        )
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Create base instances
        instances = []
        for i in range(5):
            response = client.post(
                "/api/v1/instances",
                json={"issue_id": f"concurrent-{i}"},
                headers=headers
            )
            assert response.status_code == 200
            instances.append(response.json())
        
        # Simulate concurrent operations
        import concurrent.futures
        import threading
        
        def start_instance(instance_id):
            return client.post(f"/api/v1/instances/{instance_id}/start", headers=headers)
        
        def get_instance(instance_id):
            return client.get(f"/api/v1/instances/{instance_id}", headers=headers)
        
        # Concurrent starts
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            start_futures = [executor.submit(start_instance, inst["id"]) for inst in instances[:3]]
            get_futures = [executor.submit(get_instance, inst["id"]) for inst in instances]
            
            # Wait for completion
            start_results = [f.result() for f in start_futures]
            get_results = [f.result() for f in get_futures]
        
        # All operations should succeed
        assert all(r.status_code == 200 for r in start_results)
        assert all(r.status_code == 200 for r in get_results)

    def test_websocket_connection_limits(self, client):
        """Test WebSocket connection limits and cleanup."""
        
        # Login
        login_response = client.post(
            "/auth/login",
            json={"username": "admin", "password": "admin123"}
        )
        token = login_response.json()["access_token"]
        
        # Try to create multiple connections
        connections = []
        successful_connections = 0
        
        try:
            for i in range(8):  # Try more than typical limit
                try:
                    ws_context = client.websocket_connect("/ws/dashboard")
                    websocket = ws_context.__enter__()
                    
                    # Authenticate
                    auth_message = {"type": "auth", "token": token}
                    websocket.send_text(json.dumps(auth_message))
                    response = websocket.receive_json()
                    
                    if response["type"] == "auth_success":
                        websocket.receive_json()  # Welcome message
                        connections.append((ws_context, websocket))
                        successful_connections += 1
                    else:
                        ws_context.__exit__(None, None, None)
                        break
                        
                except Exception:
                    # Connection rejected due to limits
                    break
            
            # Should not accept unlimited connections
            assert successful_connections <= 6, f"Too many connections accepted: {successful_connections}"
            
        finally:
            # Cleanup
            for ws_context, websocket in connections:
                try:
                    ws_context.__exit__(None, None, None)
                except:
                    pass


class TestDataConsistency:
    """Test data consistency across operations."""

    def test_instance_state_consistency(self, client):
        """Test that instance state remains consistent across operations."""
        
        # Login
        login_response = client.post(
            "/auth/login",
            json={"username": "admin", "password": "admin123"}
        )
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Create instance
        create_response = client.post(
            "/api/v1/instances",
            json={"issue_id": "consistency-test"},
            headers=headers
        )
        instance_id = create_response.json()["id"]
        
        # Track state through multiple operations
        states = []
        
        # Initial state
        response = client.get(f"/api/v1/instances/{instance_id}", headers=headers)
        states.append(response.json()["status"])
        
        # Start instance
        client.post(f"/api/v1/instances/{instance_id}/start", headers=headers)
        response = client.get(f"/api/v1/instances/{instance_id}", headers=headers)
        states.append(response.json()["status"])
        
        # Stop instance
        client.post(f"/api/v1/instances/{instance_id}/stop", headers=headers)
        response = client.get(f"/api/v1/instances/{instance_id}", headers=headers)
        states.append(response.json()["status"])
        
        # Restart instance
        client.post(f"/api/v1/instances/{instance_id}/restart", headers=headers)
        response = client.get(f"/api/v1/instances/{instance_id}", headers=headers)
        states.append(response.json()["status"])
        
        # Verify expected state transitions
        assert states[0] == InstanceStatus.INITIALIZING.value
        assert states[1] == InstanceStatus.RUNNING.value
        assert states[2] == InstanceStatus.STOPPED.value
        assert states[3] == InstanceStatus.RUNNING.value  # After restart
        
        # Verify consistency across different endpoints
        detail_response = client.get(f"/api/v1/instances/{instance_id}", headers=headers)
        health_response = client.get(f"/api/v1/instances/{instance_id}/health", headers=headers)
        list_response = client.get("/api/v1/instances", headers=headers)
        
        detail_status = detail_response.json()["status"]
        health_status = health_response.json()["status"]
        list_instance = next(i for i in list_response.json()["instances"] if i["id"] == instance_id)
        list_status = list_instance["status"]
        
        # All endpoints should report same status
        assert detail_status == health_status == list_status