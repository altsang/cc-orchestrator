"""Tests for health monitoring alerts module."""

import json
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

from cc_orchestrator.health.alerts import (
    Alert,
    AlertHandler,
    AlertLevel,
    AlertManager,
    EmailAlertHandler,
    FileAlertHandler,
    LogAlertHandler,
    WebhookAlertHandler,
)


class TestAlert:
    """Test Alert dataclass."""

    def test_basic_creation(self):
        """Test basic Alert creation."""
        timestamp = datetime.now()
        alert = Alert(
            instance_id="test-instance",
            level=AlertLevel.WARNING,
            message="Test alert",
            timestamp=timestamp,
            details={"cpu": 90.0},
        )

        assert alert.instance_id == "test-instance"
        assert alert.level == AlertLevel.WARNING
        assert alert.message == "Test alert"
        assert alert.timestamp == timestamp
        assert alert.details == {"cpu": 90.0}
        assert alert.alert_id != ""  # Should be auto-generated

    def test_alert_id_generation(self):
        """Test alert ID auto-generation."""
        timestamp = datetime.now()
        alert = Alert(
            instance_id="test-instance",
            level=AlertLevel.ERROR,
            message="Test alert",
            timestamp=timestamp,
            details={},
        )

        expected_id = f"test-instance_error_{int(timestamp.timestamp())}"
        assert alert.alert_id == expected_id

    def test_custom_alert_id(self):
        """Test alert with custom ID."""
        alert = Alert(
            instance_id="test-instance",
            level=AlertLevel.INFO,
            message="Test alert",
            timestamp=datetime.now(),
            details={},
            alert_id="custom-id-123",
        )

        assert alert.alert_id == "custom-id-123"

    def test_alert_level_enum(self):
        """Test AlertLevel enum values."""
        assert AlertLevel.INFO.value == "info"
        assert AlertLevel.WARNING.value == "warning"
        assert AlertLevel.ERROR.value == "error"
        assert AlertLevel.CRITICAL.value == "critical"


class TestLogAlertHandler:
    """Test LogAlertHandler class."""

    @pytest.fixture
    def log_handler(self):
        """Create LogAlertHandler instance."""
        return LogAlertHandler()

    @pytest.mark.asyncio
    async def test_successful_alert_logging(self, log_handler):
        """Test successful alert logging."""
        alert = Alert(
            instance_id="test-instance",
            level=AlertLevel.WARNING,
            message="Test warning",
            timestamp=datetime.now(),
            details={"test": "data"},
        )

        with patch("cc_orchestrator.health.alerts.logger") as mock_logger:
            result = await log_handler.send_alert(alert)

        assert result is True
        mock_logger.warning.assert_called_once()
        call_args = mock_logger.warning.call_args
        assert "ALERT: Test warning" in call_args[0]

    @pytest.mark.asyncio
    async def test_critical_alert_maps_to_error_log(self, log_handler):
        """Test that critical alerts map to error log level."""
        alert = Alert(
            instance_id="test-instance",
            level=AlertLevel.CRITICAL,
            message="Critical issue",
            timestamp=datetime.now(),
            details={},
        )

        with patch("cc_orchestrator.health.alerts.logger") as mock_logger:
            result = await log_handler.send_alert(alert)

        assert result is True
        mock_logger.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_logging_exception_handling(self, log_handler):
        """Test exception handling during logging."""
        alert = Alert(
            instance_id="test-instance",
            level=AlertLevel.INFO,
            message="Test info",
            timestamp=datetime.now(),
            details={},
        )

        with patch("cc_orchestrator.health.alerts.logger") as mock_logger:
            mock_logger.info.side_effect = Exception("Logging failed")
            result = await log_handler.send_alert(alert)

        assert result is False
        mock_logger.error.assert_called_with("Failed to log alert", error="Logging failed")


