# ADR-0004: Weather inputs — GFS day-2 temperature only, plain city mean

Status: Accepted · 2026-09-23

## Context
Verified against the Open-Meteo Previous Runs API on 2026-09-23:

* `*_previous_day2` is "the value predicted 48 hours before valid time" (provider docs).
* Only **GFS 2 m temperature** is archived before 2024: non-null from **2021-03-25**. Dew point,
  humidity, cloud, wind and radiation are null until **2024-01-20**.
* For US points the default model returned values identical to `gfs_seamless` (Dallas, Dec 2023
  and Jan 2025), so pinning the model changes nothing but makes the archive explicit.
* The free tier counts a request spanning more than 14 days as several calls and allows about
  10,000 calls per day; the full 47-city archive costs roughly one day's budget.

## Decision
* Models use **forecast temperature only** (plus derived heating/cooling degrees and the
  cross-city spread). Other variables are a post-2024 ablation.
* Request `models=gfs_seamless`; one raw JSON file per (city, month); resumable, weighted
  rate-limiting persisted across processes; newest months first.
* A value at hour-ending instant *T* becomes available at *T − 48 h + 6 h* (a generous allowance
  for GFS publication latency). For the last hour of a 25-hour day this is still ≥ 3 h before
  the 10:00 D-1 issue time, so no hour of the target day leaks.
* BA weather = **plain mean** over 3–6 cities. *Amended 2026-09-23:* the original choice was a
  population-weighted mean; the ablation (`reports/ablations/20260923T132504Z`) found the plain
  mean significantly better (skill +0.032, 95 % CI [+0.016, +0.046], DM p = 0.00016). The
  approximate weights let one metro dominate (New York carries 84 % of the NYIS weight), while
  demand responds to weather across the whole footprint. The weighted mean remains available as
  an ablation (`--population-weighted`).

## Consequences
* Training starts in April 2021, not 2019, for any model that uses weather.
* Percentages in the archive can exceed 100 (cloud cover = 101 seen); staging clamps them.
