from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import numpy as np
import polars as pl

from gridcast.models.conformal import conformalize


def _synthetic(
    days: int, width: float, noise: float, seed: int = 0
) -> tuple[pl.DataFrame, pl.DataFrame]:
    rng = np.random.default_rng(seed)
    rows, acts = [], []
    start = date(2024, 1, 1)
    for d in range(days):
        day = start + timedelta(days=d)
        for h in range(24):
            t = datetime(day.year, day.month, day.day, tzinfo=UTC) + timedelta(hours=h + 1)
            y = 1000 + rng.normal(0, noise)
            rows.append(
                {
                    "ba_code": "X",
                    "target_day": day,
                    "hour_ending_utc": t,
                    "issued_at": t - timedelta(hours=30),
                    "model": "m",
                    "yhat": 1000.0,
                    "q10": 1000 - width,
                    "q90": 1000 + width,
                    "q025": 1000 - 2 * width,
                    "q975": 1000 + 2 * width,
                }
            )
            acts.append({"ba_code": "X", "hour_ending_utc": t, "y": y})
    return pl.DataFrame(rows), pl.DataFrame(acts)


def _coverage(frame: pl.DataFrame, actuals: pl.DataFrame, lo: str, hi: str, since: date) -> float:
    j = frame.filter(pl.col("target_day") >= since).join(actuals, on=["ba_code", "hour_ending_utc"])
    return float(((j["y"] >= j[lo]) & (j["y"] <= j[hi])).mean())


def test_overconfident_intervals_are_widened_to_nominal() -> None:
    fc, act = _synthetic(150, width=10, noise=50)  # raw 80 % interval is far too narrow
    res = conformalize(fc, act, "m")
    assert res.days_uncalibrated == 22  # first days lack 21 days of history (+2-day gap)
    since = date(2024, 2, 15)
    assert _coverage(fc, act, "q10", "q90", since) < 0.3
    assert abs(_coverage(res.forecasts, act, "q10", "q90", since) - 0.80) < 0.04
    assert abs(_coverage(res.forecasts, act, "q025", "q975", since) - 0.95) < 0.03
    assert res.forecasts["model"].unique().to_list() == ["m+cqr"]


def test_underconfident_intervals_are_narrowed() -> None:
    fc, act = _synthetic(150, width=300, noise=50)
    res = conformalize(fc, act, "m")
    before = (fc["q90"] - fc["q10"]).mean()
    after = (
        res.forecasts.filter(pl.col("target_day") >= date(2024, 2, 15))
        .select((pl.col("q90") - pl.col("q10")).mean())
        .item()
    )
    assert after < before  # type: ignore[operator]


def test_calibration_ignores_the_target_day_and_the_gap() -> None:
    """Changing actuals on D-1 and D must not change D's calibrated interval."""
    fc, act = _synthetic(80, width=10, noise=50)
    target = date(2024, 3, 10)
    base = conformalize(fc, act, "m").forecasts.filter(pl.col("target_day") == target)
    moved = act.with_columns(
        pl.when(pl.col("hour_ending_utc") > datetime(2024, 3, 9, tzinfo=UTC))
        .then(pl.col("y") * 5)
        .otherwise(pl.col("y"))
        .alias("y")
    )
    after = conformalize(fc, moved, "m").forecasts.filter(pl.col("target_day") == target)
    assert base.select("q10", "q90").equals(after.select("q10", "q90"))
