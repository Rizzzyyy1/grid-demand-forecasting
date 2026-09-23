"""The scheduled daily run (GitHub Actions): refresh recent data, forecast, score, report status.

Stages run in order and each is timed and logged; ``status/latest.json`` is written whatever
happens, so the public dashboard can show when the last run succeeded or what failed.

* ``eia``      - only the six-month files that cover recent days (tens of MB, not the archive);
* ``weather``  - only recent months; a provider quota refusal is a *warning* (issuance continues
                 with the forecasts already on disk, and the missing values are visible);
* ``build``    - ``dbt build`` including every data test (a failing test stops the run);
* ``forecast`` - the verified model artefact forecasts tomorrow (Eastern) for every BA; if that
                 day is already stored the stage is a no-op, so retries are idempotent;
* ``score``    - live scores against published actuals, restricted to days after the locked
                 test window, written as small CSVs.

Critical stages (``build``, ``forecast``) make the run fail after the status file is written.
Nothing here can train, tune or evaluate the test split: the run requires live mode, in which
those actions raise (``gridcast.core.settings.ensure_offline``).
"""

from __future__ import annotations

import json
import os
import subprocess
import time
import traceback
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import structlog

from gridcast.core.regions import all_regions
from gridcast.core.settings import Settings
from gridcast.core.time import utc_now

log = structlog.get_logger(__name__)
CRITICAL = frozenset({"build", "forecast"})
WEATHER_LOOKBACK_DAYS = 40  # features need 21 days; one extra month of margin
EIA_MIN_LOOKBACK_DAYS = 45


class LiveRunError(RuntimeError):
    """A critical stage failed (the status file still records what happened)."""


@dataclass
class StageResult:
    """Outcome of one stage."""

    name: str
    ok: bool
    seconds: float
    detail: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


@dataclass
class DailyStatus:
    """What ``status/latest.json`` records."""

    started_at: str
    finished_at: str | None = None
    ok: bool = False
    code_version: str = "unknown"
    model_version: str | None = None
    target_day: str | None = None
    stages: list[StageResult] = field(default_factory=list)


def code_version() -> str:
    """The commit being run (``GITHUB_SHA`` in Actions, else ``git rev-parse``)."""
    if sha := os.environ.get("GITHUB_SHA"):
        return sha[:12]
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short=12", "HEAD"],  # noqa: S607 - fixed command
            capture_output=True,
            text=True,
            check=False,
        )
        return out.stdout.strip() or "unknown"
    except OSError:
        return "unknown"


def _stage(status: DailyStatus, name: str, fn: Callable[[], dict[str, Any]]) -> bool:
    started = time.perf_counter()
    log.info("live.stage.start", stage=name)
    try:
        detail = fn()
        result = StageResult(name, True, time.perf_counter() - started, detail)
    except Exception as exc:
        result = StageResult(
            name,
            False,
            time.perf_counter() - started,
            error=f"{type(exc).__name__}: {exc}",
            detail={"traceback": traceback.format_exc(limit=6)},
        )
        log.error("live.stage.failed", stage=name, error=result.error)
    else:
        log.info("live.stage.done", stage=name, seconds=round(result.seconds, 1), **detail)
    status.stages.append(result)
    return result.ok


def _write_status(root: Path, status: DailyStatus) -> Path:
    out = root / "status"
    out.mkdir(parents=True, exist_ok=True)
    body = {
        **{k: v for k, v in status.__dict__.items() if k != "stages"},
        "stages": [s.__dict__ for s in status.stages],
    }
    path = out / "latest.json"
    path.write_text(json.dumps(body, indent=2, default=str) + "\n")
    return path


