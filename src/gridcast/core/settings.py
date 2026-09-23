"""Runtime settings (paths and evaluation windows), from ``GRIDCAST_*`` environment variables.

No secrets live here: every data source GridCast uses is keyless (DESIGN section 2).
"""

from __future__ import annotations

from datetime import date
from functools import cache
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from gridcast.core.domain import ProtocolConfig


class Window(BaseModel):
    """An inclusive range of target days."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    start: date
    end: date

    @model_validator(mode="after")
    def _ordered(self) -> Window:
        if self.end < self.start:
            raise ValueError(f"window ends ({self.end}) before it starts ({self.start})")
        return self

    def contains(self, day: date) -> bool:
        """True if ``day`` lies inside the window."""
        return self.start <= day <= self.end


class Settings(BaseSettings):
    """Process-wide configuration."""

    model_config = SettingsConfigDict(
        env_prefix="GRIDCAST_", env_nested_delimiter="__", env_file=".env", extra="ignore"
    )

    base_dir: Path = Field(default=Path())
    eia_start_year: int = 2019
    weather_start: date = date(2021, 3, 1)  # archived forecasts begin 2021-03-25
    protocol: ProtocolConfig = ProtocolConfig()
    validation: Window = Window(start=date(2023, 7, 1), end=date(2024, 6, 30))
    test: Window = Window(start=date(2024, 7, 1), end=date(2026, 6, 30))
    http_timeout_s: float = 60.0
    open_meteo_requests_per_minute: int = Field(default=300, gt=0)

    @model_validator(mode="after")
    def _test_after_validation(self) -> Settings:
        if self.test.start <= self.validation.end:
            raise ValueError("the test window must start after the validation window ends")
        return self

    @property
    def data_dir(self) -> Path:
        """Root of all data (raw downloads, warehouse, artefacts)."""
        return self.base_dir / "data"

    @property
    def raw_dir(self) -> Path:
        """Immutable raw downloads."""
        return self.data_dir / "raw"

    @property
    def warehouse_path(self) -> Path:
        """The DuckDB warehouse file dbt builds into."""
        return self.data_dir / "warehouse.duckdb"

    @property
    def reports_dir(self) -> Path:
        """Generated reports and run results."""
        return self.base_dir / "reports"

    @property
    def mlruns_dir(self) -> Path:
        """Local MLflow tracking store."""
        return self.data_dir / "mlruns"


@cache
def get_settings() -> Settings:
    """The process-wide settings (cached; call ``get_settings.cache_clear()`` in tests)."""
    return Settings()
