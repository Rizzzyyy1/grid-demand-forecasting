"""EIA-930 six-month bulk "BALANCE" files: enumerate, download idempotently, record in a manifest.

Periods whose end lies more than ``CLOSE_AFTER`` in the past are *closed*: downloaded once and
never re-fetched (a forced refresh is available). Open periods are re-fetched with
``If-Modified-Since`` so an unchanged file costs one 304. Note: EIA regenerates every file's
``Last-Modified`` daily, so revisions to closed periods are only picked up by a forced refresh.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

import httpx
import structlog

from gridcast.core.time import utc_now
from gridcast.ingestion.http import raise_for_status, with_retries
from gridcast.ingestion.manifest import Manifest, ManifestEntry

log = structlog.get_logger(__name__)

BASE_URL = "https://www.eia.gov/electricity/gridmonitor/sixMonthFiles"
CLOSE_AFTER = timedelta(days=60)


@dataclass(frozen=True)
class BulkFile:
    """One six-month EIA-930 balance file."""

    year: int
    first_half: bool

    @property
    def filename(self) -> str:
        """File name as published by EIA."""
        return f"EIA930_BALANCE_{self.year}_{'Jan_Jun' if self.first_half else 'Jul_Dec'}.csv"

    @property
    def url(self) -> str:
        """Download URL."""
        return f"{BASE_URL}/{self.filename}"

    @property
    def period_start(self) -> date:
        """First day covered."""
        return date(self.year, 1 if self.first_half else 7, 1)

    @property
    def period_end(self) -> date:
        """Last day covered."""
        return date(self.year, 6, 30) if self.first_half else date(self.year, 12, 31)

    def is_closed(self, today: date) -> bool:
        """True once the period ended long enough ago that EIA no longer revises it."""
        return self.period_end + CLOSE_AFTER < today


def bulk_files(start_year: int, today: date) -> list[BulkFile]:
    """Every half-year file from ``start_year`` up to the one containing ``today``."""
    files = []
    for year in range(start_year, today.year + 1):
        for first_half in (True, False):
            f = BulkFile(year, first_half)
            if f.period_start <= today:
                files.append(f)
    return files


@dataclass
class SyncReport:
    """What a sync did - so a no-op re-run is visibly a no-op."""

    downloaded: list[str] = field(default_factory=list)
    not_modified: list[str] = field(default_factory=list)
    skipped_closed: list[str] = field(default_factory=list)
    bytes_downloaded: int = 0

    @property
    def files_checked(self) -> int:
        """Total files considered."""
        return len(self.downloaded) + len(self.not_modified) + len(self.skipped_closed)


class EiaBulkDownloader:
    """Downloads EIA-930 bulk files into ``raw_dir`` and records them in a manifest."""

    def __init__(self, client: httpx.Client, raw_dir: Path) -> None:
        """``raw_dir`` is ``data/raw/eia``; the manifest lives inside it."""
        self._client = client
        self.raw_dir = raw_dir
        self.manifest = Manifest(raw_dir / "manifest.jsonl")

    def sync(self, start_year: int, today: date, force: bool = False) -> SyncReport:
        """Bring ``raw_dir`` up to date. Safe to re-run; closed files are fetched once."""
        report = SyncReport()
        for f in bulk_files(start_year, today):
            entry = self.manifest.get(f.filename)
            path = self.raw_dir / f.filename
            if entry and entry.closed and path.exists() and not force:
                report.skipped_closed.append(f.filename)
                continue
            last_modified = entry.last_modified if (entry and path.exists() and not force) else None
            result = self._download(f, path, last_modified, closed=f.is_closed(today))
            if result is None:
                report.not_modified.append(f.filename)
            else:
                report.downloaded.append(f.filename)
                report.bytes_downloaded += result.bytes
        log.info(
            "eia.sync",
            checked=report.files_checked,
            downloaded=len(report.downloaded),
            not_modified=len(report.not_modified),
            skipped_closed=len(report.skipped_closed),
        )
        return report

    def _download(
        self, f: BulkFile, path: Path, last_modified: str | None, closed: bool
    ) -> ManifestEntry | None:
        headers = {"If-Modified-Since": last_modified} if last_modified else {}

        def fetch() -> ManifestEntry | None:
            with self._client.stream("GET", f.url, headers=headers) as response:
                if response.status_code == 304:
                    return None
                raise_for_status(response)
                digest = hashlib.sha256()
                size = 0
                path.parent.mkdir(parents=True, exist_ok=True)
                tmp = path.with_suffix(".csv.part")
                with tmp.open("wb") as fh:
                    for chunk in response.iter_bytes(1 << 20):
                        fh.write(chunk)
                        digest.update(chunk)
                        size += len(chunk)
                if size == 0:
                    tmp.unlink()
                    raise ValueError(f"{f.url} returned an empty body")
                tmp.replace(path)
                return ManifestEntry(
                    key=f.filename,
                    url=f.url,
                    path=str(path.name),
                    sha256=digest.hexdigest(),
                    bytes=size,
                    fetched_at=utc_now(),
                    last_modified=response.headers.get("Last-Modified"),
                    closed=closed,
                )

        entry = with_retries(fetch)
        if entry is not None:
            self.manifest.record(entry)
            log.info("eia.downloaded", file=f.filename, bytes=entry.bytes, closed=closed)
        return entry
