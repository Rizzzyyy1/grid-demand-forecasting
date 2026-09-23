# ADR-0001: Benchmark against the operators' day-ahead forecasts under a conservative protocol

Status: Accepted · 2026-09-23

## Context
Forecasting projects usually report error against naive baselines, which says little about
whether the forecast is useful. EIA-930 publishes each balancing authority's own day-ahead
forecast alongside actual demand, so a professional benchmark exists for free. The operators'
exact issue times are not published.

## Decision
The primary metric is error relative to the operator forecast on the same hours. Our forecasts are
issued at 10:00 local on D-1 using demand up to 06:00 D-1 and Open-Meteo `previous_day2` weather
forecasts only. The operator forecast is never a model feature.

## Consequences
* The comparison is conservative: we use information at least as old as the operators' probably is.
* We expect to lose in many regions; results are reported with CIs and DM tests either way.
* `previous_day1` weather would be fresher but leaks for hours after 10:00 on D; rejected.
