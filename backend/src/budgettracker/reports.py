"""Report calculations. Plain functions, kept separate from the routers so they're easy to test."""

import datetime
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from budgettracker.budgets import find_monthly_budget
from budgettracker.models import Category, Transaction, TransactionType, User


def month_date_range(year: int, month: int) -> tuple[datetime.date, datetime.date]:
    """(first day of the month, first day of the next month).

    Use as start <= date < end, so the last day of the month is included without needing to know
    how many days the month has.
    """
    return datetime.date(year, month, 1), _first_day_of_next_month(year, month)


def year_to_date_range(year: int, month: int) -> tuple[datetime.date, datetime.date]:
    """(January 1, first day of the month after `month`), used the same way as month_date_range."""
    return datetime.date(year, 1, 1), _first_day_of_next_month(year, month)


def percent_of(part_cents: int, whole_cents: int) -> Decimal:
    """part / whole as a percentage, rounded half-up to one decimal place (1 of 3 -> 33.3)."""
    percent = Decimal(part_cents) * 100 / Decimal(whole_cents)
    return percent.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)


@dataclass
class BudgetStatus:
    """A month's budget compared with what was spent. None fields mean no budget is set."""

    year: int
    month: int
    limit_cents: int | None
    spent_cents: int
    remaining_cents: int | None
    percent_used: Decimal | None


def budget_status(session: Session, user: User, year: int, month: int) -> BudgetStatus:
    """The user's budget for the month and how much of it their expenses have used."""
    start, end = month_date_range(year, month)
    spent_cents = _total_cents(session, user, TransactionType.expense, start, end)
    budget = find_monthly_budget(session, user, year, month)
    if budget is None:
        return BudgetStatus(
            year=year,
            month=month,
            limit_cents=None,
            spent_cents=spent_cents,
            remaining_cents=None,
            percent_used=None,
        )
    return BudgetStatus(
        year=year,
        month=month,
        limit_cents=budget.limit_cents,
        spent_cents=spent_cents,
        remaining_cents=budget.limit_cents - spent_cents,
        percent_used=percent_of(spent_cents, budget.limit_cents),
    )


@dataclass
class CategorySpending:
    category_id: int
    category_name: str
    total_cents: int
    percent: Decimal  # share of the month's total spending


@dataclass
class SpendingByCategory:
    """A month's expenses by category. Only categories with spending are listed."""

    total_spent_cents: int
    categories: list[CategorySpending]  # highest total first; ties by name


def spending_by_category(session: Session, user: User, year: int, month: int) -> SpendingByCategory:
    """How the user's expenses for the month split across categories."""
    start, end = month_date_range(year, month)
    category_total = func.sum(Transaction.amount_cents)
    query = (
        select(Category.id, Category.name, category_total)
        .select_from(Transaction)
        .join(Category, Transaction.category_id == Category.id)
        .where(
            Transaction.user_id == user.id,
            Transaction.type == TransactionType.expense,
            Transaction.date >= start,
            Transaction.date < end,
        )
        .group_by(Category.id, Category.name)
        .order_by(category_total.desc(), Category.name)
    )
    rows = session.execute(query).all()

    # One row per category that has spending, so this adds up at most a handful of numbers.
    total_spent_cents = sum(total for _, _, total in rows)
    categories = [
        CategorySpending(
            category_id=category_id,
            category_name=name,
            total_cents=total,
            percent=percent_of(total, total_spent_cents),
        )
        for category_id, name, total in rows
    ]
    return SpendingByCategory(total_spent_cents=total_spent_cents, categories=categories)


@dataclass
class TopCategory:
    category_id: int
    category_name: str
    total_cents: int


@dataclass
class MonthlySummary:
    """Everything the dashboard shows for one month. Budget fields are None if none is set."""

    year: int
    month: int
    total_income_cents: int
    total_expenses_cents: int
    budget_cents: int | None
    remaining_cents: int | None
    percent_used: Decimal | None
    categories: list[CategorySpending]  # same as spending_by_category
    top_category: TopCategory | None  # None if there are no expenses
    ytd_income_cents: int  # January 1 through the end of this month
    ytd_expenses_cents: int


def monthly_summary(session: Session, user: User, year: int, month: int) -> MonthlySummary:
    """The user's income, spending, and budget for the month, plus year-to-date totals."""
    # Reuse the other reports so the summary always agrees with them.
    budget = budget_status(session, user, year, month)
    spending = spending_by_category(session, user, year, month)

    # The breakdown is already sorted (total, then name), so its first entry is the top category.
    top_category = None
    if spending.categories:
        first = spending.categories[0]
        top_category = TopCategory(first.category_id, first.category_name, first.total_cents)

    month_start, month_end = month_date_range(year, month)
    ytd_start, ytd_end = year_to_date_range(year, month)
    income_cents = _total_cents(session, user, TransactionType.income, month_start, month_end)
    ytd_income_cents = _total_cents(session, user, TransactionType.income, ytd_start, ytd_end)
    ytd_expenses_cents = _total_cents(session, user, TransactionType.expense, ytd_start, ytd_end)
    return MonthlySummary(
        year=year,
        month=month,
        total_income_cents=income_cents,
        total_expenses_cents=budget.spent_cents,
        budget_cents=budget.limit_cents,
        remaining_cents=budget.remaining_cents,
        percent_used=budget.percent_used,
        categories=spending.categories,
        top_category=top_category,
        ytd_income_cents=ytd_income_cents,
        ytd_expenses_cents=ytd_expenses_cents,
    )


def _total_cents(
    session: Session,
    user: User,
    transaction_type: TransactionType,
    start: datetime.date,
    end: datetime.date,
) -> int:
    """Sum of the user's income or expenses dated start <= date < end, added up by the database."""
    # coalesce(..., 0): SUM over no rows is NULL in SQL; this turns it into 0.
    total = select(func.coalesce(func.sum(Transaction.amount_cents), 0)).where(
        Transaction.user_id == user.id,
        Transaction.type == transaction_type,
        Transaction.date >= start,
        Transaction.date < end,
    )
    return session.execute(total).scalar_one()


def _first_day_of_next_month(year: int, month: int) -> datetime.date:
    # December is the only month whose next month is in the following year.
    if month == 12:
        return datetime.date(year + 1, 1, 1)
    return datetime.date(year, month + 1, 1)
