"""Input validation layer for WebUI.

This package provides comprehensive input validation using Pydantic
schemas and custom validators for file uploads, configuration parameters,
and user inputs.
"""

from __future__ import annotations

__all__ = [
    "TranscriptionConfig",
    "FileUploadConfig",
    "validate_audio_file",
    "validate_output_directory",
]


def __getattr__(name: str):  # type: ignore[no-untyped-def]
    """Lazy import to avoid loading dependencies until needed.

    Args:
        name: Attribute name to import.

    Returns:
        Requested module attribute.

    Raises:
        AttributeError: If attribute name not found.
    """
    if name == "TranscriptionConfig":
        from parakeet_rocm.webui.validation.schemas import TranscriptionConfig

        return TranscriptionConfig
    if name == "FileUploadConfig":
        from parakeet_rocm.webui.validation.schemas import FileUploadConfig

        return FileUploadConfig
    if name == "validate_audio_file":
        from parakeet_rocm.webui.validation.file_validator import validate_audio_file

        return validate_audio_file
    if name == "validate_output_directory":
        from parakeet_rocm.webui.validation.file_validator import (
            validate_output_directory,
        )

        return validate_output_directory
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
