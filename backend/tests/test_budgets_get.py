"""GET /budgets/{year}/{month}: fetching a month's spending limit."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from budgettracker.models import MonthlyBudget, User
from tests.helpers import ActAs


@pytest.fixture
def november_budget(session: Session, main_user: User) -> None:
    """The dev user has a 500.00 budget for November 2026."""
    session.add(MonthlyBudget(user_id=main_user.id, year=2026, month=11, limit_cents=50000))
    session.commit()


@pytest.mark.usefixtures("november_budget")
def test_returns_the_budget(client: TestClient):
    response = client.get("/budgets/2026/11")
    assert response.status_code == 200
    assert response.json() == {"year": 2026, "month": 11, "limit": "500.00"}


def test_returns_404_when_no_budget_is_set(client: TestClient):
    response = client.get("/budgets/2026/11")
    assert response.status_code == 404
    assert "detail" in response.json()


@pytest.mark.usefixtures("november_budget")
@pytest.mark.parametrize(
    "path",
    [
        pytest.param("/budgets/2026/12", id="other-month"),
        pytest.param("/budgets/2027/11", id="same-month-other-year"),
    ],
)
def test_returns_404_for_a_month_without_a_budget(client: TestClient, path: str):
    assert client.get(path).status_code == 404


@pytest.mark.usefixtures("november_budget")
def test_another_users_budget_is_not_found(client: TestClient, other_user: User, act_as: ActAs):
    act_as(other_user)  # who has no budget of their own
    assert client.get("/budgets/2026/11").status_code == 404


@pytest.mark.usefixtures("november_budget", "logged_out")
def test_requires_a_logged_in_user(client: TestClient):
    assert client.get("/budgets/2026/11").status_code == 401


@pytest.mark.parametrize(
    "path",
    [
        pytest.param("/budgets/1999/11", id="year-out-of-range"),
        pytest.param("/budgets/2026/13", id="month-out-of-range"),
        pytest.param("/budgets/2026/abc", id="month-not-a-number"),
    ],
)
def test_invalid_year_or_month_returns_422(client: TestClient, path: str):
    assert client.get(path).status_code == 422
