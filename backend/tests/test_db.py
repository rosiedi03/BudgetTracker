"""Database setup, seeding, and the constraints the database itself enforces."""

import datetime

import pytest
from sqlalchemy import Engine, func, select
from sqlalchemy.exc import IntegrityError, StatementError
from sqlalchemy.orm import Session

from budgettracker.db import DEFAULT_CATEGORY_NAMES, init_db
from budgettracker.models import Category, MonthlyBudget, Transaction, TransactionType, User


def assert_rejected(session: Session, row: object) -> None:
    """Assert the database refuses to save `row`, then reset the session for further use."""
    session.add(row)
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


# Seeding


def test_categories_are_seeded_in_order(session: Session):
    categories = session.scalars(select(Category).order_by(Category.id)).all()
    assert [(c.id, c.name) for c in categories] == [
        (1, "Food"),
        (2, "Transportation"),
        (3, "Bills"),
        (4, "Entertainment"),
        (5, "Shopping"),
        (6, "Other"),
    ]


def test_no_users_are_seeded(session: Session):
    assert session.scalars(select(User)).all() == []


def test_init_db_can_run_again_without_duplicating_seed_data(db_engine: Engine, session: Session):
    init_db(db_engine)  # the fixture already ran it once
    assert session.scalar(select(func.count()).select_from(Category)) == len(DEFAULT_CATEGORY_NAMES)
    assert session.scalar(select(func.count()).select_from(User)) == 0


# Valid rows (so the rejection tests below can't pass just because every insert fails)


def test_valid_expense_and_income_are_saved(session: Session, main_user: User):
    user_id = main_user.id
    session.add(
        Transaction(
            user_id=user_id,
            type=TransactionType.expense,
            amount_cents=1250,
            category_id=1,
            date=datetime.date(2026, 11, 1),
        )
    )
    session.add(
        Transaction(
            user_id=user_id,
            type=TransactionType.income,
            amount_cents=500000,
            date=datetime.date(2026, 11, 1),
        )
    )
    session.add(MonthlyBudget(user_id=user_id, year=2026, month=11, limit_cents=100000))
    session.commit()
    assert session.scalar(select(func.count()).select_from(Transaction)) == 2


# Foreign keys


def test_transaction_with_nonexistent_category_is_rejected(session: Session, main_user: User):
    row = Transaction(
        user_id=main_user.id,
        type=TransactionType.expense,
        amount_cents=100,
        category_id=999,
        date=datetime.date(2026, 11, 1),
    )
    assert_rejected(session, row)


def test_budget_for_nonexistent_user_is_rejected(session: Session):
    assert_rejected(session, MonthlyBudget(user_id=999, year=2026, month=11, limit_cents=100))


# Check and unique constraints


@pytest.mark.parametrize("amount_cents", [0, -100])
def test_transaction_amount_must_be_positive(session: Session, main_user: User, amount_cents: int):
    row = Transaction(
        user_id=main_user.id,
        type=TransactionType.expense,
        amount_cents=amount_cents,
        category_id=1,
        date=datetime.date(2026, 11, 1),
    )
    assert_rejected(session, row)


def test_expense_without_category_is_rejected(session: Session, main_user: User):
    row = Transaction(
        user_id=main_user.id,
        type=TransactionType.expense,
        amount_cents=100,
        date=datetime.date(2026, 11, 1),
    )
    assert_rejected(session, row)


def test_income_with_category_is_rejected(session: Session, main_user: User):
    row = Transaction(
        user_id=main_user.id,
        type=TransactionType.income,
        amount_cents=100,
        category_id=1,
        date=datetime.date(2026, 11, 1),
    )
    assert_rejected(session, row)


@pytest.mark.parametrize("limit_cents", [0, -100])
def test_budget_limit_must_be_positive(session: Session, main_user: User, limit_cents: int):
    row = MonthlyBudget(user_id=main_user.id, year=2026, month=11, limit_cents=limit_cents)
    assert_rejected(session, row)


@pytest.mark.parametrize("month", [0, 13])
def test_budget_month_must_be_1_to_12(session: Session, main_user: User, month: int):
    row = MonthlyBudget(user_id=main_user.id, year=2026, month=month, limit_cents=100)
    assert_rejected(session, row)


def test_second_budget_for_same_user_and_month_is_rejected(session: Session, main_user: User):
    user_id = main_user.id
    session.add(MonthlyBudget(user_id=user_id, year=2026, month=11, limit_cents=100))
    session.commit()
    assert_rejected(session, MonthlyBudget(user_id=user_id, year=2026, month=11, limit_cents=200))


def test_uppercase_email_is_rejected(session: Session):
    assert_rejected(session, User(email="Someone@Example.com", password_hash="x"))


def test_duplicate_email_is_rejected(session: Session, main_user: User):
    assert_rejected(session, User(email=main_user.email, password_hash="x"))


# UTC timestamps


def test_created_at_is_set_and_loaded_as_utc(db_engine: Engine):
    with Session(db_engine) as session:
        session.add(User(email="new@example.com", password_hash="x"))
        session.commit()

    # A fresh session, so the value really comes from the database rather than memory.
    with Session(db_engine) as session:
        user = session.scalars(select(User).where(User.email == "new@example.com")).one()
        assert user.created_at.tzinfo == datetime.UTC
        age = datetime.datetime.now(datetime.UTC) - user.created_at
        assert datetime.timedelta(0) <= age < datetime.timedelta(minutes=1)


def test_non_utc_timestamp_is_converted_to_utc(db_engine: Engine):
    eastern = datetime.timezone(datetime.timedelta(hours=-5))
    with Session(db_engine) as session:
        session.add(
            User(
                email="new@example.com",
                password_hash="x",
                created_at=datetime.datetime(2026, 11, 12, 9, 0, tzinfo=eastern),
            )
        )
        session.commit()

    with Session(db_engine) as session:
        user = session.scalars(select(User).where(User.email == "new@example.com")).one()
        assert user.created_at == datetime.datetime(2026, 11, 12, 14, 0, tzinfo=datetime.UTC)
        assert user.created_at.tzinfo == datetime.UTC


def test_timestamp_without_timezone_is_rejected(session: Session):
    session.add(
        User(
            email="new@example.com",
            password_hash="x",
            created_at=datetime.datetime(2026, 11, 12, 9, 0),
        )
    )
    with pytest.raises(StatementError, match="Naive datetime"):
        session.commit()
