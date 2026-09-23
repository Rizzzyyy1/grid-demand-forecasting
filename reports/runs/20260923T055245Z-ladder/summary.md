> **SUPERSEDED** - Feature set v1 (no recent-day temperature features). Superseded by ladder-v2; kept as the record of that decision.

# Run 20260923T055245Z-ladder — validation split

Target days 2023-07-01 → 2024-06-30; training from 2021-08-01, expanding, refit monthly (15 refits). Issue time 10:00 local D-1; demand up to 06:00 D-1; weather = GFS forecasts made 48 h ahead. Leakage check: 4,811,798 feature values over 10,650 forecast origins, 0 violations.

## MAPE (%) by BA

| BA | hours | operator | operator_debiased | seasonal_naive | ridge | lgbm_global | lgbm_global+cqr | ridge+cqr | seasonal_naive+cqr |
|---|---|---|---|---|---|---|---|---|---|
| CISO | 8,781 | 6.27 | 2.67 | 6.60 | 4.40 | **3.46** | **3.46** | 4.40 | 6.60 |
| ERCO | 8,783 | 2.42 | 2.38 | 8.10 | 5.40 | **4.40** | **4.40** | 5.40 | 8.10 |
| FPL | 8,547 | 3.22 | 2.18 | 8.75 | 5.95 | **4.90** | **4.90** | 5.95 | 8.75 |
| ISNE | 8,783 | 2.49 | 1.90 | 10.35 | 6.78 | **5.59** | **5.59** | 6.78 | 10.35 |
| MISO | 8,784 | 3.11 | 1.75 | 6.80 | 4.11 | **2.90** | **2.90** | 4.11 | 6.80 |
| NYIS | 8,758 | 2.63 | 1.74 | 8.33 | 5.28 | **4.03** | **4.03** | 5.28 | 8.33 |
| PJM | 8,734 | 3.59 | 2.06 | 8.56 | 5.12 | **3.39** | **3.39** | 5.12 | 8.56 |
| SOCO | 8,782 | 1.91 | 0.95 | 9.76 | 6.47 | **4.67** | **4.67** | 6.47 | 9.76 |
| SWPP | 8,783 | 2.56 | 2.58 | 8.10 | 5.08 | **3.91** | **3.91** | 5.08 | 8.10 |
| TVA | 8,783 | 2.38 | 2.40 | 11.00 | 7.03 | **4.77** | **4.77** | 7.03 | 11.00 |

Bold = best of our models. Operator columns are benchmarks, not our models.

## Skill vs `operator` (1 - MAE/MAE_ref), 95 % block-bootstrap CI, DM p-value

