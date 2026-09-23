"""N-HiTS (``neuralforecast``) as a ``Forecaster``: one global network over all BA series.

The network sees each BA's hourly demand up to the origin's ``demand_cutoff`` and forecasts
``HORIZON`` hours ahead, conditioned on "future-known" exogenous inputs (the day-2 temperature
forecast and calendar terms). Only the hours of the target day are kept.

Point-in-time discipline lives here, not in the feature builder: for every target day the input
series is truncated at that origin's cutoff, and ``predict`` asserts it. Hours after the cutoff are
never used, even though ``context`` / ``frame`` carry their actuals.
"""

from __future__ import annotations

import logging
import math
import warnings
from datetime import date, datetime
from typing import Any

import polars as pl

HORIZON = 44  # 06:00 D-1 cutoff -> end of a 25-hour day D is at most 43 hours ahead
EXOG = ("temp_c", "hour_sin", "hour_cos", "weekday", "is_holiday", "is_weekend")


def climatology(rows: pl.DataFrame) -> pl.DataFrame:
    """Mean forecast temperature per (BA, month, local hour) - used to fill weather gaps."""
    return (
        rows.filter(pl.col("temp_c").is_not_null())
        .group_by("ba_code", "month", "local_hour")
        .agg(pl.col("temp_c").mean().alias("_clim"))
    )


def _series_frame(rows: pl.DataFrame, clim: pl.DataFrame | None = None) -> pl.DataFrame:
    """Hourly panel (one row per BA-hour) with target and exogenous inputs, gaps filled.

    Missing temperatures are filled from ``clim`` (training-period climatology), *not* forward
    filled: a weeks-long archive gap (2023-12-30 -> 2024-01-20) forward-filled gives a constant
    input window, whose zero spread makes the robust scaler explode on the first real values.
    """
    if clim is not None:
        rows = rows.join(clim, on=["ba_code", "month", "local_hour"], how="left").with_columns(
            pl.coalesce("temp_c", "_clim").alias("temp_c")
        )
    panel = (
        rows.select(
            "ba_code",
            "hour_ending_utc",
            "y",
            "temp_c",
            (2 * math.pi * pl.col("local_hour").cast(pl.Float64) / 24).sin().alias("hour_sin"),
            (2 * math.pi * pl.col("local_hour").cast(pl.Float64) / 24).cos().alias("hour_cos"),
            pl.col("weekday").cast(pl.Float64),
            pl.col("is_holiday").cast(pl.Float64),
            pl.col("is_weekend").cast(pl.Float64),
        )
        .unique(subset=["ba_code", "hour_ending_utc"], keep="last")
        .sort("ba_code", "hour_ending_utc")
    )
    # a regular hourly grid per BA; missing hours are forward-filled (past values only)
    grids = []
    for (code,), part in panel.group_by("ba_code"):
        first, last = part["hour_ending_utc"].min(), part["hour_ending_utc"].max()
        if not isinstance(first, datetime) or not isinstance(last, datetime):
            continue
        full = pl.datetime_range(first, last, "1h", eager=True, time_zone="UTC")
        grid = (
            pl.DataFrame({"hour_ending_utc": full})
            .join(part, on="hour_ending_utc", how="left")
            .with_columns(pl.lit(code).alias("ba_code"))
        )
        grids.append(grid.with_columns(pl.exclude("ba_code", "hour_ending_utc").forward_fill()))
    return pl.concat(grids).with_columns(pl.col("temp_c").fill_null(strategy="backward"))


def _to_nf(panel: pl.DataFrame) -> Any:
    return (
        panel.with_columns(pl.col("hour_ending_utc").dt.replace_time_zone(None).alias("ds"))
        .rename({"ba_code": "unique_id"})
        .select("unique_id", "ds", "y", *EXOG)
        .to_pandas()
    )


