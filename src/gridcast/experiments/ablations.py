"""Ablations (DESIGN section 5): one change at a time against the production configuration.

Each variant is a full validation backtest of LightGBM with one knob changed. Variants are compared
with the *baseline variant* on paired days: skill = 1 - MAE_variant / MAE_baseline, with a
moving-block bootstrap CI and a Diebold-Mariano test, per BA and pooled.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import polars as pl
import structlog

from gridcast.core.domain import ProtocolConfig
from gridcast.core.regions import all_regions
from gridcast.core.settings import Settings, ensure_offline
from gridcast.evaluation.backtest import BacktestConfig, run_backtest
from gridcast.evaluation.metrics import point_metrics, score
from gridcast.evaluation.stats import bootstrap_skill, diebold_mariano
from gridcast.features.build import FeatureConfig, build_features
from gridcast.models.base import Forecaster
from gridcast.models.gbm import LightGBMForecaster
from gridcast.warehouse.duck import read_demand, read_weather

log = structlog.get_logger(__name__)


@dataclass(frozen=True)
class Variant:
    """One ablation arm."""

    name: str
    description: str
    feature_config: FeatureConfig = field(default_factory=FeatureConfig)
    train_start: date = date(2021, 4, 1)
    factory: Callable[[], Forecaster] = LightGBMForecaster


def default_variants() -> list[Variant]:
    """Baseline first; every other arm changes exactly one thing."""
    base = Variant("baseline", "global LightGBM, unweighted city-mean weather, realtime protocol")
    return [
        base,
        replace(
            base,
            name="population_weighted_weather",
            description="population-weighted mean over cities",
            feature_config=FeatureConfig(population_weighted=True),
        ),
        replace(
            base,
            name="per_ba_models",
            description="one LightGBM per BA instead of one global",
            factory=lambda: LightGBMForecaster(per_ba=True),
        ),
        replace(
            base,
            name="short_history",
            description="training from 2022-07-01 instead of 2021-04-01",
            train_start=date(2022, 7, 1),
        ),
        replace(
            base,
            name="bulk_latency",
            description="demand only to the end of D-3 (keyless live feed)",
            feature_config=FeatureConfig(protocol=ProtocolConfig.bulk()),
        ),
    ]


def _daily_abs(scored: pl.DataFrame) -> pl.DataFrame:
    return scored.group_by("ba_code", "target_day").agg(
        pl.col("abs_err").sum().alias("abs_sum"), pl.len().alias("n")
    )


def run_ablations(
    settings: Settings, variants: list[Variant], start: date, end: date, n_boot: int = 1000
) -> Path:
    """Run every variant over [start, end]; write ``reports/ablations/<id>/summary.md``."""
    ensure_offline(settings, "ablations")
    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    out = settings.reports_dir / "ablations" / run_id
    out.mkdir(parents=True)
    demand = read_demand(settings.warehouse_path)
    weather = read_weather(settings.warehouse_path)
    daily: dict[str, pl.DataFrame] = {}
    overall: list[dict[str, Any]] = []
    for v in variants:
        features = build_features(
            demand,
            weather,
            all_regions(),
            min(v.train_start, date(2021, 4, 1)),
            end,
            config=v.feature_config,
        )
        cfg = BacktestConfig(
            start=start,
            end=end,
            train_start=v.train_start,
            gap_days=v.feature_config.protocol.recent_day_offset,
        )
        result = run_backtest(features, {v.name: v.factory}, cfg)
        scored = score(result.forecasts, features.select("ba_code", "hour_ending_utc", "y"))
        daily[v.name] = _daily_abs(scored)
        m = point_metrics(scored, by=("model",)).row(0, named=True)
        overall.append(
            {
                "variant": v.name,
                "description": v.description,
                "mape": m["mape"],
                "mae": m["mae"],
                "hours": m["hours"],
                "seconds": sum(result.fit_seconds.values()),
            }
        )
        log.info("ablation.done", variant=v.name, mape=m["mape"])
    base_name = variants[0].name
    rows: list[dict[str, Any]] = []
    for v in variants[1:]:
        for ba in [*sorted(daily[base_name]["ba_code"].unique().to_list()), "ALL"]:
            a = daily[v.name] if ba == "ALL" else daily[v.name].filter(pl.col("ba_code") == ba)
            b = (
                daily[base_name]
                if ba == "ALL"
                else daily[base_name].filter(pl.col("ba_code") == ba)
            )
            paired = a.join(b, on=["ba_code", "target_day"], suffix="_b").filter(
                pl.col("n") == pl.col("n_b")
            )
            if ba == "ALL":
                paired = paired.group_by("target_day").agg(
                    pl.col("abs_sum").sum(), pl.col("abs_sum_b").sum(), pl.col("n").sum()
                )
            paired = paired.sort("target_day")
            x = paired["abs_sum"].to_numpy().astype(float)
            y = paired["abs_sum_b"].to_numpy().astype(float)
            ci = bootstrap_skill(x, y, n_boot=n_boot, seed=17)
            dm = diebold_mariano(x / paired["n"].to_numpy(), y / paired["n"].to_numpy())
            rows.append(
                {
                    "variant": v.name,
                    "ba_code": ba,
                    "days": paired.height,
                    "skill_vs_baseline": ci.estimate,
                    "low": ci.low,
                    "high": ci.high,
                    "dm_p": dm.p_value,
                }
            )
    comp = pl.DataFrame(rows)
    comp.write_csv(out / "comparisons.csv")
    pl.DataFrame(overall).write_csv(out / "overall.csv")
    (out / "config.json").write_text(
        json.dumps(
            {
                "run_id": run_id,
                "window": [str(start), str(end)],
                "variants": [
                    {
                        "name": v.name,
                        "description": v.description,
                        "train_start": str(v.train_start),
                    }
                    for v in variants
                ],
            },
            indent=2,
        )
    )
    (out / "summary.md").write_text(_render(run_id, start, end, overall, comp))
    return out


def _render(
    run_id: str, start: date, end: date, overall: list[dict[str, Any]], comp: pl.DataFrame
) -> str:
    lines = [
        f"# Ablations {run_id}",
        "",
        f"Validation target days {start} → {end}. Each arm is global LightGBM with one change; "
        "skill = 1 - MAE_arm / MAE_baseline on paired days (positive = the change helps), "
        "95 % moving-block bootstrap CI, Diebold-Mariano p.",
        "",
        "| variant | change | MAPE % | fit s |",
        "|---|---|---|---|",
    ]
    for r in overall:
        lines.append(
            f"| {r['variant']} | {r['description']} | {r['mape']:.3f} | {r['seconds']:.0f} |"
        )
    lines += [
        "",
        "## Pooled over all BAs",
        "",
        "| variant | skill vs baseline | 95 % CI | DM p |",
        "|---|---|---|---|",
    ]
    for r in comp.filter(pl.col("ba_code") == "ALL").iter_rows(named=True):
        lines.append(
            f"| {r['variant']} | {r['skill_vs_baseline']:+.4f} | "
            f"[{r['low']:+.4f}, {r['high']:+.4f}] | {r['dm_p']:.2g} |"
        )
    lines += [
        "",
        "## Per BA",
        "",
        "| variant | BA | skill | 95 % CI | DM p |",
        "|---|---|---|---|---|",
    ]
    for r in (
        comp.filter(pl.col("ba_code") != "ALL").sort("variant", "ba_code").iter_rows(named=True)
    ):
        lines.append(
            f"| {r['variant']} | {r['ba_code']} | {r['skill_vs_baseline']:+.4f} | "
            f"[{r['low']:+.4f}, {r['high']:+.4f}] | {r['dm_p']:.2g} |"
        )
    return "\n".join(lines) + "\n"
