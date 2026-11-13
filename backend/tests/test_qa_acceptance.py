"""QA acceptance tests: one test per test case in docs/qa/TEST_CASES.md (TC_01 - TC_32).

Unlike the unit tests, these go through the real API the way the frontend will: register, log in,
and send the token on every request. No dependencies are overridden except the database, which
conftest.py points at a fresh copy for every test.

Tests marked xfail document open defects (see docs/qa/TEST_REPORT.md). They are strict: when a
defect is fixed, its test starts passing, pytest reports that as a failure, and the marker must be
removed. That keeps the defect log and the code in step.
"""

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from budgettracker.main import app
from budgettracker.models import AuthToken, Transaction, utc_now
from budgettracker.routers.transactions import expenses, incomes

PASSWORD = "TestPass123"
EXPENSE = {"amount": 42.5, "category": "Food", "date": "2026-11-05", "description": "Groceries"}
INCOME = {"amount": 1500, "source": "Paycheck", "date": "2026-11-01"}

# Every endpoint that needs a login, with a body where one is required.
PROTECTED_ENDPOINTS = [
    ("GET", "/me", None),
    ("GET", "/expenses", None),
    ("POST", "/expenses", EXPENSE),
    ("PUT", "/expenses/0", EXPENSE),
    ("DELETE", "/expenses/0", None),
    ("GET", "/income", None),
    ("POST", "/income", INCOME),
    ("GET", "/categories", None),
    ("PUT", "/budgets/2026/11", {"limit": "500.00"}),
    ("GET", "/budgets/2026/11", None),
    ("GET", "/budgets/2026/11/status", None),
    ("GET", "/reports/2026/11/spending-by-category", None),
    ("GET", "/reports/2026/11/summary", None),
]


@pytest.fixture(autouse=True)
def clear_in_memory_transactions() -> Generator[None]:
    """Expenses and income are module-level dicts (DEF-02), so they'd leak between tests."""
    expenses.clear()
    incomes.clear()
    yield
    expenses.clear()
    incomes.clear()


@pytest.fixture
def api() -> TestClient:
    """A client with no login. Tests log in through the API like a real user."""
    return TestClient(app)


def register(api: TestClient, email: str, password: str = PASSWORD) -> int:
    return api.post("/register", json={"email": email, "password": password}).status_code


