from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import polars as pl
import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from gridcast.core.regions import all_regions, get_region
from gridcast.features.build import (
    AVAIL_PREFIX,
    BENCHMARK_COLUMNS,
    FEATURE_COLUMNS,
    _same_hour_lag,
    build_features,
    check_point_in_time,
    with_local_fields,
)
from tests.support.synthetic import make_demand, make_weather

BAS = ("PJM", "MISO", "CISO")
REGIONS = tuple(get_region(b) for b in BAS)
START = date(2025, 2, 1)
DAYS = 70  # spans the 2025-03-09 spring-forward change
DEMAND = make_demand(BAS, START, DAYS)
WEATHER = make_weather(BAS, START, DAYS)
FIRST_TARGET = START + timedelta(days=10)
LAST_TARGET = START + timedelta(days=DAYS - 1)


@pytest.fixture(scope="module")
def features() -> pl.DataFrame:
    return build_features(DEMAND, WEATHER, REGIONS, FIRST_TARGET, LAST_TARGET)


def test_operator_forecast_is_never_a_feature() -> None:
    assert not set(BENCHMARK_COLUMNS) & set(FEATURE_COLUMNS)
    assert not any("operator" in f for f in FEATURE_COLUMNS)


def test_every_feature_has_an_availability_column(features: pl.DataFrame) -> None:
    for f in FEATURE_COLUMNS:
        assert AVAIL_PREFIX + f in features.columns


def test_one_row_per_target_hour_and_dst_day_shapes(features: pl.DataFrame) -> None:
    assert features.select("ba_code", "hour_ending_utc").is_duplicated().sum() == 0
    per_day = features.group_by("ba_code", "target_day").len()
    pjm_dst = per_day.filter(
        (pl.col("ba_code") == "PJM") & (pl.col("target_day") == date(2025, 3, 9))
    )
    miso_dst = per_day.filter(
        (pl.col("ba_code") == "MISO") & (pl.col("target_day") == date(2025, 3, 9))
    )
    assert pjm_dst["len"].item() == 23 and miso_dst["len"].item() == 24


def test_lag_values_match_the_source_rows(features: pl.DataFrame) -> None:
    hours = with_local_fields(DEMAND, REGIONS)
    row = features.filter(
        (pl.col("ba_code") == "PJM")
        & (pl.col("target_day") == date(2025, 3, 20))
        & (pl.col("local_hour") == 17)
    ).row(0, named=True)
    src = hours.filter(
        (pl.col("ba_code") == "PJM")
        & (pl.col("local_date") == date(2025, 3, 13))
        & (pl.col("local_hour") == 17)
    )
    assert row["lag7_mw"] == pytest.approx(src["demand_filled_mw"].item())
    assert row["lag7_ratio"] == pytest.approx(row["lag7_mw"] / row["level_7d_mw"])
    assert row["issued_at"].isoformat() == "2025-03-19T14:00:00+00:00"  # 10:00 EDT


def test_spring_forward_missing_hour_gives_null_lag(features: pl.DataFrame) -> None:
    # 2025-03-16 02:00 local looks back to 2025-03-09 02:00, which did not exist in PJM
    row = features.filter(
        (pl.col("ba_code") == "PJM")
        & (pl.col("target_day") == date(2025, 3, 16))
        & (pl.col("local_hour") == 2)
    )
    assert row["lag7_mw"].item() is None


def test_real_protocol_has_no_leakage_and_says_how_much_it_checked(features: pl.DataFrame) -> None:
    report = check_point_in_time(features)
    assert report.ok, report.violating_features
    assert report.origins_checked == len(BAS) * (DAYS - 10)
    assert report.cells_checked > 50_000
    assert report.worst_margin is not None and report.worst_margin >= timedelta(0)


def test_a_deliberately_leaky_feature_is_caught(features: pl.DataFrame) -> None:
    """Yesterday's same hour is not fully published at 10:00 D-1: the check must say so."""
    hours = with_local_fields(DEMAND, REGIONS)
    leaky = _same_hour_lag(hours, 1, "lag1_mw", timedelta(hours=4))
    frame = features.join(
        hours.select("ba_code", "hour_ending_utc", "local_hour"), on=["ba_code", "hour_ending_utc"]
    ).join(leaky, on=["ba_code", "target_day", "local_hour"], how="left")
    report = check_point_in_time(frame)
    assert not report.ok
    assert report.violating_features == ("lag1_mw",)
    # afternoon hours of D-1 leak; morning hours (before 06:00) do not
    assert 0 < report.violations < frame.height


def test_observed_weather_would_be_flagged_as_leakage(features: pl.DataFrame) -> None:
    """Using weather *observed* at the target hour (available at T) must violate the protocol."""
    frame = features.with_columns(pl.col("hour_ending_utc").alias(AVAIL_PREFIX + "temp_c"))
    report = check_point_in_time(frame)
    assert report.violating_features == ("temp_c",)
    assert report.violations == frame.height  # every target hour is after its issue time


