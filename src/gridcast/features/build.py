"""Point-in-time feature matrix: one row per (BA, target day, target hour).

Every feature column ``f`` has a companion ``avail__f``: the latest instant at which any input to
``f`` became available, derived from the *source rows' own timestamps* (not from the offset the
code intended to use). ``check_point_in_time`` asserts ``avail__f <= issued_at`` for every cell,
so a join against the wrong rows is caught rather than trusted.

Availability rules (DESIGN section 3, ADR-0001, ADR-0004):

* demand for the hour ending at *h* counts as available at ``h + (issued_at - demand_cutoff)``
  for each origin, so exactly the hours ending at or before the protocol's cutoff are usable
  (06:00 on D-1 for the realtime protocol, midnight ending D-3 for the bulk protocol);
* a day-2 weather value valid at *T* is available at ``T - 42 h`` (predicted 48 h ahead, plus a
  6 h publication allowance);
* calendar facts are known in advance (``avail`` is null, meaning "always").

The operator's forecast is carried as ``operator_forecast_mw`` for benchmarking only; it is not in
``FEATURE_COLUMNS`` and a test enforces that it never becomes one.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date, timedelta

import polars as pl

from gridcast.core.calendar import holiday_dates
from gridcast.core.domain import BalancingAuthority, ProtocolConfig

AVAIL_PREFIX = "avail__"
WEATHER_AVAILABLE_OFFSET = timedelta(hours=-42)
COMFORT_TEMPERATURE_C = 18.0

CALENDAR_FEATURES = (
    "local_hour",
    "hour_number",
    "hours_in_day",
    "weekday",
    "is_weekend",
    "is_holiday",
    "is_day_after_holiday",
    "month",
    "doy_sin",
    "doy_cos",
)
DEMAND_FEATURES = (
    "level_7d_mw",
    "lag_recent_mw",
    "lag7_mw",
    "recent_peak_mw",
    "partial_day_mean_mw",
    "last_known_mw",
    "lag_recent_ratio",
    "lag7_ratio",
    "partial_day_ratio",
    "recent_peak_ratio",
)
WEATHER_FEATURES = (
    "temp_c",
    "cdd",
    "hdd",
    "temp_day_mean_c",
    "temp_day_max_c",
    "temp_day_min_c",
    "temp_spread_c",
    "temp_delta_7d_c",
    "temp_prev3h_c",
    "temp_recent_c",
    "temp_delta_recent_c",
)
FEATURE_COLUMNS: tuple[str, ...] = CALENDAR_FEATURES + DEMAND_FEATURES + WEATHER_FEATURES
KEY_COLUMNS = ("ba_code", "target_day", "hour_ending_utc", "issued_at")
BENCHMARK_COLUMNS = ("operator_forecast_mw",)
TARGET_COLUMN = "y"


@dataclass(frozen=True)
class FeatureConfig:
    """Knobs for ablations; defaults are the production configuration."""

    protocol: ProtocolConfig = field(default_factory=ProtocolConfig)
    # plain city mean: the population-weighted mean was significantly worse on validation
    # (reports/ablations/20260923T132504Z) - approximate weights let one metro dominate a BA
    population_weighted: bool = False

    @property
    def demand_publication_lag(self) -> timedelta:
        """Delay after which an hour's demand counts as published (4 h realtime, 34 h bulk)."""
        return self.protocol.publication_lag


# --------------------------------------------------------------------------- local time fields


def with_local_fields(demand: pl.DataFrame, regions: Sequence[BalancingAuthority]) -> pl.DataFrame:
    """Add ``local_hour`` (wall-clock hour at the *start* of the hour, 0-23) per BA clock."""
    parts = []
    for ba in regions:
        part = demand.filter(pl.col("ba_code") == ba.code)
        if part.is_empty():
            continue
        start_local = (pl.col("hour_ending_utc") - pl.duration(hours=1)).dt.convert_time_zone(
            ba.timezone
        )
        parts.append(part.with_columns(start_local.dt.hour().cast(pl.Int8).alias("local_hour")))
    if not parts:
        raise ValueError("no demand rows for the requested regions")
    return pl.concat(parts)


