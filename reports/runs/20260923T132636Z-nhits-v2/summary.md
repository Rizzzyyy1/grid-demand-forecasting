> **SUPERSEDED** - Population-weighted weather, training from 2021-08-01. Superseded by ladder-v3 (unweighted weather, training from 2021-04-01, chosen from the ablation); kept as the record of that decision.

# Run 20260923T132636Z-nhits-v2 — validation split

Target days 2023-07-01 → 2024-06-30; training from 2021-08-01, expanding, refit monthly (15 refits). Protocol `realtime`: issued 10:00 local D-1 with demand to 06:00 on D-1; weather = GFS forecasts made 48 h ahead. Leakage check: 5,313,158 feature values over 10,650 forecast origins, 0 violations.

## MAPE (%) by BA

| BA | hours | operator | operator_debiased | nhits |
|---|---|---|---|---|
| CISO | 8,782 | 6.27 | 2.67 | **4.84** |
| ERCO | 8,784 | 2.42 | 2.38 | **4.90** |
| FPL | 8,578 | 3.22 | 2.19 | **6.72** |
| ISNE | 8,784 | 2.49 | 1.90 | **7.07** |
| MISO | 8,784 | 3.11 | 1.75 | **3.50** |
| NYIS | 8,760 | 2.63 | 1.74 | **5.01** |
| PJM | 8,736 | 3.59 | 2.06 | **4.31** |
| SOCO | 8,783 | 1.91 | 0.95 | **5.83** |
| SWPP | 8,784 | 2.56 | 2.58 | **4.27** |
| TVA | 8,784 | 2.38 | 2.40 | **6.18** |

Bold = best of our models. Operator columns are benchmarks, not our models.

## Skill vs `operator` (1 - MAE/MAE_ref), 95 % block-bootstrap CI, DM p-value

| BA | model | days | skill | 95 % CI | DM p | note |
|---|---|---|---|---|---|---|
| CISO | nhits | 366 | +0.200 | [+0.129, +0.278] | 5.93e-06 | operator series has a growing midday bias (data_profile 5.1) |
| ERCO | nhits | 366 | -1.066 | [-1.363, -0.811] | 2.45e-11 |  |
| FPL | nhits | 359 | -1.084 | [-1.296, -0.938] | 7.25e-35 |  |
| ISNE | nhits | 366 | -2.000 | [-2.272, -1.743] | 2.24e-45 |  |
| MISO | nhits | 366 | -0.147 | [-0.333, -0.022] | 0.055 |  |
| NYIS | nhits | 366 | -0.945 | [-1.196, -0.709] | 5.62e-14 |  |
| PJM | nhits | 364 | -0.250 | [-0.432, -0.118] | 0.00553 |  |
| SOCO | nhits | 366 | -2.341 | [-2.953, -1.835] | 1.91e-16 |  |
| SWPP | nhits | 366 | -0.667 | [-0.951, -0.451] | 1.35e-08 | operator series changes definition in 2025-05 (data_profile 5.2) |
| TVA | nhits | 366 | -1.642 | [-2.220, -1.264] | 5.23e-12 |  |

## Skill vs `operator_debiased` (1 - MAE/MAE_ref), 95 % block-bootstrap CI, DM p-value

| BA | model | days | skill | 95 % CI | DM p | note |
|---|---|---|---|---|---|---|
| CISO | nhits | 366 | -0.843 | [-0.995, -0.702] | 4.98e-28 |  |
| ERCO | nhits | 366 | -1.115 | [-1.374, -0.855] | 1.43e-12 |  |
| FPL | nhits | 359 | -1.988 | [-2.317, -1.769] | 8.85e-56 |  |
| ISNE | nhits | 366 | -2.823 | [-3.164, -2.500] | 2.04e-52 |  |
| MISO | nhits | 366 | -0.998 | [-1.228, -0.832] | 1.7e-20 |  |
| NYIS | nhits | 366 | -1.915 | [-2.302, -1.593] | 1.34e-23 |  |
| PJM | nhits | 364 | -1.170 | [-1.508, -0.931] | 1.16e-13 |  |
| SOCO | nhits | 366 | -5.559 | [-6.853, -4.426] | 1.34e-23 |  |
| SWPP | nhits | 366 | -0.682 | [-0.931, -0.459] | 3.44e-09 |  |
| TVA | nhits | 366 | -1.599 | [-2.178, -1.219] | 1.53e-11 |  |

## Prediction intervals (nominal 80 % and 95 %)

