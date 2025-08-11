"""Tests for database migration system."""

from datetime import datetime
from unittest.mock import Mock

import pytest
from sqlalchemy.engine import Engine

from cc_orchestrator.database.migrations.migration import Migration, MigrationRecord


class MockMigration(Migration):
    """Mock migration class for testing."""

    def __init__(self, version: str, description: str):
        super().__init__(version, description)
        self.upgrade_called = False
        self.downgrade_called = False
        self.upgrade_engine = None
        self.downgrade_engine = None

    def upgrade(self, engine: Engine) -> None:
        """Mock upgrade implementation."""
        self.upgrade_called = True
        self.upgrade_engine = engine

    def downgrade(self, engine: Engine) -> None:
        """Mock downgrade implementation."""
        self.downgrade_called = True
        self.downgrade_engine = engine


class FailingMigration(Migration):
    """Migration that fails for testing error handling."""

    def upgrade(self, engine: Engine) -> None:
        """Raise exception during upgrade."""
        raise RuntimeError("Migration failed")

    def downgrade(self, engine: Engine) -> None:
        """Raise exception during downgrade."""
        raise RuntimeError("Downgrade failed")


class TestMigration:
    """Test Migration base class."""

    def test_migration_initialization(self):
        """Test Migration initialization."""
        version = "001"
        description = "Create initial tables"

        migration = MockMigration(version, description)

        assert migration.version == version
        assert migration.description == description
        assert isinstance(migration.created_at, datetime)
        assert not migration.upgrade_called
        assert not migration.downgrade_called

    def test_migration_str_representation(self):
        """Test Migration string representation."""
        migration = MockMigration("001", "Create initial tables")

        expected = "Migration 001: Create initial tables"
        assert str(migration) == expected

    def test_migration_repr_representation(self):
        """Test Migration repr representation."""
        migration = MockMigration("001", "Create initial tables")

        expected = "<Migration(version='001', description='Create initial tables')>"
        assert repr(migration) == expected

    def test_migration_upgrade(self):
        """Test Migration upgrade method."""
        migration = MockMigration("001", "Create initial tables")
        mock_engine = Mock(spec=Engine)

        migration.upgrade(mock_engine)

        assert migration.upgrade_called
        assert migration.upgrade_engine is mock_engine
        assert not migration.downgrade_called

    def test_migration_downgrade(self):
        """Test Migration downgrade method."""
        migration = MockMigration("001", "Create initial tables")
        mock_engine = Mock(spec=Engine)

        migration.downgrade(mock_engine)

        assert migration.downgrade_called
        assert migration.downgrade_engine is mock_engine
        assert not migration.upgrade_called

    def test_migration_upgrade_failure(self):
        """Test Migration upgrade failure handling."""
        migration = FailingMigration("001", "Failing migration")
        mock_engine = Mock(spec=Engine)

        with pytest.raises(RuntimeError, match="Migration failed"):
            migration.upgrade(mock_engine)

    def test_migration_downgrade_failure(self):
        """Test Migration downgrade failure handling."""
        migration = FailingMigration("001", "Failing migration")
        mock_engine = Mock(spec=Engine)

        with pytest.raises(RuntimeError, match="Downgrade failed"):
            migration.downgrade(mock_engine)

    def test_migration_abstract_methods(self):
        """Test that Migration is abstract and cannot be instantiated."""
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            Migration("001", "Abstract migration")

    def test_migration_version_comparison_preparation(self):
        """Test migrations can be created with different versions for comparison."""
        migration1 = MockMigration("001", "First migration")
        migration2 = MockMigration("002", "Second migration")
        migration3 = MockMigration("010", "Tenth migration")

        # Verify versions are strings and can be compared
        assert migration1.version < migration2.version
        assert migration2.version < migration3.version
        assert migration1.version != migration2.version

    def test_migration_creation_time(self):
        """Test migration creation time tracking."""
        start_time = datetime.now()
        migration = MockMigration("001", "Test migration")
        end_time = datetime.now()

        assert start_time <= migration.created_at <= end_time

    def test_multiple_migration_operations(self):
        """Test performing multiple operations on a migration."""
        migration = MockMigration("001", "Multi-op migration")
        engine1 = Mock(spec=Engine)
        engine2 = Mock(spec=Engine)

        # Perform upgrade
        migration.upgrade(engine1)
        assert migration.upgrade_called
        assert migration.upgrade_engine is engine1

        # Perform downgrade
        migration.downgrade(engine2)
        assert migration.downgrade_called
        assert migration.downgrade_engine is engine2

        # Both operations should be recorded
        assert migration.upgrade_called and migration.downgrade_called


