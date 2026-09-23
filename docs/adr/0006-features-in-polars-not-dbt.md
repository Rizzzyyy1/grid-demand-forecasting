# ADR-0006: Point-in-time features are built in Python (Polars), not in dbt

Status: Accepted · 2026-09-23

## Context
DESIGN §6 listed `fct_features` as a dbt mart. Feature correctness here is dominated by one
property — nothing may be used before it was available — which needs property-based tests over
thousands of random forecast origins, deliberately-leaky counter-examples, and the same code path
at training, backtest and serving time.

## Decision
dbt owns cleaning and conformed marts (`fct_demand_hourly`, `fct_weather_forecast_hourly`,
`dim_calendar`). `gridcast.features` builds the feature matrix per forecast origin in Polars,
attaching an `available_at` to every input value, and a Hypothesis test asserts
`available_at <= issued_at` across ≥ 10,000 sampled forecasts.

## Consequences
* One feature implementation serves backtests, the daily live run and the API.
* dbt keeps what SQL does best (joins, cleaning, tests with row counts); Python keeps what needs
  unit tests and property tests.
