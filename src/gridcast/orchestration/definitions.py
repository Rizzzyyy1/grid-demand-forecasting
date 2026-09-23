"""Dagster definitions: the whole pipeline as software-defined assets.

Lineage: raw EIA files + raw weather files -> dbt staging/marts -> production model -> daily live
forecasts -> live scores (+ the data-profile report). Schedules: daily at 12:30 UTC - after the
previous day's EIA bulk refresh (~14:40 UTC) and before the earliest issue time (10:00 EDT =
14:00 UTC) - and a weekly retrain. Asset checks surface freshness and leakage in the UI.

This module deliberately omits ``from __future__ import annotations``: Dagster inspects the
``context`` annotation at definition time and rejects string annotations.
"""

import os
from collections.abc import Iterator, Mapping
from datetime import timedelta
from typing import Any

import dagster as dg
from dagster import AssetExecutionContext
from dagster_dbt import DagsterDbtTranslator, DbtCliResource, DbtProject, dbt_assets

from gridcast.core.regions import all_regions
from gridcast.core.settings import get_settings
from gridcast.core.time import utc_now
from gridcast.warehouse.dbt import TRANSFORM_DIR, dbt_env

SETTINGS = get_settings()
os.environ.update(dbt_env(SETTINGS))

dbt_project = DbtProject(project_dir=TRANSFORM_DIR, profiles_dir=TRANSFORM_DIR)
dbt_project.prepare_if_dev()
if not dbt_project.manifest_path.exists():  # e.g. `dagster asset materialize` outside `dagster dev`
    dbt_project.preparer.prepare(dbt_project)

RAW_EIA = dg.AssetKey(["raw", "eia_bulk_files"])
RAW_WEATHER = dg.AssetKey(["raw", "weather_forecast_files"])
MARTS = [dg.AssetKey(["fct_demand_hourly"]), dg.AssetKey(["fct_weather_forecast_hourly"])]


class Translator(DagsterDbtTranslator):
    """Wire dbt staging models to the Python assets that produce their raw files."""

    def get_asset_spec(
        self, manifest: Mapping[str, Any], unique_id: str, project: Any
    ) -> dg.AssetSpec:
        spec = super().get_asset_spec(manifest, unique_id, project)
        name = unique_id.rsplit(".", maxsplit=1)[-1]
        if name == "stg_eia__balance":
            return spec.merge_attributes(deps=[RAW_EIA])
        if name.startswith("stg_open_meteo__"):
            return spec.merge_attributes(deps=[RAW_WEATHER])
        return spec


@dg.asset(
    key=RAW_EIA,
    group_name="raw",
    kinds={"python"},
    description="EIA-930 six-month bulk files (idempotent sync with sha256 manifest).",
)
def eia_bulk_files(context: AssetExecutionContext) -> dg.MaterializeResult[None]:
    from gridcast.ingestion.eia.bulk import EiaBulkDownloader  # noqa: PLC0415
    from gridcast.ingestion.http import make_client  # noqa: PLC0415

    with make_client(SETTINGS.http_timeout_s) as client:
        report = EiaBulkDownloader(client, SETTINGS.raw_dir / "eia").sync(
            SETTINGS.eia_start_year, utc_now().date()
        )
    context.log.info(f"EIA: {report.files_checked} files checked")
    return dg.MaterializeResult(
        metadata={
            "files_checked": report.files_checked,
            "downloaded": len(report.downloaded),
            "not_modified": len(report.not_modified),
            "mb_downloaded": report.bytes_downloaded / 1e6,
        }
    )


@dg.asset(
    key=RAW_WEATHER,
    group_name="raw",
    kinds={"python"},
    description="Open-Meteo GFS day-2 forecasts per city and month (quota-aware, resumable).",
)
def weather_forecast_files(context: AssetExecutionContext) -> dg.MaterializeResult[None]:
    from gridcast.ingestion.http import make_client  # noqa: PLC0415
    from gridcast.ingestion.weather.open_meteo import (  # noqa: PLC0415
        OpenMeteoDownloader,
        WeatherKind,
    )

    with make_client(SETTINGS.http_timeout_s) as client:
        report = OpenMeteoDownloader(client, SETTINGS.raw_dir / "weather").sync(
            WeatherKind.FORECAST_D2, all_regions(), SETTINGS.weather_start, utc_now().date()
        )
    if report.stopped_for_quota:
        context.log.warning(f"quota reached, {report.remaining} chunks left for the next run")
    return dg.MaterializeResult(
        metadata={
            "downloaded": report.downloaded,
            "skipped": report.skipped,
            "remaining": report.remaining,
            "quota_stop": report.stopped_for_quota,
        }
    )


@dbt_assets(manifest=dbt_project.manifest_path, dagster_dbt_translator=Translator())
def warehouse(context: AssetExecutionContext, dbt: DbtCliResource) -> Iterator[Any]:
    """Every dbt seed, model and test (the tests become Dagster asset checks)."""
    yield from dbt.cli(["build"], context=context).stream()


