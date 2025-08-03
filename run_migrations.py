#!/usr/bin/env python3
"""Simple script to run database migrations."""

import sys
from pathlib import Path

# Add src to path to import cc_orchestrator modules
sys.path.insert(0, str(Path(__file__).parent / "src"))

from cc_orchestrator.database.connection import DatabaseManager
from cc_orchestrator.database.migrations.manager import MigrationManager


def main():
    """Run database migrations."""
    print("Running database migrations...")

    # Create database manager
    db_manager = DatabaseManager()

    # Create migration manager
    migration_manager = MigrationManager(db_manager.engine)

    # Get migration status
    status = migration_manager.get_migration_status()
    print(f"Current version: {status['current_version']}")
    print(f"Applied migrations: {status['applied_count']}")
    print(f"Pending migrations: {status['pending_count']}")

    if status["pending_count"] > 0:
        print("\nApplying pending migrations:")
        for migration in status["pending_migrations"]:
            print(f"  - {migration['version']}: {migration['description']}")

        # Apply migrations
        success = migration_manager.migrate_up()
        if success:
            print("\nMigrations applied successfully!")
        else:
            print("\nFailed to apply migrations!")
            return 1
    else:
        print("\nNo pending migrations to apply.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
