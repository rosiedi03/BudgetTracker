from fastapi import APIRouter

from budgettracker.db import SessionDep
from budgettracker.deps import AuthenticatedUserDep
from budgettracker.reports import CategorySpending, monthly_summary, spending_by_category
from budgettracker.schemas.money import cents_to_decimal, optional_cents_to_decimal
from budgettracker.schemas.period import Month, Year
from budgettracker.schemas.reports import (
    CategorySpendingOut,
    MonthlySummaryOut,
    SpendingByCategoryOut,
    TopCategoryOut,
)

router = APIRouter(tags=["reports"])


@router.get("/reports/{year}/{month}/spending-by-category")
def get_spending_by_category(
    year: Year, month: Month, session: SessionDep, user: AuthenticatedUserDep
) -> SpendingByCategoryOut:
    """The month's expenses split by category, largest first."""
    result = spending_by_category(session, user, year, month)
    return SpendingByCategoryOut(
        total_spent=cents_to_decimal(result.total_spent_cents),
        categories=[_category_out(category) for category in result.categories],
    )


@router.get("/reports/{year}/{month}/summary")
def get_monthly_summary(
    year: Year, month: Month, session: SessionDep, user: AuthenticatedUserDep
) -> MonthlySummaryOut:
    """Income, spending, budget, category breakdown, and year-to-date totals for the month."""
    result = monthly_summary(session, user, year, month)
    top_category = None
    if result.top_category is not None:
        top_category = TopCategoryOut(
            category_id=result.top_category.category_id,
            category_name=result.top_category.category_name,
            total=cents_to_decimal(result.top_category.total_cents),
        )
    return MonthlySummaryOut(
        year=result.year,
        month=result.month,
        total_income=cents_to_decimal(result.total_income_cents),
        total_expenses=cents_to_decimal(result.total_expenses_cents),
        budget=optional_cents_to_decimal(result.budget_cents),
        remaining=optional_cents_to_decimal(result.remaining_cents),
        percent_used=result.percent_used,
        categories=[_category_out(category) for category in result.categories],
        top_category=top_category,
        ytd_income=cents_to_decimal(result.ytd_income_cents),
        ytd_expenses=cents_to_decimal(result.ytd_expenses_cents),
    )


def _category_out(category: CategorySpending) -> CategorySpendingOut:
    return CategorySpendingOut(
        category_id=category.category_id,
        category_name=category.category_name,
        total=cents_to_decimal(category.total_cents),
        percent=category.percent,
    )
