"""Configuration presets for WebUI.

Provides predefined configuration presets for common transcription
use cases, allowing users to quickly select optimal settings.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass

from parakeet_rocm.utils.constant import (
    DEFAULT_BATCH_SIZE,
    DEFAULT_CHUNK_LEN_SEC,
    DEFAULT_DEMUCS,
    DEFAULT_STABILIZE,
    DEFAULT_VAD,
    DEFAULT_WORD_TIMESTAMPS,
)
from parakeet_rocm.webui.validation.schemas import TranscriptionConfig


@dataclass(frozen=True)
class Preset:
    """Configuration preset for a common use case.

    Attributes:
        name: Preset identifier.
        description: Human-readable description of the preset.
        config: Transcription configuration for this preset.

    Examples:
        >>> preset = Preset(
        ...     name="fast",
        ...     description="Fast transcription",
        ...     config=TranscriptionConfig(batch_size=16),
        ... )
        >>> preset.name
        'fast'
    """

    name: str
    description: str
    config: TranscriptionConfig


# Define preset configurations
PRESETS: dict[str, Preset] = {
    "default": Preset(
        name="default",
        description="Default settings from environment configuration",
        config=TranscriptionConfig(
            batch_size=DEFAULT_BATCH_SIZE,
            chunk_len_sec=DEFAULT_CHUNK_LEN_SEC,
            word_timestamps=DEFAULT_WORD_TIMESTAMPS,
            stabilize=DEFAULT_STABILIZE,
            vad=DEFAULT_VAD,
            demucs=DEFAULT_DEMUCS,
            fp16=True,
        ),
    ),
    "fast": Preset(
        name="fast",
        description="Optimized for speed - minimal processing",
        config=TranscriptionConfig(
            batch_size=16,
            chunk_len_sec=150,
            word_timestamps=False,
            stabilize=False,
            vad=False,
            demucs=False,
            fp16=True,
        ),
    ),
    "balanced": Preset(
        name="balanced",
        description="Good balance between speed and accuracy",
        config=TranscriptionConfig(
            batch_size=8,
            chunk_len_sec=150,
            word_timestamps=True,
            stabilize=False,
            vad=False,
            demucs=False,
            fp16=True,
        ),
    ),
    "high_quality": Preset(
        name="high_quality",
        description="Best accuracy with word-level timestamps and stabilization",
        config=TranscriptionConfig(
            batch_size=4,
            chunk_len_sec=150,
            word_timestamps=True,
            stabilize=True,
            vad=False,
            demucs=False,
            vad_threshold=0.35,
            fp16=True,
        ),
    ),
    "best": Preset(
        name="best",
        description="Maximum quality - all enhancements enabled (slowest)",
        config=TranscriptionConfig(
            batch_size=4,
            chunk_len_sec=150,
            word_timestamps=True,
            stabilize=True,
            vad=True,
            demucs=True,
            vad_threshold=0.35,
            fp16=True,
        ),
    ),
}


def get_preset(name: str) -> Preset:
    """Retrieve a preset by name.

    Returns a deep copy of the preset to ensure configuration
    independence between calls.

    Args:
        name: Preset identifier.

    Returns:
        Preset with independent configuration copy.

    Raises:
        KeyError: If preset name not found.

    Examples:
        >>> preset = get_preset("fast")
        >>> preset.name
        'fast'

        >>> preset = get_preset("nonexistent")
        Traceback (most recent call last):
            ...
        KeyError: 'nonexistent'
    """
    if name not in PRESETS:
        raise KeyError(f"Preset '{name}' not found. Available: {list(PRESETS.keys())}")

    # Return deep copy to ensure independence
    original = PRESETS[name]
    return Preset(
        name=original.name,
        description=original.description,
        config=copy.deepcopy(original.config),
    )
