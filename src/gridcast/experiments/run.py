"""Run a backtest split end to end and write an immutable run directory.

``reports/runs/<run_id>/`` holds everything a results table is generated from:
``config.json``, ``forecasts.parquet``, ``metrics_*.csv``, ``comparisons.csv`` and ``summary.md``.
The same numbers are logged to MLflow. The **test** split is locked: it can be evaluated once,
and only with an explicit confirmation (DESIGN section 4).
"""

from __future__ import annotations

import json
import subprocess
import zlib
from dataclasses import asdict, dataclass, field
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import polars as pl
import structlog

from gridcast.core.domain import ProtocolConfig
from gridcast.core.regions import all_regions
from gridcast.core.settings import Settings, Window, ensure_offline
from gridcast.evaluation.backtest import BacktestConfig, BacktestResult, run_backtest
from gridcast.evaluation.metrics import (
    interval_metrics,
    peak_metrics,
    point_metrics,
    score,
    skill,
    slice_metrics,
)
from gridcast.evaluation.stats import bootstrap_skill, diebold_mariano
from gridcast.experiments.registry import BENCHMARKS, LADDER, factories
from gridcast.features.build import FeatureConfig, build_features, check_point_in_time
from gridcast.models.conformal import conformalize
from gridcast.warehouse.duck import read_demand, read_weather

log = structlog.get_logger(__name__)
TEST_LOCK = "TEST_SPLIT_EVALUATED.json"
FLAGGED = {
    "SWPP": "operator series changes definition in 2025-05 (data_profile 5.2)",
    "CISO": "operator series has a growing midday bias (data_profile 5.1)",
}


class SplitLockedError(RuntimeError):
    """Raised when the test split would be evaluated without confirmation or a second time."""


@dataclass
class RunSpec:
    """What to run."""

    split: str = "validation"
    models: tuple[str, ...] = (*BENCHMARKS, *LADDER)
    train_start: date = date(2021, 4, 1)
    feature_config: FeatureConfig = field(default_factory=FeatureConfig)
    n_boot: int = 1000
    tag: str = ""
    conformal: bool = True
    burn_in_days: int = 63  # forecasts before the window, used only to calibrate CQR


def _git_sha(base: Path) -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],  # noqa: S607 - fixed command
            cwd=base,
            capture_output=True,
            text=True,
            check=False,
        )
        return out.stdout.strip() or "uncommitted"
    except OSError:
        return "unknown"


def _window(settings: Settings, split: str) -> Window:
    if split == "validation":
        return settings.validation
    if split == "test":
        return settings.test
    raise ValueError(f"unknown split {split!r} (validation or test)")


def guard_test_split(settings: Settings, split: str, confirmed: bool) -> None:
    """Refuse to touch the test split unless confirmed, and only ever once (never in live mode)."""
    ensure_offline(settings, f"a {split} backtest")
    if split != "test":
        return
    lock = settings.reports_dir / TEST_LOCK
    if lock.exists():
        raise SplitLockedError(f"the test split was already evaluated: {lock.read_text()}")
    if not confirmed:
        raise SplitLockedError(
            "evaluating the test split is a one-time act after the model set is frozen; "
            "re-run with --confirm-final-test-evaluation"
        )


def comparisons(scored: pl.DataFrame, models: tuple[str, ...], n_boot: int) -> pl.DataFrame:
    """Per BA and model: skill vs each benchmark with a block-bootstrap CI and a DM test."""
    rows: list[dict[str, Any]] = []
    daily = scored.group_by("ba_code", "model", "target_day").agg(
        pl.col("abs_err").sum().alias("abs_sum"), pl.len().alias("n")
    )
    for ref in BENCHMARKS:
        if ref not in models:
            continue
        for model in models:
            if model in BENCHMARKS or model.endswith("+cqr"):  # CQR changes intervals only
                continue
            for ba in sorted(daily["ba_code"].unique().to_list()):
                a = daily.filter((pl.col("model") == model) & (pl.col("ba_code") == ba))
                b = daily.filter((pl.col("model") == ref) & (pl.col("ba_code") == ba))
                paired = (
                    a.join(b, on="target_day", suffix="_ref")
                    .filter(pl.col("n") == pl.col("n_ref"))
                    .sort("target_day")
                )
                if paired.height < 30:
                    continue
                m = paired["abs_sum"].to_numpy().astype(float)
                r = paired["abs_sum_ref"].to_numpy().astype(float)
                ci = bootstrap_skill(
                    m, r, n_boot=n_boot, seed=zlib.crc32(f"{model}|{ref}|{ba}".encode())
                )
                dm = diebold_mariano(m / paired["n"].to_numpy(), r / paired["n"].to_numpy())
                rows.append(
                    {
                        "ba_code": ba,
                        "model": model,
                        "reference": ref,
                        "days": paired.height,
                        "skill": ci.estimate,
                        "skill_low": ci.low,
                        "skill_high": ci.high,
                        "dm_stat": dm.statistic,
                        "dm_p": dm.p_value,
                        "flag": FLAGGED.get(ba, "") if ref == "operator" else "",
                    }
                )
    return pl.DataFrame(rows)


