> **SUPERSEDED** - Population-weighted weather, training from 2021-08-01. Superseded by ladder-v3 (unweighted weather, training from 2021-04-01, chosen from the ablation); kept as the record of that decision.

# Run 20260923T152134Z-final — validation split

Target days 2023-07-01 → 2024-06-30; training from 2021-08-01, expanding, refit monthly (15 refits). Protocol `realtime`: issued 10:00 local D-1 with demand to 06:00 on D-1; weather = GFS forecasts made 48 h ahead. Leakage check: 5,313,115 feature values over 10,650 forecast origins, 0 violations.

## MAPE (%) by BA

| BA | hours | operator | operator_debiased | seasonal_naive | ridge | lgbm_global | nhits |
|---|---|---|---|---|---|---|---|
| CISO | 8,781 | 6.27 | 2.67 | 6.60 | 4.40 | **3.39** | 4.84 |
| ERCO | 8,783 | 2.42 | 2.38 | 8.10 | 5.40 | **3.98** | 4.91 |
| FPL | 8,547 | 3.22 | 2.18 | 8.75 | 5.95 | **4.44** | 6.72 |
| ISNE | 8,783 | 2.49 | 1.90 | 10.35 | 6.78 | **5.35** | 7.07 |
| MISO | 8,784 | 3.11 | 1.75 | 6.80 | 4.11 | **2.67** | 3.50 |
| NYIS | 8,758 | 2.63 | 1.74 | 8.33 | 5.28 | **3.68** | 5.01 |
| PJM | 8,734 | 3.59 | 2.06 | 8.56 | 5.12 | **3.15** | 4.31 |
| SOCO | 8,782 | 1.91 | 0.95 | 9.76 | 6.47 | **4.48** | 5.83 |
| SWPP | 8,783 | 2.56 | 2.58 | 8.10 | 5.08 | **3.50** | 4.27 |
| TVA | 8,783 | 2.38 | 2.40 | 11.00 | 7.03 | **4.38** | 6.18 |

Bold = best of our models. Operator columns are benchmarks, not our models.

## Skill vs `operator` (1 - MAE/MAE_ref), 95 % block-bootstrap CI, DM p-value

