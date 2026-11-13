"""Spending by category: how a month's expenses split across categories."""

from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from budgettracker.models import User
from budgettracker.reports import CategorySpending, SpendingByCategory, spending_by_category
from tests.helpers import BILLS, FOOD, SHOPPING, TRANSPORTATION, ActAs, AddExpense, AddIncome


def november(session: Session, user: User) -> SpendingByCategory:
    return spending_by_category(session, user, 2026, 11)


# Report function: totals, percentages, order


def test_no_expenses(session: Session, main_user: User):
    assert november(session, main_user) == SpendingByCategory(total_spent_cents=0, categories=[])


def test_income_is_not_spending(session: Session, main_user: User, add_income: AddIncome):
    add_income(500000, date(2026, 11, 5))
    assert november(session, main_user) == SpendingByCategory(total_spent_cents=0, categories=[])


def test_single_category(session: Session, main_user: User, add_expense: AddExpense):
    add_expense(1000, date(2026, 11, 5), category_id=FOOD)
    assert november(session, main_user) == SpendingByCategory(
        total_spent_cents=1000,
        categories=[CategorySpending(FOOD, "Food", 1000, Decimal("100.0"))],
    )


def test_categories_sorted_by_total_with_percentages(
    session: Session, main_user: User, add_expense: AddExpense
):
    add_expense(3000, date(2026, 11, 5), category_id=FOOD)
    add_expense(5000, date(2026, 11, 5), category_id=BILLS)
    add_expense(2000, date(2026, 11, 5), category_id=SHOPPING)
    assert november(session, main_user) == SpendingByCategory(
        total_spent_cents=10000,
        categories=[
            CategorySpending(BILLS, "Bills", 5000, Decimal("50.0")),
            CategorySpending(FOOD, "Food", 3000, Decimal("30.0")),
            CategorySpending(SHOPPING, "Shopping", 2000, Decimal("20.0")),
        ],
    )


def test_expenses_in_the_same_category_are_added_together(
    session: Session, main_user: User, add_expense: AddExpense
):
    add_expense(1000, date(2026, 11, 2), category_id=FOOD)
    add_expense(2500, date(2026, 11, 20), category_id=FOOD)
    add_expense(500, date(2026, 11, 5), category_id=BILLS)
    result = november(session, main_user)
    assert [(c.category_name, c.total_cents) for c in result.categories] == [
        ("Food", 3500),
        ("Bills", 500),
    ]
    assert result.total_spent_cents == 4000


def test_ties_are_ordered_by_name(session: Session, main_user: User, add_expense: AddExpense):
    # Id order (Food, Transportation, Bills) differs from name order, so this tells them apart.
    add_expense(1000, date(2026, 11, 5), category_id=TRANSPORTATION)
    add_expense(1000, date(2026, 11, 5), category_id=FOOD)
    add_expense(1000, date(2026, 11, 5), category_id=BILLS)
    result = november(session, main_user)
    assert [c.category_name for c in result.categories] == ["Bills", "Food", "Transportation"]
    # Equal thirds each round to 33.3, so the percentages add up to 99.9, not 100.
    assert [c.percent for c in result.categories] == [Decimal("33.3")] * 3


# Report function: which transactions count


def test_only_expenses_within_the_month_count(
    session: Session, main_user: User, add_expense: AddExpense
):
    add_expense(100, date(2026, 11, 1), category_id=FOOD)
    add_expense(200, date(2026, 11, 30), category_id=FOOD)
    add_expense(1000, date(2026, 10, 31), category_id=BILLS)
    add_expense(1000, date(2026, 12, 1), category_id=SHOPPING)
    add_expense(1000, date(2025, 11, 15), category_id=TRANSPORTATION)
    assert november(session, main_user) == SpendingByCategory(
        total_spent_cents=300,
        categories=[CategorySpending(FOOD, "Food", 300, Decimal("100.0"))],
    )


def test_other_users_expenses_are_ignored(
    session: Session, main_user: User, other_user: User, add_expense: AddExpense
):
    add_expense(1000, date(2026, 11, 5), category_id=FOOD)
    add_expense(9000, date(2026, 11, 5), category_id=SHOPPING, user=other_user)
    assert november(session, main_user) == SpendingByCategory(
        total_spent_cents=1000,
        categories=[CategorySpending(FOOD, "Food", 1000, Decimal("100.0"))],
    )


# Endpoint

PATH = "/reports/2026/11/spending-by-category"


def test_endpoint_returns_breakdown(client: TestClient, add_expense: AddExpense):
    add_expense(7525, date(2026, 11, 5), category_id=BILLS)
    add_expense(2475, date(2026, 11, 5), category_id=FOOD)
    response = client.get(PATH)
    assert response.status_code == 200
    assert response.json() == {
        "total_spent": "100.00",
        "categories": [
            {"category_id": BILLS, "category_name": "Bills", "total": "75.25", "percent": 75.3},
            {"category_id": FOOD, "category_name": "Food", "total": "24.75", "percent": 24.8},
        ],
    }


def test_endpoint_with_no_expenses(client: TestClient):
    response = client.get(PATH)
    assert response.status_code == 200
    assert response.json() == {"total_spent": "0.00", "categories": []}


def test_endpoint_uses_the_current_user(
    client: TestClient, other_user: User, act_as: ActAs, add_expense: AddExpense
):
    add_expense(1000, date(2026, 11, 5))  # main_user's
    act_as(other_user)  # who has no expenses
    response = client.get(PATH)
    assert response.status_code == 200
    assert response.json() == {"total_spent": "0.00", "categories": []}


@pytest.mark.usefixtures("logged_out")
def test_endpoint_requires_a_logged_in_user(client: TestClient):
    assert client.get(PATH).status_code == 401


@pytest.mark.parametrize(
    "path",
    [
        pytest.param("/reports/1999/11/spending-by-category", id="year-out-of-range"),
        pytest.param("/reports/2026/13/spending-by-category", id="month-out-of-range"),
    ],
)
def test_endpoint_invalid_year_or_month_returns_422(client: TestClient, path: str):
    assert client.get(path).status_code == 422
