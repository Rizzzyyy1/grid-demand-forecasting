"""Response models for the public API (versioned under ``/v1``)."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class _Out(BaseModel):
    model_config = ConfigDict(frozen=True)


class Region(_Out):
    """A balancing authority."""

    code: str
    name: str
    timezone: str
    cities: list[str]


class ForecastPoint(_Out):
    """One forecast hour."""

    hour_ending_utc: datetime
    yhat: float | None
    q10: float | None
    q90: float | None
    q025: float | None
    q975: float | None


class ForecastResponse(_Out):
    """The latest stored forecast for a BA and target day."""

    ba_code: str
    target_day: date
    model: str
    model_version: str
    issued_at: datetime
    created_at: datetime
    late: bool
    protocol: str
    hours: list[ForecastPoint]


class LeaderboardRow(_Out):
    """Live accuracy of one model in one BA (live forecasts only, never backtests)."""

    ba_code: str
    model: str
    days: int
    hours: int
    mape: float
    mae: float
    late_hours: int


class RunSummary(_Out):
    """A backtest run on disk."""

    run_id: str
    split: str
    window: list[str]
    models: list[str]
    refits: int
    superseded: str | None = None


class Health(_Out):
    """Liveness / readiness."""

    status: str
    warehouse: bool
    store_rows: int | None = None
    version: str