def _fmt(v: object, spec: str = ".2f") -> str:
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "—"
    return format(v, spec) if isinstance(v, int | float) else str(v)


def render_summary(
    run_id: str,
    spec: RunSpec,
    *,
    window: Window,
    point: pl.DataFrame,
    peaks: pl.DataFrame,
    intervals: pl.DataFrame,
    comps: pl.DataFrame,
    leakage: dict[str, Any],
    result: BacktestResult,
    slices: pl.DataFrame | None = None,
) -> str:
    """Markdown summary for one run - every number comes from the frames passed in."""
    proto = spec.feature_config.protocol
    present = point["model"].unique().to_list()
    models = [m for m in spec.models if m in present]
    models += sorted(m for m in present if m not in models)
    # CQR variants share their base model's point forecast; they appear in the interval table only
    point_models = [m for m in models if not m.endswith("+cqr")]
    lines = [
        f"# Run {run_id} — {spec.split} split",
        "",
        f"Target days {window.start} → {window.end}; training from {spec.train_start}, expanding, "
        f"refit monthly ({result.refits} refits). Protocol `{proto.name}`: issued "
        f"{proto.issue_time:%H:%M} local D-1 with demand to {proto.demand_cutoff_time:%H:%M} on "
        f"D-{proto.demand_cutoff_days_before}; weather = GFS forecasts made 48 h ahead. "
        f"Leakage check: {leakage['cells_checked']:,} feature values over "
        f"{leakage['origins_checked']:,} forecast origins, {leakage['violations']} violations.",
        "",
        "## MAPE (%) by BA",
        "",
        "| BA | hours | " + " | ".join(point_models) + " |",
        "|---|---|" + "---|" * len(point_models),
    ]
    wide = point.pivot(on="model", index="ba_code", values="mape")
    hours = point.filter(pl.col("model") == point_models[0]).select("ba_code", "hours")
    for row in wide.join(hours, on="ba_code").sort("ba_code").iter_rows(named=True):
        best = min(
            (row[m] for m in point_models if m not in BENCHMARKS and row.get(m) is not None),
            default=None,
        )
        cells = []
        for m in point_models:
            v = row.get(m)
            text = _fmt(v)
            cells.append(f"**{text}**" if v is not None and v == best else text)
        lines.append(f"| {row['ba_code']} | {row['hours']:,} | " + " | ".join(cells) + " |")
    lines += ["", "Bold = best of our models. Operator columns are benchmarks, not our models.", ""]
    for ref in BENCHMARKS:
        sub = comps.filter(pl.col("reference") == ref) if comps.height else comps
        if sub.is_empty():
            continue
        lines += [
            f"## Skill vs `{ref}` (1 - MAE/MAE_ref), 95 % block-bootstrap CI, DM p-value",
            "",
            "| BA | model | days | skill | 95 % CI | DM p | note |",
            "|---|---|---|---|---|---|---|",
        ]
        for r in sub.sort("ba_code", "model").iter_rows(named=True):
            lines.append(
                f"| {r['ba_code']} | {r['model']} | {r['days']} | {r['skill']:+.3f} | "
                f"[{r['skill_low']:+.3f}, {r['skill_high']:+.3f}] | {r['dm_p']:.3g} | {r['flag']} |"
            )
        lines.append("")
    if intervals.height:
        lines += [
            "## Prediction intervals (nominal 80 % and 95 %)",
            "",
            "| BA | model | coverage 80 | width 80 (%) | coverage 95 | width 95 (%) |",
            "|---|---|---|---|---|---|",
        ]
        for r in intervals.sort("ba_code", "model").iter_rows(named=True):
            lines.append(
                f"| {r['ba_code']} | {r['model']} | {r['coverage_80']:.1f} | "
                f"{r['width_80_pct']:.1f} | {r['coverage_95']:.1f} | {r['width_95_pct']:.1f} |"
            )
        lines.append("")
    lines += [
        "## Daily peak",
        "",
        "| BA | model | days | peak APE (%) | peak hour off by >1 h (%) |",
        "|---|---|---|---|---|",
    ]
    for r in (
        peaks.filter(~pl.col("model").str.ends_with("+cqr"))
        .sort("ba_code", "model")
        .iter_rows(named=True)
    ):
        lines.append(
            f"| {r['ba_code']} | {r['model']} | {r['days']} | {r['peak_ape']:.2f} | "
            f"{r['peak_hour_miss_pct']:.1f} |"
        )
    if slices is not None and slices.height:
        focus = [m for m in point_models if m in {"operator_debiased", *point_models[-2:]}]
        lines += [
            "",
            "## Slices (MAPE %, pooled over BAs)",
            "",
            "| slice | value | " + " | ".join(focus) + " |",
            "|---|---|" + "---|" * len(focus),
        ]
        wide = slices.pivot(on="model", index=["slice", "value"], values="mape").sort(
            "slice", "value"
        )
        for r in wide.iter_rows(named=True):
            lines.append(
                f"| {r['slice']} | {r['value']} | "
                + " | ".join(_fmt(r.get(m)) for m in focus)
                + " |"
            )
    lines += ["", "## Compute", ""]
    for name, secs in result.fit_seconds.items():
        lines.append(f"* `{name}`: {secs:.0f} s fit+predict over {result.refits} refits")
    return "\n".join(lines) + "\n"


