"""Generate ``reports/data_profile.md`` from the warehouse and raw manifests.

Every number in the report is computed here at generation time; the prose only frames them.
Findings that depend on thresholds say which threshold they use.
"""

from __future__ import annotations

import json
from datetime import UTC, date, datetime
from pathlib import Path

import duckdb
import polars as pl

from gridcast.core.settings import Settings
from gridcast.warehouse.duck import connect

ACCURACY_SQL = """
    select ba_code, year(local_date) as year,
           100 * avg(abs(operator_forecast_mw - demand_mw) / demand_mw) as mape,
           100 * avg((operator_forecast_mw - demand_mw) / demand_mw) as bias
    from fct_demand_hourly
    where demand_mw > 0 and operator_forecast_mw is not null
    group by all
"""


def _md_table(frame: pl.DataFrame, float_fmt: str = "{:.2f}") -> str:
    cols = frame.columns
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for row in frame.iter_rows():
        cells = []
        for v in row:
            if v is None:
                cells.append("—")
            elif isinstance(v, float):
                cells.append(float_fmt.format(v))
            else:
                cells.append(str(v))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def _pivot_years(frame: pl.DataFrame, value: str) -> pl.DataFrame:
    wide = frame.pivot(on="year", index="ba_code", values=value, sort_columns=True)
    return wide.sort("ba_code").rename({c: str(c) for c in wide.columns})


def _raw_inventory(settings: Settings) -> pl.DataFrame:
    rows = []
    for source in ("eia", "weather"):
        manifest = settings.raw_dir / source / "manifest.jsonl"
        if not manifest.exists():
            continue
        latest: dict[str, dict[str, object]] = {}
        for line in manifest.read_text("utf-8").splitlines():
            entry = json.loads(line)
            latest[entry["key"]] = entry
        kinds: dict[str, list[dict[str, object]]] = {}
        for key, entry in latest.items():
            kind = source if source == "eia" else f"weather/{key.split('/')[0]}"
            kinds.setdefault(kind, []).append(entry)
        for kind, entries in sorted(kinds.items()):
            rows.append(
                {
                    "source": kind,
                    "files": len(entries),
                    "closed": sum(bool(e["closed"]) for e in entries),
                    "MB": sum(int(str(e["bytes"])) for e in entries) / 1e6,
                }
            )
    return pl.DataFrame(rows)


def _mean(series: pl.Series) -> float:
    value = series.mean()
    return float(value) if isinstance(value, int | float) else float("nan")


def _first_date(frame: pl.DataFrame, column: str) -> date | None:
    values = [v for v in frame[column].to_list() if isinstance(v, date)] if frame.height else []
    return min(values) if values else None


def _q(con: duckdb.DuckDBPyConnection, sql: str) -> pl.DataFrame:
    return con.sql(sql).pl()