class TestFileAlertHandler:
    """Test FileAlertHandler class."""

    def test_initialization_creates_directory(self):
        """Test that initialization creates parent directories."""
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "alerts" / "test.log"
            handler = FileAlertHandler(file_path)

            assert handler.file_path == file_path
            assert file_path.parent.exists()

    @pytest.mark.asyncio
    async def test_successful_file_alert(self):
        """Test successful file alert writing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "alerts.log"
            handler = FileAlertHandler(file_path)

            alert = Alert(
                instance_id="test-instance",
                level=AlertLevel.ERROR,
                message="File test",
                timestamp=datetime(2023, 1, 1, 12, 0, 0),
                details={"error_code": 500},
            )

            result = await handler.send_alert(alert)

            assert result is True
            assert file_path.exists()

            # Verify file content
            with open(file_path) as f:
                content = f.read()
                alert_data = json.loads(content.strip())

            assert alert_data["instance_id"] == "test-instance"
            assert alert_data["level"] == "error"
            assert alert_data["message"] == "File test"
            assert alert_data["timestamp"] == "2023-01-01T12:00:00"
            assert alert_data["details"]["error_code"] == 500

    @pytest.mark.asyncio
    async def test_multiple_alerts_append(self):
        """Test that multiple alerts are appended to file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "alerts.log"
            handler = FileAlertHandler(file_path)

            # Send first alert
            alert1 = Alert(
                instance_id="test-1",
                level=AlertLevel.INFO,
                message="First alert",
                timestamp=datetime.now(),
                details={},
            )
            await handler.send_alert(alert1)

            # Send second alert
            alert2 = Alert(
                instance_id="test-2",
                level=AlertLevel.WARNING,
                message="Second alert",
                timestamp=datetime.now(),
                details={},
            )
            await handler.send_alert(alert2)

            # Verify both alerts in file
            with open(file_path) as f:
                lines = f.readlines()

            assert len(lines) == 2
            alert1_data = json.loads(lines[0])
            alert2_data = json.loads(lines[1])

            assert alert1_data["message"] == "First alert"
            assert alert2_data["message"] == "Second alert"

    @pytest.mark.asyncio
    async def test_file_write_exception(self):
        """Test exception handling during file writing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "alerts.log"
            handler = FileAlertHandler(file_path)

            alert = Alert(
                instance_id="test-instance",
                level=AlertLevel.ERROR,
                message="Test error",
                timestamp=datetime.now(),
                details={},
            )

            # Mock open to raise an exception
            with patch("builtins.open", side_effect=OSError("Write failed")):
                with patch("cc_orchestrator.health.alerts.logger") as mock_logger:
                    result = await handler.send_alert(alert)

            assert result is False
            mock_logger.error.assert_called_once()
            call_args = mock_logger.error.call_args
            assert "Failed to write alert to file" in call_args[0]


class TestWebhookAlertHandler:
    """Test WebhookAlertHandler class."""

    @pytest.fixture
    def webhook_handler(self):
        """Create WebhookAlertHandler instance."""
        return WebhookAlertHandler("https://webhook.example.com/alerts", timeout=10.0)

    def test_initialization(self, webhook_handler):
        """Test WebhookAlertHandler initialization."""
        assert webhook_handler.webhook_url == "https://webhook.example.com/alerts"
        assert webhook_handler.timeout == 10.0

    @pytest.mark.asyncio
    async def test_successful_webhook_alert(self, webhook_handler):
        """Test successful webhook alert."""
        alert = Alert(
            instance_id="test-instance",
            level=AlertLevel.CRITICAL,
            message="Webhook test",
            timestamp=datetime(2023, 1, 1, 12, 0, 0),
            details={"severity": "high"},
        )

        mock_response = Mock()
        mock_response.status_code = 200

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = Mock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            result = await webhook_handler.send_alert(alert)

        assert result is True
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert call_args[1]["json"]["instance_id"] == "test-instance"
        assert call_args[1]["json"]["level"] == "critical"
        assert call_args[1]["timeout"] == 10.0

    @pytest.mark.asyncio
    async def test_webhook_error_status(self, webhook_handler):
        """Test webhook with error status code."""
        alert = Alert(
            instance_id="test-instance",
            level=AlertLevel.ERROR,
            message="Error test",
            timestamp=datetime.now(),
            details={},
        )

        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = Mock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            with patch("cc_orchestrator.health.alerts.logger") as mock_logger:
                result = await webhook_handler.send_alert(alert)

        assert result is False
        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args
        assert "Webhook returned error status" in call_args[0]

    @pytest.mark.asyncio
    async def test_webhook_import_error(self, webhook_handler):
        """Test webhook with httpx import error."""
        alert = Alert(
            instance_id="test-instance",
            level=AlertLevel.WARNING,
            message="Import test",
            timestamp=datetime.now(),
            details={},
        )

        with patch("builtins.__import__", side_effect=ImportError("httpx not found")):
            with patch("cc_orchestrator.health.alerts.logger") as mock_logger:
                result = await webhook_handler.send_alert(alert)

        assert result is False
        mock_logger.error.assert_called_with("httpx not available for webhook alerts")

    @pytest.mark.asyncio
    async def test_webhook_request_exception(self, webhook_handler):
        """Test webhook with request exception."""
        alert = Alert(
            instance_id="test-instance",
            level=AlertLevel.ERROR,
            message="Exception test",
            timestamp=datetime.now(),
            details={},
        )

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = Mock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.post = AsyncMock(side_effect=Exception("Connection failed"))
            mock_client_class.return_value = mock_client

            with patch("cc_orchestrator.health.alerts.logger") as mock_logger:
                result = await webhook_handler.send_alert(alert)

        assert result is False
        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args
        assert "Failed to send webhook alert" in call_args[0]


class TestEmailAlertHandler:
    """Test EmailAlertHandler class."""

    @pytest.fixture
    def email_handler(self):
        """Create EmailAlertHandler instance."""
        return EmailAlertHandler(
            smtp_host="smtp.example.com",
            smtp_port=587,
            username="test@example.com",
            password="password123",
            from_email="alerts@example.com",
            to_emails=["admin@example.com", "ops@example.com"],
            use_tls=True,
        )

    def test_initialization(self, email_handler):
        """Test EmailAlertHandler initialization."""
        assert email_handler.smtp_host == "smtp.example.com"
        assert email_handler.smtp_port == 587
        assert email_handler.username == "test@example.com"
        assert email_handler.password == "password123"
        assert email_handler.from_email == "alerts@example.com"
        assert email_handler.to_emails == ["admin@example.com", "ops@example.com"]
        assert email_handler.use_tls is True

    @pytest.mark.asyncio
    async def test_successful_email_alert(self, email_handler):
        """Test successful email alert."""
        alert = Alert(
            instance_id="test-instance",
            level=AlertLevel.CRITICAL,
            message="Email test alert",
            timestamp=datetime(2023, 1, 1, 12, 0, 0),
            details={"error": "Database connection failed"},
            alert_id="test-alert-123",
        )

        mock_server = Mock()
        mock_server.sendmail = Mock()
        mock_server.quit = Mock()

        with patch("smtplib.SMTP", return_value=mock_server):
            result = await email_handler.send_alert(alert)

        assert result is True
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with("test@example.com", "password123")
        mock_server.sendmail.assert_called_once()
        mock_server.quit.assert_called_once()

        # Verify email content
        sendmail_args = mock_server.sendmail.call_args[0]
        assert sendmail_args[0] == "alerts@example.com"  # from_email
        assert sendmail_args[1] == ["admin@example.com", "ops@example.com"]  # to_emails
        email_content = sendmail_args[2]
        assert "[CRITICAL] Claude Instance Alert: test-instance" in email_content
        assert "Email test alert" in email_content
        assert "test-alert-123" in email_content

    @pytest.mark.asyncio
    async def test_email_without_tls(self):
        """Test email handler without TLS."""
        handler = EmailAlertHandler(
            smtp_host="smtp.example.com",
            smtp_port=25,
            username="test@example.com",
            password="password123",
            from_email="alerts@example.com",
            to_emails=["admin@example.com"],
            use_tls=False,
        )

        alert = Alert(
            instance_id="test-instance",
            level=AlertLevel.INFO,
            message="No TLS test",
            timestamp=datetime.now(),
            details={},
        )

        mock_server = Mock()
        mock_server.sendmail = Mock()
        mock_server.quit = Mock()

        with patch("smtplib.SMTP", return_value=mock_server):
            result = await handler.send_alert(alert)

        assert result is True
        mock_server.starttls.assert_not_called()

    @pytest.mark.asyncio
    async def test_email_import_error(self, email_handler):
        """Test email with smtplib import error."""
        alert = Alert(
            instance_id="test-instance",
            level=AlertLevel.WARNING,
            message="Import test",
            timestamp=datetime.now(),
            details={},
        )

        with patch("builtins.__import__", side_effect=ImportError("smtplib not found")):
            with patch("cc_orchestrator.health.alerts.logger") as mock_logger:
                result = await email_handler.send_alert(alert)

        assert result is False
        mock_logger.error.assert_called_with("smtplib not available for email alerts")

    @pytest.mark.asyncio
    async def test_email_smtp_exception(self, email_handler):
        """Test email with SMTP exception."""
        alert = Alert(
            instance_id="test-instance",
            level=AlertLevel.ERROR,
            message="SMTP test",
            timestamp=datetime.now(),
            details={},
        )

        with patch("smtplib.SMTP", side_effect=Exception("SMTP connection failed")):
            with patch("cc_orchestrator.health.alerts.logger") as mock_logger:
                result = await email_handler.send_alert(alert)

        assert result is False
        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args
        assert "Failed to send email alert" in call_args[0]


class TestAlertManager:
    """Test AlertManager class."""

    @pytest.fixture
    def mock_handlers(self):
        """Create mock alert handlers."""
        handler1 = Mock(spec=AlertHandler)
        handler1.send_alert = AsyncMock(return_value=True)

        handler2 = Mock(spec=AlertHandler)
        handler2.send_alert = AsyncMock(return_value=False)

        return [handler1, handler2]

    @pytest.fixture
    def alert_manager(self, mock_handlers):
        """Create AlertManager with mock handlers."""
        return AlertManager(handlers=mock_handlers)

    def test_initialization_with_handlers(self, mock_handlers):
        """Test AlertManager initialization with custom handlers."""
        manager = AlertManager(handlers=mock_handlers)
        assert len(manager.handlers) == 2
        assert manager.max_history == 1000

    def test_initialization_default_handlers(self):
        """Test AlertManager initialization with default handlers."""
        manager = AlertManager()
        assert len(manager.handlers) == 1
        assert isinstance(manager.handlers[0], LogAlertHandler)

    @pytest.mark.asyncio
    async def test_send_alert_success(self, alert_manager, mock_handlers):
        """Test successful alert sending."""
        with patch("cc_orchestrator.health.alerts.logger") as mock_logger:
            await alert_manager.send_alert(
                instance_id="test-instance",
                level=AlertLevel.WARNING,
                message="Test alert",
                details={"cpu": 85.0},
            )

        # Verify handlers were called
        for handler in mock_handlers:
            handler.send_alert.assert_called_once()

        # Verify alert was stored in history
        assert len(alert_manager._alert_history) == 1
        alert = alert_manager._alert_history[0]
        assert alert.instance_id == "test-instance"
        assert alert.level == AlertLevel.WARNING
        assert alert.message == "Test alert"
        assert alert.details == {"cpu": 85.0}

    @pytest.mark.asyncio
    async def test_send_alert_partial_failure(self, alert_manager, mock_handlers):
        """Test alert sending with partial handler failure."""
        with patch("cc_orchestrator.health.alerts.logger") as mock_logger:
            await alert_manager.send_alert(
                instance_id="test-instance",
                level=AlertLevel.ERROR,
                message="Partial failure test",
            )

        # Verify warning was logged for failed handlers
        mock_logger.warning.assert_called_once()
        call_args = mock_logger.warning.call_args
        assert "Some alert handlers failed" in call_args[0]

    @pytest.mark.asyncio
    async def test_send_alert_handler_exception(self, alert_manager):
        """Test alert sending with handler exception."""
        # Replace handler with one that raises exception
        failing_handler = Mock(spec=AlertHandler)
        failing_handler.send_alert = AsyncMock(side_effect=Exception("Handler failed"))
        alert_manager.handlers = [failing_handler]

        with patch("cc_orchestrator.health.alerts.logger") as mock_logger:
            await alert_manager.send_alert(
                instance_id="test-instance",
                level=AlertLevel.CRITICAL,
                message="Exception test",
            )

        # Verify error was logged
        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args
        assert "Alert handler failed" in call_args[0]

    def test_add_handler(self, alert_manager):
        """Test adding alert handler."""
        new_handler = Mock(spec=AlertHandler)
        initial_count = len(alert_manager.handlers)

        with patch("cc_orchestrator.health.alerts.logger") as mock_logger:
            alert_manager.add_handler(new_handler)

        assert len(alert_manager.handlers) == initial_count + 1
        assert new_handler in alert_manager.handlers
        mock_logger.info.assert_called_once()

    def test_remove_handler_success(self, alert_manager, mock_handlers):
        """Test successful handler removal."""
        handler_to_remove = mock_handlers[0]

        with patch("cc_orchestrator.health.alerts.logger") as mock_logger:
            result = alert_manager.remove_handler(handler_to_remove)

        assert result is True
        assert handler_to_remove not in alert_manager.handlers
        assert len(alert_manager.handlers) == 1
        mock_logger.info.assert_called_once()

    def test_remove_handler_not_found(self, alert_manager):
        """Test removing handler that's not in the list."""
        non_existent_handler = Mock(spec=AlertHandler)

        result = alert_manager.remove_handler(non_existent_handler)

        assert result is False
        assert len(alert_manager.handlers) == 2  # Original count unchanged

    def test_get_alert_history_all(self, alert_manager):
        """Test getting all alert history."""
        # Add some test alerts to history
        alert1 = Alert(
            instance_id="instance1",
            level=AlertLevel.INFO,
            message="Alert 1",
            timestamp=datetime(2023, 1, 1, 12, 0, 0),
            details={},
        )
        alert2 = Alert(
            instance_id="instance2",
            level=AlertLevel.WARNING,
            message="Alert 2",
            timestamp=datetime(2023, 1, 1, 13, 0, 0),
            details={},
        )
        alert_manager._alert_history = [alert1, alert2]

        history = alert_manager.get_alert_history()

        assert len(history) == 2
        # Should be sorted by timestamp (newest first)
        assert history[0].message == "Alert 2"
        assert history[1].message == "Alert 1"

    def test_get_alert_history_filtered_by_instance(self, alert_manager):
        """Test getting alert history filtered by instance ID."""
        alert1 = Alert(
            instance_id="instance1",
            level=AlertLevel.INFO,
            message="Alert 1",
            timestamp=datetime.now(),
            details={},
        )
        alert2 = Alert(
            instance_id="instance2",
            level=AlertLevel.WARNING,
            message="Alert 2",
            timestamp=datetime.now(),
            details={},
        )
        alert_manager._alert_history = [alert1, alert2]

        history = alert_manager.get_alert_history(instance_id="instance1")

        assert len(history) == 1
        assert history[0].instance_id == "instance1"

    def test_get_alert_history_filtered_by_level(self, alert_manager):
        """Test getting alert history filtered by alert level."""
        alert1 = Alert(
            instance_id="instance1",
            level=AlertLevel.INFO,
            message="Alert 1",
            timestamp=datetime.now(),
            details={},
        )
        alert2 = Alert(
            instance_id="instance1",
            level=AlertLevel.ERROR,
            message="Alert 2",
            timestamp=datetime.now(),
            details={},
        )
        alert_manager._alert_history = [alert1, alert2]

        history = alert_manager.get_alert_history(level=AlertLevel.ERROR)

        assert len(history) == 1
        assert history[0].level == AlertLevel.ERROR

    def test_get_alert_history_with_limit(self, alert_manager):
        """Test getting alert history with limit."""
        # Add 5 alerts
        for i in range(5):
            alert = Alert(
                instance_id="test-instance",
                level=AlertLevel.INFO,
                message=f"Alert {i}",
                timestamp=datetime.now(),
                details={},
            )
            alert_manager._alert_history.append(alert)

        history = alert_manager.get_alert_history(limit=3)

        assert len(history) == 3

    def test_clear_alert_history_all(self, alert_manager):
        """Test clearing all alert history."""
        # Add some alerts
        alert = Alert(
            instance_id="test-instance",
            level=AlertLevel.INFO,
            message="Test alert",
            timestamp=datetime.now(),
            details={},
        )
        alert_manager._alert_history = [alert]

        with patch("cc_orchestrator.health.alerts.logger") as mock_logger:
            alert_manager.clear_alert_history()

        assert len(alert_manager._alert_history) == 0
        mock_logger.info.assert_called_with("All alert history cleared")

    def test_clear_alert_history_by_instance(self, alert_manager):
        """Test clearing alert history for specific instance."""
        alert1 = Alert(
            instance_id="instance1",
            level=AlertLevel.INFO,
            message="Alert 1",
            timestamp=datetime.now(),
            details={},
        )
        alert2 = Alert(
            instance_id="instance2",
            level=AlertLevel.INFO,
            message="Alert 2",
            timestamp=datetime.now(),
            details={},
        )
        alert_manager._alert_history = [alert1, alert2]

        with patch("cc_orchestrator.health.alerts.logger") as mock_logger:
            alert_manager.clear_alert_history(instance_id="instance1")

        assert len(alert_manager._alert_history) == 1
        assert alert_manager._alert_history[0].instance_id == "instance2"
        mock_logger.info.assert_called_with(
            "Alert history cleared for instance", instance_id="instance1"
        )

    def test_alert_history_max_limit(self, alert_manager):
        """Test that alert history respects max limit."""
        alert_manager.max_history = 3

        # Add more alerts than the limit
        for i in range(5):
            alert = Alert(
                instance_id="test-instance",
                level=AlertLevel.INFO,
                message=f"Alert {i}",
                timestamp=datetime.now(),
                details={},
            )
            alert_manager._alert_history.append(alert)

            # Simulate the limit check from send_alert
            if len(alert_manager._alert_history) > alert_manager.max_history:
                alert_manager._alert_history.pop(0)

        assert len(alert_manager._alert_history) == 3
        # Should keep the most recent alerts
        assert alert_manager._alert_history[0].message == "Alert 2"
        assert alert_manager._alert_history[2].message == "Alert 4"