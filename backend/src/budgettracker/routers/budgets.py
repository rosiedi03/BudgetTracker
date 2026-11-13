from fastapi import APIRouter, HTTPException, status

from budgettracker.budgets import find_monthly_budget, set_monthly_budget
from budgettracker.db import SessionDep
from budgettracker.deps import AuthenticatedUserDep
from budgettracker.reports import budget_status
from budgettracker.schemas.budgets import BudgetIn, BudgetOut, BudgetStatusOut
from budgettracker.schemas.money import (
    cents_to_decimal,
    decimal_to_cents,
    optional_cents_to_decimal,
)
from budgettracker.schemas.period import Month, Year

router = APIRouter(tags=["budgets"])


@router.put("/budgets/{year}/{month}")
def set_budget(
    year: Year, month: Month, budget: BudgetIn, session: SessionDep, user: AuthenticatedUserDep
) -> BudgetOut:
    """Set the spending limit for a month, replacing any existing one."""
    saved = set_monthly_budget(session, user, year, month, decimal_to_cents(budget.limit))
    session.commit()
    return BudgetOut(year=saved.year, month=saved.month, limit=cents_to_decimal(saved.limit_cents))


@router.get("/budgets/{year}/{month}")
def get_budget(
    year: Year, month: Month, session: SessionDep, user: AuthenticatedUserDep
) -> BudgetOut:
    """The spending limit for a month. 404 if none has been set."""
    budget = find_monthly_budget(session, user, year, month)
    if budget is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No budget set for this month")
    return BudgetOut(
        year=budget.year, month=budget.month, limit=cents_to_decimal(budget.limit_cents)
    )


@router.get("/budgets/{year}/{month}/status")
def get_budget_status(
    year: Year, month: Month, session: SessionDep, user: AuthenticatedUserDep
) -> BudgetStatusOut:
    """The month's budget, how much has been spent, and how much is left."""
    result = budget_status(session, user, year, month)
    return BudgetStatusOut(
        year=result.year,
        month=result.month,
        limit=optional_cents_to_decimal(result.limit_cents),
        spent=cents_to_decimal(result.spent_cents),
        remaining=optional_cents_to_decimal(result.remaining_cents),
        percent_used=result.percent_used,
    )