@dg.asset(
    deps=MARTS,
    group_name="ml",
    kinds={"lightgbm", "mlflow"},
    description="LightGBM trained on all history under the live protocol; MLflow champion.",
)
def production_model() -> dg.MaterializeResult[None]:
    from gridcast.live.production import train_production  # noqa: PLC0415

    trained = train_production(SETTINGS, utc_now().date())
    return dg.MaterializeResult(
        metadata={
            "version": trained.version,
            "train_rows": trained.train_rows,
            "last_train_day": str(trained.last_train_day),
            "mlflow_run": trained.run_id,
        }
    )


@dg.asset(
    deps=[*MARTS, production_model],
    group_name="live",
    kinds={"duckdb"},
    description="Tomorrow's forecasts, appended to the immutable forecast store.",
)
def live_forecasts(context: AssetExecutionContext) -> dg.MaterializeResult[None]:
    from gridcast.live.issue import default_target_day, issue_forecasts  # noqa: PLC0415
    from gridcast.live.store import DuplicateForecastError  # noqa: PLC0415

    target = default_target_day(utc_now())
    try:
        report = issue_forecasts(SETTINGS, target)
    except DuplicateForecastError:
        context.log.info(f"forecasts for {target} already stored; the store is append-only")
        return dg.MaterializeResult(metadata={"target_day": str(target), "rows": 0})
    return dg.MaterializeResult(
        metadata={
            "target_day": str(target),
            "rows": report.rows,
            "late_rows": report.late_rows,
            "model_version": report.model_version,
            "leak_checked_cells": report.cells_checked,
        }
    )


@dg.asset_check(asset=live_forecasts, description="No forecast was produced after its issue time.")
def forecasts_on_time() -> dg.AssetCheckResult:
    from gridcast.live.issue import store  # noqa: PLC0415

    rows = store(SETTINGS).read()
    late = int(rows["late"].sum()) if rows.height else 0
    return dg.AssetCheckResult(
        passed=late == 0,
        metadata={"rows": rows.height, "late": late},
        severity=dg.AssetCheckSeverity.WARN,
    )


@dg.asset(
    deps=[live_forecasts, *MARTS],
    group_name="live",
    kinds={"polars"},
    description="Live track record: stored forecasts vs published actuals and the operator.",
)
def live_scores() -> dg.MaterializeResult[None]:
    from gridcast.live.issue import live_scores as compute  # noqa: PLC0415

    scores = compute(SETTINGS)
    md = scores.to_pandas().to_markdown(index=False) if scores.height else "no scored days yet"
    return dg.MaterializeResult(metadata={"rows": scores.height, "table": dg.MetadataValue.md(md)})


@dg.asset(
    deps=MARTS,
    group_name="reports",
    kinds={"markdown"},
    description="reports/data_profile.md regenerated from the warehouse.",
)
def data_profile_report() -> dg.MaterializeResult[None]:
    from gridcast.warehouse.profile import write_profile  # noqa: PLC0415

    path = write_profile(SETTINGS)
    return dg.MaterializeResult(metadata={"path": str(path)})


@dg.asset_check(asset=RAW_EIA, description="The open EIA file was refreshed within 36 hours.")
def eia_fresh() -> dg.AssetCheckResult:
    from gridcast.ingestion.manifest import Manifest  # noqa: PLC0415

    manifest = Manifest(SETTINGS.raw_dir / "eia" / "manifest.jsonl")
    newest = max(manifest.entries(), key=lambda e: e.fetched_at)
    age = utc_now() - newest.fetched_at
    return dg.AssetCheckResult(
        passed=age < timedelta(hours=36),
        metadata={"newest_fetch": str(newest.fetched_at), "age_h": age.total_seconds() / 3600},
    )


@dg.asset(
    deps=MARTS,
    group_name="reports",
    kinds={"evidently"},
    description="Feature drift (last 28 days vs the preceding year), HTML + JSON.",
)
def feature_drift_report() -> dg.MaterializeResult[None]:
    from gridcast.live.monitoring import drift_report  # noqa: PLC0415

    s = drift_report(SETTINGS, utc_now().date())
    return dg.MaterializeResult(
        metadata={
            "drifted_columns": s.drifted_columns,
            "share": s.share,
            "columns_checked": s.columns_checked,
            "html": str(s.html),
        }
    )


daily_job = dg.define_asset_job(
    "daily_live",
    selection=dg.AssetSelection.all() - dg.AssetSelection.assets(production_model),
)
weekly_job = dg.define_asset_job(
    "weekly_retrain", selection=dg.AssetSelection.assets(production_model)
)

defs = dg.Definitions(
    assets=[
        eia_bulk_files,
        weather_forecast_files,
        warehouse,
        production_model,
        live_forecasts,
        live_scores,
        data_profile_report,
    ],
    asset_checks=[forecasts_on_time, eia_fresh],
    jobs=[daily_job, weekly_job],
    schedules=[
        dg.ScheduleDefinition(job=daily_job, cron_schedule="30 12 * * *", execution_timezone="UTC"),
        dg.ScheduleDefinition(job=weekly_job, cron_schedule="0 12 * * 1", execution_timezone="UTC"),
    ],
    resources={"dbt": DbtCliResource(project_dir=dbt_project)},
)