| BA | model | coverage 80 | width 80 (%) | coverage 95 | width 95 (%) |
|---|---|---|---|---|---|
| CISO | nhits | 79.5 | 16.1 | 94.6 | 29.0 |
| CISO | nhits+cqr | 79.1 | 15.9 | 95.4 | 30.0 |
| ERCO | nhits | 73.9 | 14.2 | 91.0 | 26.0 |
| ERCO | nhits+cqr | 78.4 | 15.9 | 94.6 | 30.3 |
| FPL | nhits | 76.1 | 21.2 | 94.9 | 40.5 |
| FPL | nhits+cqr | 79.4 | 22.9 | 95.6 | 41.0 |
| ISNE | nhits | 73.2 | 20.0 | 91.1 | 35.9 |
| ISNE | nhits+cqr | 78.3 | 22.2 | 94.3 | 40.7 |
| MISO | nhits | 82.2 | 12.6 | 95.5 | 23.2 |
| MISO | nhits+cqr | 78.3 | 12.1 | 94.3 | 22.6 |
| NYIS | nhits | 76.3 | 15.1 | 93.4 | 28.0 |
| NYIS | nhits+cqr | 77.8 | 15.9 | 93.9 | 28.5 |
| PJM | nhits | 76.7 | 13.5 | 92.8 | 24.6 |
| PJM | nhits+cqr | 78.3 | 14.4 | 93.9 | 26.7 |
| SOCO | nhits | 76.0 | 18.2 | 92.9 | 33.6 |
| SOCO | nhits+cqr | 79.1 | 20.2 | 94.8 | 36.9 |
| SWPP | nhits | 76.4 | 12.9 | 91.9 | 23.5 |
| SWPP | nhits+cqr | 78.6 | 14.0 | 95.5 | 27.5 |
| TVA | nhits | 75.4 | 18.7 | 92.1 | 34.4 |
| TVA | nhits+cqr | 78.1 | 21.7 | 93.9 | 39.1 |

## Daily peak

| BA | model | days | peak APE (%) | peak hour off by >1 h (%) |
|---|---|---|---|---|
| CISO | nhits | 366 | 4.94 | 8.2 |
| CISO | operator | 366 | 1.78 | 7.4 |
| CISO | operator_debiased | 366 | 1.87 | 4.6 |
| ERCO | nhits | 366 | 5.25 | 29.2 |
| ERCO | operator | 366 | 2.52 | 15.3 |
| ERCO | operator_debiased | 366 | 2.43 | 14.8 |
| FPL | nhits | 357 | 7.23 | 29.1 |
| FPL | operator | 357 | 2.76 | 20.4 |
| FPL | operator_debiased | 357 | 2.70 | 17.1 |
| ISNE | nhits | 366 | 5.93 | 24.3 |
| ISNE | operator | 366 | 1.48 | 2.5 |
| ISNE | operator_debiased | 366 | 1.46 | 3.6 |
| MISO | nhits | 366 | 3.74 | 26.0 |
| MISO | operator | 366 | 2.96 | 9.3 |
| MISO | operator_debiased | 366 | 1.82 | 9.8 |
| NYIS | nhits | 365 | 4.93 | 22.5 |
| NYIS | operator | 365 | 2.69 | 5.8 |
| NYIS | operator_debiased | 365 | 1.75 | 5.5 |
| PJM | nhits | 364 | 4.65 | 23.4 |
| PJM | operator | 364 | 1.72 | 17.6 |
| PJM | operator_debiased | 364 | 1.89 | 11.3 |
| SOCO | nhits | 366 | 6.49 | 30.3 |
| SOCO | operator | 366 | 0.77 | 3.8 |
| SOCO | operator_debiased | 366 | 0.65 | 4.4 |
| SWPP | nhits | 366 | 4.79 | 32.0 |
| SWPP | operator | 366 | 3.03 | 15.8 |
| SWPP | operator_debiased | 366 | 3.01 | 17.5 |
| TVA | nhits | 366 | 6.68 | 35.5 |
| TVA | operator | 366 | 2.53 | 12.8 |
| TVA | operator_debiased | 366 | 2.67 | 13.7 |

## Slices (MAPE %, pooled over BAs)

| slice | value | operator_debiased | nhits |
|---|---|---|---|
| day_type | holiday | 2.23 | 7.10 |
| day_type | weekday | 1.97 | 5.07 |
| day_type | weekend | 2.25 | 5.50 |
| hour_block | 00 | 1.80 | 4.17 |
| hour_block | 06 | 1.98 | 5.24 |
| hour_block | 12 | 2.49 | 6.30 |
| hour_block | 18 | 1.97 | 5.33 |
| season | autumn | 1.87 | 4.76 |
| season | spring | 2.07 | 4.87 |
| season | summer | 2.14 | 5.20 |
| season | winter | 2.16 | 6.22 |
| temperature | cold 5% | 2.32 | 8.56 |
| temperature | hot 5% | 2.00 | 4.81 |
| temperature | no weather | 2.48 | 7.07 |
| temperature | normal | 2.02 | 4.97 |

## Compute

* `operator`: 0 s fit+predict over 15 refits
* `operator_debiased`: 0 s fit+predict over 15 refits
* `nhits`: 5951 s fit+predict over 15 refits
