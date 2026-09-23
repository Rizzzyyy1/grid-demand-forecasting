from __future__ import annotations

import json
from datetime import timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from gridcast.core.settings import get_settings
from gridcast.live.issue import STORE_FILE
from gridcast.live.store import ForecastStore
from gridcast.serving.app import create_app
from tests.unit.live.test_store import ISSUED, _batch


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("GRIDCAST_BASE_DIR", str(tmp_path))
    get_settings.cache_clear()
    return TestClient(create_app())


def test_health_and_regions(client: TestClient) -> None:
    assert client.get("/healthz").json()["status"] == "ok"
    assert client.get("/readyz").status_code == 503  # nothing built yet
    regions = client.get("/v1/regions").json()
    assert [r["code"] for r in regions][:3] == ["PJM", "MISO", "ERCO"]


def test_forecast_roundtrip(client: TestClient, tmp_path: Path) -> None:
    store = ForecastStore(tmp_path / "data" / STORE_FILE)
    store.append(
        _batch("lgbm_live"),
        created_at=ISSUED - timedelta(minutes=30),
        protocol="bulk",
        model_version="4",
    )
    r = client.get("/v1/forecasts/PJM", params={"day": "2025-07-15"})
    assert r.status_code == 200
    body = r.json()
    assert body["model_version"] == "4" and not body["late"] and len(body["hours"]) == 24
    assert body["issued_at"].startswith("2025-07-14T14:00:00")
    assert client.get("/v1/forecasts/PJM", params={"day": "2025-07-16"}).status_code == 404
    assert client.get("/v1/forecasts/NOPE", params={"day": "2025-07-15"}).status_code == 404


def test_backtest_listing(client: TestClient, tmp_path: Path) -> None:
    run = tmp_path / "reports" / "runs" / "20260101T000000Z"
    run.mkdir(parents=True)
    (run / "config.json").write_text(
        json.dumps(
            {
                "run_id": run.name,
                "split": "validation",
                "window": ["a", "b"],
                "models": ["x"],
                "refits": 12,
            }
        )
    )
    (run / "summary.md").write_text("# hi")
    assert client.get("/v1/backtests").json()[0]["refits"] == 12
    assert client.get(f"/v1/backtests/{run.name}/summary").json()["markdown"] == "# hi"
    assert client.get("/v1/backtests/..%2Fetc/summary").status_code in (400, 404)


def test_leaderboard_empty_without_store(client: TestClient) -> None:
    assert client.get("/v1/leaderboard").json() == []
