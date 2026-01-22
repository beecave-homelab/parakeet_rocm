"""Core business logic for WebUI.

This package contains the core business logic components:
- Job management and orchestration
- Session state management
- Result handling and processing
"""

from __future__ import annotations

from typing import TYPE_CHECKING

__all__ = ["JobManager", "SessionManager", "TranscriptionJob", "JobStatus"]

if TYPE_CHECKING:
    from parakeet_rocm.webui.core.job_manager import JobManager, JobStatus, TranscriptionJob
    from parakeet_rocm.webui.core.session import SessionManager


def __getattr__(name: str) -> object:  # type: ignore[no-untyped-def]
    """Lazy import to avoid loading dependencies until needed.

    Args:
        name: Attribute name to import.

    Returns:
        Requested module attribute.

    Raises:
        AttributeError: If attribute name not found.
    """
    if name == "JobManager":
        from parakeet_rocm.webui.core.job_manager import JobManager

        return JobManager
    if name == "SessionManager":
        from parakeet_rocm.webui.core.session import SessionManager

        return SessionManager
    if name == "TranscriptionJob":
        from parakeet_rocm.webui.core.job_manager import TranscriptionJob

        return TranscriptionJob
    if name == "JobStatus":
        from parakeet_rocm.webui.core.job_manager import JobStatus

        return JobStatus
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
