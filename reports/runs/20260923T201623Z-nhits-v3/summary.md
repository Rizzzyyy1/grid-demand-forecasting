# Run 20260923T201623Z-nhits-v3 — validation split

Target days 2023-07-01 → 2024-06-30; training from 2021-04-01, expanding, refit monthly (15 refits). Protocol `realtime`: issued 10:00 local D-1 with demand to 06:00 on D-1; weather = GFS forecasts made 48 h ahead. Leakage check: 5,928,038 feature values over 11,870 forecast origins, 0 violations.

## MAPE (%) by BA

| BA | hours | operator | operator_debiased | nhits |
|---|---|---|---|---|
| CISO | 8,782 | 6.27 | 2.67 | **4.48** |
| ERCO | 8,784 | 2.42 | 2.38 | **4.69** |
| FPL | 8,578 | 3.22 | 2.19 | **5.99** |
| ISNE | 8,784 | 2.49 | 1.90 | **6.49** |
| MISO | 8,784 | 3.11 | 1.75 | **3.13** |
| NYIS | 8,760 | 2.63 | 1.74 | **4.62** |
| PJM | 8,736 | 3.59 | 2.06 | **3.74** |
| SOCO | 8,783 | 1.91 | 0.95 | **5.11** |
| SWPP | 8,784 | 2.56 | 2.58 | **3.81** |
| TVA | 8,784 | 2.38 | 2.40 | **5.49** |

Bold = best of our models. Operator columns are benchmarks, not our models.

## Skill vs `operator` (1 - MAE/MAE_ref), 95 % block-bootstrap CI, DM p-value

| BA | model | days | skill | 95 % CI | DM p | note |
|---|---|---|---|---|---|---|
| CISO | nhits | 366 | +0.269 | [+0.212, +0.333] | 1.12e-14 | operator series has a growing midday bias (data_profile 5.1) |
| ERCO | nhits | 366 | -0.967 | [-1.339, -0.693] | 6.66e-08 |  |
| FPL | nhits | 359 | -0.831 | [-1.004, -0.697] | 9.55e-30 |  |
| ISNE | nhits | 366 | -1.746 | [-1.980, -1.537] | 9.28e-62 |  |
| MISO | nhits | 366 | -0.024 | [-0.246, +0.102] | 0.792 |  |
| NYIS | nhits | 366 | -0.775 | [-0.977, -0.583] | 3.76e-13 |  |
| PJM | nhits | 364 | -0.071 | [-0.238, +0.052] | 0.382 |  |
| SOCO | nhits | 366 | -1.921 | [-2.377, -1.544] | 1.02e-18 |  |
| SWPP | nhits | 366 | -0.488 | [-0.776, -0.283] | 7.98e-05 | operator series changes definition in 2025-05 (data_profile 5.2) |
| TVA | nhits | 366 | -1.338 | [-1.858, -1.018] | 3.06e-10 |  |

## Skill vs `operator_debiased` (1 - MAE/MAE_ref), 95 % block-bootstrap CI, DM p-value

| BA | model | days | skill | 95 % CI | DM p | note |
|---|---|---|---|---|---|---|
| CISO | nhits | 366 | -0.683 | [-0.831, -0.551] | 4.7e-28 |  |
| ERCO | nhits | 366 | -1.013 | [-1.312, -0.751] | 7.47e-09 |  |
| FPL | nhits | 359 | -1.625 | [-1.908, -1.435] | 1.09e-56 |  |
| ISNE | nhits | 366 | -2.500 | [-2.799, -2.243] | 3.88e-75 |  |
| MISO | nhits | 366 | -0.783 | [-1.055, -0.589] | 5.97e-10 |  |
| NYIS | nhits | 366 | -1.661 | [-2.011, -1.380] | 6.1e-23 |  |
| PJM | nhits | 364 | -0.860 | [-1.148, -0.654] | 1.36e-10 |  |
| SOCO | nhits | 366 | -4.733 | [-5.752, -3.886] | 4.62e-29 |  |
| SWPP | nhits | 366 | -0.502 | [-0.751, -0.296] | 1.67e-05 |  |
| TVA | nhits | 366 | -1.300 | [-1.809, -0.968] | 9.27e-10 |  |

## Prediction intervals (nominal 80 % and 95 %)

