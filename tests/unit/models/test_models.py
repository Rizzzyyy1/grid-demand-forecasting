from __future__ import annotations

from datetime import date

import numpy as np
import polars as pl
import pytest

from gridcast.core.regions import get_region
from gridcast.features.build import build_features
from gridcast.models.base import QUANTILES, Forecaster, as_batch
from gridcast.models.baselines import RidgeForecaster, SeasonalNaive
from gridcast.models.gbm import GBM_FEATURES, GBMParams, LightGBMForecaster
from tests.support.synthetic import make_demand, make_weather

BAS = ("ERCO", "ISNE")
REGIONS = tuple(get_region(b) for b in BAS)
FEATURES = build_features(
    make_demand(BAS, date(2024, 1, 1), 150),
    make_weather(BAS, date(2024, 1, 1), 150),
    REGIONS,
    date(2024, 1, 12),
    date(2024, 5, 29),
)
TRAIN = FEATURES.filter((pl.col("target_day") <= date(2024, 4, 30)) & pl.col("y").is_not_null())
TEST = FEATURES.filter(pl.col("target_day") >= date(2024, 5, 2))
FAST = GBMParams(n_estimators=60, quantile_estimators=40, num_leaves=15, min_child_samples=20)


def _check(model: Forecaster, quantiles: bool = True) -> pl.DataFrame:
    model.fit(TRAIN)
    preds = model.predict(TEST)
    batch = as_batch(TEST, preds, model.name)
    assert batch.height == TEST.height
    mape = (batch["yhat"] - TEST["y"]).abs() / TEST["y"]
    assert float(mape.mean()) < 0.1  # type: ignore[arg-type]
    if quantiles:
        q = batch.select(list(QUANTILES)).to_numpy()
        assert np.all(np.diff(q, axis=1) >= -1e-9), "quantiles cross"
    return batch


def test_seasonal_naive_is_the_week_ago_value() -> None:
    batch = _check(SeasonalNaive())
    assert batch["yhat"].to_list() == TEST["lag7_mw"].to_list()


def test_ridge() -> None:
    _check(RidgeForecaster())


def test_lgbm_global_and_per_ba() -> None:
    glob = LightGBMForecaster(FAST)
    _check(glob)
    assert set(glob.feature_importance) <= {*GBM_FEATURES, "ba_code"}
    assert abs(sum(glob.feature_importance.values()) - 1) < 1e-9
    per = LightGBMForecaster(FAST, per_ba=True)
    _check(per)
    assert per.name == "lgbm_per_ba"


def test_lgbm_never_sees_raw_megawatts_or_the_operator() -> None:
    assert "operator_forecast_mw" not in GBM_FEATURES
    assert not any(f.endswith("_mw") for f in GBM_FEATURES)


def test_predict_before_fit_fails() -> None:
    with pytest.raises(RuntimeError):
        SeasonalNaive().predict(TEST)
    with pytest.raises(RuntimeError):
        LightGBMForecaster(FAST).predict(TEST)
