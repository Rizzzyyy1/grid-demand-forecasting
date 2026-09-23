# ADR-0003: A model ladder — each model must beat the one below it

Status: Accepted · 2026-09-23

## Decision
Seasonal naive → ridge → LightGBM (quantile) → N-HiTS, with split-conformal calibration of
intervals and an ensemble only if it wins on validation. Complexity is kept only when the
validation CI shows it pays. The test period is evaluated once, after the model set is frozen.

## Why N-HiTS
It is designed for multi-horizon forecasting with multi-rate sampling, trains quickly on CPU/MPS,
and `neuralforecast` supports exogenous features and quantile losses. A time-series foundation
model (e.g. Chronos) is a possible later ablation, not part of the core.
