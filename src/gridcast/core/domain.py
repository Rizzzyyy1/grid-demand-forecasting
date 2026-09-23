"""Frozen domain models shared by every GridCast package.

These are the value objects that cross package boundaries: balancing authorities, the cities used
for their weather, and the forecasting protocol's per-forecast timestamps. Bulk data (hours x
regions) travels as Polars frames validated by Pandera contracts, not as these models.
"""

from __future__ import annotations

import re
from datetime import date, datetime, time, timedelta
from functools import cached_property
from typing import Annotated
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from gridcast.core import time as t

BACode = Annotated[str, Field(pattern=r"^[A-Z]{2,5}$")]


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


def slugify(name: str) -> str:
    """File-system-safe lower-case name (``St. Louis`` -> ``st-louis``)."""
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


class City(_Frozen):
    """A population centre whose weather stands in for part of a BA's load."""

    name: str
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    population: int = Field(gt=0, description="Metropolitan-area population used as a weight")

    @property
    def slug(self) -> str:
        """Identifier used in raw-file paths and the ``cities`` seed."""
        return slugify(self.name)


class BalancingAuthority(_Frozen):
    """A balancing authority as used by GridCast (EIA-930 code, clock, weather cities)."""

    code: BACode
    name: str
    timezone: str = Field(description="IANA zone of the BA's EIA-930 reporting clock")
    cities: tuple[City, ...] = Field(min_length=1)
    notes: str = ""

    @field_validator("timezone")
    @classmethod
    def _known_zone(cls, value: str) -> str:
        ZoneInfo(value)  # raises ZoneInfoNotFoundError for typos
        return value

    @cached_property
    def tz(self) -> ZoneInfo:
        """The BA's clock as a ``ZoneInfo``."""
        return t.zone(self.timezone)

    def population_weights(self) -> dict[str, float]:
        """City name -> weight (population share), summing to 1."""
        total = sum(c.population for c in self.cities)
        return {c.name: c.population / total for c in self.cities}


class ProtocolConfig(_Frozen):
    """The leakage-free forecasting protocol (DESIGN section 3, ADR-0001, ADR-0007).

    Forecasts for local day D are issued at ``issue_time`` on D-1 and may use demand for hours
    ending at or before ``demand_cutoff_time`` on day D - ``demand_cutoff_days_before``.
    The default ("realtime", 06:00 on D-1) assumes an hourly feed such as the EIA API; ``bulk()``
    matches EIA's keyless daily bulk file (data through the end of D-3).
    """

    name: str = "realtime"
    issue_time: time = time(10, 0)
    demand_cutoff_time: time = time(6, 0)
    demand_cutoff_days_before: int = Field(default=1, ge=1)
    weather_lead_days: int = Field(default=2, ge=2, description="Open-Meteo previous_dayN")

    @model_validator(mode="after")
    def _cutoff_before_issue(self) -> ProtocolConfig:
        if self.demand_cutoff_days_before == 1 and self.demand_cutoff_time > self.issue_time:
            raise ValueError("demand cutoff must not be after the issue time")
        return self

    @classmethod
    def bulk(cls) -> ProtocolConfig:
        """Protocol a keyless live loop can honour (EIA bulk file, updated ~14:40 UTC daily)."""
        return cls(name="bulk", demand_cutoff_time=time(0, 0), demand_cutoff_days_before=2)

    @property
    def recent_day_offset(self) -> int:
        """Days back to the most recent *complete* local day usable at issue time."""
        return self.demand_cutoff_days_before + 1

    @property
    def publication_lag(self) -> timedelta:
        """Issue instant minus cutoff instant on a day without a DST change."""
        anchor = date(2000, 1, 3)
        issued = datetime.combine(anchor, self.issue_time)
        cutoff = datetime.combine(
            anchor - timedelta(days=self.demand_cutoff_days_before - 1), self.demand_cutoff_time
        )
        return issued - cutoff


class ForecastOrigin(_Frozen):
    """When a forecast for ``target_day`` in ``ba`` is issued and what it may see."""

    ba: BACode
    target_day: date
    issued_at: datetime
    demand_cutoff: datetime

    @field_validator("issued_at", "demand_cutoff")
    @classmethod
    def _aware(cls, value: datetime) -> datetime:
        return t.to_utc(value)

    @classmethod
    def for_day(
        cls, ba: BalancingAuthority, target_day: date, protocol: ProtocolConfig
    ) -> ForecastOrigin:
        """Origin for forecasting local ``target_day`` from 10:00 local on the day before."""
        issue_day = target_day - timedelta(days=1)
        cutoff_day = target_day - timedelta(days=protocol.demand_cutoff_days_before)
        return cls(
            ba=ba.code,
            target_day=target_day,
            issued_at=t.local_wall_time(issue_day, protocol.issue_time, ba.tz),
            demand_cutoff=t.local_wall_time(cutoff_day, protocol.demand_cutoff_time, ba.tz),
        )
