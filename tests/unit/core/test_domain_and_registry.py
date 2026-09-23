from __future__ import annotations

from datetime import date

import pytest
from pydantic import ValidationError

from gridcast.core.calendar import day_type, holiday_name
from gridcast.core.domain import ForecastOrigin, ProtocolConfig, slugify
from gridcast.core.regions import UnknownRegionError, all_regions, get_region, region_codes
from gridcast.core.settings import Settings, Window


def test_registry_has_the_ten_designed_regions() -> None:
    assert region_codes() == (
        "PJM",
        "MISO",
        "ERCO",
        "SWPP",
        "SOCO",
        "CISO",
        "TVA",
        "NYIS",
        "FPL",
        "ISNE",
    )
    for ba in all_regions():
        assert 3 <= len(ba.cities) <= 6
        assert sum(ba.population_weights().values()) == pytest.approx(1.0)


def test_unknown_region() -> None:
    with pytest.raises(UnknownRegionError):
        get_region("NOPE")


def test_origin_protocol_for_pjm() -> None:
    origin = ForecastOrigin.for_day(get_region("PJM"), date(2025, 7, 15), ProtocolConfig())
    assert origin.issued_at.isoformat() == "2025-07-14T14:00:00+00:00"  # 10:00 EDT
    assert origin.demand_cutoff.isoformat() == "2025-07-14T10:00:00+00:00"  # 06:00 EDT


def test_protocol_rejects_leaky_settings() -> None:
    with pytest.raises(ValidationError):
        ProtocolConfig(weather_lead_days=1)
    with pytest.raises(ValidationError):
        ProtocolConfig.model_validate({"demand_cutoff_time": "11:00", "issue_time": "10:00"})


def test_models_are_frozen() -> None:
    ba = get_region("ERCO")
    with pytest.raises(ValidationError):
        ba.code = "X"  # type: ignore[misc]


def test_settings_windows_do_not_overlap() -> None:
    with pytest.raises(ValidationError):
        Settings(test=Window(start=date(2024, 1, 1), end=date(2024, 12, 31)))
    s = Settings()
    assert s.validation.end < s.test.start


def test_calendar() -> None:
    assert holiday_name(date(2025, 7, 4)) == "Independence Day"
    assert day_type(date(2025, 7, 4)) == "holiday"
    assert day_type(date(2025, 7, 5)) == "weekend"
    assert day_type(date(2025, 7, 7)) == "weekday"


def test_slugify() -> None:
    assert slugify("St. Louis") == "st-louis"
    assert slugify("Dallas-Fort Worth") == "dallas-fort-worth"


def test_bulk_protocol_timing() -> None:
    from datetime import timedelta

    bulk = ProtocolConfig.bulk()
    assert bulk.publication_lag == timedelta(hours=34)
    assert bulk.recent_day_offset == 3
    assert ProtocolConfig().publication_lag == timedelta(hours=4)
    assert ProtocolConfig().recent_day_offset == 2
    origin = ForecastOrigin.for_day(get_region("ERCO"), date(2025, 7, 15), bulk)
    assert origin.demand_cutoff.isoformat() == "2025-07-13T05:00:00+00:00"  # 00:00 CDT on D-2
