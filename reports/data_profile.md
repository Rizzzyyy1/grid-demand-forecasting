# GridCast data profile

Generated 2026-09-23 13:19 UTC by `gridcast profile` from `warehouse.duckdb` and the raw-file manifests. Do not edit by hand.

## 1. Raw inventory

| source | files | closed | MB |
|---|---|---|---|
| eia | 16 | 15 | 685.2 |
| weather/forecast_d2 | 3283 | 3234 | 113.6 |

## 2. Demand rows and coverage per BA

`target_pct` = share of hours with a usable reported demand (the scoring target); `operator_pct` = share with a usable operator day-ahead forecast.

| ba_code | hours | first_day | last_day | target_pct | operator_pct |
|---|---|---|---|---|---|
| CISO | 67727 | 2019-01-01 | 2026-09-22 | 99.74 | 99.82 |
| ERCO | 67727 | 2019-01-01 | 2026-09-22 | 99.89 | 99.92 |
| FPL | 67727 | 2019-01-01 | 2026-09-22 | 98.78 | 99.72 |
| ISNE | 67727 | 2019-01-01 | 2026-09-22 | 99.94 | 99.98 |
| MISO | 67728 | 2019-01-01 | 2026-09-22 | 99.86 | 99.86 |
| NYIS | 67727 | 2019-01-01 | 2026-09-22 | 99.94 | 99.73 |
| PJM | 67727 | 2019-01-01 | 2026-09-22 | 99.67 | 99.65 |
| SOCO | 67727 | 2019-01-01 | 2026-09-22 | 99.91 | 99.95 |
| SWPP | 67727 | 2019-01-01 | 2026-09-22 | 99.92 | 99.12 |
| TVA | 67727 | 2019-01-01 | 2026-09-22 | 99.94 | 99.90 |

Target coverage (%) by year:

| ba_code | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|---|---|
| CISO | 99.9 | 99.9 | 99.9 | 100.0 | 100.0 | 99.5 | 99.4 | 99.2 |
| ERCO | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 99.5 | 99.6 |
| FPL | 99.9 | 99.7 | 99.8 | 93.6 | 98.7 | 99.1 | 100.0 | 99.6 |
| ISNE | 100.0 | 100.0 | 99.9 | 100.0 | 100.0 | 100.0 | 99.9 | 99.6 |
| MISO | 99.9 | 100.0 | 100.0 | 100.0 | 100.0 | 99.7 | 99.7 | 99.4 |
| NYIS | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 99.5 |
| PJM | 100.0 | 99.4 | 100.0 | 99.7 | 99.7 | 99.5 | 99.7 | 99.3 |
| SOCO | 99.7 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 99.6 |
| SWPP | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 99.2 |
| TVA | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 | 99.5 |

## 3. Cleaning rules and rows affected

Rules are defined in `transform/models/intermediate/int_eia__demand_cleaned.sql` (R3/R4 band: 0.5x-1.6x the centred 7-day median).

| ba_code | n_staged | r1_duplicates_removed | n_rows | r0_missing_reported | r2_nonpositive | r3_outlier | r4_forecast_invalid | target_null | filled_null | operator_forecast_null |
|---|---|---|---|---|---|---|---|---|---|---|
| CISO | 67727 | 0 | 67727 | 172 | 0 | 7 | 1 | 179 | 55 | 121 |
| ERCO | 67727 | 0 | 67727 | 72 | 0 | 1 | 3 | 73 | 49 | 51 |
| FPL | 67727 | 0 | 67727 | 781 | 3 | 42 | 10 | 826 | 302 | 191 |
| ISNE | 67727 | 0 | 67727 | 27 | 0 | 12 | 14 | 39 | 36 | 14 |
| MISO | 67728 | 0 | 67728 | 96 | 0 | 0 | 0 | 96 | 24 | 96 |
| NYIS | 67727 | 0 | 67727 | 24 | 12 | 2 | 184 | 38 | 38 | 184 |
| PJM | 67727 | 0 | 67727 | 213 | 0 | 12 | 0 | 225 | 32 | 238 |
| SOCO | 67727 | 0 | 67727 | 49 | 1 | 8 | 0 | 58 | 28 | 31 |
| SWPP | 67727 | 0 | 67727 | 49 | 0 | 2 | 47 | 51 | 25 | 599 |
| TVA | 67727 | 0 | 67727 | 25 | 4 | 9 | 6 | 38 | 28 | 71 |

## 4. Operator day-ahead forecast accuracy (the benchmark)

MAPE (%) of the operator forecast against cleaned reported demand, by year:

| ba_code | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|---|---|
| CISO | 4.25 | 2.32 | 2.09 | 3.56 | 5.50 | 6.97 | 8.14 | 9.30 |
| ERCO | 2.35 | 2.21 | 2.88 | 2.79 | 2.60 | 2.16 | 2.46 | 1.83 |
| FPL | 4.36 | 4.19 | 4.26 | 3.51 | 3.15 | 3.33 | 3.18 | 3.13 |
| ISNE | 2.42 | 2.40 | 2.35 | 2.37 | 2.40 | 2.77 | 2.52 | 3.17 |
| MISO | 3.22 | 3.18 | 2.30 | 2.96 | 2.98 | 2.77 | 2.38 | 2.62 |
| NYIS | 2.91 | 2.51 | 2.71 | 2.59 | 2.41 | 2.78 | 2.70 | 2.67 |
| PJM | 3.64 | 3.87 | 3.62 | 3.64 | 3.45 | 3.56 | 3.44 | 3.67 |
| SOCO | 3.84 | 3.78 | 3.00 | 2.09 | 2.03 | 1.89 | 1.22 | 1.34 |
| SWPP | 3.90 | 4.11 | 4.02 | 3.72 | 2.97 | 2.32 | 7.71 | 10.49 |
| TVA | 2.28 | 2.28 | 2.05 | 2.37 | 2.39 | 2.14 | 2.31 | 2.40 |

Mean signed error (%) (positive = operator over-forecasts):

| ba_code | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|---|---|
| CISO | 3.00 | 0.40 | -0.81 | -1.71 | -2.26 | -4.51 | -6.44 | -8.79 |
| ERCO | 0.28 | 0.34 | 0.64 | 0.19 | 0.42 | 0.42 | 1.23 | 0.23 |
| FPL | -3.08 | -2.41 | -3.05 | -1.82 | -0.35 | 1.00 | 0.59 | 0.57 |
| ISNE | -1.60 | -1.49 | -1.58 | -1.22 | -1.27 | -2.02 | -1.89 | -2.64 |
| MISO | 3.12 | 2.74 | 1.74 | 2.61 | 2.84 | 2.25 | 1.99 | 2.37 |
| NYIS | -2.58 | -1.80 | -2.35 | -2.28 | -1.94 | -2.49 | -2.15 | -1.70 |
| PJM | -0.81 | -0.90 | -1.10 | -1.34 | -1.21 | -1.55 | -1.46 | -1.69 |
| SOCO | -3.03 | -3.22 | -2.48 | -1.33 | -1.38 | -1.72 | -0.95 | -1.05 |
| SWPP | 2.87 | 3.72 | 3.50 | 2.87 | 1.80 | -0.61 | 6.30 | 10.01 |
| TVA | 0.54 | 0.10 | 0.24 | 0.56 | 0.90 | 0.87 | 1.26 | 1.28 |

## 5. Findings

### 5.1 CISO: a growing midday under-forecast (open)

CISO's operator MAPE rose from 4.25 % (2019) to 9.30 % (2026), with the signed error moving from +3.00 % to -8.79 %. Since 2025 the bias is -21.1 % in hours 10-15 but -1.8 % outside hours 8-17:

| hour | bias_pct | demand_mw | operator_mw |
|---|---|---|---|
| 1 | -3.7 | 24794.4 | 23860.9 |
| 2 | -4.1 | 23795.3 | 22807.2 |
| 3 | -4.6 | 22949.7 | 21873.8 |
| 4 | -4.3 | 22378.0 | 21387.0 |
| 5 | -2.6 | 22107.3 | 21502.8 |
| 6 | 0.0 | 22332.6 | 22311.6 |
| 7 | 1.2 | 23255.3 | 23496.3 |
| 8 | -2.4 | 24794.9 | 24141.1 |
| 9 | -10.4 | 26576.2 | 23681.3 |
| 10 | -17.9 | 27693.6 | 22657.7 |
| 11 | -22.5 | 27938.3 | 21657.2 |
| 12 | -24.4 | 27766.3 | 21060.7 |
| 13 | -24.1 | 27553.1 | 21047.3 |
| 14 | -21.4 | 27301.0 | 21664.1 |
| 15 | -16.5 | 27113.5 | 22850.1 |
| 16 | -9.8 | 26996.1 | 24516.6 |
| 17 | -3.8 | 27295.4 | 26332.8 |
| 18 | 0.6 | 28203.7 | 28359.9 |
| 19 | 1.3 | 29138.6 | 29488.4 |
| 20 | 0.4 | 29498.4 | 29597.1 |
| 21 | -0.6 | 29318.2 | 29142.1 |
| 22 | -1.4 | 28750.8 | 28335.2 |
| 23 | -3.2 | 27625.9 | 26707.7 |
| 24 | -4.2 | 26061.4 | 24947.7 |

