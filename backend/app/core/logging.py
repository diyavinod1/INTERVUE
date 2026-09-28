"""
Structured logging configuration.

We log meaningful lifecycle events (interview created, graph node executed,
question generated, provider failure, etc.) as structured key=value pairs so
they're greppable, but we never log API keys, passwords, full resumes, or
full answer text (only lengths / ids) to keep candidate data out of logs.
"""
import logging
import sys

from app.core.config import get_settings

_CONFIGURED = False


def configure_logging() -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return
    settings = get_settings()
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    root = logging.getLogger()
    root.setLevel(settings.log_level.upper())
    root.handlers = [handler]
    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    configure_logging()
    return logging.getLogger(name)