def _add_conformal(
    result: BacktestResult, actuals: pl.DataFrame, spec: RunSpec, gap_days: int
) -> dict[str, dict[str, int]]:
    """Append ``<model>+cqr`` forecasts for every model that produced quantiles."""
    calibration: dict[str, dict[str, int]] = {}
    extra = []
    for model in spec.models:
        rows = result.forecasts.filter(pl.col("model") == model)
        if model in BENCHMARKS or rows["q10"].null_count() == rows.height:
            continue
        cqr = conformalize(result.forecasts, actuals, model, gap_days=gap_days)
        extra.append(cqr.forecasts)
        calibration[f"{model}+cqr"] = {
            "days_calibrated": cqr.days_calibrated,
            "days_uncalibrated": cqr.days_uncalibrated,
        }
    if extra:
        result.forecasts = pl.concat([result.forecasts, *extra])
    return calibration


def _score_and_write(
    settings: Settings,
    out: Path,
    spec: RunSpec,
    *,
    window: Window,
    result: BacktestResult,
    features: pl.DataFrame,
    leakage: dict[str, Any],
    calibration: dict[str, dict[str, int]],
) -> tuple[dict[str, Any], pl.DataFrame, pl.DataFrame]:
    """Score ``result.forecasts`` (already restricted to the window) and write every artefact."""
    actuals = features.select("ba_code", "hour_ending_utc", "y")
    models_scored = tuple(result.forecasts["model"].unique(maintain_order=True).to_list())
    scored = score(result.forecasts, actuals)
    point = (
        skill(skill(point_metrics(scored), "operator"), "operator_debiased")
        if "operator_debiased" in spec.models
        else point_metrics(scored)
    )
    peaks = peak_metrics(scored)
    intervals = interval_metrics(scored)
    comps = comparisons(scored, models_scored, spec.n_boot)
    overall = point_metrics(scored, by=("model",))
    slices = slice_metrics(scored, features)
    slices.write_csv(out / "metrics_slices.csv")

    result.forecasts.write_parquet(out / "forecasts.parquet")
    point.write_csv(out / "metrics_point.csv")
    overall.write_csv(out / "metrics_overall.csv")
    peaks.write_csv(out / "metrics_peak.csv")
    if intervals.height:
        intervals.write_csv(out / "metrics_intervals.csv")
    if comps.height:
        comps.write_csv(out / "comparisons.csv")
    config = {
        "run_id": out.name,
        "split": spec.split,
        "window": [str(window.start), str(window.end)],
        "models": list(spec.models),
        "train_start": str(spec.train_start),
        "feature_config": {
            "population_weighted": spec.feature_config.population_weighted,
            "protocol": spec.feature_config.protocol.model_dump(mode="json"),
        },
        "git_sha": _git_sha(settings.base_dir),
        "leakage": leakage,
        "refits": result.refits,
        "train_gap_checks": result.train_gap_checks,
        "null_forecasts": result.null_forecasts,
        "fit_seconds": result.fit_seconds,
        "n_boot": spec.n_boot,
        "conformal": calibration,
        "burn_in_days": spec.burn_in_days if spec.conformal else 0,
        "models_scored": list(models_scored),
    }
    (out / "config.json").write_text(json.dumps(config, indent=2, default=str))
    summary = render_summary(
        out.name,
        spec,
        window=window,
        point=point,
        peaks=peaks,
        intervals=intervals,
        comps=comps,
        leakage=leakage,
        result=result,
        slices=slices,
    )
    (out / "summary.md").write_text(summary)
    return config, overall, point