| BA | model | days | skill | 95 % CI | DM p | note |
|---|---|---|---|---|---|---|
| CISO | lgbm_global | 366 | +0.447 | [+0.393, +0.501] | 3.93e-36 | operator series has a growing midday bias (data_profile 5.1) |
| CISO | nhits | 366 | +0.200 | [+0.129, +0.278] | 5.92e-06 | operator series has a growing midday bias (data_profile 5.1) |
| CISO | ridge | 366 | +0.275 | [+0.199, +0.358] | 3.37e-09 | operator series has a growing midday bias (data_profile 5.1) |
| CISO | seasonal_naive | 366 | -0.128 | [-0.300, +0.083] | 0.221 | operator series has a growing midday bias (data_profile 5.1) |
| ERCO | lgbm_global | 366 | -0.666 | [-0.951, -0.425] | 2.03e-05 |  |
| ERCO | nhits | 366 | -1.066 | [-1.363, -0.811] | 2.45e-11 |  |
| ERCO | ridge | 366 | -1.253 | [-1.562, -0.962] | 7.54e-13 |  |
| ERCO | seasonal_naive | 366 | -2.380 | [-2.891, -1.893] | 2.18e-17 |  |
| FPL | lgbm_global | 358 | -0.349 | [-0.472, -0.250] | 1.12e-09 |  |
| FPL | nhits | 358 | -1.084 | [-1.303, -0.939] | 1.74e-34 |  |
| FPL | ridge | 358 | -0.767 | [-0.992, -0.603] | 9.61e-18 |  |
| FPL | seasonal_naive | 358 | -1.645 | [-1.988, -1.387] | 1.05e-32 |  |
| ISNE | lgbm_global | 366 | -1.241 | [-1.413, -1.080] | 3.95e-44 |  |
| ISNE | nhits | 366 | -2.000 | [-2.272, -1.744] | 2.21e-45 |  |
| ISNE | ridge | 366 | -1.847 | [-2.070, -1.629] | 6.08e-51 |  |
| ISNE | seasonal_naive | 366 | -3.442 | [-4.092, -2.869] | 5.23e-22 |  |
| MISO | lgbm_global | 366 | +0.124 | [-0.053, +0.262] | 0.16 |  |
| MISO | nhits | 366 | -0.147 | [-0.333, -0.022] | 0.055 |  |
| MISO | ridge | 366 | -0.342 | [-0.549, -0.190] | 7.73e-05 |  |
| MISO | seasonal_naive | 366 | -1.251 | [-1.663, -0.932] | 3.13e-10 |  |
| NYIS | lgbm_global | 366 | -0.428 | [-0.578, -0.270] | 2.56e-07 |  |
| NYIS | nhits | 366 | -0.944 | [-1.195, -0.709] | 5.56e-14 |  |
| NYIS | ridge | 366 | -1.027 | [-1.287, -0.797] | 1.76e-16 |  |
| NYIS | seasonal_naive | 366 | -2.252 | [-2.801, -1.710] | 1.01e-12 |  |
| PJM | lgbm_global | 364 | +0.096 | [-0.053, +0.220] | 0.192 |  |
| PJM | nhits | 364 | -0.250 | [-0.432, -0.118] | 0.00551 |  |
| PJM | ridge | 364 | -0.469 | [-0.635, -0.340] | 3.63e-09 |  |
| PJM | seasonal_naive | 364 | -1.461 | [-1.820, -1.140] | 4.5e-14 |  |
| SOCO | lgbm_global | 366 | -1.553 | [-2.166, -1.035] | 2.65e-07 |  |
| SOCO | nhits | 366 | -2.342 | [-2.954, -1.835] | 1.91e-16 |  |
| SOCO | ridge | 366 | -2.668 | [-3.432, -2.111] | 5.15e-17 |  |
| SOCO | seasonal_naive | 366 | -4.481 | [-5.672, -3.560] | 1.15e-17 |  |
| SWPP | lgbm_global | 366 | -0.373 | [-0.623, -0.183] | 0.00139 | operator series changes definition in 2025-05 (data_profile 5.2) |
| SWPP | nhits | 366 | -0.667 | [-0.951, -0.452] | 1.36e-08 | operator series changes definition in 2025-05 (data_profile 5.2) |
| SWPP | ridge | 366 | -0.991 | [-1.279, -0.756] | 1.12e-14 | operator series changes definition in 2025-05 (data_profile 5.2) |
| SWPP | seasonal_naive | 366 | -2.168 | [-2.765, -1.688] | 4.5e-17 | operator series changes definition in 2025-05 (data_profile 5.2) |
| TVA | lgbm_global | 366 | -0.873 | [-1.400, -0.567] | 4.11e-05 |  |
| TVA | nhits | 366 | -1.642 | [-2.220, -1.264] | 5.25e-12 |  |
| TVA | ridge | 366 | -1.977 | [-2.650, -1.567] | 2.38e-12 |  |
| TVA | seasonal_naive | 366 | -3.613 | [-4.762, -2.915] | 2.4e-15 |  |

## Skill vs `operator_debiased` (1 - MAE/MAE_ref), 95 % block-bootstrap CI, DM p-value

