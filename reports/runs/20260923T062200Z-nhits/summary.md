> **SUPERSEDED** - N-HiTS predictions exploded on 2024-01-20/21 after a 3-week weather-archive gap (forward-filled constant inputs + robust scaler). Fixed in nhits-v2; kept as evidence.

# Run 20260923T062200Z-nhits — validation split

Target days 2023-07-01 → 2024-06-30; training from 2021-08-01, expanding, refit monthly (15 refits). Protocol `realtime`: issued 10:00 local D-1 with demand to 06:00 on D-1; weather = GFS forecasts made 48 h ahead. Leakage check: 5,313,115 feature values over 10,650 forecast origins, 0 violations.

## MAPE (%) by BA

| BA | hours | operator | operator_debiased | nhits |
|---|---|---|---|---|
| CISO | 8,782 | 6.27 | 2.67 | **7770.82** |
| ERCO | 8,784 | 2.42 | 2.38 | **24590.06** |
| FPL | 8,578 | 3.22 | 2.19 | **6.98** |
| ISNE | 8,784 | 2.49 | 1.90 | **7.06** |
| MISO | 8,784 | 3.11 | 1.75 | **86803.16** |
| NYIS | 8,760 | 2.63 | 1.74 | **112560.45** |
| PJM | 8,736 | 3.59 | 2.06 | **127643.99** |
| SOCO | 8,783 | 1.91 | 0.95 | **28328.60** |
| SWPP | 8,784 | 2.56 | 2.58 | **43314.08** |
| TVA | 8,784 | 2.38 | 2.40 | **42914.04** |

Bold = best of our models. Operator columns are benchmarks, not our models.

## Skill vs `operator` (1 - MAE/MAE_ref), 95 % block-bootstrap CI, DM p-value

| BA | model | days | skill | 95 % CI | DM p | note |
|---|---|---|---|---|---|---|
| CISO | nhits | 366 | -1160.664 | [-3678.315, +0.244] | 0.322 | operator series has a growing midday bias (data_profile 5.1) |
| ERCO | nhits | 366 | -12067.649 | [-40215.395, -0.924] | 0.322 |  |
| FPL | nhits | 359 | -1.160 | [-1.364, -1.023] | 2.91e-42 |  |
| ISNE | nhits | 366 | -2.009 | [-2.260, -1.738] | 1.47e-41 |  |
| MISO | nhits | 366 | -33171.904 | [-119743.009, -0.076] | 0.307 |  |
| NYIS | nhits | 366 | -47690.678 | [-150481.637, -0.759] | 0.31 |  |
| PJM | nhits | 364 | -44508.628 | [-148070.476, -0.220] | 0.307 |  |
| SOCO | nhits | 366 | -22343.792 | [-71015.959, -2.015] | 0.322 |  |
| SWPP | nhits | 366 | -18650.077 | [-64854.748, -0.493] | 0.322 | operator series changes definition in 2025-05 (data_profile 5.2) |
| TVA | nhits | 366 | -28388.352 | [-93968.276, -1.380] | 0.322 |  |

## Skill vs `operator_debiased` (1 - MAE/MAE_ref), 95 % block-bootstrap CI, DM p-value

| BA | model | days | skill | 95 % CI | DM p | note |
|---|---|---|---|---|---|---|
| CISO | nhits | 366 | -2674.321 | [-8365.953, -0.792] | 0.322 |  |
| ERCO | nhits | 366 | -12352.512 | [-38337.536, -0.986] | 0.322 |  |
| FPL | nhits | 359 | -2.096 | [-2.413, -1.885] | 1.49e-63 |  |
| ISNE | nhits | 366 | -2.835 | [-3.176, -2.484] | 2.73e-48 |  |
| MISO | nhits | 366 | -57766.537 | [-177515.789, -0.925] | 0.307 |  |
| NYIS | nhits | 366 | -71489.171 | [-231757.948, -1.656] | 0.31 |  |
| PJM | nhits | 364 | -77297.330 | [-262244.577, -1.107] | 0.307 |  |
| SOCO | nhits | 366 | -43860.110 | [-142035.118, -4.840] | 0.322 |  |
| SWPP | nhits | 366 | -18818.249 | [-60220.257, -0.513] | 0.322 |  |
| TVA | nhits | 366 | -27922.148 | [-106409.942, -1.319] | 0.322 |  |

## Prediction intervals (nominal 80 % and 95 %)

