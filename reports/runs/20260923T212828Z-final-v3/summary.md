# Run 20260923T212828Z-final-v3 — validation split

Target days 2023-07-01 → 2024-06-30; training from 2021-04-01, expanding, refit monthly (15 refits). Protocol `realtime`: issued 10:00 local D-1 with demand to 06:00 on D-1; weather = GFS forecasts made 48 h ahead. Leakage check: 5,928,038 feature values over 11,870 forecast origins, 0 violations.

## MAPE (%) by BA

| BA | hours | operator | operator_debiased | seasonal_naive | ridge | lgbm_global | nhits |
|---|---|---|---|---|---|---|---|
| CISO | 8,781 | 6.27 | 2.67 | 6.60 | 4.40 | **3.20** | 4.48 |
| ERCO | 8,783 | 2.42 | 2.38 | 8.10 | 5.40 | **4.02** | 4.69 |
| FPL | 8,547 | 3.22 | 2.18 | 8.75 | 5.95 | **4.20** | 5.99 |
| ISNE | 8,783 | 2.49 | 1.90 | 10.35 | 6.73 | **5.26** | 6.49 |
| MISO | 8,784 | 3.11 | 1.75 | 6.80 | 4.15 | **2.57** | 3.13 |
| NYIS | 8,758 | 2.63 | 1.74 | 8.33 | 4.91 | **3.47** | 4.62 |
| PJM | 8,734 | 3.59 | 2.06 | 8.56 | 5.04 | **2.93** | 3.74 |
| SOCO | 8,782 | 1.91 | 0.95 | 9.76 | 6.49 | **4.43** | 5.11 |
| SWPP | 8,783 | 2.56 | 2.58 | 8.10 | 5.05 | **3.39** | 3.81 |
| TVA | 8,783 | 2.38 | 2.40 | 11.00 | 7.07 | **4.26** | 5.49 |

Bold = best of our models. Operator columns are benchmarks, not our models.

## Skill vs `operator` (1 - MAE/MAE_ref), 95 % block-bootstrap CI, DM p-value

