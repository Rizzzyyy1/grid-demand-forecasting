"""Baselines: seasonal naive (same local hour a week earlier) and per-BA ridge regression.

Both predict demand *relative to the BA's recent level* (``y / level_7d_mw``) and scale back, so
one set of hyper-parameters fits BAs of very different sizes. Intervals come from empirical
quantiles of the training residual ratios per BA and local hour: simple, honest, and a
reference point for the conformal calibration in Phase 5.
"""

from __future__ import annotations

import numpy as np
import polars as pl
from numpy.typing import NDArray

from gridcast.models.base import QUANTILES


def _residual_quantiles(train: pl.DataFrame, ratio: pl.Expr) -> pl.DataFrame:
    """Per (BA, local hour): quantiles of actual / predicted over the training rows."""
    return (
        train.with_columns(ratio.alias("_r"))
        .filter(pl.col("_r").is_finite())
        .group_by("ba_code", "local_hour")
        .agg([pl.col("_r").quantile(tau).alias(name) for name, tau in QUANTILES.items()])
    )


def _apply_quantiles(frame: pl.DataFrame, yhat: pl.Series, table: pl.DataFrame) -> pl.DataFrame:
    joined = (
        frame.select("ba_code", "local_hour")
        .with_columns(yhat.alias("yhat"))
        .join(table, on=["ba_code", "local_hour"], how="left", maintain_order="left")
    )
    return joined.select("yhat", *[(pl.col("yhat") * pl.col(q)).alias(q) for q in QUANTILES])


class SeasonalNaive:
    """Same local hour one week earlier."""

    name = "seasonal_naive"

    def __init__(self) -> None:
        """Unfitted."""
        self._quantiles: pl.DataFrame | None = None

    def fit(self, train: pl.DataFrame) -> None:
        """Learn residual-ratio quantiles for the intervals."""
        recent = train.filter(
            pl.col("target_day") >= pl.col("target_day").max() - pl.duration(days=365)
        )
        self._quantiles = _residual_quantiles(recent, pl.col("y") / pl.col("lag7_mw"))

    def predict(self, frame: pl.DataFrame, *, context: pl.DataFrame | None = None) -> pl.DataFrame:
        """``lag7_mw`` with empirical intervals."""
        if self._quantiles is None:
            raise RuntimeError("fit() first")
        return _apply_quantiles(frame, frame["lag7_mw"], self._quantiles)


class RidgeForecaster:
    """Per-BA ridge on hour/weekday one-hots, lag ratios and temperature splines."""

    name = "ridge"

    def __init__(self, alpha: float = 1.0, n_knots: int = 7) -> None:
        """``alpha`` is the L2 penalty; ``n_knots`` the temperature-spline knots."""
        self.alpha = alpha
        self.n_knots = n_knots
        self._models: dict[str, object] = {}
        self._quantiles: pl.DataFrame | None = None

    def _design(self, frame: pl.DataFrame) -> pl.DataFrame:
        return frame.select(
            "local_hour",
            "weekday",
            pl.col("is_holiday").cast(pl.Int8),
            pl.col("is_day_after_holiday").cast(pl.Int8),
            "doy_sin",
            "doy_cos",
            "lag_recent_ratio",
            "lag7_ratio",
            "partial_day_ratio",
            "temp_c",
            "temp_day_mean_c",
            "temp_day_max_c",
        )

    def _pipeline(self) -> object:
        from sklearn.compose import ColumnTransformer  # noqa: PLC0415 - ml extra
        from sklearn.impute import SimpleImputer  # noqa: PLC0415
        from sklearn.linear_model import Ridge  # noqa: PLC0415
        from sklearn.pipeline import make_pipeline  # noqa: PLC0415
        from sklearn.preprocessing import (  # noqa: PLC0415
            OneHotEncoder,
            SplineTransformer,
            StandardScaler,
        )

        temps = ["temp_c", "temp_day_mean_c", "temp_day_max_c"]
        pre = ColumnTransformer(
            [
                ("cat", OneHotEncoder(handle_unknown="ignore"), ["local_hour", "weekday"]),
                (
                    "spline",
                    make_pipeline(
                        SimpleImputer(strategy="median"),
                        SplineTransformer(n_knots=self.n_knots, degree=3),
                    ),
                    temps,
                ),
                (
                    "num",
                    make_pipeline(SimpleImputer(strategy="median"), StandardScaler()),
                    [
                        "is_holiday",
                        "is_day_after_holiday",
                        "doy_sin",
                        "doy_cos",
                        "lag_recent_ratio",
                        "lag7_ratio",
                        "partial_day_ratio",
                    ],
                ),
            ]
        )
        return make_pipeline(pre, Ridge(alpha=self.alpha))

    def fit(self, train: pl.DataFrame) -> None:
        """One pipeline per BA on rows with a level and a target."""
        usable = train.filter(
            pl.col("level_7d_mw").is_not_null() & pl.col("lag7_ratio").is_not_null()
        )
        residuals = []
        for (code,), part in usable.group_by("ba_code"):
            model = self._pipeline()
            x = self._design(part).to_pandas()
            target = (part["y"] / part["level_7d_mw"]).to_numpy()
            model.fit(x, target)  # type: ignore[attr-defined]
            self._models[str(code)] = model
            fitted = np.asarray(model.predict(x)) * part["level_7d_mw"].to_numpy()  # type: ignore[attr-defined]
            residuals.append(part.with_columns(pl.Series("_fit", fitted)))
        recent = pl.concat(residuals)
        recent = recent.filter(
            pl.col("target_day") >= pl.col("target_day").max() - pl.duration(days=365)
        )
        self._quantiles = _residual_quantiles(recent, pl.col("y") / pl.col("_fit"))

    def predict(self, frame: pl.DataFrame, *, context: pl.DataFrame | None = None) -> pl.DataFrame:
        """Point forecast and empirical intervals; null where a BA has no model or level."""
        if self._quantiles is None:
            raise RuntimeError("fit() first")
        yhat = np.full(frame.height, np.nan)
        codes = frame["ba_code"].to_numpy()
        for code, model in self._models.items():
            mask = codes == code
            if not mask.any():
                continue
            part = frame.filter(pl.Series(mask))
            pred: NDArray[np.float64] = np.asarray(model.predict(self._design(part).to_pandas()))  # type: ignore[attr-defined]
            yhat[mask] = pred * part["level_7d_mw"].to_numpy()
        series = pl.Series("yhat", yhat).fill_nan(None)
        return _apply_quantiles(frame, series, self._quantiles)
