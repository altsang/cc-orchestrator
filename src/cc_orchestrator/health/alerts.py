"""Alert system for health monitoring."""

import asyncio
import json
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from ..utils.logging import LogContext, get_logger

logger = get_logger(__name__, LogContext.HEALTH)


class AlertLevel(Enum):
    """Alert severity levels."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class Alert:
    """Alert message."""

    instance_id: str
    level: AlertLevel
    message: str
    timestamp: datetime
    details: dict[str, Any]
    alert_id: str = ""

    def __post_init__(self) -> None:
        """Generate alert ID if not provided."""
        if not self.alert_id:
            self.alert_id = f"{self.instance_id}_{self.level.value}_{int(self.timestamp.timestamp())}"


class AlertHandler(ABC):
    """Abstract base class for alert handlers."""

    @abstractmethod
    async def send_alert(self, alert: Alert) -> bool:
        """Send an alert.

        Args:
            alert: Alert to send

        Returns:
            True if alert was sent successfully
        """
        pass


class LogAlertHandler(AlertHandler):
    """Alert handler that logs alerts."""

    async def send_alert(self, alert: Alert) -> bool:
        """Log the alert."""
        try:
            log_level = {
                AlertLevel.INFO: "info",
                AlertLevel.WARNING: "warning",
                AlertLevel.ERROR: "error",
                AlertLevel.CRITICAL: "error",
            }[alert.level]

            getattr(logger, log_level)(
                f"ALERT: {alert.message}",
                instance_id=alert.instance_id,
                level=alert.level.value,
                alert_id=alert.alert_id,
                details=alert.details,
            )

            return True

        except Exception as e:
            logger.error("Failed to log alert", error=str(e))
            return False


class FileAlertHandler(AlertHandler):
    """Alert handler that writes alerts to a file."""

    def __init__(self, file_path: Path):
        """Initialize file alert handler.

        Args:
            file_path: Path to alert log file
        """
        self.file_path = file_path
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

    async def send_alert(self, alert: Alert) -> bool:
        """Write alert to file."""
        try:
            alert_data = asdict(alert)
            alert_data["timestamp"] = alert.timestamp.isoformat()
            alert_data["level"] = alert.level.value

            alert_json = json.dumps(alert_data)

            # Append to file
            with open(self.file_path, "a") as f:
                f.write(alert_json + "\n")

            return True

        except Exception as e:
            logger.error(
                "Failed to write alert to file",
                file_path=str(self.file_path),
                error=str(e),
            )
            return False


class WebhookAlertHandler(AlertHandler):
    """Alert handler that sends alerts to a webhook."""

    def __init__(self, webhook_url: str, timeout: float = 30.0):
        """Initialize webhook alert handler.

        Args:
            webhook_url: URL to send webhooks to
            timeout: Request timeout in seconds
        """
        self.webhook_url = webhook_url
        self.timeout = timeout

    async def send_alert(self, alert: Alert) -> bool:
        """Send alert to webhook."""
        try:
            import httpx

            alert_data = asdict(alert)
            alert_data["timestamp"] = alert.timestamp.isoformat()
            alert_data["level"] = alert.level.value

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.webhook_url, json=alert_data, timeout=self.timeout
                )

                if response.status_code == 200:
                    return True
                else:
                    logger.error(
                        "Webhook returned error status",
                        url=self.webhook_url,
                        status_code=response.status_code,
                        response=response.text,
                    )
                    return False

        except ImportError:
            logger.error("httpx not available for webhook alerts")
            return False
        except Exception as e:
            logger.error(
                "Failed to send webhook alert", url=self.webhook_url, error=str(e)
            )
            return False


class EmailAlertHandler(AlertHandler):
    """Alert handler that sends email alerts."""

    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        username: str,
        password: str,
        from_email: str,
        to_emails: list[str],
        use_tls: bool = True,
    ):
        """Initialize email alert handler.

        Args:
            smtp_host: SMTP server hostname
            smtp_port: SMTP server port
            username: SMTP username
            password: SMTP password
            from_email: From email address
            to_emails: List of recipient email addresses
            use_tls: Whether to use TLS
        """
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.from_email = from_email
        self.to_emails = to_emails
        self.use_tls = use_tls

    async def send_alert(self, alert: Alert) -> bool:
        """Send email alert."""
        try:
            import smtplib
            from email.mime.multipart import MIMEMultipart
            from email.mime.text import MIMEText

            # Create message
            msg = MIMEMultipart()
            msg["From"] = self.from_email
            msg["To"] = ", ".join(self.to_emails)
            msg["Subject"] = (
                f"[{alert.level.value.upper()}] Claude Instance Alert: {alert.instance_id}"
            )

            # Email body
            body = f"""
