from __future__ import annotations

from pathlib import Path

import gridcast
from gridcast.warehouse.seeds import render_seeds

SEEDS = Path(gridcast.__file__).parents[2] / "transform" / "seeds"


def test_checked_in_seeds_match_the_registry() -> None:
    rendered = render_seeds()
    assert set(rendered) == {"regions.csv", "cities.csv", "us_holidays.csv"}
    for name, text in rendered.items():
        on_disk = (SEEDS / name).read_text(encoding="utf-8")
        assert on_disk == text, f"{name} is stale: run `gridcast seeds`"


def test_seed_contents() -> None:
    rendered = render_seeds()
    assert len(rendered["regions.csv"].splitlines()) == 11
    assert "2025-07-04,Independence Day" in rendered["us_holidays.csv"]
    weights = [float(line.split(",")[-1]) for line in rendered["cities.csv"].splitlines()[1:]]
    assert abs(sum(weights) - 10) < 1e-4  # ten BAs, each summing to 1
