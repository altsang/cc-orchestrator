"""Comprehensive tests for web schemas module."""

from datetime import datetime

import pytest
from pydantic import ValidationError

from cc_orchestrator.database.models import InstanceStatus
from cc_orchestrator.web.schemas import (
    InstanceBase,
    InstanceCreate,
    InstanceHealthResponse,
    InstanceListResponse,
    InstanceLogsResponse,
    InstanceMetrics,
    InstanceResponse,
    InstanceStatusUpdate,
    SystemStatus,
    WebSocketMessage,
)


class TestInstanceStatus:
    """Test InstanceStatus enum."""

    def test_instance_status_values(self):
        """Test all instance status values."""
        assert InstanceStatus.INITIALIZING.value == "initializing"
        assert InstanceStatus.RUNNING.value == "running"
        assert InstanceStatus.STOPPED.value == "stopped"
        assert InstanceStatus.ERROR.value == "error"

    def test_instance_status_membership(self):
        """Test instance status membership."""
        status_values = [status.value for status in InstanceStatus]
        assert "initializing" in status_values
        assert "running" in status_values
        assert "stopped" in status_values
        assert "error" in status_values


class TestInstanceBase:
    """Test InstanceBase schema."""

    def test_instance_base_valid_data(self):
        """Test InstanceBase with valid data."""
        instance = InstanceBase(issue_id="123", status=InstanceStatus.RUNNING)

        assert instance.issue_id == "123"
        assert instance.status == InstanceStatus.RUNNING

    def test_instance_base_status_validation(self):
        """Test InstanceBase status validation."""
        # Valid status
        instance = InstanceBase(issue_id="123", status="running")
        assert instance.status == InstanceStatus.RUNNING

        # Invalid status should fail
        with pytest.raises(ValidationError):
            InstanceBase(issue_id="123", status="invalid-status")

    def test_instance_base_required_fields(self):
        """Test InstanceBase required fields."""
        # Missing issue_id
        with pytest.raises(ValidationError):
            InstanceBase(status="running")

        # Missing status
        with pytest.raises(ValidationError):
            InstanceBase(issue_id="123")


class TestInstanceCreate:
    """Test InstanceCreate schema."""

    def test_instance_create_inheritance(self):
        """Test InstanceCreate inherits from InstanceBase."""
        instance = InstanceCreate(issue_id="123", status=InstanceStatus.INITIALIZING)

        assert isinstance(instance, InstanceBase)
        assert instance.issue_id == "123"
        assert instance.status == InstanceStatus.INITIALIZING

    def test_instance_create_validation(self):
        """Test InstanceCreate validation."""
        # Should work with all valid statuses
        for status in [
            InstanceStatus.INITIALIZING,
            InstanceStatus.RUNNING,
            InstanceStatus.STOPPED,
            InstanceStatus.ERROR,
        ]:
            instance = InstanceCreate(issue_id="123", status=status)
            assert instance.status == status


class TestInstanceStatusUpdate:
    """Test InstanceStatusUpdate schema."""

    def test_status_update_valid(self):
        """Test InstanceStatusUpdate with valid data."""
        update = InstanceStatusUpdate(status=InstanceStatus.RUNNING)
        assert update.status == InstanceStatus.RUNNING

    def test_status_update_all_statuses(self):
        """Test InstanceStatusUpdate with all valid statuses."""
        statuses = [
            InstanceStatus.INITIALIZING,
            InstanceStatus.RUNNING,
            InstanceStatus.STOPPED,
            InstanceStatus.ERROR,
        ]

        for status in statuses:
            update = InstanceStatusUpdate(status=status)
            assert update.status == status

    def test_status_update_validation(self):
        """Test InstanceStatusUpdate validation."""
        # Invalid status
        with pytest.raises(ValidationError):
            InstanceStatusUpdate(status="invalid-status")

        # Missing status
        with pytest.raises(ValidationError):
            InstanceStatusUpdate()


