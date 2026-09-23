> **SUPERSEDED** - Population-weighted weather, training from 2021-08-01. Superseded by ladder-v3 (unweighted weather, training from 2021-04-01, chosen from the ablation); kept as the record of that decision.

# Run 20260923T061359Z-ladder-v2 — validation split

Target days 2023-07-01 → 2024-06-30; training from 2021-08-01, expanding, refit monthly (15 refits). Protocol `realtime`: issued 10:00 local D-1 with demand to 06:00 on D-1; weather = GFS forecasts made 48 h ahead. Leakage check: 5,313,115 feature values over 10,650 forecast origins, 0 violations.

## MAPE (%) by BA

| BA | hours | operator | operator_debiased | seasonal_naive | ridge | lgbm_global | lgbm_global+cqr | ridge+cqr | seasonal_naive+cqr |
|---|---|---|---|---|---|---|---|---|---|
| CISO | 8,781 | 6.27 | 2.67 | 6.60 | 4.40 | **3.39** | **3.39** | 4.40 | 6.60 |
| ERCO | 8,783 | 2.42 | 2.38 | 8.10 | 5.40 | **3.98** | **3.98** | 5.40 | 8.10 |
| FPL | 8,547 | 3.22 | 2.18 | 8.75 | 5.95 | **4.44** | **4.44** | 5.95 | 8.75 |
| ISNE | 8,783 | 2.49 | 1.90 | 10.35 | 6.78 | **5.35** | **5.35** | 6.78 | 10.35 |
| MISO | 8,784 | 3.11 | 1.75 | 6.80 | 4.11 | **2.67** | **2.67** | 4.11 | 6.80 |
| NYIS | 8,758 | 2.63 | 1.74 | 8.33 | 5.28 | **3.68** | **3.68** | 5.28 | 8.33 |
| PJM | 8,734 | 3.59 | 2.06 | 8.56 | 5.12 | **3.15** | **3.15** | 5.12 | 8.56 |
| SOCO | 8,782 | 1.91 | 0.95 | 9.76 | 6.47 | **4.48** | **4.48** | 6.47 | 9.76 |
| SWPP | 8,783 | 2.56 | 2.58 | 8.10 | 5.08 | **3.50** | **3.50** | 5.08 | 8.10 |
| TVA | 8,783 | 2.38 | 2.40 | 11.00 | 7.03 | **4.38** | **4.38** | 7.03 | 11.00 |

Bold = best of our models. Operator columns are benchmarks, not our models.

## Skill vs `operator` (1 - MAE/MAE_ref), 95 % block-bootstrap CI, DM p-value

