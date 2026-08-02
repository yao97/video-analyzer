"""
Structured logging configuration using structlog.
Outputs JSON-formatted logs with request_id, job_id, and other contextual fields.
Resolves the "no structured logging" issue from Bug #6.
"""
from __future__ import annotations

import logging
import sys

import structlog


def configure_logging(debug: bool = False) -> None:
    """Configure structlog for JSON structured logging."""

    # Configure standard library logging to route through structlog
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.DEBUG if debug else logging.INFO,
    )

    timestamper = structlog.processors.TimeStamper(fmt="iso")

    structlog.configure(
        processors=[
            # Merge context variables (request_id, job_id, etc.)
            structlog.contextvars.merge_contextvars,
            # Add log level
            structlog.stdlib.add_log_level,
            # Add timestamp
            timestamper,
            # Stack info for exceptions
            structlog.processors.StackInfoRenderer(),
            # Exception formatting
            structlog.processors.format_exc_info,
            # JSON output
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.DEBUG if debug else logging.INFO
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = "app") -> structlog.stdlib.BoundLogger:
    """Get a structured logger instance."""
    return structlog.get_logger(name)
