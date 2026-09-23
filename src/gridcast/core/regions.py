"""The balancing-authority registry, loaded from ``gridcast/resources/regions.yaml``."""

from __future__ import annotations

from functools import cache
from importlib import resources

import yaml
from pydantic import BaseModel, ConfigDict

from gridcast.core.domain import BalancingAuthority


class _RegistryFile(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    balancing_authorities: tuple[BalancingAuthority, ...]


class UnknownRegionError(KeyError):
    """Raised for a BA code that is not in the registry."""


@cache
def all_regions() -> tuple[BalancingAuthority, ...]:
    """Every configured BA, in registry order (largest average demand first)."""
    text = resources.files("gridcast.resources").joinpath("regions.yaml").read_text("utf-8")
    registry = _RegistryFile.model_validate(yaml.safe_load(text))
    codes = [ba.code for ba in registry.balancing_authorities]
    if len(codes) != len(set(codes)):
        raise ValueError(f"duplicate BA codes in regions.yaml: {codes}")
    return registry.balancing_authorities


def region_codes() -> tuple[str, ...]:
    """Codes of every configured BA."""
    return tuple(ba.code for ba in all_regions())


def get_region(code: str) -> BalancingAuthority:
    """Look up one BA by EIA code."""
    for ba in all_regions():
        if ba.code == code:
            return ba
    raise UnknownRegionError(f"unknown balancing authority {code!r}; known: {region_codes()}")
