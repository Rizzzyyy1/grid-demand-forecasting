"""Uncertainty for forecast comparisons: moving-block bootstrap over days and Diebold-Mariano.

Hourly errors within a day (and across neighbouring days) are strongly correlated, so both
procedures work on *daily* loss series: resampling or testing individual hours would overstate
confidence (DESIGN section 4).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import polars as pl
from numpy.typing import NDArray


@dataclass(frozen=True)
class Interval:
    """A point estimate with a percentile bootstrap confidence interval."""

    estimate: float
    low: float
    high: float
    n_days: int


def daily_losses(scored: pl.DataFrame, model: str, ba: str) -> pl.DataFrame:
    """Per target day: sum of absolute errors, sum of actuals and hours, for one model and BA."""
    return (
        scored.filter((pl.col("model") == model) & (pl.col("ba_code") == ba))
        .group_by("target_day")
        .agg(
            pl.col("abs_err").sum().alias("abs_err_sum"),
            (pl.col("abs_err") / pl.col("y")).sum().alias("ape_sum"),
            pl.len().alias("hours"),
        )
        .sort("target_day")
    )


def block_indices(n: int, block: int, rng: np.random.Generator) -> NDArray[np.int64]:
    """Indices of one moving-block bootstrap resample of length ``n``."""
    if n <= 0:
        raise ValueError("need at least one observation")
    block = max(1, min(block, n))
    n_blocks = math.ceil(n / block)
    starts = rng.integers(0, n - block + 1, size=n_blocks)
    idx = (starts[:, None] + np.arange(block)[None, :]).ravel()[:n]
    return idx.astype(np.int64)


def bootstrap_ratio(
    numerator: NDArray[np.float64],
    denominator: NDArray[np.float64],
    *,
    n_boot: int = 1000,
    block: int = 7,
    level: float = 0.95,
    seed: int = 0,
) -> Interval:
    """CI for ``sum(numerator) / sum(denominator)`` (e.g. MAE = sum|e| / hours) over days."""
    rng = np.random.default_rng(seed)
    n = len(numerator)
    stats = np.empty(n_boot)
    for b in range(n_boot):
        idx = block_indices(n, block, rng)
        stats[b] = numerator[idx].sum() / denominator[idx].sum()
    alpha = (1 - level) / 2
    return Interval(
        estimate=float(numerator.sum() / denominator.sum()),
        low=float(np.quantile(stats, alpha)),
        high=float(np.quantile(stats, 1 - alpha)),
        n_days=n,
    )


def bootstrap_skill(
    model_abs: NDArray[np.float64],
    ref_abs: NDArray[np.float64],
    *,
    n_boot: int = 1000,
    block: int = 7,
    level: float = 0.95,
    seed: int = 0,
) -> Interval:
    """CI for skill = 1 - MAE_model / MAE_ref from paired daily absolute-error sums."""
    rng = np.random.default_rng(seed)
    n = len(model_abs)
    stats = np.empty(n_boot)
    for b in range(n_boot):
        idx = block_indices(n, block, rng)
        stats[b] = 1 - model_abs[idx].sum() / ref_abs[idx].sum()
    alpha = (1 - level) / 2
    return Interval(
        estimate=float(1 - model_abs.sum() / ref_abs.sum()),
        low=float(np.quantile(stats, alpha)),
        high=float(np.quantile(stats, 1 - alpha)),
        n_days=n,
    )


@dataclass(frozen=True)
class DMResult:
    """Diebold-Mariano test of equal accuracy (with the Harvey-Leybourne-Newbold correction)."""

    statistic: float
    p_value: float
    mean_diff: float
    n: int


def diebold_mariano(
    loss_a: NDArray[np.float64], loss_b: NDArray[np.float64], lag: int = 7
) -> DMResult:
    """Two-sided DM test on paired loss series (negative statistic: ``a`` more accurate).

    The long-run variance uses a Bartlett (Newey-West) kernel with ``lag`` autocovariances.
    """
    d = np.asarray(loss_a, dtype=float) - np.asarray(loss_b, dtype=float)
    n = len(d)
    if n < 10:
        raise ValueError(f"need at least 10 paired observations, got {n}")
    mean = d.mean()
    centred = d - mean
    lrv = centred @ centred / n
    for k in range(1, min(lag, n - 1) + 1):
        weight = 1 - k / (lag + 1)
        lrv += 2 * weight * (centred[k:] @ centred[:-k]) / n
    if lrv <= 0:
        return DMResult(statistic=0.0, p_value=1.0, mean_diff=float(mean), n=n)
    stat = mean / math.sqrt(lrv / n)
    h = lag + 1
    correction = math.sqrt((n + 1 - 2 * h + h * (h - 1) / n) / n)
    stat *= correction
    p_value = math.erfc(abs(stat) / math.sqrt(2))  # normal approximation, two-sided
    return DMResult(statistic=float(stat), p_value=float(p_value), mean_diff=float(mean), n=n)