| BA | model | days | skill | 95 % CI | DM p | note |
|---|---|---|---|---|---|---|
| CISO | lgbm_global | 366 | -0.273 | [-0.370, -0.187] | 1.7e-08 |  |
| CISO | nhits | 366 | -0.843 | [-0.995, -0.702] | 4.99e-28 |  |
| CISO | ridge | 366 | -0.670 | [-0.801, -0.553] | 3.82e-21 |  |
| CISO | seasonal_naive | 366 | -1.597 | [-1.933, -1.258] | 8.58e-15 |  |
| ERCO | lgbm_global | 366 | -0.705 | [-0.959, -0.474] | 4.32e-06 |  |
| ERCO | nhits | 366 | -1.115 | [-1.375, -0.855] | 1.44e-12 |  |
| ERCO | ridge | 366 | -1.306 | [-1.598, -1.004] | 6.19e-14 |  |
| ERCO | seasonal_naive | 366 | -2.459 | [-3.004, -1.953] | 4.09e-18 |  |
| FPL | lgbm_global | 358 | -0.936 | [-1.109, -0.806] | 1.05e-39 |  |
| FPL | nhits | 358 | -1.992 | [-2.308, -1.775] | 1.94e-55 |  |
| FPL | ridge | 358 | -1.537 | [-1.840, -1.328] | 1.03e-39 |  |
| FPL | seasonal_naive | 358 | -2.797 | [-3.312, -2.415] | 1.06e-45 |  |
| ISNE | lgbm_global | 366 | -1.857 | [-2.059, -1.638] | 2.99e-56 |  |
| ISNE | nhits | 366 | -2.824 | [-3.164, -2.500] | 1.97e-52 |  |
| ISNE | ridge | 366 | -2.629 | [-2.934, -2.358] | 1.31e-58 |  |
| ISNE | seasonal_naive | 366 | -4.662 | [-5.418, -3.930] | 3.54e-24 |  |
| MISO | lgbm_global | 366 | -0.526 | [-0.745, -0.346] | 9.38e-06 |  |
| MISO | nhits | 366 | -0.998 | [-1.228, -0.832] | 1.7e-20 |  |
| MISO | ridge | 366 | -1.338 | [-1.618, -1.134] | 2.78e-24 |  |
| MISO | seasonal_naive | 366 | -2.921 | [-3.571, -2.417] | 6.37e-18 |  |
| NYIS | lgbm_global | 366 | -1.141 | [-1.309, -0.979] | 3.43e-28 |  |
| NYIS | nhits | 366 | -1.915 | [-2.301, -1.593] | 1.32e-23 |  |
| NYIS | ridge | 366 | -2.038 | [-2.352, -1.741] | 3.33e-33 |  |
| NYIS | seasonal_naive | 366 | -3.875 | [-4.655, -3.112] | 1.04e-16 |  |
| PJM | lgbm_global | 364 | -0.570 | [-0.825, -0.371] | 3.86e-06 |  |
| PJM | nhits | 364 | -1.170 | [-1.508, -0.931] | 1.16e-13 |  |
| PJM | ridge | 364 | -1.551 | [-1.843, -1.318] | 1.9e-25 |  |
| PJM | seasonal_naive | 364 | -3.273 | [-3.837, -2.764] | 5.81e-22 |  |
| SOCO | lgbm_global | 366 | -4.011 | [-5.313, -2.891] | 1.16e-11 |  |
| SOCO | nhits | 366 | -5.559 | [-6.853, -4.426] | 1.34e-23 |  |
| SOCO | ridge | 366 | -6.199 | [-7.629, -4.985] | 1.17e-23 |  |
| SOCO | seasonal_naive | 366 | -9.758 | [-12.137, -7.744] | 1.07e-21 |  |
| SWPP | lgbm_global | 366 | -0.385 | [-0.581, -0.205] | 0.000388 |  |
| SWPP | nhits | 366 | -0.682 | [-0.931, -0.459] | 3.5e-09 |  |
| SWPP | ridge | 366 | -1.009 | [-1.305, -0.714] | 8.46e-14 |  |
| SWPP | seasonal_naive | 366 | -2.196 | [-2.791, -1.706] | 1.12e-17 |  |
| TVA | lgbm_global | 366 | -0.842 | [-1.350, -0.526] | 5.89e-05 |  |
| TVA | nhits | 366 | -1.599 | [-2.178, -1.219] | 1.54e-11 |  |
| TVA | ridge | 366 | -1.928 | [-2.614, -1.497] | 4.76e-12 |  |
| TVA | seasonal_naive | 366 | -3.537 | [-4.618, -2.829] | 4.21e-15 |  |

## Prediction intervals (nominal 80 % and 95 %)

