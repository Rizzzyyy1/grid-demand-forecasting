"""structlog configuration: human-readable console logs locally, JSON when ``json=True``."""

from __future__ import annotations

import logging

import structlog


def configure_logging(level: str = "INFO", json: bool = False) -> None:
    """Configure structlog once per process."""
    renderer: structlog.types.Processor = (
        structlog.processors.JSONRenderer() if json else structlog.dev.ConsoleRenderer()
    )
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.getLevelName(level)),
        cache_logger_on_first_use=True,
    )
