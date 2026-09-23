"""Generate dbt seed CSVs from the Python registry, so there is one source of truth.

``regions.yaml`` and the ``holidays`` package are authoritative; ``transform/seeds/*.csv`` are
derived artefacts, checked in so ``dbt`` runs without Python; a unit test fails if they drift.
"""

from __future__ import annotations

import csv
import io
from collections.abc import Sequence
from datetime import date
from pathlib import Path

from gridcast.core.calendar import holiday_name
from gridcast.core.regions import all_regions

HOLIDAY_YEARS = range(2018, 2029)


def _csv(header: list[str], rows: Sequence[Sequence[object]]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(header)
    writer.writerows(rows)
    return buf.getvalue()


def render_seeds() -> dict[str, str]:
    """File name -> CSV text for every generated seed."""
    regions = [[ba.code, ba.name, ba.timezone, len(ba.cities)] for ba in all_regions()]
    cities = []
    for ba in all_regions():
        weights = ba.population_weights()
        for c in ba.cities:
            cities.append(
                [
                    ba.code,
                    c.name,
                    c.slug,
                    c.latitude,
                    c.longitude,
                    c.population,
                    round(weights[c.name], 6),
                ]
            )
    holidays = []
    for year in HOLIDAY_YEARS:
        day = date(year, 1, 1)
        while day.year == year:
            if (name := holiday_name(day)) is not None:
                holidays.append([day.isoformat(), name])
            day = date.fromordinal(day.toordinal() + 1)
    return {
        "regions.csv": _csv(["ba_code", "name", "timezone", "n_cities"], regions),
        "cities.csv": _csv(
            ["ba_code", "city", "city_slug", "latitude", "longitude", "population", "weight"],
            cities,
        ),
        "us_holidays.csv": _csv(["holiday_date", "holiday_name"], holidays),
    }


def write_seeds(seed_dir: Path) -> list[Path]:
    """Write all seeds into ``seed_dir``; returns the paths written."""
    seed_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for name, text in render_seeds().items():
        path = seed_dir / name
        path.write_text(text, encoding="utf-8")
        written.append(path)
    return written
