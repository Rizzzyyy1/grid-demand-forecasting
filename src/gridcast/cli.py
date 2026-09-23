"""The ``gridcast`` command line: ingest, build, backtest, serve.

Commands are thin: they resolve settings, build collaborators and call library code, so everything
they do is also reachable from Dagster assets and tests.
"""

from __future__ import annotations

from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from gridcast.core.regions import all_regions
from gridcast.core.settings import get_settings
from gridcast.core.time import utc_now
from gridcast.logging import configure_logging

app = typer.Typer(
    no_args_is_help=True, add_completion=False, help=__doc__, pretty_exceptions_show_locals=False
)
ingest_app = typer.Typer(no_args_is_help=True, help="Download raw data (idempotent).")
app.add_typer(ingest_app, name="ingest")
console = Console()


@app.callback()
def _main(
    log_level: Annotated[str, typer.Option(help="DEBUG, INFO, WARNING")] = "INFO",
    json_logs: Annotated[bool, typer.Option(help="Emit JSON logs")] = False,
) -> None:
    configure_logging(log_level, json_logs)


@app.command()
def regions() -> None:
    """List the configured balancing authorities and their weather cities."""
    table = Table("BA", "Name", "Clock", "Cities (population weight)")
    for ba in all_regions():
        weights = ba.population_weights()
        cities = ", ".join(f"{c.name} {weights[c.name]:.0%}" for c in ba.cities)
        table.add_row(ba.code, ba.name, ba.timezone, cities)
    console.print(table)


@ingest_app.command("eia")
def ingest_eia(
    force: Annotated[bool, typer.Option(help="Re-download closed periods too")] = False,
) -> None:
    """Download EIA-930 six-month balance files into data/raw/eia."""
    from gridcast.ingestion.eia.bulk import EiaBulkDownloader  # noqa: PLC0415
    from gridcast.ingestion.http import make_client  # noqa: PLC0415

    settings = get_settings()
    with make_client(settings.http_timeout_s) as client:
        report = EiaBulkDownloader(client, settings.raw_dir / "eia").sync(
            settings.eia_start_year, utc_now().date(), force=force
        )
    console.print(
        f"checked {report.files_checked} files: {len(report.downloaded)} downloaded "
        f"({report.bytes_downloaded / 1e6:.1f} MB), {len(report.not_modified)} not modified, "
        f"{len(report.skipped_closed)} closed and already present"
    )


@ingest_app.command("weather")
def ingest_weather(
    kind: Annotated[str, typer.Option(help="forecast_d2 or observed")] = "forecast_d2",
    max_chunks: Annotated[int | None, typer.Option(help="Stop after N downloads")] = None,
    daily_budget: Annotated[
        float | None, typer.Option(help="Override the local daily call budget (provider: 10k)")
    ] = None,
) -> None:
    """Download Open-Meteo weather (city x month files) into data/raw/weather."""
    from gridcast.ingestion.http import make_client  # noqa: PLC0415
    from gridcast.ingestion.weather.open_meteo import (  # noqa: PLC0415
        OpenMeteoDownloader,
        WeatherKind,
    )

    settings = get_settings()
    with make_client(settings.http_timeout_s) as client:
        downloader = OpenMeteoDownloader(
            client, settings.raw_dir / "weather", daily_budget=daily_budget
        )
        report = downloader.sync(
            WeatherKind(kind), all_regions(), settings.weather_start, utc_now().date(), max_chunks
        )
    console.print(
        f"{kind}: {report.downloaded} downloaded, {report.skipped} already complete, "
        f"weight {report.weight_spent:.0f}, remaining {report.remaining}"
        + (
            " - stopped: provider quota reached, re-run later to resume"
            if report.stopped_for_quota
            else ""
        )
    )
    if report.stopped_for_quota:
        raise typer.Exit(code=3)