def target_hours(regions: Sequence[BalancingAuthority], start: date, end: date) -> pl.DataFrame:
    """Every hour-ending instant of local days ``start..end`` per BA (23/24/25 per day).

    Columns: ba_code, target_day, hour_ending_utc, hour_number, local_hour. Vectorised per BA:
    local midnights are localised with the BA's zone and the UTC hours between them enumerated.
    """
    days = pl.date_range(start, end, "1d", eager=True).alias("target_day")
    parts = []
    for ba in regions:
        frame = pl.DataFrame(days).with_columns(
            pl.lit(ba.code).alias("ba_code"),
            pl.col("target_day")
            .cast(pl.Datetime("us"))
            .dt.replace_time_zone(ba.timezone)
            .dt.convert_time_zone("UTC")
            .alias("_start"),
            (pl.col("target_day") + pl.duration(days=1))
            .cast(pl.Datetime("us"))
            .dt.replace_time_zone(ba.timezone)
            .dt.convert_time_zone("UTC")
            .alias("_end"),
        )
        frame = (
            frame.with_columns(
                pl.datetime_ranges(
                    pl.col("_start") + pl.duration(hours=1), pl.col("_end"), "1h"
                ).alias("hour_ending_utc")
            )
            .explode("hour_ending_utc", empty_as_null=False)
            .with_columns(
                pl.col("hour_ending_utc")
                .cum_count()
                .over("target_day")
                .cast(pl.Int32)
                .alias("hour_number"),
                (pl.col("hour_ending_utc") - pl.duration(hours=1))
                .dt.convert_time_zone(ba.timezone)
                .dt.hour()
                .cast(pl.Int8)
                .alias("local_hour"),
            )
        )
        parts.append(
            frame.select("ba_code", "target_day", "hour_ending_utc", "hour_number", "local_hour")
        )
    return pl.concat(parts)


def origins_frame(
    target_days: pl.DataFrame, regions: Sequence[BalancingAuthority], protocol: ProtocolConfig
) -> pl.DataFrame:
    """(ba_code, target_day) -> issued_at, demand_cutoff (UTC), per the BA's clock."""
    parts = []
    for ba in regions:
        days = target_days.filter(pl.col("ba_code") == ba.code)
        if days.is_empty():
            continue
        issue_day = pl.col("target_day") - pl.duration(days=1)
        cutoff_day = pl.col("target_day") - pl.duration(days=protocol.demand_cutoff_days_before)

        def at(t: object, day: pl.Expr, tz: str = ba.timezone) -> pl.Expr:
            local = day.cast(pl.Datetime("us")) + pl.duration(
                hours=t.hour,  # type: ignore[attr-defined]
                minutes=t.minute,  # type: ignore[attr-defined]
            )
            return local.dt.replace_time_zone(tz, non_existent="raise").dt.convert_time_zone("UTC")

        parts.append(
            days.with_columns(
                at(protocol.issue_time, issue_day).alias("issued_at"),
                at(protocol.demand_cutoff_time, cutoff_day).alias("demand_cutoff"),
            )
        )
    return pl.concat(parts)


# --------------------------------------------------------------------------- building blocks


def _same_hour_lag(hours: pl.DataFrame, days: int, name: str, lag: timedelta) -> pl.DataFrame:
    """Demand at the same local wall-clock hour ``days`` earlier (mean over a repeated DST hour)."""
    return (
        hours.with_columns((pl.col("local_date") + pl.duration(days=days)).alias("target_day"))
        .group_by("ba_code", "target_day", "local_hour")
        .agg(
            pl.col("demand_filled_mw").mean().alias(name),
            (pl.col("hour_ending_utc").max() + lag).alias(AVAIL_PREFIX + name),
        )
    )


def _daily(hours: pl.DataFrame) -> pl.DataFrame:
    return hours.group_by("ba_code", "local_date").agg(
        pl.col("demand_filled_mw").mean().alias("day_mean"),
        pl.col("demand_filled_mw").max().alias("day_peak"),
        pl.col("hour_ending_utc").max().alias("day_last_hour"),
        pl.col("demand_filled_mw").count().alias("day_hours"),
    )