| BA | model | days | skill | 95 % CI | DM p | note |
|---|---|---|---|---|---|---|
| CISO | lgbm_global | 366 | +0.433 | [+0.378, +0.485] | 2.44e-32 | operator series has a growing midday bias (data_profile 5.1) |
| CISO | lgbm_global+cqr | 366 | +0.433 | [+0.378, +0.487] | 2.44e-32 | operator series has a growing midday bias (data_profile 5.1) |
| CISO | ridge | 366 | +0.275 | [+0.195, +0.353] | 3.37e-09 | operator series has a growing midday bias (data_profile 5.1) |
| CISO | ridge+cqr | 366 | +0.275 | [+0.194, +0.349] | 3.37e-09 | operator series has a growing midday bias (data_profile 5.1) |
| CISO | seasonal_naive | 366 | -0.128 | [-0.316, +0.068] | 0.221 | operator series has a growing midday bias (data_profile 5.1) |
| CISO | seasonal_naive+cqr | 366 | -0.128 | [-0.299, +0.075] | 0.221 | operator series has a growing midday bias (data_profile 5.1) |
| ERCO | lgbm_global | 366 | -0.841 | [-1.186, -0.550] | 7.31e-06 |  |
| ERCO | lgbm_global+cqr | 366 | -0.841 | [-1.176, -0.553] | 7.31e-06 |  |
| ERCO | ridge | 366 | -1.253 | [-1.564, -0.955] | 7.54e-13 |  |
| ERCO | ridge+cqr | 366 | -1.253 | [-1.587, -0.950] | 7.54e-13 |  |
| ERCO | seasonal_naive | 366 | -2.380 | [-2.951, -1.884] | 2.18e-17 |  |
| ERCO | seasonal_naive+cqr | 366 | -2.380 | [-2.880, -1.903] | 2.18e-17 |  |
| FPL | lgbm_global | 358 | -0.488 | [-0.651, -0.362] | 2.15e-13 |  |
| FPL | lgbm_global+cqr | 358 | -0.488 | [-0.634, -0.370] | 2.15e-13 |  |
| FPL | ridge | 358 | -0.767 | [-0.980, -0.615] | 9.61e-18 |  |
| FPL | ridge+cqr | 358 | -0.767 | [-0.992, -0.606] | 9.61e-18 |  |
| FPL | seasonal_naive | 358 | -1.645 | [-1.952, -1.400] | 1.05e-32 |  |
| FPL | seasonal_naive+cqr | 358 | -1.645 | [-1.978, -1.395] | 1.05e-32 |  |
| ISNE | lgbm_global | 366 | -1.349 | [-1.549, -1.152] | 1.51e-40 |  |
| ISNE | lgbm_global+cqr | 366 | -1.349 | [-1.543, -1.176] | 1.51e-40 |  |
| ISNE | ridge | 366 | -1.847 | [-2.083, -1.642] | 6.08e-51 |  |
| ISNE | ridge+cqr | 366 | -1.847 | [-2.064, -1.626] | 6.08e-51 |  |
| ISNE | seasonal_naive | 366 | -3.442 | [-4.071, -2.872] | 5.23e-22 |  |
| ISNE | seasonal_naive+cqr | 366 | -3.442 | [-4.089, -2.858] | 5.23e-22 |  |
| MISO | lgbm_global | 366 | +0.049 | [-0.177, +0.240] | 0.663 |  |
| MISO | lgbm_global+cqr | 366 | +0.049 | [-0.173, +0.228] | 0.663 |  |
| MISO | ridge | 366 | -0.342 | [-0.521, -0.190] | 7.73e-05 |  |
| MISO | ridge+cqr | 366 | -0.342 | [-0.530, -0.190] | 7.73e-05 |  |
| MISO | seasonal_naive | 366 | -1.251 | [-1.632, -0.922] | 3.13e-10 |  |
| MISO | seasonal_naive+cqr | 366 | -1.251 | [-1.675, -0.915] | 3.13e-10 |  |
| NYIS | lgbm_global | 366 | -0.566 | [-0.755, -0.376] | 1.01e-08 |  |
| NYIS | lgbm_global+cqr | 366 | -0.566 | [-0.750, -0.374] | 1.01e-08 |  |
| NYIS | ridge | 366 | -1.027 | [-1.284, -0.780] | 1.76e-16 |  |
| NYIS | ridge+cqr | 366 | -1.027 | [-1.283, -0.808] | 1.76e-16 |  |
| NYIS | seasonal_naive | 366 | -2.252 | [-2.866, -1.694] | 1.01e-12 |  |
| NYIS | seasonal_naive+cqr | 366 | -2.252 | [-2.802, -1.730] | 1.01e-12 |  |
| PJM | lgbm_global | 364 | +0.025 | [-0.178, +0.174] | 0.795 |  |
| PJM | lgbm_global+cqr | 364 | +0.025 | [-0.203, +0.171] | 0.795 |  |
| PJM | ridge | 364 | -0.469 | [-0.642, -0.339] | 3.63e-09 |  |
| PJM | ridge+cqr | 364 | -0.469 | [-0.656, -0.343] | 3.63e-09 |  |
| PJM | seasonal_naive | 364 | -1.461 | [-1.868, -1.127] | 4.5e-14 |  |
| PJM | seasonal_naive+cqr | 364 | -1.461 | [-1.850, -1.154] | 4.5e-14 |  |
| SOCO | lgbm_global | 366 | -1.653 | [-2.310, -1.150] | 1.89e-07 |  |
| SOCO | lgbm_global+cqr | 366 | -1.653 | [-2.312, -1.133] | 1.89e-07 |  |
| SOCO | ridge | 366 | -2.668 | [-3.423, -2.106] | 5.15e-17 |  |
| SOCO | ridge+cqr | 366 | -2.668 | [-3.344, -2.117] | 5.15e-17 |  |
| SOCO | seasonal_naive | 366 | -4.481 | [-5.694, -3.543] | 1.15e-17 |  |
| SOCO | seasonal_naive+cqr | 366 | -4.481 | [-5.550, -3.535] | 1.15e-17 |  |
| SWPP | lgbm_global | 366 | -0.538 | [-0.898, -0.300] | 0.000942 | operator series changes definition in 2025-05 (data_profile 5.2) |
| SWPP | lgbm_global+cqr | 366 | -0.538 | [-0.885, -0.300] | 0.000942 | operator series changes definition in 2025-05 (data_profile 5.2) |
| SWPP | ridge | 366 | -0.991 | [-1.272, -0.748] | 1.12e-14 | operator series changes definition in 2025-05 (data_profile 5.2) |
| SWPP | ridge+cqr | 366 | -0.991 | [-1.259, -0.757] | 1.12e-14 | operator series changes definition in 2025-05 (data_profile 5.2) |
| SWPP | seasonal_naive | 366 | -2.168 | [-2.787, -1.664] | 4.5e-17 | operator series changes definition in 2025-05 (data_profile 5.2) |
| SWPP | seasonal_naive+cqr | 366 | -2.168 | [-2.791, -1.691] | 4.5e-17 | operator series changes definition in 2025-05 (data_profile 5.2) |
| TVA | lgbm_global | 366 | -1.039 | [-1.614, -0.685] | 5.69e-05 |  |
| TVA | lgbm_global+cqr | 366 | -1.039 | [-1.609, -0.661] | 5.69e-05 |  |
| TVA | ridge | 366 | -1.977 | [-2.605, -1.573] | 2.38e-12 |  |
| TVA | ridge+cqr | 366 | -1.977 | [-2.703, -1.524] | 2.38e-12 |  |
| TVA | seasonal_naive | 366 | -3.613 | [-4.807, -2.934] | 2.4e-15 |  |
| TVA | seasonal_naive+cqr | 366 | -3.613 | [-4.763, -2.896] | 2.4e-15 |  |

