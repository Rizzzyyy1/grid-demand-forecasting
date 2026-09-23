from __future__ import annotations

from datetime import date
from pathlib import Path

import httpx
import pytest

from gridcast.ingestion.eia.bulk import BulkFile, EiaBulkDownloader, bulk_files
from gridcast.ingestion.http import QuotaExhaustedError, make_client
from gridcast.ingestion.manifest import sha256_file

BODY = b'"Balancing Authority","Data Date"\nPJM,01/01/2025\n'


def test_bulk_files_enumeration_and_closing() -> None:
    files = bulk_files(2024, date(2025, 8, 1))
    assert [f.filename for f in files] == [
        "EIA930_BALANCE_2024_Jan_Jun.csv",
        "EIA930_BALANCE_2024_Jul_Dec.csv",
        "EIA930_BALANCE_2025_Jan_Jun.csv",
        "EIA930_BALANCE_2025_Jul_Dec.csv",
    ]
    today = date(2025, 8, 1)
    assert BulkFile(2024, False).is_closed(today)
    assert not BulkFile(2025, True).is_closed(today)  # ended 31 days ago: EIA may still revise


class FakeEia:
    def __init__(self) -> None:
        self.requests: list[httpx.Request] = []
        self.last_modified = "Tue, 22 Sep 2026 14:39:19 GMT"

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if request.headers.get("If-Modified-Since") == self.last_modified:
            return httpx.Response(304)
        return httpx.Response(200, content=BODY, headers={"Last-Modified": self.last_modified})


def test_sync_is_idempotent(tmp_path: Path) -> None:
    fake = FakeEia()
    today = date(2025, 8, 1)
    with make_client(transport=httpx.MockTransport(fake)) as client:
        first = EiaBulkDownloader(client, tmp_path).sync(2024, today)
        assert len(first.downloaded) == 4
        assert first.bytes_downloaded == 4 * len(BODY)

        # a fresh downloader (new process) reads the manifest back
        second = EiaBulkDownloader(client, tmp_path).sync(2024, today)
    assert second.downloaded == []
    assert second.skipped_closed == [
        "EIA930_BALANCE_2024_Jan_Jun.csv",
        "EIA930_BALANCE_2024_Jul_Dec.csv",
    ]
    assert second.not_modified == [
        "EIA930_BALANCE_2025_Jan_Jun.csv",
        "EIA930_BALANCE_2025_Jul_Dec.csv",
    ]
    assert second.files_checked == 4
    assert len(fake.requests) == 6  # 4 downloads + 2 conditional GETs, no re-download of closed
    entry = EiaBulkDownloader(client, tmp_path).manifest.get("EIA930_BALANCE_2024_Jan_Jun.csv")
    assert entry is not None and entry.closed
    assert entry.sha256 == sha256_file(tmp_path / "EIA930_BALANCE_2024_Jan_Jun.csv")
    assert not list(tmp_path.glob("*.part"))


def test_empty_body_is_an_error(tmp_path: Path) -> None:
    transport = httpx.MockTransport(lambda r: httpx.Response(200, content=b""))
    with make_client(transport=transport) as client, pytest.raises(ValueError, match="empty"):
        EiaBulkDownloader(client, tmp_path).sync(2025, date(2025, 2, 1))


def test_429_is_not_retried(tmp_path: Path) -> None:
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(429, text="slow down")

    with (
        make_client(transport=httpx.MockTransport(handler)) as client,
        pytest.raises(QuotaExhaustedError),
    ):
        EiaBulkDownloader(client, tmp_path).sync(2025, date(2025, 2, 1))
    assert len(calls) == 1