def _level(daily: pl.DataFrame, lag: timedelta, recent: int) -> pl.DataFrame:
    """Mean of daily means over the 7 local days ending at D-``recent``, keyed by target day D."""
    windows = []
    for offset in range(recent, recent + 7):
        windows.append(
            daily.select(
                "ba_code",
                (pl.col("local_date") + pl.duration(days=offset)).alias("target_day"),
                "day_mean",
                "day_last_hour",
            )
        )
    return (
        pl.concat(windows)
        .group_by("ba_code", "target_day")
        .agg(
            pl.col("day_mean").mean().alias("level_7d_mw"),
            (pl.col("day_last_hour").max() + lag).alias(AVAIL_PREFIX + "level_7d_mw"),
            pl.col("day_mean").count().alias("_level_days"),
        )
        .filter(pl.col("_level_days") >= 5)
        .drop("_level_days")
    )


def _recent_peak(daily: pl.DataFrame, lag: timedelta, recent: int) -> pl.DataFrame:
    return daily.select(
        "ba_code",
        (pl.col("local_date") + pl.duration(days=recent)).alias("target_day"),
        pl.col("day_peak").alias("recent_peak_mw"),
        (pl.col("day_last_hour") + lag).alias(AVAIL_PREFIX + "recent_peak_mw"),
    )


def _partial_day(
    hours: pl.DataFrame, origins: pl.DataFrame, lag: timedelta, cutoff_days: int
) -> pl.DataFrame:
    """Hours of the cutoff day ending at or before the cutoff (mean), and the latest such hour.

    Under the realtime protocol this is 00:00-06:00 on D-1; under the bulk protocol the cutoff
    is midnight, so the partial day is empty and ``last_known_mw`` is the final hour of D-3.
    """
    cols = ("ba_code", "target_day", "demand_cutoff")
    shifted = hours.with_columns(
        (pl.col("local_date") + pl.duration(days=cutoff_days)).alias("target_day")
    ).join(origins.select(*cols), on=["ba_code", "target_day"])
    usable = shifted.filter(pl.col("hour_ending_utc") <= pl.col("demand_cutoff"))
    partial = usable.group_by("ba_code", "target_day").agg(
        pl.col("demand_filled_mw").mean().alias("partial_day_mean_mw"),
        (pl.col("hour_ending_utc").max() + lag).alias(AVAIL_PREFIX + "partial_day_mean_mw"),
    )
    # an hour in (cutoff - 6 h, cutoff] lies on the cutoff day or the day before it
    candidates = pl.concat(
        [
            hours.with_columns(
                (pl.col("local_date") + pl.duration(days=cutoff_days + extra)).alias("target_day")
            )
            for extra in (0, 1)
        ]
    )
    last = (
        candidates.join(origins.select(*cols), on=["ba_code", "target_day"])
        .filter(
            (pl.col("hour_ending_utc") <= pl.col("demand_cutoff"))
            & (pl.col("hour_ending_utc") > pl.col("demand_cutoff") - pl.duration(hours=6))
        )
        .group_by("ba_code", "target_day")
        .agg(
            pl.col("demand_filled_mw").sort_by("hour_ending_utc").last().alias("last_known_mw"),
            (pl.col("hour_ending_utc").max() + lag).alias(AVAIL_PREFIX + "last_known_mw"),
        )
    )
    return last.join(partial, on=["ba_code", "target_day"], how="left")


def _weather(weather: pl.DataFrame, config: FeatureConfig) -> pl.DataFrame:
    source = "temperature_c" if config.population_weighted else "temperature_unweighted_c"
    return weather.select(
        "ba_code",
        "hour_ending_utc",
        pl.col(source).alias("_temp"),
        pl.col("temperature_spread_c").alias("_spread")
        if "temperature_spread_c" in weather.columns
        else pl.lit(None, dtype=pl.Float64).alias("_spread"),
        (pl.col("hour_ending_utc") + WEATHER_AVAILABLE_OFFSET).alias("_temp_avail"),
    ).filter(pl.col("_temp").is_not_null())


