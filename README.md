# live-data

Output branch of the scheduled GridCast job (`.github/workflows/live.yml` on `main`).
Nothing here is edited by hand except `model/manifest.json`, which changes only when a new
model is exported and released.

| Path | What | Mutability |
|---|---|---|
| `forecasts/target=YYYY-MM-DD/lgbm_live.parquet` | every issued forecast (24 hours x 10 BAs, intervals, issue/creation time, model and code version) | **append-only** - a commit that modifies or deletes one is refused |
| `scores/leaderboard.csv`, `scores/daily.csv` | live accuracy vs the operator, days after the locked test window only | rewritten daily |
| `status/latest.json` | outcome of the last run, stage by stage | rewritten daily |
| `model/manifest.json` | the served model: version, sha256, training window, features | changed only by a model release |

The model file itself is attached to the GitHub Release `model-v<version>`; the job downloads it
and refuses to run unless its sha256 matches the manifest.
