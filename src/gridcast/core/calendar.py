"""Calendar facts known in advance: US federal holidays and day types.

Used for features (always ``available_at`` = -infinity: the calendar is known years ahead) and for
evaluation slices (weekday / weekend / holiday).
"""

from __future__ import annotations

from datetime import date
from functools import cache

import holidays


@cache
def _us_holidays(year: int) -> dict[date, str]:
    return dict(holidays.country_holidays("US", years=year, observed=True))


def is_holiday(day: date) -> bool:
    """True if ``day`` is a US federal holiday (observed date)."""
    return day in _us_holidays(day.year)


def holiday_name(day: date) -> str | None:
    """Name of the federal holiday on ``day``, if any."""
    return _us_holidays(day.year).get(day)


def day_type(day: date) -> str:
    """``holiday``, ``weekend`` or ``weekday`` - holidays take precedence."""
    if is_holiday(day):
        return "holiday"
    return "weekend" if day.weekday() >= 5 else "weekday"


def holiday_dates(first_year: int, last_year: int) -> list[date]:
    """Every federal holiday (observed) between two years inclusive, sorted."""
    days: list[date] = []
    for year in range(first_year, last_year + 1):
        days.extend(_us_holidays(year))
    return sorted(days)
