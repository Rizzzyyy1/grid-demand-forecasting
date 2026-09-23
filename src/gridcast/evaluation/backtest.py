"""Rolling-origin backtest: expanding window, one refit per calendar month.

For each month *M* of the evaluation window every forecaster is re-created from its factory,
fitted on all feature rows with a known target whose target day is at most ``M_start - 2 days``
(so every training actual was published before the first issue time in *M*), then asked to
forecast every target hour in *M*. Features themselves are point-in-time per origin, so within a
month the forecasts still use each day's freshest allowed data; only model parameters are frozen.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import date, timedelta

import polars as pl
import structlog

from gridcast.models.base import Forecaster, as_batch

log = structlog.get_logger(__name__)
CONTEXT_DAYS = 14


@dataclass(frozen=True)
class BacktestConfig:
    """Evaluation window and training policy."""

    start: date
    end: date
    train_start: date | None = None
    min_train_days: int = 180
    gap_days: int = 2

    def months(self) -> list[tuple[date, date]]:
        """(first, last) target day of each refit month inside the window."""
        out = []
        cursor = date(self.start.year, self.start.month, 1)
        while cursor <= self.end:
            nxt = date(cursor.year + cursor.month // 12, cursor.month % 12 + 1, 1)
            out.append((max(cursor, self.start), min(nxt - timedelta(days=1), self.end)))
            cursor = nxt
        return out


@dataclass
class BacktestResult:
    """Forecasts from every model plus bookkeeping about what was checked."""

    forecasts: pl.DataFrame
    refits: int = 0
    train_rows: dict[str, list[int]] = field(default_factory=dict)
    fit_seconds: dict[str, float] = field(default_factory=dict)
    train_gap_checks: int = 0
    null_forecasts: dict[str, int] = field(default_factory=dict)


def run_backtest(
    features: pl.DataFrame,
    factories: Mapping[str, Callable[[], Forecaster]],
    config: BacktestConfig,
) -> BacktestResult:
    """Run every forecaster over the window; returns the stacked ``ForecastBatch`` frames."""
    batches: list[pl.DataFrame] = []
    result = BacktestResult(forecasts=pl.DataFrame())
    known = features.filter(pl.col("y").is_not_null())
    if config.train_start is not None:
        known = known.filter(pl.col("target_day") >= config.train_start)
    for first, last in config.months():
        test = features.filter(pl.col("target_day").is_between(first, last))
        if test.is_empty():
            continue
        train_end = first - timedelta(days=config.gap_days)
        train = known.filter(pl.col("target_day") <= train_end)
        context = features.filter(
            pl.col("target_day").is_between(
                first - timedelta(days=CONTEXT_DAYS), first - timedelta(days=1)
            )
        )
        _assert_training_precedes_issue(train, test)
        result.train_gap_checks += test.height
        train_days = train.select("target_day").n_unique()
        if train_days < config.min_train_days:
            raise ValueError(
                f"only {train_days} training days before {first}; need {config.min_train_days}"
            )
        for name, factory in factories.items():
            model = factory()
            started = time.perf_counter()
            model.fit(train)
            preds = model.predict(test, context=context)
            elapsed = time.perf_counter() - started
            batch = as_batch(test, preds, name)
            batches.append(batch)
            result.null_forecasts[name] = (
                result.null_forecasts.get(name, 0) + batch["yhat"].null_count()
            )
            result.train_rows.setdefault(name, []).append(train.height)
            result.fit_seconds[name] = result.fit_seconds.get(name, 0.0) + elapsed
        result.refits += 1
        log.info(
            "backtest.month", month=f"{first:%Y-%m}", train_rows=train.height, test_rows=test.height
        )
    result.forecasts = pl.concat(batches) if batches else pl.DataFrame()
    return result


def _assert_training_precedes_issue(train: pl.DataFrame, test: pl.DataFrame) -> None:
    """Per BA, every training actual must end at or before the earliest demand cutoff in ``test``.

    Checked per BA because cutoffs are local times: a global max/min comparison mixes time zones.
    """
    if train.is_empty():
        return
    newest = train.group_by("ba_code").agg(pl.col("hour_ending_utc").max().alias("newest"))
    cutoffs = test.group_by("ba_code").agg(
        pl.col("demand_cutoff").min().alias("cutoff"), pl.col("issued_at").min().alias("issued")
    )
    bad = newest.join(cutoffs, on="ba_code").filter(pl.col("newest") > pl.col("cutoff"))
    if bad.height:
        r = bad.row(0, named=True)
        raise AssertionError(
            f"{r['ba_code']}: training uses an actual ending {r['newest']!s}, after the demand "
            f"cutoff {r['cutoff']!s} of the first forecast issued {r['issued']!s}"
        )
