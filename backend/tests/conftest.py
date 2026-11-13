"""Shared test fixtures. pytest loads this file automatically.

Every test gets its own fresh database, so tests never touch the real budgettracker.db or affect
each other.
"""

import datetime
import secrets
import shutil
from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi import HTTPException, status
from fastapi.testclient import TestClient
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session, sessionmaker

from budgettracker.db import DEV_USER_EMAIL, create_db_engine, get_session, init_db
from budgettracker.deps import get_authenticated_user, hash_token
from budgettracker.main import app
from budgettracker.models import AuthToken, Transaction, TransactionType, User, utc_now
from tests.helpers import FOOD, ActAs, AddExpense, AddIncome, TokenFor


@pytest.fixture(scope="session")
def template_db_path(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A database set up the same way as at app startup, built once per test run.

    Copying this file is several times faster than creating tables and seeding for every test.
    """
    path = tmp_path_factory.mktemp("template") / "template.db"
    engine = create_db_engine(f"sqlite:///{path}")
    init_db(engine)
    engine.dispose()
    return path


@pytest.fixture
def db_engine(tmp_path: Path, template_db_path: Path) -> Generator[Engine]:
    """This test's own copy of the template database."""
    path = tmp_path / "test.db"
    shutil.copyfile(template_db_path, path)
    engine = create_db_engine(f"sqlite:///{path}")
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
def token_for(session: Session) -> TokenFor:
    """A function that creates a login token for a user and returns request headers that use it.

    token_for(user) gives a token that's valid for a day; pass expires_at for a different expiry.
    """

    def create(user: User, expires_at: datetime.datetime | None = None) -> dict[str, str]:
        if expires_at is None:
            expires_at = utc_now() + datetime.timedelta(days=1)
        token = secrets.token_urlsafe(16)
        session.add(AuthToken(user_id=user.id, token_hash=hash_token(token), expires_at=expires_at))
        session.commit()
        return {"Authorization": f"Bearer {token}"}

    return create


@pytest.fixture
def client(main_user: User, token_for: TokenFor) -> TestClient:
    """Sends requests to the app without running a server, logged in as the dev user."""
    return TestClient(app, headers=token_for(main_user))


@pytest.fixture
def main_user(session: Session) -> User:
    """The seeded user that requests act as by default."""
    return session.scalars(select(User).where(User.email == DEV_USER_EMAIL)).one()


@pytest.fixture
def other_user(session: Session) -> User:
    """A second user, for checking that users never see or change each other's data."""
    user = User(email="other@example.com", password_hash="x")
    session.add(user)
    session.commit()
    return user


@pytest.fixture
def act_as() -> ActAs:
    """A function that switches users: after act_as(user), requests in the test act as `user`."""

    def switch(user: User) -> None:
        app.dependency_overrides[get_authenticated_user] = lambda: user

    return switch


@pytest.fixture
def logged_out() -> None:
    """Every request in the test is rejected as not logged in (401)."""

    def reject() -> User:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    app.dependency_overrides[get_authenticated_user] = reject


@pytest.fixture
def add_expense(session: Session, main_user: User) -> AddExpense:
    """A function that saves an expense: add_expense(1250, date(2026, 11, 5)).

    Optional: category_id (default Food) and user (default the dev user).
    """

    def add(
        amount_cents: int,
        on: datetime.date,
        category_id: int = FOOD,
        user: User | None = None,
    ) -> Transaction:
        owner = main_user if user is None else user
        transaction = Transaction(
            user_id=owner.id,
            type=TransactionType.expense,
            amount_cents=amount_cents,
            category_id=category_id,
            date=on,
        )
        session.add(transaction)
        session.commit()
        return transaction

    return add


@pytest.fixture
def add_income(session: Session, main_user: User) -> AddIncome:
    """A function that saves income: add_income(500000, date(2026, 11, 1)). Optional: user."""

    def add(amount_cents: int, on: datetime.date, user: User | None = None) -> Transaction:
        owner = main_user if user is None else user
        transaction = Transaction(
            user_id=owner.id, type=TransactionType.income, amount_cents=amount_cents, date=on
        )
        session.add(transaction)
        session.commit()
        return transaction

    return add
