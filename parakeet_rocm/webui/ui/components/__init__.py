"""Reusable UI components for WebUI.

This package contains small, focused UI components that can be
composed into larger pages. Each component is self-contained and testable.
"""

from __future__ import annotations

__all__ = [
    "FileUploader",
    "ConfigPanel",
    "ProgressTracker",
    "ResultViewer",
]


def __getattr__(name: str):  # type: ignore[no-untyped-def]
    """Lazy import to avoid loading Gradio until needed.

    Args:
        name: Attribute name to import.

    Returns:
        Requested module attribute.

    Raises:
        AttributeError: If attribute name not found.
    """
    if name == "FileUploader":
        from parakeet_rocm.webui.ui.components.file_uploader import FileUploader

        return FileUploader
    if name == "ConfigPanel":
        from parakeet_rocm.webui.ui.components.config_panel import ConfigPanel

        return ConfigPanel
    if name == "ProgressTracker":
        from parakeet_rocm.webui.ui.components.progress_tracker import ProgressTracker

        return ProgressTracker
    if name == "ResultViewer":
        from parakeet_rocm.webui.ui.components.result_viewer import ResultViewer

        return ResultViewer
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
