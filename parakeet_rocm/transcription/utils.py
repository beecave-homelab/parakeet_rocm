"""Utility helpers for transcription operations."""

from __future__ import annotations

import warnings
from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # Import for type hints only to avoid heavy runtime import
    from nemo.collections.asr.models import ASRModel

from parakeet_rocm.chunking import segment_waveform
from parakeet_rocm.utils.audio_io import DEFAULT_SAMPLE_RATE, load_audio


def configure_environment(verbose: bool) -> None:
    """Configure logging verbosity for heavy dependencies.

    .. deprecated::
        Use :func:`parakeet_rocm.utils.logging_config.configure_logging` instead.

    Args:
        verbose: When ``True``, enable verbose logs for NeMo and Transformers.

    """
    # Delegate to centralized logging configuration
    from parakeet_rocm.utils.logging_config import configure_logging

    configure_logging(verbose=verbose)


def compute_total_segments(
    audio_files: Sequence[Path],
    chunk_len_sec: int,
    overlap_duration: int,
) -> int:
    """Return total number of segments for a list of audio files.

    Args:
        audio_files: Iterable of audio file paths to process.
        chunk_len_sec: Length of each chunk in seconds.
        overlap_duration: Overlap between chunks in seconds.

    Returns:
        The total number of segments across all files.

    """
    total_segments = 0
    for path in audio_files:
        wav, sr = load_audio(path, DEFAULT_SAMPLE_RATE)
        total_segments += len(
            segment_waveform(wav, sr, chunk_len_sec, overlap_duration)
        )
    return total_segments


def calc_time_stride(model: ASRModel, verbose: bool = False) -> float:
    """Return seconds-per-frame stride for timestamp conversion.

    Args:
        model (ASRModel): The ASR model whose encoder configuration is
            inspected.
        verbose (bool): Whether to emit warnings when heuristics fail.

    Returns:
        float: Seconds represented by a single encoder output frame.

    """
    window_stride: float | None = getattr(model.cfg.preprocessor, "window_stride", None)
    if window_stride is None and hasattr(model.cfg.preprocessor, "features"):
        window_stride = getattr(model.cfg.preprocessor.features, "window_stride", None)
    if window_stride is None and hasattr(model.cfg.preprocessor, "hop_length"):
        hop = getattr(model.cfg.preprocessor, "hop_length")
        sr = getattr(model.cfg.preprocessor, "sample_rate", 16000)
        window_stride = hop / sr
    if window_stride is None:
        window_stride = 0.01

    subsampling_factor = 1
    candidates = [
        (
            "conv_subsampling",
            lambda enc: (
                enc.conv_subsampling.get_stride()
                if hasattr(enc, "conv_subsampling")
                else None
            ),
        ),
        ("stride", lambda enc: getattr(enc, "stride", None)),
        ("subsampling_factor", lambda enc: getattr(enc, "subsampling_factor", None)),
        ("_stride", lambda enc: getattr(enc, "_stride", None)),
    ]
    enc = model.encoder
    for _name, getter in candidates:
        try:
            val = getter(enc)
        except Exception:  # pragma: no cover
            val = None
        if val is not None:
            subsampling_factor = val
            break

    if subsampling_factor == 1:
        cfg_val = getattr(model.cfg.encoder, "stride", None)
        if cfg_val is not None:
            subsampling_factor = cfg_val

    if isinstance(subsampling_factor, (list, tuple)):
        from math import prod  # pylint: disable=import-outside-toplevel

        subsampling_factor = int(prod(subsampling_factor))
    try:
        subsampling_factor = int(subsampling_factor)
    except Exception:  # pragma: no cover
        subsampling_factor = 1
        if verbose:
            warnings.warn(
                "Could not determine subsampling factor; defaulting to 1.",
            )

    return subsampling_factor * window_stride
