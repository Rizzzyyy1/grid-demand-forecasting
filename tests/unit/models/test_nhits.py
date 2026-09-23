from __future__ import annotations

from datetime import date

import numpy as np
import polars as pl
import pytest

from gridcast.core.regions import get_region
from gridcast.features.build import build_features
from gridcast.models.base import as_batch
from gridcast.models.nhits import NHiTSForecaster
from tests.support.synthetic import make_demand, make_weather

pytestmark = pytest.mark.slow
BAS = ("ERCO", "ISNE")
REGIONS = tuple(get_region(b) for b in BAS)
FEATURES = build_features(
    make_demand(BAS, date(2024, 1, 1), 90),
    make_weather(BAS, date(2024, 1, 1), 90),
    REGIONS,
    date(2024, 1, 10),
    date(2024, 3, 29),
)
TRAIN = FEATURES.filter(pl.col("target_day") <= date(2024, 3, 13))
CONTEXT = FEATURES.filter(pl.col("target_day").is_between(date(2024, 3, 14), date(2024, 3, 14)))
TEST = FEATURES.filter(pl.col("target_day").is_between(date(2024, 3, 15), date(2024, 3, 18)))


@pytest.fixture(scope="module")
def fitted() -> NHiTSForecaster:
    model = NHiTSForecaster(max_steps=30)
    model.fit(TRAIN)
    return model


def test_shapes_and_accuracy(fitted: NHiTSForecaster) -> None:
    preds = fitted.predict(TEST, context=CONTEXT)
    batch = as_batch(TEST, preds, "nhits")
    assert batch.height == TEST.height and batch["yhat"].null_count() == 0
    mape = float(((batch["yhat"] - TEST["y"]).abs() / TEST["y"]).mean())  # type: ignore[arg-type]
    assert mape < 0.25  # 30 training steps: sanity, not skill
    assert fitted.max_input_hour_checked > 0


def test_actuals_after_the_cutoff_are_never_used(fitted: NHiTSForecaster) -> None:
    base = fitted.predict(TEST, context=CONTEXT)
    rng = np.random.default_rng(0)
    # scramble every actual in the forecast frame: all of them lie after some origin's cutoff,
    # and the rows each origin may use (<= its cutoff) must come from context/earlier days only
    scrambled_test = TEST.with_columns(pl.Series("y", rng.uniform(1, 1e6, TEST.height)))
    day1 = TEST.filter(pl.col("target_day") == date(2024, 3, 15))
    p1 = fitted.predict(day1, context=CONTEXT)
    p2 = fitted.predict(
        scrambled_test.filter(pl.col("target_day") == date(2024, 3, 15)), context=CONTEXT
    )
    assert np.allclose(p1["yhat"].to_numpy(), p2["yhat"].to_numpy())
    assert base.height == TEST.height


def test_long_weather_gap_does_not_blow_up() -> None:
    """Regression: 3 weeks of missing temperature used to be forward-filled into a constant
    input window; the robust scaler then exploded on the first real value (2024-01-20)."""
    gap = pl.col("target_day").is_between(date(2024, 2, 20), date(2024, 3, 14))
    gappy = FEATURES.with_columns(
        pl.when(gap).then(None).otherwise(pl.col("temp_c")).alias("temp_c")
    )
    model = NHiTSForecaster(max_steps=30)
    model.fit(gappy.filter(pl.col("target_day") <= date(2024, 3, 13)))
    ctx = gappy.filter(pl.col("target_day") == date(2024, 3, 14))
    preds = model.predict(gappy.filter(pl.col("target_day") == date(2024, 3, 15)), context=ctx)
    assert preds["yhat"].null_count() == 0 and model.abstained == 0
    assert float(preds["yhat"].max()) < 2 * float(FEATURES["y"].max())  # type: ignore[arg-type]
