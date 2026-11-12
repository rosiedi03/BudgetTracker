from datetime import date

from fastapi import FastAPI, HTTPException
from pwdlib import PasswordHash
from pydantic import BaseModel, Field

# Create the Budget Tracker backend application
app = FastAPI(title="Budget Tracker API")


# Check if the backend server is running
@app.get("/health")
def health_check():
    return {"status": "running"}


# Expense information received from the frontend
class Expense(BaseModel):
    amount: float = Field(gt=0)
    category: str
    date: date
    description: str = ""
    payer: str = ""


# Temporary storage until the database is connected
expenses = []


@app.post("/expenses")
def add_expense(expense: Expense):
    expenses.append(expense.model_dump(mode="json"))
    return {"message": "Expense added successfully"}


@app.get("/expenses")
def get_expenses():
    return expenses


# Income information received from the frontend
class Income(BaseModel):
    amount: float = Field(gt=0)
    source: str
    date: date
    description: str = ""


# Temporary income storage
incomes = []


@app.post("/income")
def add_income(income: Income):
    incomes.append(income.model_dump(mode="json"))
    return {"message": "Income added successfully"}


@app.get("/income")
def get_income():
    return incomes


# Update an existing expense
@app.put("/expenses/{index}")
def update_expense(index: int, expense: Expense):
    if index < 0 or index >= len(expenses):
        raise HTTPException(status_code=404, detail="Expense not found")
    expenses[index] = expense.model_dump(mode="json")
    return {"message": "Expense updated successfully"}


# Delete an existing expense
@app.delete("/expenses/{index}")
def delete_expense(index: int):
    if index < 0 or index >= len(expenses):
        raise HTTPException(status_code=404, detail="Expense not found")
    expenses.pop(index)
    return {"message": "Expense deleted successfully"}


# Password hashing and temporary user storage
password_hash = PasswordHash.recommended()
users = {}


class User(BaseModel):
    email: str
    password: str = Field(min_length=8)


# Register a new user
@app.post("/register")
def register(user: User):
    email = user.email.strip().lower()
    if email in users:
        raise HTTPException(status_code=409, detail="User already exists")
    users[email] = password_hash.hash(user.password)
    return {"message": "Registration successful"}


# Verify user login
@app.post("/login")
def login(user: User):
    email = user.email.strip().lower()
    saved_password = users.get(email)
    if not saved_password or not password_hash.verify(user.password, saved_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"message": "Login successful"}