| BA | model | coverage 80 | width 80 (%) | coverage 95 | width 95 (%) |
|---|---|---|---|---|---|
| CISO | nhits | 77.5 | 17148.1 | 93.4 | 29207.0 |
| CISO | nhits+cqr | 79.1 | 17148.6 | 95.1 | 29209.0 |
| ERCO | nhits | 72.5 | 60568.3 | 92.1 | 103903.5 |
| ERCO | nhits+cqr | 78.4 | 60570.2 | 94.9 | 103907.2 |
| FPL | nhits | 76.7 | 22.7 | 94.6 | 43.1 |
| FPL | nhits+cqr | 79.9 | 24.4 | 95.0 | 44.1 |
| ISNE | nhits | 72.8 | 19.8 | 91.2 | 36.1 |
| ISNE | nhits+cqr | 78.1 | 22.3 | 94.0 | 40.0 |
| MISO | nhits | 81.6 | 186674.2 | 96.1 | 317265.5 |
| MISO | nhits+cqr | 79.1 | 186674.0 | 95.1 | 317264.3 |
| NYIS | nhits | 77.0 | 234438.6 | 94.4 | 398743.4 |
| NYIS | nhits+cqr | 78.5 | 234439.4 | 94.2 | 398743.3 |
| PJM | nhits | 75.3 | 270641.8 | 92.6 | 459910.3 |
| PJM | nhits+cqr | 78.7 | 270643.3 | 94.4 | 459912.6 |
| SOCO | nhits | 77.5 | 63763.8 | 94.7 | 110067.0 |
| SOCO | nhits+cqr | 80.1 | 63765.3 | 95.2 | 110068.5 |
| SWPP | nhits | 77.8 | 104134.0 | 93.1 | 178140.0 |
| SWPP | nhits+cqr | 79.0 | 104134.8 | 95.9 | 178143.0 |
| TVA | nhits | 75.9 | 97303.9 | 92.3 | 167452.9 |
| TVA | nhits+cqr | 79.2 | 97306.7 | 94.5 | 167457.1 |

## Daily peak

| BA | model | days | peak APE (%) | peak hour off by >1 h (%) |
|---|---|---|---|---|
| CISO | nhits | 366 | 10769.12 | 8.7 |
| CISO | operator | 366 | 1.78 | 7.4 |
| CISO | operator_debiased | 366 | 1.87 | 4.6 |
| ERCO | nhits | 366 | 36487.17 | 28.7 |
| ERCO | operator | 366 | 2.52 | 15.3 |
| ERCO | operator_debiased | 366 | 2.43 | 14.8 |
| FPL | nhits | 357 | 7.55 | 33.3 |
| FPL | operator | 357 | 2.76 | 20.4 |
| FPL | operator_debiased | 357 | 2.70 | 17.1 |
| ISNE | nhits | 366 | 6.26 | 24.6 |
| ISNE | operator | 366 | 1.48 | 2.5 |
| ISNE | operator_debiased | 366 | 1.46 | 3.6 |
| MISO | nhits | 366 | 124482.68 | 27.9 |
| MISO | operator | 366 | 2.96 | 9.3 |
| MISO | operator_debiased | 366 | 1.82 | 9.8 |
| NYIS | nhits | 365 | 149056.12 | 24.1 |
| NYIS | operator | 365 | 2.69 | 5.8 |
| NYIS | operator_debiased | 365 | 1.75 | 5.5 |
| PJM | nhits | 364 | 182982.33 | 21.4 |
| PJM | operator | 364 | 1.72 | 17.6 |
| PJM | operator_debiased | 364 | 1.89 | 11.3 |
| SOCO | nhits | 366 | 41104.13 | 27.9 |
| SOCO | operator | 366 | 0.77 | 3.8 |
| SOCO | operator_debiased | 366 | 0.65 | 4.4 |
| SWPP | nhits | 366 | 63676.76 | 30.9 |
| SWPP | operator | 366 | 3.03 | 15.8 |
| SWPP | operator_debiased | 366 | 3.01 | 17.5 |
| TVA | nhits | 366 | 63798.64 | 33.6 |
| TVA | operator | 366 | 2.53 | 12.8 |
| TVA | operator_debiased | 366 | 2.67 | 13.7 |

## Slices (MAPE %, pooled over BAs)

| slice | value | operator_debiased | nhits |
|---|---|---|---|
| day_type | holiday | 2.23 | 7.27 |
| day_type | weekday | 1.97 | 5.26 |
| day_type | weekend | 2.25 | 165334.92 |
| hour_block | 00 | 1.80 | 42059.84 |
| hour_block | 06 | 1.98 | 62385.65 |
| hour_block | 12 | 2.49 | 44990.82 |
| hour_block | 18 | 1.97 | 40338.18 |
| season | autumn | 1.87 | 4.76 |
| season | spring | 2.07 | 5.37 |
| season | summer | 2.14 | 5.41 |
| season | winter | 2.16 | 190212.84 |
| temperature | cold 5% | 2.32 | 951238.87 |
| temperature | hot 5% | 2.00 | 4.89 |
| temperature | no weather | 2.48 | 6.93 |
| temperature | normal | 2.02 | 927.67 |

## Compute

* `operator`: 0 s fit+predict over 15 refits
* `operator_debiased`: 0 s fit+predict over 15 refits
* `nhits`: 4706 s fit+predict over 15 refits