## Skill vs `operator_debiased` (1 - MAE/MAE_ref), 95 % block-bootstrap CI, DM p-value

| BA | model | days | skill | 95 % CI | DM p | note |
|---|---|---|---|---|---|---|
| CISO | lgbm_global | 366 | -0.305 | [-0.404, -0.209] | 2.08e-09 |  |
| CISO | lgbm_global+cqr | 366 | -0.305 | [-0.413, -0.209] | 2.08e-09 |  |
| CISO | ridge | 366 | -0.670 | [-0.810, -0.555] | 3.82e-21 |  |
| CISO | ridge+cqr | 366 | -0.670 | [-0.820, -0.544] | 3.82e-21 |  |
| CISO | seasonal_naive | 366 | -1.597 | [-1.929, -1.253] | 8.58e-15 |  |
| CISO | seasonal_naive+cqr | 366 | -1.597 | [-1.926, -1.273] | 8.58e-15 |  |
| ERCO | lgbm_global | 366 | -0.884 | [-1.190, -0.627] | 1.84e-06 |  |
| ERCO | lgbm_global+cqr | 366 | -0.884 | [-1.175, -0.598] | 1.84e-06 |  |
| ERCO | ridge | 366 | -1.306 | [-1.615, -0.992] | 6.19e-14 |  |
| ERCO | ridge+cqr | 366 | -1.306 | [-1.588, -0.989] | 6.19e-14 |  |
| ERCO | seasonal_naive | 366 | -2.459 | [-2.930, -1.974] | 4.09e-18 |  |
| ERCO | seasonal_naive+cqr | 366 | -2.459 | [-2.967, -1.998] | 4.09e-18 |  |
| FPL | lgbm_global | 358 | -1.135 | [-1.332, -0.999] | 1.37e-41 |  |
| FPL | lgbm_global+cqr | 358 | -1.135 | [-1.346, -0.983] | 1.37e-41 |  |
| FPL | ridge | 358 | -1.537 | [-1.863, -1.333] | 1.03e-39 |  |
| FPL | ridge+cqr | 358 | -1.537 | [-1.857, -1.317] | 1.03e-39 |  |
| FPL | seasonal_naive | 358 | -2.797 | [-3.329, -2.449] | 1.06e-45 |  |
| FPL | seasonal_naive+cqr | 358 | -2.797 | [-3.300, -2.416] | 1.06e-45 |  |
| ISNE | lgbm_global | 366 | -1.995 | [-2.235, -1.726] | 1.04e-49 |  |
| ISNE | lgbm_global+cqr | 366 | -1.995 | [-2.251, -1.746] | 1.04e-49 |  |
| ISNE | ridge | 366 | -2.629 | [-2.907, -2.324] | 1.31e-58 |  |
| ISNE | ridge+cqr | 366 | -2.629 | [-2.923, -2.329] | 1.31e-58 |  |
| ISNE | seasonal_naive | 366 | -4.662 | [-5.413, -3.961] | 3.54e-24 |  |
| ISNE | seasonal_naive+cqr | 366 | -4.662 | [-5.381, -3.914] | 3.54e-24 |  |
| MISO | lgbm_global | 366 | -0.656 | [-1.002, -0.391] | 0.000102 |  |
| MISO | lgbm_global+cqr | 366 | -0.656 | [-0.971, -0.393] | 0.000102 |  |
| MISO | ridge | 366 | -1.338 | [-1.603, -1.131] | 2.78e-24 |  |
| MISO | ridge+cqr | 366 | -1.338 | [-1.605, -1.107] | 2.78e-24 |  |
| MISO | seasonal_naive | 366 | -2.921 | [-3.529, -2.460] | 6.37e-18 |  |
| MISO | seasonal_naive+cqr | 366 | -2.921 | [-3.608, -2.439] | 6.37e-18 |  |
| NYIS | lgbm_global | 366 | -1.348 | [-1.558, -1.140] | 3.91e-25 |  |
| NYIS | lgbm_global+cqr | 366 | -1.348 | [-1.574, -1.131] | 3.91e-25 |  |
| NYIS | ridge | 366 | -2.038 | [-2.335, -1.777] | 3.33e-33 |  |
| NYIS | ridge+cqr | 366 | -2.038 | [-2.350, -1.778] | 3.33e-33 |  |
| NYIS | seasonal_naive | 366 | -3.875 | [-4.659, -3.148] | 1.04e-16 |  |
| NYIS | seasonal_naive+cqr | 366 | -3.875 | [-4.661, -3.150] | 1.04e-16 |  |
| PJM | lgbm_global | 364 | -0.692 | [-1.074, -0.437] | 3.02e-05 |  |
| PJM | lgbm_global+cqr | 364 | -0.692 | [-1.033, -0.433] | 3.02e-05 |  |
| PJM | ridge | 364 | -1.551 | [-1.847, -1.334] | 1.9e-25 |  |
| PJM | ridge+cqr | 364 | -1.551 | [-1.847, -1.314] | 1.9e-25 |  |
| PJM | seasonal_naive | 364 | -3.273 | [-3.865, -2.744] | 5.81e-22 |  |
| PJM | seasonal_naive+cqr | 364 | -3.273 | [-3.892, -2.753] | 5.81e-22 |  |
| SOCO | lgbm_global | 366 | -4.207 | [-5.588, -3.062] | 1.27e-11 |  |
| SOCO | lgbm_global+cqr | 366 | -4.207 | [-5.576, -3.091] | 1.27e-11 |  |
| SOCO | ridge | 366 | -6.199 | [-7.743, -5.088] | 1.17e-23 |  |
| SOCO | ridge+cqr | 366 | -6.199 | [-7.479, -4.999] | 1.17e-23 |  |
| SOCO | seasonal_naive | 366 | -9.758 | [-12.041, -7.769] | 1.07e-21 |  |
| SOCO | seasonal_naive+cqr | 366 | -9.758 | [-12.135, -7.671] | 1.07e-21 |  |
| SWPP | lgbm_global | 366 | -0.552 | [-0.837, -0.295] | 0.000408 |  |
| SWPP | lgbm_global+cqr | 366 | -0.552 | [-0.837, -0.310] | 0.000408 |  |
| SWPP | ridge | 366 | -1.009 | [-1.296, -0.722] | 8.46e-14 |  |
| SWPP | ridge+cqr | 366 | -1.009 | [-1.288, -0.741] | 8.46e-14 |  |
| SWPP | seasonal_naive | 366 | -2.196 | [-2.744, -1.701] | 1.12e-17 |  |
| SWPP | seasonal_naive+cqr | 366 | -2.196 | [-2.752, -1.732] | 1.12e-17 |  |
| TVA | lgbm_global | 366 | -1.006 | [-1.581, -0.649] | 7.48e-05 |  |
| TVA | lgbm_global+cqr | 366 | -1.006 | [-1.602, -0.649] | 7.48e-05 |  |
| TVA | ridge | 366 | -1.928 | [-2.555, -1.496] | 4.76e-12 |  |
| TVA | ridge+cqr | 366 | -1.928 | [-2.625, -1.463] | 4.76e-12 |  |
| TVA | seasonal_naive | 366 | -3.537 | [-4.555, -2.851] | 4.21e-15 |  |
| TVA | seasonal_naive+cqr | 366 | -3.537 | [-4.587, -2.839] | 4.21e-15 |  |

