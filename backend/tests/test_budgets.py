"""PUT /budgets/{year}/{month}: setting a month's spending limit."""

import threading
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, event, select
from sqlalchemy.orm import Session

from budgettracker.budgets import set_monthly_budget
from budgettracker.models import MonthlyBudget, User
from tests.helpers import ActAs


def all_budgets(session: Session) -> list[tuple[int, int, int, int]]:
    """Every budget row as (user_id, year, month, limit_cents), freshly read from the database."""
    session.expire_all()  # forget cached rows so changes made by the app are visible
    budgets = session.scalars(select(MonthlyBudget).order_by(MonthlyBudget.id))
    return [(b.user_id, b.year, b.month, b.limit_cents) for b in budgets]


# Creating and replacing


def test_creates_budget(client: TestClient, session: Session, main_user: User):
    response = client.put("/budgets/2026/11", json={"limit": "500.00"})
    assert response.status_code == 200
    assert response.json() == {"year": 2026, "month": 11, "limit": "500.00"}
    assert all_budgets(session) == [(main_user.id, 2026, 11, 50000)]


def test_setting_again_replaces_the_limit(client: TestClient, session: Session, main_user: User):
    first = client.put("/budgets/2026/11", json={"limit": "500.00"})
    assert first.status_code == 200
    assert all_budgets(session) == [(main_user.id, 2026, 11, 50000)]

    response = client.put("/budgets/2026/11", json={"limit": "750.25"})
    assert response.status_code == 200
    assert response.json() == {"year": 2026, "month": 11, "limit": "750.25"}
    assert all_budgets(session) == [(main_user.id, 2026, 11, 75025)]


def test_each_month_has_its_own_budget(client: TestClient, session: Session, main_user: User):
    client.put("/budgets/2026/11", json={"limit": "500.00"})
    client.put("/budgets/2026/12", json={"limit": "650.00"})
    client.put("/budgets/2027/11", json={"limit": "700.00"})
    assert all_budgets(session) == [
        (main_user.id, 2026, 11, 50000),
        (main_user.id, 2026, 12, 65000),
        (main_user.id, 2027, 11, 70000),
    ]


def test_two_saves_at_once_for_a_new_month_keep_one_budget(
    db_engine: Engine, session: Session, main_user: User
):
    # E.g. a double-clicked Save. Each save runs in its own thread and session, like two requests.
    # The barrier holds each save just before it writes, until both have got that far, so the
    # writes always overlap instead of only sometimes.
    both_ready_to_write = threading.Barrier(2, timeout=5)

    def wait_before_budget_insert(_conn, _cursor, statement: str, *_args) -> None:
        if statement.startswith("INSERT INTO monthly_budgets"):
            both_ready_to_write.wait()

    event.listen(db_engine, "before_cursor_execute", wait_before_budget_insert)
    user_id = main_user.id

    def save(limit_cents: int) -> None:
        with Session(db_engine) as request_session:
            user = request_session.get_one(User, user_id)
            set_monthly_budget(request_session, user, 2026, 11, limit_cents)
            request_session.commit()

    with ThreadPoolExecutor(max_workers=2) as pool:
        saves = [pool.submit(save, 50000), pool.submit(save, 75000)]
    for finished in saves:
        finished.result()  # re-raises any error from inside the thread

    budgets = all_budgets(session)
    assert len(budgets) == 1
    assert budgets[0][3] in (50000, 75000)  # whichever save wrote last


def test_limit_can_be_sent_as_a_number(client: TestClient):
    response = client.put("/budgets/2026/11", json={"limit": 500})
    assert response.status_code == 200
    assert response.json()["limit"] == "500.00"


# Users


def test_never_changes_another_users_budget(
    client: TestClient, session: Session, main_user: User, other_user: User, act_as: ActAs
):
    session.add(MonthlyBudget(user_id=main_user.id, year=2026, month=11, limit_cents=50000))
    session.commit()

    act_as(other_user)
    response = client.put("/budgets/2026/11", json={"limit": "900.00"})
    assert response.status_code == 200
    assert all_budgets(session) == [
        (main_user.id, 2026, 11, 50000),
        (other_user.id, 2026, 11, 90000),
    ]


@pytest.mark.usefixtures("logged_out")
def test_requires_a_logged_in_user(client: TestClient, session: Session):
    assert client.put("/budgets/2026/11", json={"limit": "500.00"}).status_code == 401
    assert all_budgets(session) == []


# Validation


@pytest.mark.parametrize(
    ("path", "body"),
    [
        pytest.param("/budgets/2026/11", {"limit": "0"}, id="limit-zero"),
        pytest.param("/budgets/2026/11", {"limit": "-5.00"}, id="limit-negative"),
        pytest.param("/budgets/2026/11", {"limit": "12.345"}, id="limit-fraction-of-cent"),
        pytest.param("/budgets/2026/11", {"limit": "100000000.00"}, id="limit-too-large"),
        pytest.param("/budgets/2026/11", {"limit": "abc"}, id="limit-not-a-number"),
        pytest.param("/budgets/2026/11", {}, id="limit-missing"),
        pytest.param("/budgets/1999/11", {"limit": "500.00"}, id="year-out-of-range"),
        pytest.param("/budgets/2026/13", {"limit": "500.00"}, id="month-out-of-range"),
    ],
)
def test_invalid_request_returns_422_and_saves_nothing(
    client: TestClient, session: Session, path: str, body: dict
):
    assert client.put(path, json=body).status_code == 422
    assert all_budgets(session) == []
