from fastapi import APIRouter

from budgettracker.db import SessionDep
from budgettracker.deps import CurrentUserDep
from budgettracker.reports import CategorySpending, spending_by_category
from budgettracker.schemas.money import cents_to_decimal
from budgettracker.schemas.period import Month, Year
from budgettracker.schemas.reports import (
    CategorySpendingOut,
    SpendingByCategoryOut,
)

router = APIRouter(tags=["reports"])


@router.get("/reports/{year}/{month}/spending-by-category")
def get_spending_by_category(
    year: Year, month: Month, session: SessionDep, user: CurrentUserDep
) -> SpendingByCategoryOut:
    """The month's expenses split by category, largest first."""
    result = spending_by_category(session, user, year, month)
    return SpendingByCategoryOut(
        total_spent=cents_to_decimal(result.total_spent_cents),
        categories=[_category_out(category) for category in result.categories],
    )


def _category_out(category: CategorySpending) -> CategorySpendingOut:
    return CategorySpendingOut(
        category_id=category.category_id,
        category_name=category.category_name,
        total=cents_to_decimal(category.total_cents),
        percent=category.percent,
    )
