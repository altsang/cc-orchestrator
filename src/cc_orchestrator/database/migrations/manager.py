"""Migration management system."""

import hashlib
import importlib.util
import inspect
from pathlib import Path

from sqlalchemy import MetaData, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from .migration import Migration, MigrationRecord


class MigrationManager:
    """Manages database migrations."""

    def __init__(self, engine: Engine, migrations_dir: Path | None = None) -> None:
        """Initialize migration manager.

        Args:
            engine: Database engine.
            migrations_dir: Directory containing migration files.
        """
        self.engine = engine
        self.migrations_dir = migrations_dir or self._get_default_migrations_dir()
        self.metadata = MetaData()

        # Set up the migration tracking table
        self._create_migration_table()
        self._ensure_migration_table()

    def _get_default_migrations_dir(self) -> Path:
        """Get the default migrations directory."""
        return Path(__file__).parent / "versions"

    def _create_migration_table(self) -> None:
        """Create the migration tracking table definition."""
        from datetime import datetime

        from sqlalchemy import Column, DateTime, Integer, String, Table

        MigrationRecord.table = Table(
            "schema_migrations",
            self.metadata,
            Column("id", Integer, primary_key=True),
            Column("version", String(50), unique=True, nullable=False),
            Column("description", String(255), nullable=False),
            Column("applied_at", DateTime, nullable=False, default=datetime.now),
            Column("checksum", String(64), nullable=True),
        )

    def _ensure_migration_table(self) -> None:
        """Ensure the migration tracking table exists."""
        try:
            MigrationRecord.table.create(self.engine, checkfirst=True)
        except SQLAlchemyError as e:
            raise RuntimeError(f"Failed to create migration table: {e}") from e

    def get_applied_migrations(self) -> list[MigrationRecord]:
        """Get list of applied migrations.

        Returns:
            List of applied migration records, ordered by application time.
        """
        with Session(self.engine) as session:
            result = session.execute(
                text(
                    "SELECT version, description, applied_at, checksum "
                    "FROM schema_migrations ORDER BY applied_at"
                )
            )

            records = []
            for row in result:
                # Convert string datetime back to datetime object if needed
                applied_at = row.applied_at
                if isinstance(applied_at, str):
                    from datetime import datetime

                    try:
                        applied_at = datetime.fromisoformat(
                            applied_at.replace("Z", "+00:00")
                        )
                    except ValueError:
                        # Try parsing without timezone info
                        applied_at = datetime.fromisoformat(applied_at)

                records.append(
                    MigrationRecord(
                        version=row.version,
                        description=row.description,
                        applied_at=applied_at,
                        checksum=row.checksum,
                    )
                )

            return records

    def get_pending_migrations(self) -> list[Migration]:
        """Get list of pending migrations.

        Returns:
            List of migrations that haven't been applied yet.
        """
        applied_versions = {record.version for record in self.get_applied_migrations()}
        available_migrations = self.discover_migrations()

        return [
            migration
            for migration in available_migrations
            if migration.version not in applied_versions
        ]

    def discover_migrations(self) -> list[Migration]:
        """Discover migration files in the migrations directory.

        Returns:
            List of available migrations, sorted by version.
        """
        if not self.migrations_dir.exists():
            return []

        migrations = []

        for migration_file in self.migrations_dir.glob("*.py"):
            if migration_file.name.startswith("__"):
                continue

            try:
                migration = self._load_migration_from_file(migration_file)
                if migration:
                    migrations.append(migration)
            except Exception as e:
                print(f"Warning: Failed to load migration from {migration_file}: {e}")

        # Sort by version
        migrations.sort(key=lambda m: m.version)
        return migrations

    def _load_migration_from_file(self, migration_file: Path) -> Migration | None:
        """Load a migration from a Python file.

        Args:
            migration_file: Path to the migration file.

        Returns:
            Migration instance or None if not found.
        """
        spec = importlib.util.spec_from_file_location("migration", migration_file)
        if spec is None or spec.loader is None:
            return None

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Look for Migration subclass in the module
        for _name, obj in inspect.getmembers(module):
            if (
                inspect.isclass(obj)
                and issubclass(obj, Migration)
                and obj is not Migration
            ):
                return obj()

        return None

    def _calculate_file_checksum(self, migration_file: Path) -> str:
        """Calculate checksum for a migration file.

        Args:
            migration_file: Path to the migration file.

        Returns:
            SHA-256 checksum of the file.
        """
        return hashlib.sha256(migration_file.read_bytes()).hexdigest()

    def apply_migration(self, migration: Migration) -> bool:
        """Apply a single migration.

        Args:
            migration: Migration to apply.

        Returns:
            True if successful, False otherwise.
        """
        try:
            with self.engine.begin() as conn:
                # Apply the migration
                migration.upgrade(self.engine)

                # Record the migration
                conn.execute(
                    text(
                        "INSERT INTO schema_migrations "
                        "(version, description, applied_at) "
                        "VALUES (:version, :description, :applied_at)"
                    ),
                    {
                        "version": migration.version,
                        "description": migration.description,
                        "applied_at": migration.created_at,
                    },
                )

            print(f"Applied migration {migration.version}: {migration.description}")
            return True

        except Exception as e:
            print(f"Failed to apply migration {migration.version}: {e}")
            return False

    def rollback_migration(self, migration: Migration) -> bool:
        """Rollback a single migration.

        Args:
            migration: Migration to rollback.

        Returns:
            True if successful, False otherwise.
        """
        try:
            with self.engine.begin() as conn:
                # Rollback the migration
                migration.downgrade(self.engine)

                # Remove the migration record
                conn.execute(
                    text("DELETE FROM schema_migrations WHERE version = :version"),
                    {"version": migration.version},
                )

            print(f"Rolled back migration {migration.version}: {migration.description}")
            return True

        except Exception as e:
            print(f"Failed to rollback migration {migration.version}: {e}")
            return False

    def migrate_up(self, target_version: str | None = None) -> bool:
        """Apply pending migrations up to a target version.

        Args:
            target_version: Version to migrate to. If None, applies all pending.

        Returns:
            True if all migrations applied successfully.
        """
        pending = self.get_pending_migrations()

        if target_version:
            # Filter to only migrations up to target version
            pending = [m for m in pending if m.version <= target_version]

        if not pending:
            print("No pending migrations to apply.")
            return True

        success = True
        for migration in pending:
            if not self.apply_migration(migration):
                success = False
                break

        return success

    def migrate_down(self, target_version: str) -> bool:
        """Rollback migrations down to a target version.

        Args:
            target_version: Version to rollback to.

        Returns:
            True if all rollbacks successful.
        """
        applied = self.get_applied_migrations()

        # Find migrations to rollback (in reverse order)
        to_rollback = [
            record for record in reversed(applied) if record.version > target_version
        ]

        if not to_rollback:
            print(f"Already at or below version {target_version}.")
            return True

        # Load migration objects for rollback
        available_migrations = {m.version: m for m in self.discover_migrations()}

        success = True
        for record in to_rollback:
            migration = available_migrations.get(record.version)
            if migration is None:
                print(
                    f"Warning: Migration file for version {record.version} not found."
                )
                continue

            if not self.rollback_migration(migration):
                success = False
                break

        return success

    def get_current_version(self) -> str | None:
        """Get the current database version.

        Returns:
            Current version string or None if no migrations applied.
        """
        applied = self.get_applied_migrations()
        return applied[-1].version if applied else None

    def get_migration_status(self) -> dict[str, any]:
        """Get detailed migration status information.

        Returns:
            Dictionary with migration status details.
        """
        applied = self.get_applied_migrations()
        pending = self.get_pending_migrations()

        return {
            "current_version": self.get_current_version(),
            "applied_count": len(applied),
            "pending_count": len(pending),
            "applied_migrations": [
                {
                    "version": record.version,
                    "description": record.description,
                    "applied_at": record.applied_at.isoformat(),
                }
                for record in applied
            ],
            "pending_migrations": [
                {
                    "version": migration.version,
                    "description": migration.description,
                }
                for migration in pending
            ],
        }
