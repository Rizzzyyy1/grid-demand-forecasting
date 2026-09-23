from __future__ import annotations

import re
from pathlib import Path

from typer.testing import CliRunner

import gridcast
from gridcast.cli import app

ROOT = Path(gridcast.__file__).parents[2]
runner = CliRunner()


def _registered() -> set[str]:
    names = {c.name or c.callback.__name__ for c in app.registered_commands}  # type: ignore[union-attr]
    for group in app.registered_groups:
        names.add(group.name or "")
    return names


def test_every_documented_command_is_registered() -> None:
    documented = set()
    for doc in (ROOT / "README.md", ROOT / "CLAUDE.md"):
        documented |= set(re.findall(r"gridcast ([a-z]+)", doc.read_text()))
    missing = documented - _registered()
    assert not missing, f"documented but not registered: {missing}"
    assert len(documented) >= 8  # the check says how much it checked


def test_regions_command_runs() -> None:
    result = runner.invoke(app, ["regions"])
    assert result.exit_code == 0
    assert "PJM" in result.output and "Etc/GMT+5" in result.output