class TestInstanceResponse:
    """Test InstanceResponse schema."""

    def test_instance_response_valid(self):
        """Test InstanceResponse with valid data."""
        now = datetime.now()
        response = InstanceResponse(
            id=1,
            issue_id="123",
            status=InstanceStatus.RUNNING,
            created_at=now,
            updated_at=now,
        )

        assert response.id == 1
        assert response.issue_id == "123"
        assert response.status == InstanceStatus.RUNNING
        assert response.created_at == now
        assert response.updated_at == now

    def test_instance_response_optional_updated_at(self):
        """Test InstanceResponse with optional updated_at."""
        now = datetime.now()
        response = InstanceResponse(
            id=1, issue_id="123", status=InstanceStatus.RUNNING, created_at=now
        )

        assert response.updated_at is None

    def test_instance_response_inheritance(self):
        """Test InstanceResponse inherits from InstanceBase."""
        now = datetime.now()
        response = InstanceResponse(
            id=1, issue_id="123", status=InstanceStatus.RUNNING, created_at=now
        )

        assert isinstance(response, InstanceBase)

    def test_instance_response_required_fields(self):
        """Test InstanceResponse required fields."""
        now = datetime.now()
        base_data = {
            "id": 1,
            "issue_id": "123",
            "status": InstanceStatus.RUNNING,
            "created_at": now,
        }

        # Test missing each required field
        for field in ["id", "issue_id", "status", "created_at"]:
            invalid_data = {k: v for k, v in base_data.items() if k != field}
            with pytest.raises(ValidationError):
                InstanceResponse(**invalid_data)


class TestInstanceListResponse:
    """Test InstanceListResponse schema."""

    def test_instance_list_response_valid(self):
        """Test InstanceListResponse with valid data."""
        now = datetime.now()
        instances = [
            InstanceResponse(
                id=1, issue_id="123", status=InstanceStatus.RUNNING, created_at=now
            ),
            InstanceResponse(
                id=2, issue_id="124", status=InstanceStatus.STOPPED, created_at=now
            ),
        ]

        response = InstanceListResponse(instances=instances, total=2)
        assert len(response.instances) == 2
        assert response.total == 2
        assert response.instances[0].id == 1
        assert response.instances[1].id == 2

    def test_instance_list_response_empty(self):
        """Test InstanceListResponse with empty list."""
        response = InstanceListResponse(instances=[], total=0)
        assert len(response.instances) == 0
        assert response.total == 0

    def test_instance_list_response_validation(self):
        """Test InstanceListResponse validation."""
        # Missing instances
        with pytest.raises(ValidationError):
            InstanceListResponse(total=0)

        # Missing total
        with pytest.raises(ValidationError):
            InstanceListResponse(instances=[])


class TestInstanceHealthResponse:
    """Test InstanceHealthResponse schema."""

    def test_health_response_valid(self):
        """Test InstanceHealthResponse with valid data."""
        response = InstanceHealthResponse(
            instance_id=1,
            status=InstanceStatus.RUNNING,
            health="healthy",
            cpu_usage=45.5,
            memory_usage=67.2,
            uptime_seconds=3600,
            last_activity="2025-01-01T12:00:00Z",
        )

        assert response.instance_id == 1
        assert response.status == InstanceStatus.RUNNING
        assert response.health == "healthy"
        assert response.cpu_usage == 45.5
        assert response.memory_usage == 67.2
        assert response.uptime_seconds == 3600
        assert response.last_activity == "2025-01-01T12:00:00Z"

    def test_health_response_optional_last_activity(self):
        """Test InstanceHealthResponse with optional last_activity."""
        response = InstanceHealthResponse(
            instance_id=1,
            status=InstanceStatus.RUNNING,
            health="healthy",
            cpu_usage=45.5,
            memory_usage=67.2,
            uptime_seconds=3600,
        )

        assert response.last_activity is None

    def test_health_response_validation(self):
        """Test InstanceHealthResponse validation."""
        base_data = {
            "instance_id": 1,
            "status": InstanceStatus.RUNNING,
            "health": "healthy",
            "cpu_usage": 45.5,
            "memory_usage": 67.2,
            "uptime_seconds": 3600,
        }

        # Test missing each required field
        for field in [
            "instance_id",
            "status",
            "health",
            "cpu_usage",
            "memory_usage",
            "uptime_seconds",
        ]:
            invalid_data = {k: v for k, v in base_data.items() if k != field}
            with pytest.raises(ValidationError):
                InstanceHealthResponse(**invalid_data)


