"""Percentages in API responses."""

from decimal import Decimal
from typing import Annotated

from pydantic import Field, PlainSerializer

# Written to JSON as a number with one decimal place.
PercentOutput = Annotated[
    Decimal,
    PlainSerializer(float, return_type=float, when_used="json"),
    Field(
        description=(
            "Percentage rounded to one decimal place. A share under 0.05% rounds to 0.0, so when "
            'the matching amount is non-zero, display 0.0 as "<0.1%".'
        )
    ),
]
