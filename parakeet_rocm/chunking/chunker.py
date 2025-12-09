"""Sliding-window chunker for long-audio transcription.

This module provides utilities to split long mono waveforms into overlapping
windows and later restore global timestamps by offsetting NeMo hypotheses.
Further merge helpers will be added in follow-up iterations.

The logic is intentionally kept free of any NeMo or torch imports so that it
can be reused for offline testing without GPU dependencies.
"""

from __future__ import annotations

import numpy as np

__all__ = [
    "segment_waveform",
]


def segment_waveform(
    wav: np.ndarray,
    sr: int,
    chunk_len_sec: int,
    overlap_sec: int = 0,
) -> list[tuple[np.ndarray, float]]:
    """Split a mono waveform into overlapping time-windowed segments.

    Parameters:
        wav (np.ndarray): 1-D float32 mono waveform.
        sr (int): Sample rate in Hz.
        chunk_len_sec (int): Window length in seconds. If <= 0 the entire signal
            is returned as a single segment.
        overlap_sec (int, optional): Overlap between successive windows in
            seconds. Must be >= 0 and less than chunk_len_sec. Defaults to 0.

    Returns:
        list[tuple[np.ndarray, float]]: List of (segment, offset_sec) tuples
            where segment is a 1-D NumPy array for the window and offset_sec is
            the start time of that segment in seconds relative to the original
            waveform.

    Raises:
        ValueError: If overlap_sec is negative or overlap_sec >= chunk_len_sec.
    """
    if chunk_len_sec <= 0 or wav.size == 0:
        return [(wav, 0.0)]

    if overlap_sec < 0:
        raise ValueError("overlap_sec must be >= 0")
    if overlap_sec >= chunk_len_sec:
        raise ValueError("overlap_sec must be < chunk_len_sec")

    window_samples = int(chunk_len_sec * sr)
    step_samples = int(max(chunk_len_sec - overlap_sec, 1) * sr)

    segments: list[tuple[np.ndarray, float]] = []
    for start in range(0, len(wav), step_samples):
        seg = wav[start : start + window_samples]
        if seg.size == 0:
            break
        offset_sec = start / sr
        segments.append((seg, offset_sec))
        if seg.size < window_samples:
            # reached tail; avoid duplicate empty segment due to range()
            break
    return segments