| BA | model | coverage 80 | width 80 (%) | coverage 95 | width 95 (%) |
|---|---|---|---|---|---|
| CISO | lgbm_global | 68.1 | 8.8 | 87.3 | 14.4 |
| CISO | lgbm_global+cqr | 79.7 | 10.9 | 94.4 | 18.2 |
| CISO | nhits | 79.5 | 16.1 | 94.6 | 29.0 |
| CISO | nhits+cqr | 79.1 | 15.9 | 95.4 | 30.0 |
| CISO | ridge | 76.8 | 13.0 | 92.8 | 19.7 |
| CISO | ridge+cqr | 78.5 | 13.6 | 94.2 | 20.9 |
| CISO | seasonal_naive | 78.7 | 21.5 | 94.8 | 37.8 |
| CISO | seasonal_naive+cqr | 78.1 | 21.8 | 93.8 | 36.7 |
| ERCO | lgbm_global | 69.2 | 9.2 | 86.9 | 15.6 |
| ERCO | lgbm_global+cqr | 79.4 | 12.6 | 93.1 | 24.1 |
| ERCO | nhits | 73.9 | 14.2 | 91.0 | 26.0 |
| ERCO | nhits+cqr | 78.4 | 15.9 | 94.6 | 30.3 |
| ERCO | ridge | 77.9 | 15.7 | 93.6 | 26.2 |
| ERCO | ridge+cqr | 78.6 | 17.4 | 93.1 | 29.5 |
| ERCO | seasonal_naive | 81.4 | 27.0 | 95.3 | 47.7 |
| ERCO | seasonal_naive+cqr | 78.0 | 27.0 | 92.0 | 46.2 |
| FPL | lgbm_global | 72.7 | 12.2 | 89.3 | 19.7 |
| FPL | lgbm_global+cqr | 80.6 | 14.6 | 95.3 | 24.3 |
| FPL | nhits | 76.2 | 21.3 | 94.9 | 40.5 |
| FPL | nhits+cqr | 79.5 | 22.9 | 95.6 | 41.1 |
| FPL | ridge | 75.6 | 16.9 | 92.4 | 26.5 |
| FPL | ridge+cqr | 79.9 | 19.2 | 94.5 | 29.0 |
| FPL | seasonal_naive | 78.8 | 27.3 | 96.3 | 46.3 |
| FPL | seasonal_naive+cqr | 79.7 | 28.2 | 94.1 | 41.0 |
| ISNE | lgbm_global | 68.1 | 13.9 | 83.8 | 21.0 |
| ISNE | lgbm_global+cqr | 78.6 | 17.4 | 94.2 | 30.3 |
| ISNE | nhits | 73.2 | 20.0 | 91.1 | 35.9 |
| ISNE | nhits+cqr | 78.3 | 22.2 | 94.3 | 40.7 |
| ISNE | ridge | 77.3 | 20.0 | 93.1 | 31.5 |
| ISNE | ridge+cqr | 78.8 | 21.1 | 94.1 | 33.7 |
| ISNE | seasonal_naive | 78.3 | 32.4 | 93.9 | 52.7 |
| ISNE | seasonal_naive+cqr | 77.9 | 34.1 | 92.8 | 53.7 |
| MISO | lgbm_global | 70.3 | 6.6 | 89.1 | 11.7 |
| MISO | lgbm_global+cqr | 79.7 | 8.6 | 93.5 | 15.9 |
| MISO | nhits | 82.2 | 12.6 | 95.5 | 23.2 |
| MISO | nhits+cqr | 78.3 | 12.1 | 94.3 | 22.6 |
| MISO | ridge | 77.9 | 12.3 | 93.9 | 20.2 |
| MISO | ridge+cqr | 79.9 | 13.1 | 94.4 | 22.0 |
| MISO | seasonal_naive | 79.4 | 21.2 | 94.5 | 38.5 |
| MISO | seasonal_naive+cqr | 78.6 | 22.7 | 93.0 | 38.5 |
| NYIS | lgbm_global | 66.6 | 9.2 | 84.8 | 14.7 |
| NYIS | lgbm_global+cqr | 79.0 | 11.9 | 94.3 | 21.1 |
| NYIS | nhits | 76.3 | 15.1 | 93.4 | 28.0 |
| NYIS | nhits+cqr | 77.8 | 15.9 | 93.9 | 28.5 |
| NYIS | ridge | 76.2 | 15.0 | 92.9 | 24.3 |
| NYIS | ridge+cqr | 79.3 | 16.4 | 93.9 | 27.1 |
| NYIS | seasonal_naive | 75.5 | 24.4 | 92.3 | 41.6 |
| NYIS | seasonal_naive+cqr | 76.7 | 26.8 | 91.7 | 43.5 |
| PJM | lgbm_global | 68.4 | 7.8 | 87.7 | 13.5 |
| PJM | lgbm_global+cqr | 78.0 | 10.0 | 92.8 | 18.0 |
| PJM | nhits | 76.7 | 13.5 | 92.8 | 24.6 |
| PJM | nhits+cqr | 78.3 | 14.4 | 93.9 | 26.7 |
| PJM | ridge | 75.3 | 14.2 | 92.2 | 23.3 |
| PJM | ridge+cqr | 78.5 | 15.7 | 93.6 | 26.7 |
| PJM | seasonal_naive | 74.5 | 25.1 | 93.4 | 43.3 |
| PJM | seasonal_naive+cqr | 76.4 | 28.0 | 92.4 | 43.1 |
| SOCO | lgbm_global | 66.8 | 10.5 | 85.9 | 17.6 |
| SOCO | lgbm_global+cqr | 78.9 | 15.1 | 93.0 | 25.9 |
| SOCO | nhits | 76.0 | 18.2 | 92.9 | 33.6 |
| SOCO | nhits+cqr | 79.1 | 20.2 | 94.8 | 36.9 |
| SOCO | ridge | 75.8 | 18.2 | 93.1 | 31.1 |
| SOCO | ridge+cqr | 79.6 | 21.1 | 93.9 | 35.4 |
| SOCO | seasonal_naive | 80.3 | 31.2 | 94.7 | 59.5 |
| SOCO | seasonal_naive+cqr | 79.0 | 33.2 | 93.4 | 56.5 |
| SWPP | lgbm_global | 65.1 | 7.2 | 85.8 | 13.2 |
| SWPP | lgbm_global+cqr | 81.3 | 11.1 | 94.9 | 20.6 |
| SWPP | nhits | 76.4 | 12.9 | 91.9 | 23.5 |
| SWPP | nhits+cqr | 78.6 | 14.0 | 95.5 | 27.5 |
| SWPP | ridge | 75.7 | 14.4 | 92.1 | 23.1 |
| SWPP | ridge+cqr | 80.8 | 16.5 | 94.1 | 27.9 |
| SWPP | seasonal_naive | 78.1 | 25.5 | 94.4 | 43.3 |
| SWPP | seasonal_naive+cqr | 79.6 | 27.5 | 94.1 | 45.2 |
| TVA | lgbm_global | 68.5 | 10.5 | 86.5 | 17.8 |
| TVA | lgbm_global+cqr | 79.2 | 14.8 | 93.1 | 27.2 |
| TVA | nhits | 75.4 | 18.8 | 92.1 | 34.4 |
| TVA | nhits+cqr | 78.1 | 21.7 | 93.9 | 39.1 |
| TVA | ridge | 78.6 | 20.4 | 92.6 | 33.9 |
| TVA | ridge+cqr | 79.3 | 23.0 | 92.8 | 39.7 |
| TVA | seasonal_naive | 79.8 | 36.0 | 94.8 | 65.8 |
| TVA | seasonal_naive+cqr | 78.9 | 38.4 | 93.4 | 62.3 |

