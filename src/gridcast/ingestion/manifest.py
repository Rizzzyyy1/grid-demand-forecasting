"""Append-only download manifest: what was fetched, from where, when, and its sha256.

The manifest is JSON Lines so that concurrent history is never rewritten; the latest entry per key
wins. It is how a re-run knows it has nothing to do, and how every raw file is auditable.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict


class ManifestEntry(BaseModel):
    """One completed download."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    key: str
    url: str
    path: str
    sha256: str
    bytes: int
    fetched_at: datetime
    last_modified: str | None = None
    closed: bool = False


class Manifest:
    """JSON Lines manifest stored next to the raw files it describes."""

    def __init__(self, path: Path) -> None:
        """Open (or lazily create) the manifest at ``path``."""
        self.path = path
        self._latest: dict[str, ManifestEntry] = {}
        if path.exists():
            for line in path.read_text("utf-8").splitlines():
                if line.strip():
                    entry = ManifestEntry.model_validate_json(line)
                    self._latest[entry.key] = entry

    def get(self, key: str) -> ManifestEntry | None:
        """Latest entry for ``key``."""
        return self._latest.get(key)

    def record(self, entry: ManifestEntry) -> None:
        """Append ``entry`` and make it the latest for its key."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry.model_dump(mode="json"), sort_keys=True) + "\n")
        self._latest[entry.key] = entry

    def entries(self) -> list[ManifestEntry]:
        """Latest entry for every key."""
        return list(self._latest.values())

    def __len__(self) -> int:
        return len(self._latest)


def sha256_file(path: Path, chunk: int = 1 << 20) -> str:
    """Hex sha256 of a file, streamed."""
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        while block := fh.read(chunk):
            digest.update(block)
    return digest.hexdigest()


def atomic_write_bytes(path: Path, data: bytes) -> None:
    """Write ``data`` to ``path`` via a temp file + rename, so readers never see partial files."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".part")
    tmp.write_bytes(data)
    tmp.replace(path)
