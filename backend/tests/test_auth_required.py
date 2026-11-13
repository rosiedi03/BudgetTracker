"""Budget, report, and category endpoints only work with a valid login token."""

import datetime
from datetime import date

import pytest
from fastapi.testclient import TestClient

from budgettracker.main import app
from budgettracker.models import User, utc_now
from tests.helpers import AddExpense, TokenFor

ENDPOINTS = [
    pytest.param("GET", "/categories", id="list-categories"),
    pytest.param("PUT", "/budgets/2026/11", id="set-budget"),
    pytest.param("GET", "/budgets/2026/11", id="get-budget"),
    pytest.param("GET", "/budgets/2026/11/status", id="budget-status"),
    pytest.param("GET", "/reports/2026/11/spending-by-category", id="spending-by-category"),
    pytest.param("GET", "/reports/2026/11/summary", id="monthly-summary"),
]


def send(method: str, path: str, headers: dict[str, str] | None = None):
    """Send a request from a client with no login, plus any headers given."""
    body = {"limit": "500.00"} if method == "PUT" else None
    return TestClient(app).request(method, path, json=body, headers=headers)


@pytest.mark.parametrize(("method", "path"), ENDPOINTS)
def test_without_a_token_returns_401(method: str, path: str):
    assert send(method, path).status_code == 401


@pytest.mark.parametrize(("method", "path"), ENDPOINTS)
def test_with_an_unknown_token_returns_401(method: str, path: str):
    headers = {"Authorization": "Bearer not-a-real-token"}
    assert send(method, path, headers).status_code == 401


@pytest.mark.parametrize(("method", "path"), ENDPOINTS)
def test_with_an_expired_token_returns_401(
    main_user: User, token_for: TokenFor, method: str, path: str
):
    headers = token_for(main_user, expires_at=utc_now() - datetime.timedelta(minutes=1))
    assert send(method, path, headers).status_code == 401


@pytest.mark.parametrize(
    ("method", "path", "expected_status"),
    [
        pytest.param("GET", "/categories", 200, id="list-categories"),
        pytest.param("PUT", "/budgets/2026/11", 200, id="set-budget"),
        pytest.param("GET", "/budgets/2026/11", 404, id="get-budget"),  # none set yet
        pytest.param("GET", "/budgets/2026/11/status", 200, id="budget-status"),
        pytest.param(
            "GET", "/reports/2026/11/spending-by-category", 200, id="spending-by-category"
        ),
        pytest.param("GET", "/reports/2026/11/summary", 200, id="monthly-summary"),
    ],
)
def test_with_a_valid_token_works(
    main_user: User, token_for: TokenFor, method: str, path: str, expected_status: int
):
    assert send(method, path, token_for(main_user)).status_code == expected_status


def test_the_token_decides_whose_data_is_used(
    main_user: User, other_user: User, token_for: TokenFor, add_expense: AddExpense
):
    add_expense(1000, date(2026, 11, 5))  # the dev user's
    dev_headers = token_for(main_user)
    other_headers = token_for(other_user)

    dev_summary = send("GET", "/reports/2026/11/summary", dev_headers)
    other_summary = send("GET", "/reports/2026/11/summary", other_headers)
    assert dev_summary.status_code == 200
    assert other_summary.status_code == 200
    assert dev_summary.json()["total_expenses"] == "10.00"
    assert other_summary.json()["total_expenses"] == "0.00"

    assert send("PUT", "/budgets/2026/11", other_headers).status_code == 200
    assert send("GET", "/budgets/2026/11", other_headers).status_code == 200
    assert send("GET", "/budgets/2026/11", dev_headers).status_code == 404
