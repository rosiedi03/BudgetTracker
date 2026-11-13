"""Percentages: calculating them from cents and writing them to JSON."""

from decimal import Decimal

import pytest
from pydantic import TypeAdapter

from budgettracker.reports import percent_of
from budgettracker.schemas.percent import PercentOutput

percent_output = TypeAdapter(PercentOutput)


# Calculation


@pytest.mark.parametrize(
    ("part_cents", "whole_cents", "expected"),
    [
        pytest.param(1, 3, "33.3", id="rounds-down"),
        pytest.param(2, 3, "66.7", id="rounds-up"),
        pytest.param(1, 8, "12.5", id="exact"),
        pytest.param(1, 16, "6.3", id="half-rounds-up"),
        pytest.param(5, 16, "31.3", id="half-rounds-up-again"),
        pytest.param(0, 500, "0.0", id="zero"),
        pytest.param(500, 500, "100.0", id="all"),
        pytest.param(15000, 10000, "150.0", id="over-100"),
        pytest.param(1, 9999999999, "0.0", id="tiny-share-rounds-to-zero"),
    ],
)
def test_percent_of(part_cents: int, whole_cents: int, expected: str):
    # Comparing the string form also checks there's exactly one decimal place.
    assert str(percent_of(part_cents, whole_cents)) == expected


def test_percent_of_zero_whole_raises():
    with pytest.raises(ZeroDivisionError):
        percent_of(100, 0)


# Output


@pytest.mark.parametrize(
    ("percent", "expected_json"),
    [
        (Decimal("33.3"), b"33.3"),
        (Decimal("0.0"), b"0.0"),
        (Decimal("100.0"), b"100.0"),
        (Decimal("150.0"), b"150.0"),
    ],
)
def test_output_percent_is_a_json_number(percent: Decimal, expected_json: bytes):
    assert percent_output.dump_json(percent) == expected_json
