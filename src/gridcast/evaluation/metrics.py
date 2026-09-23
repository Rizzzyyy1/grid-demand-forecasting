"""Forecast accuracy metrics on a scored frame (forecasts joined to actuals).

A *scored* frame has at least: ``ba_code, target_day, hour_ending_utc, model, yhat, y`` and
optionally the quantile columns. Only hours with a non-null actual and forecast are scored.
"""

from __future__ import annotations

import polars as pl

INTERVALS = {"80": ("q10", "q90", 0.10, 0.90), "95": ("q025", "q975", 0.025, 0.975)}


def score(
    forecasts: pl.DataFrame, actuals: pl.DataFrame, common_support: bool = True
) -> pl.DataFrame:
    """Join forecasts to actuals and keep only scorable hours.

    With ``common_support`` (the default) an hour is scored only if *every* model forecast it,
    so models are always compared on identical hours.
    """
    scored = (
        forecasts.join(
            actuals.select("ba_code", "hour_ending_utc", "y"),
            on=["ba_code", "hour_ending_utc"],
            how="inner",
        )
        .filter(pl.col("y").is_not_null() & pl.col("yhat").is_not_null() & (pl.col("y") > 0))
        .with_columns(
            (pl.col("yhat") - pl.col("y")).alias("err"),
            (pl.col("yhat") - pl.col("y")).abs().alias("abs_err"),
        )
    )
    if common_support:
        n_models = forecasts["model"].n_unique()
        keep = (
            scored.group_by("ba_code", "hour_ending_utc")
            .agg(pl.col("model").n_unique().alias("_n"))
            .filter(pl.col("_n") == n_models)
            .select("ba_code", "hour_ending_utc")
        )
        scored = scored.join(keep, on=["ba_code", "hour_ending_utc"], how="semi")
    return scored


def point_metrics(scored: pl.DataFrame, by: tuple[str, ...] = ("ba_code", "model")) -> pl.DataFrame:
    """MAE, RMSE, MAPE, bias and the number of hours scored, per group."""
    return (
        scored.group_by(*by)
        .agg(
            pl.len().alias("hours"),
            pl.col("abs_err").mean().alias("mae"),
            (pl.col("err") ** 2).mean().sqrt().alias("rmse"),
            (100 * pl.col("abs_err") / pl.col("y")).mean().alias("mape"),
            (100 * pl.col("err") / pl.col("y")).mean().alias("bias_pct"),
        )
        .sort(*by)
    )


def peak_metrics(scored: pl.DataFrame, by: tuple[str, ...] = ("ba_code", "model")) -> pl.DataFrame:
    """Daily-peak magnitude error (%) and how often the peak hour is off by more than one hour."""
    daily = scored.group_by(*by, "target_day").agg(
        pl.col("y").max().alias("peak"),
        pl.col("yhat").max().alias("peak_hat"),
        pl.col("hour_ending_utc").sort_by("y").last().alias("peak_hour"),
        pl.col("hour_ending_utc").sort_by("yhat").last().alias("peak_hour_hat"),
        pl.len().alias("n"),
    )
    daily = daily.filter(pl.col("n") >= 20)  # only days with (nearly) all hours scored
    return (
        daily.group_by(*by)
        .agg(
            pl.len().alias("days"),
            (100 * (pl.col("peak_hat") - pl.col("peak")).abs() / pl.col("peak"))
            .mean()
            .alias("peak_ape"),
            ((pl.col("peak_hour_hat") - pl.col("peak_hour")).abs() > pl.duration(hours=1))
            .mean()
            .mul(100)
            .alias("peak_hour_miss_pct"),
        )
        .sort(*by)
    )


def pinball(y: pl.Expr, q: pl.Expr, tau: float) -> pl.Expr:
    """Pinball (quantile) loss of quantile forecast ``q`` at level ``tau``."""
    diff = y - q
    return pl.max_horizontal(tau * diff, (tau - 1) * diff)


