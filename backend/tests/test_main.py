from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from budgettracker.main import app
from budgettracker.models import AuthToken, User
from budgettracker.routers.transactions import expenses, incomes

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_data():
    expenses.clear()
    incomes.clear()
    yield
    expenses.clear()
    incomes.clear()


# Register and log in a user
def login_headers(email="test@example.com"):
    data = {"email": email, "password": "TestPass123"}
    assert client.post("/register", json=data).status_code == 200
    response = client.post("/login", json=data)
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_health():
    assert client.get("/health").status_code == 200


def test_expense():
    headers = login_headers()
    data = {"amount": 50, "category": "Groceries", "date": "2026-11-11"}
    assert client.post("/expenses", json=data, headers=headers).status_code == 200
    response = client.get("/expenses", headers=headers)
    assert response.status_code == 200
    assert response.json()[0]["amount"] == 50


def test_invalid_expense():
    headers = login_headers()
    data = {"amount": -50, "category": "Groceries", "date": "2026-11-11"}
    assert client.post("/expenses", json=data, headers=headers).status_code == 422
    assert client.get("/expenses", headers=headers).json() == []


def test_income():
    headers = login_headers()
    data = {"amount": 1500, "source": "Salary", "date": "2026-11-11"}
    assert client.post("/income", json=data, headers=headers).status_code == 200
    assert client.get("/income", headers=headers).json()[0]["amount"] == 1500


def test_invalid_income():
    headers = login_headers()
    data = {"amount": -50, "source": "Salary", "date": "2026-11-11"}
    assert client.post("/income", json=data, headers=headers).status_code == 422


def test_update_expense():
    headers = login_headers()
    data = {"amount": 50, "category": "Food", "date": "2026-11-11"}
    client.post("/expenses", json=data, headers=headers)
    data["amount"] = 75
    assert client.put("/expenses/0", json=data, headers=headers).status_code == 200
    assert client.get("/expenses", headers=headers).json()[0]["amount"] == 75


def test_delete_expense():
    headers = login_headers()
    data = {"amount": 50, "category": "Food", "date": "2026-11-11"}
    client.post("/expenses", json=data, headers=headers)
    assert client.delete("/expenses/0", headers=headers).status_code == 200
    assert client.get("/expenses", headers=headers).json() == []


def test_register_login(session: Session):
    data = {"email": "test@example.com", "password": "TestPass123"}
    assert client.post("/register", json=data).status_code == 200
    user = session.scalar(select(User).where(User.email == data["email"]))
    assert user is not None
    assert user.password_hash != data["password"]
    response = client.post("/login", json=data)
    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
    assert response.json()["access_token"]


def test_invalid_login():
    data = {"email": "test@example.com", "password": "TestPass123"}
    client.post("/register", json=data)
    data["password"] = "WrongPass123"
    assert client.post("/login", json=data).status_code == 401


def test_valid_token():
    headers = login_headers()
    response = client.get("/me", headers=headers)
    assert response.status_code == 200
    assert response.json()["email"] == "test@example.com"


def test_missing_token():
    assert client.get("/me").status_code == 401
    assert client.get("/expenses").status_code == 401
    assert client.get("/income").status_code == 401


def test_invalid_token():
    headers = {"Authorization": "Bearer invalid-token"}
    assert client.get("/me", headers=headers).status_code == 401


def test_expired_token(session: Session):
    headers = login_headers("expired@example.com")
    token = session.scalar(select(AuthToken))
    assert token is not None
    token.expires_at = datetime.now(UTC) - timedelta(minutes=1)
    session.commit()
    assert client.get("/me", headers=headers).status_code == 401


# Check that users cannot access each other's data
def test_user_data_isolation():
    user_a = login_headers("usera@example.com")
    user_b = login_headers("userb@example.com")
    expense = {"amount": 50, "category": "Food", "date": "2026-11-11"}
    income = {"amount": 100, "source": "Salary", "date": "2026-11-11"}
    client.post("/expenses", json=expense, headers=user_a)
    client.post("/income", json=income, headers=user_a)
    assert len(client.get("/expenses", headers=user_a).json()) == 1
    assert len(client.get("/income", headers=user_a).json()) == 1
    assert client.get("/expenses", headers=user_b).json() == []
    assert client.get("/income", headers=user_b).json() == []
    assert client.put("/expenses/0", json=expense, headers=user_b).status_code == 404
    assert client.delete("/expenses/0", headers=user_b).status_code == 404
    assert len(client.get("/expenses", headers=user_a).json()) == 1
