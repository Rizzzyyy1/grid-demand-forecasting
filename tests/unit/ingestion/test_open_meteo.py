from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from pathlib import Path

import httpx
import pytest

from gridcast.core.regions import get_region
from gridcast.ingestion.http import WeightedRateLimiter, make_client
from gridcast.ingestion.weather.open_meteo import (
    OpenMeteoDownloader,
    WeatherKind,
    month_chunks,
    parse_hourly,
    request_weight,
)

ERCO = (get_region("ERCO"),)  # 4 cities


def fake_api(status_after: int | None = None, hours_short: bool = False):  # type: ignore[no-untyped-def]
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if status_after is not None and len(calls) > status_after:
            return httpx.Response(429, json={"reason": "Daily API request limit exceeded"})
        start = date.fromisoformat(request.url.params["start_date"])
        end = date.fromisoformat(request.url.params["end_date"])
        n = ((end - start).days + 1) * 24 - (1 if hours_short else 0)
        t0 = datetime(start.year, start.month, start.day)
        times = [(t0 + timedelta(hours=i)).strftime("%Y-%m-%dT%H:%M") for i in range(n)]
        hourly = {"time": times}
        for var in request.url.params["hourly"].split(","):
            hourly[var] = [20.5] * n
        return httpx.Response(200, json={"latitude": 1, "longitude": 2, "hourly": hourly})

    return handler, calls


def unlimited() -> WeightedRateLimiter:
    return WeightedRateLimiter({60.0: 1e9})


def test_request_weight_matches_open_meteo_accounting() -> None:
    assert request_weight(14, 6) == 1
    assert request_weight(31, 6) == 3
    assert request_weight(28, 11) == 4


def test_month_chunks_newest_first_and_closing() -> None:
    chunks = list(month_chunks(WeatherKind.FORECAST_D2, ERCO, date(2025, 1, 1), date(2025, 3, 10)))
    assert len(chunks) == 3 * 4
    assert chunks[0].start == date(2025, 3, 1) and chunks[0].end == date(2025, 3, 11)  # tomorrow
    assert not chunks[0].closed  # current month
    assert chunks[4].start == date(2025, 2, 1) and chunks[4].closed  # Feb settled by Mar 10
    assert chunks[-1].start == date(2025, 1, 1)


def test_sync_downloads_then_skips_closed(tmp_path: Path) -> None:
    handler, calls = fake_api()
    with make_client(transport=httpx.MockTransport(handler)) as client:
        d = OpenMeteoDownloader(client, tmp_path, limiter=unlimited())
        first = d.sync(WeatherKind.FORECAST_D2, ERCO, date(2025, 1, 1), date(2025, 3, 10))
        assert first.downloaded == 12
        second = OpenMeteoDownloader(client, tmp_path, limiter=unlimited()).sync(
            WeatherKind.FORECAST_D2, ERCO, date(2025, 1, 1), date(2025, 3, 10)
        )
    assert second.skipped == 8  # Jan + Feb closed
    assert second.downloaded == 4 and second.refreshed_open == 4  # March refreshed
    assert calls[0].url.params["hourly"].endswith("_previous_day2")
    assert calls[0].url.params["models"] == "gfs_seamless"
    path = tmp_path / "forecast_d2/ERCO/houston/2025-02.json"
    rows = parse_hourly(path.read_bytes())
    assert len(rows) == 28 * 24
    assert rows[0][1]["temperature_2m_previous_day2"] == 20.5
    assert len((tmp_path / "usage.jsonl").read_text().splitlines()) == 16


def test_quota_stops_cleanly_and_resumes(tmp_path: Path) -> None:
    handler, _ = fake_api(status_after=5)
    with make_client(transport=httpx.MockTransport(handler)) as client:
        report = OpenMeteoDownloader(client, tmp_path, limiter=unlimited()).sync(
            WeatherKind.OBSERVED, ERCO, date(2025, 1, 1), date(2025, 3, 20)
        )
    assert report.stopped_for_quota and report.downloaded == 5 and report.remaining == 7

    handler, _ = fake_api()
    with make_client(transport=httpx.MockTransport(handler)) as client:
        resumed = OpenMeteoDownloader(client, tmp_path, limiter=unlimited()).sync(
            WeatherKind.OBSERVED, ERCO, date(2025, 1, 1), date(2025, 3, 20)
        )
    # first run got 4 open March chunks + 1 closed Feb chunk; only the closed one is skipped
    assert resumed.skipped == 1 and resumed.downloaded == 11 and resumed.refreshed_open == 4


def test_truncated_response_is_rejected(tmp_path: Path) -> None:
    handler, _ = fake_api(hours_short=True)
    with make_client(transport=httpx.MockTransport(handler)) as client:
        d = OpenMeteoDownloader(client, tmp_path, limiter=unlimited())
        with pytest.raises(ValueError, match="expected"):
            d.sync(WeatherKind.FORECAST_D2, ERCO, date(2025, 1, 1), date(2025, 1, 20))
    assert not list(tmp_path.rglob("*.json"))
    assert json.loads((tmp_path / "usage.jsonl").read_text().splitlines()[0])[1] == 2