def interval_metrics(
    scored: pl.DataFrame, by: tuple[str, ...] = ("ba_code", "model")
) -> pl.DataFrame:
    """Empirical coverage, mean width (% of demand) and mean pinball loss per interval."""
    exprs: list[pl.Expr] = []
    for label, (lo, hi, tau_lo, tau_hi) in INTERVALS.items():
        inside = (pl.col("y") >= pl.col(lo)) & (pl.col("y") <= pl.col(hi))
        exprs += [
            (100 * inside.cast(pl.Float64)).mean().alias(f"coverage_{label}"),
            (100 * (pl.col(hi) - pl.col(lo)) / pl.col("y")).mean().alias(f"width_{label}_pct"),
            (
                (
                    pinball(pl.col("y"), pl.col(lo), tau_lo)
                    + pinball(pl.col("y"), pl.col(hi), tau_hi)
                )
                / 2
            )
            .mean()
            .alias(f"pinball_{label}"),
        ]
    with_q = scored.filter(pl.col("q10").is_not_null() & pl.col("q975").is_not_null())
    if with_q.is_empty():
        return pl.DataFrame()
    return with_q.group_by(*by).agg(pl.len().alias("hours"), *exprs).sort(*by)


def skill(point: pl.DataFrame, reference: str, metric: str = "mae") -> pl.DataFrame:
    """``1 - metric_model / metric_reference`` per BA (positive = better than the reference)."""
    ref = point.filter(pl.col("model") == reference).select("ba_code", pl.col(metric).alias("_ref"))
    return (
        point.join(ref, on="ba_code", how="left")
        .with_columns((1 - pl.col(metric) / pl.col("_ref")).alias(f"skill_vs_{reference}"))
        .drop("_ref")
    )


def slice_metrics(scored: pl.DataFrame, features: pl.DataFrame) -> pl.DataFrame:
    """MAPE by model over the slices of DESIGN section 4, pooled across BAs.

    Slices: season, local-hour block, day type, and temperature extremes (days whose forecast
    daily-mean temperature is in the top / bottom 5 % for that BA within the scored window).
    """
    keys = features.select(
        "ba_code",
        "hour_ending_utc",
        "local_hour",
        "month",
        "is_weekend",
        "is_holiday",
        "temp_day_mean_c",
    )
    frame = scored.join(keys, on=["ba_code", "hour_ending_utc"], how="left").with_columns(
        pl.col("month")
        .replace_strict(
            {
                12: "winter",
                1: "winter",
                2: "winter",
                3: "spring",
                4: "spring",
                5: "spring",
                6: "summer",
                7: "summer",
                8: "summer",
            },
            default="autumn",
        )
        .alias("season"),
        (pl.col("local_hour") // 6 * 6).cast(pl.String).str.zfill(2).alias("hour_block"),
        pl.when(pl.col("is_holiday"))
        .then(pl.lit("holiday"))
        .when(pl.col("is_weekend"))
        .then(pl.lit("weekend"))
        .otherwise(pl.lit("weekday"))
        .alias("day_type"),
    )
    hi = pl.col("temp_day_mean_c").quantile(0.95).over("ba_code", "model")
    lo = pl.col("temp_day_mean_c").quantile(0.05).over("ba_code", "model")
    frame = frame.with_columns(
        pl.when(pl.col("temp_day_mean_c").is_null())
        .then(pl.lit("no weather"))
        .when(pl.col("temp_day_mean_c") >= hi)
        .then(pl.lit("hot 5%"))
        .when(pl.col("temp_day_mean_c") <= lo)
        .then(pl.lit("cold 5%"))
        .otherwise(pl.lit("normal"))
        .alias("temperature")
    )
    parts = []
    for dim in ("season", "hour_block", "day_type", "temperature"):
        parts.append(
            frame.group_by("model", dim)
            .agg(
                pl.len().alias("hours"),
                (100 * pl.col("abs_err") / pl.col("y")).mean().alias("mape"),
            )
            .rename({dim: "value"})
            .with_columns(pl.lit(dim).alias("slice"))
            .select("slice", "value", "model", "hours", "mape")
        )
    return pl.concat(parts).sort("slice", "value", "model")
