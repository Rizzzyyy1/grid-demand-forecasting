"""Rolling conformalized quantile regression (CQR) on out-of-sample forecasts.

For target day D the calibration set is the model's *own backtest forecasts* for the
``window_days`` days ending at D - ``gap_days`` (all of whose actuals were published before D's
issue time). With conformity score ``s = max(q_lo - y, y - q_hi)``, the interval for D becomes
``[q_lo - c, q_hi + c]`` where ``c`` is the ``ceil((n + 1)(1 - alpha)) / n`` empirical quantile of
the ``n`` calibration scores: wider when the model has recently been over-confident, narrower when
under-confident. Scores are pooled over the hours of a BA (Romano, Patterson & Candes 2019,
applied on a rolling window).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, timedelta

import numpy as np
import polars as pl

INTERVALS = (("q10", "q90", 0.20), ("q025", "q975", 0.05))


@dataclass(frozen=True)
class ConformalResult:
    """Calibrated forecasts plus how many target days had too little history to calibrate."""

    forecasts: pl.DataFrame
    days_calibrated: int
    days_uncalibrated: int


def _conformal_quantile(scores: np.ndarray, alpha: float) -> float:
    n = len(scores)
    k = min(n, math.ceil((n + 1) * (1 - alpha)))
    return float(np.sort(scores)[k - 1])


def conformalize(
    forecasts: pl.DataFrame,
    actuals: pl.DataFrame,
    model: str,
    *,
    window_days: int = 56,
    gap_days: int = 2,
    min_days: int = 21,
) -> ConformalResult:
    """Return ``model``'s forecasts re-labelled ``<model>+cqr`` with calibrated intervals."""
    rows = forecasts.filter(pl.col("model") == model)
    if rows.is_empty():
        raise ValueError(f"no forecasts for model {model!r}")
    scored = rows.join(
        actuals.select("ba_code", "hour_ending_utc", "y"),
        on=["ba_code", "hour_ending_utc"],
        how="inner",
    ).filter(pl.col("y").is_not_null())
    score_cols = {
        lo: pl.max_horizontal(pl.col(lo) - pl.col("y"), pl.col("y") - pl.col(hi))
        for lo, hi, _ in INTERVALS
    }
    daily = (
        scored.with_columns([expr.alias(f"s_{lo}") for lo, expr in score_cols.items()])
        .group_by("ba_code", "target_day")
        .agg([pl.col(f"s_{lo}").drop_nulls() for lo, _, _ in INTERVALS])
    )
    by_ba: dict[str, dict[date, dict[str, np.ndarray]]] = {}
    for r in daily.iter_rows(named=True):
        by_ba.setdefault(r["ba_code"], {})[r["target_day"]] = {
            lo: np.asarray(r[f"s_{lo}"], dtype=float) for lo, _, _ in INTERVALS
        }
    adj_rows: list[dict[str, object]] = []
    calibrated = uncalibrated = 0
    for (ba, day), _ in rows.group_by("ba_code", "target_day"):
        history = by_ba.get(str(ba), {})
        last = day - timedelta(days=gap_days)
        window = [last - timedelta(days=i) for i in range(window_days)]
        present = [d for d in window if d in history]
        entry: dict[str, object] = {"ba_code": ba, "target_day": day}
        if len(present) >= min_days:
            for lo, _, alpha in INTERVALS:
                scores = np.concatenate([history[d][lo] for d in present])
                entry[f"c_{lo}"] = _conformal_quantile(scores, alpha) if scores.size else None
            calibrated += 1
        else:
            for lo, _, _ in INTERVALS:
                entry[f"c_{lo}"] = None
            uncalibrated += 1
        adj_rows.append(entry)
    adjust = pl.DataFrame(
        adj_rows,
        schema={
            "ba_code": pl.String,
            "target_day": pl.Date,
            "c_q10": pl.Float64,
            "c_q025": pl.Float64,
        },
    )
    out = rows.join(adjust, on=["ba_code", "target_day"], how="left", maintain_order="left")
    for lo, hi, _ in INTERVALS:
        c = pl.col(f"c_{lo}").fill_null(0.0)
        out = out.with_columns((pl.col(lo) - c).alias(lo), (pl.col(hi) + c).alias(hi))
    out = out.with_columns(
        # keep the 95 % interval at least as wide as the 80 % one after adjustment
        pl.min_horizontal("q025", "q10").alias("q025"),
        pl.max_horizontal("q975", "q90").alias("q975"),
        pl.lit(f"{model}+cqr").alias("model"),
    ).drop("c_q10", "c_q025")
    return ConformalResult(out, calibrated, uncalibrated)
