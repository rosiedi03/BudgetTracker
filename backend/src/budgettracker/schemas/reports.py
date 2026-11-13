from pydantic import BaseModel

from budgettracker.schemas.money import MoneyOutput
from budgettracker.schemas.percent import PercentOutput


class CategorySpendingOut(BaseModel):
    category_id: int
    category_name: str
    total: MoneyOutput
    percent: PercentOutput


class SpendingByCategoryOut(BaseModel):
    total_spent: MoneyOutput
    categories: list[CategorySpendingOut]
