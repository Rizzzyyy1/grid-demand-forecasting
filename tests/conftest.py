"""Test isolation: every test runs in a temp cwd with a scrubbed ``GRIDCAST_*`` environment."""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

import pytest

from gridcast.core.settings import get_settings


@pytest.fixture(autouse=True)
def _isolated(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    for key in list(os.environ):
        if key.startswith("GRIDCAST_"):
            monkeypatch.delenv(key)
    monkeypatch.chdir(tmp_path)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
