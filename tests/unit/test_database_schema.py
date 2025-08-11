"""Tests for database schema utilities."""

from unittest.mock import Mock, PropertyMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from cc_orchestrator.database.models import (
    Base,
    Configuration,
    HealthCheck,
    Instance,
    Task,
    Worktree,
)
from cc_orchestrator.database.schema import (
    create_sample_data,
    export_schema_sql,
    get_model_classes,
    get_schema_version,
    get_table_counts,
    get_table_info,
    validate_schema,
)


class TestSchemaInformation:
    """Test schema information functions."""

    def test_get_schema_version(self):
        """Test getting schema version."""
        version = get_schema_version()
        assert version == "1.0.0"
        assert isinstance(version, str)

    def test_get_table_info(self):
        """Test getting table information."""
        table_info = get_table_info()

        # Check all expected tables are present
        expected_tables = {"instances", "tasks", "worktrees", "configurations"}
        assert set(table_info.keys()) == expected_tables

        # Check instances table info
        instances_info = table_info["instances"]
        assert instances_info["description"] == "Claude Code instance management"
        assert instances_info["primary_key"] == "id"
        assert "issue_id" in instances_info["unique_fields"]
        assert "status" in instances_info["indexed_fields"]
        assert "created_at" in instances_info["indexed_fields"]

        # Check tasks table info
        tasks_info = table_info["tasks"]
        assert tasks_info["description"] == "Work items and task management"
        assert tasks_info["primary_key"] == "id"
        assert "instance_id" in tasks_info["foreign_keys"]
        assert "worktree_id" in tasks_info["foreign_keys"]
        assert "status" in tasks_info["indexed_fields"]
        assert "priority" in tasks_info["indexed_fields"]

        # Check worktrees table info
        worktrees_info = table_info["worktrees"]
        assert worktrees_info["description"] == "Git worktree management"
        assert worktrees_info["primary_key"] == "id"
        assert "path" in worktrees_info["unique_fields"]
        assert "instance_id" in worktrees_info["foreign_keys"]

        # Check configurations table info
        configs_info = table_info["configurations"]
        assert configs_info["description"] == "System and user configuration settings"
        assert configs_info["primary_key"] == "id"
        assert "instance_id" in configs_info["foreign_keys"]

    def test_get_model_classes(self):
        """Test getting model classes."""
        model_classes = get_model_classes()

        # Check all expected model classes are present
        expected_models = {Instance, Task, Worktree, Configuration, HealthCheck}
        assert set(model_classes) == expected_models

        # Check they're all proper model classes
        for model_class in model_classes:
            assert hasattr(model_class, "__tablename__")
            assert hasattr(model_class, "__table__")


class TestSchemaValidation:
    """Test schema validation functions."""

    def test_validate_schema_all_tables_exist(self):
        """Test schema validation when all tables exist."""
        # Create a mock engine and metadata
        mock_engine = Mock(spec=Engine)
        mock_metadata = Mock()

        # Mock table names to match our model table names
        expected_tables = {model.__tablename__ for model in get_model_classes()}
        mock_metadata.tables.keys.return_value = expected_tables

        with patch(
            "cc_orchestrator.database.schema.MetaData", return_value=mock_metadata
        ):
            results = validate_schema(mock_engine)

            # All expected tables should be marked as valid
            for table_name in expected_tables:
                assert results[table_name] is True

            # Should not have unexpected tables
            assert "unexpected_tables" not in results

    def test_validate_schema_missing_tables(self):
        """Test schema validation when tables are missing."""
        mock_engine = Mock(spec=Engine)
        mock_metadata = Mock()

        # Mock missing some tables
        actual_tables = {"instances", "tasks"}  # Missing worktrees and configurations
        mock_metadata.tables.keys.return_value = actual_tables

        with patch(
            "cc_orchestrator.database.schema.MetaData", return_value=mock_metadata
        ):
            results = validate_schema(mock_engine)

            # Present tables should be marked as valid
            assert results["instances"] is True
            assert results["tasks"] is True

            # Missing tables should be marked as invalid
            assert results["worktrees"] is False
            assert results["configurations"] is False

    def test_validate_schema_unexpected_tables(self):
        """Test schema validation with unexpected tables."""
        mock_engine = Mock(spec=Engine)
        mock_metadata = Mock()

        # Mock having extra tables
        expected_tables = {model.__tablename__ for model in get_model_classes()}
        unexpected_tables = {"legacy_table", "temp_table"}
        actual_tables = expected_tables | unexpected_tables
        mock_metadata.tables.keys.return_value = actual_tables

        with patch(
            "cc_orchestrator.database.schema.MetaData", return_value=mock_metadata
        ):
            results = validate_schema(mock_engine)

            # All expected tables should be valid
            for table_name in expected_tables:
                assert results[table_name] is True

            # Unexpected tables should be listed
            assert "unexpected_tables" in results
            assert set(results["unexpected_tables"]) == unexpected_tables


