"""Feature-drift monitoring with Evidently.

Compares the model-input distribution of the most recent ``current_days`` against the same weeks
one year earlier (seasonally matched), for BA-agnostic features (ratios and weather, not raw MW,
which drift by design with load growth). Writes an HTML report and a JSON summary for Dagster.
"""

from __future__ import annotations

import json
import warnings
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

import polars as pl

from gridcast.core.regions import all_regions
from gridcast.core.settings import Settings
from gridcast.features.build import FeatureConfig, build_features
from gridcast.live.production import LIVE_PROTOCOL
from gridcast.models.gbm import GBM_FEATURES
from gridcast.warehouse.duck import read_demand, read_weather

MONITORED = tuple(f for f in GBM_FEATURES if f.endswith(("_ratio", "_c")) or f in {"cdd", "hdd"})


@dataclass(frozen=True)
class DriftSummary:
    """Headline of one drift report."""

    drifted_columns: int
    share: float
    columns_checked: int
    rows_reference: int
    rows_current: int
    html: Path


def drift_report(settings: Settings, today: date, current_days: int = 28) -> DriftSummary:
    """Write ``reports/monitoring/drift_<today>.html`` and a JSON summary; return the headline."""
    from evidently import Report  # noqa: PLC0415 - monitor extra
    from evidently.presets import DataDriftPreset  # noqa: PLC0415

    last = today - timedelta(days=LIVE_PROTOCOL.recent_day_offset)
    cur_start = last - timedelta(days=current_days - 1)
    # seasonally matched reference: exactly the same dates one year earlier, so a summer window
    # is not "drifted" merely for being summer (padding the window pulled in cooler weeks and
    # inflated temperature drift - found when the first report flagged every feature)
    ref_start = cur_start - timedelta(days=364)
    ref_end = last - timedelta(days=364)
    demand = read_demand(settings.warehouse_path, start=ref_start - timedelta(days=21))
    weather = read_weather(settings.warehouse_path, start=ref_start - timedelta(days=21))
    frame = build_features(
        demand,
        weather,
        all_regions(),
        ref_start,
        last,
        config=FeatureConfig(protocol=LIVE_PROTOCOL),
    )
    ref_rows = frame.filter(pl.col("target_day").is_between(ref_start, ref_end))
    cur_rows = frame.filter(pl.col("target_day") >= cur_start)
    # features that are structurally absent under the protocol (e.g. the partial day under
    # "bulk") or not yet available are skipped rather than silently emptying the comparison
    cols = [
        c
        for c in MONITORED
        if ref_rows[c].null_count() < ref_rows.height / 2
        and cur_rows[c].null_count() < cur_rows.height / 2
    ]
    if not cols:
        raise ValueError("no monitored feature has data in both windows")
    reference = ref_rows.select(cols).drop_nulls()
    current = cur_rows.select(cols).drop_nulls()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        snapshot = Report([DataDriftPreset()]).run(
            current_data=current.to_pandas(), reference_data=reference.to_pandas()
        )
    out = settings.reports_dir / "monitoring"
    out.mkdir(parents=True, exist_ok=True)
    html = out / f"drift_{today}.html"
    snapshot.save_html(str(html))
    headline = next(
        m["value"]
        for m in snapshot.dict()["metrics"]
        if m["metric_name"].startswith("DriftedColumnsCount")
    )
    summary = DriftSummary(
        drifted_columns=int(headline["count"]),
        share=float(headline["share"]),
        columns_checked=len(cols),
        rows_reference=reference.height,
        rows_current=current.height,
        html=html,
    )
    (out / f"drift_{today}.json").write_text(
        json.dumps(
            {**summary.__dict__, "html": str(html), "window": [str(cur_start), str(last)]}, indent=2
        )
    )
    return summary
