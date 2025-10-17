"""UI pages for WebUI.

This package contains page-level UI components that compose
smaller components into complete application pages.
"""

from __future__ import annotations

__all__ = ["MainPage"]


def __getattr__(name: str):  # type: ignore[no-untyped-def]
    """Lazy import to avoid loading Gradio until needed.

    Args:
        name: Attribute name to import.

    Returns:
        Requested module attribute.

    Raises:
        AttributeError: If attribute name not found.
    """
    if name == "MainPage":
        from parakeet_rocm.webui.ui.pages.main import MainPage

        return MainPage
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