def login(api: TestClient, email: str = "luke@example.com") -> dict[str, str]:
    """Register a user, log in, and return the Authorization header for their token."""
    assert register(api, email) == 200
    response = api.post("/login", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


# ---- FR1: user registration ----


def test_tc01_register_with_valid_details_then_log_in(api: TestClient):
    assert register(api, "new@example.com") == 200
    response = api.post("/login", json={"email": "new@example.com", "password": PASSWORD})
    assert response.status_code == 200


@pytest.mark.parametrize("duplicate", ["new@example.com", "NEW@Example.com", " new@example.com "])
def test_tc02_duplicate_email_is_rejected(api: TestClient, duplicate: str):
    assert register(api, "new@example.com") == 200
    assert register(api, duplicate) == 409


@pytest.mark.parametrize("password", ["", "short", "1234567"])
def test_tc03_password_under_eight_characters_is_rejected(api: TestClient, password: str):
    assert register(api, "new@example.com", password) == 422


@pytest.mark.xfail(strict=True, reason="DEF-05: any text containing '@' is accepted as an email")
@pytest.mark.parametrize("email", ["a@", "@", "a b@c", "@example.com"])
def test_tc04_malformed_email_is_rejected(api: TestClient, email: str):
    assert register(api, email) == 422


@pytest.mark.xfail(strict=True, reason="DEF-05: a password of eight spaces is accepted")
def test_tc05_blank_password_is_rejected(api: TestClient):
    assert register(api, "new@example.com", " " * 8) == 422


# ---- FR2: login and token authentication ----


def test_tc06_login_returns_a_token_that_identifies_the_user(api: TestClient):
    headers = login(api, "luke@example.com")
    response = api.get("/me", headers=headers)
    assert response.status_code == 200
    assert response.json()["email"] == "luke@example.com"


def test_tc07_wrong_password_and_unknown_email_get_the_same_401(api: TestClient):
    register(api, "luke@example.com")
    wrong_password = api.post(
        "/login", json={"email": "luke@example.com", "password": "WrongPass123"}
    )
    unknown_email = api.post("/login", json={"email": "nobody@example.com", "password": PASSWORD})
    assert wrong_password.status_code == unknown_email.status_code == 401
    # Same message for both, so the response doesn't reveal which emails are registered.
    assert wrong_password.json() == unknown_email.json()


@pytest.mark.parametrize(("method", "path", "body"), PROTECTED_ENDPOINTS)
def test_tc08_protected_endpoints_reject_requests_without_a_token(
    api: TestClient, method: str, path: str, body: dict[str, object] | None
):
    assert api.request(method, path, json=body).status_code == 401
    bad_token = {"Authorization": "Bearer not-a-real-token"}
    assert api.request(method, path, json=body, headers=bad_token).status_code == 401


def test_tc09_expired_token_is_rejected(api: TestClient, session: Session):
    headers = login(api)
    token = session.scalars(select(AuthToken)).one()
    token.expires_at = utc_now()
    session.commit()
    assert api.get("/me", headers=headers).status_code == 401


# ---- FR3: expense management ----


def test_tc10_add_an_expense_and_see_it_in_the_list(api: TestClient):
    headers = login(api)
    assert api.post("/expenses", json=EXPENSE, headers=headers).status_code == 200
    listed = api.get("/expenses", headers=headers).json()
    assert len(listed) == 1
    assert listed[0]["amount"] == 42.5
    assert listed[0]["category"] == "Food"
    assert listed[0]["date"] == "2026-11-05"


def test_tc11_update_an_expense(api: TestClient):
    headers = login(api)
    api.post("/expenses", json=EXPENSE, headers=headers)
    updated = {**EXPENSE, "amount": 60, "category": "Bills"}
    assert api.put("/expenses/0", json=updated, headers=headers).status_code == 200
    listed = api.get("/expenses", headers=headers).json()
    assert (listed[0]["amount"], listed[0]["category"]) == (60, "Bills")


def test_tc12_delete_an_expense(api: TestClient):
    headers = login(api)
    api.post("/expenses", json=EXPENSE, headers=headers)
    assert api.delete("/expenses/0", headers=headers).status_code == 200
    assert api.get("/expenses", headers=headers).json() == []


@pytest.mark.parametrize(
    "invalid",
    [
        pytest.param({**EXPENSE, "amount": 0}, id="zero-amount"),
        pytest.param({**EXPENSE, "amount": -5}, id="negative-amount"),
        pytest.param({**EXPENSE, "amount": "abc"}, id="text-amount"),
        pytest.param({**EXPENSE, "date": "11/05/2026"}, id="wrong-date-format"),
        pytest.param({"amount": 10, "date": "2026-11-05"}, id="missing-category"),
        pytest.param({"amount": 10, "category": "Food"}, id="missing-date"),
    ],
)
def test_tc13_invalid_expense_is_rejected_and_not_saved(
    api: TestClient, invalid: dict[str, object]
):
    headers = login(api)
    assert api.post("/expenses", json=invalid, headers=headers).status_code == 422
    assert api.get("/expenses", headers=headers).json() == []


def test_tc14_updating_or_deleting_a_missing_expense_returns_404(api: TestClient):
    headers = login(api)
    assert api.put("/expenses/0", json=EXPENSE, headers=headers).status_code == 404
    assert api.delete("/expenses/0", headers=headers).status_code == 404
    assert api.delete("/expenses/-1", headers=headers).status_code == 404


@pytest.mark.xfail(strict=True, reason="DEF-04: expense category isn't checked against /categories")
@pytest.mark.parametrize("category", ["NotACategory", ""])
def test_tc15_unknown_expense_category_is_rejected(api: TestClient, category: str):
    headers = login(api)
    response = api.post("/expenses", json={**EXPENSE, "category": category}, headers=headers)
    assert response.status_code == 422


@pytest.mark.xfail(strict=True, reason="DEF-04: expenses skip the money rules used by budgets")
@pytest.mark.parametrize("amount", [0.001, 12.345, 100_000_000])
def test_tc16_expense_amount_follows_the_money_rules(api: TestClient, amount: float):
    """backend/README.md: at most two decimal places and at most 99,999,999.99."""
    headers = login(api)
    response = api.post("/expenses", json={**EXPENSE, "amount": amount}, headers=headers)
    assert response.status_code == 422


# ---- FR4: income management ----


def test_tc17_add_income_and_see_it_in_the_list(api: TestClient):
    headers = login(api)
    assert api.post("/income", json=INCOME, headers=headers).status_code == 200
    listed = api.get("/income", headers=headers).json()
    assert len(listed) == 1
    assert (listed[0]["amount"], listed[0]["source"]) == (1500, "Paycheck")


@pytest.mark.parametrize(
    "invalid",
    [
        pytest.param({**INCOME, "amount": 0}, id="zero-amount"),
        pytest.param({**INCOME, "amount": -100}, id="negative-amount"),
        pytest.param({"amount": 100, "date": "2026-11-01"}, id="missing-source"),
        pytest.param({**INCOME, "date": "not-a-date"}, id="bad-date"),
    ],
)
def test_tc18_invalid_income_is_rejected_and_not_saved(api: TestClient, invalid: dict[str, object]):
    headers = login(api)
    assert api.post("/income", json=invalid, headers=headers).status_code == 422
    assert api.get("/income", headers=headers).json() == []


# ---- FR5: monthly budget ----


def test_tc19_set_a_monthly_budget_and_read_it_back(api: TestClient):
    headers = login(api)
    saved = api.put("/budgets/2026/11", json={"limit": "500.00"}, headers=headers)
    assert saved.status_code == 200
    expected = {"year": 2026, "month": 11, "limit": "500.00"}
    assert api.get("/budgets/2026/11", headers=headers).json() == expected


def test_tc20_setting_a_budget_again_replaces_it(api: TestClient):
    headers = login(api)
    api.put("/budgets/2026/11", json={"limit": "500.00"}, headers=headers)
    api.put("/budgets/2026/11", json={"limit": "750.25"}, headers=headers)
    assert api.get("/budgets/2026/11", headers=headers).json()["limit"] == "750.25"


@pytest.mark.parametrize(
    ("path", "limit"),
    [
        pytest.param("/budgets/2026/11", "0", id="zero-limit"),
        pytest.param("/budgets/2026/11", "-50", id="negative-limit"),
        pytest.param("/budgets/2026/11", "10.999", id="fraction-of-a-cent"),
        pytest.param("/budgets/2026/11", "100000000", id="over-maximum"),
        pytest.param("/budgets/2026/13", "500", id="month-13"),
        pytest.param("/budgets/1999/11", "500", id="year-too-early"),
    ],
)
def test_tc21_invalid_budget_is_rejected(api: TestClient, path: str, limit: str):
    headers = login(api)
    assert api.put(path, json={"limit": limit}, headers=headers).status_code == 422


def test_tc22_month_without_a_budget_returns_404(api: TestClient):
    headers = login(api)
    assert api.get("/budgets/2026/11", headers=headers).status_code == 404


# ---- FR6: reports ----


def test_tc23_reports_for_an_empty_month_are_all_zero(api: TestClient):
    headers = login(api)
    summary = api.get("/reports/2026/11/summary", headers=headers).json()
    assert (summary["total_income"], summary["total_expenses"]) == ("0.00", "0.00")
    assert summary["categories"] == []
    assert summary["budget"] is None
    status = api.get("/budgets/2026/11/status", headers=headers).json()
    assert (status["spent"], status["limit"], status["percent_used"]) == ("0.00", None, None)


@pytest.mark.xfail(strict=True, reason="DEF-02: API expenses never reach the database")
def test_tc24_an_added_expense_counts_against_the_budget(api: TestClient):
    headers = login(api)
    api.put("/budgets/2026/11", json={"limit": "500.00"}, headers=headers)
    api.post("/expenses", json=EXPENSE, headers=headers)
    status = api.get("/budgets/2026/11/status", headers=headers).json()
    assert status["spent"] == "42.50"
    assert status["remaining"] == "457.50"
    assert status["percent_used"] == 8.5


@pytest.mark.xfail(strict=True, reason="DEF-02: API expenses never reach the database")
def test_tc25_an_added_expense_appears_in_spending_by_category(api: TestClient):
    headers = login(api)
    api.post("/expenses", json=EXPENSE, headers=headers)
    report = api.get("/reports/2026/11/spending-by-category", headers=headers).json()
    assert report["total_spent"] == "42.50"
    assert [category["category_name"] for category in report["categories"]] == ["Food"]


@pytest.mark.xfail(strict=True, reason="DEF-02: API income never reaches the database")
def test_tc26_added_income_appears_in_the_monthly_summary(api: TestClient):
    headers = login(api)
    api.post("/income", json=INCOME, headers=headers)
    summary = api.get("/reports/2026/11/summary", headers=headers).json()
    assert summary["total_income"] == "1500.00"
    assert summary["ytd_income"] == "1500.00"


# ---- FR7: each user sees only their own data ----


def test_tc27_users_cannot_see_or_change_each_others_transactions(api: TestClient):
    owner = login(api, "owner@example.com")
    intruder = login(api, "intruder@example.com")
    api.post("/expenses", json=EXPENSE, headers=owner)
    api.post("/income", json=INCOME, headers=owner)

    assert api.get("/expenses", headers=intruder).json() == []
    assert api.get("/income", headers=intruder).json() == []
    assert api.put("/expenses/0", json=EXPENSE, headers=intruder).status_code == 404
    assert api.delete("/expenses/0", headers=intruder).status_code == 404
    assert len(api.get("/expenses", headers=owner).json()) == 1


def test_tc28_users_cannot_see_or_change_each_others_budgets(api: TestClient):
    owner = login(api, "owner@example.com")
    intruder = login(api, "intruder@example.com")
    api.put("/budgets/2026/11", json={"limit": "500.00"}, headers=owner)

    assert api.get("/budgets/2026/11", headers=intruder).status_code == 404
    api.put("/budgets/2026/11", json={"limit": "1.00"}, headers=intruder)
    assert api.get("/budgets/2026/11", headers=owner).json()["limit"] == "500.00"


# ---- FR8: data is stored permanently ----


@pytest.mark.xfail(strict=True, reason="DEF-02: transactions are kept in memory, lost on restart")
def test_tc29_transactions_are_saved_to_the_database(api: TestClient, session: Session):
    headers = login(api)
    api.post("/expenses", json=EXPENSE, headers=headers)
    api.post("/income", json=INCOME, headers=headers)
    assert session.scalar(select(func.count()).select_from(Transaction)) == 2


# ---- System ----


def test_tc30_health_check_works_without_a_login(api: TestClient):
    response = api.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "running"}


def test_tc31_cors_allows_the_frontend_origin_only(api: TestClient):
    def preflight(origin: str):
        return api.options(
            "/expenses",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "authorization,content-type",
            },
        )

    allowed = preflight("http://localhost:5173")
    assert allowed.status_code == 200
    assert allowed.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert "access-control-allow-origin" not in preflight("http://evil.example.com").headers


def test_tc32_api_documentation_lists_every_endpoint(api: TestClient):
    assert api.get("/docs").status_code == 200
    documented = api.get("/openapi.json").json()["paths"]
    for _method, path, _body in PROTECTED_ENDPOINTS:
        template = path.replace("/2026/11", "/{year}/{month}").replace("/0", "/{index}")
        assert template in documented
