"""Database infrastructure for the AcmeCloud checkout service.

Short overview:
- Creates the SQLAlchemy engine from runtime configuration.
- Enforces the configured connection-pool size.
- Tracks active database connections.
- Measures database connection acquisition time.
- Creates one database session per request and always closes it.
"""

import time
from collections.abc import Generator
from functools import lru_cache

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import get_settings
from .metrics import DB_CONNECTION_WAIT_TIME, DB_CONNECTIONS_ACTIVE


class Base(DeclarativeBase):
    """Base class for SQLAlchemy ORM models."""


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    """Return the process-wide SQLAlchemy session factory.

    ``max_overflow=0`` makes ``db_pool_size`` the actual maximum number
    of database connections available to the service.
    """
    settings = get_settings()

    engine = create_engine(
        settings.database_url,
        pool_pre_ping=True,
        pool_size=settings.db_pool_size,
        max_overflow=0,
        pool_timeout=settings.db_pool_timeout,
    )

    @event.listens_for(engine, "checkout")
    def on_checkout(dbapi_connection, connection_record, connection_proxy):
        """Record a successful database connection checkout."""
        DB_CONNECTIONS_ACTIVE.inc()

    @event.listens_for(engine, "checkin")
    def on_checkin(dbapi_connection, connection_record):
        """Record a database connection returned to the pool."""
        DB_CONNECTIONS_ACTIVE.dec()

    return sessionmaker(
        bind=engine,
        class_=Session,
        autoflush=False,
        autocommit=False,
    )


def get_db() -> Generator[Session, None, None]:
    """Yield a database session for the lifetime of a request."""
    start = time.perf_counter()
    db = get_session_factory()()

    try:
        # Force physical connection acquisition here so pool acquisition
        # time is measured at a deterministic point.
        db.connection()

        DB_CONNECTION_WAIT_TIME.observe(time.perf_counter() - start)

        yield db
    finally:
        db.close()