def run_daily(settings: Settings, now: datetime | None = None) -> DailyStatus:  # noqa: PLR0915
    """Run every stage; raises ``LiveRunError`` after writing status if a critical stage failed."""
    from gridcast.ingestion.eia.bulk import EiaBulkDownloader  # noqa: PLC0415
    from gridcast.ingestion.http import make_client  # noqa: PLC0415
    from gridcast.ingestion.weather.open_meteo import (  # noqa: PLC0415
        OpenMeteoDownloader,
        WeatherKind,
    )
    from gridcast.live.artifact import load_artifact  # noqa: PLC0415
    from gridcast.live.issue import (  # noqa: PLC0415
        default_target_day,
        issue_forecasts,
        live_daily_scores,
        live_scores,
    )
    from gridcast.live.store import ParquetForecastStore  # noqa: PLC0415
    from gridcast.warehouse.dbt import run_dbt_subprocess  # noqa: PLC0415

    if not settings.live_mode:
        raise LiveRunError("run_daily requires live mode (GRIDCAST_LIVE_MODE=1)")
    now = now or utc_now()
    today = now.date()
    root = settings.live_root
    store = ParquetForecastStore(root / "forecasts")
    status = DailyStatus(started_at=now.isoformat(), code_version=code_version())
    target = default_target_day(now)
    status.target_day = str(target)

    stored = store.read()
    first_day = stored["target_day"].min() if stored.height else None
    since = today - timedelta(days=EIA_MIN_LOOKBACK_DAYS)
    if isinstance(first_day, date):
        since = min(since, first_day - timedelta(days=30))

    def eia() -> dict[str, Any]:
        with make_client(settings.http_timeout_s) as client:
            r = EiaBulkDownloader(client, settings.raw_dir / "eia").sync(
                settings.eia_start_year, today, since=since
            )
        return {
            "files_checked": r.files_checked,
            "downloaded": len(r.downloaded),
            "since": str(since),
        }

    def weather() -> dict[str, Any]:
        start = today - timedelta(days=WEATHER_LOOKBACK_DAYS)
        with make_client(settings.http_timeout_s) as client:
            r = OpenMeteoDownloader(client, settings.raw_dir / "weather").sync(
                WeatherKind.FORECAST_D2, all_regions(), start, today
            )
        return {
            "downloaded": r.downloaded,
            "skipped": r.skipped,
            "quota_stop": r.stopped_for_quota,
            "remaining": r.remaining,
        }

    def build() -> dict[str, Any]:
        r = run_dbt_subprocess(settings, ["build"])
        if not r.success:
            raise RuntimeError("dbt build failed: " + "; ".join(r.messages[:5]))
        return {"passed": r.passed, "failed": r.failed}

    def forecast() -> dict[str, Any]:
        model, manifest = load_artifact(root / "model")
        status.model_version = manifest.version
        r = issue_forecasts(
            settings,
            target,
            now,
            sink=store,
            model=model,
            model_version=manifest.version,
            code_version=status.code_version,
            skip_existing=True,
        )
        return {
            "target_day": str(r.target_day),
            "rows": r.rows,
            "late_rows": r.late_rows,
            "null_forecasts": r.null_forecasts,
            "skipped_existing": r.skipped_existing,
            "leak_checked_cells": r.cells_checked,
        }

    def scores() -> dict[str, Any]:
        rows = store.read()
        out = root / "scores"
        out.mkdir(parents=True, exist_ok=True)
        board = live_scores(settings, rows)
        daily = live_daily_scores(settings, rows)
        for name, frame in (("leaderboard.csv", board), ("daily.csv", daily)):
            path = out / name
            if frame.height:
                frame.sort(frame.columns[:3]).write_csv(path, float_precision=4)
            elif not path.exists():
                path.write_text("")
        return {
            "leaderboard_rows": board.height,
            "daily_rows": daily.height,
            "forecast_rows": rows.height,
        }

    ok = True
    for name, fn in (
        ("eia", eia),
        ("weather", weather),
        ("build", build),
        ("forecast", forecast),
        ("score", scores),
    ):
        stage_ok = _stage(status, name, fn)
        if not stage_ok and name in CRITICAL:
            ok = False
            if name == "build":  # nothing downstream can be trusted
                break
    status.ok = ok
    status.finished_at = utc_now().isoformat()
    path = _write_status(root, status)
    log.info("live.status", ok=ok, path=str(path))
    if not ok:
        failed = [s.name for s in status.stages if not s.ok]
        raise LiveRunError(f"critical stage failed: {failed}")
    return status


def summary_markdown(status: DailyStatus) -> str:
    """A short table for ``$GITHUB_STEP_SUMMARY``."""
    lines = [
        f"### GridCast daily run - {'✅ ok' if status.ok else '❌ failed'}",
        "",
        f"target day `{status.target_day}` · model `v{status.model_version}` · code "
        f"`{status.code_version}`",
        "",
        "| stage | ok | seconds | detail |",
        "|---|---|---|---|",
    ]
    for s in status.stages:
        detail = s.error or ", ".join(f"{k}={v}" for k, v in s.detail.items())
        lines.append(f"| {s.name} | {'✅' if s.ok else '❌'} | {s.seconds:.1f} | {detail} |")
    return "\n".join(lines) + "\n"


def load_status(root: Path) -> dict[str, Any] | None:
    """The last written status, if any."""
    path = root / "status" / "latest.json"
    return json.loads(path.read_text()) if path.exists() else None