def _ratio(num: str, den: str, name: str) -> list[pl.Expr]:
    return [
        (pl.col(num) / pl.col(den)).alias(name),
        pl.max_horizontal(AVAIL_PREFIX + num, AVAIL_PREFIX + den).alias(AVAIL_PREFIX + name),
    ]


# --------------------------------------------------------------------------- public API


def build_features(
    demand: pl.DataFrame,
    weather: pl.DataFrame | None,
    regions: Sequence[BalancingAuthority],
    start: date,
    end: date,
    *,
    config: FeatureConfig | None = None,
) -> pl.DataFrame:
    """Feature matrix for every target hour of local days ``start..end`` (inclusive).

    ``demand`` has the ``fct_demand_hourly`` columns; ``weather`` the forecast-weather columns
    (``None`` builds demand + calendar features only, with weather features null).
    """
    config = config or FeatureConfig()
    # Demand blocks record the *source* hour's end; it is shifted to an availability instant
    # per origin below (issued_at - demand_cutoff), which stays exact across DST changes.
    lag = timedelta(0)
    hours = with_local_fields(demand, regions)
    # Target hours come from the clock, not from the data, so future days (the live loop) and
    # days with missing rows still get every hour; actuals are joined on where they exist.
    known = [ba for ba in regions if ba.code in set(hours["ba_code"].unique().to_list())]
    targets = target_hours(known, start, end).join(
        hours.select(
            "ba_code",
            "hour_ending_utc",
            pl.col("demand_mw").alias(TARGET_COLUMN),
            "operator_forecast_mw",
        ),
        on=["ba_code", "hour_ending_utc"],
        how="left",
    )
    if targets.is_empty():
        raise ValueError(f"no target hours between {start} and {end}")
    origins = origins_frame(
        targets.select("ba_code", "target_day").unique(), regions, config.protocol
    )
    frame = targets.join(origins, on=["ba_code", "target_day"])

    # demand history ------------------------------------------------------------------------
    recent = config.protocol.recent_day_offset
    for days, name in ((recent, "lag_recent_mw"), (7, "lag7_mw")):
        frame = frame.join(
            _same_hour_lag(hours, days, name, lag),
            on=["ba_code", "target_day", "local_hour"],
            how="left",
        )
    daily = _daily(hours)
    frame = frame.join(_level(daily, lag, recent), on=["ba_code", "target_day"], how="left")
    frame = frame.join(_recent_peak(daily, lag, recent), on=["ba_code", "target_day"], how="left")
    frame = frame.join(
        _partial_day(hours, origins, lag, config.protocol.demand_cutoff_days_before),
        on=["ba_code", "target_day"],
        how="left",
    )
    publication = pl.col("issued_at") - pl.col("demand_cutoff")
    raw_demand = (
        "lag_recent_mw",
        "lag7_mw",
        "level_7d_mw",
        "recent_peak_mw",
        "partial_day_mean_mw",
        "last_known_mw",
    )
    frame = frame.with_columns(
        [(pl.col(AVAIL_PREFIX + f) + publication).alias(AVAIL_PREFIX + f) for f in raw_demand]
    )
    frame = frame.with_columns(
        *_ratio("lag_recent_mw", "level_7d_mw", "lag_recent_ratio"),
        *_ratio("lag7_mw", "level_7d_mw", "lag7_ratio"),
        *_ratio("partial_day_mean_mw", "level_7d_mw", "partial_day_ratio"),
        *_ratio("recent_peak_mw", "level_7d_mw", "recent_peak_ratio"),
    )

    # calendar ------------------------------------------------------------------------------
    frame = _add_calendar(frame)

    # weather -------------------------------------------------------------------------------
    frame = _add_weather(frame, weather, config)

    ordered = [*KEY_COLUMNS, "demand_cutoff", TARGET_COLUMN, *BENCHMARK_COLUMNS, *FEATURE_COLUMNS]
    avail = [AVAIL_PREFIX + f for f in FEATURE_COLUMNS]
    return frame.select(*ordered, *avail).sort("ba_code", "hour_ending_utc")


