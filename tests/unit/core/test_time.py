from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from itertools import pairwise

import pytest
from hypothesis import given
from hypothesis import strategies as st

from gridcast.core import time as t
from gridcast.core.regions import all_regions

ZONES = sorted({ba.timezone for ba in all_regions()})
days = st.dates(min_value=date(2015, 1, 1), max_value=date(2035, 12, 31))
zones = st.sampled_from(ZONES)


def test_spring_forward_and_fall_back_lengths() -> None:
    ny = t.zone("America/New_York")
    assert t.hours_in_local_day(date(2025, 3, 9), ny) == 23
    assert t.hours_in_local_day(date(2025, 11, 2), ny) == 25
    assert t.hours_in_local_day(date(2025, 7, 1), ny) == 24


def test_miso_fixed_est_has_no_dst() -> None:
    est = t.zone("Etc/GMT+5")
    assert t.hours_in_local_day(date(2025, 3, 9), est) == 24
    assert t.hours_in_local_day(date(2025, 11, 2), est) == 24


def test_matches_eia_rows_observed_2025_03_09() -> None:
    # PJM 2025-03-09 hour 2 ended at 03:00 EDT = 07:00 UTC (hour 02:00 local does not exist).
    ny = t.zone("America/New_York")
    instants = t.hour_ending_instants(date(2025, 3, 9), ny)
    assert instants[1] == datetime(2025, 3, 9, 7, tzinfo=UTC)
    # MISO hour 23 on the same day ended at 04:00 UTC the next day.
    est = t.zone("Etc/GMT+5")
    assert t.hour_ending_instants(date(2025, 3, 9), est)[22] == datetime(2025, 3, 10, 4, tzinfo=UTC)


def test_parse_eia_utc() -> None:
    assert t.parse_eia_utc("01/16/2025 4:00:00 AM") == datetime(2025, 1, 16, 4, tzinfo=UTC)
    assert t.parse_eia_utc("01/16/2025 12:00:00 PM") == datetime(2025, 1, 16, 12, tzinfo=UTC)


def test_naive_datetimes_are_rejected() -> None:
    with pytest.raises(t.NaiveDatetimeError):
        t.to_utc(datetime(2025, 1, 1))


def test_nonexistent_wall_time_raises() -> None:
    with pytest.raises(ValueError, match=r"does not exist|ambiguous"):
        t.local_wall_time(date(2025, 3, 9), time(2, 30), t.zone("America/New_York"))


@given(day=days, tz_name=zones)
def test_hours_partition_the_day(day: date, tz_name: str) -> None:
    tz = t.zone(tz_name)
    instants = t.hour_ending_instants(day, tz)
    assert len(instants) in (23, 24, 25)
    assert all(b - a == timedelta(hours=1) for a, b in pairwise(instants))
    assert instants[-1] == t.local_midnight(day + timedelta(days=1), tz)
    # consecutive days tile the timeline with no gap or overlap
    assert t.hour_ending_instants(day + timedelta(days=1), tz)[0] == instants[-1] + t.ONE_HOUR


@given(day=days, tz_name=zones)
def test_round_trip_day_and_hour_number(day: date, tz_name: str) -> None:
    tz = t.zone(tz_name)
    for number, instant in enumerate(t.hour_ending_instants(day, tz), start=1):
        assert t.local_day_of(instant, tz) == day
        assert t.local_hour_number(instant, tz) == number


@given(day=days, tz_name=zones)
def test_issue_time_is_before_every_target_hour(day: date, tz_name: str) -> None:
    tz = t.zone(tz_name)
    issued = t.local_wall_time(day - timedelta(days=1), time(10), tz)
    first_hour_start = t.hour_ending_instants(day, tz)[0] - t.ONE_HOUR
    lead = first_hour_start - issued
    assert timedelta(hours=13) <= lead <= timedelta(hours=15)
