"""Refuse a scheduled commit to the `live-data` branch unless it only appends what it should.

Run from the live-data checkout after `git add -A`:  python verify_live_commit.py
Reads `git diff --cached --name-status` and fails (exit 1) if the commit would

* modify or delete any issued forecast (forecasts are immutable - append only),
* touch anything outside forecasts/, scores/ and status/ (e.g. the model artefact, which only a
  human export may change),
* add a file larger than 1 MB (a runaway write), or
* add a forecast file whose path is not `forecasts/target=YYYY-MM-DD/<model>.parquet`.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

MAX_BYTES = 1_000_000
FORECAST = re.compile(r"^forecasts/target=\d{4}-\d{2}-\d{2}/[a-z0-9_]+\.parquet$")
MUTABLE = re.compile(r"^(scores/(leaderboard|daily)\.csv|status/latest\.json)$")


def check(name_status: list[str], size_of: dict[str, int]) -> list[str]:
    """Problems with a staged change set (empty list = allowed)."""
    problems = []
    for line in name_status:
        if not line.strip():
            continue
        status, *paths = line.split("\t")
        path = paths[-1]
        kind = status[0]
        if path.startswith("forecasts/"):
            if kind != "A":
                problems.append(f"{path}: issued forecasts are immutable (status {status})")
            elif not FORECAST.match(path):
                problems.append(f"{path}: unexpected forecast file name")
        elif not MUTABLE.match(path):
            problems.append(f"{path}: the scheduled job may not change this path")
        if kind in {"A", "M"} and size_of.get(path, 0) > MAX_BYTES:
            problems.append(f"{path}: {size_of[path]:,} bytes exceeds {MAX_BYTES:,}")
    return problems


def main() -> int:
    """Check the index of the current repository."""
    out = subprocess.run(
        ["git", "diff", "--cached", "--name-status"],  # noqa: S607 - fixed command
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()
    sizes = {}
    for line in out:
        path = line.split("\t")[-1]
        if Path(path).exists():
            sizes[path] = Path(path).stat().st_size
    problems = check(out, sizes)
    for p in problems:
        print(f"::error::{p}")
    print(f"checked {len([o for o in out if o.strip()])} staged paths, {len(problems)} problems")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
