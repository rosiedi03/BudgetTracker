"""Transaction totals: income and expense sums for the transaction list's filters."""

from datetime import date

import pytest
from sqlalchemy.orm import Session

from budgettracker.models import TransactionType, User
from budgettracker.reports import TransactionTotals, transaction_totals
from tests.helpers import AddExpense, AddIncome


def test_no_transactions(session: Session, main_user: User):
    assert transaction_totals(session, main_user) == TransactionTotals(0, 0)


def test_no_filters_counts_everything(
    session: Session, main_user: User, add_expense: AddExpense, add_income: AddIncome
):
    add_income(5000, date(2025, 6, 1))  # a year earlier
    add_income(3000, date(2026, 11, 15))
    add_expense(1200, date(2026, 11, 15))
    add_expense(800, date(2027, 1, 10))  # a year later
    assert transaction_totals(session, main_user) == TransactionTotals(
        income_cents=5000 + 3000, expenses_cents=1200 + 800
    )


def test_type_filter_leaves_the_other_total_at_zero(
    session: Session, main_user: User, add_expense: AddExpense, add_income: AddIncome
):
    add_income(5000, date(2026, 11, 15))
    add_expense(1200, date(2026, 11, 15))
    income_only = transaction_totals(session, main_user, transaction_type=TransactionType.income)
    expenses_only = transaction_totals(session, main_user, transaction_type=TransactionType.expense)
    assert income_only == TransactionTotals(income_cents=5000, expenses_cents=0)
    assert expenses_only == TransactionTotals(income_cents=0, expenses_cents=1200)


@pytest.fixture
def expenses_around_november(add_expense: AddExpense) -> None:
    """Expenses of 10.00 on Oct 31, 20.00 on Nov 1, 30.00 on Nov 30, and 40.00 on Dec 1."""
    add_expense(1000, date(2026, 10, 31))
    add_expense(2000, date(2026, 11, 1))
    add_expense(3000, date(2026, 11, 30))
    add_expense(4000, date(2026, 12, 1))


@pytest.mark.usefixtures("expenses_around_november")
@pytest.mark.parametrize(
    ("start_date", "end_date", "expected_expenses_cents"),
    [
        pytest.param(date(2026, 11, 1), None, 2000 + 3000 + 4000, id="from-nov-1"),
        pytest.param(None, date(2026, 11, 30), 1000 + 2000 + 3000, id="until-nov-30"),
        pytest.param(date(2026, 11, 1), date(2026, 11, 30), 2000 + 3000, id="nov-1-to-nov-30"),
        pytest.param(date(2026, 11, 30), date(2026, 11, 30), 3000, id="just-nov-30"),
        pytest.param(date(2026, 11, 2), date(2026, 11, 29), 0, id="nov-2-to-nov-29"),
    ],
)
def test_date_filters_include_both_end_dates(
    session: Session,
    main_user: User,
    start_date: date | None,
    end_date: date | None,
    expected_expenses_cents: int,
):
    result = transaction_totals(session, main_user, start_date=start_date, end_date=end_date)
    assert result == TransactionTotals(income_cents=0, expenses_cents=expected_expenses_cents)


def test_type_and_date_filters_combine(
    session: Session, main_user: User, add_expense: AddExpense, add_income: AddIncome
):
    add_income(5000, date(2026, 11, 15))  # wrong type
    add_expense(1200, date(2026, 11, 15))  # counted
    add_expense(800, date(2026, 12, 1))  # outside the dates
    result = transaction_totals(
        session,
        main_user,
        transaction_type=TransactionType.expense,
        start_date=date(2026, 11, 1),
        end_date=date(2026, 11, 30),
    )
    assert result == TransactionTotals(income_cents=0, expenses_cents=1200)


def test_other_users_transactions_are_ignored(
    session: Session,
    main_user: User,
    other_user: User,
    add_expense: AddExpense,
    add_income: AddIncome,
):
    add_income(5000, date(2026, 11, 15))
    add_expense(1200, date(2026, 11, 15))
    add_income(9900, date(2026, 11, 15), user=other_user)
    add_expense(4400, date(2026, 11, 15), user=other_user)
    assert transaction_totals(session, main_user) == TransactionTotals(5000, 1200)
    assert transaction_totals(session, other_user) == TransactionTotals(9900, 4400)