@app.command()
def seeds() -> None:
    """Regenerate dbt seed CSVs (regions, cities, holidays) from the Python registry."""
    from gridcast.warehouse.dbt import TRANSFORM_DIR  # noqa: PLC0415
    from gridcast.warehouse.seeds import write_seeds  # noqa: PLC0415

    for path in write_seeds(TRANSFORM_DIR / "seeds"):
        console.print(f"wrote {path}")


@app.command()
def build(
    select: Annotated[str | None, typer.Option(help="dbt node selection")] = None,
) -> None:
    """Build and test the warehouse with dbt (seeds, staging, marts, data tests)."""
    from gridcast.warehouse.dbt import run_dbt  # noqa: PLC0415

    args = ["build"] + (["--select", select] if select else [])
    result = run_dbt(get_settings(), args)
    console.print(f"dbt build: {result.passed} passed, {result.failed} failed")
    for message in result.messages:
        console.print(f"  [red]{message}[/red]", markup=True, highlight=False)
    if not result.success:
        raise typer.Exit(code=1)


@app.command()
def profile() -> None:
    """Write reports/data_profile.md from the warehouse (row counts, coverage, findings)."""
    from gridcast.warehouse.profile import write_profile  # noqa: PLC0415

    console.print(f"wrote {write_profile(get_settings())}")


@app.command()
def backtest(
    split: Annotated[str, typer.Option(help="validation or test")] = "validation",
    models: Annotated[str | None, typer.Option(help="Comma-separated model names")] = None,
    population_weighted: Annotated[
        bool, typer.Option(help="Ablation: population-weighted city mean")
    ] = False,
    tag: Annotated[str, typer.Option(help="Suffix for the run id")] = "",
    n_boot: Annotated[int, typer.Option(help="Bootstrap resamples")] = 1000,
    train_start: Annotated[
        str, typer.Option(help="First training day (YYYY-MM-DD)")
    ] = "2021-04-01",
    conformal: Annotated[bool, typer.Option(help="Add CQR-calibrated variants")] = True,
    confirm_final_test_evaluation: Annotated[
        bool, typer.Option(help="Required (once) to evaluate the locked test split")
    ] = False,
) -> None:
    """Rolling-origin backtest over a split; writes reports/runs/<run_id>/ and logs to MLflow."""
    from datetime import date as _date  # noqa: PLC0415

    from gridcast.experiments.run import RunSpec, run_experiment  # noqa: PLC0415
    from gridcast.features.build import FeatureConfig  # noqa: PLC0415

    spec = RunSpec(
        split=split,
        feature_config=FeatureConfig(population_weighted=population_weighted),
        tag=tag,
        n_boot=n_boot,
        train_start=_date.fromisoformat(train_start),
        conformal=conformal,
    )
    if models:
        spec.models = tuple(m.strip() for m in models.split(","))
    out = run_experiment(get_settings(), spec, confirmed_test=confirm_final_test_evaluation)
    console.print(f"wrote {out}")
    console.print((out / "summary.md").read_text(), markup=False, highlight=False)


@app.command()
def train() -> None:
    """Train the live (bulk-protocol) LightGBM on all history and register it as `champion`."""
    from gridcast.live.production import train_production  # noqa: PLC0415

    trained = train_production(get_settings(), utc_now().date())
    console.print(
        f"registered gridcast-lgbm-live v{trained.version}: {trained.train_rows:,} rows "
        f"through {trained.last_train_day} (MLflow run {trained.run_id})"
    )


@app.command()
def forecast(
    day: Annotated[
        str | None, typer.Option(help="Target day YYYY-MM-DD (default: tomorrow)")
    ] = None,
) -> None:
    """Issue forecasts for a target day with the champion model and append them to the store."""
    from datetime import date as _date  # noqa: PLC0415

    from gridcast.live.issue import default_target_day, issue_forecasts  # noqa: PLC0415

    target = _date.fromisoformat(day) if day else default_target_day(utc_now())
    report = issue_forecasts(get_settings(), target)
    console.print(
        f"stored {report.rows} forecasts for {report.target_day} across {report.bas} BAs "
        f"(model v{report.model_version}; {report.late_rows} late; "
        f"{report.null_forecasts} null; {report.cells_checked:,} feature values leak-checked)"
    )


