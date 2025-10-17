"""UI layer for WebUI.

This package contains presentation layer components:
- Pages (main transcription page, settings)
- Reusable UI components
- Theme and styling configuration
"""

from __future__ import annotations

__all__ = ["configure_theme"]


def __getattr__(name: str):  # type: ignore[no-untyped-def]
    """Lazy import to avoid loading Gradio until needed.

    Args:
        name: Attribute name to import.

    Returns:
        Requested module attribute.

    Raises:
        AttributeError: If attribute name not found.
    """
    if name == "configure_theme":
        from parakeet_rocm.webui.ui.theme import configure_theme

        return configure_theme
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