## Prediction intervals (nominal 80 % and 95 %)

| BA | model | coverage 80 | width 80 (%) | coverage 95 | width 95 (%) |
|---|---|---|---|---|---|
| CISO | lgbm_global | 68.5 | 9.2 | 87.0 | 14.8 |
| CISO | lgbm_global+cqr | 79.7 | 11.2 | 94.5 | 18.5 |
| CISO | ridge | 76.8 | 13.0 | 92.8 | 19.7 |
| CISO | ridge+cqr | 78.5 | 13.6 | 94.2 | 20.9 |
| CISO | seasonal_naive | 78.7 | 21.5 | 94.8 | 37.8 |
| CISO | seasonal_naive+cqr | 78.1 | 21.8 | 93.8 | 36.7 |
| ERCO | lgbm_global | 69.5 | 9.8 | 86.8 | 16.3 |
| ERCO | lgbm_global+cqr | 80.1 | 13.1 | 93.1 | 26.2 |
| ERCO | ridge | 77.9 | 15.7 | 93.6 | 26.2 |
| ERCO | ridge+cqr | 78.6 | 17.4 | 93.1 | 29.5 |
| ERCO | seasonal_naive | 81.4 | 27.0 | 95.3 | 47.7 |
| ERCO | seasonal_naive+cqr | 78.0 | 27.0 | 92.0 | 46.2 |
| FPL | lgbm_global | 71.1 | 12.7 | 89.1 | 20.3 |
| FPL | lgbm_global+cqr | 80.4 | 15.3 | 95.1 | 25.0 |
| FPL | ridge | 75.6 | 16.9 | 92.4 | 26.5 |
| FPL | ridge+cqr | 79.9 | 19.2 | 94.5 | 29.0 |
| FPL | seasonal_naive | 78.8 | 27.3 | 96.3 | 46.3 |
| FPL | seasonal_naive+cqr | 79.7 | 28.2 | 94.1 | 41.0 |
| ISNE | lgbm_global | 68.5 | 14.4 | 83.7 | 21.7 |
| ISNE | lgbm_global+cqr | 78.6 | 18.2 | 93.9 | 30.9 |
| ISNE | ridge | 77.3 | 20.0 | 93.1 | 31.5 |
| ISNE | ridge+cqr | 78.8 | 21.1 | 94.1 | 33.7 |
| ISNE | seasonal_naive | 78.3 | 32.4 | 93.9 | 52.7 |
| ISNE | seasonal_naive+cqr | 77.9 | 34.1 | 92.8 | 53.7 |
| MISO | lgbm_global | 68.8 | 6.8 | 88.1 | 12.2 |
| MISO | lgbm_global+cqr | 79.4 | 9.1 | 93.3 | 17.4 |
| MISO | ridge | 77.9 | 12.3 | 93.9 | 20.2 |
| MISO | ridge+cqr | 79.9 | 13.1 | 94.4 | 22.0 |
| MISO | seasonal_naive | 79.4 | 21.2 | 94.5 | 38.5 |
| MISO | seasonal_naive+cqr | 78.6 | 22.7 | 93.0 | 38.5 |
| NYIS | lgbm_global | 65.7 | 9.5 | 84.1 | 15.3 |
| NYIS | lgbm_global+cqr | 78.7 | 12.6 | 94.1 | 22.2 |
| NYIS | ridge | 76.2 | 15.0 | 92.9 | 24.3 |
| NYIS | ridge+cqr | 79.3 | 16.4 | 93.9 | 27.1 |
| NYIS | seasonal_naive | 75.5 | 24.4 | 92.3 | 41.6 |
| NYIS | seasonal_naive+cqr | 76.7 | 26.8 | 91.7 | 43.5 |
| PJM | lgbm_global | 68.7 | 8.1 | 88.0 | 14.1 |
| PJM | lgbm_global+cqr | 77.5 | 10.3 | 92.3 | 19.8 |
| PJM | ridge | 75.3 | 14.2 | 92.2 | 23.3 |
| PJM | ridge+cqr | 78.5 | 15.7 | 93.6 | 26.7 |
| PJM | seasonal_naive | 74.5 | 25.1 | 93.4 | 43.3 |
| PJM | seasonal_naive+cqr | 76.4 | 28.0 | 92.4 | 43.1 |
| SOCO | lgbm_global | 66.2 | 10.7 | 85.4 | 17.8 |
| SOCO | lgbm_global+cqr | 79.2 | 15.5 | 93.1 | 26.8 |
| SOCO | ridge | 75.8 | 18.2 | 93.1 | 31.1 |
| SOCO | ridge+cqr | 79.6 | 21.1 | 93.9 | 35.4 |
| SOCO | seasonal_naive | 80.3 | 31.2 | 94.7 | 59.5 |
| SOCO | seasonal_naive+cqr | 79.0 | 33.2 | 93.4 | 56.5 |
| SWPP | lgbm_global | 64.6 | 7.6 | 85.6 | 13.6 |
| SWPP | lgbm_global+cqr | 81.6 | 12.0 | 94.8 | 22.7 |
| SWPP | ridge | 75.7 | 14.4 | 92.1 | 23.1 |
| SWPP | ridge+cqr | 80.8 | 16.5 | 94.1 | 27.9 |
| SWPP | seasonal_naive | 78.1 | 25.5 | 94.4 | 43.3 |
| SWPP | seasonal_naive+cqr | 79.6 | 27.5 | 94.1 | 45.2 |
| TVA | lgbm_global | 67.7 | 11.0 | 86.1 | 18.4 |
| TVA | lgbm_global+cqr | 79.4 | 15.5 | 93.3 | 29.3 |
| TVA | ridge | 78.6 | 20.4 | 92.6 | 33.9 |
| TVA | ridge+cqr | 79.3 | 23.0 | 92.8 | 39.7 |
| TVA | seasonal_naive | 79.8 | 36.0 | 94.8 | 65.8 |
| TVA | seasonal_naive+cqr | 78.9 | 38.4 | 93.4 | 62.3 |