def _add_calendar(frame: pl.DataFrame) -> pl.DataFrame:
    days = frame.select("target_day").unique()
    first = days["target_day"].min()
    last = days["target_day"].max()
    assert isinstance(first, date) and isinstance(last, date)  # noqa: S101 - narrows for mypy
    holidays = pl.Series(holiday_dates(first.year - 1, last.year), dtype=pl.Date)
    holiday = days.with_columns(
        pl.col("target_day").is_in(holidays.implode()).alias("is_holiday"),
        (pl.col("target_day") - pl.duration(days=1))
        .is_in(holidays.implode())
        .alias("is_day_after_holiday"),
    )
    n_hours = frame.group_by("ba_code", "target_day").agg(pl.len().alias("hours_in_day"))
    doy = pl.col("target_day").dt.ordinal_day().cast(pl.Float64) * (2 * 3.141592653589793 / 365.25)
    frame = frame.join(holiday, on="target_day", how="left").join(
        n_hours, on=["ba_code", "target_day"], how="left"
    )
    frame = frame.with_columns(
        pl.col("target_day").dt.weekday().cast(pl.Int8).alias("weekday"),
        (pl.col("target_day").dt.weekday() >= 6).alias("is_weekend"),
        pl.col("target_day").dt.month().cast(pl.Int8).alias("month"),
        doy.sin().alias("doy_sin"),
        doy.cos().alias("doy_cos"),
        pl.col("hours_in_day").cast(pl.Int8),
    )
    null_avail = pl.lit(None, dtype=pl.Datetime("us", "UTC"))
    return frame.with_columns([null_avail.alias(AVAIL_PREFIX + f) for f in CALENDAR_FEATURES])


