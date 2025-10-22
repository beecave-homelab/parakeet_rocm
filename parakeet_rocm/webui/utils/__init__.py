"""WebUI-specific utilities.

This package contains utility functions and classes specific to the
WebUI, including configuration presets and output formatters.
"""

from __future__ import annotations

__all__ = ["PRESETS", "get_preset"]


def __getattr__(name: str):  # type: ignore[no-untyped-def]
    """Lazy import to avoid loading dependencies until needed.

    Args:
        name: Attribute name to import.

    Returns:
        Requested module attribute.

    Raises:
        AttributeError: If attribute name not found.
    """
    if name == "PRESETS":
        from parakeet_rocm.webui.utils.presets import PRESETS

        return PRESETS
    if name == "get_preset":
        from parakeet_rocm.webui.utils.presets import get_preset

        return get_preset
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