def test_features_do_not_depend_on_data_published_after_issue() -> None:
    """Perturbation test: scrambling everything unavailable at issue time changes nothing."""
    target = date(2025, 3, 30)
    base = build_features(DEMAND, WEATHER, REGIONS, target, target)
    rng = np.random.default_rng(7)
    for code in BAS:
        issued = base.filter(pl.col("ba_code") == code)["issued_at"][0]
        cutoff = base.filter(pl.col("ba_code") == code)["demand_cutoff"][0]
        demand = DEMAND.with_columns(
            pl.when((pl.col("ba_code") == code) & (pl.col("hour_ending_utc") > cutoff))
            .then(pl.lit(rng.uniform(1, 1e6)))
            .otherwise(pl.col("demand_filled_mw"))
            .alias("demand_filled_mw")
        )
        weather = WEATHER.with_columns(
            pl.when(
                (pl.col("ba_code") == code)
                & (pl.col("hour_ending_utc") - timedelta(hours=42) > issued)
            )
            .then(pl.lit(99.0))
            .otherwise(pl.col("temperature_c"))
            .alias("temperature_c")
        )
        after = build_features(demand, weather, REGIONS, target, target)
        cols = list(FEATURE_COLUMNS)
        assert (
            base.filter(pl.col("ba_code") == code)
            .select(cols)
            .equals(after.filter(pl.col("ba_code") == code).select(cols))
        ), code


SMALL_DEMAND = make_demand(("ERCO", "CISO"), date(2024, 10, 20), 30, seed=3)
SMALL_WEATHER = make_weather(("ERCO", "CISO"), date(2024, 10, 20), 30, seed=4)
SMALL_REGIONS = (get_region("ERCO"), get_region("CISO"))


@settings(max_examples=25, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(offset=st.integers(min_value=9, max_value=29), code=st.sampled_from(["ERCO", "CISO"]))
def test_perturbation_property_over_random_origins(offset: int, code: str) -> None:
    """For random origins (incl. the 2024-11-03 fall-back day), future data never matters."""
    target = date(2024, 10, 20) + timedelta(days=offset)
    base = build_features(SMALL_DEMAND, SMALL_WEATHER, SMALL_REGIONS, target, target).filter(
        pl.col("ba_code") == code
    )
    issued, cutoff = base["issued_at"][0], base["demand_cutoff"][0]
    demand = SMALL_DEMAND.with_columns(
        pl.when(pl.col("hour_ending_utc") > cutoff)
        .then(0.0)
        .otherwise(pl.col("demand_filled_mw"))
        .alias("demand_filled_mw"),
        pl.when(pl.col("hour_ending_utc") > cutoff)
        .then(0.0)
        .otherwise(pl.col("demand_mw"))
        .alias("demand_mw"),
    )
    weather = SMALL_WEATHER.with_columns(
        pl.when(pl.col("hour_ending_utc") - timedelta(hours=42) > issued)
        .then(-50.0)
        .otherwise(pl.col("temperature_c"))
        .alias("temperature_c")
    )
    after = build_features(demand, weather, SMALL_REGIONS, target, target).filter(
        pl.col("ba_code") == code
    )
    assert base.select(FEATURE_COLUMNS).equals(after.select(FEATURE_COLUMNS))


def test_leakage_check_over_ten_thousand_origins() -> None:
    """Phase 3 exit criterion: the vectorised check over >= 10,000 forecast origins."""
    bas = tuple(ba.code for ba in all_regions())
    demand = make_demand(bas, date(2023, 1, 1), 1015, seed=11)
    weather = make_weather(bas, date(2023, 1, 1), 1015, seed=12)
    frame = build_features(demand, weather, all_regions(), date(2023, 1, 12), date(2025, 10, 11))
    report = check_point_in_time(frame)
    assert report.ok, report.violating_features
    assert report.origins_checked >= 10_000
    print(
        f"leakage check: {report.origins_checked} origins, {report.cells_checked} cells, 0 violations"
    )


def test_bulk_protocol_is_leak_free_across_dst_and_uses_older_data() -> None:
    from gridcast.core.domain import ProtocolConfig
    from gridcast.features.build import FeatureConfig

    bulk = FeatureConfig(protocol=ProtocolConfig.bulk())
    # 2025-03-10/11: the spring-forward change falls between the bulk cutoff and the issue time
    frame = build_features(
        DEMAND, WEATHER, REGIONS, date(2025, 3, 5), date(2025, 3, 20), config=bulk
    )
    report = check_point_in_time(frame)
    assert report.ok, report.violating_features
    assert frame["partial_day_mean_mw"].null_count() == frame.height  # nothing after midnight D-3
    row = frame.filter(
        (pl.col("ba_code") == "PJM") & (pl.col("target_day") == date(2025, 3, 11))
    ).row(0, named=True)
    assert (
        row["demand_cutoff"].isoformat() == "2025-03-09T05:00:00+00:00"
    )  # midnight EST ending D-3


def test_fixed_publication_lag_would_leak_on_dst_days() -> None:
    """Regression: a constant 34 h lag mis-states availability when DST changes in between."""
    from gridcast.core.domain import ProtocolConfig
    from gridcast.features.build import FeatureConfig

    bulk = FeatureConfig(protocol=ProtocolConfig.bulk())
    frame = build_features(
        DEMAND, WEATHER, REGIONS, date(2025, 3, 5), date(2025, 3, 20), config=bulk
    )
    spans = frame.select((pl.col("issued_at") - pl.col("demand_cutoff")).alias("span"))[
        "span"
    ].unique()
    assert len(spans) >= 2  # 33 h around the change, 34 h otherwise


def test_future_day_without_any_demand_rows_still_gets_every_hour() -> None:
    """The live loop forecasts a day that has no rows in the demand table yet."""
    last_day = START + timedelta(days=DAYS - 1)
    future = last_day + timedelta(days=2)
    frame = build_features(DEMAND, WEATHER, REGIONS, future, future)
    assert frame.group_by("ba_code").len()["len"].to_list() == [24, 24, 24]
    assert frame["y"].null_count() == frame.height  # no actuals, as it should be
    assert check_point_in_time(frame).ok
    assert frame["lag7_mw"].null_count() == 0  # a week ago is known
