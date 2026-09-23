from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import polars as pl
import pytest

from gridcast.live.store import DuplicateForecastError, ForecastStore

ISSUED = datetime(2025, 7, 14, 14, tzinfo=UTC)


def _batch(model: str = "m") -> pl.DataFrame:
    hours = [datetime(2025, 7, 15, 5, tzinfo=UTC) + timedelta(hours=h) for h in range(24)]
    return pl.DataFrame(
        {
            "ba_code": "PJM",
            "target_day": date(2025, 7, 15),
            "hour_ending_utc": hours,
            "issued_at": ISSUED,
            "model": model,
            "yhat": [100.0] * 24,
            "q10": [90.0] * 24,
            "q90": [110.0] * 24,
            "q025": [80.0] * 24,
            "q975": [120.0] * 24,
        },
        schema_overrides={
            "hour_ending_utc": pl.Datetime("us", "UTC"),
            "issued_at": pl.Datetime("us", "UTC"),
        },
    )


def test_append_and_read_back(tmp_path: Path) -> None:
    store = ForecastStore(tmp_path / "s.duckdb")
    assert (
        store.append(
            _batch(), created_at=ISSUED - timedelta(hours=1), protocol="bulk", model_version="3"
        )
        == 24
    )
    rows = store.read("ba_code = ?", ["PJM"])
    assert rows.height == 24 and not rows["late"].any()
    assert rows["model_version"].unique().to_list() == ["3"]


def test_store_is_immutable(tmp_path: Path) -> None:
    store = ForecastStore(tmp_path / "s.duckdb")
    store.append(_batch(), created_at=ISSUED, protocol="bulk", model_version="1")
    with pytest.raises(DuplicateForecastError):
        store.append(_batch(), created_at=ISSUED, protocol="bulk", model_version="2")
    assert store.count() == 24  # the failed insert wrote nothing
    assert store.read()["model_version"].unique().to_list() == ["1"]


def test_late_forecasts_are_flagged_not_hidden(tmp_path: Path) -> None:
    store = ForecastStore(tmp_path / "s.duckdb")
    store.append(
        _batch("late_model"),
        created_at=ISSUED + timedelta(minutes=5),
        protocol="bulk",
        model_version="1",
    )
    assert store.read()["late"].all()


def test_contract_rejects_forecasts_issued_after_their_hour(tmp_path: Path) -> None:
    store = ForecastStore(tmp_path / "s.duckdb")
    bad = _batch().with_columns(pl.lit(datetime(2025, 7, 16, tzinfo=UTC)).alias("issued_at"))
    with pytest.raises(Exception, match="issued_before_target"):
        store.append(bad, created_at=ISSUED, protocol="bulk", model_version="1")
