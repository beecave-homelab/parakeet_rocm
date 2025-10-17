"""Pydantic validation schemas for WebUI.

Provides type-safe configuration schemas with comprehensive validation
for transcription parameters and file uploads.
"""

from __future__ import annotations

import pathlib
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from parakeet_rocm.utils.constant import (
    DEFAULT_BATCH_SIZE,
    DEFAULT_CHUNK_LEN_SEC,
    PARAKEET_MODEL_NAME,
)


class TranscriptionConfig(BaseModel):
    """Configuration schema for transcription jobs.

    Validates all transcription parameters with sensible defaults
    and clear error messages for invalid inputs.

    Attributes:
        model_name: Model name or path for transcription.
        output_dir: Directory to save output files.
        output_format: Output file format (txt, srt, vtt, json).
        batch_size: Number of samples per batch (1-128).
        chunk_len_sec: Audio chunk length in seconds (>0).
        word_timestamps: Enable word-level timestamps.
        stabilize: Enable stable-ts timestamp refinement.
        vad: Enable voice activity detection.
        demucs: Enable Demucs audio source separation.
        vad_threshold: VAD threshold (0.0-1.0).
        overwrite: Overwrite existing output files.
        fp16: Use FP16 precision.
        fp32: Use FP32 precision.

    Examples:
        >>> config = TranscriptionConfig()
        >>> config.model_name
        'nvidia/parakeet-ctc-1.1b'

        >>> config = TranscriptionConfig(batch_size=16, word_timestamps=True)
        >>> config.batch_size
        16
    """

    model_name: str = Field(
        default=PARAKEET_MODEL_NAME,
        description="Model name or path for transcription",
    )
    output_dir: pathlib.Path = Field(
        default_factory=lambda: pathlib.Path("./output"),
        description="Directory to save output files",
    )
    output_format: Literal["txt", "srt", "vtt", "json"] = Field(
        default="srt",
        description="Output file format",
    )
    batch_size: int = Field(
        default=DEFAULT_BATCH_SIZE,
        ge=1,
        le=128,
        description="Number of samples per batch",
    )
    chunk_len_sec: int = Field(
        default=DEFAULT_CHUNK_LEN_SEC,
        ge=1,
        description="Audio chunk length in seconds",
    )
    word_timestamps: bool = Field(
        default=False,
        description="Enable word-level timestamps",
    )
    stabilize: bool = Field(
        default=False,
        description="Enable stable-ts timestamp refinement",
    )
    vad: bool = Field(
        default=False,
        description="Enable voice activity detection",
    )
    demucs: bool = Field(
        default=False,
        description="Enable Demucs audio source separation",
    )
    vad_threshold: float = Field(
        default=0.35,
        ge=0.0,
        le=1.0,
        description="VAD threshold (0.0-1.0)",
    )
    overwrite: bool = Field(
        default=False,
        description="Overwrite existing output files",
    )
    fp16: bool = Field(
        default=True,
        description="Use FP16 precision",
    )
    fp32: bool = Field(
        default=False,
        description="Use FP32 precision",
    )

    @model_validator(mode="after")
    def validate_precision_flags(self) -> TranscriptionConfig:
        """Ensure exactly one precision flag is set.

        If both fp16 and fp32 are True, prefer fp16.
        If both are False, default to fp16.

        Returns:
            Self with corrected precision flags.
        """
        if self.fp16 and self.fp32:
            # Prefer fp16 when both are set
            self.fp32 = False
        elif not self.fp16 and not self.fp32:
            # Default to fp16 when neither is set
            self.fp16 = True

        return self


class FileUploadConfig(BaseModel):
    """Configuration schema for file uploads.

    Validates uploaded files with support for path conversion
    and size limits.

    Attributes:
        files: List of file paths to process.
        max_file_size_mb: Maximum file size in MB (optional).

    Examples:
        >>> config = FileUploadConfig(files=["/path/to/audio.wav"])
        >>> len(config.files)
        1

        >>> config = FileUploadConfig(
        ...     files=["audio1.wav", "audio2.wav"],
        ...     max_file_size_mb=500
        ... )
        >>> config.max_file_size_mb
        500
    """

    files: list[pathlib.Path] = Field(
        ...,
        min_length=1,
        description="List of file paths to process",
    )
    max_file_size_mb: int | None = Field(
        default=None,
        ge=1,
        description="Maximum file size in MB",
    )

    @field_validator("files", mode="before")
    @classmethod
    def convert_to_paths(cls, value: list[str | pathlib.Path]) -> list[pathlib.Path]:
        """Convert string paths to pathlib.Path objects.

        Args:
            value: List of file paths (strings or Path objects).

        Returns:
            List of Path objects.
        """
        return [pathlib.Path(f) if isinstance(f, str) else f for f in value]
