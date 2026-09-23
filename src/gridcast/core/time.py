"""All time-zone and daylight-saving handling for GridCast.

Every conversion between UTC instants and a balancing authority's local clock goes through this
module (DESIGN section 8). Conventions, verified against EIA-930 on 2026-09-23:

* Instants are timezone-aware UTC ``datetime`` values; naive datetimes are rejected.
* EIA-930 hours are labelled by their **end** ("hour ending"): the value stamped 01:00 local
  covers 00:00-01:00. A local day therefore consists of the hours whose *end* lies in
  ``(local midnight D, local midnight D+1]`` - 24 hours normally, 23 on spring-forward days and
  25 on fall-back days.
* Each BA's clock is an IANA zone. Nine of our ten BAs report in prevailing (DST-observing) time;
  MISO reports in Eastern *Standard* Time all year, modelled as the fixed zone ``Etc/GMT+5``.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

ONE_HOUR = timedelta(hours=1)
EIA_TIMESTAMP_FORMAT = "%m/%d/%Y %I:%M:%S %p"


class NaiveDatetimeError(ValueError):
    """Raised when a timezone-naive datetime reaches code that needs an instant."""


def _require_aware(value: datetime, name: str = "datetime") -> None:
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        raise NaiveDatetimeError(f"{name} must be timezone-aware, got naive {value!r}")


def zone(name: str) -> ZoneInfo:
    """Return the IANA zone ``name`` (cached by ``zoneinfo`` itself)."""
    return ZoneInfo(name)


def to_utc(value: datetime) -> datetime:
    """Convert an aware datetime to UTC."""
    _require_aware(value)
    return value.astimezone(UTC)


def to_local(value: datetime, tz: ZoneInfo) -> datetime:
    """Convert an aware datetime to the wall clock of ``tz``."""
    _require_aware(value)
    return value.astimezone(tz)


def local_wall_time(day: date, at: time, tz: ZoneInfo) -> datetime:
    """The UTC instant at which the wall clock of ``tz`` shows ``at`` on ``day``.

    Only used for times that exist exactly once on every day in US zones (DST transitions happen
    at 02:00, so 00:00, 06:00 and 10:00 are always unambiguous). Ambiguous or non-existent wall
    times raise, so a future change of issue time cannot silently shift by an hour.
    """
    naive = datetime.combine(day, at)
    first = naive.replace(tzinfo=tz, fold=0)
    second = naive.replace(tzinfo=tz, fold=1)
    if first.utcoffset() != second.utcoffset():
        raise ValueError(f"{at} on {day} is ambiguous or non-existent in {tz.key}")
    # A non-existent wall time round-trips to a different wall time.
    if first.astimezone(UTC).astimezone(tz).replace(tzinfo=None) != naive:
        raise ValueError(f"{at} on {day} does not exist in {tz.key}")
    return first.astimezone(UTC)


def local_midnight(day: date, tz: ZoneInfo) -> datetime:
    """UTC instant of 00:00 local on ``day``."""
    return local_wall_time(day, time(0), tz)


def hours_in_local_day(day: date, tz: ZoneInfo) -> int:
    """Number of hours in local ``day``: 24, or 23 / 25 on DST-change days."""
    span = local_midnight(day + timedelta(days=1), tz) - local_midnight(day, tz)
    return int(span / ONE_HOUR)


def hour_ending_instants(day: date, tz: ZoneInfo) -> list[datetime]:
    """UTC hour-ending instants of every hour of local ``day``, in order (23, 24 or 25 items)."""
    start = local_midnight(day, tz)
    return [start + ONE_HOUR * (i + 1) for i in range(hours_in_local_day(day, tz))]


def local_day_of(hour_ending: datetime, tz: ZoneInfo) -> date:
    """The local day an hour-ending instant belongs to (hour ending 00:00 is the day before's)."""
    return to_local(hour_ending - ONE_HOUR, tz).date()


def local_hour_number(hour_ending: datetime, tz: ZoneInfo) -> int:
    """EIA-style hour number (1-based position of the hour within its local day)."""
    day = local_day_of(hour_ending, tz)
    return int((to_utc(hour_ending) - local_midnight(day, tz)) / ONE_HOUR)


def parse_eia_utc(text: str) -> datetime:
    """Parse an EIA-930 ``UTC Time at End of Hour`` string (e.g. ``01/16/2025 4:00:00 AM``)."""
    return datetime.strptime(text.strip(), EIA_TIMESTAMP_FORMAT).replace(tzinfo=UTC)


def utc_now() -> datetime:
    """The current instant (the single place wall-clock time enters the code base)."""
    return datetime.now(UTC)


def floor_hour(value: datetime) -> datetime:
    """Truncate an aware datetime to the start of its UTC hour."""
    return to_utc(value).replace(minute=0, second=0, microsecond=0)
