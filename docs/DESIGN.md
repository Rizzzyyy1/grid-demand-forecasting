# GridCast — Design

**Day-ahead electricity-demand forecasting for the ten largest US grid regions, benchmarked
every day against the grid operators' own published forecasts.**

Status: built through Phase 7 · Last updated: 2026-09-23

> **Amendments since approval** (each has an ADR): weather is GFS day-2 *temperature only*
> (ADR-0004); results are also scored against a debiased operator forecast (ADR-0005); the feature
> matrix is built in Polars rather than as a dbt mart (ADR-0006); a second, `bulk` latency protocol
> serves the keyless live loop (ADR-0007).

---

## 1. The problem and the claim we want to be able to make

Every US balancing authority (BA) publishes a day-ahead forecast of its hourly demand, and EIA
republishes it next to the demand that actually occurred (form EIA-930). That gives an unusually
honest benchmark: professionals with better data than ours, scored on the same hours.

GridCast answers one question, with evidence:

> *How close can an open pipeline built only from public data get to the operators' day-ahead
> forecasts — in which regions, which seasons, and which hours does it win or lose, and why?*

We **expect to lose in most regions** — operators have real-time telemetry, commercial weather
feeds and knowledge of behind-the-meter solar. Losing by a measured, explained margin is a valid
result; the project is judged on rigor, not on winning.

Non-goals: price forecasting, trading signals, generation-mix forecasting (possible later work).

## 2. Scope

| Item | Decision |
|---|---|
| Regions | Top 10 BAs by average demand: `PJM, MISO, ERCO, SWPP, SOCO, CISO, TVA, NYIS, FPL, ISNE` |
| Target | Hourly demand (MW) for each of the 24 local hours of day **D** (23 / 25 on DST-change days) |
| Issue time | **10:00 local prevailing time on D-1** (horizon 14–38 h) |
| Outputs | Point forecast + 80 % and 95 % prediction intervals, per BA per hour |
| History | EIA-930 from 2019; archived weather forecasts from 2021 (start date verified in Phase 1) |
| Live | A scheduled daily run issues forecasts for tomorrow and scores yesterday |

### Verified facts about the data (checked 2026-09-23, not assumed)

* EIA-930 six-month bulk files (`EIA930_BALANCE_{YYYY}_{Jan_Jun|Jul_Dec}.csv`) download without a
  key, contain 62 BAs, and include `Demand Forecast (MW)` next to `Demand (MW)`. The current file
  is refreshed daily (last modified 2026-09-22), so the live loop needs no API key.
* For Jan–Jun 2025, forecast and demand coverage is ≥ 99.4 % for all ten BAs. The operators'
  MAPE ranges from 1.24 % (SOCO) to 5.35 % (SWPP), with **CISO an outlier at 8.46 %** — to be
  investigated in Phase 1 (candidate causes: behind-the-meter solar, a reporting convention, bad
  hours), not explained away.
* Open-Meteo serves observed weather (archive API) and **archived forecasts as they were issued
  N days before the valid time** (`previous-runs` API, `*_previous_dayN`), without a key.
  A spot check found a gap (2024-01-15 returned no values), so coverage is measured, not assumed.

## 3. The forecasting protocol (the part that makes the numbers trustworthy)

The most common error in public forecasting projects is **information leakage**: training or
scoring with data that would not have existed at issue time. GridCast's protocol:

| Input | What the forecast issued at 10:00 D-1 may use | Why |
|---|---|---|
| Demand history | Hours ending at or before **06:00 local on D-1** | 4-hour publication-latency buffer |
| Weather | Open-Meteo **`previous_day2`** forecasts only | A forecast issued ~48 h before each valid hour of D was issued before D-1 10:00 for *every* hour of D. `previous_day1` would leak for afternoon/evening hours |
| Calendar | Hour, weekday, federal holidays, DST flags | Known in advance |
| Operator forecast | **Never a feature** — only a benchmark | Using it would make the comparison meaningless |

Every feature row carries an `available_at` timestamp; a property-based test asserts
`available_at <= issued_at` for every feature of every forecast. The comparison is conservative
towards the operator: we do not know each BA's exact issue time, so we use information that is
at least as old as theirs is likely to be.

Weather per BA is the **plain mean over 3–6 cities** in its footprint (checked-in config).
Population weighting was the original design; validation showed it hurts (ADR-0004).

## 4. Evaluation

* **Backtest:** rolling origin, expanding window, retrain monthly. Test period **2024-07-01 →
  2026-06-30** (two full years, two summers). Validation for tuning: 2023-07 → 2024-06.
  The test period is not looked at until the model set is frozen (lesson from FinSight's gold
  `test` split).
* **Point metrics:** MAPE, MAE, RMSE per BA; **daily-peak error** (the hour operators care about
  most); skill score vs the operator (`1 − MAE_ours / MAE_operator`).
* **Probabilistic metrics:** pinball loss, empirical coverage of the 80 % / 95 % intervals,
  interval width.
* **Uncertainty:** every headline metric has a 95 % CI from a **moving-block bootstrap over days**
  (hours within a day are correlated; an i.i.d. bootstrap would lie). Ours-vs-operator
  differences get a Diebold–Mariano test.
