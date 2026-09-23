from __future__ import annotations

import pytest

from gridcast.ingestion.http import QuotaExhaustedError, WeightedRateLimiter


class FakeClock:
    def __init__(self) -> None:
        self.now = 1_000.0
        self.slept: list[float] = []

    def __call__(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.slept.append(seconds)
        self.now += seconds


def test_waits_until_window_frees() -> None:
    clock = FakeClock()
    limiter = WeightedRateLimiter({60.0: 10.0}, clock=clock, sleep=clock.sleep)
    for _ in range(5):
        limiter.acquire(2)
    assert clock.slept == []
    limiter.acquire(2)  # 12 > 10: must wait for the first event to leave the window
    assert clock.slept == [pytest.approx(60.0)]
    assert limiter.total_weight == 12


def test_multiple_windows_bind_independently() -> None:
    clock = FakeClock()
    limiter = WeightedRateLimiter({1.0: 5.0, 100.0: 6.0}, clock=clock, sleep=clock.sleep)
    limiter.acquire(3)
    clock.now += 2  # the short window has cleared, the long one has not
    limiter.acquire(3)
    limiter.acquire(3)
    assert sum(clock.slept) == pytest.approx(98.0)


def test_preloaded_usage_counts_and_long_waits_raise() -> None:
    clock = FakeClock()
    limiter = WeightedRateLimiter({86400.0: 10.0}, clock=clock, sleep=clock.sleep, max_wait_s=3600)
    limiter.preload(clock.now - 10, 9)  # another process spent the budget
    with pytest.raises(QuotaExhaustedError, match="budget spent"):
        limiter.acquire(2)


def test_weight_above_any_limit_is_rejected() -> None:
    limiter = WeightedRateLimiter({60.0: 5.0})
    with pytest.raises(ValueError, match="exceeds"):
        limiter.acquire(6)