def run_experiment(settings: Settings, spec: RunSpec, confirmed_test: bool = False) -> Path:
    """Execute ``spec``; returns the run directory."""
    guard_test_split(settings, spec.split, confirmed_test)
    window = _window(settings, spec.split)
    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + (f"-{spec.tag}" if spec.tag else "")
    out = settings.reports_dir / "runs" / run_id
    out.mkdir(parents=True, exist_ok=False)

    demand = read_demand(settings.warehouse_path)
    weather = read_weather(settings.warehouse_path)
    features = build_features(
        demand, weather, all_regions(), spec.train_start, window.end, config=spec.feature_config
    )
    first_forecast = window.start - timedelta(days=spec.burn_in_days if spec.conformal else 0)
    report = check_point_in_time(features)
    if not report.ok:
        raise AssertionError(f"leakage in features: {report.violating_features}")
    leakage = {
        "rows_checked": report.rows_checked,
        "cells_checked": report.cells_checked,
        "origins_checked": report.origins_checked,
        "violations": report.violations,
    }
    cfg = BacktestConfig(
        start=first_forecast,
        end=window.end,
        train_start=spec.train_start,
        # training actuals must be published before the first issue time under this protocol
        gap_days=spec.feature_config.protocol.recent_day_offset,
    )
    result = run_backtest(features, factories(spec.models, features), cfg)
    actuals = features.select("ba_code", "hour_ending_utc", "y")
    calibration = _add_conformal(result, actuals, spec, cfg.gap_days) if spec.conformal else {}
    result.forecasts = result.forecasts.filter(pl.col("target_day") >= window.start)
    config, overall, point = _score_and_write(
        settings,
        out,
        spec,
        window=window,
        result=result,
        features=features,
        leakage=leakage,
        calibration=calibration,
    )
    if spec.split == "test":
        (settings.reports_dir / TEST_LOCK).write_text(json.dumps({"run_id": run_id, "at": run_id}))
    _log_mlflow(settings, run_id, config=config, overall=overall, point=point, out=out)
    log.info("run.done", run_id=run_id, out=str(out))
    return out


def _log_mlflow(
    settings: Settings,
    run_id: str,
    *,
    config: dict[str, Any],
    overall: pl.DataFrame,
    point: pl.DataFrame,
    out: Path,
) -> None:
    try:
        import mlflow  # noqa: PLC0415 - ml extra
    except ImportError:  # pragma: no cover - tracking is optional
        log.warning("mlflow.missing")
        return
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    mlflow.set_tracking_uri(f"sqlite:///{(settings.data_dir / 'mlflow.db').resolve()}")
    mlflow.set_experiment(f"gridcast-{config['split']}")
    for row in overall.iter_rows(named=True):
        with mlflow.start_run(run_name=f"{run_id}:{row['model']}"):
            mlflow.set_tags({"run_id": run_id, "model": row["model"], "git_sha": config["git_sha"]})
            mlflow.log_params(
                {
                    "split": config["split"],
                    "train_start": config["train_start"],
                    "population_weighted": config["feature_config"]["population_weighted"],
                    "refits": config["refits"],
                }
            )
            mlflow.log_metrics(
                {
                    "mape": row["mape"],
                    "mae": row["mae"],
                    "rmse": row["rmse"],
                    "bias_pct": row["bias_pct"],
                }
            )
            per_ba = point.filter(pl.col("model") == row["model"])
            mlflow.log_metrics(
                {f"mape_{r['ba_code']}": r["mape"] for r in per_ba.iter_rows(named=True)}
            )
            mlflow.log_artifact(str(out / "summary.md"))


