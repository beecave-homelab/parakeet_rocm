"""Centralized logging configuration for Parakeet-NEMO ASR.

This module provides consistent logging setup across CLI, WebUI,
and background services. Configuration respects environment variables
and provides sensible defaults for production and development.
"""

from __future__ import annotations

import logging
import os
import sys
import warnings
from functools import partial
from typing import Literal

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


def _configure_third_party_log_levels(*, log_level: int) -> None:
    """Set explicit levels for noisy third-party loggers.

    Args:
        log_level: Effective root log level chosen for the application.
    """
    del log_level
    # Keep multipart parser internals from flooding --debug output.
    logging.getLogger("python_multipart").setLevel(logging.WARNING)
    logging.getLogger("python_multipart.multipart").setLevel(logging.WARNING)
    # Alias used by some multipart implementations.
    logging.getLogger("multipart").setLevel(logging.WARNING)


def configure_logging(
    *,
    level: LogLevel | None = None,
    verbose: bool = False,
    quiet: bool = False,
    format_string: str | None = None,
) -> None:
    """Configure centralized logging for the application.

    Sets up Python logging, NeMo logging, and Transformers verbosity
    based on the provided configuration. This should be called once
    at application startup (CLI entry or WebUI launch).

    Args:
        level: Explicit log level (overrides verbose/quiet).
        verbose: Enable verbose logging (DEBUG level + dependency logs).
        quiet: Suppress all non-critical logs and progress bars.
        format_string: Custom log format (uses default if None).

    Examples:
        >>> # CLI verbose mode
        >>> configure_logging(verbose=True)

        >>> # WebUI debug mode
        >>> configure_logging(level="DEBUG")

        >>> # Production quiet mode
        >>> configure_logging(quiet=True)
    """
    # Determine effective log level
    if level is not None:
        log_level = getattr(logging, level.upper())
    elif verbose:
        log_level = logging.DEBUG
    elif quiet:
        log_level = logging.CRITICAL
    else:
        log_level = logging.INFO

    # Default format with timestamp
    if format_string is None:
        format_string = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Configure Python logging
    logging.basicConfig(
        level=log_level,
        format=format_string,
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
        force=True,  # Reconfigure even if already configured
    )
    _configure_third_party_log_levels(log_level=log_level)

    # Configure heavy dependencies (NeMo, Transformers)
    if verbose:
        os.environ["NEMO_LOG_LEVEL"] = "INFO"
        os.environ["TRANSFORMERS_VERBOSITY"] = "info"
    elif quiet:
        # Suppress warnings and disable logging for dependencies
        warnings.filterwarnings("ignore")
        os.environ.setdefault("NEMO_LOG_LEVEL", "ERROR")
        os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")

        # Disable tqdm progress bars in quiet mode
        try:
            import tqdm

            tqdm.tqdm = partial(tqdm.tqdm, disable=True)  # type: ignore[attr-defined]
        except ImportError:  # pragma: no cover
            pass
    else:
        # Default: minimal NeMo/Transformers logs
        os.environ.setdefault("NEMO_LOG_LEVEL", "WARNING")
        os.environ.setdefault("TRANSFORMERS_VERBOSITY", "warning")

    # Log the configuration (only if not in quiet mode)
    if not quiet:
        logger = logging.getLogger(__name__)
        logger.debug(f"Logging configured: level={logging.getLevelName(log_level)}")


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the given name.

    Args:
        name: Logger name (typically __name__ of calling module).

    Returns:
        Configured logger instance.

    Examples:
        >>> logger = get_logger(__name__)
        >>> logger.info("Processing started")
    """
    return logging.getLogger(name)
