"""Append-only store of issued forecasts (``data/forecast_store.duckdb``).

A forecast, once written, is never updated or deleted: the primary key is
(ba_code, hour_ending_utc, model, issued_at) and a duplicate insert raises. Each row records
``created_at`` (the wall-clock time it was actually produced) next to the protocol's
``issued_at``; a forecast produced after its issue time is kept but flagged ``late`` so the live
track record cannot quietly benefit from late data.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

import duckdb
import polars as pl

from gridcast.core.contracts import ForecastBatch

DDL = """
create table if not exists forecasts (
    ba_code varchar not null,
    target_day date not null,
    hour_ending_utc timestamptz not null,
    issued_at timestamptz not null,
    model varchar not null,
    yhat double,
    q10 double,
    q90 double,
    q025 double,
    q975 double,
    created_at timestamptz not null,
    late boolean not null,
    protocol varchar not null,
    model_version varchar not null,
    primary key (ba_code, hour_ending_utc, model, issued_at)
)
"""


class DuplicateForecastError(RuntimeError):
    """Raised when a forecast with the same key was already stored (the store is immutable)."""


class ForecastStore:
    """Thin wrapper around one DuckDB file."""

    def __init__(self, path: Path) -> None:
        """Open or create the store at ``path``."""
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect(read_only=False) as con:
            con.execute(DDL)

    @contextmanager
    def _connect(self, read_only: bool) -> Iterator[duckdb.DuckDBPyConnection]:
        con = duckdb.connect(str(self.path), read_only=read_only)
        try:
            con.execute("SET TimeZone = 'UTC'")
            yield con
        finally:
            con.close()

    def append(
        self, batch: pl.DataFrame, created_at: datetime, protocol: str, model_version: str
    ) -> int:
        """Insert a validated batch; returns rows written. Never overwrites."""
        batch = ForecastBatch.validate(batch)
        rows = batch.with_columns(
            pl.lit(created_at).cast(pl.Datetime("us", "UTC")).alias("created_at"),
            (pl.lit(created_at).cast(pl.Datetime("us", "UTC")) > pl.col("issued_at")).alias("late"),
            pl.lit(protocol).alias("protocol"),
            pl.lit(model_version).alias("model_version"),
        )
        with self._connect(read_only=False) as con:
            con.register("incoming", rows.to_arrow())
            try:
                con.execute(
                    """insert into forecasts
                       select ba_code, target_day, hour_ending_utc, issued_at, model, yhat,
                              q10, q90, q025, q975, created_at, late, protocol, model_version
                       from incoming"""
                )
            except duckdb.ConstraintException as exc:
                raise DuplicateForecastError(str(exc).splitlines()[0]) from exc
        return rows.height

    def read(self, where: str = "true", params: list[object] | None = None) -> pl.DataFrame:
        """Rows matching a parameterised ``where`` clause, ordered by key."""
        with self._connect(read_only=True) as con:
            return con.execute(
                f"select * from forecasts where {where} order by ba_code, hour_ending_utc, model",  # noqa: S608
                params or [],
            ).pl()

    def count(self) -> int:
        """Rows stored."""
        with self._connect(read_only=True) as con:
            row = con.execute("select count(*) from forecasts").fetchone()
        return int(row[0]) if row else 0
