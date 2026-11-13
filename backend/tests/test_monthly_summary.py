"""Monthly summary: a month's income, spending, budget, breakdown, and year-to-date totals."""

from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from budgettracker.models import MonthlyBudget, User
from budgettracker.reports import (
    CategorySpending,
    MonthlySummary,
    TopCategory,
    budget_status,
    monthly_summary,
    spending_by_category,
)
from tests.helpers import (
    BILLS,
    FOOD,
    OTHER,
    SHOPPING,
    TRANSPORTATION,
    ActAs,
    AddExpense,
    AddIncome,
)


def november(session: Session, user: User) -> MonthlySummary:
    return monthly_summary(session, user, 2026, 11)


@pytest.fixture
def example_year(
    session: Session, dev_user: User, add_expense: AddExpense, add_income: AddIncome
) -> None:
    """A year of the dev user's data, built around November 2026.

    November: budget 2000.00, income 3000.00, and expenses Food 300.00, Bills 1200.00, and
    Shopping 150.00.
    Earlier in 2026 (counted in year-to-date only): January income 2500.00 and expense 100.00,
    October income 1000.00 and expense 50.00.
    Outside November and its year-to-date (never counted): December 2026, January 2027, and
    November 2025.
    """
    session.add(MonthlyBudget(user_id=dev_user.id, year=2026, month=11, limit_cents=200000))
    session.commit()

    add_income(300000, date(2026, 11, 1))
    add_expense(30000, date(2026, 11, 3), category_id=FOOD)
    add_expense(120000, date(2026, 11, 1), category_id=BILLS)
    add_expense(15000, date(2026, 11, 30), category_id=SHOPPING)

    add_income(250000, date(2026, 1, 1))
    add_expense(10000, date(2026, 1, 15), category_id=OTHER)
    add_income(100000, date(2026, 10, 31))
    add_expense(5000, date(2026, 10, 31), category_id=FOOD)

    add_income(500000, date(2026, 12, 1))
    add_expense(99900, date(2026, 12, 1), category_id=FOOD)
    add_expense(88800, date(2027, 1, 1), category_id=FOOD)
    add_income(777700, date(2025, 11, 15))
    add_expense(66600, date(2025, 11, 15), category_id=BILLS)


# Report function


def test_empty_month(session: Session, dev_user: User):
    assert november(session, dev_user) == MonthlySummary(
        year=2026,
        month=11,
        total_income_cents=0,
        total_expenses_cents=0,
        budget_cents=None,
        remaining_cents=None,
        percent_used=None,
        categories=[],
        top_category=None,
        ytd_income_cents=0,
        ytd_expenses_cents=0,
    )


@pytest.mark.usefixtures("example_year")
def test_full_summary(session: Session, dev_user: User):
    assert november(session, dev_user) == MonthlySummary(
        year=2026,
        month=11,
        total_income_cents=300000,
        total_expenses_cents=165000,
        budget_cents=200000,
        remaining_cents=35000,
        percent_used=Decimal("82.5"),
        categories=[
            CategorySpending(BILLS, "Bills", 120000, Decimal("72.7")),
            CategorySpending(FOOD, "Food", 30000, Decimal("18.2")),
            CategorySpending(SHOPPING, "Shopping", 15000, Decimal("9.1")),
        ],
        top_category=TopCategory(BILLS, "Bills", 120000),
        ytd_income_cents=650000,  # January + October + November
        ytd_expenses_cents=180000,
    )


@pytest.mark.usefixtures("example_year")
def test_matches_budget_status_and_spending_by_category(session: Session, dev_user: User):
    summary = november(session, dev_user)
    budget = budget_status(session, dev_user, 2026, 11)
    spending = spending_by_category(session, dev_user, 2026, 11)

    assert summary.total_expenses_cents == budget.spent_cents == spending.total_spent_cents
    assert summary.budget_cents == budget.limit_cents
    assert summary.remaining_cents == budget.remaining_cents
    assert summary.percent_used == budget.percent_used
    assert summary.categories == spending.categories


def test_without_a_budget(session: Session, dev_user: User, add_expense: AddExpense):
    add_expense(1000, date(2026, 11, 5))
    result = november(session, dev_user)
    assert result.total_expenses_cents == 1000
    assert result.budget_cents is None
    assert result.remaining_cents is None
    assert result.percent_used is None


def test_income_only_month_has_no_top_category(
    session: Session, dev_user: User, add_income: AddIncome
):
    add_income(300000, date(2026, 11, 1))
    result = november(session, dev_user)
    assert result.total_income_cents == 300000
    assert result.total_expenses_cents == 0
    assert result.categories == []
    assert result.top_category is None


