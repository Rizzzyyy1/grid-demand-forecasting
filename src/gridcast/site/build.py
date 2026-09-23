"""Render the public dashboard as one self-contained ``index.html`` (plus a JSON copy of its data).

Inputs are files only - the live store, live scores, the daily status and the latest validation
run - so the page can be rebuilt anywhere and always shows exactly what those files say. Every
number on the page comes from them; nothing is typed into the template.
"""

from __future__ import annotations

import html
import json
from datetime import date
from importlib import resources
from pathlib import Path
from typing import Any

import polars as pl

from gridcast import __version__
from gridcast.core.regions import all_regions
from gridcast.live.daily import load_status
from gridcast.live.store import ParquetForecastStore

REPO_URL = "https://github.com/Rizzzyyy1/grid-demand-forecasting"
PLOTLY = "https://cdn.jsdelivr.net/npm/plotly.js-dist-min@2.35.2/plotly.min.js"


def _latest_validation_run(reports: Path) -> Path | None:
    candidates = []
    for cfg in (reports / "runs").glob("*/config.json"):
        c = json.loads(cfg.read_text())
        if (
            c.get("split") == "validation"
            and not c.get("superseded")
            and not c["run_id"].endswith("smoke")
        ):
            candidates.append((len(c["models"]), c["run_id"], cfg.parent))
    return max(candidates)[2] if candidates else None


def _read_csv(path: Path) -> pl.DataFrame:
    return pl.read_csv(path) if path.exists() and path.stat().st_size else pl.DataFrame()


def collect(live_root: Path, reports: Path) -> dict[str, Any]:
    """Everything the page shows, as plain JSON-serialisable data."""
    forecasts = ParquetForecastStore(live_root / "forecasts").read()
    latest: dict[str, Any] = {}
    if forecasts.height:
        newest = forecasts.filter(pl.col("target_day") == pl.col("target_day").max())
        for (code,), group in newest.group_by("ba_code"):
            part = group.sort("hour_ending_utc")
            latest[str(code)] = {
                "target_day": str(part["target_day"][0]),
                "issued_at": part["issued_at"][0].isoformat(),
                "created_at": part["created_at"][0].isoformat(),
                "model_version": str(part["model_version"][0]),
                "late": bool(part["late"].any()),
                "t": [x.isoformat() for x in part["hour_ending_utc"]],
                **{
                    k: [None if v is None else round(v, 1) for v in part[k].to_list()]
                    for k in ("yhat", "q10", "q90", "q025", "q975")
                },
            }
    board = _read_csv(live_root / "scores" / "leaderboard.csv")
    daily = _read_csv(live_root / "scores" / "daily.csv")
    run = _latest_validation_run(reports)
    validation: dict[str, Any] = {}
    if run is not None:
        cfg = json.loads((run / "config.json").read_text())
        point = pl.read_csv(run / "metrics_point.csv").filter(
            ~pl.col("model").str.ends_with("+cqr")
        )
        validation = {
            "run_id": cfg["run_id"],
            "window": cfg["window"],
            "rows": point.select("ba_code", "model", "mape").to_dicts(),
            "overall": pl.read_csv(run / "metrics_overall.csv")
            .filter(~pl.col("model").str.ends_with("+cqr"))
            .select("model", "mape")
            .sort("mape")
            .to_dicts(),
        }
    return {
        "version": __version__,
        "status": load_status(live_root),
        "regions": [{"code": b.code, "name": b.name} for b in all_regions()],
        "latest": latest,
        "leaderboard": board.to_dicts() if board.height else [],
        "daily": daily.with_columns(pl.col("target_day").cast(pl.String)).to_dicts()
        if daily.height
        else [],
        "validation": validation,
        "forecast_days": forecasts["target_day"].n_unique() if forecasts.height else 0,
        "first_day": str(forecasts["target_day"].min()) if forecasts.height else None,
        "generated": date.today().isoformat(),  # noqa: DTZ011 - page build date, display only
    }


def _json_for_script(data: dict[str, Any]) -> str:
    return json.dumps(data, default=str).replace("</", "<\\/")


def render(data: dict[str, Any]) -> str:
    """The HTML page."""
    status = data.get("status") or {}
    ok = status.get("ok")
    badge = "ok" if ok else ("failed" if status else "no run yet")
    template = resources.files("gridcast.site").joinpath("template.html").read_text("utf-8")
    return (
        template.replace("__DATA__", _json_for_script(data))
        .replace("__PLOTLY__", PLOTLY)
        .replace("__REPO__", REPO_URL)
        .replace("__BADGE__", html.escape(badge))
        .replace("__BADGE_CLASS__", "ok" if ok else "bad")
    )


def build_site(live_root: Path, reports: Path, out: Path) -> Path:
    """Write ``out/index.html`` and ``out/data.json``; returns the page path."""
    data = collect(live_root, reports)
    out.mkdir(parents=True, exist_ok=True)
    (out / "data.json").write_text(json.dumps(data, indent=1, default=str))
    page = out / "index.html"
    page.write_text(render(data), encoding="utf-8")
    (out / ".nojekyll").write_text("")
    return page