| BA | model | days | skill | 95 % CI | DM p | note |
|---|---|---|---|---|---|---|
| CISO | lgbm_global | 366 | +0.481 | [+0.438, +0.526] | 2.86e-49 | operator series has a growing midday bias (data_profile 5.1) |
| CISO | nhits | 366 | +0.269 | [+0.212, +0.333] | 1.12e-14 | operator series has a growing midday bias (data_profile 5.1) |
| CISO | ridge | 366 | +0.277 | [+0.201, +0.357] | 1.99e-09 | operator series has a growing midday bias (data_profile 5.1) |
| CISO | seasonal_naive | 366 | -0.128 | [-0.300, +0.083] | 0.221 | operator series has a growing midday bias (data_profile 5.1) |
| ERCO | lgbm_global | 366 | -0.689 | [-0.975, -0.458] | 8.61e-06 |  |
| ERCO | nhits | 366 | -0.967 | [-1.339, -0.693] | 6.64e-08 |  |
| ERCO | ridge | 366 | -1.244 | [-1.544, -0.969] | 1.59e-13 |  |
| ERCO | seasonal_naive | 366 | -2.380 | [-2.891, -1.893] | 2.18e-17 |  |
| FPL | lgbm_global | 358 | -0.275 | [-0.383, -0.176] | 6.1e-07 |  |
| FPL | nhits | 358 | -0.830 | [-1.007, -0.700] | 1.43e-29 |  |
| FPL | ridge | 358 | -0.777 | [-1.045, -0.606] | 2.55e-14 |  |
| FPL | seasonal_naive | 358 | -1.645 | [-1.988, -1.387] | 1.05e-32 |  |
| ISNE | lgbm_global | 366 | -1.188 | [-1.356, -1.028] | 6.62e-46 |  |
| ISNE | nhits | 366 | -1.746 | [-1.980, -1.537] | 8.87e-62 |  |
| ISNE | ridge | 366 | -1.819 | [-2.039, -1.597] | 1.48e-55 |  |
| ISNE | seasonal_naive | 366 | -3.442 | [-4.092, -2.869] | 5.23e-22 |  |
| MISO | lgbm_global | 366 | +0.154 | [-0.003, +0.281] | 0.0624 |  |
| MISO | nhits | 366 | -0.024 | [-0.246, +0.102] | 0.792 |  |
| MISO | ridge | 366 | -0.357 | [-0.558, -0.205] | 6.06e-05 |  |
| MISO | seasonal_naive | 366 | -1.251 | [-1.663, -0.932] | 3.13e-10 |  |
| NYIS | lgbm_global | 366 | -0.331 | [-0.476, -0.191] | 8.08e-06 |  |
| NYIS | nhits | 366 | -0.775 | [-0.976, -0.583] | 3.61e-13 |  |
| NYIS | ridge | 366 | -0.863 | [-1.083, -0.670] | 6.56e-19 |  |
| NYIS | seasonal_naive | 366 | -2.252 | [-2.801, -1.710] | 1.01e-12 |  |
| PJM | lgbm_global | 364 | +0.160 | [+0.028, +0.279] | 0.0203 |  |
| PJM | nhits | 364 | -0.071 | [-0.238, +0.052] | 0.381 |  |
| PJM | ridge | 364 | -0.442 | [-0.608, -0.319] | 2.36e-09 |  |
| PJM | seasonal_naive | 364 | -1.461 | [-1.820, -1.140] | 4.5e-14 |  |
| SOCO | lgbm_global | 366 | -1.550 | [-2.164, -1.027] | 3.26e-07 |  |
| SOCO | nhits | 366 | -1.921 | [-2.377, -1.544] | 1.02e-18 |  |
| SOCO | ridge | 366 | -2.667 | [-3.401, -2.125] | 5.93e-18 |  |
| SOCO | seasonal_naive | 366 | -4.481 | [-5.672, -3.560] | 1.15e-17 |  |
| SWPP | lgbm_global | 366 | -0.328 | [-0.564, -0.143] | 0.00254 | operator series changes definition in 2025-05 (data_profile 5.2) |
| SWPP | nhits | 366 | -0.488 | [-0.776, -0.283] | 8.01e-05 | operator series changes definition in 2025-05 (data_profile 5.2) |
| SWPP | ridge | 366 | -0.975 | [-1.267, -0.744] | 2.05e-14 | operator series changes definition in 2025-05 (data_profile 5.2) |
| SWPP | seasonal_naive | 366 | -2.168 | [-2.765, -1.688] | 4.5e-17 | operator series changes definition in 2025-05 (data_profile 5.2) |
| TVA | lgbm_global | 366 | -0.820 | [-1.337, -0.538] | 6.53e-05 |  |
| TVA | nhits | 366 | -1.338 | [-1.858, -1.018] | 3.07e-10 |  |
| TVA | ridge | 366 | -1.981 | [-2.666, -1.590] | 8.62e-13 |  |
| TVA | seasonal_naive | 366 | -3.613 | [-4.762, -2.915] | 2.4e-15 |  |

## Skill vs `operator_debiased` (1 - MAE/MAE_ref), 95 % block-bootstrap CI, DM p-value