class TestTableCounts:
    """Test table count functions."""

    def test_get_table_counts_success(self):
        """Test getting table counts successfully."""
        mock_engine = Mock(spec=Engine)
        mock_connection = Mock()
        mock_result = Mock()
        mock_result.scalar.return_value = 42
        mock_connection.execute.return_value = mock_result

        # Mock the connection context manager properly
        mock_context = Mock()
        mock_context.__enter__ = Mock(return_value=mock_connection)
        mock_context.__exit__ = Mock(return_value=None)
        mock_engine.connect.return_value = mock_context

        with patch("sqlalchemy.text") as mock_text:
            mock_text.return_value = "SELECT COUNT(*) FROM table_name"

            counts = get_table_counts(mock_engine)

            # All model tables should have counts
            expected_tables = [model.__tablename__ for model in get_model_classes()]
            for table_name in expected_tables:
                assert table_name in counts
                assert counts[table_name] == 42

    def test_get_table_counts_with_exceptions(self):
        """Test getting table counts when some queries fail."""
        mock_engine = Mock(spec=Engine)
        mock_connection = Mock()

        # Mock some queries succeeding and others failing
        def mock_execute(query):
            query_str = str(query)
            if "instances" in query_str:
                mock_result = Mock()
                mock_result.scalar.return_value = 10
                return mock_result
            else:
                raise SQLAlchemyError("Table does not exist")

        mock_connection.execute.side_effect = mock_execute

        # Mock the connection context manager properly
        mock_context = Mock()
        mock_context.__enter__ = Mock(return_value=mock_connection)
        mock_context.__exit__ = Mock(return_value=None)
        mock_engine.connect.return_value = mock_context

        with patch("sqlalchemy.text") as mock_text:
            mock_text.side_effect = lambda sql: Mock(__str__=lambda self: sql)

            counts = get_table_counts(mock_engine)

            # Should have success for instances
            assert counts["instances"] == 10

            # Should have error messages for others
            for table_name in ["tasks", "worktrees", "configurations"]:
                assert table_name in counts
                assert counts[table_name].startswith("Error:")

    def test_get_table_counts_invalid_table_security(self):
        """Test table count security validation."""
        # This test ensures the function validates table names against known models
        # The actual implementation should prevent SQL injection
        mock_engine = Mock(spec=Engine)
        mock_connection = Mock()
        mock_result = Mock()
        mock_result.scalar.return_value = 5
        mock_connection.execute.return_value = mock_result

        # Mock the connection context manager properly
        mock_context = Mock()
        mock_context.__enter__ = Mock(return_value=mock_connection)
        mock_context.__exit__ = Mock(return_value=None)
        mock_engine.connect.return_value = mock_context

        with patch("sqlalchemy.text") as mock_text:
            mock_text.return_value = "SELECT COUNT(*) FROM table_name"

            # This should work normally since we only query valid model table names
            counts = get_table_counts(mock_engine)

            # Verify only valid table names are queried
            expected_tables = [model.__tablename__ for model in get_model_classes()]
            for table_name in counts.keys():
                assert table_name in expected_tables

    def test_get_table_counts_with_invalid_table_name(self):
        """Test table count security validation for invalid table names."""
        mock_engine = Mock(spec=Engine)
        mock_connection = Mock()

        # Mock the connection context manager
        mock_context = Mock()
        mock_context.__enter__ = Mock(return_value=mock_connection)
        mock_context.__exit__ = Mock(return_value=None)
        mock_engine.connect.return_value = mock_context

        # Create a mock model class with suspicious table name
        class FakeModel:
            __tablename__ = "suspicious_table"

        # Mock get_model_classes to return only valid models (excluding FakeModel)
        valid_models = [Instance, Task, Worktree, Configuration, HealthCheck]

        with patch(
            "cc_orchestrator.database.schema.get_model_classes"
        ) as mock_get_models:
            # First call returns FakeModel (from table_names = [model.__tablename__ for model in get_model_classes()])
            # Second call returns valid models (from valid_table_names = [table.__tablename__ for table in get_model_classes()])
            mock_get_models.side_effect = [
                [FakeModel],  # This creates the table_names list
                valid_models,  # This creates the valid_table_names list for comparison
            ]

            counts = get_table_counts(mock_engine)

            # Should return error for the suspicious table name that's not in valid models
            assert "suspicious_table" in counts
            assert counts["suspicious_table"] == "Error: Invalid table name"