def test_top_category_tie_goes_to_the_name_first_alphabetically(
    session: Session, dev_user: User, add_expense: AddExpense
):
    # Transportation has the lower id, so this only passes if ties are broken by name.
    add_expense(1000, date(2026, 11, 5), category_id=TRANSPORTATION)
    add_expense(1000, date(2026, 11, 5), category_id=BILLS)
    assert november(session, dev_user).top_category == TopCategory(BILLS, "Bills", 1000)


@pytest.mark.parametrize(
    ("month", "ytd_income_cents", "ytd_expenses_cents"),
    [
        pytest.param(1, 250000, 10000, id="january-is-just-january"),
        pytest.param(10, 350000, 15000, id="through-october"),
        pytest.param(12, 1150000, 279900, id="december-is-the-whole-year"),
    ],
)
@pytest.mark.usefixtures("example_year")
def test_year_to_date_runs_from_january_through_the_month(
    session: Session, dev_user: User, month: int, ytd_income_cents: int, ytd_expenses_cents: int
):
    result = monthly_summary(session, dev_user, 2026, month)
    assert result.ytd_income_cents == ytd_income_cents
    assert result.ytd_expenses_cents == ytd_expenses_cents


@pytest.mark.usefixtures("example_year")
def test_other_users_data_is_ignored(
    session: Session,
    dev_user: User,
    other_user: User,
    add_expense: AddExpense,
    add_income: AddIncome,
):
    add_income(111100, date(2026, 11, 2), user=other_user)
    add_expense(22200, date(2026, 11, 2), category_id=TRANSPORTATION, user=other_user)
    add_income(33300, date(2026, 3, 1), user=other_user)
    add_expense(4400, date(2026, 3, 1), category_id=OTHER, user=other_user)

    result = november(session, dev_user)
    assert result.total_income_cents == 300000
    assert result.total_expenses_cents == 165000
    assert [c.category_name for c in result.categories] == ["Bills", "Food", "Shopping"]
    assert result.ytd_income_cents == 650000
    assert result.ytd_expenses_cents == 180000


# Endpoint

PATH = "/reports/2026/11/summary"


@pytest.mark.usefixtures("example_year")
def test_endpoint_returns_summary(client: TestClient):
    response = client.get(PATH)
    assert response.status_code == 200
    assert response.json() == {
        "year": 2026,
        "month": 11,
        "total_income": "3000.00",
        "total_expenses": "1650.00",
        "budget": "2000.00",
        "remaining": "350.00",
        "percent_used": 82.5,
        "categories": [
            {"category_id": BILLS, "category_name": "Bills", "total": "1200.00", "percent": 72.7},
            {"category_id": FOOD, "category_name": "Food", "total": "300.00", "percent": 18.2},
            {
                "category_id": SHOPPING,
                "category_name": "Shopping",
                "total": "150.00",
                "percent": 9.1,
            },
        ],
        "top_category": {"category_id": BILLS, "category_name": "Bills", "total": "1200.00"},
        "ytd_income": "6500.00",
        "ytd_expenses": "1800.00",
    }


def test_endpoint_empty_month(client: TestClient):
    response = client.get(PATH)
    assert response.status_code == 200
    assert response.json() == {
        "year": 2026,
        "month": 11,
        "total_income": "0.00",
        "total_expenses": "0.00",
        "budget": None,
        "remaining": None,
        "percent_used": None,
        "categories": [],
        "top_category": None,
        "ytd_income": "0.00",
        "ytd_expenses": "0.00",
    }


@pytest.mark.usefixtures("example_year")
def test_endpoint_uses_the_current_user(client: TestClient, other_user: User, act_as: ActAs):
    act_as(other_user)  # who has no data
    response = client.get(PATH)
    assert response.status_code == 200
    body = response.json()
    assert body["total_income"] == "0.00"
    assert body["total_expenses"] == "0.00"
    assert body["budget"] is None
    assert body["ytd_income"] == "0.00"


@pytest.mark.usefixtures("logged_out")
def test_endpoint_requires_a_logged_in_user(client: TestClient):
    assert client.get(PATH).status_code == 401


@pytest.mark.parametrize(
    "path",
    [
        pytest.param("/reports/1999/11/summary", id="year-out-of-range"),
        pytest.param("/reports/2026/13/summary", id="month-out-of-range"),
    ],
)
def test_endpoint_invalid_year_or_month_returns_422(client: TestClient, path: str):
    assert client.get(path).status_code == 422
