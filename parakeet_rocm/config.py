"""Configuration dataclasses for transcription pipeline.

This module defines configuration objects that group related settings,
reducing parameter explosion and improving Interface Segregation compliance.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from parakeet_rocm.utils.constant import DEFAULT_BATCH_SIZE, DEFAULT_CHUNK_LEN_SEC


@dataclass
class TranscriptionConfig:
    """Groups transcription-related settings.

    Attributes:
        batch_size: Number of segments processed per batch.
        chunk_len_sec: Length of each chunk in seconds.
        overlap_duration: Overlap between chunks in seconds.
        word_timestamps: Request word-level timestamps from the model.
        merge_strategy: Strategy for merging timestamps (``"lcs"`` or ``"contiguous"``).

    """

    batch_size: int = DEFAULT_BATCH_SIZE
    chunk_len_sec: int = DEFAULT_CHUNK_LEN_SEC
    overlap_duration: int = 15
    word_timestamps: bool = False
    merge_strategy: str = "lcs"


@dataclass
class StabilizationConfig:
    """Groups stable-ts refinement settings.

    Attributes:
        enabled: Refine word timestamps using stable-ts when ``True``.
        demucs: Enable Demucs denoising during stabilization.
        vad: Enable voice activity detection during stabilization.
        vad_threshold: VAD probability threshold when ``vad`` is enabled.

    """

    enabled: bool = False
    demucs: bool = False
    vad: bool = False
    vad_threshold: float = 0.35


@dataclass
class OutputConfig:
    """Groups output-related settings.

    Attributes:
        output_dir: Directory to store output files.
        output_format: Desired output format extension.
        output_template: Filename template for outputs.
        overwrite: Overwrite existing files when ``True``.
        highlight_words: Highlight words in output when supported.

    """

    output_dir: Path
    output_format: str
    output_template: str
    overwrite: bool = False
    highlight_words: bool = False


@dataclass
class UIConfig:
    """Groups UI and logging settings.

    Attributes:
        verbose: Enable detailed diagnostic output.
        quiet: Suppress non-error output.
        no_progress: Disable progress bars.

    """

    verbose: bool = False
    quiet: bool = False
    no_progress: bool = False
