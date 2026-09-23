from __future__ import annotations

import importlib.util
from pathlib import Path

import gridcast

ROOT = Path(gridcast.__file__).parents[2]
spec = importlib.util.spec_from_file_location("verify", ROOT / "scripts" / "verify_live_commit.py")
assert spec and spec.loader
verify = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verify)


def test_normal_daily_commit_is_allowed() -> None:
    lines = [
        "A\tforecasts/target=2026-09-26/lgbm_live.parquet",
        "M\tscores/leaderboard.csv",
        "M\tscores/daily.csv",
        "M\tstatus/latest.json",
    ]
    assert verify.check(lines, {}) == []


def test_rewriting_or_deleting_a_forecast_is_refused() -> None:
    assert verify.check(["M\tforecasts/target=2026-09-26/lgbm_live.parquet"], {})
    assert verify.check(["D\tforecasts/target=2026-09-26/lgbm_live.parquet"], {})
    assert verify.check(["R100\tforecasts/a.parquet\tforecasts/target=2026-09-26/x.parquet"], {})


def test_model_and_other_paths_are_refused() -> None:
    assert verify.check(["M\tmodel/manifest.json"], {})
    assert verify.check(["A\treports/TEST_SPLIT_EVALUATED.json"], {})
    assert verify.check(["A\tforecasts/target=2026-09-26/../../x.parquet"], {})


def test_large_files_are_refused() -> None:
    path = "forecasts/target=2026-09-26/lgbm_live.parquet"
    assert verify.check([f"A\t{path}"], {path: 5_000_000})
