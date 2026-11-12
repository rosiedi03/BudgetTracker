from fastapi.testclient import TestClient

from budgettracker.main import app, expenses, incomes, users

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
    users.clear()
    data = {"email": "test@example.com", "password": "TestPass123"}
    response = client.post("/register", json=data)
    assert response.status_code == 200
    assert users[data["email"]] != data["password"]
    response = client.post("/login", json=data)
    assert response.status_code == 200
    users.clear()


# Test incorrect password
def test_invalid_login():
    users.clear()
    data = {"email": "test@example.com", "password": "TestPass123"}
    client.post("/register", json=data)
    data["password"] = "WrongPass123"
    response = client.post("/login", json=data)
    assert response.status_code == 401
    users.clear()
