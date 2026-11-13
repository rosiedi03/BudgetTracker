"""Money in the API.

Amounts are Decimal values with two decimal places, sent and received as JSON strings like
"12.50". The database and business logic use integer cents; convert with the functions below.
"""

from decimal import Decimal
from typing import Annotated

from pydantic import AfterValidator, Field, PlainSerializer

MAX_AMOUNT = Decimal("99999999.99")
ONE_CENT = Decimal("0.01")


def _require_whole_cents(amount: Decimal) -> Decimal:
    """Reject fractions of a cent; return the amount with exactly two decimal places."""
    rounded = amount.quantize(ONE_CENT)
    if rounded != amount:
        raise ValueError("must have at most 2 decimal places")
    return rounded


def _format_two_places(amount: Decimal) -> str:
    return str(amount.quantize(ONE_CENT))


# For amounts in requests: positive, at most MAX_AMOUNT, whole cents. Accepts a JSON number or
# string. Pydantic checks the Field limits first, then runs the AfterValidator.
MoneyInput = Annotated[
    Decimal,
    Field(gt=0, le=MAX_AMOUNT),
    AfterValidator(_require_whole_cents),
]

# For amounts in responses: any value, including zero and negatives, written to JSON as a string
# with two decimal places.
MoneyOutput = Annotated[Decimal, PlainSerializer(_format_two_places, when_used="json")]


def decimal_to_cents(amount: Decimal) -> int:
    """Convert an amount like Decimal("12.50") to cents (1250)."""
    cents = amount * 100
    if cents != cents.to_integral_value():
        raise ValueError(f"{amount} has fractions of a cent")
    return int(cents)


def cents_to_decimal(cents: int) -> Decimal:
    """Convert cents (1250) to an amount with exactly two decimal places (Decimal("12.50"))."""
    return (Decimal(cents) / 100).quantize(ONE_CENT)


def optional_cents_to_decimal(cents: int | None) -> Decimal | None:
    """cents_to_decimal, but None stays None (for fields that are null when no budget is set)."""
    if cents is None:
        return None
    return cents_to_decimal(cents)
