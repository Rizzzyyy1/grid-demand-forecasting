"""The ``Forecaster`` protocol every model (and benchmark) implements, plus output helpers.

A forecaster is fitted on feature rows whose target is known, then predicts the target hours of
new feature rows. Output is a ``ForecastBatch`` frame: point forecast ``yhat`` and optional
quantiles (80 % interval ``q10``-``q90``, 95 % interval ``q025``-``q975``).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol, runtime_checkable

import polars as pl

from gridcast.core.contracts import ForecastBatch

QUANTILES: dict[str, float] = {"q025": 0.025, "q10": 0.10, "q90": 0.90, "q975": 0.975}
OUTPUT_KEYS = ("ba_code", "target_day", "hour_ending_utc", "issued_at")


@runtime_checkable
class Forecaster(Protocol):
    """Anything that can be fitted on history and forecast target hours."""

    name: str

    def fit(self, train: pl.DataFrame) -> None:
        """Fit on feature rows with a non-null target column ``y``."""

    def predict(self, frame: pl.DataFrame, *, context: pl.DataFrame | None = None) -> pl.DataFrame:
        """Return ``yhat`` (+ any of ``QUANTILES``) for every row of ``frame``, in order.

        ``context`` holds feature rows for the days just before ``frame`` (between the end of
        training and the forecast month), *including their actuals*. Sequence models may use
        those actuals only up to each row's ``demand_cutoff``; tabular models ignore it.
        """


ForecasterFactory = Callable[[], Forecaster]


def as_batch(frame: pl.DataFrame, predictions: pl.DataFrame, model: str) -> pl.DataFrame:
    """Normalise a model's predictions to the ``ForecastBatch`` contract."""
    if predictions.height != frame.height:
        raise ValueError(f"{model}: {predictions.height} predictions for {frame.height} rows")
    out = frame.select(OUTPUT_KEYS).with_columns(
        pl.lit(model).alias("model"),
        predictions["yhat"].cast(pl.Float64).alias("yhat"),
        *[
            (predictions[q] if q in predictions.columns else pl.lit(None)).cast(pl.Float64).alias(q)
            for q in ("q10", "q90", "q025", "q975")
        ],
    )
    return ForecastBatch.validate(out.select(list(ForecastBatch.to_schema().columns)))
