"""Open-Meteo weather for every configured city, one raw JSON file per (city, month).

Two kinds are fetched:

* ``forecast_d2`` - archived forecasts "predicted 48 hours before valid time" (``previous-runs``
  API, ``*_previous_day2``, GFS). The only weather the models may use (ADR-0001). GFS 2 m
  temperature is archived from 2021-03-25; the other variables only from 2024-01-20 (ADR-0004).
* ``observed`` - reanalysis "actuals" (archive API), used only for the perfect-weather ablation.

Open-Meteo's free tier counts a request covering more than 14 days as several calls and caps
calls per minute / hour / day. Requests are weighted accordingly and paced by a limiter seeded from
a persisted usage ledger, so separate processes share one budget. A 429 stops the run cleanly; the
next run resumes where it stopped because completed months are skipped via the manifest.
"""

from __future__ import annotations

import hashlib
import json
import math
import time
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from enum import StrEnum
from pathlib import Path

import httpx
import structlog

from gridcast.core.domain import BalancingAuthority, City
from gridcast.core.time import utc_now
from gridcast.ingestion.http import (
    QuotaExhaustedError,
    WeightedRateLimiter,
    raise_for_status,
    with_retries,
)
from gridcast.ingestion.manifest import Manifest, ManifestEntry, atomic_write_bytes

log = structlog.get_logger(__name__)

VARIABLES = (
    "temperature_2m",
    "dew_point_2m",
    "relative_humidity_2m",
    "cloud_cover",
    "wind_speed_10m",
    "shortwave_radiation",
)
FORECAST_MODEL = "gfs_seamless"  # the only model with archived day-2 temperature before 2024
# Free-tier limits with ~10 % headroom (https://open-meteo.com/en/terms).
DEFAULT_LIMITS: dict[float, float] = {60.0: 540.0, 3600.0: 4500.0, 86400.0: 9000.0}


class WeatherKind(StrEnum):
    """Which weather product a file holds."""

    FORECAST_D2 = "forecast_d2"
    OBSERVED = "observed"

    @property
    def endpoint(self) -> str:
        """API endpoint for this product."""
        if self is WeatherKind.FORECAST_D2:
            return "https://previous-runs-api.open-meteo.com/v1/forecast"
        return "https://archive-api.open-meteo.com/v1/archive"

    @property
    def variables(self) -> tuple[str, ...]:
        """Hourly variable names as the API expects them."""
        if self is WeatherKind.FORECAST_D2:
            return tuple(f"{v}_previous_day2" for v in VARIABLES)
        return VARIABLES

    @property
    def settle_days(self) -> int:
        """Days after which a month's data is final (reanalysis lags ~5 days)."""
        return 3 if self is WeatherKind.FORECAST_D2 else 8


def request_weight(days: int, n_variables: int) -> int:
    """Open-Meteo's call accounting: >14 days or >10 variables count as multiple calls."""
    return math.ceil(days / 14) * math.ceil(n_variables / 10)


@dataclass(frozen=True)
class MonthChunk:
    """One (BA, city, month) request."""

    kind: WeatherKind
    ba: str
    city: City
    start: date
    end: date
    closed: bool

    @property
    def key(self) -> str:
        """Manifest key and relative path stem."""
        return f"{self.kind}/{self.ba}/{self.city.slug}/{self.start:%Y-%m}"

    @property
    def days(self) -> int:
        """Days covered (inclusive)."""
        return (self.end - self.start).days + 1


