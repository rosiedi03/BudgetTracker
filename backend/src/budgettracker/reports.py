"""Report calculations. Plain functions, kept separate from the routers so they're easy to test."""

import datetime


def month_date_range(year: int, month: int) -> tuple[datetime.date, datetime.date]:
    """(first day of the month, first day of the next month).

    Use as start <= date < end, so the last day of the month is included without needing to know
    how many days the month has.
    """
    return datetime.date(year, month, 1), _first_day_of_next_month(year, month)


def year_to_date_range(year: int, month: int) -> tuple[datetime.date, datetime.date]:
    """(January 1, first day of the month after `month`), used the same way as month_date_range."""
    return datetime.date(year, 1, 1), _first_day_of_next_month(year, month)


def _first_day_of_next_month(year: int, month: int) -> datetime.date:
    # December is the only month whose next month is in the following year.
    if month == 12:
        return datetime.date(year + 1, 1, 1)
    return datetime.date(year, month + 1, 1)