| BA | model | days | skill | 95 % CI | DM p | note |
|---|---|---|---|---|---|---|
| CISO | lgbm_global | 366 | +0.447 | [+0.393, +0.501] | 3.93e-36 | operator series has a growing midday bias (data_profile 5.1) |
| CISO | lgbm_global+cqr | 366 | +0.447 | [+0.396, +0.503] | 3.93e-36 | operator series has a growing midday bias (data_profile 5.1) |
| CISO | ridge | 366 | +0.275 | [+0.199, +0.358] | 3.37e-09 | operator series has a growing midday bias (data_profile 5.1) |
| CISO | ridge+cqr | 366 | +0.275 | [+0.203, +0.349] | 3.37e-09 | operator series has a growing midday bias (data_profile 5.1) |
| CISO | seasonal_naive | 366 | -0.128 | [-0.300, +0.083] | 0.221 | operator series has a growing midday bias (data_profile 5.1) |
| CISO | seasonal_naive+cqr | 366 | -0.128 | [-0.333, +0.071] | 0.221 | operator series has a growing midday bias (data_profile 5.1) |
| ERCO | lgbm_global | 366 | -0.666 | [-0.951, -0.425] | 2.03e-05 |  |
| ERCO | lgbm_global+cqr | 366 | -0.666 | [-0.950, -0.422] | 2.03e-05 |  |
| ERCO | ridge | 366 | -1.253 | [-1.562, -0.962] | 7.54e-13 |  |
| ERCO | ridge+cqr | 366 | -1.253 | [-1.574, -0.966] | 7.54e-13 |  |
| ERCO | seasonal_naive | 366 | -2.380 | [-2.891, -1.893] | 2.18e-17 |  |
| ERCO | seasonal_naive+cqr | 366 | -2.380 | [-2.937, -1.911] | 2.18e-17 |  |
| FPL | lgbm_global | 358 | -0.349 | [-0.472, -0.250] | 1.12e-09 |  |
| FPL | lgbm_global+cqr | 358 | -0.349 | [-0.475, -0.245] | 1.12e-09 |  |
| FPL | ridge | 358 | -0.767 | [-0.992, -0.603] | 9.61e-18 |  |
| FPL | ridge+cqr | 358 | -0.767 | [-0.992, -0.613] | 9.61e-18 |  |
| FPL | seasonal_naive | 358 | -1.645 | [-1.988, -1.387] | 1.05e-32 |  |
| FPL | seasonal_naive+cqr | 358 | -1.645 | [-1.974, -1.376] | 1.05e-32 |  |
| ISNE | lgbm_global | 366 | -1.241 | [-1.413, -1.080] | 3.95e-44 |  |
| ISNE | lgbm_global+cqr | 366 | -1.241 | [-1.402, -1.069] | 3.95e-44 |  |
| ISNE | ridge | 366 | -1.847 | [-2.070, -1.629] | 6.08e-51 |  |
| ISNE | ridge+cqr | 366 | -1.847 | [-2.067, -1.612] | 6.08e-51 |  |
| ISNE | seasonal_naive | 366 | -3.442 | [-4.092, -2.869] | 5.23e-22 |  |
| ISNE | seasonal_naive+cqr | 366 | -3.442 | [-4.037, -2.870] | 5.23e-22 |  |
| MISO | lgbm_global | 366 | +0.124 | [-0.053, +0.262] | 0.16 |  |
| MISO | lgbm_global+cqr | 366 | +0.124 | [-0.055, +0.258] | 0.16 |  |
| MISO | ridge | 366 | -0.342 | [-0.549, -0.190] | 7.73e-05 |  |
| MISO | ridge+cqr | 366 | -0.342 | [-0.529, -0.188] | 7.73e-05 |  |
| MISO | seasonal_naive | 366 | -1.251 | [-1.663, -0.932] | 3.13e-10 |  |
| MISO | seasonal_naive+cqr | 366 | -1.251 | [-1.686, -0.918] | 3.13e-10 |  |
| NYIS | lgbm_global | 366 | -0.428 | [-0.578, -0.270] | 2.56e-07 |  |
| NYIS | lgbm_global+cqr | 366 | -0.428 | [-0.586, -0.268] | 2.56e-07 |  |
| NYIS | ridge | 366 | -1.027 | [-1.287, -0.797] | 1.76e-16 |  |
| NYIS | ridge+cqr | 366 | -1.027 | [-1.287, -0.767] | 1.76e-16 |  |
| NYIS | seasonal_naive | 366 | -2.252 | [-2.801, -1.710] | 1.01e-12 |  |
| NYIS | seasonal_naive+cqr | 366 | -2.252 | [-2.827, -1.741] | 1.01e-12 |  |
| PJM | lgbm_global | 364 | +0.096 | [-0.053, +0.220] | 0.192 |  |
| PJM | lgbm_global+cqr | 364 | +0.096 | [-0.048, +0.211] | 0.192 |  |
| PJM | ridge | 364 | -0.469 | [-0.635, -0.340] | 3.63e-09 |  |
| PJM | ridge+cqr | 364 | -0.469 | [-0.634, -0.351] | 3.63e-09 |  |
| PJM | seasonal_naive | 364 | -1.461 | [-1.820, -1.140] | 4.5e-14 |  |
| PJM | seasonal_naive+cqr | 364 | -1.461 | [-1.825, -1.166] | 4.5e-14 |  |
| SOCO | lgbm_global | 366 | -1.553 | [-2.166, -1.035] | 2.65e-07 |  |
| SOCO | lgbm_global+cqr | 366 | -1.553 | [-2.199, -1.077] | 2.65e-07 |  |
| SOCO | ridge | 366 | -2.668 | [-3.432, -2.111] | 5.15e-17 |  |
| SOCO | ridge+cqr | 366 | -2.668 | [-3.427, -2.091] | 5.15e-17 |  |
| SOCO | seasonal_naive | 366 | -4.481 | [-5.672, -3.560] | 1.15e-17 |  |
| SOCO | seasonal_naive+cqr | 366 | -4.481 | [-5.674, -3.537] | 1.15e-17 |  |
| SWPP | lgbm_global | 366 | -0.373 | [-0.623, -0.183] | 0.00139 | operator series changes definition in 2025-05 (data_profile 5.2) |
| SWPP | lgbm_global+cqr | 366 | -0.373 | [-0.631, -0.188] | 0.00139 | operator series changes definition in 2025-05 (data_profile 5.2) |
| SWPP | ridge | 366 | -0.991 | [-1.279, -0.756] | 1.12e-14 | operator series changes definition in 2025-05 (data_profile 5.2) |
| SWPP | ridge+cqr | 366 | -0.991 | [-1.259, -0.736] | 1.12e-14 | operator series changes definition in 2025-05 (data_profile 5.2) |
| SWPP | seasonal_naive | 366 | -2.168 | [-2.765, -1.688] | 4.5e-17 | operator series changes definition in 2025-05 (data_profile 5.2) |
| SWPP | seasonal_naive+cqr | 366 | -2.168 | [-2.772, -1.709] | 4.5e-17 | operator series changes definition in 2025-05 (data_profile 5.2) |
| TVA | lgbm_global | 366 | -0.873 | [-1.400, -0.567] | 4.11e-05 |  |
| TVA | lgbm_global+cqr | 366 | -0.873 | [-1.381, -0.569] | 4.11e-05 |  |
| TVA | ridge | 366 | -1.977 | [-2.650, -1.567] | 2.38e-12 |  |
| TVA | ridge+cqr | 366 | -1.977 | [-2.627, -1.560] | 2.38e-12 |  |
| TVA | seasonal_naive | 366 | -3.613 | [-4.762, -2.915] | 2.4e-15 |  |
| TVA | seasonal_naive+cqr | 366 | -3.613 | [-4.747, -2.919] | 2.4e-15 |  |

