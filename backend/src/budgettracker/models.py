"""Database tables.

These describe what's stored, not the JSON the API sends and receives (that's `schemas/`).
Money is always stored as integer cents.
"""

import datetime
from enum import StrEnum
from typing import override

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    TypeDecorator,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utc_now() -> datetime.datetime:
    """Current time in UTC."""
    return datetime.datetime.now(datetime.UTC)


class UTCDateTime(TypeDecorator[datetime.datetime]):
    """Datetime column that always returns timezone-aware UTC values.

    SQLite doesn't store timezones, so values are saved as UTC and given back their UTC timezone
    when loaded.
    """

    impl = DateTime
    cache_ok = True

    @override
    def process_bind_param(
        self, value: datetime.datetime | None, dialect: object
    ) -> datetime.datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("Naive datetime given; use utc_now() or another timezone-aware value")
        return value.astimezone(datetime.UTC).replace(tzinfo=None)

    @override
    def process_result_value(
        self, value: datetime.datetime | None, dialect: object
    ) -> datetime.datetime | None:
        if value is None:
            return None
        return value.replace(tzinfo=datetime.UTC)


class Base(DeclarativeBase):
    """Parent class of every model."""


class User(Base):
    __tablename__ = "users"
    __table_args__ = (CheckConstraint("email = lower(email)", name="email_is_lowercase"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(unique=True)
    password_hash: Mapped[str]
    created_at: Mapped[datetime.datetime] = mapped_column(UTCDateTime, default=utc_now)


class AuthToken(Base):
    """A login session. Only a hash of the token is stored, never the token itself."""

    __tablename__ = "auth_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    token_hash: Mapped[str] = mapped_column(unique=True)
    created_at: Mapped[datetime.datetime] = mapped_column(UTCDateTime, default=utc_now)
    expires_at: Mapped[datetime.datetime] = mapped_column(UTCDateTime)


class Category(Base):
    """Expense category, shared by all users."""

    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True)


class TransactionType(StrEnum):
    income = "income"
    expense = "expense"


class Transaction(Base):
    """An income or expense. Amounts are always positive; `type` gives the direction."""

    __tablename__ = "transactions"
    __table_args__ = (
        CheckConstraint("amount_cents > 0", name="amount_is_positive"),
        # Expenses must have a category; income must not.
        CheckConstraint(
            "(type = 'expense' AND category_id IS NOT NULL)"
            " OR (type = 'income' AND category_id IS NULL)",
            name="category_matches_type",
        ),
        # Speeds up the common "this user's transactions in this date range" query.
        Index("ix_transactions_user_id_date", "user_id", "date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    # Stored as text ("income" / "expense"), with a CHECK allowing only those values.
    type: Mapped[TransactionType] = mapped_column(
        Enum(TransactionType, native_enum=False, create_constraint=True, name="transaction_type")
    )
    amount_cents: Mapped[int]
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"))
    date: Mapped[datetime.date]
    description: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime.datetime] = mapped_column(UTCDateTime, default=utc_now)


class MonthlyBudget(Base):
    """A user's spending limit for one calendar month."""

    __tablename__ = "monthly_budgets"
    __table_args__ = (
        UniqueConstraint("user_id", "year", "month", name="one_budget_per_user_month"),
        CheckConstraint("month BETWEEN 1 AND 12", name="month_in_range"),
        CheckConstraint("limit_cents > 0", name="limit_is_positive"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    year: Mapped[int]
    month: Mapped[int]
    limit_cents: Mapped[int]
