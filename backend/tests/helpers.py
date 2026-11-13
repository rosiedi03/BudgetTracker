"""Constants and types shared by test files. Fixtures live in conftest.py."""

import datetime
from collections.abc import Callable
from typing import Protocol

from budgettracker.models import Transaction, User

# The act_as fixture: act_as(other_user).
type ActAs = Callable[[User], None]

# Ids of the seeded categories, which are always created in this order.
FOOD = 1
TRANSPORTATION = 2
BILLS = 3
ENTERTAINMENT = 4
SHOPPING = 5
OTHER = 6


class AddExpense(Protocol):
    """The add_expense fixture: add_expense(1250, date(2026, 11, 5), category_id=BILLS)."""

    def __call__(
        self,
        amount_cents: int,
        on: datetime.date,
        category_id: int = FOOD,
        user: User | None = None,
    ) -> Transaction: ...


class AddIncome(Protocol):
    """The add_income fixture: add_income(500000, date(2026, 11, 1))."""

    def __call__(
        self, amount_cents: int, on: datetime.date, user: User | None = None
    ) -> Transaction: ...
