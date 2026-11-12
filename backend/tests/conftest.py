"""Shared test fixtures. pytest loads this file automatically.

Every test gets its own fresh database, so tests never touch the real budgettracker.db or affect
each other.
"""

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from budgettracker.db import create_db_engine, get_session, init_db
from budgettracker.main import app


@pytest.fixture
def db_engine(tmp_path) -> Generator[Engine]:
    """A new database file, set up the same way as at app startup."""
    engine = create_db_engine(f"sqlite:///{tmp_path / 'test.db'}")
    init_db(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def session(db_engine: Engine) -> Generator[Session]:
    """A session on the test database, for tests that work with the database directly."""
    with Session(db_engine) as session:
        yield session


@pytest.fixture(autouse=True)
def use_test_database(db_engine: Engine) -> Generator[None]:
    """Point the app's endpoints at the test database. Applies to every test automatically."""
    make_session = sessionmaker(bind=db_engine)

    def get_test_session() -> Generator[Session]:
        with make_session() as session:
            yield session

    app.dependency_overrides[get_session] = get_test_session
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client() -> TestClient:
    """Sends requests to the app without running a server."""
    return TestClient(app)