class TestInstanceLogsResponse:
    """Test InstanceLogsResponse schema."""

    def test_logs_response_valid(self):
        """Test InstanceLogsResponse with valid data."""
        logs = [
            {
                "timestamp": "2025-01-01T12:00:00Z",
                "level": "INFO",
                "message": "Test log 1",
            },
            {
                "timestamp": "2025-01-01T12:01:00Z",
                "level": "ERROR",
                "message": "Test log 2",
            },
        ]

        response = InstanceLogsResponse(
            instance_id=1, logs=logs, total=100, limit=50, search="error"
        )

        assert response.instance_id == 1
        assert len(response.logs) == 2
        assert response.total == 100
        assert response.limit == 50
        assert response.search == "error"

    def test_logs_response_optional_search(self):
        """Test InstanceLogsResponse with optional search."""
        response = InstanceLogsResponse(instance_id=1, logs=[], total=0, limit=50)

        assert response.search is None

    def test_logs_response_validation(self):
        """Test InstanceLogsResponse validation."""
        base_data = {"instance_id": 1, "logs": [], "total": 0, "limit": 50}

        # Test missing each required field
        for field in ["instance_id", "logs", "total", "limit"]:
            invalid_data = {k: v for k, v in base_data.items() if k != field}
            with pytest.raises(ValidationError):
                InstanceLogsResponse(**invalid_data)


class TestWebSocketMessage:
    """Test WebSocketMessage schema."""

    def test_websocket_message_valid(self):
        """Test WebSocketMessage with valid data."""
        message = WebSocketMessage(
            type="status_update",
            data={"instance_id": 1, "status": "running"},
            timestamp="2025-01-01T12:00:00Z",
        )

        assert message.type == "status_update"
        assert message.data == {"instance_id": 1, "status": "running"}
        assert message.timestamp == "2025-01-01T12:00:00Z"

    def test_websocket_message_optional_fields(self):
        """Test WebSocketMessage with optional fields."""
        message = WebSocketMessage(type="heartbeat")

        assert message.type == "heartbeat"
        assert message.data == {}
        assert message.timestamp is None

    def test_websocket_message_validation(self):
        """Test WebSocketMessage validation."""
        # Type is required
        with pytest.raises(ValidationError):
            WebSocketMessage()

    def test_websocket_message_data_factory(self):
        """Test WebSocketMessage data field default factory."""
        message1 = WebSocketMessage(type="test1")
        message2 = WebSocketMessage(type="test2")

        # Should be separate dict instances
        assert message1.data is not message2.data
        assert message1.data == {}
        assert message2.data == {}


class TestInstanceMetrics:
    """Test InstanceMetrics schema."""

    def test_instance_metrics_valid(self):
        """Test InstanceMetrics with valid data."""
        timestamp = datetime.now()
        metrics = InstanceMetrics(
            instance_id=1,
            cpu_usage=45.5,
            memory_usage=67.2,
            disk_usage=80.1,
            network_in=1024.5,
            network_out=2048.7,
            uptime_seconds=3600,
            timestamp=timestamp,
        )

        assert metrics.instance_id == 1
        assert metrics.cpu_usage == 45.5
        assert metrics.memory_usage == 67.2
        assert metrics.disk_usage == 80.1
        assert metrics.network_in == 1024.5
        assert metrics.network_out == 2048.7
        assert metrics.uptime_seconds == 3600
        assert metrics.timestamp == timestamp

    def test_instance_metrics_validation_ranges(self):
        """Test InstanceMetrics field validation ranges."""
        timestamp = datetime.now()
        base_data = {
            "instance_id": 1,
            "cpu_usage": 50.0,
            "memory_usage": 50.0,
            "disk_usage": 50.0,
            "network_in": 100.0,
            "network_out": 100.0,
            "uptime_seconds": 3600,
            "timestamp": timestamp,
        }

        # Test CPU usage range
        with pytest.raises(ValidationError):
            InstanceMetrics(**{**base_data, "cpu_usage": -1.0})

        with pytest.raises(ValidationError):
            InstanceMetrics(**{**base_data, "cpu_usage": 101.0})

        # Test memory usage range
        with pytest.raises(ValidationError):
            InstanceMetrics(**{**base_data, "memory_usage": -1.0})

        with pytest.raises(ValidationError):
            InstanceMetrics(**{**base_data, "memory_usage": 101.0})

        # Test disk usage range
        with pytest.raises(ValidationError):
            InstanceMetrics(**{**base_data, "disk_usage": -1.0})

        with pytest.raises(ValidationError):
            InstanceMetrics(**{**base_data, "disk_usage": 101.0})

        # Test network values (should be >= 0)
        with pytest.raises(ValidationError):
            InstanceMetrics(**{**base_data, "network_in": -1.0})

        with pytest.raises(ValidationError):
            InstanceMetrics(**{**base_data, "network_out": -1.0})

        # Test uptime (should be >= 0)
        with pytest.raises(ValidationError):
            InstanceMetrics(**{**base_data, "uptime_seconds": -1})

    def test_instance_metrics_edge_values(self):
        """Test InstanceMetrics with edge values."""
        timestamp = datetime.now()

        # Test minimum values
        metrics = InstanceMetrics(
            instance_id=1,
            cpu_usage=0.0,
            memory_usage=0.0,
            disk_usage=0.0,
            network_in=0.0,
            network_out=0.0,
            uptime_seconds=0,
            timestamp=timestamp,
        )
        assert metrics.cpu_usage == 0.0

        # Test maximum values
        metrics = InstanceMetrics(
            instance_id=1,
            cpu_usage=100.0,
            memory_usage=100.0,
            disk_usage=100.0,
            network_in=999999.99,
            network_out=999999.99,
            uptime_seconds=999999,
            timestamp=timestamp,
        )
        assert metrics.cpu_usage == 100.0


