"""Pandera data contracts for the frames that cross package boundaries.

dbt tests guard the warehouse; these guard the Python side (a mart read, a feature matrix, a
forecast batch), so a schema change fails loudly at the boundary instead of deep inside a model.
"""

from __future__ import annotations

import pandera.polars as pa
import polars as pl
from pandera.engines.polars_engine import DateTime as UtcDatetime

_UTC = {"time_unit": "us", "time_zone": "UTC"}


class DemandHourly(pa.DataFrameModel):
    """Rows of ``fct_demand_hourly``."""

    ba_code: str
    hour_ending_utc: UtcDatetime = pa.Field(dtype_kwargs=_UTC)
    local_date: pl.Date
    hour_number: pl.Int32 = pa.Field(ge=1, le=25)
    demand_mw: pl.Float64 = pa.Field(nullable=True, ge=0)
    demand_filled_mw: pl.Float64 = pa.Field(nullable=True, ge=0)
    operator_forecast_mw: pl.Float64 = pa.Field(nullable=True, ge=0)

    class Config:
        """Reject unexpected columns and duplicated keys."""

        strict = True
        unique = ["ba_code", "hour_ending_utc"]  # noqa: RUF012 - pandera config idiom


class WeatherHourly(pa.DataFrameModel):
    """Rows of ``fct_weather_forecast_hourly``."""

    ba_code: str
    hour_ending_utc: UtcDatetime = pa.Field(dtype_kwargs=_UTC)
    n_cities: pl.Int64 = pa.Field(ge=0, le=6)
    temperature_c: pl.Float64 = pa.Field(nullable=True, ge=-60, le=60)
    temperature_unweighted_c: pl.Float64 = pa.Field(nullable=True, ge=-60, le=60)
    temperature_spread_c: pl.Float64 = pa.Field(nullable=True, ge=0)
    dew_point_c: pl.Float64 = pa.Field(nullable=True)
    relative_humidity_pct: pl.Float64 = pa.Field(nullable=True, ge=0, le=100)
    cloud_cover_pct: pl.Float64 = pa.Field(nullable=True, ge=0, le=100)
    wind_speed_kmh: pl.Float64 = pa.Field(nullable=True, ge=0)
    shortwave_radiation_wm2: pl.Float64 = pa.Field(nullable=True, ge=0)

    class Config:
        """Reject unexpected columns and duplicated keys."""

        strict = True
        unique = ["ba_code", "hour_ending_utc"]  # noqa: RUF012 - pandera config idiom


class ForecastBatch(pa.DataFrameModel):
    """Forecasts produced by any ``Forecaster``: one row per (BA, target hour, model)."""

    ba_code: str
    target_day: pl.Date
    hour_ending_utc: UtcDatetime = pa.Field(dtype_kwargs=_UTC)
    issued_at: UtcDatetime = pa.Field(dtype_kwargs=_UTC)
    model: str
    yhat: pl.Float64 = pa.Field(nullable=True)  # null = model abstains (e.g. missing lag)
    q10: pl.Float64 = pa.Field(nullable=True)
    q90: pl.Float64 = pa.Field(nullable=True)
    q025: pl.Float64 = pa.Field(nullable=True)
    q975: pl.Float64 = pa.Field(nullable=True)

    class Config:
        """One forecast per key; issue strictly before the hour it forecasts."""

        strict = True
        unique = ["ba_code", "hour_ending_utc", "model", "issued_at"]  # noqa: RUF012

    @pa.dataframe_check
    @classmethod
    def issued_before_target(cls, data: pa.PolarsData) -> pl.LazyFrame:
        """Every forecast is issued before its hour starts."""
        return data.lazyframe.select(
            (pl.col("issued_at") < pl.col("hour_ending_utc") - pl.duration(hours=1)).alias("ok")
        )