## Skill vs `operator_debiased` (1 - MAE/MAE_ref), 95 % block-bootstrap CI, DM p-value

| BA | model | days | skill | 95 % CI | DM p | note |
|---|---|---|---|---|---|---|
| CISO | lgbm_global | 366 | -0.273 | [-0.370, -0.187] | 1.7e-08 |  |
| CISO | lgbm_global+cqr | 366 | -0.273 | [-0.378, -0.180] | 1.7e-08 |  |
| CISO | ridge | 366 | -0.670 | [-0.801, -0.553] | 3.82e-21 |  |
| CISO | ridge+cqr | 366 | -0.670 | [-0.805, -0.548] | 3.82e-21 |  |
| CISO | seasonal_naive | 366 | -1.597 | [-1.933, -1.258] | 8.58e-15 |  |
| CISO | seasonal_naive+cqr | 366 | -1.597 | [-1.914, -1.255] | 8.58e-15 |  |
| ERCO | lgbm_global | 366 | -0.705 | [-0.959, -0.474] | 4.32e-06 |  |
| ERCO | lgbm_global+cqr | 366 | -0.705 | [-0.944, -0.473] | 4.32e-06 |  |
| ERCO | ridge | 366 | -1.306 | [-1.598, -1.004] | 6.19e-14 |  |
| ERCO | ridge+cqr | 366 | -1.306 | [-1.583, -0.994] | 6.19e-14 |  |
| ERCO | seasonal_naive | 366 | -2.459 | [-3.004, -1.953] | 4.09e-18 |  |
| ERCO | seasonal_naive+cqr | 366 | -2.459 | [-2.941, -1.995] | 4.09e-18 |  |
| FPL | lgbm_global | 358 | -0.936 | [-1.109, -0.806] | 1.05e-39 |  |
| FPL | lgbm_global+cqr | 358 | -0.936 | [-1.116, -0.808] | 1.05e-39 |  |
| FPL | ridge | 358 | -1.537 | [-1.840, -1.328] | 1.03e-39 |  |
| FPL | ridge+cqr | 358 | -1.537 | [-1.836, -1.319] | 1.03e-39 |  |
| FPL | seasonal_naive | 358 | -2.797 | [-3.312, -2.415] | 1.06e-45 |  |
| FPL | seasonal_naive+cqr | 358 | -2.797 | [-3.303, -2.436] | 1.06e-45 |  |
| ISNE | lgbm_global | 366 | -1.857 | [-2.059, -1.638] | 2.99e-56 |  |
| ISNE | lgbm_global+cqr | 366 | -1.857 | [-2.069, -1.641] | 2.99e-56 |  |
| ISNE | ridge | 366 | -2.629 | [-2.934, -2.358] | 1.31e-58 |  |
| ISNE | ridge+cqr | 366 | -2.629 | [-2.903, -2.346] | 1.31e-58 |  |
| ISNE | seasonal_naive | 366 | -4.662 | [-5.418, -3.930] | 3.54e-24 |  |
| ISNE | seasonal_naive+cqr | 366 | -4.662 | [-5.442, -3.936] | 3.54e-24 |  |
| MISO | lgbm_global | 366 | -0.526 | [-0.745, -0.346] | 9.38e-06 |  |
| MISO | lgbm_global+cqr | 366 | -0.526 | [-0.780, -0.347] | 9.38e-06 |  |
| MISO | ridge | 366 | -1.338 | [-1.618, -1.134] | 2.78e-24 |  |
| MISO | ridge+cqr | 366 | -1.338 | [-1.612, -1.130] | 2.78e-24 |  |
| MISO | seasonal_naive | 366 | -2.921 | [-3.571, -2.417] | 6.37e-18 |  |
| MISO | seasonal_naive+cqr | 366 | -2.921 | [-3.627, -2.440] | 6.37e-18 |  |
| NYIS | lgbm_global | 366 | -1.141 | [-1.309, -0.979] | 3.43e-28 |  |
| NYIS | lgbm_global+cqr | 366 | -1.141 | [-1.319, -0.968] | 3.43e-28 |  |
| NYIS | ridge | 366 | -2.038 | [-2.352, -1.741] | 3.33e-33 |  |
| NYIS | ridge+cqr | 366 | -2.038 | [-2.357, -1.751] | 3.33e-33 |  |
| NYIS | seasonal_naive | 366 | -3.875 | [-4.655, -3.112] | 1.04e-16 |  |
| NYIS | seasonal_naive+cqr | 366 | -3.875 | [-4.687, -3.177] | 1.04e-16 |  |
| PJM | lgbm_global | 364 | -0.570 | [-0.825, -0.371] | 3.86e-06 |  |
| PJM | lgbm_global+cqr | 364 | -0.570 | [-0.815, -0.387] | 3.86e-06 |  |
| PJM | ridge | 364 | -1.551 | [-1.843, -1.318] | 1.9e-25 |  |
| PJM | ridge+cqr | 364 | -1.551 | [-1.827, -1.339] | 1.9e-25 |  |
| PJM | seasonal_naive | 364 | -3.273 | [-3.837, -2.764] | 5.81e-22 |  |
| PJM | seasonal_naive+cqr | 364 | -3.273 | [-3.847, -2.753] | 5.81e-22 |  |
| SOCO | lgbm_global | 366 | -4.011 | [-5.313, -2.891] | 1.16e-11 |  |
| SOCO | lgbm_global+cqr | 366 | -4.011 | [-5.391, -2.996] | 1.16e-11 |  |
| SOCO | ridge | 366 | -6.199 | [-7.629, -4.985] | 1.17e-23 |  |
| SOCO | ridge+cqr | 366 | -6.199 | [-7.636, -4.889] | 1.17e-23 |  |
| SOCO | seasonal_naive | 366 | -9.758 | [-12.137, -7.744] | 1.07e-21 |  |
| SOCO | seasonal_naive+cqr | 366 | -9.758 | [-12.171, -7.747] | 1.07e-21 |  |
| SWPP | lgbm_global | 366 | -0.385 | [-0.581, -0.205] | 0.000388 |  |
| SWPP | lgbm_global+cqr | 366 | -0.385 | [-0.581, -0.201] | 0.000388 |  |
| SWPP | ridge | 366 | -1.009 | [-1.305, -0.714] | 8.46e-14 |  |
| SWPP | ridge+cqr | 366 | -1.009 | [-1.296, -0.731] | 8.46e-14 |  |
| SWPP | seasonal_naive | 366 | -2.196 | [-2.791, -1.706] | 1.12e-17 |  |
| SWPP | seasonal_naive+cqr | 366 | -2.196 | [-2.744, -1.705] | 1.12e-17 |  |
| TVA | lgbm_global | 366 | -0.842 | [-1.350, -0.526] | 5.89e-05 |  |
| TVA | lgbm_global+cqr | 366 | -0.842 | [-1.303, -0.538] | 5.89e-05 |  |
| TVA | ridge | 366 | -1.928 | [-2.614, -1.497] | 4.76e-12 |  |
| TVA | ridge+cqr | 366 | -1.928 | [-2.576, -1.501] | 4.76e-12 |  |
| TVA | seasonal_naive | 366 | -3.537 | [-4.618, -2.829] | 4.21e-15 |  |
| TVA | seasonal_naive+cqr | 366 | -3.537 | [-4.588, -2.865] | 4.21e-15 |  |

