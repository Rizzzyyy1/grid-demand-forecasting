from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import numpy as np
import polars as pl
import pytest

from gridcast.evaluation.metrics import interval_metrics, peak_metrics, point_metrics, score, skill
from gridcast.evaluation.stats import (
    block_indices,
    bootstrap_ratio,
    bootstrap_skill,
    diebold_mariano,
)


def _frame() -> tuple[pl.DataFrame, pl.DataFrame]:
    hours = [datetime(2025, 1, 1, tzinfo=UTC) + timedelta(hours=h) for h in range(1, 25)]
    y = [100.0 + h for h in range(24)]
    actuals = pl.DataFrame({"ba_code": "X", "hour_ending_utc": hours, "y": y})
    fc = pl.DataFrame(
        {
            "ba_code": "X",
            "target_day": date(2025, 1, 1),
            "hour_ending_utc": hours * 2,
            "model": ["a"] * 24 + ["b"] * 24,
            "yhat": [v + 10 for v in y] + [v - 5 for v in y],
            "q10": [v - 1 for v in y] * 2,
            "q90": [v + 1 for v in y] * 2,
            "q025": [v - 2 for v in y] * 2,
            "q975": [v + 2 for v in y] * 2,
        }
    )
    return fc, actuals


def test_point_metrics_and_skill() -> None:
    fc, actuals = _frame()
    scored = score(fc, actuals)
    pm = point_metrics(scored)
    a = pm.filter(pl.col("model") == "a").row(0, named=True)
    assert a["hours"] == 24 and a["mae"] == pytest.approx(10) and a["rmse"] == pytest.approx(10)
    assert a["bias_pct"] > 0
    sk = skill(pm, "a").filter(pl.col("model") == "b")["skill_vs_a"].item()
    assert sk == pytest.approx(0.5)


def test_peak_and_interval_metrics() -> None:
    fc, actuals = _frame()
    scored = score(fc, actuals)
    peaks = peak_metrics(scored).filter(pl.col("model") == "b").row(0, named=True)
    assert peaks["days"] == 1 and peaks["peak_ape"] == pytest.approx(500 / 123)
    assert peaks["peak_hour_miss_pct"] == 0
    iv = interval_metrics(scored).filter(pl.col("model") == "a").row(0, named=True)
    assert iv["coverage_80"] == 100 and iv["coverage_95"] == 100


def test_unscorable_hours_are_dropped() -> None:
    fc, actuals = _frame()
    actuals = actuals.with_columns(
        pl.when(pl.col("y") < 105).then(None).otherwise(pl.col("y")).alias("y")
    )
    assert score(fc, actuals).height == 2 * 19


def test_block_indices_are_contiguous_blocks() -> None:
    rng = np.random.default_rng(0)
    idx = block_indices(30, 7, rng)
    assert len(idx) == 30 and idx.min() >= 0 and idx.max() < 30
    assert all(idx[i + 1] - idx[i] == 1 for i in range(6))  # first block is contiguous


def test_bootstrap_interval_brackets_estimate() -> None:
    rng = np.random.default_rng(1)
    num = rng.gamma(2, 50, size=365)
    den = np.full(365, 24.0)
    ci = bootstrap_ratio(num, den, n_boot=300)
    assert ci.low < ci.estimate < ci.high and ci.n_days == 365
    ski = bootstrap_skill(num * 0.9, num, n_boot=300)
    assert ski.estimate == pytest.approx(0.1) and ski.low <= 0.1 <= ski.high


def test_diebold_mariano_detects_real_differences_only() -> None:
    rng = np.random.default_rng(2)
    base = rng.gamma(2, 1, size=400)
    same = diebold_mariano(base + rng.normal(0, 0.01, 400), base)
    assert same.p_value > 0.01
    better = diebold_mariano(base * 0.8, base)
    assert better.statistic < 0 and better.p_value < 1e-6
    with pytest.raises(ValueError):
        diebold_mariano(base[:5], base[:5])


def test_common_support_scores_identical_hours() -> None:
    fc, actuals = _frame()
    fc = fc.with_columns(
        pl.when((pl.col("model") == "b") & (pl.col("hour_ending_utc").dt.hour() < 5))
        .then(None)
        .otherwise(pl.col("yhat"))
        .alias("yhat")
    )
    common = score(fc, actuals)
    # hours ending 01-04 and 00 (the 24th hour) are withheld for model b
    assert common.group_by("model").len()["len"].to_list() == [19, 19]
    assert score(fc, actuals, common_support=False).height == 24 + 19