class TestMigrationRecord:
    """Test MigrationRecord class."""

    def setup_method(self):
        """Reset MigrationRecord.table before each test."""
        from cc_orchestrator.database.migrations.migration import MigrationRecord

        MigrationRecord.table = None

    def test_migration_record_initialization_minimal(self):
        """Test MigrationRecord initialization with minimal parameters."""
        version = "001"
        description = "Create initial tables"

        record = MigrationRecord(version, description)

        assert record.version == version
        assert record.description == description
        assert isinstance(record.applied_at, datetime)
        assert record.checksum is None

    def test_migration_record_initialization_full(self):
        """Test MigrationRecord initialization with all parameters."""
        version = "002"
        description = "Add user authentication"
        applied_at = datetime(2025, 1, 15, 12, 0, 0)
        checksum = "abc123def456"

        record = MigrationRecord(
            version=version,
            description=description,
            applied_at=applied_at,
            checksum=checksum,
        )

        assert record.version == version
        assert record.description == description
        assert record.applied_at == applied_at
        assert record.checksum == checksum

    def test_migration_record_default_applied_at(self):
        """Test MigrationRecord uses current time when applied_at not provided."""
        start_time = datetime.now()
        record = MigrationRecord("001", "Test migration")
        end_time = datetime.now()

        assert start_time <= record.applied_at <= end_time

    def test_migration_record_str_representation(self):
        """Test MigrationRecord string representation."""
        record = MigrationRecord("001", "Create initial tables")

        expected = "MigrationRecord 001: Create initial tables"
        assert str(record) == expected

    def test_migration_record_repr_representation(self):
        """Test MigrationRecord repr representation."""
        applied_at = datetime(2025, 1, 15, 12, 0, 0)
        record = MigrationRecord("001", "Create initial tables", applied_at=applied_at)

        expected = "<MigrationRecord(version='001', applied_at='2025-01-15 12:00:00')>"
        assert repr(record) == expected

    def test_migration_record_with_checksum(self):
        """Test MigrationRecord with checksum verification data."""
        version = "003"
        description = "Add indexes"
        checksum = "sha256:abcdef123456789"

        record = MigrationRecord(version, description, checksum=checksum)

        assert record.checksum == checksum
        assert record.version == version
        assert record.description == description

    def test_migration_record_equality_preparation(self):
        """Test MigrationRecord properties for potential equality comparisons."""
        record1 = MigrationRecord("001", "First migration")
        record2 = MigrationRecord("001", "First migration")
        record3 = MigrationRecord("002", "Second migration")

        # Verify records have the same basic properties for version comparison
        assert record1.version == record2.version
        assert record1.description == record2.description
        assert record1.version != record3.version

    def test_migration_record_table_class_attribute(self):
        """Test MigrationRecord table class attribute."""
        # Verify the table class attribute exists and is initially None
        assert hasattr(MigrationRecord, "table")
        assert MigrationRecord.table is None

        # Test that it can be set (would be done by migration manager)
        mock_table = Mock()
        MigrationRecord.table = mock_table
        assert MigrationRecord.table is mock_table

        # Clean up
        MigrationRecord.table = None

    def test_migration_record_with_none_values(self):
        """Test MigrationRecord handles None values appropriately."""
        record = MigrationRecord(
            version="001",
            description="Test migration",
            applied_at=None,  # Should use current time
            checksum=None,  # Should remain None
        )

        assert record.version == "001"
        assert record.description == "Test migration"
        assert isinstance(record.applied_at, datetime)
        assert record.checksum is None

    def test_migration_record_empty_checksum(self):
        """Test MigrationRecord with empty string checksum."""
        record = MigrationRecord(
            version="001",
            description="Test migration",
            checksum="",
        )

        assert record.checksum == ""
        assert record.version == "001"