def spec_as_dict(spec: RunSpec) -> dict[str, Any]:
    """Serialisable view of a spec (for logs)."""
    d = asdict(spec)
    d["feature_config"] = {"population_weighted": spec.feature_config.population_weighted}
    return d


def rescore(settings: Settings, run_id: str, n_boot: int | None = None) -> Path:
    """Recompute every metric and the summary of a finished run from its saved forecasts.

    Forecasts are never touched (they are the run's immutable output); only derived files are
    rewritten, and ``config.json`` records when that happened.
    """
    ensure_offline(settings, "rescoring a run")
    out = settings.reports_dir / "runs" / run_id
    cfg = json.loads((out / "config.json").read_text())
    forecasts = pl.read_parquet(out / "forecasts.parquet")
    protocol = ProtocolConfig.model_validate(cfg["feature_config"]["protocol"])
    spec = RunSpec(
        split=cfg["split"],
        models=tuple(cfg["models"]),
        train_start=date.fromisoformat(cfg["train_start"]),
        feature_config=FeatureConfig(
            protocol=protocol, population_weighted=cfg["feature_config"]["population_weighted"]
        ),
        n_boot=n_boot or cfg["n_boot"],
        conformal=bool(cfg.get("conformal")),
    )
    window = Window(
        start=date.fromisoformat(cfg["window"][0]), end=date.fromisoformat(cfg["window"][1])
    )
    demand = read_demand(settings.warehouse_path)
    weather = read_weather(settings.warehouse_path)
    features = build_features(
        demand, weather, all_regions(), spec.train_start, window.end, config=spec.feature_config
    )
    result = BacktestResult(
        forecasts=forecasts,
        refits=cfg["refits"],
        fit_seconds=cfg["fit_seconds"],
        train_gap_checks=cfg["train_gap_checks"],
        null_forecasts=cfg.get("null_forecasts", {}),
    )
    config, _, _ = _score_and_write(
        settings,
        out,
        spec,
        window=window,
        result=result,
        features=features,
        leakage=cfg["leakage"],
        calibration=cfg.get("conformal", {}),
    )
    config["rescored_at"] = datetime.now(UTC).isoformat()
    config["git_sha"] = cfg.get("git_sha", config["git_sha"])
    (out / "config.json").write_text(json.dumps(config, indent=2, default=str))
    return out


def combine_runs(settings: Settings, run_ids: list[str], tag: str) -> Path:
    """Merge the forecasts of several runs over the same split/window/protocol, then rescore.

    Lets models trained in separate processes (e.g. LightGBM and N-HiTS) be compared on one
    common set of hours with one set of CIs. Benchmark rows present in several runs are
    de-duplicated (they are deterministic).
    """
    ensure_offline(settings, "combining runs")
    configs = [
        json.loads((settings.reports_dir / "runs" / r / "config.json").read_text()) for r in run_ids
    ]
    keys = {
        (
            c["split"],
            tuple(c["window"]),
            json.dumps(c["feature_config"], sort_keys=True),
            c["train_start"],
        )
        for c in configs
    }
    if len(keys) != 1:
        raise ValueError(f"runs differ in split/window/protocol/train_start: {keys}")
    frames = [
        pl.read_parquet(settings.reports_dir / "runs" / r / "forecasts.parquet") for r in run_ids
    ]
    merged = pl.concat(frames).unique(
        subset=["ba_code", "hour_ending_utc", "model", "issued_at"], keep="first"
    )
    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + f"-{tag}"
    out = settings.reports_dir / "runs" / run_id
    out.mkdir(parents=True)
    merged.write_parquet(out / "forecasts.parquet")
    base = dict(configs[0])
    models: list[str] = []
    for c in configs:
        models += [m for m in c["models"] if m not in models]
    fit_seconds: dict[str, float] = {}
    conformal: dict[str, Any] = {}
    for c in configs:
        fit_seconds.update(c["fit_seconds"])
        conformal.update(c.get("conformal", {}))
    base.update(
        {
            "run_id": run_id,
            "models": models,
            "fit_seconds": fit_seconds,
            "conformal": conformal,
            "combined_from": run_ids,
        }
    )
    (out / "config.json").write_text(json.dumps(base, indent=2, default=str))
    return rescore(settings, run_id)