## Daily peak

| BA | model | days | peak APE (%) | peak hour off by >1 h (%) |
|---|---|---|---|---|
| CISO | lgbm_global | 366 | 2.90 | 4.4 |
| CISO | lgbm_global+cqr | 366 | 2.90 | 4.4 |
| CISO | operator | 366 | 1.78 | 7.4 |
| CISO | operator_debiased | 366 | 1.87 | 4.6 |
| CISO | ridge | 366 | 3.72 | 2.5 |
| CISO | ridge+cqr | 366 | 3.72 | 2.5 |
| CISO | seasonal_naive | 366 | 6.85 | 10.4 |
| CISO | seasonal_naive+cqr | 366 | 6.85 | 10.4 |
| ERCO | lgbm_global | 366 | 4.42 | 22.1 |
| ERCO | lgbm_global+cqr | 366 | 4.42 | 22.1 |
| ERCO | operator | 366 | 2.52 | 15.3 |
| ERCO | operator_debiased | 366 | 2.43 | 14.8 |
| ERCO | ridge | 366 | 5.05 | 26.5 |
| ERCO | ridge+cqr | 366 | 5.05 | 26.5 |
| ERCO | seasonal_naive | 366 | 8.58 | 34.7 |
| ERCO | seasonal_naive+cqr | 366 | 8.58 | 34.7 |
| FPL | lgbm_global | 356 | 5.11 | 27.0 |
| FPL | lgbm_global+cqr | 356 | 5.11 | 27.0 |
| FPL | operator | 356 | 2.76 | 20.5 |
| FPL | operator_debiased | 356 | 2.71 | 16.9 |
| FPL | ridge | 356 | 5.93 | 20.8 |
| FPL | ridge+cqr | 356 | 5.93 | 20.8 |
| FPL | seasonal_naive | 356 | 9.18 | 35.4 |
| FPL | seasonal_naive+cqr | 356 | 9.18 | 35.4 |
| ISNE | lgbm_global | 366 | 4.30 | 7.9 |
| ISNE | lgbm_global+cqr | 366 | 4.30 | 7.9 |
| ISNE | operator | 366 | 1.48 | 2.5 |
| ISNE | operator_debiased | 366 | 1.46 | 3.6 |
| ISNE | ridge | 366 | 5.55 | 4.4 |
| ISNE | ridge+cqr | 366 | 5.55 | 4.4 |
| ISNE | seasonal_naive | 366 | 8.27 | 7.9 |
| ISNE | seasonal_naive+cqr | 366 | 8.27 | 7.9 |
| MISO | lgbm_global | 366 | 3.13 | 22.4 |
| MISO | lgbm_global+cqr | 366 | 3.13 | 22.4 |
| MISO | operator | 366 | 2.96 | 9.3 |
| MISO | operator_debiased | 366 | 1.82 | 9.8 |
| MISO | ridge | 366 | 4.05 | 31.4 |
| MISO | ridge+cqr | 366 | 4.05 | 31.4 |
| MISO | seasonal_naive | 366 | 7.64 | 32.0 |
| MISO | seasonal_naive+cqr | 366 | 7.64 | 32.0 |
| NYIS | lgbm_global | 365 | 4.00 | 11.2 |
| NYIS | lgbm_global+cqr | 365 | 4.00 | 11.2 |
| NYIS | operator | 365 | 2.69 | 5.8 |
| NYIS | operator_debiased | 365 | 1.75 | 5.5 |
| NYIS | ridge | 365 | 5.17 | 7.9 |
| NYIS | ridge+cqr | 365 | 5.17 | 7.9 |
| NYIS | seasonal_naive | 365 | 8.08 | 12.1 |
| NYIS | seasonal_naive+cqr | 365 | 8.08 | 12.1 |
| PJM | lgbm_global | 364 | 3.59 | 23.4 |
| PJM | lgbm_global+cqr | 364 | 3.59 | 23.4 |
| PJM | operator | 364 | 1.72 | 17.6 |
| PJM | operator_debiased | 364 | 1.89 | 11.3 |
| PJM | ridge | 364 | 5.23 | 28.6 |
| PJM | ridge+cqr | 364 | 5.23 | 28.6 |
| PJM | seasonal_naive | 364 | 9.73 | 37.6 |
| PJM | seasonal_naive+cqr | 364 | 9.73 | 37.6 |
| SOCO | lgbm_global | 366 | 4.85 | 20.5 |
| SOCO | lgbm_global+cqr | 366 | 4.85 | 20.5 |
| SOCO | operator | 366 | 0.77 | 3.8 |
| SOCO | operator_debiased | 366 | 0.65 | 4.4 |
| SOCO | ridge | 366 | 6.68 | 27.6 |
| SOCO | ridge+cqr | 366 | 6.68 | 27.6 |
| SOCO | seasonal_naive | 366 | 11.83 | 37.7 |
| SOCO | seasonal_naive+cqr | 366 | 11.83 | 37.7 |
| SWPP | lgbm_global | 366 | 4.48 | 28.1 |
| SWPP | lgbm_global+cqr | 366 | 4.48 | 28.1 |
| SWPP | operator | 366 | 3.03 | 15.8 |
| SWPP | operator_debiased | 366 | 3.01 | 17.5 |
| SWPP | ridge | 366 | 5.40 | 32.5 |
| SWPP | ridge+cqr | 366 | 5.40 | 32.5 |
| SWPP | seasonal_naive | 366 | 9.54 | 37.2 |
| SWPP | seasonal_naive+cqr | 366 | 9.54 | 37.2 |
| TVA | lgbm_global | 366 | 5.08 | 25.4 |
| TVA | lgbm_global+cqr | 366 | 5.08 | 25.4 |
| TVA | operator | 366 | 2.53 | 12.8 |
| TVA | operator_debiased | 366 | 2.67 | 13.7 |
| TVA | ridge | 366 | 7.03 | 30.1 |
| TVA | ridge+cqr | 366 | 7.03 | 30.1 |
| TVA | seasonal_naive | 366 | 12.52 | 45.6 |
| TVA | seasonal_naive+cqr | 366 | 12.52 | 45.6 |