## Prediction intervals (nominal 80 % and 95 %)

| BA | model | coverage 80 | width 80 (%) | coverage 95 | width 95 (%) |
|---|---|---|---|---|---|
| CISO | lgbm_global | 68.1 | 8.8 | 87.3 | 14.4 |
| CISO | lgbm_global+cqr | 79.7 | 10.9 | 94.4 | 18.2 |
| CISO | ridge | 76.8 | 13.0 | 92.8 | 19.7 |
| CISO | ridge+cqr | 78.5 | 13.6 | 94.2 | 20.9 |
| CISO | seasonal_naive | 78.7 | 21.5 | 94.8 | 37.8 |
| CISO | seasonal_naive+cqr | 78.1 | 21.8 | 93.8 | 36.7 |
| ERCO | lgbm_global | 69.2 | 9.2 | 86.9 | 15.6 |
| ERCO | lgbm_global+cqr | 79.4 | 12.6 | 93.1 | 24.1 |
| ERCO | ridge | 77.9 | 15.7 | 93.6 | 26.2 |
| ERCO | ridge+cqr | 78.6 | 17.4 | 93.1 | 29.5 |
| ERCO | seasonal_naive | 81.4 | 27.0 | 95.3 | 47.7 |
| ERCO | seasonal_naive+cqr | 78.0 | 27.0 | 92.0 | 46.2 |
| FPL | lgbm_global | 72.7 | 12.2 | 89.3 | 19.7 |
| FPL | lgbm_global+cqr | 80.6 | 14.6 | 95.3 | 24.3 |
| FPL | ridge | 75.6 | 16.9 | 92.4 | 26.5 |
| FPL | ridge+cqr | 79.9 | 19.2 | 94.5 | 29.0 |
| FPL | seasonal_naive | 78.8 | 27.3 | 96.3 | 46.3 |
| FPL | seasonal_naive+cqr | 79.7 | 28.2 | 94.1 | 41.0 |
| ISNE | lgbm_global | 68.1 | 13.9 | 83.8 | 21.0 |
| ISNE | lgbm_global+cqr | 78.6 | 17.4 | 94.2 | 30.3 |
| ISNE | ridge | 77.3 | 20.0 | 93.1 | 31.5 |
| ISNE | ridge+cqr | 78.8 | 21.1 | 94.1 | 33.7 |
| ISNE | seasonal_naive | 78.3 | 32.4 | 93.9 | 52.7 |
| ISNE | seasonal_naive+cqr | 77.9 | 34.1 | 92.8 | 53.7 |
| MISO | lgbm_global | 70.3 | 6.6 | 89.1 | 11.7 |
| MISO | lgbm_global+cqr | 79.7 | 8.6 | 93.5 | 15.9 |
| MISO | ridge | 77.9 | 12.3 | 93.9 | 20.2 |
| MISO | ridge+cqr | 79.9 | 13.1 | 94.4 | 22.0 |
| MISO | seasonal_naive | 79.4 | 21.2 | 94.5 | 38.5 |
| MISO | seasonal_naive+cqr | 78.6 | 22.7 | 93.0 | 38.5 |
| NYIS | lgbm_global | 66.6 | 9.2 | 84.8 | 14.7 |
| NYIS | lgbm_global+cqr | 79.0 | 11.9 | 94.3 | 21.1 |
| NYIS | ridge | 76.2 | 15.0 | 92.9 | 24.3 |
| NYIS | ridge+cqr | 79.3 | 16.4 | 93.9 | 27.1 |
| NYIS | seasonal_naive | 75.5 | 24.4 | 92.3 | 41.6 |
| NYIS | seasonal_naive+cqr | 76.7 | 26.8 | 91.7 | 43.5 |
| PJM | lgbm_global | 68.4 | 7.8 | 87.7 | 13.5 |
| PJM | lgbm_global+cqr | 78.0 | 10.0 | 92.8 | 18.0 |
| PJM | ridge | 75.3 | 14.2 | 92.2 | 23.3 |
| PJM | ridge+cqr | 78.5 | 15.7 | 93.6 | 26.7 |
| PJM | seasonal_naive | 74.5 | 25.1 | 93.4 | 43.3 |
| PJM | seasonal_naive+cqr | 76.4 | 28.0 | 92.4 | 43.1 |
| SOCO | lgbm_global | 66.8 | 10.5 | 85.9 | 17.6 |
| SOCO | lgbm_global+cqr | 78.9 | 15.1 | 93.0 | 25.9 |
| SOCO | ridge | 75.8 | 18.2 | 93.1 | 31.1 |
| SOCO | ridge+cqr | 79.6 | 21.1 | 93.9 | 35.4 |
| SOCO | seasonal_naive | 80.3 | 31.2 | 94.7 | 59.5 |
| SOCO | seasonal_naive+cqr | 79.0 | 33.2 | 93.4 | 56.5 |
| SWPP | lgbm_global | 65.1 | 7.2 | 85.8 | 13.2 |
| SWPP | lgbm_global+cqr | 81.3 | 11.1 | 94.9 | 20.6 |
| SWPP | ridge | 75.7 | 14.4 | 92.1 | 23.1 |
| SWPP | ridge+cqr | 80.8 | 16.5 | 94.1 | 27.9 |
| SWPP | seasonal_naive | 78.1 | 25.5 | 94.4 | 43.3 |
| SWPP | seasonal_naive+cqr | 79.6 | 27.5 | 94.1 | 45.2 |
| TVA | lgbm_global | 68.5 | 10.5 | 86.5 | 17.8 |
| TVA | lgbm_global+cqr | 79.2 | 14.8 | 93.1 | 27.2 |
| TVA | ridge | 78.6 | 20.4 | 92.6 | 33.9 |
| TVA | ridge+cqr | 79.3 | 23.0 | 92.8 | 39.7 |
| TVA | seasonal_naive | 79.8 | 36.0 | 94.8 | 65.8 |
| TVA | seasonal_naive+cqr | 78.9 | 38.4 | 93.4 | 62.3 |