Alert Details:
- Instance ID: {alert.instance_id}
- Level: {alert.level.value.upper()}
- Message: {alert.message}
- Timestamp: {alert.timestamp.isoformat()}
- Alert ID: {alert.alert_id}

Additional Details:
{json.dumps(alert.details, indent=2)}
"""

            msg.attach(MIMEText(body, "plain"))

            # Send email
            server = smtplib.SMTP(self.smtp_host, self.smtp_port)
            if self.use_tls:
                server.starttls()
            server.login(self.username, self.password)

            text = msg.as_string()
            server.sendmail(self.from_email, self.to_emails, text)
            server.quit()

            return True

        except ImportError:
            logger.error("smtplib not available for email alerts")
            return False
        except Exception as e:
            logger.error("Failed to send email alert", error=str(e))
            return False


class AlertManager:
    """Manages sending alerts through multiple handlers."""

    def __init__(self, handlers: list[AlertHandler] | None = None):
        """Initialize alert manager.

        Args:
            handlers: List of alert handlers (creates default if None)
        """
        if handlers is None:
            # Default to log handler
            self.handlers = [LogAlertHandler()]
        else:
            self.handlers = handlers

        self._alert_history: list[Alert] = []
        self.max_history = 1000

        logger.info("Alert manager initialized", handler_count=len(self.handlers))

    async def send_alert(
        self,
        instance_id: str,
        level: AlertLevel,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Send an alert through all handlers.

        Args:
            instance_id: Instance identifier
            level: Alert level
            message: Alert message
            details: Additional alert details
        """
        if details is None:
            details = {}

        alert = Alert(
            instance_id=instance_id,
            level=level,
            message=message,
            timestamp=datetime.now(),
            details=details,
        )

        logger.debug(
            "Sending alert",
            instance_id=instance_id,
            level=level.value,
            alert_id=alert.alert_id,
        )

        # Store in history
        self._alert_history.append(alert)
        if len(self._alert_history) > self.max_history:
            self._alert_history.pop(0)

        # Send through all handlers
        tasks = []
        for handler in self.handlers:
            task = asyncio.create_task(self._send_with_handler(handler, alert))
            tasks.append(task)

        # Wait for all handlers to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Log any handler failures
        successful_handlers = sum(1 for result in results if result is True)
        if successful_handlers < len(self.handlers):
            logger.warning(
                "Some alert handlers failed",
                alert_id=alert.alert_id,
                successful=successful_handlers,
                total=len(self.handlers),
            )

    async def _send_with_handler(self, handler: AlertHandler, alert: Alert) -> bool:
        """Send alert with a specific handler.

        Args:
            handler: Alert handler to use
            alert: Alert to send

        Returns:
            True if successful
        """
        try:
            return await handler.send_alert(alert)
        except Exception as e:
            logger.error(
                "Alert handler failed",
                handler=type(handler).__name__,
                alert_id=alert.alert_id,
                error=str(e),
            )
            return False

    def add_handler(self, handler: AlertHandler) -> None:
        """Add an alert handler.

        Args:
            handler: Alert handler to add
        """
        self.handlers.append(handler)
        logger.info("Alert handler added", handler=type(handler).__name__)

    def remove_handler(self, handler: AlertHandler) -> bool:
        """Remove an alert handler.

        Args:
            handler: Alert handler to remove

        Returns:
            True if handler was removed
        """
        try:
            self.handlers.remove(handler)
            logger.info("Alert handler removed", handler=type(handler).__name__)
            return True
        except ValueError:
            return False

    def get_alert_history(
        self,
        instance_id: str | None = None,
        level: AlertLevel | None = None,
        limit: int | None = None,
    ) -> list[Alert]:
        """Get alert history with optional filtering.

        Args:
            instance_id: Filter by instance ID
            level: Filter by alert level
            limit: Maximum number of alerts to return

        Returns:
            List of alerts matching criteria
        """
        alerts = self._alert_history.copy()

        # Apply filters
        if instance_id:
            alerts = [alert for alert in alerts if alert.instance_id == instance_id]

        if level:
            alerts = [alert for alert in alerts if alert.level == level]

        # Sort by timestamp (newest first)
        alerts.sort(key=lambda x: x.timestamp, reverse=True)

        # Apply limit
        if limit:
            alerts = alerts[:limit]

        return alerts

    def clear_alert_history(self, instance_id: str | None = None) -> None:
        """Clear alert history.

        Args:
            instance_id: Clear only alerts for this instance (clears all if None)
        """
        if instance_id:
            self._alert_history = [
                alert
                for alert in self._alert_history
                if alert.instance_id != instance_id
            ]
            logger.info("Alert history cleared for instance", instance_id=instance_id)
        else:
            self._alert_history.clear()
            logger.info("All alert history cleared")
