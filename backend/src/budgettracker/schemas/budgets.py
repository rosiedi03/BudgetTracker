from pydantic import BaseModel

from budgettracker.schemas.money import MoneyInput, MoneyOutput


class BudgetIn(BaseModel):
    limit: MoneyInput


class BudgetOut(BaseModel):
    year: int
    month: int
    limit: MoneyOutput
