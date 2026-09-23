# GridCast — working notes for Claude Code

Day-ahead electricity-demand forecasting for 10 US balancing authorities, benchmarked against the
operators' own forecasts (EIA-930). Read `docs/DESIGN.md` first; `docs/ROADMAP.md` gives the phase.

## Rules that matter
* **No leakage.** Every feature has `available_at <= issued_at`; the protocol is DESIGN §3 / ADR-0001.
  Weather features use Open-Meteo `previous_day2` only. The operator forecast is never a feature.
* **Never invent results.** README/docs numbers come from `reports/runs/*/`; `—` until a real run exists.
* **The test period (2024-07-01 → 2026-06-30) is evaluated once**, after models are frozen.
* **All time conversion goes through `core/time.py`** (DST days have 23/25 hours).
* Everything external (HTTP) is behind a `Protocol` with a fake; unit tests are hermetic.
* A check that passes must say how much it checked.
* Never state a finding you have not read off real output.

## Commands
```bash
make install / make check        # uv sync --all-extras + hooks / ruff + mypy --strict + arch + tests (== CI)
make test-all                    # + slow tests (real dbt build on fixtures, N-HiTS)
uv run gridcast ingest eia|weather ; gridcast build ; gridcast profile
uv run gridcast backtest [--models a,b] [--tag x]   # validation split -> reports/runs/<id>/ + MLflow
uv run gridcast train ; gridcast forecast ; gridcast score ; gridcast drift   # local live loop
uv run gridcast export-model --out ../gridcast-live-data/model   # then release model-v<N>
GRIDCAST_LIVE_MODE=1 GRIDCAST_LIVE_DIR=../gridcast-live-data uv run gridcast daily   # = the scheduled job
uv run gridcast site --out site                   # static dashboard (GitHub Pages)
python scripts/collect_results.py --readme          # README numbers are generated, never typed
docker compose up --build        # api :8000, ui :8501, dagster :3000, mlflow :5001
```

## Lessons that cost time (do not repeat)
* **A constant publication lag is wrong across DST changes.** Availability of demand is
  `source hour + (issued_at - demand_cutoff)` per origin; the fixed-34 h version leaked by 1 h.
* **EIA's keyless bulk file lags ~1.5 days** (refreshed ~14:40 UTC with data to the previous
  local midnight). The live loop therefore uses the `bulk` protocol (ADR-0007).
* **Open-Meteo archives only GFS temperature before 2024-01-20**; other variables are null.
* **Joining every hour to every origin explodes** (N_hours x N_origins). Join on candidate days.
* **Polars `join(how="left")` does not promise order** - pass `maintain_order="left"` when rows
  are matched back positionally.
* **Dagster rejects string annotations** on `context`; `orchestration/definitions.py` omits the
  `__future__` import (the conventions test exempts it).
* **dbt run in-process holds the DuckDB file** until the process exits; open the warehouse with
  the same (read-write) config in that process, or use a subprocess.
* **dbt's partial-parse cache remembers the project path it was parsed with.** A manual
  `dbt build --project-dir transform` (relative) made Dagster's run look for
  `transform/seeds/...` inside `transform/`. Always pass absolute paths (the `gridcast` CLI does);
  if in doubt `rm -rf transform/target`.
* **Use `uv add --no-sync` while long runs are going**: `uv add` re-syncs `.venv` under the
  running processes (it happened to be harmless once; do not rely on that).
* **In a long-lived process, run dbt as a subprocess** (`run_dbt_subprocess`) if the warehouse is
  read afterwards: in-process dbt keeps its read-write DuckDB handle and later read-only opens fail.
  The first local `gridcast daily` failed exactly this way.
* Host port 5000 is taken by macOS AirPlay; MLflow is published on 5001.
* LightGBM on macOS needs `brew install libomp`.
* **LightGBM then PyTorch in one process deadlocks on macOS** (two OpenMP runtimes; PyTorch's
  parallel copy waits forever at 0 % CPU). `NHiTSForecaster` pins `torch.set_num_threads(1)`.
  Diagnose a 0 %-CPU hang with `sample <pid>`, not by waiting.
* Drift reports need a seasonally matched reference (same dates a year earlier) or every weather
  feature "drifts".

## Conventions
* Python 3.13, `uv`, `from __future__ import annotations`, strict typing, Ruff line length 100.
* New module → docstring stating its responsibility. New decision → ADR in `docs/adr/`.
* Tests mirror the package under `tests/unit/`; mark costly ones `network` / `slow`.
* Docker CLI lives at `/Applications/Docker.app/Contents/Resources/bin` (also `~/.docker/bin`).