@app.command()
def score() -> None:
    """Score stored live forecasts against published actuals and the operator."""
    from gridcast.live.issue import live_scores  # noqa: PLC0415

    scores = live_scores(get_settings())
    if scores.is_empty():
        console.print("no scorable live forecasts yet (actuals publish ~2 days after the day)")
        return
    table = Table("BA", "model", "days", "hours", "MAPE %", "late hours")
    for r in scores.sort("ba_code", "model").iter_rows(named=True):
        table.add_row(
            r["ba_code"],
            r["model"],
            str(r["days"]),
            str(r["hours"]),
            f"{r['mape']:.2f}",
            str(r["late_hours"]),
        )
    console.print(table)


@app.command()
def serve(
    host: Annotated[str, typer.Option()] = "127.0.0.1",
    port: Annotated[int, typer.Option()] = 8000,
) -> None:
    """Run the FastAPI service."""
    import uvicorn  # noqa: PLC0415

    uvicorn.run("gridcast.serving.app:create_app", factory=True, host=host, port=port)


@app.command()
def ui(port: Annotated[int, typer.Option()] = 8501) -> None:
    """Run the Streamlit dashboard (expects the API on GRIDCAST_API_URL)."""
    import subprocess  # noqa: PLC0415
    import sys  # noqa: PLC0415
    from pathlib import Path  # noqa: PLC0415

    import gridcast.ui  # noqa: PLC0415

    script = Path(gridcast.ui.__file__).parent / "app.py"
    subprocess.run(  # noqa: S603 - fixed interpreter and script
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            str(script),
            "--server.port",
            str(port),
            "--server.headless",
            "true",
        ],
        check=False,
    )


@app.command()
def drift(days: Annotated[int, typer.Option(help="Current window length")] = 28) -> None:
    """Evidently feature-drift report: last N days vs the preceding year."""
    from gridcast.live.monitoring import drift_report  # noqa: PLC0415

    s = drift_report(get_settings(), utc_now().date(), days)
    console.print(
        f"{s.drifted_columns}/{s.columns_checked} features drifted ({s.share:.0%}); "
        f"{s.rows_current:,} current vs {s.rows_reference:,} reference rows -> {s.html}"
    )


@app.command()
def ablate(
    only: Annotated[str | None, typer.Option(help="Comma-separated variant names")] = None,
    n_boot: Annotated[int, typer.Option(help="Bootstrap resamples")] = 1000,
) -> None:
    """Run the DESIGN section 5 ablations on the validation split."""
    from gridcast.experiments.ablations import default_variants, run_ablations  # noqa: PLC0415

    settings = get_settings()
    variants = default_variants()
    if only:
        keep = {"baseline", *only.split(",")}
        variants = [v for v in variants if v.name in keep]
    out = run_ablations(
        settings, variants, settings.validation.start, settings.validation.end, n_boot
    )
    console.print((out / "summary.md").read_text(), markup=False, highlight=False)


@app.command()
def rescore(
    run_id: str,
    n_boot: Annotated[int | None, typer.Option(help="Bootstrap resamples")] = None,
) -> None:
    """Recompute metrics and summary of a run from its saved forecasts (no refitting)."""
    from gridcast.experiments.run import rescore as _rescore  # noqa: PLC0415

    out = _rescore(get_settings(), run_id, n_boot)
    console.print((out / "summary.md").read_text(), markup=False, highlight=False)


@app.command()
def combine(
    run_ids: list[str],
    tag: Annotated[str, typer.Option(help="Suffix for the combined run id")] = "combined",
) -> None:
    """Merge runs over the same split (e.g. LightGBM + N-HiTS) and score them together."""
    from gridcast.experiments.run import combine_runs  # noqa: PLC0415

    out = combine_runs(get_settings(), run_ids, tag)
    console.print(f"wrote {out}")
