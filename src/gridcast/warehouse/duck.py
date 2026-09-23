"""Connections to the DuckDB warehouse and typed reads of its marts into Polars.

All connections use ``TimeZone = 'UTC'`` so TIMESTAMPTZ columns arrive in Polars as UTC-aware
datetimes. Reads validate against the Pandera contracts in ``gridcast.core.contracts``.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date
from pathlib import Path

import duckdb
import polars as pl

from gridcast.core.contracts import DemandHourly, WeatherHourly


@contextmanager
def connect(path: Path, read_only: bool = True) -> Iterator[duckdb.DuckDBPyConnection]:
    """Open the warehouse (read-only by default, so readers never block ``dbt build``)."""
    if read_only and not path.exists():
        raise FileNotFoundError(f"warehouse {path} does not exist: run `gridcast build` first")
    con = duckdb.connect(str(path), read_only=read_only)
    try:
        con.execute("SET TimeZone = 'UTC'")
        yield con
    finally:
        con.close()


def _where(bas: tuple[str, ...] | None, start: date | None, end: date | None) -> str:
    clauses = ["true"]
    if bas:
        clauses.append("ba_code in (" + ", ".join(f"'{b}'" for b in bas) + ")")
    if start:
        clauses.append(f"hour_ending_utc >= timestamptz '{start.isoformat()} 00:00:00+00'")
    if end:
        clauses.append(f"hour_ending_utc < timestamptz '{end.isoformat()} 00:00:00+00'")
    return " and ".join(clauses)


def read_demand(
    path: Path,
    bas: tuple[str, ...] | None = None,
    start: date | None = None,
    end: date | None = None,
) -> pl.DataFrame:
    """``fct_demand_hourly`` as a validated Polars frame, sorted by (ba_code, hour_ending_utc)."""
    for b in bas or ():
        if not b.isalnum():
            raise ValueError(f"invalid BA code {b!r}")
    sql = f"""
        select ba_code, hour_ending_utc, local_date, hour_number,
               demand_mw, demand_filled_mw, operator_forecast_mw
        from fct_demand_hourly where {_where(bas, start, end)}
        order by ba_code, hour_ending_utc
    """  # noqa: S608 - codes validated above, dates are typed
    with connect(path) as con:
        frame = con.sql(sql).pl()
    return DemandHourly.validate(frame)


def read_weather(
    path: Path,
    bas: tuple[str, ...] | None = None,
    start: date | None = None,
    end: date | None = None,
) -> pl.DataFrame:
    """``fct_weather_forecast_hourly`` as a validated Polars frame."""
    for b in bas or ():
        if not b.isalnum():
            raise ValueError(f"invalid BA code {b!r}")
    sql = f"""
        select ba_code, hour_ending_utc, n_cities, temperature_c, temperature_unweighted_c,
               temperature_spread_c,
               dew_point_c, relative_humidity_pct, cloud_cover_pct, wind_speed_kmh,
               shortwave_radiation_wm2
        from fct_weather_forecast_hourly where {_where(bas, start, end)}
        order by ba_code, hour_ending_utc
    """  # noqa: S608 - codes validated above, dates are typed
    with connect(path) as con:
        frame = con.sql(sql).pl()
    return WeatherHourly.validate(frame)
