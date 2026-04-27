# app/logger.py
import logging
import sys
import structlog
from app.config import settings


def setup_logging() -> None:
    """
    Configure structlog for the entire application.
    Call this once at startup — in the lifespan function in main.py.

    Two modes:
    - console: human-readable colored output (development)
    - json: machine-readable JSON (production)
    """

    # Shared processors run on EVERY log event regardless of format.
    # Think of processors as a pipeline — each one transforms the log event
    # and passes it to the next.
    shared_processors = [
        # Adds the log level (INFO, ERROR, etc.) to every event
        structlog.stdlib.add_log_level,

        # Adds a timestamp in ISO format to every event
        structlog.processors.TimeStamper(fmt="iso"),

        # If you log an exception, this adds the full traceback
        structlog.processors.StackInfoRenderer(),
    ]

    if settings.log_format == "json":
        # Production: output clean JSON
        # Each log line is a valid JSON object — easy to parse programmatically
        processors = shared_processors + [
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer()
        ]
    else:
        # Development: output colored, human-readable logs
        # ConsoleRenderer adds colors and aligns fields nicely
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(colors=True)
        ]

    structlog.configure(
        processors=processors,
        # context_var_cls: allows passing context (like request_id) that
        # automatically appears in all logs within that context
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Also configure Python's standard logging to use structlog
    # Some libraries (like uvicorn) use standard logging — this makes them
    # consistent with our structured format
    log_level = getattr(logging, settings.log_level, logging.INFO)
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )


def get_logger(name: str = __name__):
    """
    Get a logger instance.
    Usage: logger = get_logger(__name__)
    The __name__ automatically becomes the module path, e.g. "app.agents.search"
    This tells you exactly which file produced each log line.
    """
    return structlog.get_logger(name)
