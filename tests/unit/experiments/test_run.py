from __future__ import annotations

import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import numpy as np
import polars as pl
import pytest

from gridcast.core.settings import Settings
from gridcast.evaluation.metrics import score
from gridcast.experiments.run import TEST_LOCK, SplitLockedError, comparisons, guard_test_split


def test_validation_split_is_never_guarded(tmp_path: Path) -> None:
    guard_test_split(Settings(base_dir=tmp_path), "validation", confirmed=False)


def test_test_split_needs_confirmation_and_runs_once(tmp_path: Path) -> None:
    settings = Settings(base_dir=tmp_path)
    with pytest.raises(SplitLockedError, match="one-time"):
        guard_test_split(settings, "test", confirmed=False)
    guard_test_split(settings, "test", confirmed=True)  # allowed the first time
    settings.reports_dir.mkdir(parents=True)
    (settings.reports_dir / TEST_LOCK).write_text(json.dumps({"run_id": "x"}))
    with pytest.raises(SplitLockedError, match="already evaluated"):
        guard_test_split(settings, "test", confirmed=True)


def _scored(days: int = 60) -> pl.DataFrame:
    rng = np.random.default_rng(0)
    rows, acts = [], []
    for d in range(days):
        day = date(2024, 1, 1) + timedelta(days=d)
        for h in range(24):
            t = datetime(2024, 1, 1, tzinfo=UTC) + timedelta(days=d, hours=h + 1)
            y = 1000.0
            acts.append({"ba_code": "X", "hour_ending_utc": t, "y": y})
            for model, noise in (("good", 10), ("operator", 30), ("operator_debiased", 20)):
                rows.append(
                    {
                        "ba_code": "X",
                        "target_day": day,
                        "hour_ending_utc": t,
                        "model": model,
                        "yhat": y + rng.normal(0, noise),
                    }
                )
    return score(pl.DataFrame(rows), pl.DataFrame(acts))


def test_comparisons_report_skill_ci_and_dm_per_reference() -> None:
    comps = comparisons(_scored(), ("operator", "operator_debiased", "good"), n_boot=200)
    assert set(comps["reference"]) == {"operator", "operator_debiased"}
    vs_op = comps.filter(pl.col("reference") == "operator").row(0, named=True)
    assert vs_op["days"] == 60
    assert vs_op["skill_low"] > 0.5  # 10 vs 30 noise: ~2/3 skill
    assert vs_op["dm_p"] < 1e-6
