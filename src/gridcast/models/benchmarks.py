"""Benchmarks implemented as forecasters: the operator's published forecast, raw and debiased.

They need no fitting. The debiased variant (ADR-0005) subtracts the operator's trailing 28-day
mean error at the same local hour, using only target days D-29..D-2, whose actuals were all
published before the 06:00 D-1 demand cutoff.
"""

from __future__ import annotations

import polars as pl

DEBIAS_WINDOW_DAYS = 28
DEBIAS_MIN_DAYS = 14


def operator_debias_offsets(features: pl.DataFrame) -> pl.DataFrame:
    """(ba_code, target_day, local_hour) -> trailing mean operator error from D-29..D-2."""
    daily = (
        features.filter(pl.col("y").is_not_null() & pl.col("operator_forecast_mw").is_not_null())
        .group_by("ba_code", "local_hour", "target_day")
        .agg((pl.col("operator_forecast_mw") - pl.col("y")).mean().alias("err"))
        .sort("ba_code", "local_hour", "target_day")
    )
    window = f"{DEBIAS_WINDOW_DAYS}d"
    rolled = daily.with_columns(
        pl.col("err")
        .rolling_mean_by("target_day", window_size=window, min_samples=DEBIAS_MIN_DAYS)
        .over("ba_code", "local_hour")
        .alias("operator_bias_mw"),
    )
    # the value computed at day t summarises days t-27..t; it is usable for target day t + 2
    return rolled.select(
        "ba_code",
        "local_hour",
        (pl.col("target_day") + pl.duration(days=2)).alias("target_day"),
        "operator_bias_mw",
    )


class OperatorForecast:
    """The BA's own day-ahead forecast as published in EIA-930."""

    name = "operator"

    def fit(self, train: pl.DataFrame) -> None:
        """Nothing to fit."""

    def predict(self, frame: pl.DataFrame, *, context: pl.DataFrame | None = None) -> pl.DataFrame:
        """Return the published forecast (null where the operator published none)."""
        return frame.select(pl.col("operator_forecast_mw").alias("yhat"))


class DebiasedOperatorForecast:
    """Operator forecast minus its trailing same-hour bias (ADR-0005)."""

    name = "operator_debiased"

    def __init__(self, offsets: pl.DataFrame) -> None:
        """``offsets`` from ``operator_debias_offsets`` over the full feature history."""
        self._offsets = offsets

    def fit(self, train: pl.DataFrame) -> None:
        """Nothing to fit: offsets are computed point-in-time already."""

    def predict(self, frame: pl.DataFrame, *, context: pl.DataFrame | None = None) -> pl.DataFrame:
        """Operator forecast minus the bias estimate (raw forecast if no estimate yet)."""
        joined = frame.select("ba_code", "target_day", "local_hour", "operator_forecast_mw").join(
            self._offsets,
            on=["ba_code", "target_day", "local_hour"],
            how="left",
            maintain_order="left",
        )
        return joined.select(
            (pl.col("operator_forecast_mw") - pl.col("operator_bias_mw").fill_null(0.0)).alias(
                "yhat"
            )
        )
