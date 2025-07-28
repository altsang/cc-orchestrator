"""Database schema definitions and utilities."""

from typing import Dict, List

from sqlalchemy import MetaData, Table
from sqlalchemy.engine import Engine

from .models import Base, Configuration, Instance, Task, Worktree


def get_schema_version() -> str:
    """Get the current database schema version."""
    return "1.0.0"


def get_table_info() -> Dict[str, Dict[str, str]]:
    """Get information about all database tables.
    
    Returns:
        Dictionary with table names as keys and table info as values.
    """
    return {
        "instances": {
            "description": "Claude Code instance management",
            "primary_key": "id",
            "unique_fields": ["issue_id"],
            "indexed_fields": ["status", "created_at"],
        },
        "tasks": {
            "description": "Work items and task management",
            "primary_key": "id",
            "foreign_keys": ["instance_id", "worktree_id"],
            "indexed_fields": ["status", "priority", "created_at", "due_date"],
        },
        "worktrees": {
            "description": "Git worktree management",
            "primary_key": "id",
            "unique_fields": ["path"],
            "foreign_keys": ["instance_id"],
            "indexed_fields": ["branch_name", "status"],
        },
        "configurations": {
            "description": "System and user configuration settings",
            "primary_key": "id",
            "foreign_keys": ["instance_id"],
            "indexed_fields": ["key", "scope"],
        },
    }


def get_model_classes() -> List[type]:
    """Get all SQLAlchemy model classes.
    
    Returns:
        List of model classes.
    """
    return [Instance, Task, Worktree, Configuration]


def validate_schema(engine: Engine) -> Dict[str, bool]:
    """Validate that the database schema matches the expected structure.
    
    Args:
        engine: Database engine to check.
    
    Returns:
        Dictionary with validation results for each table.
    """
    metadata = MetaData()
    metadata.reflect(bind=engine)
    
    expected_tables = {table.__tablename__ for table in get_model_classes()}
    actual_tables = set(metadata.tables.keys())
    
    results = {}
    
    # Check if all expected tables exist
    for table_name in expected_tables:
        results[table_name] = table_name in actual_tables
    
    # Check for unexpected tables
    unexpected_tables = actual_tables - expected_tables
    if unexpected_tables:
        results["unexpected_tables"] = list(unexpected_tables)
    
    return results


def get_table_counts(engine: Engine) -> Dict[str, int]:
    """Get record counts for all tables.
    
    Args:
        engine: Database engine.
    
    Returns:
        Dictionary with table names as keys and counts as values.
    """
    from sqlalchemy import text
    
    counts = {}
    table_names = [table.__tablename__ for table in get_model_classes()]
    
    with engine.connect() as conn:
        for table_name in table_names:
            try:
                result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                counts[table_name] = result.scalar() or 0
            except Exception as e:
                counts[table_name] = f"Error: {e}"
    
    return counts


def create_sample_data(engine: Engine) -> None:
    """Create sample data for testing and development.
    
    Args:
        engine: Database engine.
    """
    from datetime import datetime
    from sqlalchemy.orm import Session
    
    from .models import (
        ConfigScope,
        Configuration,
        Instance,
        InstanceStatus,
        Task,
        TaskPriority,
        TaskStatus,
        Worktree,
        WorktreeStatus,
    )
    
    with Session(engine) as session:
        # Create sample instance
        instance = Instance(
            issue_id="123",
            status=InstanceStatus.RUNNING,
            workspace_path="/tmp/cc-orchestrator-issue-123",
            branch_name="feature/issue-123",
            tmux_session="claude-issue-123",
            extra_metadata={"github_url": "https://github.com/example/repo/issues/123"},
        )
        session.add(instance)
        session.flush()  # Get the ID
        
        # Create sample worktree
        worktree = Worktree(
            name="issue-123-worktree",
            path="/tmp/cc-orchestrator-issue-123",
            branch_name="feature/issue-123",
            repository_url="https://github.com/example/repo.git",
            status=WorktreeStatus.ACTIVE,
            instance_id=instance.id,
            current_commit="abc123def456",
            has_uncommitted_changes=False,
            git_config={"remote.origin.url": "https://github.com/example/repo.git"},
        )
        session.add(worktree)
        session.flush()
        
        # Create sample tasks
        tasks = [
            Task(
                title="Implement feature X",
                description="Add the new feature X to the codebase",
                status=TaskStatus.IN_PROGRESS,
                priority=TaskPriority.HIGH,
                instance_id=instance.id,
                worktree_id=worktree.id,
                estimated_duration=120,  # 2 hours
                requirements={"language": "python", "framework": "fastapi"},
            ),
            Task(
                title="Write tests for feature X",
                description="Create comprehensive tests",
                status=TaskStatus.PENDING,
                priority=TaskPriority.MEDIUM,
                instance_id=instance.id,
                worktree_id=worktree.id,
                estimated_duration=60,  # 1 hour
            ),
            Task(
                title="Update documentation",
                description="Update docs with new feature",
                status=TaskStatus.PENDING,
                priority=TaskPriority.LOW,
                worktree_id=worktree.id,
                estimated_duration=30,  # 30 minutes
            ),
        ]
        
        for task in tasks:
            session.add(task)
        
        # Create sample configurations
        configs = [
            Configuration(
                key="claude.model",
                value="claude-3-sonnet",
                scope=ConfigScope.GLOBAL,
                description="Default Claude model to use",
            ),
            Configuration(
                key="git.default_branch",
                value="main",
                scope=ConfigScope.GLOBAL,
                description="Default git branch name",
            ),
            Configuration(
                key="instance.timeout",
                value="3600",
                scope=ConfigScope.INSTANCE,
                instance_id=instance.id,
                description="Instance timeout in seconds",
            ),
        ]
        
        for config in configs:
            session.add(config)
        
        session.commit()


def export_schema_sql(engine: Engine) -> str:
    """Export the database schema as SQL DDL statements.
    
    Args:
        engine: Database engine.
    
    Returns:
        SQL DDL statements as a string.
    """
    from sqlalchemy.schema import CreateTable
    
    ddl_statements = []
    
    for table in Base.metadata.sorted_tables:
        create_table = CreateTable(table)
        ddl_statements.append(str(create_table.compile(engine)).strip())
    
    return ";\n\n".join(ddl_statements) + ";"