The error is concentrated in solar hours and grows year over year, which fits a definitional mismatch between CAISO's load forecast and EIA's reported demand (for example battery charging or behind-the-meter effects counted on one side only). **This is a hypothesis, not a finding**: EIA-930's battery-storage column is empty for CISO, so it cannot be tested from this data. Consequence for GridCast: raw 'skill vs operator' in CISO would flatter our models, so every results table also reports skill against a *bias-corrected operator* benchmark (trailing 28-day mean error per hour of day, using only data available at issue time).

### 5.2 SWPP: a step change in May 2025

SWPP's operator bias averaged -0.7 % from Nov 2024 to Apr 2025 and +8.9 % from May to Aug 2025 - a level shift between two consecutive months, not a gradual drift:

| month | bias_pct | mape |
|---|---|---|
| 2024-11 | -0.68 | 1.52 |
| 2024-12 | -0.71 | 1.93 |
| 2025-01 | -1.18 | 1.98 |
| 2025-02 | -1.15 | 2.75 |
| 2025-03 | 0.35 | 2.09 |
| 2025-04 | -0.78 | 1.92 |
| 2025-05 | 8.19 | 9.47 |
| 2025-06 | 9.83 | 10.55 |
| 2025-07 | 9.50 | 10.12 |
| 2025-08 | 8.03 | 8.67 |

A step of this size is characteristic of a reporting or definition change rather than a forecasting failure. The same bias-corrected benchmark applies; SWPP results after 2025-05 are flagged in every table.

### 5.3 Archived weather forecasts

The first archived day-2 temperature forecast on disk is 2021-03-25; the other variables (dew point, humidity, cloud, wind, radiation) begin 2024-01-20. Because they start later, models use forecast temperature only (ADR-0004) and the richer variables are a post-2024 ablation.

| ba_code | first_temperature | first_other_vars | last_hour | temperature_hours | all_cities_pct |
|---|---|---|---|---|---|
| CISO | 2021-03-25 | 2024-01-20 | 2026-09-24 | 47724 | 97.8 |
| ERCO | 2021-03-25 | 2024-01-20 | 2026-09-24 | 47724 | 97.8 |
| FPL | 2021-03-25 | 2024-01-20 | 2026-09-24 | 47724 | 97.8 |
| ISNE | 2021-03-25 | 2024-01-20 | 2026-09-24 | 47724 | 97.8 |
| MISO | 2021-03-25 | 2024-01-20 | 2026-09-24 | 47724 | 97.8 |
| NYIS | 2021-03-25 | 2024-01-20 | 2026-09-24 | 47724 | 97.8 |
| PJM | 2021-03-25 | 2024-01-20 | 2026-09-24 | 47724 | 97.8 |
| SOCO | 2021-03-25 | 2024-01-20 | 2026-09-24 | 47724 | 97.8 |
| SWPP | 2021-03-25 | 2024-01-20 | 2026-09-24 | 47724 | 97.8 |
| TVA | 2021-03-25 | 2024-01-20 | 2026-09-24 | 47724 | 97.8 |

Hours with a BA-level forecast temperature since 2021-03-26 (gaps are what the downloader has not fetched yet, or upstream holes):

| ba_code | expected_hours | with_temperature | pct |
|---|---|---|---|
| CISO | 48216 | 47700 | 98.9 |
| ERCO | 48216 | 47700 | 98.9 |
| FPL | 48216 | 47700 | 98.9 |
| ISNE | 48216 | 47700 | 98.9 |
| MISO | 48216 | 47700 | 98.9 |
| NYIS | 48216 | 47700 | 98.9 |
| PJM | 48216 | 47700 | 98.9 |
| SOCO | 48216 | 47700 | 98.9 |
| SWPP | 48216 | 47700 | 98.9 |
| TVA | 48216 | 47700 | 98.9 |

### 5.4 Gaps of more than 24 hours in the archived forecasts

Holes in the provider's archive (`bas` = how many BAs share the same dates). Models see missing weather as missing (LightGBM) or median-imputed (ridge); hours in a gap are still scored, so the gap costs accuracy rather than hiding it.

| gap_start | gap_end | missing_hours | bas |
|---|---|---|---|
| 2023-12-30 | 2024-01-20 | 516 | 10 |
