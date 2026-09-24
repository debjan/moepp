"""Logger factory for consistent logging configuration."""

import logging
import sys

from .settings import DEFAULT_LOG_LEVEL


def get_logger(name: str) -> logging.Logger:
    """Get logger instance with consistent configuration.

    Args:
        name: Logger name

    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)


def configure_logging(level: str | None = None) -> None:
    """Configure root logging with standard format.

    Args:
        level: Logging level name (DEBUG, INFO, WARNING, ERROR)

    Removes existing root handlers first so repeated calls apply the new
    level and don't accumulate handlers.
    """
    log_level = level or DEFAULT_LOG_LEVEL

    root = logging.getLogger()
    for handler in root.handlers[:]:
        root.removeHandler(handler)
        handler.close()

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    )
    root.addHandler(handler)
    root.setLevel(getattr(logging, log_level.upper()))
