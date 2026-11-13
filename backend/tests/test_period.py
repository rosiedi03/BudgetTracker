"""Year/month request parameters and the date ranges built from them."""

import datetime

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from budgettracker.reports import month_date_range, year_to_date_range
from budgettracker.schemas.period import Month, Year


@pytest.fixture
def probe_client() -> TestClient:
    """A small app with one endpoint that takes year and month the way report endpoints will."""
    probe = FastAPI()

    @probe.get("/period")
    def period(year: Year, month: Month) -> dict[str, int]:
        return {"year": year, "month": month}

    return TestClient(probe)


# Parameters: accepted


@pytest.mark.parametrize(
    ("year", "month"),
    [
        (2026, 11),
        (2000, 1),  # lowest allowed
        (2100, 12),  # highest allowed
    ],
)
def test_valid_year_and_month_are_accepted(probe_client: TestClient, year: int, month: int):
    response = probe_client.get("/period", params={"year": year, "month": month})
    assert response.status_code == 200
    assert response.json() == {"year": year, "month": month}


# Parameters: rejected


@pytest.mark.parametrize(
    "params",
    [
        pytest.param({"year": 1999, "month": 11}, id="year-too-low"),
        pytest.param({"year": 2101, "month": 11}, id="year-too-high"),
        pytest.param({"year": 2026, "month": 0}, id="month-too-low"),
        pytest.param({"year": 2026, "month": 13}, id="month-too-high"),
        pytest.param({"year": "abc", "month": 11}, id="year-not-a-number"),
        pytest.param({"year": 2026, "month": 1.5}, id="month-not-an-integer"),
        pytest.param({"month": 11}, id="year-missing"),
        pytest.param({"year": 2026}, id="month-missing"),
        pytest.param({}, id="both-missing"),
    ],
)
def test_invalid_or_missing_year_or_month_returns_422(probe_client: TestClient, params: dict):
    response = probe_client.get("/period", params=params)
    assert response.status_code == 422


# Month range


@pytest.mark.parametrize(
    ("year", "month", "expected"),
    [
        (2026, 11, (datetime.date(2026, 11, 1), datetime.date(2026, 12, 1))),
        (2026, 12, (datetime.date(2026, 12, 1), datetime.date(2027, 1, 1))),  # rolls into Jan
        (2026, 1, (datetime.date(2026, 1, 1), datetime.date(2026, 2, 1))),
        (2028, 2, (datetime.date(2028, 2, 1), datetime.date(2028, 3, 1))),  # leap year
    ],
)
def test_month_date_range(year: int, month: int, expected: tuple[datetime.date, datetime.date]):
    assert month_date_range(year, month) == expected


# Year-to-date range


@pytest.mark.parametrize(
    ("year", "month", "expected"),
    [
        (2026, 11, (datetime.date(2026, 1, 1), datetime.date(2026, 12, 1))),
        (2026, 1, (datetime.date(2026, 1, 1), datetime.date(2026, 2, 1))),  # just January
        (2026, 12, (datetime.date(2026, 1, 1), datetime.date(2027, 1, 1))),  # whole year
    ],
)
def test_year_to_date_range(year: int, month: int, expected: tuple[datetime.date, datetime.date]):
    assert year_to_date_range(year, month) == expected