class TestMigrationIntegration:
    """Test integration between Migration and MigrationRecord."""

    def test_migration_to_record_conversion_pattern(self):
        """Test pattern for converting Migration to MigrationRecord."""
        migration = MockMigration("001", "Create initial schema")

        # Simulate conversion pattern that might be used by migration manager
        record = MigrationRecord(
            version=migration.version,
            description=migration.description,
            applied_at=datetime.now(),
            checksum="calculated_checksum",
        )

        assert record.version == migration.version
        assert record.description == migration.description
        assert isinstance(record.applied_at, datetime)
        assert record.checksum == "calculated_checksum"

    def test_migration_version_ordering(self):
        """Test that migration versions can be ordered consistently."""
        migrations = [
            MockMigration("010", "Tenth migration"),
            MockMigration("001", "First migration"),
            MockMigration("002", "Second migration"),
            MockMigration("005", "Fifth migration"),
        ]

        # Sort migrations by version
        sorted_migrations = sorted(migrations, key=lambda m: m.version)

        expected_order = ["001", "002", "005", "010"]
        actual_order = [m.version for m in sorted_migrations]

        assert actual_order == expected_order

    def test_migration_record_version_ordering(self):
        """Test that migration record versions can be ordered consistently."""
        records = [
            MigrationRecord("010", "Tenth migration"),
            MigrationRecord("001", "First migration"),
            MigrationRecord("002", "Second migration"),
            MigrationRecord("005", "Fifth migration"),
        ]

        # Sort records by version
        sorted_records = sorted(records, key=lambda r: r.version)

        expected_order = ["001", "002", "005", "010"]
        actual_order = [r.version for r in sorted_records]

        assert actual_order == expected_order

    def test_migration_lifecycle_simulation(self):
        """Test complete migration lifecycle simulation."""
        # Create migration
        migration = MockMigration("001", "Initial schema")
        mock_engine = Mock(spec=Engine)

        # Apply migration
        migration.upgrade(mock_engine)
        assert migration.upgrade_called

        # Create record of applied migration
        record = MigrationRecord(
            version=migration.version,
            description=migration.description,
            applied_at=datetime.now(),
        )

        # Verify record matches migration
        assert record.version == migration.version
        assert record.description == migration.description

        # Simulate rollback
        migration.downgrade(mock_engine)
        assert migration.downgrade_called

    def test_error_handling_in_migration_workflow(self):
        """Test error handling in migration workflow."""
        migration = FailingMigration("001", "Problematic migration")
        mock_engine = Mock(spec=Engine)

        # Test upgrade failure
        with pytest.raises(RuntimeError, match="Migration failed"):
            migration.upgrade(mock_engine)

        # Test downgrade failure
        with pytest.raises(RuntimeError, match="Downgrade failed"):
            migration.downgrade(mock_engine)

        # Verify no record should be created for failed migrations
        # (This would be handled by the migration manager)
        assert migration.version == "001"
        assert migration.description == "Problematic migration"


class TestMigrationEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_migration_with_special_characters(self):
        """Test migration with special characters in description."""
        special_desc = "Add field with 'quotes' and \"double quotes\" & symbols"
        migration = MockMigration("001", special_desc)

        assert migration.description == special_desc
        assert str(migration) == f"Migration 001: {special_desc}"

    def test_migration_with_long_version_string(self):
        """Test migration with long version string."""
        long_version = "001_020_300_4000"
        migration = MockMigration(long_version, "Test migration")

        assert migration.version == long_version
        assert str(migration) == f"Migration {long_version}: Test migration"

    def test_migration_record_with_very_long_description(self):
        """Test MigrationRecord with very long description."""
        long_desc = "A" * 1000  # 1000 character description
        record = MigrationRecord("001", long_desc)

        assert record.description == long_desc
        assert len(record.description) == 1000

    def test_migration_with_unicode_characters(self):
        """Test migration with unicode characters."""
        unicode_desc = "Add support for émojis 🎉 and ñoñó characters"
        migration = MockMigration("001", unicode_desc)
        record = MigrationRecord("001", unicode_desc)

        assert migration.description == unicode_desc
        assert record.description == unicode_desc
        assert str(migration) == f"Migration 001: {unicode_desc}"

    def test_migration_record_with_microseconds(self):
        """Test MigrationRecord with datetime including microseconds."""
        precise_time = datetime(2025, 1, 15, 12, 30, 45, 123456)
        record = MigrationRecord(
            "001", "Precise timing migration", applied_at=precise_time
        )

        assert record.applied_at == precise_time
        assert record.applied_at.microsecond == 123456
