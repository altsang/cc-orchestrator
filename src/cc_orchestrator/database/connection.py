"""Database connection and session management."""

import os
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from .models import Base


class DatabaseManager:
    """Manages database connections and sessions."""

    def __init__(
        self,
        database_url: str | None = None,
        echo: bool = False,
        pool_pre_ping: bool = True,
        pool_size: int = 10,
        max_overflow: int = 20,
        pool_timeout: int = 30,
        pool_recycle: int = 3600,
    ) -> None:
        """Initialize database manager.

        Args:
            database_url: Database connection URL. If None, uses default SQLite.
            echo: Whether to echo SQL statements to stdout.
            pool_pre_ping: Whether to enable pool pre-ping for connection validation.
            pool_size: Number of connections to maintain in the pool.
            max_overflow: Maximum number of overflow connections.
            pool_timeout: Timeout for getting connection from pool.
            pool_recycle: Time in seconds to recycle connections.
        """
        self.database_url = database_url or self._get_default_database_url()
        self.echo = echo
        self.pool_pre_ping = pool_pre_ping
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.pool_timeout = pool_timeout
        self.pool_recycle = pool_recycle

        self._engine: Engine | None = None
        self._session_factory: sessionmaker[Session] | None = None

    def _get_default_database_url(self) -> str:
        """Get default SQLite database URL."""
        # Use environment variable if set
        if db_url := os.getenv("CC_ORCHESTRATOR_DATABASE_URL"):
            return db_url

        # Default to SQLite in user's home directory
        db_path = Path.home() / ".cc-orchestrator" / "database.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)

        return f"sqlite:///{db_path}"

    @property
    def engine(self) -> Engine:
        """Get the database engine, creating it if necessary."""
        if self._engine is None:
            self._engine = self._create_engine()
        return self._engine

    @property
    def session_factory(self) -> sessionmaker[Session]:
        """Get the session factory, creating it if necessary."""
        if self._session_factory is None:
            self._session_factory = sessionmaker(bind=self.engine)
        return self._session_factory

    def _create_engine(self) -> Engine:
        """Create the database engine with appropriate configuration."""
        engine_kwargs: dict[str, Any] = {
            "echo": self.echo,
            "pool_pre_ping": self.pool_pre_ping,
        }

        # Special configuration for SQLite
        if self.database_url.startswith("sqlite"):
            sqlite_config = {
                "poolclass": StaticPool,
                "connect_args": {
                    "check_same_thread": False,  # Allow multi-threading
                    "timeout": self.pool_timeout,  # Configurable timeout
                },
            }
            engine_kwargs.update(sqlite_config)
        else:
            # Production database configuration with connection pooling
            pool_config = {
                "pool_size": self.pool_size,
                "max_overflow": self.max_overflow,
                "pool_timeout": self.pool_timeout,
                "pool_recycle": self.pool_recycle,
            }
            engine_kwargs.update(pool_config)

        engine = create_engine(self.database_url, **engine_kwargs)

        # Enable foreign key constraints for SQLite
        if self.database_url.startswith("sqlite"):

            @event.listens_for(engine, "connect")
            def set_sqlite_pragma(
                dbapi_connection: Any, connection_record: Any
            ) -> None:
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.execute(
                    "PRAGMA journal_mode=WAL"
                )  # Enable WAL mode for better concurrency
                cursor.close()

        return engine

    def create_tables(self) -> None:
        """Create all database tables."""
        Base.metadata.create_all(self.engine)

    async def initialize(self) -> None:
        """Initialize the database asynchronously."""
        self.create_tables()

    def close(self) -> None:
        """Close database connections."""
        if self._engine:
            self._engine.dispose()
            self._engine = None
        self._session_factory = None

    def drop_tables(self) -> None:
        """Drop all database tables."""
        Base.metadata.drop_all(self.engine)

    def reset_database(self) -> None:
        """Drop and recreate all tables."""
        self.drop_tables()
        self.create_tables()

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """Get a database session with automatic cleanup.

        Yields:
            Database session that will be automatically committed/rolled back.
        """
        session = self.session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def create_session(self) -> Session:
        """Create a new database session.

        Note: The caller is responsible for managing the session lifecycle.
        Consider using get_session() context manager instead.

        Returns:
            New database session.
        """
        return self.session_factory()

    def __enter__(self) -> "DatabaseManager":
        """Enter context manager."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit context manager and clean up."""
        self.close()


# Global database manager instance
_db_manager: DatabaseManager | None = None


def get_database_manager(
    database_url: str | None = None,
    echo: bool = False,
    reset: bool = False,
    pool_size: int = 10,
    max_overflow: int = 20,
    pool_timeout: int = 30,
    pool_recycle: int = 3600,
) -> DatabaseManager:
    """Get the global database manager instance.

    Args:
        database_url: Database connection URL.
        echo: Whether to echo SQL statements.
        reset: Whether to recreate the database manager.

    Returns:
        Database manager instance.
    """
    global _db_manager

    if _db_manager is None or reset:
        if _db_manager is not None:
            _db_manager.close()

        _db_manager = DatabaseManager(
            database_url=database_url,
            echo=echo,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_timeout=pool_timeout,
            pool_recycle=pool_recycle,
        )

        # Create tables if they don't exist
        _db_manager.create_tables()

    return _db_manager


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """Convenience function to get a database session.

    Yields:
        Database session.
    """
    db_manager = get_database_manager()
    with db_manager.get_session() as session:
        yield session


def initialize_database(database_url: str | None = None, echo: bool = False) -> None:
    """Initialize the database with tables.

    Args:
        database_url: Database connection URL.
        echo: Whether to echo SQL statements.
    """
    db_manager = get_database_manager(database_url=database_url, echo=echo)
    db_manager.create_tables()


def close_database() -> None:
    """Close the global database manager."""
    global _db_manager
    if _db_manager is not None:
        _db_manager.close()
        _db_manager = None