def build_profile(settings: Settings) -> str:
    """Render the data-profile report as Markdown."""
    generated = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    with connect(settings.warehouse_path) as con:
        rows = _q(
            con,
            """select ba_code, count(*) as hours, min(local_date) as first_day,
                      max(local_date) as last_day,
                      100 * avg((demand_mw is not null)::int) as target_pct,
                      100 * avg((operator_forecast_mw is not null)::int) as operator_pct
               from fct_demand_hourly group by 1 order by 1""",
        )
        coverage = _q(
            con,
            """select ba_code, year(local_date) as year,
                      100 * avg((demand_mw is not null)::int) as pct
               from fct_demand_hourly group by all""",
        )
        cleaning = _q(con, "select * from dq_cleaning_log order by ba_code")
        accuracy = _q(con, ACCURACY_SQL)
        ciso_hours = _q(
            con,
            """select hour_number as hour,
                      100 * avg((operator_forecast_mw - demand_mw) / demand_mw) as bias_pct,
                      avg(demand_mw) as demand_mw, avg(operator_forecast_mw) as operator_mw
               from fct_demand_hourly
               where ba_code = 'CISO' and demand_mw > 0 and operator_forecast_mw is not null
                 and local_date >= date '2025-01-01' and hour_number <= 24
               group by 1 order by 1""",
        )
        swpp_months = _q(
            con,
            """select strftime(local_date, '%Y-%m') as month,
                      100 * avg((operator_forecast_mw - demand_mw) / demand_mw) as bias_pct,
                      100 * avg(abs(operator_forecast_mw - demand_mw) / demand_mw) as mape
               from fct_demand_hourly
               where ba_code = 'SWPP' and demand_mw > 0 and operator_forecast_mw is not null
                 and local_date between date '2024-11-01' and date '2025-08-31'
               group by 1 order by 1""",
        )
        weather = _q(
            con,
            """select ba_code,
                      min(hour_ending_utc) filter (where temperature_c is not null)::date
                          as first_temperature,
                      min(hour_ending_utc) filter (where dew_point_c is not null)::date
                          as first_other_vars,
                      max(hour_ending_utc)::date as last_hour,
                      count(*) filter (where temperature_c is not null) as temperature_hours,
                      100 * avg((n_cities = (select n_cities from ref.regions r
                                             where r.ba_code = w.ba_code))::int)
                          as all_cities_pct
               from fct_weather_forecast_hourly w group by 1 order by 1""",
        )
        weather_gaps = _q(
            con,
            """with expected as (
                   select ba_code, unnest(generate_series(
                       timestamptz '2021-03-26 00:00:00+00',
                       (select max(hour_ending_utc) from fct_weather_forecast_hourly),
                       interval 1 hour)) as h
                   from ref.regions)
               select e.ba_code, count(*) as expected_hours,
                      count(w.temperature_c) as with_temperature,
                      100 * count(w.temperature_c) / count(*) as pct
               from expected e left join fct_weather_forecast_hourly w
                 on w.ba_code = e.ba_code and w.hour_ending_utc = e.h
               group by 1 order by 1""",
        )

    with connect(settings.warehouse_path) as con:
        long_gaps = _q(
            con,
            """with hours as (
                   select ba_code, hour_ending_utc as h from fct_weather_forecast_hourly
                   where temperature_c is not null),
               steps as (
                   select ba_code, h,
                          lag(h) over (partition by ba_code order by h) as prev
                   from hours)
               select min(prev + interval 1 hour)::date as gap_start,
                      max(h - interval 1 hour)::date as gap_end,
                      max(epoch(h - prev) / 3600 - 1)::int as missing_hours,
                      count(distinct ba_code) as bas
               from steps
               where h - prev > interval 24 hour
               group by prev, h
               order by gap_start""",
        )
    ciso = accuracy.filter(pl.col("ba_code") == "CISO").sort("year")
    ciso_midday = ciso_hours.filter(pl.col("hour").is_between(10, 15))
    ciso_nonsolar = ciso_hours.filter(~pl.col("hour").is_between(8, 17))
    swpp_before = _mean(swpp_months.filter(pl.col("month") <= "2025-04")["bias_pct"])
    swpp_after = _mean(swpp_months.filter(pl.col("month") >= "2025-05")["bias_pct"])
    first_temp = _first_date(weather, "first_temperature")
    first_other = _first_date(weather, "first_other_vars")

    ciso_first, ciso_last = ciso.row(0, named=True), ciso.row(-1, named=True)
    parts = [
        "# GridCast data profile",
        "",
        f"Generated {generated} by `gridcast profile` from `{settings.warehouse_path.name}` "
        "and the raw-file manifests. Do not edit by hand.",
        "",
        "## 1. Raw inventory",
        "",
        _md_table(_raw_inventory(settings), "{:.1f}"),
        "",
        "## 2. Demand rows and coverage per BA",
        "",
        "`target_pct` = share of hours with a usable reported demand (the scoring target); "
        "`operator_pct` = share with a usable operator day-ahead forecast.",
        "",
        _md_table(rows),
        "",
        "Target coverage (%) by year:",
        "",
        _md_table(_pivot_years(coverage, "pct"), "{:.1f}"),
        "",
        "## 3. Cleaning rules and rows affected",
        "",
        "Rules are defined in `transform/models/intermediate/int_eia__demand_cleaned.sql` "
        "(R3/R4 band: 0.5x-1.6x the centred 7-day median).",
        "",
        _md_table(cleaning, "{:.0f}"),
        "",
        "## 4. Operator day-ahead forecast accuracy (the benchmark)",
        "",
        "MAPE (%) of the operator forecast against cleaned reported demand, by year:",
        "",
        _md_table(_pivot_years(accuracy, "mape")),
        "",
        "Mean signed error (%) (positive = operator over-forecasts):",
        "",
        _md_table(_pivot_years(accuracy, "bias")),
        "",
        "## 5. Findings",
        "",
        "### 5.1 CISO: a growing midday under-forecast (open)",
        "",
        f"CISO's operator MAPE rose from {ciso_first['mape']:.2f} % ({ciso_first['year']}) to "
        f"{ciso_last['mape']:.2f} % ({ciso_last['year']}), with the signed error moving from "
        f"{ciso_first['bias']:+.2f} % to {ciso_last['bias']:+.2f} %. Since 2025 the bias is "
        f"{_mean(ciso_midday['bias_pct']):+.1f} % in hours 10-15 but "
        f"{_mean(ciso_nonsolar['bias_pct']):+.1f} % outside hours 8-17:",
        "",
        _md_table(ciso_hours, "{:.1f}"),
        "",
        "The error is concentrated in solar hours and grows year over year, which fits a "
        "definitional mismatch between CAISO's load forecast and EIA's reported demand (for "
        "example battery charging or behind-the-meter effects counted on one side only). "
        "**This is a hypothesis, not a finding**: EIA-930's battery-storage column is empty for "
        "CISO, so it cannot be tested from this data. Consequence for GridCast: raw 'skill vs "
        "operator' in CISO would flatter our models, so every results table also reports skill "
        "against a *bias-corrected operator* benchmark (trailing 28-day mean error per hour of "
        "day, using only data available at issue time).",
        "",
        "### 5.2 SWPP: a step change in May 2025",
        "",
        f"SWPP's operator bias averaged {swpp_before:+.1f} % from Nov 2024 to Apr 2025 and "
        f"{swpp_after:+.1f} % from May to Aug 2025 - a level shift between two consecutive "
        "months, not a gradual drift:",
        "",
        _md_table(swpp_months),
        "",
        "A step of this size is characteristic of a reporting or definition change rather than "
        "a forecasting failure. The same bias-corrected benchmark applies; SWPP results after "
        "2025-05 are flagged in every table.",
        "",
        "### 5.3 Archived weather forecasts",
        "",
        f"The first archived day-2 temperature forecast on disk is {first_temp}; the other "
        f"variables (dew point, humidity, cloud, wind, radiation) begin {first_other}. "
        + (
            "Because they start later, models use forecast temperature only (ADR-0004) and the "
            "richer variables are a post-2024 ablation."
            if first_temp and first_other and first_other > first_temp
            else "Both start together in the data downloaded so far; the full archive "
            "(temperature from 2021-03-25, other variables from 2024-01-20 per the provider) "
            "is still being fetched - regenerate this report when ingestion completes."
        ),
        "",
        _md_table(weather, "{:.1f}"),
        "",
        "Hours with a BA-level forecast temperature since 2021-03-26 (gaps are what the "
        "downloader has not fetched yet, or upstream holes):",
        "",
        _md_table(weather_gaps, "{:.1f}"),
        "",
        "### 5.4 Gaps of more than 24 hours in the archived forecasts",
        "",
        "Holes in the provider's archive (`bas` = how many BAs share the same dates). Models "
        "see missing weather as missing (LightGBM) or median-imputed (ridge); hours in a gap are "
        "still scored, so the gap costs accuracy rather than hiding it.",
        "",
        _md_table(long_gaps) if long_gaps.height else "None.",
        "",
    ]
    return "\n".join(parts)


def write_profile(settings: Settings) -> Path:
    """Write the report and return its path."""
    path = settings.reports_dir / "data_profile.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(build_profile(settings), encoding="utf-8")
    return path