## Daily peak

| BA | model | days | peak APE (%) | peak hour off by >1 h (%) |
|---|---|---|---|---|
| CISO | lgbm_global | 366 | 2.78 | 3.6 |
| CISO | nhits | 366 | 4.94 | 8.2 |
| CISO | operator | 366 | 1.78 | 7.4 |
| CISO | operator_debiased | 366 | 1.87 | 4.6 |
| CISO | ridge | 366 | 3.72 | 2.5 |
| CISO | seasonal_naive | 366 | 6.85 | 10.4 |
| ERCO | lgbm_global | 366 | 3.94 | 26.2 |
| ERCO | nhits | 366 | 5.25 | 29.2 |
| ERCO | operator | 366 | 2.52 | 15.3 |
| ERCO | operator_debiased | 366 | 2.43 | 14.8 |
| ERCO | ridge | 366 | 5.05 | 26.5 |
| ERCO | seasonal_naive | 366 | 8.58 | 34.7 |
| FPL | lgbm_global | 356 | 4.59 | 25.8 |
| FPL | nhits | 356 | 7.22 | 28.9 |
| FPL | operator | 356 | 2.76 | 20.5 |
| FPL | operator_debiased | 356 | 2.71 | 16.9 |
| FPL | ridge | 356 | 5.93 | 20.8 |
| FPL | seasonal_naive | 356 | 9.18 | 35.4 |
| ISNE | lgbm_global | 366 | 3.96 | 7.4 |
| ISNE | nhits | 366 | 5.93 | 24.6 |
| ISNE | operator | 366 | 1.48 | 2.5 |
| ISNE | operator_debiased | 366 | 1.46 | 3.6 |
| ISNE | ridge | 366 | 5.55 | 4.4 |
| ISNE | seasonal_naive | 366 | 8.27 | 7.9 |
| MISO | lgbm_global | 366 | 2.80 | 24.0 |
| MISO | nhits | 366 | 3.74 | 25.7 |
| MISO | operator | 366 | 2.96 | 9.6 |
| MISO | operator_debiased | 366 | 1.82 | 10.1 |
| MISO | ridge | 366 | 4.05 | 31.4 |
| MISO | seasonal_naive | 366 | 7.64 | 32.0 |
| NYIS | lgbm_global | 365 | 3.52 | 11.8 |
| NYIS | nhits | 365 | 4.93 | 22.5 |
| NYIS | operator | 365 | 2.69 | 5.8 |
| NYIS | operator_debiased | 365 | 1.75 | 5.5 |
| NYIS | ridge | 365 | 5.17 | 7.9 |
| NYIS | seasonal_naive | 365 | 8.08 | 11.8 |
| PJM | lgbm_global | 364 | 3.27 | 22.3 |
| PJM | nhits | 364 | 4.65 | 23.4 |
| PJM | operator | 364 | 1.72 | 17.6 |
| PJM | operator_debiased | 364 | 1.89 | 11.3 |
| PJM | ridge | 364 | 5.23 | 28.6 |
| PJM | seasonal_naive | 364 | 9.73 | 37.6 |
| SOCO | lgbm_global | 366 | 4.66 | 23.8 |
| SOCO | nhits | 366 | 6.49 | 30.3 |
| SOCO | operator | 366 | 0.77 | 3.8 |
| SOCO | operator_debiased | 366 | 0.65 | 4.4 |
| SOCO | ridge | 366 | 6.68 | 27.6 |
| SOCO | seasonal_naive | 366 | 11.83 | 37.7 |
| SWPP | lgbm_global | 366 | 3.98 | 27.9 |
| SWPP | nhits | 366 | 4.79 | 31.1 |
| SWPP | operator | 366 | 3.03 | 15.0 |
| SWPP | operator_debiased | 366 | 3.01 | 16.7 |
| SWPP | ridge | 366 | 5.40 | 32.0 |
| SWPP | seasonal_naive | 366 | 9.54 | 36.3 |
| TVA | lgbm_global | 366 | 4.70 | 28.4 |
| TVA | nhits | 366 | 6.68 | 35.2 |
| TVA | operator | 366 | 2.53 | 12.8 |
| TVA | operator_debiased | 366 | 2.67 | 13.9 |
| TVA | ridge | 366 | 7.03 | 30.1 |
| TVA | seasonal_naive | 366 | 12.52 | 45.6 |

