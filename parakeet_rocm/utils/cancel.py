"""Cooperative cancellation utilities for graceful shutdown.

This module provides a singleton cancel event and signal handler installation
to enable graceful cancellation of long-running transcription operations.
"""

from __future__ import annotations

import logging
import signal
import threading

logger = logging.getLogger(__name__)

_cancel_event: threading.Event | None = None
_signal_handlers_installed: bool = False


def get_cancel_event() -> threading.Event:
    """Get or create the global cancellation event.

    Returns:
        A threading.Event that will be set when cancellation is requested.
    """
    global _cancel_event
    if _cancel_event is None:
        _cancel_event = threading.Event()
    return _cancel_event


def install_signal_handlers(cancel_event: threading.Event | None = None) -> None:
    """Install signal handlers for SIGINT and SIGTERM to set the cancel event.

    Args:
        cancel_event: Optional event to set on signal. If None, uses the global event.
    """
    global _signal_handlers_installed

    if _signal_handlers_installed:
        logger.warning("Signal handlers already installed, skipping")
        return

    event = cancel_event if cancel_event is not None else get_cancel_event()

    def signal_handler(signum: int, frame: object) -> None:
        """Handle SIGINT/SIGTERM by setting the cancel event.

        Args:
            signum: Signal number received.
            frame: Current stack frame (unused).
        """
        sig_name = signal.Signals(signum).name
        logger.info(f"Received {sig_name}, requesting graceful cancellation")
        event.set()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    _signal_handlers_installed = True
    logger.debug("Signal handlers installed for SIGINT and SIGTERM")


def reset_cancel_event() -> None:
    """Reset the global cancel event to allow reuse.

    This is primarily useful for testing scenarios where multiple
    cancellation cycles need to be tested in the same process.
    """
    global _cancel_event
    if _cancel_event is not None:
        _cancel_event.clear()
        logger.debug("Cancel event reset")


def is_cancelled(cancel_event: threading.Event | None = None) -> bool:
    """Check if cancellation has been requested.

    Args:
        cancel_event: Optional event to check. If None, uses the global event.

    Returns:
        True if cancellation has been requested, False otherwise.
    """
    event = cancel_event if cancel_event is not None else get_cancel_event()
    return event.is_set()
