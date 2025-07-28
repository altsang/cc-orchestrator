"""Base migration class and utilities."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, DateTime, Integer, String, Table, MetaData, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session


class Migration(ABC):
    """Base class for database migrations."""
    
    def __init__(self, version: str, description: str) -> None:
        """Initialize migration.
        
        Args:
            version: Migration version (e.g., "001", "002").
            description: Human-readable description of the migration.
        """
        self.version = version
        self.description = description
        self.created_at = datetime.now()
    
    @abstractmethod
    def upgrade(self, engine: Engine) -> None:
        """Apply the migration.
        
        Args:
            engine: Database engine.
        """
        pass
    
    @abstractmethod
    def downgrade(self, engine: Engine) -> None:
        """Reverse the migration.
        
        Args:
            engine: Database engine.
        """
        pass
    
    def __str__(self) -> str:
        return f"Migration {self.version}: {self.description}"
    
    def __repr__(self) -> str:
        return f"<Migration(version='{self.version}', description='{self.description}')>"


class MigrationRecord:
    """Represents a migration record in the database."""
    
    # SQLAlchemy table definition for migration tracking
    # This will be properly initialized by the migration manager
    table = None
    
    def __init__(
        self,
        version: str,
        description: str,
        applied_at: Optional[datetime] = None,
        checksum: Optional[str] = None,
    ) -> None:
        """Initialize migration record.
        
        Args:
            version: Migration version.
            description: Migration description.
            applied_at: When the migration was applied.
            checksum: Migration file checksum for integrity verification.
        """
        self.version = version
        self.description = description
        self.applied_at = applied_at or datetime.now()
        self.checksum = checksum
    
    def __str__(self) -> str:
        return f"MigrationRecord {self.version}: {self.description}"
    
    def __repr__(self) -> str:
        return (
            f"<MigrationRecord(version='{self.version}', "
            f"applied_at='{self.applied_at}')>"
        )