| BA | model | days | skill | 95 % CI | DM p | note |
|---|---|---|---|---|---|---|
| CISO | lgbm_global | 366 | -0.195 | [-0.274, -0.122] | 5.45e-07 |  |
| CISO | nhits | 366 | -0.683 | [-0.831, -0.551] | 4.64e-28 |  |
| CISO | ridge | 366 | -0.665 | [-0.779, -0.560] | 3.03e-24 |  |
| CISO | seasonal_naive | 366 | -1.597 | [-1.933, -1.258] | 8.58e-15 |  |
| ERCO | lgbm_global | 366 | -0.728 | [-0.982, -0.512] | 1.45e-06 |  |
| ERCO | nhits | 366 | -1.013 | [-1.312, -0.751] | 7.45e-09 |  |
| ERCO | ridge | 366 | -1.297 | [-1.573, -1.008] | 1.26e-14 |  |
| ERCO | seasonal_naive | 366 | -2.459 | [-3.004, -1.953] | 4.09e-18 |  |
| FPL | lgbm_global | 358 | -0.830 | [-0.992, -0.709] | 1.61e-32 |  |
| FPL | nhits | 358 | -1.627 | [-1.905, -1.431] | 1.61e-56 |  |
| FPL | ridge | 358 | -1.551 | [-1.882, -1.324] | 1.9e-29 |  |
| FPL | seasonal_naive | 358 | -2.797 | [-3.312, -2.415] | 1.06e-45 |  |
| ISNE | lgbm_global | 366 | -1.790 | [-1.995, -1.586] | 3.49e-60 |  |
| ISNE | nhits | 366 | -2.501 | [-2.799, -2.244] | 3.51e-75 |  |
| ISNE | ridge | 366 | -2.594 | [-2.880, -2.322] | 3.35e-65 |  |
| ISNE | seasonal_naive | 366 | -4.662 | [-5.418, -3.930] | 3.54e-24 |  |
| MISO | lgbm_global | 366 | -0.473 | [-0.676, -0.313] | 9.69e-06 |  |
| MISO | nhits | 366 | -0.783 | [-1.055, -0.589] | 5.97e-10 |  |
| MISO | ridge | 366 | -1.362 | [-1.653, -1.147] | 3.1e-23 |  |
| MISO | seasonal_naive | 366 | -2.921 | [-3.571, -2.417] | 6.37e-18 |  |
| NYIS | lgbm_global | 366 | -0.995 | [-1.163, -0.853] | 9.96e-30 |  |
| NYIS | nhits | 366 | -1.661 | [-2.010, -1.380] | 5.63e-23 |  |
| NYIS | ridge | 366 | -1.793 | [-2.056, -1.566] | 6.7e-47 |  |
| NYIS | seasonal_naive | 366 | -3.875 | [-4.655, -3.112] | 1.04e-16 |  |
| PJM | lgbm_global | 364 | -0.459 | [-0.689, -0.273] | 4.2e-05 |  |
| PJM | nhits | 364 | -0.859 | [-1.148, -0.654] | 1.36e-10 |  |
| PJM | ridge | 364 | -1.504 | [-1.770, -1.288] | 2.04e-27 |  |
| PJM | seasonal_naive | 364 | -3.273 | [-3.837, -2.764] | 5.81e-22 |  |
| SOCO | lgbm_global | 366 | -4.004 | [-5.310, -2.911] | 1.63e-11 |  |
| SOCO | nhits | 366 | -4.733 | [-5.752, -3.886] | 4.66e-29 |  |
| SOCO | ridge | 366 | -6.198 | [-7.594, -5.016] | 5.74e-25 |  |
| SOCO | seasonal_naive | 366 | -9.758 | [-12.137, -7.744] | 1.07e-21 |  |
| SWPP | lgbm_global | 366 | -0.340 | [-0.521, -0.172] | 0.000717 |  |
| SWPP | nhits | 366 | -0.502 | [-0.751, -0.296] | 1.69e-05 |  |
| SWPP | ridge | 366 | -0.993 | [-1.292, -0.694] | 1.58e-13 |  |
| SWPP | seasonal_naive | 366 | -2.196 | [-2.791, -1.706] | 1.12e-17 |  |
| TVA | lgbm_global | 366 | -0.790 | [-1.267, -0.489] | 9.84e-05 |  |
| TVA | nhits | 366 | -1.300 | [-1.809, -0.968] | 9.3e-10 |  |
| TVA | ridge | 366 | -1.932 | [-2.600, -1.508] | 1.73e-12 |  |
| TVA | seasonal_naive | 366 | -3.537 | [-4.618, -2.829] | 4.21e-15 |  |

## Prediction intervals (nominal 80 % and 95 %)

