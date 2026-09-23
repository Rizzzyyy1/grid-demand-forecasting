"""Run the real dbt project against small synthetic raw files (no network, temp warehouse)."""

from __future__ import annotations

import csv
import json
import math
from datetime import date, timedelta
from pathlib import Path

import duckdb
import pytest

from gridcast.core import time as t
from gridcast.core.regions import get_region
from gridcast.core.settings import Settings
from gridcast.warehouse.dbt import run_dbt

pytestmark = pytest.mark.slow

HEADER = [
    "Balancing Authority",
    "Data Date",
    "Hour Number",
    "Local Time at End of Hour",
    "UTC Time at End of Hour",
    "Demand Forecast (MW)",
    "Demand (MW)",
    "Net Generation (MW)",
    "Demand (MW) (Adjusted)",
]
DAYS = [date(2025, 3, 5) + timedelta(days=i) for i in range(8)]  # spans the 2025-03-09 DST change
BAS = ("PJM", "MISO")


def _eia_rows() -> list[list[str]]:
    rows = []
    for code in BAS:
        tz = get_region(code).tz
        for day in DAYS:
            for n, instant in enumerate(t.hour_ending_instants(day, tz), start=1):
                local = t.to_local(instant, tz)
                demand = 50_000 + 8_000 * math.sin(n / 24 * 2 * math.pi)
                rows.append(
                    [
                        code,
                        day.strftime("%m/%d/%Y"),
                        str(n),
                        local.strftime("%m/%d/%Y %-I:%M:%S %p"),
                        instant.strftime("%m/%d/%Y %-I:%M:%S %p"),
                        f"{demand * 1.01:.0f}",
                        f"{demand:.0f}",
                        f"{demand:.0f}",
                        f"{demand:.0f}",
                    ]
                )
    return rows


def _write_raw(raw: Path, rows: list[list[str]]) -> None:
    (raw / "eia").mkdir(parents=True)
    with (raw / "eia" / "EIA930_BALANCE_2025_Jan_Jun.csv").open("w", newline="") as fh:
        writer = csv.writer(fh, quoting=csv.QUOTE_MINIMAL)
        writer.writerow(HEADER)
        writer.writerows(rows)
    start, end = DAYS[0] - timedelta(days=2), DAYS[-1] + timedelta(days=2)
    hours = int((end - start).days * 24)
    times = [f"{start + timedelta(hours=h):%Y-%m-%d}T{h % 24:02d}:00" for h in range(hours)]
    for code in BAS:
        for city in get_region(code).cities:
            hourly: dict[str, list[object]] = {"time": times}
            for var in (
                "temperature_2m",
                "dew_point_2m",
                "relative_humidity_2m",
                "cloud_cover",
                "wind_speed_10m",
                "shortwave_radiation",
            ):
                hourly[f"{var}_previous_day2"] = [10.0] * hours
            path = raw / "weather" / "forecast_d2" / code / city.slug / "2025-03.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps({"hourly": hourly}))


def _settings(tmp_path: Path) -> Settings:
    return Settings(base_dir=tmp_path)


def test_build_on_synthetic_raw_files(tmp_path: Path) -> None:
    _write_raw(tmp_path / "data" / "raw", _eia_rows())
    result = run_dbt(_settings(tmp_path), ["build", "--target-path", str(tmp_path / "target")])
    assert result.success, result.messages
    assert result.passed >= 40 and result.failed == 0
    # dbt ran in-process and still holds a read-write handle; match its configuration
    con = duckdb.connect(str(tmp_path / "data" / "warehouse.duckdb"))
    counts = dict(
        con.sql(
            "select local_date::varchar, count(*) from fct_demand_hourly where ba_code='PJM' group by 1"
        ).fetchall()
    )
    assert counts["2025-03-09"] == 23 and counts["2025-03-08"] == 24
    miso = con.sql(
        "select count(*) from fct_demand_hourly where ba_code='MISO' and local_date='2025-03-09'"
    ).fetchone()
    assert miso == (24,)  # fixed EST: no DST
    assert con.sql("select count(*) from fct_weather_forecast_hourly").fetchone()[0] > 0  # type: ignore[index]


def test_malformed_timestamp_fails_with_a_readable_error(tmp_path: Path) -> None:
    rows = _eia_rows()
    rows[5][4] = "13/45/2025 9:00:00 AM"  # impossible UTC timestamp
    _write_raw(tmp_path / "data" / "raw", rows)
    result = run_dbt(_settings(tmp_path), ["build", "--target-path", str(tmp_path / "target")])
    assert not result.success
    text = " ".join(result.messages)
    assert "stg_eia__balance" in text
    assert "13/45/2025" in text  # the offending value is named in the error
