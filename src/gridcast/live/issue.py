"""Issue tomorrow's forecasts and score past ones.

``issue_forecasts`` builds features for the target day under the live protocol, verifies them
point-in-time, predicts with the ``champion`` model and appends to the store. ``live_scores``
joins stored forecasts to published actuals and the operator's forecast for the same hours.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta

import polars as pl
import structlog

from gridcast.core import time as t
from gridcast.core.regions import all_regions
from gridcast.core.settings import Settings
from gridcast.evaluation.metrics import point_metrics, score
from gridcast.features.build import FeatureConfig, build_features, check_point_in_time
from gridcast.live.production import LIVE_PROTOCOL, load_champion
from gridcast.live.store import ForecastStore
from gridcast.models.base import as_batch
from gridcast.warehouse.duck import read_demand, read_weather

log = structlog.get_logger(__name__)
STORE_FILE = "forecast_store.duckdb"


def store(settings: Settings) -> ForecastStore:
    """The live forecast store under ``data/``."""
    return ForecastStore(settings.data_dir / STORE_FILE)


def default_target_day(now: datetime) -> date:
    """Tomorrow in US Eastern time - the day most BAs are forecasting at this moment."""
    return (t.to_local(now, t.zone("America/New_York")) + timedelta(days=1)).date()


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


def issue_forecasts(
    settings: Settings, target_day: date, now: datetime | None = None
) -> IssueReport:
    """Forecast every BA's hours on ``target_day`` with the champion model and store them."""
    now = now or t.utc_now()
    config = FeatureConfig(protocol=LIVE_PROTOCOL)
    start = target_day - timedelta(days=21)
    demand = read_demand(settings.warehouse_path, start=start)
    weather = read_weather(settings.warehouse_path, start=start)
    frame = build_features(demand, weather, all_regions(), target_day, target_day, config=config)
    leak = check_point_in_time(frame)
    if not leak.ok:
        raise AssertionError(f"live features leak: {leak.violating_features}")
    model, version = load_champion(settings)
    batch = as_batch(frame, model.predict(frame), "lgbm_live")
    written = store(settings).append(
        batch, created_at=now, protocol=LIVE_PROTOCOL.name, model_version=version
    )
    late = batch.filter(pl.col("issued_at") < pl.lit(now)).height
    report = IssueReport(
        target_day=target_day,
        rows=written,
        bas=batch["ba_code"].n_unique(),
        late_rows=late,
        model_version=version,
        null_forecasts=batch["yhat"].null_count(),
        cells_checked=leak.cells_checked,
    )
    log.info("live.issued", **report.__dict__)
    return report


def live_scores(settings: Settings) -> pl.DataFrame:
    """Per BA: live MAPE of our stored forecasts vs the operator on the same scored hours."""
    stored = store(settings).read()
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
    scored = score(forecasts, actuals)
    if scored.is_empty():
        return pl.DataFrame()
    metrics = point_metrics(scored)
    days = scored.group_by("ba_code", "model").agg(
        pl.col("target_day").n_unique().alias("days"), pl.col("late").sum().alias("late_hours")
    )
    return metrics.join(days, on=["ba_code", "model"])