class NHiTSForecaster:
    """Global N-HiTS with multi-quantile loss (median, 80 % and 95 % intervals)."""

    name = "nhits"

    def __init__(
        self,
        max_steps: int = 800,
        input_size: int = 7 * 24,
        seed: int = 1,
        accelerator: str = "cpu",
    ) -> None:
        """Hyper-parameters; CPU is as fast as Apple MPS at this size and is deterministic."""
        self.max_steps = max_steps
        self.input_size = input_size
        self.seed = seed
        self.accelerator = accelerator
        self._nf: Any = None
        self._train_panel: pl.DataFrame | None = None
        self.max_input_hour_checked: int = 0
        self.abstained: int = 0
        self._clim: pl.DataFrame | None = None
        self._y_max: float = float("inf")

    def _model(self) -> Any:
        import torch  # noqa: PLC0415 - deep extra
        from neuralforecast.losses.pytorch import MQLoss  # noqa: PLC0415
        from neuralforecast.models import NHITS  # noqa: PLC0415

        # LightGBM (Homebrew libomp) and PyTorch (bundled libomp) in one process deadlock inside
        # PyTorch's parallel kernels on macOS once LightGBM has run. One intra-op thread avoids
        # the second OpenMP runtime entirely and costs nothing at this model size.
        torch.set_num_threads(1)

        return NHITS(
            h=HORIZON,
            input_size=self.input_size,
            futr_exog_list=list(EXOG),
            loss=MQLoss(level=[80, 95]),
            max_steps=self.max_steps,
            scaler_type="robust",
            batch_size=16,
            windows_batch_size=256,
            random_seed=self.seed,
            accelerator=self.accelerator,
            enable_progress_bar=False,
            enable_model_summary=False,
            logger=False,
        )

    def fit(self, train: pl.DataFrame) -> None:
        """Train on every BA series in ``train`` (hours with known actuals)."""
        from neuralforecast import NeuralForecast  # noqa: PLC0415 - deep extra

        logging.getLogger("lightning.pytorch").setLevel(logging.ERROR)
        logging.getLogger("pytorch_lightning").setLevel(logging.ERROR)
        self._clim = climatology(train)
        panel = _series_frame(train.filter(pl.col("y").is_not_null()), self._clim)
        self._train_panel = panel
        self._y_max = float(train["y"].max())  # type: ignore[arg-type]
        self._nf = NeuralForecast(models=[self._model()], freq="h")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            self._nf.fit(_to_nf(panel), val_size=0)

    def predict(self, frame: pl.DataFrame, *, context: pl.DataFrame | None = None) -> pl.DataFrame:
        """One network call per target day, each on series truncated at that day's cutoff."""
        if self._nf is None or self._train_panel is None:
            raise RuntimeError("fit() first")
        pieces = [frame] + ([context] if context is not None else [])
        known = pl.concat([p.select(frame.columns) for p in pieces], how="vertical_relaxed")
        panel = (
            pl.concat([self._train_panel, _series_frame(known, self._clim)], how="vertical_relaxed")
            .unique(subset=["ba_code", "hour_ending_utc"], keep="last")
            .sort("ba_code", "hour_ending_utc")
        )
        out: list[pl.DataFrame] = []
        for (day,), rows in frame.group_by("target_day", maintain_order=True):
            out.append(self._predict_day(panel, rows, day))
        preds = pl.concat(out)
        # sanity net: a forecast above 3x the largest demand seen in training is a numerical
        # failure, not a forecast - abstain (null) and count it so it cannot poison the metrics
        bad = pl.col("yhat") > 3 * self._y_max
        self.abstained += int(preds.select(bad.sum()).item())
        preds = preds.with_columns(
            [
                pl.when(bad).then(None).otherwise(pl.col(c)).alias(c)
                for c in ("yhat", "q10", "q90", "q025", "q975")
            ]
        )
        return (
            frame.select("ba_code", "hour_ending_utc")
            .join(preds, on=["ba_code", "hour_ending_utc"], how="left", maintain_order="left")
            .select("yhat", "q10", "q90", "q025", "q975")
        )

    def _predict_day(self, panel: pl.DataFrame, rows: pl.DataFrame, day: date) -> pl.DataFrame:
        cutoffs = rows.group_by("ba_code").agg(pl.col("demand_cutoff").first())
        history = panel.join(cutoffs, on="ba_code").filter(
            pl.col("hour_ending_utc") <= pl.col("demand_cutoff")
        )
        # enforce the protocol explicitly: no input hour after its origin's cutoff
        latest = history.group_by("ba_code").agg(
            (pl.col("hour_ending_utc").max() <= pl.col("demand_cutoff").first()).alias("ok")
        )
        if not latest["ok"].all():
            raise AssertionError(f"N-HiTS input extends past the demand cutoff for {day}")
        self.max_input_hour_checked += history.height
        # exactly HORIZON hours after each series' last input hour; exogenous values past the end
        # of the data are forward-filled (those hours lie beyond the target day and are dropped)
        last = history.group_by("ba_code").agg(pl.col("hour_ending_utc").max().alias("_last"))
        grid = last.with_columns(
            pl.datetime_ranges(
                pl.col("_last") + pl.duration(hours=1),
                pl.col("_last") + pl.duration(hours=HORIZON),
                "1h",
            ).alias("hour_ending_utc")
        ).explode("hour_ending_utc", empty_as_null=False)
        future = (
            grid.join(panel.drop("y"), on=["ba_code", "hour_ending_utc"], how="left")
            .sort("ba_code", "hour_ending_utc")
            .with_columns(
                pl.exclude("ba_code", "hour_ending_utc", "_last").forward_fill().over("ba_code")
            )
            .with_columns(pl.lit(0.0).alias("y"))
            .drop("_last")
        )
        hist_nf = _to_nf(history.drop("demand_cutoff"))
        fut_nf = _to_nf(future).drop(columns=["y"])
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            pred = self._nf.predict(df=hist_nf, futr_df=fut_nf)
        result = pl.from_pandas(pred).select(
            pl.col("unique_id").alias("ba_code"),
            pl.col("ds")
            .dt.replace_time_zone("UTC")
            .cast(pl.Datetime("us", "UTC"))
            .alias("hour_ending_utc"),
            pl.col("NHITS-median").alias("yhat"),
            pl.col("NHITS-lo-80").alias("q10"),
            pl.col("NHITS-hi-80").alias("q90"),
            pl.col("NHITS-lo-95").alias("q025"),
            pl.col("NHITS-hi-95").alias("q975"),
        )
        return result.join(
            rows.select("ba_code", "hour_ending_utc"), on=["ba_code", "hour_ending_utc"]
        )
