from __future__ import annotations

from datetime import date

import polars as pl
import pytest

from gridcast.core.regions import get_region
from gridcast.evaluation.backtest import BacktestConfig, run_backtest
from gridcast.features.build import build_features
from gridcast.models.base import Forecaster
from gridcast.models.benchmarks import (
    DebiasedOperatorForecast,
    OperatorForecast,
    operator_debias_offsets,
)
from tests.support.synthetic import make_demand, make_weather

BAS = ("ERCO", "NYIS")
REGIONS = tuple(get_region(b) for b in BAS)
DEMAND = make_demand(BAS, date(2024, 1, 1), 200)
FEATURES = build_features(
    DEMAND, make_weather(BAS, date(2024, 1, 1), 200), REGIONS, date(2024, 1, 10), date(2024, 7, 18)
)


class MeanForecaster:
    name = "mean"

    def __init__(self) -> None:
        self.seen_last_day: date | None = None
        self.mean = 0.0

    def fit(self, train: pl.DataFrame) -> None:
        self.mean = float(train["y"].mean())  # type: ignore[arg-type]
        self.seen_last_day = train["target_day"].max()  # type: ignore[assignment]

    def predict(self, frame: pl.DataFrame, *, context: pl.DataFrame | None = None) -> pl.DataFrame:
        return frame.with_columns(pl.lit(self.mean).alias("yhat")).select("yhat")


def test_monthly_refits_and_forecast_shape() -> None:
    cfg = BacktestConfig(start=date(2024, 5, 1), end=date(2024, 7, 18), min_train_days=60)
    result = run_backtest(FEATURES, {"mean": MeanForecaster}, cfg)
    assert result.refits == 3
    expected = FEATURES.filter(pl.col("target_day") >= date(2024, 5, 1)).height
    assert result.forecasts.height == expected
    assert result.train_gap_checks == expected
    assert result.train_rows["mean"][0] < result.train_rows["mean"][-1]  # expanding window


def test_training_rows_end_two_days_before_the_month() -> None:
    fitted: list[MeanForecaster] = []

    def factory() -> Forecaster:
        m = MeanForecaster()
        fitted.append(m)
        return m

    run_backtest(
        FEATURES,
        {"mean": factory},
        BacktestConfig(start=date(2024, 6, 1), end=date(2024, 6, 30), min_train_days=60),
    )
    assert fitted[0].seen_last_day == date(2024, 5, 30)


def test_a_zero_gap_is_refused_as_leakage() -> None:
    cfg = BacktestConfig(
        start=date(2024, 6, 1), end=date(2024, 6, 30), min_train_days=60, gap_days=0
    )
    with pytest.raises(AssertionError, match="demand cutoff"):
        run_backtest(FEATURES, {"mean": MeanForecaster}, cfg)


def test_too_little_history_is_an_error() -> None:
    with pytest.raises(ValueError, match="training days"):
        run_backtest(
            FEATURES,
            {"mean": MeanForecaster},
            BacktestConfig(start=date(2024, 2, 1), end=date(2024, 2, 5)),
        )


def test_operator_benchmarks() -> None:
    offsets = operator_debias_offsets(FEATURES)
    cfg = BacktestConfig(start=date(2024, 6, 1), end=date(2024, 6, 30), min_train_days=60)
    result = run_backtest(
        FEATURES,
        {
            "operator": OperatorForecast,
            "operator_debiased": lambda: DebiasedOperatorForecast(offsets),
        },
        cfg,
    )
    joined = result.forecasts.pivot(
        on="model", index=["ba_code", "hour_ending_utc"], values="yhat"
    ).join(FEATURES.select("ba_code", "hour_ending_utc", "y"), on=["ba_code", "hour_ending_utc"])
    raw_err = ((joined["operator"] - joined["y"]) / joined["y"]).mean()
    deb_err = ((joined["operator_debiased"] - joined["y"]) / joined["y"]).mean()
    assert raw_err == pytest.approx(0.02, abs=0.005)  # synthetic operator = demand * 1.02
    assert abs(deb_err) < 0.005  # the trailing bias correction removes it


def test_debias_offsets_only_use_days_up_to_d_minus_2() -> None:
    offsets = operator_debias_offsets(FEATURES)
    # altering the operator forecast on and after D-1 must not change the offset for D
    target = date(2024, 6, 15)
    changed = FEATURES.with_columns(
        pl.when(pl.col("target_day") >= date(2024, 6, 14))
        .then(pl.col("operator_forecast_mw") * 3)
        .otherwise(pl.col("operator_forecast_mw"))
        .alias("operator_forecast_mw")
    )
    after = operator_debias_offsets(changed)
    key = pl.col("target_day") == target
    assert (
        offsets.filter(key)
        .sort("ba_code", "local_hour")
        .equals(after.filter(key).sort("ba_code", "local_hour"))
    )


def test_bulk_protocol_needs_a_three_day_training_gap() -> None:
    """Regression: under the bulk protocol D-2 actuals are not yet published at issue time."""
    from gridcast.core.domain import ProtocolConfig
    from gridcast.features.build import FeatureConfig

    bulk = ProtocolConfig.bulk()
    feats = build_features(
        DEMAND,
        make_weather(BAS, date(2024, 1, 1), 200),
        REGIONS,
        date(2024, 1, 10),
        date(2024, 7, 18),
        config=FeatureConfig(protocol=bulk),
    )
    too_short = BacktestConfig(
        start=date(2024, 6, 1), end=date(2024, 6, 30), min_train_days=60, gap_days=2
    )
    with pytest.raises(AssertionError, match="demand cutoff"):
        run_backtest(feats, {"mean": MeanForecaster}, too_short)
    ok = BacktestConfig(
        start=date(2024, 6, 1),
        end=date(2024, 6, 30),
        min_train_days=60,
        gap_days=bulk.recent_day_offset,
    )
    assert run_backtest(feats, {"mean": MeanForecaster}, ok).refits == 1