## Slices (MAPE %, pooled over BAs)

| slice | value | operator_debiased | lgbm_global | nhits |
|---|---|---|---|---|
| day_type | holiday | 2.22 | 5.60 | 7.10 |
| day_type | weekday | 1.97 | 3.83 | 5.07 |
| day_type | weekend | 2.25 | 3.88 | 5.50 |
| hour_block | 00 | 1.80 | 3.24 | 4.17 |
| hour_block | 06 | 1.98 | 3.90 | 5.24 |
| hour_block | 12 | 2.49 | 4.75 | 6.30 |
| hour_block | 18 | 1.96 | 3.72 | 5.32 |
| season | autumn | 1.87 | 3.34 | 4.75 |
| season | spring | 2.07 | 3.41 | 4.87 |
| season | summer | 2.14 | 3.89 | 5.20 |
| season | winter | 2.16 | 4.96 | 6.22 |
| temperature | cold 5% | 2.32 | 5.01 | 8.56 |
| temperature | hot 5% | 2.00 | 3.64 | 4.81 |
| temperature | no weather | 2.48 | 7.85 | 7.07 |
| temperature | normal | 2.02 | 3.58 | 4.97 |

## Compute

* `operator`: 0 s fit+predict over 15 refits
* `operator_debiased`: 0 s fit+predict over 15 refits
* `seasonal_naive`: 0 s fit+predict over 15 refits
* `ridge`: 7 s fit+predict over 15 refits
* `lgbm_global`: 448 s fit+predict over 15 refits
* `nhits`: 5951 s fit+predict over 15 refits