| BA | model | coverage 80 | width 80 (%) | coverage 95 | width 95 (%) |
|---|---|---|---|---|---|
| CISO | lgbm_global | 69.0 | 8.5 | 88.2 | 14.1 |
| CISO | lgbm_global+cqr | 79.8 | 10.4 | 94.7 | 17.9 |
| CISO | nhits | 81.8 | 16.2 | 95.5 | 28.1 |
| CISO | nhits+cqr | 79.7 | 15.3 | 94.9 | 27.2 |
| CISO | ridge | 77.3 | 12.9 | 93.3 | 19.8 |
| CISO | ridge+cqr | 78.8 | 13.3 | 94.2 | 20.6 |
| CISO | seasonal_naive | 78.7 | 21.5 | 94.8 | 37.8 |
| CISO | seasonal_naive+cqr | 78.1 | 21.8 | 93.8 | 36.7 |
| ERCO | lgbm_global | 70.0 | 9.7 | 87.5 | 15.7 |
| ERCO | lgbm_global+cqr | 79.3 | 12.7 | 93.5 | 24.1 |
| ERCO | nhits | 72.8 | 12.7 | 90.8 | 23.4 |
| ERCO | nhits+cqr | 79.2 | 15.0 | 94.4 | 29.4 |
| ERCO | ridge | 78.1 | 15.7 | 93.9 | 26.3 |
| ERCO | ridge+cqr | 79.0 | 17.3 | 93.2 | 29.2 |
| ERCO | seasonal_naive | 81.4 | 27.0 | 95.3 | 47.7 |
| ERCO | seasonal_naive+cqr | 78.0 | 27.0 | 92.0 | 46.2 |
| FPL | lgbm_global | 74.6 | 12.0 | 90.2 | 19.4 |
| FPL | lgbm_global+cqr | 80.2 | 13.8 | 94.5 | 23.1 |
| FPL | nhits | 75.8 | 18.5 | 94.1 | 36.2 |
| FPL | nhits+cqr | 78.7 | 20.1 | 95.1 | 37.3 |
| FPL | ridge | 75.4 | 16.8 | 91.8 | 26.5 |
| FPL | ridge+cqr | 80.1 | 19.2 | 94.2 | 29.1 |
| FPL | seasonal_naive | 78.8 | 27.3 | 96.3 | 46.3 |
| FPL | seasonal_naive+cqr | 79.7 | 28.2 | 94.1 | 41.0 |
| ISNE | lgbm_global | 68.1 | 13.8 | 84.4 | 21.1 |
| ISNE | lgbm_global+cqr | 78.4 | 17.2 | 94.4 | 29.8 |
| ISNE | nhits | 73.0 | 19.7 | 90.4 | 34.9 |
| ISNE | nhits+cqr | 78.1 | 21.9 | 94.7 | 39.3 |
| ISNE | ridge | 77.3 | 19.8 | 93.5 | 31.1 |
| ISNE | ridge+cqr | 79.0 | 20.8 | 94.3 | 32.5 |
| ISNE | seasonal_naive | 78.3 | 32.4 | 93.9 | 52.7 |
| ISNE | seasonal_naive+cqr | 77.9 | 34.1 | 92.8 | 53.7 |
| MISO | lgbm_global | 70.9 | 6.6 | 89.4 | 11.4 |
| MISO | lgbm_global+cqr | 79.9 | 8.4 | 93.7 | 15.2 |
| MISO | nhits | 84.4 | 11.9 | 96.4 | 21.3 |
| MISO | nhits+cqr | 79.4 | 10.9 | 94.6 | 21.2 |
| MISO | ridge | 78.1 | 12.4 | 94.1 | 20.3 |
| MISO | ridge+cqr | 79.9 | 13.1 | 94.4 | 22.0 |
| MISO | seasonal_naive | 79.4 | 21.2 | 94.5 | 38.5 |
| MISO | seasonal_naive+cqr | 78.6 | 22.7 | 93.0 | 38.5 |
| NYIS | lgbm_global | 69.8 | 9.4 | 86.7 | 15.2 |
| NYIS | lgbm_global+cqr | 79.7 | 11.6 | 93.7 | 20.4 |
| NYIS | nhits | 79.7 | 15.7 | 94.7 | 27.6 |
| NYIS | nhits+cqr | 79.5 | 15.5 | 95.0 | 26.6 |
| NYIS | ridge | 78.9 | 14.9 | 94.5 | 23.6 |
| NYIS | ridge+cqr | 79.5 | 15.2 | 94.7 | 24.2 |
| NYIS | seasonal_naive | 75.5 | 24.4 | 92.3 | 41.6 |
| NYIS | seasonal_naive+cqr | 76.7 | 26.8 | 91.7 | 43.5 |
| PJM | lgbm_global | 70.0 | 7.5 | 89.6 | 13.3 |
| PJM | lgbm_global+cqr | 78.6 | 9.4 | 93.1 | 16.9 |
| PJM | nhits | 80.3 | 12.9 | 94.3 | 22.8 |
| PJM | nhits+cqr | 78.9 | 12.9 | 94.7 | 23.5 |
| PJM | ridge | 75.8 | 14.2 | 92.8 | 23.1 |
| PJM | ridge+cqr | 78.5 | 15.3 | 93.6 | 26.0 |
| PJM | seasonal_naive | 74.5 | 25.1 | 93.4 | 43.3 |
| PJM | seasonal_naive+cqr | 76.4 | 28.0 | 92.4 | 43.1 |
| SOCO | lgbm_global | 67.3 | 10.3 | 85.3 | 17.2 |
| SOCO | lgbm_global+cqr | 79.5 | 14.8 | 93.2 | 25.7 |
| SOCO | nhits | 75.8 | 16.0 | 92.4 | 29.0 |
| SOCO | nhits+cqr | 79.7 | 17.9 | 94.5 | 33.1 |
| SOCO | ridge | 75.4 | 18.3 | 93.4 | 31.1 |
| SOCO | ridge+cqr | 79.3 | 21.1 | 93.7 | 34.7 |
| SOCO | seasonal_naive | 80.3 | 31.2 | 94.7 | 59.5 |
| SOCO | seasonal_naive+cqr | 79.0 | 33.2 | 93.4 | 56.5 |
| SWPP | lgbm_global | 67.0 | 7.4 | 85.8 | 12.9 |
| SWPP | lgbm_global+cqr | 80.7 | 10.8 | 95.0 | 20.6 |
| SWPP | nhits | 78.9 | 12.0 | 93.0 | 21.3 |
| SWPP | nhits+cqr | 79.6 | 12.6 | 95.0 | 26.0 |
| SWPP | ridge | 76.0 | 14.5 | 92.1 | 22.9 |
| SWPP | ridge+cqr | 80.8 | 16.4 | 94.0 | 27.6 |
| SWPP | seasonal_naive | 78.1 | 25.5 | 94.4 | 43.3 |
| SWPP | seasonal_naive+cqr | 79.6 | 27.5 | 94.1 | 45.2 |
| TVA | lgbm_global | 68.9 | 10.6 | 87.5 | 17.9 |
| TVA | lgbm_global+cqr | 78.9 | 14.7 | 93.3 | 26.9 |
| TVA | nhits | 76.2 | 16.9 | 92.0 | 30.5 |
| TVA | nhits+cqr | 79.1 | 19.3 | 94.0 | 35.2 |
| TVA | ridge | 78.4 | 20.6 | 93.0 | 33.9 |
| TVA | ridge+cqr | 79.1 | 22.9 | 93.0 | 39.1 |
| TVA | seasonal_naive | 79.8 | 36.0 | 94.8 | 65.8 |
| TVA | seasonal_naive+cqr | 78.9 | 38.4 | 93.4 | 62.3 |

