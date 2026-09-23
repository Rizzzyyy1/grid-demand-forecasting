"""Shared HTTP plumbing: one configured ``httpx.Client``, retries, and a weighted rate limiter.

Every outbound request in GridCast goes through a client built here, so User-Agent, timeouts and
retry policy are defined once. Tests inject ``httpx.MockTransport`` - no network.
"""

from __future__ import annotations

import threading
import time
from collections import deque
from collections.abc import Callable

import httpx
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential_jitter,
)

from gridcast import __version__

USER_AGENT = f"gridcast/{__version__} (research; +https://github.com/)"
RETRYABLE_STATUS = frozenset({500, 502, 503, 504})


class QuotaExhaustedError(RuntimeError):
    """The provider refused further requests for now (HTTP 429). Not retried: resume later."""


def make_client(
    timeout_s: float = 60.0, transport: httpx.BaseTransport | None = None
) -> httpx.Client:
    """An ``httpx.Client`` with GridCast defaults; pass ``transport`` to mock in tests."""
    return httpx.Client(
        timeout=httpx.Timeout(timeout_s),
        headers={"User-Agent": USER_AGENT},
        follow_redirects=True,
        transport=transport,
    )


def _is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in RETRYABLE_STATUS
    return isinstance(exc, httpx.TransportError)


def with_retries[T](fn: Callable[[], T], attempts: int = 5) -> T:
    """Call ``fn`` retrying transport errors and 5xx with jittered exponential back-off."""
    wrapped = retry(
        retry=retry_if_exception(_is_retryable),
        stop=stop_after_attempt(attempts),
        wait=wait_exponential_jitter(initial=1, max=30),
        reraise=True,
    )(fn)
    return wrapped()


def raise_for_status(response: httpx.Response) -> httpx.Response:
    """Like ``Response.raise_for_status`` but maps 429 to ``QuotaExhaustedError``."""
    if response.status_code == 429:
        raise QuotaExhaustedError(response.text[:300])
    response.raise_for_status()
    return response


class WeightedRateLimiter:
    """Sliding-window limiter where each request consumes a *weight* (Open-Meteo counts a
    request spanning many days as several calls). Thread-safe; ``sleep`` injectable for tests."""

    def __init__(
        self,
        limits: dict[float, float],
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
        max_wait_s: float = float("inf"),
    ) -> None:
        """``limits`` maps window length (s) to the maximum total weight in that window.

        If honouring a limit would mean waiting longer than ``max_wait_s`` (e.g. the daily budget is
        spent), ``acquire`` raises ``QuotaExhaustedError`` instead of blocking for hours.
        """
        self._max_wait_s = max_wait_s
        self._limits = dict(limits)
        self._clock = clock
        self._sleep = sleep
        self._events: deque[tuple[float, float]] = deque()
        self._lock = threading.Lock()
        self.total_weight = 0.0

    def preload(self, ts: float, weight: float) -> None:
        """Account for a request made earlier (e.g. by another process, from a ledger)."""
        with self._lock:
            self._events.append((ts, weight))

    def _used(self, now: float, window: float) -> float:
        return sum(w for t, w in self._events if t > now - window)

    def acquire(self, weight: float) -> None:
        """Block until ``weight`` can be spent without breaking any window's limit."""
        for window, limit in self._limits.items():
            if weight > limit:
                raise ValueError(f"weight {weight} exceeds the {window}s limit {limit}")
        with self._lock:
            while True:
                now = self._clock()
                horizon = max(self._limits)
                while self._events and self._events[0][0] <= now - horizon:
                    self._events.popleft()
                waits = []
                for window, limit in self._limits.items():
                    if self._used(now, window) + weight > limit:
                        # wait until enough of the oldest events in this window expire
                        need = self._used(now, window) + weight - limit
                        freed = 0.0
                        for t, w in self._events:
                            if t <= now - window:
                                continue
                            freed += w
                            if freed >= need:
                                waits.append(t + window - now)
                                break
                if not waits:
                    self._events.append((now, weight))
                    self.total_weight += weight
                    return
                wait = max(*waits, 0.01)
                if wait > self._max_wait_s:
                    raise QuotaExhaustedError(
                        f"local budget spent: next request allowed in {wait / 3600:.1f} h"
                    )
                self._sleep(wait)