| BA | model | coverage 80 | width 80 (%) | coverage 95 | width 95 (%) |
|---|---|---|---|---|---|
| CISO | nhits | 81.8 | 16.2 | 95.5 | 28.1 |
| CISO | nhits+cqr | 79.7 | 15.3 | 94.9 | 27.2 |
| ERCO | nhits | 72.7 | 12.7 | 90.8 | 23.4 |
| ERCO | nhits+cqr | 79.2 | 15.0 | 94.4 | 29.4 |
| FPL | nhits | 75.7 | 18.5 | 94.1 | 36.1 |
| FPL | nhits+cqr | 78.6 | 20.1 | 95.2 | 37.2 |
| ISNE | nhits | 73.0 | 19.7 | 90.4 | 34.9 |
| ISNE | nhits+cqr | 78.1 | 21.9 | 94.7 | 39.3 |
| MISO | nhits | 84.4 | 11.9 | 96.4 | 21.3 |
| MISO | nhits+cqr | 79.4 | 10.9 | 94.6 | 21.2 |
| NYIS | nhits | 79.7 | 15.7 | 94.7 | 27.6 |
| NYIS | nhits+cqr | 79.5 | 15.5 | 95.0 | 26.6 |
| PJM | nhits | 80.3 | 12.9 | 94.3 | 22.8 |
| PJM | nhits+cqr | 78.9 | 12.9 | 94.7 | 23.5 |
| SOCO | nhits | 75.8 | 16.0 | 92.4 | 29.0 |
| SOCO | nhits+cqr | 79.7 | 17.9 | 94.5 | 33.1 |
| SWPP | nhits | 78.9 | 12.0 | 93.0 | 21.3 |
| SWPP | nhits+cqr | 79.6 | 12.6 | 95.0 | 26.0 |
| TVA | nhits | 76.2 | 16.9 | 92.0 | 30.5 |
| TVA | nhits+cqr | 79.1 | 19.3 | 94.0 | 35.2 |

## Daily peak

| BA | model | days | peak APE (%) | peak hour off by >1 h (%) |
|---|---|---|---|---|
| CISO | nhits | 366 | 4.41 | 8.5 |
| CISO | operator | 366 | 1.78 | 7.4 |
| CISO | operator_debiased | 366 | 1.87 | 4.6 |
| ERCO | nhits | 366 | 5.01 | 29.0 |
| ERCO | operator | 366 | 2.52 | 15.3 |
| ERCO | operator_debiased | 366 | 2.43 | 14.8 |
| FPL | nhits | 357 | 6.20 | 28.9 |
| FPL | operator | 357 | 2.76 | 20.4 |
| FPL | operator_debiased | 357 | 2.70 | 17.1 |
| ISNE | nhits | 366 | 5.03 | 25.4 |
| ISNE | operator | 366 | 1.48 | 2.5 |
| ISNE | operator_debiased | 366 | 1.46 | 3.6 |
| MISO | nhits | 366 | 3.37 | 25.4 |
| MISO | operator | 366 | 2.96 | 9.3 |
| MISO | operator_debiased | 366 | 1.82 | 9.8 |
| NYIS | nhits | 365 | 4.28 | 27.7 |
| NYIS | operator | 365 | 2.69 | 5.8 |
| NYIS | operator_debiased | 365 | 1.75 | 5.5 |
| PJM | nhits | 364 | 3.88 | 23.6 |
| PJM | operator | 364 | 1.72 | 17.6 |
| PJM | operator_debiased | 364 | 1.89 | 11.3 |
| SOCO | nhits | 366 | 5.73 | 30.6 |
| SOCO | operator | 366 | 0.77 | 3.8 |
| SOCO | operator_debiased | 366 | 0.65 | 4.4 |
| SWPP | nhits | 366 | 4.52 | 31.7 |
| SWPP | operator | 366 | 3.03 | 15.8 |
| SWPP | operator_debiased | 366 | 3.01 | 17.5 |
| TVA | nhits | 366 | 6.08 | 34.2 |
| TVA | operator | 366 | 2.53 | 12.8 |
| TVA | operator_debiased | 366 | 2.67 | 13.7 |

## Slices (MAPE %, pooled over BAs)

| slice | value | operator_debiased | nhits |
|---|---|---|---|
| day_type | holiday | 2.23 | 6.49 |
| day_type | weekday | 1.97 | 4.55 |
| day_type | weekend | 2.25 | 5.03 |
| hour_block | 00 | 1.80 | 3.90 |
| hour_block | 06 | 1.98 | 4.79 |
| hour_block | 12 | 2.49 | 5.63 |
| hour_block | 18 | 1.97 | 4.69 |
| season | autumn | 1.87 | 4.27 |
| season | spring | 2.07 | 4.62 |
| season | summer | 2.14 | 4.40 |
| season | winter | 2.16 | 5.71 |
| temperature | cold 5% | 2.37 | 7.70 |
| temperature | hot 5% | 2.16 | 4.35 |
| temperature | no weather | 2.48 | 6.89 |
| temperature | normal | 2.01 | 4.46 |

## Compute

* `operator`: 0 s fit+predict over 15 refits
* `operator_debiased`: 0 s fit+predict over 15 refits
* `nhits`: 4301 s fit+predict over 15 refits
