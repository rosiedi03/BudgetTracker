"""PLACEHOLDER: in-memory expense/income routes, to be replaced by database-backed ones."""

from datetime import date

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(tags=["transactions"])


# Expense information received from the frontend
class Expense(BaseModel):
    amount: float = Field(gt=0)
    category: str
    date: date
    description: str = ""
    payer: str = ""


# Temporary storage until the database is connected
expenses = []


@router.post("/expenses")
def add_expense(expense: Expense):
    expenses.append(expense.model_dump(mode="json"))
    return {"message": "Expense added successfully"}


@router.get("/expenses")
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


@router.post("/income")
def add_income(income: Income):
    incomes.append(income.model_dump(mode="json"))
    return {"message": "Income added successfully"}


@router.get("/income")
def get_income():
    return incomes


# Update an existing expense
@router.put("/expenses/{index}")
def update_expense(index: int, expense: Expense):
    if index < 0 or index >= len(expenses):
        raise HTTPException(status_code=404, detail="Expense not found")
    expenses[index] = expense.model_dump(mode="json")
    return {"message": "Expense updated successfully"}


# Delete an existing expense
@router.delete("/expenses/{index}")
def delete_expense(index: int):
    if index < 0 or index >= len(expenses):
        raise HTTPException(status_code=404, detail="Expense not found")
    expenses.pop(index)
    return {"message": "Expense deleted successfully"}
