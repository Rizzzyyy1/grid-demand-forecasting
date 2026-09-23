"""Repository conventions that are cheap to enforce mechanically."""

from __future__ import annotations

import ast
from pathlib import Path

import gridcast

SRC = Path(gridcast.__file__).parent
# Dagster resolves ``context`` annotations eagerly and rejects postponed (string) annotations.
DAGSTER_MODULES = {"orchestration/definitions.py"}


def _modules() -> list[Path]:
    return sorted(SRC.rglob("*.py"))


def test_every_module_states_its_responsibility() -> None:
    missing = [
        str(p.relative_to(SRC))
        for p in _modules()
        if not ast.get_docstring(ast.parse(p.read_text()))
    ]
    assert not missing, f"modules without a docstring: {missing}"
    assert len(_modules()) >= 10  # the check says how much it checked


def test_every_module_uses_postponed_annotations() -> None:
    offenders = [
        str(p.relative_to(SRC))
        for p in _modules()
        if "def " in p.read_text()
        and "from __future__ import annotations" not in p.read_text()
        and p.relative_to(SRC).as_posix() not in DAGSTER_MODULES
    ]
    assert not offenders, offenders