## Daily peak

| BA | model | days | peak APE (%) | peak hour off by >1 h (%) |
|---|---|---|---|---|
| CISO | lgbm_global | 366 | 2.78 | 3.6 |
| CISO | lgbm_global+cqr | 366 | 2.78 | 3.6 |
| CISO | operator | 366 | 1.78 | 7.4 |
| CISO | operator_debiased | 366 | 1.87 | 4.6 |
| CISO | ridge | 366 | 3.72 | 2.5 |
| CISO | ridge+cqr | 366 | 3.72 | 2.5 |
| CISO | seasonal_naive | 366 | 6.85 | 10.4 |
| CISO | seasonal_naive+cqr | 366 | 6.85 | 10.4 |
| ERCO | lgbm_global | 366 | 3.94 | 26.2 |
| ERCO | lgbm_global+cqr | 366 | 3.94 | 26.2 |
| ERCO | operator | 366 | 2.52 | 15.3 |
| ERCO | operator_debiased | 366 | 2.43 | 14.8 |
| ERCO | ridge | 366 | 5.05 | 26.5 |
| ERCO | ridge+cqr | 366 | 5.05 | 26.5 |
| ERCO | seasonal_naive | 366 | 8.58 | 34.7 |
| ERCO | seasonal_naive+cqr | 366 | 8.58 | 34.7 |
| FPL | lgbm_global | 356 | 4.59 | 25.8 |
| FPL | lgbm_global+cqr | 356 | 4.59 | 25.8 |
| FPL | operator | 356 | 2.76 | 20.5 |
| FPL | operator_debiased | 356 | 2.71 | 16.9 |
| FPL | ridge | 356 | 5.93 | 20.8 |
| FPL | ridge+cqr | 356 | 5.93 | 20.8 |
| FPL | seasonal_naive | 356 | 9.18 | 35.4 |
| FPL | seasonal_naive+cqr | 356 | 9.18 | 35.4 |
| ISNE | lgbm_global | 366 | 3.96 | 7.4 |
| ISNE | lgbm_global+cqr | 366 | 3.96 | 7.4 |
| ISNE | operator | 366 | 1.48 | 2.5 |
| ISNE | operator_debiased | 366 | 1.46 | 3.6 |
| ISNE | ridge | 366 | 5.55 | 4.4 |
| ISNE | ridge+cqr | 366 | 5.55 | 4.4 |
| ISNE | seasonal_naive | 366 | 8.27 | 7.9 |
| ISNE | seasonal_naive+cqr | 366 | 8.27 | 7.9 |
| MISO | lgbm_global | 366 | 2.80 | 24.0 |
| MISO | lgbm_global+cqr | 366 | 2.80 | 24.0 |
| MISO | operator | 366 | 2.96 | 9.3 |
| MISO | operator_debiased | 366 | 1.82 | 9.8 |
| MISO | ridge | 366 | 4.05 | 31.4 |
| MISO | ridge+cqr | 366 | 4.05 | 31.4 |
| MISO | seasonal_naive | 366 | 7.64 | 32.0 |
| MISO | seasonal_naive+cqr | 366 | 7.64 | 32.0 |
| NYIS | lgbm_global | 365 | 3.52 | 11.8 |
| NYIS | lgbm_global+cqr | 365 | 3.52 | 11.8 |
| NYIS | operator | 365 | 2.69 | 5.8 |
| NYIS | operator_debiased | 365 | 1.75 | 5.5 |
| NYIS | ridge | 365 | 5.17 | 7.9 |
| NYIS | ridge+cqr | 365 | 5.17 | 7.9 |
| NYIS | seasonal_naive | 365 | 8.08 | 12.1 |
| NYIS | seasonal_naive+cqr | 365 | 8.08 | 12.1 |
| PJM | lgbm_global | 364 | 3.27 | 22.3 |
| PJM | lgbm_global+cqr | 364 | 3.27 | 22.3 |
| PJM | operator | 364 | 1.72 | 17.6 |
| PJM | operator_debiased | 364 | 1.89 | 11.3 |
| PJM | ridge | 364 | 5.23 | 28.6 |
| PJM | ridge+cqr | 364 | 5.23 | 28.6 |
| PJM | seasonal_naive | 364 | 9.73 | 37.6 |
| PJM | seasonal_naive+cqr | 364 | 9.73 | 37.6 |
| SOCO | lgbm_global | 366 | 4.66 | 23.8 |
| SOCO | lgbm_global+cqr | 366 | 4.66 | 23.8 |
| SOCO | operator | 366 | 0.77 | 3.8 |
| SOCO | operator_debiased | 366 | 0.65 | 4.4 |
| SOCO | ridge | 366 | 6.68 | 27.6 |
| SOCO | ridge+cqr | 366 | 6.68 | 27.6 |
| SOCO | seasonal_naive | 366 | 11.83 | 37.7 |
| SOCO | seasonal_naive+cqr | 366 | 11.83 | 37.7 |
| SWPP | lgbm_global | 366 | 3.98 | 28.4 |
| SWPP | lgbm_global+cqr | 366 | 3.98 | 28.4 |
| SWPP | operator | 366 | 3.03 | 15.8 |
| SWPP | operator_debiased | 366 | 3.01 | 17.5 |
| SWPP | ridge | 366 | 5.40 | 32.5 |
| SWPP | ridge+cqr | 366 | 5.40 | 32.5 |
| SWPP | seasonal_naive | 366 | 9.54 | 37.2 |
| SWPP | seasonal_naive+cqr | 366 | 9.54 | 37.2 |
| TVA | lgbm_global | 366 | 4.70 | 28.1 |
| TVA | lgbm_global+cqr | 366 | 4.70 | 28.1 |
| TVA | operator | 366 | 2.53 | 12.8 |
| TVA | operator_debiased | 366 | 2.67 | 13.7 |
| TVA | ridge | 366 | 7.03 | 30.1 |
| TVA | ridge+cqr | 366 | 7.03 | 30.1 |
| TVA | seasonal_naive | 366 | 12.52 | 45.6 |
| TVA | seasonal_naive+cqr | 366 | 12.52 | 45.6 |

