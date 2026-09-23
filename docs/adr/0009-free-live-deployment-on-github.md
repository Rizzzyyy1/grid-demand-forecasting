# ADR-0009: Run the live loop on GitHub Actions + GitHub Pages (zero cost)

Status: Accepted · 2026-09-23

## Context
The project must run live at no cost, now or later. ADR-0008's single AWS host is validated but
would bill once any credits end. The repository is public, and GitHub Actions and Pages are free
for public repositories.

## Decision
* **A scheduled workflow** (`.github/workflows/live.yml`, 12:30 UTC with a 13:45 retry) runs
  `gridcast daily` in **live mode**. It downloads only recent EIA files and recent weather months,
  runs `dbt build` with every data test, issues tomorrow's forecasts with the frozen model
  artefact, scores past days, and writes a stage-by-stage status file.
* **Outputs go to a separate `live-data` branch**, never to `main`:
  * one immutable Parquet file per target day;
  * small score CSVs;
  * the status JSON;
  * the model manifest.
  `scripts/verify_live_commit.py` refuses any commit that modifies or deletes an issued forecast,
  touches another path, or adds a file over 1 MB.
* **The model file is a GitHub Release asset** (`model-v<N>`). The job downloads it, checks its
  sha256 against the manifest, and `load_artifact` refuses a model whose feature list, protocol or
  weather configuration differs from the code.
* **The dashboard is a static page** (`gridcast site`) generated from those files and deployed
  to GitHub Pages on every run, including failed ones, so the page shows the failure.

## Safeguards against misuse of the test split
* `GRIDCAST_LIVE_MODE=1` makes these refuse:
  * training;
  * backtests on any split, even with the confirmation flag;
  * rescoring;
  * combining runs;
  * ablations;
  * model export.

  They raise `LiveModeError` in the library functions, not just the CLI.
* Live scores only cover target days **after** the locked test window (2026-06-30), so the live
  record can never become a repeated test evaluation.
* The job fails if anything tracked on `main` changed during the run.

## Consequences
* Retraining is a deliberate local act: `gridcast train`, then `gridcast export-model`, then a new
  release and manifest.
* GitHub disables scheduled workflows after 60 days without repository activity. The daily
  commits to `live-data` count as activity; if the schedule is ever disabled, re-enable it in the
  Actions tab.
* Shared runner IPs can exhaust Open-Meteo's free quota. That is a warning, not a failure: the
  forecast is still issued, and missing weather is visible in the status.