* **Slices:** BA × season × hour-of-day × weekday/holiday × temperature extremes.
* **Live track record:** from the launch date, every issued forecast is stored immutably and scored
  when the actual demand is published. The live leaderboard never mixes in backtest numbers.
* **Results are generated, never typed:** `scripts/collect_results.py` writes README tables from
  `reports/runs/*/`. Placeholders (`—`) stay until a real run exists.

## 5. Models (each must beat the one above it to earn its complexity)

1. **Seasonal naive** — same hour last week.
2. **Ridge regression** — calendar + weather features (temperature splines for heating/cooling).
3. **LightGBM** — lags, rolling statistics, weather, calendar; one global model across BAs with a
   BA feature, vs per-BA models (ablation). Quantile objectives for intervals.
4. **N-HiTS** (`neuralforecast`, PyTorch, Apple-Silicon MPS) — the deep-learning comparison.
5. **Conformal calibration** — split-conformal on recent residuals to repair interval coverage,
   per BA.
6. **Ensemble** — only if it beats the best single model on validation.

Planned ablations: observed vs forecast weather (quantifies how much "perfect weather" would flatter
the results — the leakage cost), population weighting on/off, global vs per-BA, training-window
length, conformal on/off.

## 6. Architecture

```
            EIA-930 bulk CSVs            Open-Meteo (previous-runs + archive)
                   │                                │
   ┌───────────────▼────────────────────────────────▼──────────────┐
   │ Dagster: daily-partitioned assets, schedules, freshness checks │
   └───────────────┬───────────────────────────────────────────────┘
                   ▼
   data/raw/  (immutable downloads, sha256 manifest)
                   ▼
   dbt (duckdb adapter) → staging → intermediate → marts
     marts: fct_demand_hourly, fct_weather_forecast_hourly, dim_ba, dim_calendar,
            fct_features (point-in-time), fct_forecasts, fct_forecast_scores
     tests: dbt tests + Pandera contracts at the Python boundary
                   ▼
   Training & backtest (LightGBM, N-HiTS, conformal)  ──►  MLflow (tracking + model registry)
                   ▼
   Daily scoring job (Dagster) → fct_forecasts (append-only, immutable)
                   ▼
   FastAPI  /v1/forecast, /v1/scores, /healthz        Evidently drift reports
                   ▼
   Streamlit dashboard: forecast vs actual vs operator, live leaderboard, backtest explorer
```

Everything runs locally via `docker compose up`; Phase 8 deploys the same images to one small
cloud host with Terraform.

### Package layout and dependency rules (enforced by import-linter)

```
src/gridcast/
  core/          # time & DST handling, calendar, BA registry, domain models, Pandera contracts,
                 # settings. Imports nothing internal.
  ingestion/     # eia/, weather/ — HTTP clients (retries, weighted rate limiter), manifests
  warehouse/     # dbt runner, seeds generated from the registry, typed mart reads, data profile
  features/      # point-in-time feature builder (avail__* on every feature) + leakage check
  models/        # Forecaster protocol; baselines, gbm, nhits, conformal (CQR), operator benchmarks
  evaluation/    # rolling-origin engine, metrics & slices, block bootstrap, DM test
  experiments/   # end-to-end runs, ablations, rescoring/combining runs, MLflow logging
  live/          # production model (MLflow registry), daily issuance, append-only store,
                 # live scoring, Evidently drift
  serving/       # FastAPI app (read-only)
  ui/            # Streamlit app (talks only to the API)
  orchestration/ # Dagster definitions (the only package allowed to import everything)
transform/       # dbt project
infra/terraform/ # single-host AWS deployment (ADR-0008)
```

`core` imports nothing internal; `models` and `evaluation` do not import `ingestion`;
nothing imports `orchestration`, `serving` or `ui`.

## 7. Engineering standards (inherited from FinSight)

* Python 3.13, `uv`, Ruff (line length 100), `mypy --strict`, import-linter; `make check` == CI.
* Unit tests are hermetic: HTTP is mocked with recorded fixtures; no network, downloads or keys.
  Costly tests are marked `network` / `slow`.
* Domain models are frozen Pydantic with `extra="forbid"`.
* Every tool and every non-obvious choice has an ADR in `docs/adr/`.
* A check that passes must say how much it checked (e.g. `hours_checked=…`).

## 8. Risks

| Risk | Mitigation |
|---|---|
| Archived weather forecasts start later than expected, or have gaps | Measure coverage in Phase 1; fall back to observed weather *only* as a labelled ablation |
| EIA data errors / outliers (spikes, zeros, reporting changes) | Documented cleaning rules in dbt, with counts of rows affected; evaluate on raw vs cleaned |
| DST days (23/25 hours) break shapes | `core/time.py` owns all conversions; property tests over DST boundaries |
| Test-set peeking | Test period locked; `reports/` records when it was first evaluated |
| Operator issue times unknown | Conservative protocol (§3); stated as a caveat in every results table |

## 9. What we will not claim

* Not "beats the grid operators" unless a CI and a DM test say so, per region.
* No backtest number presented as live performance.
* No figures in the README that are not generated from `reports/runs/`.
