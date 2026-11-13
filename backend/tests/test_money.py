"""Money amounts: validating request input, formatting response output, converting to cents."""

from decimal import Decimal

import pytest
from pydantic import TypeAdapter, ValidationError

from budgettracker.schemas.money import (
    MoneyInput,
    MoneyOutput,
    cents_to_decimal,
    decimal_to_cents,
    optional_cents_to_decimal,
)

# A TypeAdapter applies a type's validation and serialization on its own, without a full model.
money_input = TypeAdapter(MoneyInput)
money_output = TypeAdapter(MoneyOutput)


# Input: accepted


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("12.50", Decimal("12.50")),
        ("12.5", Decimal("12.50")),
        ("12", Decimal("12.00")),
        ("0.01", Decimal("0.01")),
        ("99999999.99", Decimal("99999999.99")),
        ("12.500", Decimal("12.50")),  # trailing zeros don't count as extra decimal places
    ],
)
def test_string_amount_is_accepted(raw: str, expected: Decimal):
    assert money_input.validate_python(raw) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (12, Decimal("12.00")),
        (12.5, Decimal("12.50")),
        (0.1, Decimal("0.10")),
        (1.1, Decimal("1.10")),
        (19.99, Decimal("19.99")),
    ],
)
def test_number_amount_is_accepted(raw: float, expected: Decimal):
    assert money_input.validate_python(raw) == expected


@pytest.mark.parametrize(
    ("json_text", "expected"),
    [
        ('"12.50"', Decimal("12.50")),
        ("12.5", Decimal("12.50")),
        ("19.99", Decimal("19.99")),
    ],
)
def test_amount_from_json_is_accepted(json_text: str, expected: Decimal):
    assert money_input.validate_json(json_text) == expected


# Input: rejected


@pytest.mark.parametrize(
    "raw",
    [
        # Not positive
        "0",
        "0.00",
        0,
        "-5.00",
        -5,
        # More than two decimal places
        "12.345",
        12.345,
        "0.001",
        # Too large
        "100000000.00",
        100000000,
        # Not a number
        "abc",
        "",
        "NaN",
        "Infinity",
        "-Infinity",
        None,
        True,
    ],
)
def test_invalid_amount_is_rejected(raw: object):
    with pytest.raises(ValidationError):
        money_input.validate_python(raw)


# Output


@pytest.mark.parametrize(
    ("amount", "expected_json"),
    [
        (Decimal("12.5"), b'"12.50"'),
        (Decimal("12"), b'"12.00"'),
        (Decimal("0"), b'"0.00"'),
        (Decimal("-3.2"), b'"-3.20"'),  # e.g. a negative remaining budget
        (Decimal("1234567.89"), b'"1234567.89"'),
    ],
)
def test_output_amount_is_a_string_with_two_decimal_places(amount: Decimal, expected_json: bytes):
    assert money_output.dump_json(amount) == expected_json


# Conversion to and from cents


@pytest.mark.parametrize(
    ("amount", "cents"),
    [
        (Decimal("12.50"), 1250),
        (Decimal("12.5"), 1250),
        (Decimal("12"), 1200),
        (Decimal("0.01"), 1),
        (Decimal("99999999.99"), 9999999999),
    ],
)
def test_decimal_to_cents(amount: Decimal, cents: int):
    result = decimal_to_cents(amount)
    assert result == cents
    assert type(result) is int


def test_decimal_to_cents_rejects_fractions_of_a_cent():
    with pytest.raises(ValueError):
        decimal_to_cents(Decimal("0.001"))


@pytest.mark.parametrize(
    ("cents", "expected"),
    [
        (1250, "12.50"),
        (1200, "12.00"),
        (1, "0.01"),
        (0, "0.00"),
        (-320, "-3.20"),
        (9999999999, "99999999.99"),
    ],
)
def test_cents_to_decimal_has_exactly_two_decimal_places(cents: int, expected: str):
    # Comparing the string form checks the number of decimal places, not just the value.
    assert str(cents_to_decimal(cents)) == expected


def test_cents_survive_a_round_trip():
    for cents in range(-1000, 1001):
        assert decimal_to_cents(cents_to_decimal(cents)) == cents


@pytest.mark.parametrize(
    ("cents", "expected"),
    [
        (1250, "12.50"),
        (0, "0.00"),  # zero is an amount, not "no value"
        (-320, "-3.20"),
    ],
)
def test_optional_cents_to_decimal_converts_amounts(cents: int, expected: str):
    assert str(optional_cents_to_decimal(cents)) == expected


def test_optional_cents_to_decimal_keeps_none():
    assert optional_cents_to_decimal(None) is None
