from fastapi.testclient import TestClient
from budgettracker.main import app
from budgettracker.routers.transactions import expenses, incomes
from datetime import UTC, datetime, timedelta
from sqlalchemy import select
from sqlalchemy.orm import Session
from budgettracker.models import AuthToken

client = TestClient(app)


# Test that the server responds
def test_health():
    response = client.get("/health")
    assert response.status_code == 200


# Test adding and retrieving an expense
def test_expense():
    expenses.clear()

    data = {"amount": 50, "category": "Groceries", "date": "2026-11-11"}

    response = client.post("/expenses", json=data)
    assert response.status_code == 200

    response = client.get("/expenses")
    assert response.status_code == 200
    assert response.json()[0]["amount"] == 50

    expenses.clear()


# Test that negative amounts are rejected
def test_invalid_expense():
    expenses.clear()

    data = {"amount": -50, "category": "Groceries", "date": "2026-11-11"}

    response = client.post("/expenses", json=data)
    assert response.status_code == 422
    assert expenses == []


# Test adding and retrieving income
def test_income():
    incomes.clear()
    data = {"amount": 1500, "source": "Salary", "date": "2026-11-11"}
    response = client.post("/income", json=data)
    assert response.status_code == 200
    response = client.get("/income")
    assert response.status_code == 200
    assert response.json()[0]["amount"] == 1500
    incomes.clear()


# Test invalid income
def test_invalid_income():
    incomes.clear()
    data = {"amount": -50, "source": "Salary", "date": "2026-11-11"}
    response = client.post("/income", json=data)
    assert response.status_code == 422
    assert incomes == []


# Test updating an expense
def test_update_expense():
    expenses.clear()
    data = {"amount": 50, "category": "Food", "date": "2026-11-11"}
    client.post("/expenses", json=data)
    data["amount"] = 75
    response = client.put("/expenses/0", json=data)
    assert response.status_code == 200
    assert client.get("/expenses").json()[0]["amount"] == 75
    expenses.clear()


# Test deleting an expense
def test_delete_expense():
    expenses.clear()
    data = {"amount": 50, "category": "Food", "date": "2026-11-11"}
    client.post("/expenses", json=data)
    response = client.delete("/expenses/0")
    assert response.status_code == 200
    assert client.get("/expenses").json() == []


# Test registration and login
def test_register_login():
    data = {"email": "test@example.com", "password": "TestPass123"}
    response = client.post("/register", json=data)
    assert response.status_code == 200

    response = client.post("/login", json=data)
    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
    assert response.json()["access_token"]


# Test incorrect password
def test_invalid_login():
    data = {"email": "test@example.com", "password": "TestPass123"}
    client.post("/register", json=data)

    data["password"] = "WrongPass123"
    response = client.post("/login", json=data)
    assert response.status_code == 401


# Test access with a valid token
def test_valid_token():
    data = {"email": "secure@example.com", "password": "TestPass123"}
    client.post("/register", json=data)
    response = client.post("/login", json=data)
    token = response.json()["access_token"]

    response = client.get("/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["email"] == data["email"]

# Test access without a token
def test_missing_token():
    response = client.get("/me")
    assert response.status_code == 401

# Test access with an invalid token
def test_invalid_token():
    response = client.get("/me", headers={"Authorization": "Bearer invalid-token"})
    assert response.status_code == 401

# Test that expired tokens are rejected
def test_expired_token(session: Session):
    data = {"email": "expired@example.com", "password": "TestPass123"}
    client.post("/register", json=data)
    response = client.post("/login", json=data)
    assert response.status_code == 200
    token = response.json()["access_token"]

    # Set the token expiration to the past
    saved_token = session.scalar(select(AuthToken))
    assert saved_token is not None
    saved_token.expires_at = datetime.now(UTC) - timedelta(minutes=1)
    session.commit()

    response = client.get("/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
