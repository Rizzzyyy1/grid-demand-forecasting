"""LightGBM forecaster: one global model across BAs (or one per BA), point + quantile heads.

The target is demand relative to the BA's recent level (``y / level_7d_mw``) so a single model
can learn shapes shared across regions; ``ba_code`` is a categorical feature. Raw-MW features are
excluded for the same reason. Quantile heads (0.025, 0.1, 0.9, 0.975) give the intervals; they are
sorted after prediction so the four quantiles never cross.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import polars as pl

from gridcast.features.build import FEATURE_COLUMNS
from gridcast.models.base import QUANTILES

RAW_MW = {
    "level_7d_mw",
    "lag_recent_mw",
    "lag7_mw",
    "recent_peak_mw",
    "partial_day_mean_mw",
    "last_known_mw",
}
GBM_FEATURES = tuple(f for f in FEATURE_COLUMNS if f not in RAW_MW)


@dataclass
class GBMParams:
    """LightGBM hyper-parameters (validation-tuned values live in the run config)."""

    n_estimators: int = 700
    learning_rate: float = 0.04
    num_leaves: int = 63
    min_child_samples: int = 100
    subsample: float = 0.8
    subsample_freq: int = 1
    colsample_bytree: float = 0.8
    reg_lambda: float = 1.0
    quantile_estimators: int = 400
    seed: int = 7
    extra: dict[str, Any] = field(default_factory=dict)

    def common(self) -> dict[str, Any]:
        """Keyword arguments shared by every head."""
        return {
            "learning_rate": self.learning_rate,
            "num_leaves": self.num_leaves,
            "min_child_samples": self.min_child_samples,
            "subsample": self.subsample,
            "subsample_freq": self.subsample_freq,
            "colsample_bytree": self.colsample_bytree,
            "reg_lambda": self.reg_lambda,
            "random_state": self.seed,
            "deterministic": True,
            "force_row_wise": True,
            "n_jobs": -1,
            "verbose": -1,
            **self.extra,
        }


class LightGBMForecaster:
    """Global (``per_ba=False``) or per-BA gradient-boosted trees with quantile heads."""

    def __init__(
        self, params: GBMParams | None = None, per_ba: bool = False, quantiles: bool = True
    ) -> None:
        """Configure; nothing is trained until ``fit``."""
        self.params = params or GBMParams()
        self.per_ba = per_ba
        self.quantiles = quantiles
        self.name = "lgbm_per_ba" if per_ba else "lgbm_global"
        self._heads: dict[str, dict[str, Any]] = {}
        self._categories: list[str] = []
        self.feature_importance: dict[str, float] = {}

    def _x(self, frame: pl.DataFrame) -> Any:
        x = frame.select(*GBM_FEATURES, "ba_code").to_pandas()
        for col in ("is_weekend", "is_holiday", "is_day_after_holiday"):
            x[col] = x[col].astype("int8")
        import pandas as pd  # noqa: PLC0415 - ml extra

        x["ba_code"] = pd.Categorical(x["ba_code"], categories=self._categories)
        return x

    def _fit_group(self, part: pl.DataFrame) -> dict[str, Any]:
        import lightgbm as lgb  # noqa: PLC0415 - ml extra

        x = self._x(part)
        target = (part["y"] / part["level_7d_mw"]).to_numpy()
        heads: dict[str, Any] = {}
        point = lgb.LGBMRegressor(
            objective="l2", n_estimators=self.params.n_estimators, **self.params.common()
        )
        point.fit(x, target, categorical_feature=["ba_code"])
        heads["yhat"] = point
        if self.quantiles:
            for name, tau in QUANTILES.items():
                head = lgb.LGBMRegressor(
                    objective="quantile",
                    alpha=tau,
                    n_estimators=self.params.quantile_estimators,
                    **self.params.common(),
                )
                head.fit(x, target, categorical_feature=["ba_code"])
                heads[name] = head
        return heads

    def fit(self, train: pl.DataFrame) -> None:
        """Fit on rows with a level (the scale) and a target."""
        usable = train.filter(pl.col("level_7d_mw").is_not_null() & pl.col("y").is_not_null())
        self._categories = sorted(usable["ba_code"].unique().to_list())
        if self.per_ba:
            for (code,), part in usable.group_by("ba_code"):
                self._heads[str(code)] = self._fit_group(part)
        else:
            self._heads["*"] = self._fit_group(usable)
        gains: dict[str, float] = {}
        for heads in self._heads.values():
            booster = heads["yhat"].booster_
            for fname, gain in zip(
                booster.feature_name(), booster.feature_importance("gain"), strict=True
            ):
                gains[fname] = gains.get(fname, 0.0) + float(gain)
        total = sum(gains.values()) or 1.0
        self.feature_importance = {
            k: v / total for k, v in sorted(gains.items(), key=lambda kv: -kv[1])
        }

    def predict(self, frame: pl.DataFrame, *, context: pl.DataFrame | None = None) -> pl.DataFrame:
        """Point forecast and non-crossing quantiles, scaled back to MW."""
        if not self._heads:
            raise RuntimeError("fit() first")
        names = ["yhat", *(QUANTILES if self.quantiles else [])]
        out = {n: np.full(frame.height, np.nan) for n in names}
        level = frame["level_7d_mw"].to_numpy()
        groups = (
            [(code, frame["ba_code"].to_numpy() == code) for code in self._heads]
            if self.per_ba
            else [("*", np.ones(frame.height, dtype=bool))]
        )
        for key, mask in groups:
            if not mask.any():
                continue
            x = self._x(frame.filter(pl.Series(mask)))
            for n in names:
                out[n][mask] = self._heads[key][n].predict(x) * level[mask]
        if self.quantiles:
            stacked = np.sort(np.vstack([out[q] for q in QUANTILES]), axis=0)
            for i, q in enumerate(QUANTILES):
                out[q] = stacked[i]
        return pl.DataFrame({n: out[n] for n in names}).fill_nan(None)
