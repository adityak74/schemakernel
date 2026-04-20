import logging
import os
import sys
from typing import Any

import structlog

def get_log_level() -> int:
    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    return getattr(logging, level_name, logging.INFO)

def setup_logging():
    """Configure structlog for production and development."""
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.CallsiteParameterAdder(
            [
                structlog.processors.CallsiteParameter.FILENAME,
                structlog.processors.CallsiteParameter.FUNC_NAME,
                structlog.processors.CallsiteParameter.LINENO,
            ]
        ),
    ]

    # Check if we are in a TTY (development) or not (production/piped)
    if sys.stderr.isatty():
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer()
        ]
    else:
        processors = shared_processors + [
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ]

    structlog.configure(
        processors=processors,
        logger_factory=structlog.PrintLoggerFactory(),
        wrapper_class=structlog.make_filtering_bound_logger(get_log_level()),
        cache_logger_on_first_use=True,
    )

def get_logger(name: str) -> Any:
    """Return a structlog logger."""
    return structlog.get_logger(name)
