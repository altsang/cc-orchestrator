"""Initial database schema migration."""

from sqlalchemy.engine import Engine

from cc_orchestrator.database.migrations.migration import Migration
from cc_orchestrator.database.models import Base


class InitialSchemaMigration(Migration):
    """Create initial database tables."""

    def __init__(self) -> None:
        super().__init__(
            version="001",
            description="Create initial schema with instances, tasks, worktrees, and configurations tables",
        )

    def upgrade(self, engine: Engine) -> None:
        """Create all initial tables."""
        Base.metadata.create_all(engine)

    def downgrade(self, engine: Engine) -> None:
        """Drop all tables."""
        Base.metadata.drop_all(engine)
