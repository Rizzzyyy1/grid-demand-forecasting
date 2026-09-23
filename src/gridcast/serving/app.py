"""FastAPI application: forecasts, live leaderboard, backtest runs, health.

Read-only by design: it serves what the pipeline stored and never computes forecasts on request,
so an API response can always be traced to a stored, immutable forecast row.
"""

from __future__ import annotations

import json
import os
from datetime import date, timedelta
from typing import Annotated

import polars as pl
from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query

from gridcast import __version__
from gridcast.core.regions import UnknownRegionError, all_regions, get_region
from gridcast.core.settings import Settings, get_settings
from gridcast.live.issue import STORE_FILE, live_scores
from gridcast.live.store import ForecastStore
from gridcast.serving.schemas import (
    ForecastPoint,
    ForecastResponse,
    Health,
    LeaderboardRow,
    Region,
    RunSummary,
)
from gridcast.warehouse.duck import read_demand

SettingsDep = Annotated[Settings, Depends(get_settings)]


ops = APIRouter(tags=["ops"])
forecasts = APIRouter(prefix="", tags=["forecasts"])
evaluation = APIRouter(prefix="", tags=["evaluation"])


@ops.get("/healthz", response_model=Health)
def healthz(settings: SettingsDep) -> Health:
    """Liveness: the process is up."""
    return Health(status="ok", warehouse=settings.warehouse_path.exists(), version=__version__)


@ops.get("/readyz", response_model=Health)
def readyz(settings: SettingsDep) -> Health:
    """Readiness: the warehouse and forecast store exist."""
    path = settings.data_dir / STORE_FILE
    if not settings.warehouse_path.exists() or not path.exists():
        raise HTTPException(503, "warehouse or forecast store missing")
    return Health(
        status="ready",
        warehouse=True,
        store_rows=ForecastStore(path).count(),
        version=__version__,
    )


@forecasts.get("/v1/regions", response_model=list[Region])
def regions() -> list[Region]:
    """The ten balancing authorities."""
    return [
        Region(code=b.code, name=b.name, timezone=b.timezone, cities=[c.name for c in b.cities])
        for b in all_regions()
    ]


@forecasts.get("/v1/forecasts/{ba}", response_model=ForecastResponse)
def forecast(
    ba: str,
    settings: SettingsDep,
    day: Annotated[date, Query(description="Target day (BA local)")],
    model: str = "lgbm_live",
) -> ForecastResponse:
    """The most recently issued stored forecast for ``ba`` and ``day``."""
    try:
        get_region(ba)
    except UnknownRegionError as exc:
        raise HTTPException(404, str(exc)) from exc
    path = settings.data_dir / STORE_FILE
    if not path.exists():
        raise HTTPException(404, "no forecasts stored yet")
    rows = ForecastStore(path).read(
        "ba_code = ? and target_day = ? and model = ?", [ba, day, model]
    )
    if rows.is_empty():
        raise HTTPException(404, f"no {model} forecast for {ba} on {day}")
    latest = rows.filter(pl.col("issued_at") == pl.col("issued_at").max()).sort("hour_ending_utc")
    head = latest.row(0, named=True)
    return ForecastResponse(
        ba_code=ba,
        target_day=day,
        model=model,
        model_version=head["model_version"],
        issued_at=head["issued_at"],
        created_at=head["created_at"],
        late=head["late"],
        protocol=head["protocol"],
        hours=[
            ForecastPoint(**{k: r[k] for k in ForecastPoint.model_fields})
            for r in latest.iter_rows(named=True)
        ],
    )


@evaluation.get("/v1/leaderboard", response_model=list[LeaderboardRow])
def leaderboard(settings: SettingsDep) -> list[LeaderboardRow]:
    """Live track record: stored forecasts scored against published actuals."""
    if not (settings.data_dir / STORE_FILE).exists():
        return []
    scores = live_scores(settings)
    return (
        [
            LeaderboardRow(**{k: r[k] for k in LeaderboardRow.model_fields})
            for r in scores.sort("ba_code", "model").iter_rows(named=True)
        ]
        if scores.height
        else []
    )


@evaluation.get("/v1/backtests", response_model=list[RunSummary])
def backtests(settings: SettingsDep) -> list[RunSummary]:
    """Backtest runs on disk, newest first."""
    runs = []
    for cfg in sorted((settings.reports_dir / "runs").glob("*/config.json"), reverse=True):
        c = json.loads(cfg.read_text())
        runs.append(
            RunSummary(
                run_id=c["run_id"],
                split=c["split"],
                window=c["window"],
                models=c["models"],
                refits=c["refits"],
                superseded=c.get("superseded"),
            )
        )
    return runs


@evaluation.get("/v1/backtests/{run_id}/summary")
def backtest_summary(run_id: str, settings: SettingsDep) -> dict[str, str]:
    """The generated Markdown summary of one run."""
    if "/" in run_id or ".." in run_id:
        raise HTTPException(400, "invalid run id")
    path = settings.reports_dir / "runs" / run_id / "summary.md"
    if not path.exists():
        raise HTTPException(404, f"no run {run_id}")
    return {"run_id": run_id, "markdown": path.read_text()}


@evaluation.get("/v1/backtests/{run_id}/series")
def backtest_series(
    run_id: str,
    settings: SettingsDep,
    ba: str,
    start: date,
    end: date,
) -> list[dict[str, object]]:
    """Hourly forecasts of every model in a run, with actuals, for one BA and date range."""
    if "/" in run_id or ".." in run_id:
        raise HTTPException(400, "invalid run id")
    if (end - start).days > 62:
        raise HTTPException(400, "at most 62 days per request")
    path = settings.reports_dir / "runs" / run_id / "forecasts.parquet"
    if not path.exists():
        raise HTTPException(404, f"no run {run_id}")
    fc = (
        pl.scan_parquet(path)
        .filter((pl.col("ba_code") == ba) & pl.col("target_day").is_between(start, end))
        .collect()
    )
    wide = fc.pivot(on="model", index=["hour_ending_utc", "target_day"], values="yhat")
    actual = read_demand(settings.warehouse_path, (ba,), start, end + timedelta(days=2)).select(
        "hour_ending_utc", pl.col("demand_mw").alias("actual")
    )
    out = wide.join(actual, on="hour_ending_utc", how="left").sort("hour_ending_utc")
    return out.with_columns(pl.col("hour_ending_utc").dt.to_string("iso")).to_dicts()


@evaluation.get("/v1/reports/data-profile")
def data_profile(settings: SettingsDep) -> dict[str, str]:
    """The generated data-profile report."""
    path = settings.reports_dir / "data_profile.md"
    if not path.exists():
        raise HTTPException(404, "run `gridcast profile` first")
    return {"markdown": path.read_text()}


def create_app() -> FastAPI:
    """Application factory (used by uvicorn ``--factory`` and tests)."""
    app = FastAPI(
        root_path=os.environ.get("GRIDCAST_API_ROOT_PATH", ""),  # "/api" behind the Caddy proxy
        title="GridCast API",
        version=__version__,
        description="Day-ahead electricity-demand forecasts for ten US balancing authorities.",
    )
    for router in (ops, forecasts, evaluation):
        app.include_router(router)
    return app