## Slices (MAPE %, pooled over BAs)

| slice | value | operator_debiased | lgbm_global+cqr | ridge+cqr | seasonal_naive+cqr |
|---|---|---|---|---|---|
| day_type | holiday | 2.22 | 5.64 | 7.43 | 10.91 |
| day_type | weekday | 1.97 | 4.16 | 5.39 | 8.49 |
| day_type | weekend | 2.25 | 4.13 | 5.75 | 8.71 |
| hour_block | 00 | 1.80 | 3.53 | 4.99 | 8.21 |
| hour_block | 06 | 1.98 | 4.17 | 5.85 | 8.33 |
| hour_block | 12 | 2.49 | 5.04 | 6.03 | 9.77 |
| hour_block | 18 | 1.96 | 4.06 | 5.37 | 8.22 |
| season | autumn | 1.87 | 3.49 | 5.09 | 8.92 |
| season | spring | 2.07 | 3.58 | 4.67 | 7.20 |
| season | summer | 2.14 | 4.21 | 5.91 | 8.70 |
| season | winter | 2.16 | 5.53 | 6.58 | 9.73 |
| temperature | cold 5% | 2.32 | 5.70 | 7.19 | 10.90 |
| temperature | hot 5% | 2.00 | 3.84 | 4.96 | 10.89 |
| temperature | no weather | 2.48 | 8.19 | 8.64 | 10.39 |
| temperature | normal | 2.02 | 3.86 | 5.29 | 8.25 |

## Compute

* `operator`: 0 s fit+predict over 15 refits
* `operator_debiased`: 0 s fit+predict over 15 refits
* `seasonal_naive`: 0 s fit+predict over 15 refits
* `ridge`: 7 s fit+predict over 15 refits
* `lgbm_global`: 441 s fit+predict over 15 refits
