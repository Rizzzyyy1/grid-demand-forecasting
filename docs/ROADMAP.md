# GridCast — Roadmap

Each phase ends with a checkable exit criterion. "Overnight" marks the phases targeted for the
first unattended build; everything after needs the owner (accounts, review, calendar time).

| Phase | Theme | Overnight | Status (2026-09-23) |
|---|---|---|---|
| 0 | Foundations | ✅ | ✅ done |
| 1 | Ingestion + data profiling | ✅ | ✅ done (weather archive: see note) |
| 2 | dbt models + data quality | ✅ | ✅ done |
| 3 | Point-in-time features + backtest engine | ✅ | ✅ done |
| 4 | Baselines, LightGBM, MLflow, validation results | ✅ | ✅ done (`reports/runs/*-ladder-v3/`) |
| 5 | N-HiTS, conformal intervals, ablations | stretch | ✅ done (CQR coverage within ±3 pp in all BAs; `reports/ablations/`) |
| 6 | Daily live loop (Dagster schedules), API, dashboard | stretch | ✅ done (live forecasts stored from 2026-09-24; scoring once actuals publish) |
| 7 | Monitoring (Evidently), Docker Compose stack verified end-to-end | — | code done; stack verified locally |
| 8 | Cloud deploy with Terraform, CD | — | AWS IaC `tofu validate`d, **intentionally not deployed (cost)**; live system on GitHub Actions + Pages (ADR-0009) |
| 9 | Test-set results, write-up, blog post, demo video | — (needs owner) | ⬜ (test split locked, untouched) |

Note: the full 47-city weather archive costs roughly one day of Open-Meteo's free-tier quota;
the downloader is quota-aware and resumable, so a partial backfill finishes on the next run.

## Phase 0 — Foundations
**Build:** `uv` project, package skeleton (§6 of DESIGN), settings, domain models, `core/time.py`
with DST handling, Makefile, Ruff/mypy/import-linter/pytest, pre-commit, GitHub Actions CI,
`CLAUDE.md`, ADR template + ADRs 0001–0003.
**Exit:** `make check` passes on a fresh clone; the DST property tests pass.

## Phase 1 — Ingestion + profiling
**Build:** EIA bulk downloader (idempotent, sha256 manifest, resumable); Open-Meteo client for
`previous_day2` forecasts and observed weather (rate-limited, cached); BA→cities config with
population sources; `gridcast ingest`.
**Exit:** 2019→today EIA files and 2021→today weather for all 10 BAs on disk; a re-run downloads
nothing; `reports/data_profile.md` states row counts, coverage per BA/year, the first date archived
weather forecasts exist, and the CISO operator-error finding (explained or flagged open).

## Phase 2 — dbt + data quality
**Build:** staging/intermediate/marts (DESIGN §6); cleaning rules with affected-row counts;
dbt tests; Pandera contracts; DST-aware local-hour keys.
**Exit:** `dbt build` green; an injected malformed file fails with a readable error; every
cleaning rule reports how many rows it touched.

## Phase 3 — Features + backtest engine
**Build:** feature builders with `available_at`; the leakage property test; rolling-origin
backtest engine with a `Forecaster` protocol; metrics, block bootstrap, DM test.
**Exit:** the leakage test passes across ≥ 10,000 sampled forecasts and says how many it checked;
a deliberately leaky feature makes it fail.

## Phase 4 — Baselines + LightGBM
**Build:** seasonal naive, ridge, LightGBM (global and per-BA, quantile); MLflow tracking;
`gridcast backtest --split validation`; `scripts/collect_results.py`.
**Exit:** validation-period results table (ours vs operator, per BA, with CIs) generated from run
files. The test period is **not** evaluated yet.

## Phase 5 — Deep model, intervals, ablations
**Build:** N-HiTS (MPS), conformal calibration, the ablations in DESIGN §5.
**Exit:** ablation table with CIs; interval coverage within ±3 pp of nominal on validation, or a
documented reason why not.

## Phase 6 — Live loop, API, dashboard
**Build:** Dagster schedule (daily ingest → forecast for D+1 → score D-1); append-only forecast
store; FastAPI; Streamlit dashboard with a live leaderboard.
**Exit:** two consecutive scheduled runs produce and score forecasts with no manual steps; the
API and UI are driven in a real browser, not only tested against fakes.

## Phase 7 — Monitoring + container stack
**Build:** Evidently drift reports; Docker Compose (Dagster webserver + daemon, MLflow, API, UI).
**Exit:** `docker compose up` on a clean machine reaches a working dashboard.

## Phase 8 — Cloud
**Build:** Terraform for one small host + object storage + budget alarm; CD on tag.
**Exit:** public URL; `terraform destroy` and re-apply reproduces it; monthly cost stated.

## Phase 9 — Results + write-up
**Build:** freeze models → one-time test-period evaluation; error analysis; README; blog post.
**Exit:** every README number traces to `reports/runs/`; live track record ≥ 30 days.