def _add_weather(
    frame: pl.DataFrame, weather: pl.DataFrame | None, config: FeatureConfig
) -> pl.DataFrame:
    names = list(WEATHER_FEATURES)
    if weather is None or weather.is_empty():
        return frame.with_columns(
            *[pl.lit(None, dtype=pl.Float64).alias(n) for n in names],
            *[pl.lit(None, dtype=pl.Datetime("us", "UTC")).alias(AVAIL_PREFIX + n) for n in names],
        )
    w = _weather(weather, config)
    at_hour = w.rename(
        {"_temp": "temp_c", "_spread": "temp_spread_c", "_temp_avail": AVAIL_PREFIX + "temp_c"}
    )
    frame = frame.join(at_hour, on=["ba_code", "hour_ending_utc"], how="left").with_columns(
        pl.col(AVAIL_PREFIX + "temp_c").alias(AVAIL_PREFIX + "temp_spread_c"),
        (pl.col("temp_c") - COMFORT_TEMPERATURE_C).clip(lower_bound=0).alias("cdd"),
        (COMFORT_TEMPERATURE_C - pl.col("temp_c")).clip(lower_bound=0).alias("hdd"),
        pl.col(AVAIL_PREFIX + "temp_c").alias(AVAIL_PREFIX + "cdd"),
        pl.col(AVAIL_PREFIX + "temp_c").alias(AVAIL_PREFIX + "hdd"),
    )
    # whole-target-day statistics (latest valid time of the day bounds availability)
    day_stats = (
        frame.select("ba_code", "target_day", "hour_ending_utc")
        .join(w, on=["ba_code", "hour_ending_utc"])
        .group_by("ba_code", "target_day")
        .agg(
            pl.col("_temp").mean().alias("temp_day_mean_c"),
            pl.col("_temp").max().alias("temp_day_max_c"),
            pl.col("_temp").min().alias("temp_day_min_c"),
            pl.col("_temp_avail").max().alias("_day_avail"),
        )
    )
    frame = frame.join(day_stats, on=["ba_code", "target_day"], how="left").with_columns(
        [
            pl.col("_day_avail").alias(AVAIL_PREFIX + n)
            for n in ("temp_day_mean_c", "temp_day_max_c", "temp_day_min_c")
        ]
    )
    # same hour a week earlier, and the three hours before the target hour
    week = w.select(
        "ba_code",
        (pl.col("hour_ending_utc") + pl.duration(days=7)).alias("hour_ending_utc"),
        pl.col("_temp").alias("_temp_7d"),
        pl.col("_temp_avail").alias("_avail_7d"),
    )
    prev = []
    for k in (1, 2, 3):
        prev.append(
            w.select(
                "ba_code",
                (pl.col("hour_ending_utc") + pl.duration(hours=k)).alias("hour_ending_utc"),
                "_temp",
                "_temp_avail",
            )
        )
    prev3 = (
        pl.concat(prev)
        .group_by("ba_code", "hour_ending_utc")
        .agg(pl.col("_temp").mean().alias("temp_prev3h_c"), pl.col("_temp_avail").max().alias("_p"))
    )
    frame = (
        frame.join(week, on=["ba_code", "hour_ending_utc"], how="left")
        .join(prev3, on=["ba_code", "hour_ending_utc"], how="left")
        .with_columns(
            (pl.col("temp_c") - pl.col("_temp_7d")).alias("temp_delta_7d_c"),
            pl.max_horizontal(AVAIL_PREFIX + "temp_c", "_avail_7d").alias(
                AVAIL_PREFIX + "temp_delta_7d_c"
            ),
            pl.col("_p").alias(AVAIL_PREFIX + "temp_prev3h_c"),
        )
    )
    # the same hour on the most recent complete day - pairs with lag_recent_mw, so the model sees
    # how much warmer or colder the target hour is than the demand it is anchored to
    recent_days = config.protocol.recent_day_offset
    recent = w.select(
        "ba_code",
        (pl.col("hour_ending_utc") + pl.duration(days=recent_days)).alias("hour_ending_utc"),
        pl.col("_temp").alias("temp_recent_c"),
        pl.col("_temp_avail").alias("_avail_recent"),
    )
    frame = frame.join(recent, on=["ba_code", "hour_ending_utc"], how="left").with_columns(
        pl.col("_avail_recent").alias(AVAIL_PREFIX + "temp_recent_c"),
        (pl.col("temp_c") - pl.col("temp_recent_c")).alias("temp_delta_recent_c"),
        pl.max_horizontal(AVAIL_PREFIX + "temp_c", "_avail_recent").alias(
            AVAIL_PREFIX + "temp_delta_recent_c"
        ),
    )
    return frame.drop("_temp_7d", "_avail_7d", "_p", "_day_avail", "_avail_recent")


@dataclass(frozen=True)
class LeakageReport:
    """Result of a point-in-time check - says how much it checked."""

    rows_checked: int
    cells_checked: int
    origins_checked: int
    violations: int
    worst_margin: timedelta | None
    violating_features: tuple[str, ...]

    @property
    def ok(self) -> bool:
        """True when no feature value was available after its forecast's issue time."""
        return self.violations == 0


def check_point_in_time(features: pl.DataFrame) -> LeakageReport:
    """Count cells whose ``avail__f`` is later than the row's ``issued_at``."""
    avail_cols = [c for c in features.columns if c.startswith(AVAIL_PREFIX)]
    exprs = [
        (pl.col(c) > pl.col("issued_at")).fill_null(value=False).sum().alias(c) for c in avail_cols
    ]
    counts = features.select(exprs).row(0, named=True)
    checked = features.select([pl.col(c).is_not_null().sum().alias(c) for c in avail_cols]).row(
        0, named=True
    )
    margins = features.select(
        pl.min_horizontal([(pl.col("issued_at") - pl.col(c)).min() for c in avail_cols]).alias("m")
    )["m"][0]
    bad = tuple(sorted(c.removeprefix(AVAIL_PREFIX) for c, n in counts.items() if n))
    return LeakageReport(
        rows_checked=features.height,
        cells_checked=int(sum(checked.values())),
        origins_checked=features.select("ba_code", "target_day").n_unique(),
        violations=int(sum(counts.values())),
        worst_margin=margins,
        violating_features=bad,
    )
