"""Expense and income endpoints."""

from datetime import date

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from budgettracker.deps import AuthenticatedUserDep

router = APIRouter(tags=["transactions"])


class Expense(BaseModel):
    amount: float = Field(gt=0)
    category: str
    date: date
    description: str = ""
    payer: str = ""


class Income(BaseModel):
    amount: float = Field(gt=0)
    source: str
    date: date
    description: str = ""


# Temporary data separated by user ID
expenses = {}
incomes = {}


# Add an expense for the logged-in user
@router.post("/expenses")
def add_expense(expense: Expense, user: AuthenticatedUserDep):
    expenses.setdefault(user.id, []).append(expense.model_dump(mode="json"))
    return {"message": "Expense added successfully"}


# View only the user's expenses
@router.get("/expenses")
def get_expenses(user: AuthenticatedUserDep):
    return expenses.get(user.id, [])


# Add income for the logged-in user
@router.post("/income")
def add_income(income: Income, user: AuthenticatedUserDep):
    incomes.setdefault(user.id, []).append(income.model_dump(mode="json"))
    return {"message": "Income added successfully"}


# View only the user's income
@router.get("/income")
def get_income(user: AuthenticatedUserDep):
    return incomes.get(user.id, [])


# Update only the user's expense
@router.put("/expenses/{index}")
def update_expense(index: int, expense: Expense, user: AuthenticatedUserDep):
    user_expenses = expenses.get(user.id, [])
    if index < 0 or index >= len(user_expenses):
        raise HTTPException(status_code=404, detail="Expense not found")
    user_expenses[index] = expense.model_dump(mode="json")
    return {"message": "Expense updated successfully"}


# Delete only the user's expense
@router.delete("/expenses/{index}")
def delete_expense(index: int, user: AuthenticatedUserDep):
    user_expenses = expenses.get(user.id, [])
    if index < 0 or index >= len(user_expenses):
        raise HTTPException(status_code=404, detail="Expense not found")
    user_expenses.pop(index)
    return {"message": "Expense deleted successfully"}