## Daily peak

| BA | model | days | peak APE (%) | peak hour off by >1 h (%) |
|---|---|---|---|---|
| CISO | lgbm_global | 366 | 2.45 | 3.8 |
| CISO | nhits | 366 | 4.41 | 8.5 |
| CISO | operator | 366 | 1.78 | 7.1 |
| CISO | operator_debiased | 366 | 1.87 | 4.6 |
| CISO | ridge | 366 | 3.79 | 2.5 |
| CISO | seasonal_naive | 366 | 6.85 | 10.4 |
| ERCO | lgbm_global | 366 | 3.96 | 23.2 |
| ERCO | nhits | 366 | 5.01 | 29.0 |
| ERCO | operator | 366 | 2.52 | 15.6 |
| ERCO | operator_debiased | 366 | 2.43 | 14.8 |
| ERCO | ridge | 366 | 5.01 | 24.9 |
| ERCO | seasonal_naive | 366 | 8.58 | 34.7 |
| FPL | lgbm_global | 356 | 4.14 | 27.5 |
| FPL | nhits | 356 | 6.19 | 28.9 |
| FPL | operator | 356 | 2.76 | 20.5 |
| FPL | operator_debiased | 356 | 2.71 | 16.6 |
| FPL | ridge | 356 | 5.83 | 22.5 |
| FPL | seasonal_naive | 356 | 9.18 | 35.4 |
| ISNE | lgbm_global | 366 | 3.86 | 7.9 |
| ISNE | nhits | 366 | 5.03 | 25.4 |
| ISNE | operator | 366 | 1.48 | 2.5 |
| ISNE | operator_debiased | 366 | 1.46 | 3.6 |
| ISNE | ridge | 366 | 5.59 | 4.1 |
| ISNE | seasonal_naive | 366 | 8.27 | 7.9 |
| MISO | lgbm_global | 366 | 2.73 | 21.3 |
| MISO | nhits | 366 | 3.37 | 25.4 |
| MISO | operator | 366 | 2.96 | 9.6 |
| MISO | operator_debiased | 366 | 1.82 | 10.1 |
| MISO | ridge | 366 | 4.09 | 27.9 |
| MISO | seasonal_naive | 366 | 7.64 | 32.0 |
| NYIS | lgbm_global | 365 | 3.09 | 11.2 |
| NYIS | nhits | 365 | 4.27 | 27.7 |
| NYIS | operator | 365 | 2.69 | 5.8 |
| NYIS | operator_debiased | 365 | 1.75 | 5.5 |
| NYIS | ridge | 365 | 4.77 | 8.5 |
| NYIS | seasonal_naive | 365 | 8.08 | 11.8 |
| PJM | lgbm_global | 364 | 3.07 | 19.0 |
| PJM | nhits | 364 | 3.88 | 23.6 |
| PJM | operator | 364 | 1.72 | 17.6 |
| PJM | operator_debiased | 364 | 1.89 | 11.3 |
| PJM | ridge | 364 | 5.03 | 27.5 |
| PJM | seasonal_naive | 364 | 9.73 | 37.6 |
| SOCO | lgbm_global | 366 | 4.82 | 22.1 |
| SOCO | nhits | 366 | 5.73 | 30.6 |
| SOCO | operator | 366 | 0.77 | 3.8 |
| SOCO | operator_debiased | 366 | 0.65 | 4.4 |
| SOCO | ridge | 366 | 6.48 | 29.2 |
| SOCO | seasonal_naive | 366 | 11.83 | 37.7 |
| SWPP | lgbm_global | 366 | 3.86 | 31.1 |
| SWPP | nhits | 366 | 4.52 | 31.1 |
| SWPP | operator | 366 | 3.03 | 15.3 |
| SWPP | operator_debiased | 366 | 3.01 | 16.4 |
| SWPP | ridge | 366 | 5.28 | 32.5 |
| SWPP | seasonal_naive | 366 | 9.54 | 36.6 |
| TVA | lgbm_global | 366 | 4.70 | 24.6 |
| TVA | nhits | 366 | 6.08 | 34.4 |
| TVA | operator | 366 | 2.53 | 13.1 |
| TVA | operator_debiased | 366 | 2.67 | 13.7 |
| TVA | ridge | 366 | 6.93 | 29.5 |
| TVA | seasonal_naive | 366 | 12.52 | 45.6 |

