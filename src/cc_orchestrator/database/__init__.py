"""Database models and operations."""

from .connection import (
    DatabaseManager,
    get_database_manager,
    get_db_session,
    initialize_database,
    close_database,
)
from .crud import (
    CRUDError,
    ValidationError,
    NotFoundError,
    InstanceCRUD,
    TaskCRUD,
    WorktreeCRUD,
    ConfigurationCRUD,
)
from .migrations import Migration, MigrationManager
from .models import (
    Base,
    Instance,
    InstanceStatus,
    Task,
    TaskStatus,
    TaskPriority,
    Worktree,
    WorktreeStatus,
    Configuration,
    ConfigScope,
)
from .schema import (
    get_schema_version,
    get_table_info,
    validate_schema,
    get_table_counts,
    create_sample_data,
)

__all__ = [
    # Connection management
    "DatabaseManager",
    "get_database_manager",
    "get_db_session",
    "initialize_database",
    "close_database",
    
    # CRUD operations
    "CRUDError",
    "ValidationError",
    "NotFoundError",
    "InstanceCRUD",
    "TaskCRUD",
    "WorktreeCRUD",
    "ConfigurationCRUD",
    
    # Migrations
    "Migration",
    "MigrationManager",
    
    # Models
    "Base",
    "Instance",
    "InstanceStatus",
    "Task",
    "TaskStatus",
    "TaskPriority",
    "Worktree",
    "WorktreeStatus",
    "Configuration",
    "ConfigScope",
    
    # Schema utilities
    "get_schema_version",
    "get_table_info",
    "validate_schema",
    "get_table_counts",
    "create_sample_data",
]
