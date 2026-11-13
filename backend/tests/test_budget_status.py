"""Budget status: a month's limit compared with what was spent."""

from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from budgettracker.models import MonthlyBudget, Transaction, TransactionType, User
from budgettracker.reports import BudgetStatus, budget_status
from tests.helpers import FOOD, TRANSPORTATION, ActAs, AddExpense, AddIncome


def set_budget(session: Session, user: User, year: int, month: int, limit_cents: int) -> None:
    session.add(MonthlyBudget(user_id=user.id, year=year, month=month, limit_cents=limit_cents))
    session.commit()


def november_status(session: Session, user: User) -> BudgetStatus:
    return budget_status(session, user, 2026, 11)


# Report function: budget and spending combinations


def test_no_budget_and_no_spending(session: Session, main_user: User):
    assert november_status(session, main_user) == BudgetStatus(
        year=2026,
        month=11,
        limit_cents=None,
        spent_cents=0,
        remaining_cents=None,
        percent_used=None,
    )


def test_no_budget_still_reports_spending(
    session: Session, main_user: User, add_expense: AddExpense
):
    add_expense(1200, date(2026, 11, 5))
    assert november_status(session, main_user) == BudgetStatus(
        year=2026,
        month=11,
        limit_cents=None,
        spent_cents=1200,
        remaining_cents=None,
        percent_used=None,
    )


def test_budget_with_no_spending(session: Session, main_user: User):
    set_budget(session, main_user, 2026, 11, 50000)
    assert november_status(session, main_user) == BudgetStatus(
        year=2026,
        month=11,
        limit_cents=50000,
        spent_cents=0,
        remaining_cents=50000,
        percent_used=Decimal("0.0"),
    )


def test_budget_partly_spent(session: Session, main_user: User, add_expense: AddExpense):
    set_budget(session, main_user, 2026, 11, 50000)
    add_expense(10000, date(2026, 11, 3))
    add_expense(2345, date(2026, 11, 20), category_id=TRANSPORTATION)
    assert november_status(session, main_user) == BudgetStatus(
        year=2026,
        month=11,
        limit_cents=50000,
        spent_cents=12345,
        remaining_cents=37655,
        percent_used=Decimal("24.7"),  # 24.69% rounded up
    )


def test_budget_exactly_spent(session: Session, main_user: User, add_expense: AddExpense):
    set_budget(session, main_user, 2026, 11, 50000)
    add_expense(50000, date(2026, 11, 3))
    result = november_status(session, main_user)
    assert result.remaining_cents == 0
    assert result.percent_used == Decimal("100.0")


def test_overspent_budget_goes_negative(session: Session, main_user: User, add_expense: AddExpense):
    set_budget(session, main_user, 2026, 11, 10000)
    add_expense(15050, date(2026, 11, 3))
    result = november_status(session, main_user)
    assert result.remaining_cents == -5050
    assert result.percent_used == Decimal("150.5")


# Report function: which transactions count


def test_income_is_not_spending(
    session: Session, main_user: User, add_expense: AddExpense, add_income: AddIncome
):
    add_income(500000, date(2026, 11, 1))
    add_expense(1000, date(2026, 11, 2))
    assert november_status(session, main_user).spent_cents == 1000


def test_only_expenses_within_the_month_count(
    session: Session, main_user: User, add_expense: AddExpense
):
    add_expense(1, date(2026, 10, 31))  # day before
    add_expense(10, date(2026, 11, 1))  # first day
    add_expense(100, date(2026, 11, 30))  # last day
    add_expense(1000, date(2026, 12, 1))  # day after
    add_expense(10000, date(2025, 11, 15))  # same month, previous year
    assert november_status(session, main_user).spent_cents == 110


def test_december_ends_at_new_year(session: Session, main_user: User, add_expense: AddExpense):
    add_expense(10, date(2026, 12, 31))
    add_expense(100, date(2027, 1, 1))
    assert budget_status(session, main_user, 2026, 12).spent_cents == 10
    assert budget_status(session, main_user, 2027, 1).spent_cents == 100


def test_many_small_amounts_add_up_exactly(session: Session, main_user: User):
    session.add_all(
        Transaction(
            user_id=main_user.id,
            type=TransactionType.expense,
            amount_cents=10,
            category_id=FOOD,
            date=date(2026, 11, 15),
        )
        for _ in range(100)
    )
    session.commit()
    assert november_status(session, main_user).spent_cents == 1000


# Report function: users


def test_other_users_spending_and_budget_are_ignored(
    session: Session, main_user: User, other_user: User, add_expense: AddExpense
):
    set_budget(session, other_user, 2026, 11, 99900)
    add_expense(5000, date(2026, 11, 5), user=other_user)
    add_expense(700, date(2026, 11, 5))

    result = november_status(session, main_user)
    assert result.spent_cents == 700
    assert result.limit_cents is None


# Endpoint


def test_endpoint_returns_status(
    client: TestClient, session: Session, main_user: User, add_expense: AddExpense
):
    set_budget(session, main_user, 2026, 11, 50000)
    add_expense(12345, date(2026, 11, 3))
    response = client.get("/budgets/2026/11/status")
    assert response.status_code == 200
    assert response.json() == {
        "year": 2026,
        "month": 11,
        "limit": "500.00",
        "spent": "123.45",
        "remaining": "376.55",
        "percent_used": 24.7,
    }


def test_endpoint_without_budget_returns_nulls(client: TestClient, add_expense: AddExpense):
    add_expense(1200, date(2026, 11, 5))
    response = client.get("/budgets/2026/11/status")
    assert response.status_code == 200
    assert response.json() == {
        "year": 2026,
        "month": 11,
        "limit": None,
        "spent": "12.00",
        "remaining": None,
        "percent_used": None,
    }


def test_endpoint_overspent(
    client: TestClient, session: Session, main_user: User, add_expense: AddExpense
):
    set_budget(session, main_user, 2026, 11, 10000)
    add_expense(15050, date(2026, 11, 3))
    response = client.get("/budgets/2026/11/status")
    assert response.status_code == 200
    body = response.json()
    assert body["remaining"] == "-50.50"
    assert body["percent_used"] == 150.5


def test_endpoint_uses_the_current_user(
    client: TestClient,
    session: Session,
    main_user: User,
    other_user: User,
    act_as: ActAs,
    add_expense: AddExpense,
):
    set_budget(session, main_user, 2026, 11, 50000)
    add_expense(1200, date(2026, 11, 5))

    act_as(other_user)  # who has no budget or spending
    response = client.get("/budgets/2026/11/status")
    assert response.status_code == 200
    body = response.json()
    assert body["spent"] == "0.00"
    assert body["limit"] is None


@pytest.mark.usefixtures("logged_out")
def test_endpoint_requires_a_logged_in_user(client: TestClient):
    assert client.get("/budgets/2026/11/status").status_code == 401


@pytest.mark.parametrize(
    "path",
    [
        pytest.param("/budgets/1999/11/status", id="year-out-of-range"),
        pytest.param("/budgets/2026/13/status", id="month-out-of-range"),
    ],
)
def test_endpoint_invalid_year_or_month_returns_422(client: TestClient, path: str):
    assert client.get(path).status_code == 422