## Slices (MAPE %, pooled over BAs)

| slice | value | operator_debiased | lgbm_global | nhits |
|---|---|---|---|---|
| day_type | holiday | 2.22 | 5.31 | 6.49 |
| day_type | weekday | 1.97 | 3.70 | 4.55 |
| day_type | weekend | 2.25 | 3.77 | 5.03 |
| hour_block | 00 | 1.80 | 3.16 | 3.90 |
| hour_block | 06 | 1.98 | 3.82 | 4.79 |
| hour_block | 12 | 2.49 | 4.56 | 5.63 |
| hour_block | 18 | 1.96 | 3.56 | 4.69 |
| season | autumn | 1.87 | 3.25 | 4.27 |
| season | spring | 2.07 | 3.32 | 4.62 |
| season | summer | 2.14 | 3.76 | 4.40 |
| season | winter | 2.16 | 4.76 | 5.71 |
| temperature | cold 5% | 2.37 | 4.91 | 7.70 |
| temperature | hot 5% | 2.16 | 3.55 | 4.35 |
| temperature | no weather | 2.48 | 7.49 | 6.89 |
| temperature | normal | 2.01 | 3.47 | 4.46 |

## Compute

* `operator`: 0 s fit+predict over 15 refits
* `operator_debiased`: 0 s fit+predict over 15 refits
* `seasonal_naive`: 0 s fit+predict over 15 refits
* `ridge`: 9 s fit+predict over 15 refits
* `lgbm_global`: 484 s fit+predict over 15 refits
* `nhits`: 4301 s fit+predict over 15 refits
