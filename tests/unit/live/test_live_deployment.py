"""The free GitHub Actions + Pages deployment: store, artefact, live-mode guards, site."""

from __future__ import annotations

import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import polars as pl
import pytest

from gridcast.core.settings import LiveModeError, Settings, ensure_offline
from gridcast.experiments.run import guard_test_split
from gridcast.live.artifact import ArtifactMismatchError, export_artifact, load_artifact
from gridcast.live.daily import LiveRunError, run_daily
from gridcast.live.issue import scorable
from gridcast.live.store import DuplicateForecastError, ParquetForecastStore
from gridcast.models.gbm import LightGBMForecaster
from gridcast.site.build import build_site
from tests.unit.live.test_store import ISSUED, _batch


def test_parquet_store_is_append_only(tmp_path: Path) -> None:
    store = ParquetForecastStore(tmp_path / "forecasts")
    assert store.append(_batch("lgbm_live"), ISSUED - timedelta(hours=1), "bulk", "3", "abc") == 24
    path = store.path_for(date(2025, 7, 15), "lgbm_live")
    before = path.read_bytes()
    with pytest.raises(DuplicateForecastError):
        store.append(_batch("lgbm_live"), ISSUED, "bulk", "4", "def")
    assert path.read_bytes() == before  # untouched
    rows = store.read()
    assert rows.height == 24 and rows["code_version"].unique().to_list() == ["abc"]
    assert not rows["late"].any() and store.has(date(2025, 7, 15), "lgbm_live")


def test_parquet_store_refuses_mixed_batches(tmp_path: Path) -> None:
    store = ParquetForecastStore(tmp_path)
    mixed = pl.concat([_batch("a"), _batch("b")])
    with pytest.raises(ValueError, match="one target day and model"):
        store.append(mixed, ISSUED, "bulk", "1")


def _fitted() -> LightGBMForecaster:
    model = LightGBMForecaster()
    model._heads = {"*": {}}  # enough to pickle; never used to predict here
    return model


def test_artifact_round_trip_and_tamper_detection(tmp_path: Path) -> None:
    manifest = export_artifact(_fitted(), "7", tmp_path, "2021-04-01", "2026-09-20")
    model, loaded = load_artifact(tmp_path)
    assert isinstance(model, LightGBMForecaster) and loaded.version == "7"
    (tmp_path / manifest.file).write_bytes(b"tampered")
    with pytest.raises(ArtifactMismatchError, match="sha256"):
        load_artifact(tmp_path)


def test_artifact_refuses_a_feature_list_that_no_longer_matches(tmp_path: Path) -> None:
    export_artifact(_fitted(), "7", tmp_path, "2021-04-01", "2026-09-20")
    raw = json.loads((tmp_path / "manifest.json").read_text())
    raw["features"] = [*raw["features"], "a_feature_the_code_does_not_build"]
    (tmp_path / "manifest.json").write_text(json.dumps(raw))
    with pytest.raises(ArtifactMismatchError, match="feature list"):
        load_artifact(tmp_path)


def test_artifact_refuses_a_different_feature_configuration(tmp_path: Path) -> None:
    export_artifact(_fitted(), "7", tmp_path, "2021-04-01", "2026-09-20")
    raw = json.loads((tmp_path / "manifest.json").read_text())
    raw["population_weighted"] = not raw["population_weighted"]
    (tmp_path / "manifest.json").write_text(json.dumps(raw))
    with pytest.raises(ArtifactMismatchError, match="population_weighted"):
        load_artifact(tmp_path)


def test_live_mode_refuses_every_offline_action(tmp_path: Path) -> None:
    live = Settings(base_dir=tmp_path, live_mode=True)
    for action in ("training", "ablations"):
        with pytest.raises(LiveModeError):
            ensure_offline(live, action)
    for split in ("validation", "test"):
        with pytest.raises(LiveModeError):
            guard_test_split(live, split, confirmed=True)  # not even with confirmation
    offline = Settings(base_dir=tmp_path)
    ensure_offline(offline, "training")  # no error offline


def test_daily_run_requires_live_mode(tmp_path: Path) -> None:
    with pytest.raises(LiveRunError, match="live mode"):
        run_daily(Settings(base_dir=tmp_path))


def test_live_scoring_never_covers_the_test_window(tmp_path: Path) -> None:
    settings = Settings(base_dir=tmp_path)
    rows = pl.DataFrame({"target_day": [settings.test.end, settings.test.end + timedelta(days=1)]})
    kept = scorable(rows, settings)
    assert kept["target_day"].to_list() == [settings.test.end + timedelta(days=1)]


def test_site_builds_from_files_only(tmp_path: Path) -> None:
    live = tmp_path / "live"
    ParquetForecastStore(live / "forecasts").append(_batch("lgbm_live"), ISSUED, "bulk", "3", "abc")
    (live / "status").mkdir(parents=True)
    (live / "status" / "latest.json").write_text(
        json.dumps(
            {
                "started_at": datetime(2026, 9, 24, 12, 30, tzinfo=UTC).isoformat(),
                "ok": True,
                "code_version": "abc",
                "model_version": "3",
                "target_day": "2025-07-15",
                "stages": [],
            }
        )
    )
    page = build_site(live, tmp_path / "reports", tmp_path / "site")
    text = page.read_text()
    assert "last run: ok" in text and "plotly" in text
    data = json.loads((tmp_path / "site" / "data.json").read_text())
    assert data["latest"]["PJM"]["model_version"] == "3" and len(data["latest"]["PJM"]["t"]) == 24
    assert "</script><script>" not in text.split("const D = ")[1].split(";\n")[0]
