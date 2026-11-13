"""Database connection, per-request sessions, and startup setup."""

import os
from collections.abc import Generator
from typing import Annotated

from fastapi import Depends
from sqlalchemy import Engine, create_engine, event, select
from sqlalchemy.orm import Session, sessionmaker

from budgettracker.models import Base, Category

# Defaults to a file in the directory the server is started from.
DATABASE_URL = os.environ.get("BUDGETTRACKER_DATABASE_URL", "sqlite:///./budgettracker.db")

# Seconds to wait for another connection's write to finish before failing with "database is locked".
SQLITE_BUSY_TIMEOUT_SECONDS = 5

# Inserted in this order, so on a fresh database their ids are 1-6.
DEFAULT_CATEGORY_NAMES = ["Food", "Transportation", "Bills", "Entertainment", "Shopping", "Other"]


def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record) -> None:
    """SQLite ignores foreign keys unless they're turned on for each connection."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def create_db_engine(url: str) -> Engine:
    """Create an engine with the connection settings the app relies on.

    check_same_thread=False lets FastAPI's worker threads share the connection pool; this is safe
    because each request uses its own session.
    """
    engine = create_engine(
        url,
        connect_args={"check_same_thread": False, "timeout": SQLITE_BUSY_TIMEOUT_SECONDS},
    )
    event.listen(engine, "connect", _enable_sqlite_foreign_keys)
    return engine


engine = create_db_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)


def get_session() -> Generator[Session]:
    """Provide one session per request; it's closed (uncommitted changes discarded) afterwards.

    Endpoints that write must call session.commit().
    """
    with SessionLocal() as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]


def init_db(engine: Engine) -> None:
    """Create missing tables and seed the default categories. Safe to run on every startup.

    Existing tables are never altered: after changing a model, delete the .db file and restart.
    """
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        _seed_categories(session)
        session.commit()


def _seed_categories(session: Session) -> None:
    existing_names = set(session.scalars(select(Category.name)))
    for name in DEFAULT_CATEGORY_NAMES:
        if name not in existing_names:
            session.add(Category(name=name))
