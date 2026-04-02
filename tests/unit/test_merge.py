"""Unit tests for overlapping token merging utilities.

These tests cover both contiguous and LCS-based merging to ensure
chronological ordering and duplicate removal in overlapped regions.
"""

from __future__ import annotations

import pytest

from parakeet_rocm.chunking import (
    merge_longest_common_subsequence,
    merge_longest_contiguous,
)
from parakeet_rocm.timestamps.models import Word


def _make_overlap_samples() -> tuple[list[Word], list[Word]]:
    """Create two Word sequences that overlap and share duplicate tokens.

    The first sequence ``a`` contains ["Hello", "world", "this", "is"]
    with spans from 0.0s to 1.2s.
    The second sequence ``b`` starts inside ``a`` (at 0.6s) and contains
    ["this", "is", "a", "test"], producing an overlapping region of
    approximately 0.6 seconds.

    Returns:
        tuple[list[Word], list[Word]]: Pair ``(a, b)`` where ``b`` begins
            within ``a``, suitable for testing overlap-merge behavior.
    """
    a = [
        Word(word="Hello", start=0.0, end=0.3),
        Word(word="world", start=0.3, end=0.6),
        Word(word="this", start=0.6, end=0.9),
        Word(word="is", start=0.9, end=1.2),
    ]
    # Second chunk starts inside first (~0.6 s overlap)
    b = [
        Word(word="this", start=0.6, end=0.9),
        Word(word="is", start=0.9, end=1.2),
        Word(word="a", start=1.2, end=1.4),
        Word(word="test", start=1.4, end=1.6),
    ]
    return a, b


def test_merge_longest_contiguous() -> None:
    """Contiguous merge should preserve order and maintain monotonic timing."""
    a, b = _make_overlap_samples()
    merged = merge_longest_contiguous(a, b, overlap_duration=0.6)
    # Check that basic sequence ordering is chronological and no missing words
    words = [w.word for w in merged]
    assert words[0:2] == ["Hello", "world"]
    assert words[-2:] == ["a", "test"]
    # Ensure timeline monotonicity
    for prev, nxt in zip(merged, merged[1:]):
        assert prev.end <= nxt.start + 1e-6


def test_merge_longest_common_subsequence() -> None:
    """LCS merge should deduplicate overlap and keep natural order."""
    a, b = _make_overlap_samples()
    merged = merge_longest_common_subsequence(a, b, overlap_duration=0.6)
    words = [w.word for w in merged]
    assert words == ["Hello", "world", "this", "is", "a", "test"]
    # Ensure no duplicates
    assert len(words) == len(set(words)), "Duplicates found in merged words"


def test_merge_lcs_uses_robust_offset_with_repeated_tokens() -> None:
    """Repeated leading tokens should not force a wrong global shift.

    This reproduces an ambiguous overlap where the first possible LCS anchor is
    an outlier. The merge should use a robust offset estimate so the appended
    tail from chunk ``b`` remains close to chunk ``a`` timing.
    """
    a = [
        Word(word="uh", start=100.0, end=100.2),
        Word(word="uh", start=100.2, end=100.4),
        Word(word="done", start=100.4, end=100.6),
    ]
    b = [
        Word(word="uh", start=98.0, end=98.2),
        Word(word="uh", start=100.0, end=100.2),
        Word(word="done", start=100.2, end=100.4),
        Word(word="next", start=100.4, end=100.6),
    ]

    merged = merge_longest_common_subsequence(a, b, overlap_duration=1.0)

    words = [w.word for w in merged]
    assert words == ["uh", "uh", "done", "next"]
    # Correct alignment keeps "next" near the timeline continuation of chunk A.
    assert merged[-1].start == pytest.approx(100.6, abs=1e-3)
    assert merged[-1].end == pytest.approx(100.8, abs=1e-3)
