# Ablations 20260923T132504Z

Validation target days 2023-07-01 → 2024-06-30. Each arm is global LightGBM with one change; skill = 1 - MAE_arm / MAE_baseline on paired days (positive = the change helps), 95 % moving-block bootstrap CI, Diebold-Mariano p.

| variant | change | MAPE % | fit s |
|---|---|---|---|
| baseline | global LightGBM, population-weighted weather, realtime protocol | 3.883 | 649 |
| unweighted_weather | plain mean over cities | 3.778 | 644 |
| per_ba_models | one LightGBM per BA instead of one global | 4.013 | 3337 |
| short_history | training from 2022-07-01 instead of 2021-04-01 | 4.002 | 732 |
| bulk_latency | demand only to the end of D-3 (keyless live feed) | 4.495 | 558 |

## Pooled over all BAs

| variant | skill vs baseline | 95 % CI | DM p |
|---|---|---|---|
| unweighted_weather | +0.0315 | [+0.0157, +0.0459] | 0.00016 |
| per_ba_models | -0.0419 | [-0.0680, -0.0096] | 0.0075 |
| short_history | -0.0327 | [-0.0572, -0.0109] | 0.0017 |
| bulk_latency | -0.1649 | [-0.2164, -0.1234] | 5.9e-08 |

## Per BA

| variant | BA | skill | 95 % CI | DM p |
|---|---|---|---|---|
| bulk_latency | CISO | -0.1185 | [-0.1740, -0.0689] | 1.2e-05 |
| bulk_latency | ERCO | -0.1634 | [-0.2244, -0.1067] | 1.2e-06 |
| bulk_latency | FPL | -0.1156 | [-0.1874, -0.0558] | 0.00055 |
| bulk_latency | ISNE | -0.1360 | [-0.1914, -0.0761] | 1.6e-05 |
| bulk_latency | MISO | -0.1691 | [-0.2516, -0.0997] | 0.00027 |
| bulk_latency | NYIS | -0.1636 | [-0.2397, -0.0967] | 9.4e-05 |
| bulk_latency | PJM | -0.1978 | [-0.3003, -0.1102] | 0.00014 |
| bulk_latency | SOCO | -0.1000 | [-0.1966, -0.0139] | 0.015 |
| bulk_latency | SWPP | -0.2286 | [-0.3065, -0.1623] | 4.7e-06 |
| bulk_latency | TVA | -0.1631 | [-0.2391, -0.0956] | 0.00063 |
| per_ba_models | CISO | +0.0424 | [-0.0121, +0.0937] | 0.11 |
| per_ba_models | ERCO | -0.0364 | [-0.0838, +0.0151] | 0.16 |
| per_ba_models | FPL | -0.0104 | [-0.0453, +0.0273] | 0.62 |
| per_ba_models | ISNE | -0.0245 | [-0.0598, +0.0149] | 0.24 |
| per_ba_models | MISO | -0.0569 | [-0.1173, -0.0017] | 0.07 |
| per_ba_models | NYIS | -0.0633 | [-0.1154, -0.0072] | 0.023 |
| per_ba_models | PJM | -0.0179 | [-0.0905, +0.0504] | 0.66 |
| per_ba_models | SOCO | -0.0691 | [-0.1482, +0.0008] | 0.097 |
| per_ba_models | SWPP | -0.1276 | [-0.1897, -0.0578] | 0.00066 |
| per_ba_models | TVA | -0.0535 | [-0.1073, -0.0042] | 0.077 |
| short_history | CISO | +0.0221 | [-0.0189, +0.0531] | 0.25 |
| short_history | ERCO | -0.0136 | [-0.0556, +0.0290] | 0.52 |
| short_history | FPL | -0.0343 | [-0.0729, +0.0042] | 0.081 |
| short_history | ISNE | -0.0377 | [-0.0641, -0.0099] | 0.0046 |
| short_history | MISO | -0.0379 | [-0.0843, -0.0018] | 0.068 |
| short_history | NYIS | -0.0695 | [-0.1082, -0.0371] | 0.00045 |
| short_history | PJM | -0.0521 | [-0.1022, -0.0039] | 0.023 |
| short_history | SOCO | -0.0278 | [-0.0666, -0.0010] | 0.068 |
| short_history | SWPP | -0.0219 | [-0.0539, +0.0096] | 0.17 |
| short_history | TVA | -0.0452 | [-0.0787, -0.0199] | 0.00069 |
| unweighted_weather | CISO | +0.0637 | [+0.0260, +0.0964] | 0.002 |
| unweighted_weather | ERCO | -0.0017 | [-0.0353, +0.0298] | 0.92 |
| unweighted_weather | FPL | +0.0420 | [-0.0001, +0.0886] | 0.075 |
| unweighted_weather | ISNE | +0.0168 | [+0.0007, +0.0345] | 0.071 |
| unweighted_weather | MISO | +0.0359 | [+0.0046, +0.0600] | 0.021 |
| unweighted_weather | NYIS | +0.0539 | [-0.0078, +0.1071] | 0.087 |
| unweighted_weather | PJM | +0.0587 | [+0.0303, +0.0908] | 0.00046 |
| unweighted_weather | SOCO | +0.0107 | [-0.0139, +0.0369] | 0.42 |
| unweighted_weather | SWPP | +0.0185 | [-0.0023, +0.0385] | 0.098 |
| unweighted_weather | TVA | +0.0128 | [-0.0083, +0.0320] | 0.22 |