## Slices (MAPE %, pooled over BAs)

| slice | value | operator_debiased | lgbm_global+cqr | ridge+cqr | seasonal_naive+cqr |
|---|---|---|---|---|---|
| day_type | holiday | 2.22 | 5.60 | 7.43 | 10.91 |
| day_type | weekday | 1.97 | 3.83 | 5.39 | 8.49 |
| day_type | weekend | 2.25 | 3.88 | 5.75 | 8.71 |
| hour_block | 00 | 1.80 | 3.24 | 4.99 | 8.21 |
| hour_block | 06 | 1.98 | 3.90 | 5.85 | 8.33 |
| hour_block | 12 | 2.49 | 4.75 | 6.03 | 9.77 |
| hour_block | 18 | 1.96 | 3.72 | 5.37 | 8.22 |
| season | autumn | 1.87 | 3.34 | 5.09 | 8.92 |
| season | spring | 2.07 | 3.41 | 4.67 | 7.20 |
| season | summer | 2.14 | 3.89 | 5.91 | 8.70 |
| season | winter | 2.16 | 4.96 | 6.58 | 9.73 |
| temperature | cold 5% | 2.32 | 5.01 | 7.19 | 10.90 |
| temperature | hot 5% | 2.00 | 3.64 | 4.96 | 10.89 |
| temperature | no weather | 2.48 | 7.85 | 8.64 | 10.39 |
| temperature | normal | 2.02 | 3.58 | 5.29 | 8.25 |

## Compute

* `operator`: 0 s fit+predict over 15 refits
* `operator_debiased`: 0 s fit+predict over 15 refits
* `seasonal_naive`: 0 s fit+predict over 15 refits
* `ridge`: 7 s fit+predict over 15 refits
* `lgbm_global`: 448 s fit+predict over 15 refits