def month_chunks(
    kind: WeatherKind, regions: tuple[BalancingAuthority, ...], start: date, today: date
) -> Iterator[MonthChunk]:
    """Chunks from ``start`` to the last available day, most recent month first per city.

    Newest-first means a quota stop still leaves the most useful (recent) data on disk.
    """
    # Day-2 forecasts for tomorrow already exist (predicted >= 48 h before each valid hour);
    # the live loop needs them. Reanalysis lags about 5 days.
    last_available = (
        today + timedelta(days=1)
        if kind is WeatherKind.FORECAST_D2
        else (today - timedelta(days=6))
    )
    months: list[date] = []
    cursor = date(start.year, start.month, 1)
    while cursor <= last_available:
        months.append(cursor)
        cursor = date(cursor.year + cursor.month // 12, cursor.month % 12 + 1, 1)
    for month in reversed(months):
        next_month = date(month.year + month.month // 12, month.month % 12 + 1, 1)
        month_end = next_month - timedelta(days=1)
        end = min(month_end, last_available)
        closed = end == month_end and month_end + timedelta(days=kind.settle_days) < today
        for ba in regions:
            for city in ba.cities:
                yield MonthChunk(kind, ba.code, city, max(month, start), end, closed)


@dataclass
class WeatherSyncReport:
    """What a weather sync did."""

    downloaded: int = 0
    skipped: int = 0
    refreshed_open: int = 0
    weight_spent: float = 0.0
    stopped_for_quota: bool = False
    remaining: int = 0
    empty_months: list[str] = field(default_factory=list)


class UsageLedger:
    """Persisted (timestamp, weight) log so the rate limiter survives process restarts."""

    def __init__(self, path: Path) -> None:
        """Ledger stored at ``path`` (JSON Lines)."""
        self.path = path

    def recent(self, within_s: float, now: float) -> list[tuple[float, float]]:
        """Events newer than ``within_s`` seconds."""
        if not self.path.exists():
            return []
        events = []
        for line in self.path.read_text("utf-8").splitlines():
            ts, weight = json.loads(line)
            if ts > now - within_s:
                events.append((float(ts), float(weight)))
        return events

    def append(self, ts: float, weight: float) -> None:
        """Record one request."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps([ts, weight]) + "\n")


class OpenMeteoDownloader:
    """Fetches month chunks into ``raw_dir`` (``data/raw/weather``)."""

    def __init__(
        self,
        client: httpx.Client,
        raw_dir: Path,
        limiter: WeightedRateLimiter | None = None,
        ledger: UsageLedger | None = None,
        daily_budget: float | None = None,
    ) -> None:
        """Build a downloader; by default paced to the free-tier budget, seeded from the ledger."""
        self._client = client
        self.raw_dir = raw_dir
        self.manifest = Manifest(raw_dir / "manifest.jsonl")
        self.ledger = ledger or UsageLedger(raw_dir / "usage.jsonl")
        if limiter is None:
            limits = dict(DEFAULT_LIMITS)
            if daily_budget is not None:
                limits[86400.0] = daily_budget
            limiter = WeightedRateLimiter(limits, clock=time.time, max_wait_s=3700)
            for ts, weight in self.ledger.recent(86400, time.time()):
                limiter.preload(ts, weight)
        self._limiter = limiter

    def fetch_chunk(self, chunk: MonthChunk) -> bytes:
        """Download one chunk and return the raw JSON bytes (validated to contain data)."""
        params: dict[str, str | float] = {
            "latitude": chunk.city.latitude,
            "longitude": chunk.city.longitude,
            "hourly": ",".join(chunk.kind.variables),
            "start_date": chunk.start.isoformat(),
            "end_date": chunk.end.isoformat(),
            "timezone": "UTC",
        }
        if chunk.kind is WeatherKind.FORECAST_D2:
            # Pinned so the archive is one model throughout; for US points the default
            # ("best_match") returned identical values (checked 2023-12 and 2025-01, DFW).
            params["models"] = FORECAST_MODEL
        weight = request_weight(chunk.days, len(chunk.kind.variables))
        self._limiter.acquire(weight)
        self.ledger.append(time.time(), weight)

        def get() -> httpx.Response:
            return raise_for_status(self._client.get(chunk.kind.endpoint, params=params))

        response = with_retries(get)
        payload = response.json()
        hourly = payload.get("hourly") or {}
        if len(hourly.get("time", [])) != chunk.days * 24:
            raise ValueError(
                f"{chunk.key}: expected {chunk.days * 24} hours, got {len(hourly.get('time', []))}"
            )
        return response.content

    def sync(
        self,
        kind: WeatherKind,
        regions: tuple[BalancingAuthority, ...],
        start: date,
        today: date,
        max_chunks: int | None = None,
    ) -> WeatherSyncReport:
        """Download every missing or still-open month; stop cleanly on quota exhaustion."""
        report = WeatherSyncReport()
        chunks = list(month_chunks(kind, regions, start, today))
        for i, chunk in enumerate(chunks):
            entry = self.manifest.get(chunk.key)
            path = self.raw_dir / f"{chunk.key}.json"
            if entry and entry.closed and path.exists():
                report.skipped += 1
                continue
            if max_chunks is not None and report.downloaded >= max_chunks:
                report.remaining = len(chunks) - i
                break
            try:
                content = self.fetch_chunk(chunk)
            except QuotaExhaustedError as exc:
                report.stopped_for_quota = True
                report.remaining = len(chunks) - i
                log.warning("weather.quota", detail=str(exc), remaining=report.remaining)
                break
            atomic_write_bytes(path, content)
            self.manifest.record(
                ManifestEntry(
                    key=chunk.key,
                    url=chunk.kind.endpoint,
                    path=f"{chunk.key}.json",
                    sha256=_sha256(content),
                    bytes=len(content),
                    fetched_at=utc_now(),
                    closed=chunk.closed,
                )
            )
            report.downloaded += 1
            report.refreshed_open += int(entry is not None)
            report.weight_spent += request_weight(chunk.days, len(chunk.kind.variables))
            if report.downloaded % 50 == 0:
                log.info("weather.progress", kind=str(kind), done=report.downloaded, of=len(chunks))
        log.info("weather.sync", kind=str(kind), **_report_fields(report))
        return report


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _report_fields(report: WeatherSyncReport) -> dict[str, object]:
    return {
        "downloaded": report.downloaded,
        "skipped": report.skipped,
        "weight": report.weight_spent,
        "quota_stop": report.stopped_for_quota,
        "remaining": report.remaining,
    }


def parse_hourly(content: bytes) -> list[tuple[datetime, dict[str, float | None]]]:
    """Parse a raw file into (UTC valid time, {variable: value}) rows - used by tests/profiling."""
    payload = json.loads(content)
    hourly = payload["hourly"]
    names = [k for k in hourly if k != "time"]
    rows = []
    for i, stamp in enumerate(hourly["time"]):
        valid = datetime.fromisoformat(stamp).replace(tzinfo=UTC)
        rows.append((valid, {n: hourly[n][i] for n in names}))
    return rows
