from pydantic import BaseModel

from budgettracker.schemas.money import MoneyInput, MoneyOutput
from budgettracker.schemas.percent import PercentOutput


class BudgetIn(BaseModel):
    limit: MoneyInput


class BudgetOut(BaseModel):
    year: int
    month: int
    limit: MoneyOutput


class BudgetStatusOut(BaseModel):
    year: int
    month: int
    limit: MoneyOutput | None
    spent: MoneyOutput
    remaining: MoneyOutput | None
    percent_used: PercentOutput | None