class TestSystemStatus:
    """Test SystemStatus schema."""

    def test_system_status_valid(self):
        """Test SystemStatus with valid data."""
        status = SystemStatus(
            total_instances=10,
            running_instances=7,
            stopped_instances=2,
            failed_instances=1,
            pending_instances=0,
            system_cpu_usage=45.5,
            system_memory_usage=67.2,
            active_connections=5,
        )

        assert status.total_instances == 10
        assert status.running_instances == 7
        assert status.stopped_instances == 2
        assert status.failed_instances == 1
        assert status.pending_instances == 0
        assert status.system_cpu_usage == 45.5
        assert status.system_memory_usage == 67.2
        assert status.active_connections == 5

    def test_system_status_validation_ranges(self):
        """Test SystemStatus field validation ranges."""
        base_data = {
            "total_instances": 10,
            "running_instances": 7,
            "stopped_instances": 2,
            "failed_instances": 1,
            "pending_instances": 0,
            "system_cpu_usage": 50.0,
            "system_memory_usage": 50.0,
            "active_connections": 5,
        }

        # Test CPU usage range
        with pytest.raises(ValidationError):
            SystemStatus(**{**base_data, "system_cpu_usage": -1.0})

        with pytest.raises(ValidationError):
            SystemStatus(**{**base_data, "system_cpu_usage": 101.0})

        # Test memory usage range
        with pytest.raises(ValidationError):
            SystemStatus(**{**base_data, "system_memory_usage": -1.0})

        with pytest.raises(ValidationError):
            SystemStatus(**{**base_data, "system_memory_usage": 101.0})

        # Test active connections (should be >= 0)
        with pytest.raises(ValidationError):
            SystemStatus(**{**base_data, "active_connections": -1})

    def test_system_status_required_fields(self):
        """Test SystemStatus required fields."""
        base_data = {
            "total_instances": 10,
            "running_instances": 7,
            "stopped_instances": 2,
            "failed_instances": 1,
            "pending_instances": 0,
            "system_cpu_usage": 50.0,
            "system_memory_usage": 50.0,
            "active_connections": 5,
        }

        # Test missing each required field
        required_fields = [
            "total_instances",
            "running_instances",
            "stopped_instances",
            "failed_instances",
            "pending_instances",
            "system_cpu_usage",
            "system_memory_usage",
            "active_connections",
        ]

        for field in required_fields:
            invalid_data = {k: v for k, v in base_data.items() if k != field}
            with pytest.raises(ValidationError):
                SystemStatus(**invalid_data)


class TestSchemaConfiguration:
    """Test schema configuration settings."""

    def test_instance_response_config(self):
        """Test InstanceResponse has from_attributes config."""
        # This tests that the Config class is properly set
        assert hasattr(InstanceResponse, "model_config") or hasattr(
            InstanceResponse, "Config"
        )

        # Test that from_attributes works (would be used with SQLAlchemy models)
        now = datetime.now()
        response = InstanceResponse(
            id=1, issue_id="123", status=InstanceStatus.RUNNING, created_at=now
        )

        # Should be able to convert to dict
        data = response.model_dump()
        assert isinstance(data, dict)
        assert data["id"] == 1
        assert data["issue_id"] == "123"
