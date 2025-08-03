"""Add health status tracking to instances table.

Revision ID: 002
Revises: 001
Created: 2025-01-01 00:00:00.000000

"""

from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Connection

from ..migration import Migration


class AddHealthStatusMigration(Migration):
    """Migration to add health status fields to instances table."""

    version = "002"
    description = "Add health status tracking to instances table"
    depends_on = ["001"]

    def up(self, connection: Connection) -> None:
        """Apply the migration."""
        # Add health status enum type
        connection.execute(
            text(
                """
            CREATE TYPE health_status AS ENUM (
                'healthy', 'degraded', 'unhealthy', 'critical', 'unknown'
            )
        """
            )
        )

        # Add health status columns to instances table
        connection.execute(
            text(
                """
            ALTER TABLE instances
            ADD COLUMN health_status health_status DEFAULT 'unknown'
        """
            )
        )

        connection.execute(
            text(
                """
            ALTER TABLE instances
            ADD COLUMN last_health_check TIMESTAMP
        """
            )
        )

        connection.execute(
            text(
                """
            ALTER TABLE instances
            ADD COLUMN health_check_count INTEGER DEFAULT 0
        """
            )
        )

        connection.execute(
            text(
                """
            ALTER TABLE instances
            ADD COLUMN healthy_check_count INTEGER DEFAULT 0
        """
            )
        )

        connection.execute(
            text(
                """
            ALTER TABLE instances
            ADD COLUMN last_recovery_attempt TIMESTAMP
        """
            )
        )

        connection.execute(
            text(
                """
            ALTER TABLE instances
            ADD COLUMN recovery_attempt_count INTEGER DEFAULT 0
        """
            )
        )

        connection.execute(
            text(
                """
            ALTER TABLE instances
            ADD COLUMN health_check_details TEXT
        """
            )
        )

        # Create health status index
        connection.execute(
            text(
                """
            CREATE INDEX idx_instances_health_status
            ON instances (health_status)
        """
            )
        )

        connection.execute(
            text(
                """
            CREATE INDEX idx_instances_last_health_check
            ON instances (last_health_check)
        """
            )
        )

        # Create health_checks table for detailed history
        connection.execute(
            text(
                """
            CREATE TABLE health_checks (
                id SERIAL PRIMARY KEY,
                instance_id INTEGER NOT NULL REFERENCES instances(id) ON DELETE CASCADE,
                check_timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
                overall_status health_status NOT NULL,
                check_results TEXT NOT NULL,
                duration_ms REAL NOT NULL DEFAULT 0.0,
                created_at TIMESTAMP NOT NULL DEFAULT NOW()
            )
        """
            )
        )

        # Create indexes for health_checks table
        connection.execute(
            text(
                """
            CREATE INDEX idx_health_checks_instance_id
            ON health_checks (instance_id)
        """
            )
        )

        connection.execute(
            text(
                """
            CREATE INDEX idx_health_checks_timestamp
            ON health_checks (check_timestamp)
        """
            )
        )

        connection.execute(
            text(
                """
            CREATE INDEX idx_health_checks_status
            ON health_checks (overall_status)
        """
            )
        )

        # Create recovery_attempts table
        connection.execute(
            text(
                """
            CREATE TABLE recovery_attempts (
                id SERIAL PRIMARY KEY,
                instance_id INTEGER NOT NULL REFERENCES instances(id) ON DELETE CASCADE,
                attempt_timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
                strategy VARCHAR(50) NOT NULL,
                success BOOLEAN NOT NULL DEFAULT FALSE,
                error_message TEXT,
                duration_seconds REAL NOT NULL DEFAULT 0.0,
                details TEXT,
                created_at TIMESTAMP NOT NULL DEFAULT NOW()
            )
        """
            )
        )

        # Create indexes for recovery_attempts table
        connection.execute(
            text(
                """
            CREATE INDEX idx_recovery_attempts_instance_id
            ON recovery_attempts (instance_id)
        """
            )
        )

        connection.execute(
            text(
                """
            CREATE INDEX idx_recovery_attempts_timestamp
            ON recovery_attempts (attempt_timestamp)
        """
            )
        )

        connection.execute(
            text(
                """
            CREATE INDEX idx_recovery_attempts_success
            ON recovery_attempts (success)
        """
            )
        )

        # Create alerts table
        connection.execute(
            text(
                """
            CREATE TABLE alerts (
                id SERIAL PRIMARY KEY,
                instance_id INTEGER NOT NULL REFERENCES instances(id) ON DELETE CASCADE,
                alert_id VARCHAR(255) NOT NULL UNIQUE,
                level VARCHAR(20) NOT NULL,
                message TEXT NOT NULL,
                details TEXT,
                timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
                created_at TIMESTAMP NOT NULL DEFAULT NOW()
            )
        """
            )
        )

        # Create indexes for alerts table
        connection.execute(
            text(
                """
            CREATE INDEX idx_alerts_instance_id
            ON alerts (instance_id)
        """
            )
        )

        connection.execute(
            text(
                """
            CREATE INDEX idx_alerts_level
            ON alerts (level)
        """
            )
        )

        connection.execute(
            text(
                """
            CREATE INDEX idx_alerts_timestamp
            ON alerts (timestamp)
        """
            )
        )

        connection.execute(
            text(
                """
            CREATE INDEX idx_alerts_alert_id
            ON alerts (alert_id)
        """
            )
        )

    def down(self, connection: Connection) -> None:
        """Rollback the migration."""
        # Drop tables in reverse order
        connection.execute(text("DROP TABLE IF EXISTS alerts"))
        connection.execute(text("DROP TABLE IF EXISTS recovery_attempts"))
        connection.execute(text("DROP TABLE IF EXISTS health_checks"))

        # Drop indexes
        connection.execute(text("DROP INDEX IF EXISTS idx_instances_last_health_check"))
        connection.execute(text("DROP INDEX IF EXISTS idx_instances_health_status"))

        # Drop columns from instances table
        connection.execute(
            text("ALTER TABLE instances DROP COLUMN IF EXISTS health_check_details")
        )
        connection.execute(
            text("ALTER TABLE instances DROP COLUMN IF EXISTS recovery_attempt_count")
        )
        connection.execute(
            text("ALTER TABLE instances DROP COLUMN IF EXISTS last_recovery_attempt")
        )
        connection.execute(
            text("ALTER TABLE instances DROP COLUMN IF EXISTS healthy_check_count")
        )
        connection.execute(
            text("ALTER TABLE instances DROP COLUMN IF EXISTS health_check_count")
        )
        connection.execute(
            text("ALTER TABLE instances DROP COLUMN IF EXISTS last_health_check")
        )
        connection.execute(
            text("ALTER TABLE instances DROP COLUMN IF EXISTS health_status")
        )

        # Drop enum type
        connection.execute(text("DROP TYPE IF EXISTS health_status"))

    def get_metadata(self) -> dict[str, Any]:
        """Get migration metadata."""
        return {
            "version": self.version,
            "description": self.description,
            "depends_on": self.depends_on,
            "tables_created": ["health_checks", "recovery_attempts", "alerts"],
            "columns_added": [
                "instances.health_status",
                "instances.last_health_check",
                "instances.health_check_count",
                "instances.healthy_check_count",
                "instances.last_recovery_attempt",
                "instances.recovery_attempt_count",
                "instances.health_check_details",
            ],
            "indexes_created": [
                "idx_instances_health_status",
                "idx_instances_last_health_check",
                "idx_health_checks_instance_id",
                "idx_health_checks_timestamp",
                "idx_health_checks_status",
                "idx_recovery_attempts_instance_id",
                "idx_recovery_attempts_timestamp",
                "idx_recovery_attempts_success",
                "idx_alerts_instance_id",
                "idx_alerts_level",
                "idx_alerts_timestamp",
                "idx_alerts_alert_id",
            ],
        }
