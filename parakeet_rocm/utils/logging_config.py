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


def _apply_dependency_verbosity(*, nemo_level: str, transformers_level: str) -> None:
    """Apply NeMo and Transformers verbosity settings to env and live modules.

    Args:
        nemo_level: Desired NeMo verbosity level name.
        transformers_level: Desired Transformers verbosity level name.
    """
    os.environ["NEMO_LOG_LEVEL"] = nemo_level
    os.environ["TRANSFORMERS_VERBOSITY"] = transformers_level

    try:
        from nemo.utils import logging as nemo_logging

        nemo_logging.set_verbosity(getattr(logging, nemo_level, logging.ERROR))
    except Exception:
        pass

    try:
        from transformers.utils import logging as transformers_logging

        set_verbosity = getattr(
            transformers_logging,
            f"set_verbosity_{transformers_level.lower()}",
            None,
        )
        if callable(set_verbosity):
            set_verbosity()
    except Exception:
        pass


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
        _apply_dependency_verbosity(
            nemo_level="INFO",
            transformers_level="info",
        )
    elif quiet:
        # Suppress warnings and disable logging for dependencies
        warnings.filterwarnings("ignore")
        _apply_dependency_verbosity(
            nemo_level="ERROR",
            transformers_level="error",
        )

        # Disable tqdm progress bars in quiet mode
        try:
            import tqdm

            tqdm.tqdm = partial(tqdm.tqdm, disable=True)  # type: ignore[attr-defined]
        except ImportError:  # pragma: no cover
            pass
    else:
        # Default: honor env overrides; otherwise keep dependencies quiet.
        _apply_dependency_verbosity(
            nemo_level=os.getenv("NEMO_LOG_LEVEL", "ERROR").upper(),
            transformers_level=os.getenv("TRANSFORMERS_VERBOSITY", "error").lower(),
        )

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
