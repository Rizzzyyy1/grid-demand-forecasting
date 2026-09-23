"""Issue tomorrow's forecasts and score past ones.

``issue_forecasts`` builds features for the target day under the live protocol, verifies them
point-in-time, predicts with the ``champion`` model and appends to the store. ``live_scores``
joins stored forecasts to published actuals and the operator's forecast for the same hours.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Protocol

import polars as pl
import structlog

from gridcast.core import time as t
from gridcast.core.regions import all_regions
from gridcast.core.settings import Settings
from gridcast.evaluation.metrics import point_metrics, score
from gridcast.features.build import FeatureConfig, build_features, check_point_in_time
from gridcast.live.production import LIVE_PROTOCOL, load_champion
from gridcast.live.store import DuplicateForecastError, ForecastStore
from gridcast.models.base import Forecaster, as_batch
from gridcast.warehouse.duck import read_demand, read_weather

log = structlog.get_logger(__name__)
STORE_FILE = "forecast_store.duckdb"


def store(settings: Settings) -> ForecastStore:
    """The live forecast store under ``data/``."""
    return ForecastStore(settings.data_dir / STORE_FILE)


def default_target_day(now: datetime) -> date:
    """Tomorrow in US Eastern time - the day most BAs are forecasting at this moment."""
    return (t.to_local(now, t.zone("America/New_York")) + timedelta(days=1)).date()


class ForecastSink(Protocol):
    """What issuance needs from a store (DuckDB locally, Parquet files in the scheduled job)."""

    def append(
        self,
        batch: pl.DataFrame,
        created_at: datetime,
        protocol: str,
        model_version: str,
        code_version: str = "unknown",
    ) -> int:
        """Persist an immutable batch."""
        ...

    def has(self, target_day: date, model: str) -> bool:
        """True if this (target day, model) was already issued."""
        ...

    def read(self) -> pl.DataFrame:
        """Every stored row."""
        ...


LIVE_MODEL = "lgbm_live"


@dataclass(frozen=True)
class IssueReport:
    """What one issuance did."""

    target_day: date
    rows: int
    bas: int
    late_rows: int
    model_version: str
    null_forecasts: int
    cells_checked: int
    skipped_existing: bool = False


def issue_forecasts(
    settings: Settings,
    target_day: date,
    now: datetime | None = None,
    *,
    sink: ForecastSink | None = None,
    model: Forecaster | None = None,
    model_version: str | None = None,
    code_version: str = "unknown",
    skip_existing: bool = False,
) -> IssueReport:
    """Forecast every BA's hours on ``target_day`` and store them (append-only).

    Defaults use the local DuckDB store and the MLflow ``champion``; the scheduled job passes the
    Parquet store and the verified model artefact. With ``skip_existing`` an already-issued day
    is a no-op (re-runs are idempotent) instead of an error.
    """
    now = now or t.utc_now()
    sink = sink or store(settings)
    if sink.has(target_day, LIVE_MODEL):
        if skip_existing:
            log.info("live.already_issued", target_day=str(target_day))
            return IssueReport(target_day, 0, 0, 0, model_version or "-", 0, 0, True)
        raise DuplicateForecastError(f"{target_day} already issued; the store is append-only")
    config = FeatureConfig(protocol=LIVE_PROTOCOL)
    start = target_day - timedelta(days=21)
    demand = read_demand(settings.warehouse_path, start=start)
    weather = read_weather(settings.warehouse_path, start=start)
    frame = build_features(demand, weather, all_regions(), target_day, target_day, config=config)
    leak = check_point_in_time(frame)
    if not leak.ok:
        raise AssertionError(f"live features leak: {leak.violating_features}")
    if model is None:
        model, model_version = load_champion(settings)
    version = model_version or "unknown"
    batch = as_batch(frame, model.predict(frame), LIVE_MODEL)
    written = sink.append(
        batch,
        created_at=now,
        protocol=LIVE_PROTOCOL.name,
        model_version=version,
        code_version=code_version,
    )
    report = IssueReport(
        target_day=target_day,
        rows=written,
        bas=batch["ba_code"].n_unique(),
        late_rows=batch.filter(pl.col("issued_at") < pl.lit(now)).height,
        model_version=version,
        null_forecasts=batch["yhat"].null_count(),
        cells_checked=leak.cells_checked,
    )
    log.info("live.issued", **report.__dict__)
    return report


def scorable(stored: pl.DataFrame, settings: Settings) -> pl.DataFrame:
    """Live rows that may be scored: target days strictly after the locked test window.

    The live track record must never overlap the test split (2024-07-01 -> 2026-06-30), so it
    cannot become an informal, repeated test evaluation.
    """
    if stored.is_empty():
        return stored
    inside = stored.filter(pl.col("target_day") <= settings.test.end).height
    if inside:
        log.warning("live.rows_inside_test_window_ignored", rows=inside)
    return stored.filter(pl.col("target_day") > settings.test.end)


def _scored(settings: Settings, stored: pl.DataFrame) -> pl.DataFrame:
    stored = scorable(stored, settings)
    if stored.is_empty():
        return pl.DataFrame()
    first = stored["target_day"].min()
    if not isinstance(first, date):
        return pl.DataFrame()
    demand = read_demand(settings.warehouse_path, start=first - timedelta(days=1))
    ours = stored.select("ba_code", "target_day", "hour_ending_utc", "model", "yhat", "late")
    operator = demand.join(
        ours.select("ba_code", "hour_ending_utc", "target_day").unique(),
        on=["ba_code", "hour_ending_utc"],
    ).select(
        "ba_code",
        "target_day",
        "hour_ending_utc",
        pl.lit("operator").alias("model"),
        pl.col("operator_forecast_mw").alias("yhat"),
        pl.lit(False).alias("late"),
    )
    forecasts = pl.concat([ours, operator])
    actuals = demand.select("ba_code", "hour_ending_utc", pl.col("demand_mw").alias("y"))
    return score(forecasts, actuals)


def live_scores(settings: Settings, stored: pl.DataFrame | None = None) -> pl.DataFrame:
    """Per BA: live MAPE of our stored forecasts vs the operator on the same scored hours."""
    scored = _scored(settings, store(settings).read() if stored is None else stored)
    if scored.is_empty():
        return pl.DataFrame()
    metrics = point_metrics(scored)
    days = scored.group_by("ba_code", "model").agg(
        pl.col("target_day").n_unique().alias("days"), pl.col("late").sum().alias("late_hours")
    )
    return metrics.join(days, on=["ba_code", "model"])


def live_daily_scores(settings: Settings, stored: pl.DataFrame) -> pl.DataFrame:
    """Per BA, target day and model: MAPE on the hours scored so far (for the dashboard)."""
    scored = _scored(settings, stored)
    if scored.is_empty():
        return pl.DataFrame()
    return point_metrics(scored, by=("ba_code", "target_day", "model"))
