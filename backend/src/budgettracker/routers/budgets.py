from fastapi import APIRouter, HTTPException, status

from budgettracker.budgets import find_monthly_budget, set_monthly_budget
from budgettracker.db import SessionDep
from budgettracker.deps import CurrentUserDep
from budgettracker.schemas.budgets import BudgetIn, BudgetOut
from budgettracker.schemas.money import (
    cents_to_decimal,
    decimal_to_cents,
)
from budgettracker.schemas.period import Month, Year

router = APIRouter(tags=["budgets"])


@router.put("/budgets/{year}/{month}")
def set_budget(
    year: Year, month: Month, budget: BudgetIn, session: SessionDep, user: CurrentUserDep
) -> BudgetOut:
    """Set the spending limit for a month, replacing any existing one."""
    saved = set_monthly_budget(session, user, year, month, decimal_to_cents(budget.limit))
    session.commit()
    return BudgetOut(year=saved.year, month=saved.month, limit=cents_to_decimal(saved.limit_cents))


@router.get("/budgets/{year}/{month}")
def get_budget(year: Year, month: Month, session: SessionDep, user: CurrentUserDep) -> BudgetOut:
    """The spending limit for a month. 404 if none has been set."""
    budget = find_monthly_budget(session, user, year, month)
    if budget is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No budget set for this month")
    return BudgetOut(
        year=budget.year, month=budget.month, limit=cents_to_decimal(budget.limit_cents)
    )
