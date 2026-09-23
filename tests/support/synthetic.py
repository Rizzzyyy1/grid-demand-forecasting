"""Synthetic demand and weather frames with the mart schemas, built with GridCast's own clock rules."""

from __future__ import annotations

import math
from datetime import UTC, date, datetime, timedelta

import numpy as np
import polars as pl

from gridcast.core import time as t
from gridcast.core.regions import get_region

UTC_US = pl.Datetime("us", "UTC")


def make_demand(bas: tuple[str, ...], start: date, days: int, seed: int = 0) -> pl.DataFrame:
    """Hourly demand with daily/weekly shape and noise; operator forecast = demand * 1.02."""
    rng = np.random.default_rng(seed)
    rows = []
    for code in bas:
        tz = get_region(code).tz
        base = 20_000 + 5_000 * (len(code) + ord(code[0]) % 7)
        for i in range(days):
            day = start + timedelta(days=i)
            for n, instant in enumerate(t.hour_ending_instants(day, tz), start=1):
                hour = t.to_local(instant - t.ONE_HOUR, tz).hour
                weekly = 0.9 if day.weekday() >= 5 else 1.0
                value = base * weekly * (1 + 0.2 * math.sin((hour - 6) / 24 * 2 * math.pi))
                value *= 1 + 0.02 * rng.standard_normal()
                rows.append((code, instant, day, n, value, value, value * 1.02))
    return pl.DataFrame(
        rows,
        schema={
            "ba_code": pl.String,
            "hour_ending_utc": UTC_US,
            "local_date": pl.Date,
            "hour_number": pl.Int32,
            "demand_mw": pl.Float64,
            "demand_filled_mw": pl.Float64,
            "operator_forecast_mw": pl.Float64,
        },
        orient="row",
    )


def make_weather(bas: tuple[str, ...], start: date, days: int, seed: int = 1) -> pl.DataFrame:
    """Hourly forecast temperature on a continuous UTC grid covering the demand range."""
    rng = np.random.default_rng(seed)
    first = datetime(start.year, start.month, start.day, tzinfo=UTC) - timedelta(days=2)
    n = (days + 4) * 24
    rows = []
    for code in bas:
        for h in range(n):
            instant = first + timedelta(hours=h)
            temp = 15 + 10 * math.sin(h / 24 * 2 * math.pi) + rng.standard_normal()
            rows.append((code, instant, 4, temp, temp + 0.5, 3.0))
    return pl.DataFrame(
        rows,
        schema={
            "ba_code": pl.String,
            "hour_ending_utc": UTC_US,
            "n_cities": pl.Int64,
            "temperature_c": pl.Float64,
            "temperature_unweighted_c": pl.Float64,
            "temperature_spread_c": pl.Float64,
        },
        orient="row",
    )