class TestSampleDataCreation:
    """Test sample data creation."""

    @patch("sqlalchemy.orm.Session")
    @patch("tempfile.gettempdir")
    def test_create_sample_data(self, mock_gettempdir, mock_session_class):
        """Test creating sample data."""
        # Mock temporary directory
        mock_gettempdir.return_value = "/tmp"

        # Mock database session
        mock_session = Mock()
        mock_session_class.return_value.__enter__.return_value = mock_session

        # Mock instance to have an ID after flush
        mock_instance = Mock()
        mock_instance.id = "test-instance-id"

        # Mock worktree to have an ID after flush
        mock_worktree = Mock()
        mock_worktree.id = "test-worktree-id"

        def mock_flush():
            # Simulate database assigning IDs
            pass

        mock_session.flush.side_effect = mock_flush
        mock_session.add.side_effect = lambda obj: setattr(
            obj, "id", f"{type(obj).__name__.lower()}-id"
        )

        mock_engine = Mock(spec=Engine)

        # This should complete without errors
        create_sample_data(mock_engine)

        # Verify session operations were called
        assert mock_session.add.call_count > 0  # Should add multiple objects
        mock_session.commit.assert_called_once()
        mock_session.flush.assert_called()

    @patch("sqlalchemy.orm.Session")
    def test_create_sample_data_with_session_error(self, mock_session_class):
        """Test sample data creation with database errors."""
        mock_session = Mock()
        mock_session_class.return_value.__enter__.return_value = mock_session

        # Mock a database error during commit
        mock_session.commit.side_effect = SQLAlchemyError("Database error")

        mock_engine = Mock(spec=Engine)

        # Should raise the database error
        with pytest.raises(SQLAlchemyError, match="Database error"):
            create_sample_data(mock_engine)


