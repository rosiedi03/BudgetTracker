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


class TopCategoryOut(BaseModel):
    category_id: int
    category_name: str
    total: MoneyOutput


class MonthlySummaryOut(BaseModel):
    year: int
    month: int
    total_income: MoneyOutput
    total_expenses: MoneyOutput
    budget: MoneyOutput | None
    remaining: MoneyOutput | None
    percent_used: PercentOutput | None
    categories: list[CategorySpendingOut]
    top_category: TopCategoryOut | None
    ytd_income: MoneyOutput
    ytd_expenses: MoneyOutput
