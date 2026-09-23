"""Named model factories for experiments (the model ladder of ADR-0003)."""

from __future__ import annotations

from collections.abc import Callable

import polars as pl

from gridcast.models.base import Forecaster
from gridcast.models.baselines import RidgeForecaster, SeasonalNaive
from gridcast.models.benchmarks import (
    DebiasedOperatorForecast,
    OperatorForecast,
    operator_debias_offsets,
)
from gridcast.models.gbm import LightGBMForecaster

BENCHMARKS = ("operator", "operator_debiased")
LADDER = ("seasonal_naive", "ridge", "lgbm_global")


def _nhits() -> Forecaster:
    from gridcast.models.nhits import NHiTSForecaster  # noqa: PLC0415 - deep extra (PyTorch)

    return NHiTSForecaster()


def factories(
    names: tuple[str, ...], features: pl.DataFrame
) -> dict[str, Callable[[], Forecaster]]:
    """Build a factory per requested model name."""
    offsets = operator_debias_offsets(features) if "operator_debiased" in names else None
    table: dict[str, Callable[[], Forecaster]] = {
        "operator": OperatorForecast,
        "seasonal_naive": SeasonalNaive,
        "ridge": RidgeForecaster,
        "lgbm_global": LightGBMForecaster,
        "lgbm_per_ba": lambda: LightGBMForecaster(per_ba=True),
        "nhits": _nhits,
    }
    if offsets is not None:
        table["operator_debiased"] = lambda: DebiasedOperatorForecast(offsets)
    unknown = set(names) - set(table)
    if unknown:
        raise KeyError(f"unknown models {sorted(unknown)}; known: {sorted(table)}")
    return {n: table[n] for n in names}
