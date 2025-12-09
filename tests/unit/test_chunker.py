"""Unit tests for the waveform chunking utility.

These tests validate basic segmentation, input validation, and full-signal
handling for `segment_waveform`.
"""

import numpy as np
import pytest

from parakeet_rocm.chunking.chunker import segment_waveform


def test_segment_waveform_basic() -> None:
    """Regular overlapping chunks should be produced at correct offsets."""
    wav = np.arange(10, dtype=np.float32)
    segs = segment_waveform(wav, sr=1, chunk_len_sec=4, overlap_sec=2)
    assert segs[0][1] == 0.0
    assert segs[1][1] == 2.0
    assert len(segs) == 5


def test_segment_waveform_invalid_overlap() -> None:
    """Invalid overlap values should raise ``ValueError``."""
    wav = np.zeros(1, dtype=np.float32)
    with pytest.raises(ValueError):
        segment_waveform(wav, sr=1, chunk_len_sec=2, overlap_sec=2)
    with pytest.raises(ValueError):
        segment_waveform(wav, sr=1, chunk_len_sec=2, overlap_sec=-1)


def test_segment_waveform_full_signal() -> None:
    """Zero chunk length should return the full signal as one segment."""
    wav = np.arange(3, dtype=np.float32)
    segs = segment_waveform(wav, sr=1, chunk_len_sec=0)
    assert segs == [(wav, 0.0)]


def test_segment_waveform_exact_multiple() -> None:
    """Audio length exactly divisible by chunk size should loop naturally."""
    # 8 samples, chunk_len=4, step=4 -> exactly 2 chunks, no tail
    wav = np.arange(8, dtype=np.float32)
    segs = segment_waveform(wav, sr=1, chunk_len_sec=4, overlap_sec=0)
    assert len(segs) == 2
    assert segs[0][1] == 0.0
    assert segs[1][1] == 4.0
    assert segs[0][0].size == 4
    assert segs[1][0].size == 4


def test_segment_waveform_empty_audio() -> None:
    """Empty audio should return single empty segment."""
    wav = np.array([], dtype=np.float32)
    segs = segment_waveform(wav, sr=1, chunk_len_sec=10, overlap_sec=0)
    assert len(segs) == 1
    assert segs[0][0].size == 0
    assert segs[0][1] == 0.0