class TestSchemaExport:
    """Test schema export functions."""

    def test_export_schema_sql(self):
        """Test exporting schema as SQL DDL."""
        mock_engine = Mock(spec=Engine)
        mock_table = Mock()
        mock_create_table = Mock()
        mock_compiled = Mock()
        mock_compiled.__str__ = Mock(return_value="CREATE TABLE test_table (...)")
        mock_create_table.compile.return_value = mock_compiled

        with patch("sqlalchemy.schema.CreateTable", return_value=mock_create_table):
            # Mock the sorted_tables property using PropertyMock
            with patch.object(
                type(Base.metadata), "sorted_tables", new_callable=PropertyMock
            ) as mock_sorted_tables:
                mock_sorted_tables.return_value = [mock_table]
                result = export_schema_sql(mock_engine)

                assert isinstance(result, str)
                assert result.endswith(";")

    def test_export_schema_sql_multiple_tables(self):
        """Test exporting multiple tables."""
        mock_engine = Mock(spec=Engine)

        # Mock multiple tables
        mock_tables = [Mock(), Mock()]

        mock_create_statements = [
            "CREATE TABLE table1 (...)",
            "CREATE TABLE table2 (...)",
        ]

        with patch("sqlalchemy.schema.CreateTable") as mock_create_table_class:
            mock_create_instances = []
            for statement in mock_create_statements:
                mock_create = Mock()
                mock_compiled = Mock()
                mock_compiled.__str__ = Mock(return_value=statement)
                mock_create.compile.return_value = mock_compiled
                mock_create_instances.append(mock_create)

            mock_create_table_class.side_effect = mock_create_instances

            # Mock the sorted_tables property using PropertyMock
            with patch.object(
                type(Base.metadata), "sorted_tables", new_callable=PropertyMock
            ) as mock_sorted_tables:
                mock_sorted_tables.return_value = mock_tables
                result = export_schema_sql(mock_engine)

                assert isinstance(result, str)
                assert "CREATE TABLE table1" in result
                assert "CREATE TABLE table2" in result
                assert result.endswith(";")
                # Should join with semicolons and newlines
                assert ";\n\n" in result


class TestIntegrationWithRealDatabase:
    """Integration tests with real SQLite database."""

    def test_schema_validation_with_real_database(self):
        """Test schema validation with actual database."""
        # Create temporary in-memory database
        engine = create_engine("sqlite:///:memory:")

        # Create all tables
        Base.metadata.create_all(engine)

        # Validate schema
        results = validate_schema(engine)

        # All tables should exist
        expected_tables = {model.__tablename__ for model in get_model_classes()}
        for table_name in expected_tables:
            assert results[table_name] is True

        # Should not have unexpected tables
        assert "unexpected_tables" not in results

    def test_table_counts_with_real_database(self):
        """Test table counts with actual database."""
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)

        # Get counts (should all be 0)
        counts = get_table_counts(engine)

        expected_tables = [model.__tablename__ for model in get_model_classes()]
        for table_name in expected_tables:
            assert table_name in counts
            assert counts[table_name] == 0

    def test_create_sample_data_integration(self):
        """Test creating sample data with real database."""
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)

        # Create sample data
        create_sample_data(engine)

        # Verify data was created
        counts = get_table_counts(engine)

        # Should have data in all tables
        assert counts["instances"] > 0
        assert counts["tasks"] > 0
        assert counts["worktrees"] > 0
        assert counts["configurations"] > 0

    def test_export_schema_sql_integration(self):
        """Test schema export with real database."""
        engine = create_engine("sqlite:///:memory:")

        # Export schema
        sql_ddl = export_schema_sql(engine)

        # Should contain CREATE TABLE statements
        assert "CREATE TABLE" in sql_ddl
        assert sql_ddl.endswith(";")

        # Should contain all expected tables
        expected_tables = [model.__tablename__ for model in get_model_classes()]
        for table_name in expected_tables:
            assert table_name in sql_ddl


class TestErrorHandling:
    """Test error handling in schema functions."""

    def test_validate_schema_metadata_reflection_error(self):
        """Test schema validation when metadata reflection fails."""
        mock_engine = Mock(spec=Engine)

        with patch("cc_orchestrator.database.schema.MetaData") as mock_metadata_class:
            mock_metadata = Mock()
            mock_metadata.reflect.side_effect = SQLAlchemyError(
                "Cannot connect to database"
            )
            mock_metadata_class.return_value = mock_metadata

            with pytest.raises(SQLAlchemyError, match="Cannot connect to database"):
                validate_schema(mock_engine)

    def test_get_table_counts_connection_error(self):
        """Test table counts with connection error."""
        mock_engine = Mock(spec=Engine)
        mock_engine.connect.side_effect = SQLAlchemyError("Connection failed")

        with pytest.raises(SQLAlchemyError, match="Connection failed"):
            get_table_counts(mock_engine)
