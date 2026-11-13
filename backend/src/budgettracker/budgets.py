"""Storing and looking up monthly budgets."""

from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.orm import Session

from budgettracker.models import MonthlyBudget, User


def find_monthly_budget(
    session: Session, user: User, year: int, month: int
) -> MonthlyBudget | None:
    """The user's budget for the month, or None if they haven't set one."""
    return session.scalars(
        select(MonthlyBudget).where(
            MonthlyBudget.user_id == user.id,
            MonthlyBudget.year == year,
            MonthlyBudget.month == month,
        )
    ).one_or_none()


def set_monthly_budget(
    session: Session, user: User, year: int, month: int, limit_cents: int
) -> MonthlyBudget:
    """Create the user's budget for the month, or replace the limit if one exists.

    Doesn't commit; the caller does.
    """
    # One statement that inserts, or updates if the month already has a budget. Checking first and
    # then inserting would let two saves at once both see "no budget" and both try to insert.
    upsert = insert(MonthlyBudget).values(
        user_id=user.id, year=year, month=month, limit_cents=limit_cents
    )
    upsert = upsert.on_conflict_do_update(
        index_elements=[MonthlyBudget.user_id, MonthlyBudget.year, MonthlyBudget.month],
        set_={"limit_cents": upsert.excluded.limit_cents},
    )
    # populate_existing: if this session already loaded the budget, refresh it with the new limit.
    return session.scalars(
        upsert.returning(MonthlyBudget), execution_options={"populate_existing": True}
    ).one()
