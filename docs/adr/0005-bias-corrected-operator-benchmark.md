# ADR-0005: Report skill against the raw *and* a bias-corrected operator forecast

Status: Accepted · 2026-09-23

## Context
Profiling (reports/data_profile.md §5) found two operator series whose error is dominated by a
systematic offset rather than forecasting skill:

* **CISO** under-forecasts EIA-reported demand by ~20 % in solar hours, growing every year since
  2020. The cause is unconfirmed (EIA's battery column is empty for CISO).
* **SWPP** jumps from about −1 % to about +8 % bias between April and May 2025 — a step change.

Skill against these raw series would flatter any model trained on EIA's demand definition.

## Decision
Every results table reports two benchmarks:

1. **Operator (raw)** — as published.
2. **Operator (debiased)** — the operator forecast minus its trailing 28-day mean error for the
   same local hour, computed only from hours whose actuals were available at issue time
   (hour ending ≤ 06:00 D-1). This is a cheap correction any user of the operator's forecast
   could apply, so beating it is the stronger claim.

Headline claims use the debiased benchmark.

## Consequences
The benchmark shares the forecasting protocol and its `available_at` guarantees; it is
implemented as a `Forecaster` like any model so it cannot accidentally see the future.
