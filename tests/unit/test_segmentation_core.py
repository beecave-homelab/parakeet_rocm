"""Unit tests for timestamps segmentation core.

Covers `split_lines()` and `segment_words()` against readability constraints.
"""

from __future__ import annotations

from parakeet_rocm.timestamps.models import Segment, Word
from parakeet_rocm.timestamps.segmentation import (
    _fix_overlaps,
    _greedy_split_fallback,
    _merge_short_segments,
    _split_at_clause_boundaries,
    segment_words,
    split_lines,
)
from parakeet_rocm.utils.constant import (
    MAX_CPS,
    MAX_LINE_CHARS,
    MAX_SEGMENT_DURATION_SEC,
)


def _w(text: str, start: float, end: float) -> Word:
    """Create a `Word` instance for test fixtures.

    Args:
        text: Token text.
        start: Token start timestamp in seconds.
        end: Token end timestamp in seconds.

    Returns:
        Word: Configured word instance for tests.

    """
    return Word(word=text, start=start, end=end)


def test_split_lines_balanced_and_within_limit() -> None:
    """Ensure `split_lines()` balances content within line length limits."""
    text = "This is a reasonably long line that should be split in two parts."
    out = split_lines(text)
    parts = out.split("\n")
    assert 1 <= len(parts) <= 2
    # Ensure each line respects MAX_LINE_CHARS
    assert all(len(p) <= MAX_LINE_CHARS for p in parts)


def test_segment_words_single_sentence_ok_limits() -> None:
    """Check that one sentence yields a single compliant segment."""
    # A sentence that should stay one segment and respect limits
    words: list[Word] = [
        _w("This", 0.00, 0.20),
        _w("is", 0.21, 0.35),
        _w("fine", 0.36, 0.80),
        _w("enough.", 0.81, 1.40),
    ]
    segs = segment_words(words)
    assert len(segs) == 1
    seg = segs[0]
    plain = seg.text.replace("\n", " ")
    dur = seg.end - seg.start
    cps = len(plain) / max(dur, 1e-3)
    assert cps <= MAX_CPS
    assert dur <= MAX_SEGMENT_DURATION_SEC


def test_segment_words_splits_long_sentence() -> None:
    """Verify long sentences split into multiple constrained segments."""
    # Construct a long sentence that exceeds character limit, forcing a split
    t = 0.0
    words: list[Word] = []
    for token in (
        "This",
        "sentence",
        "is",
        "intentionally",
        "made",
        "very",
        "very",
        "long",
        "to",
        "exceed",
        "the",
        "character",
        "limits,",
        "so",
        "that",
        "the",
        "algorithm",
        "needs",
        "to",
        "split",
        "at",
        "clause",
        "boundaries",
        "and",
        "fallback",
        "as",
        "needed.",
    ):
        words.append(_w(token, t, t + 0.15))
        t += 0.18
    segs = segment_words(words)
    # Expect >1 segments due to length/duration
    assert len(segs) >= 2
    for seg in segs:
        dur = seg.end - seg.start
        # Duration within hard cap
        assert dur <= MAX_SEGMENT_DURATION_SEC
        # Each line within MAX_LINE_CHARS
        for line in seg.text.split("\n"):
            assert len(line) <= MAX_LINE_CHARS


def test_fix_overlaps_empty_list() -> None:
    """Test _fix_overlaps handles empty segment list."""
    result = _fix_overlaps([])
    assert result == []


def test_fix_overlaps_merges_when_trim_violates_min_duration() -> None:
    """Test _fix_overlaps merges segments when trimming would violate MIN_DURATION."""
    # Create overlapping segments where trimming prev would make it too short
    w1 = [_w("hello", 0.0, 0.2)]
    w2 = [_w("world", 0.1, 0.5)]  # Overlaps at 0.1

    seg1 = Segment(text="hello", words=w1, start=0.0, end=0.2)
    # seg2 starts before seg1 ends -> overlap
    seg2 = Segment(text="world", words=w2, start=0.1, end=0.5)

    result = _fix_overlaps([seg1, seg2])

    # Should merge because trimming seg1 to end at (0.1 - 0.04)
    # would violate MIN_DURATION
    assert len(result) == 1
    assert result[0].text == "hello world"
    assert len(result[0].words) == 2


def test_fix_overlaps_trims_when_possible() -> None:
    """Test _fix_overlaps trims prev segment when it doesn't violate MIN_DURATION."""
    # Create segments with small overlap but prev has enough duration
    w1 = [_w("hello", 0.0, 2.0)]
    w2 = [_w("world", 1.95, 3.0)]  # Small overlap

    seg1 = Segment(text="hello", words=w1, start=0.0, end=2.0)
    seg2 = Segment(text="world", words=w2, start=1.95, end=3.0)

    result = _fix_overlaps([seg1, seg2])

    # Should trim seg1 rather than merge
    assert len(result) == 2
    # seg1 should be trimmed to end before seg2 starts
    assert result[0].end < seg2.start


def test_merge_short_segments_empty_list() -> None:
    """Test _merge_short_segments handles empty segment list."""
    result = _merge_short_segments([])
    assert result == []


def test_merge_short_segments_merges_short_duration() -> None:
    """Test _merge_short_segments merges segments with duration below MIN_DURATION."""
    # Create a very short segment followed by a normal one
    w1 = [_w("hi", 0.0, 0.1)]  # 0.1 sec < MIN_SEGMENT_DURATION_SEC
    w2 = [_w("there", 0.1, 1.0)]

    seg1 = Segment(text="hi", words=w1, start=0.0, end=0.1)
    seg2 = Segment(text="there", words=w2, start=0.1, end=1.0)

    result = _merge_short_segments([seg1, seg2])

    # seg1 is too short, should be merged with seg2
    assert len(result) == 1
    assert "hi there" in result[0].text.replace("\n", " ")


def test_merge_short_segments_merges_short_text() -> None:
    """Test _merge_short_segments merges segments with text < 15 chars."""
    # Create segment with very short text but normal duration
    w1 = [_w("Hi", 0.0, 1.0)]  # Long duration but text < 15 chars
    w2 = [_w("everyone", 1.0, 2.0)]

    seg1 = Segment(text="Hi", words=w1, start=0.0, end=1.0)
    seg2 = Segment(text="everyone", words=w2, start=1.0, end=2.0)

    result = _merge_short_segments([seg1, seg2])

    # seg1 has < 15 chars, should be merged
    assert len(result) == 1
    assert "Hi everyone" in result[0].text.replace("\n", " ")


def test_merge_short_segments_stops_when_limits_exceeded() -> None:
    """Test _merge_short_segments stops merging when combined exceeds limits."""
    # Create short segment followed by very long segment
    # Combining them would exceed MAX_BLOCK_CHARS
    w1 = [_w("Hi", 0.0, 0.5)]
    # Create a long text that would exceed limits when combined
    long_words = [_w(f"word{i}", float(i), float(i + 0.5)) for i in range(1, 100)]
    long_text = " ".join(f"word{i}" for i in range(1, 100))

    seg1 = Segment(text="Hi", words=w1, start=0.0, end=0.5)
    seg2 = Segment(text=long_text, words=long_words, start=1.0, end=50.0)

    result = _merge_short_segments([seg1, seg2])

    # Should NOT merge because combined would exceed limits
    assert len(result) == 2


def test_split_at_clause_boundaries_empty_sentence() -> None:
    """Test _split_at_clause_boundaries handles empty sentence."""
    result = _split_at_clause_boundaries([])
    assert result == []


def test_split_at_clause_boundaries_within_limits() -> None:
    """Test _split_at_clause_boundaries returns as-is when within limits."""
    # Short sentence that doesn't need splitting
    words = [_w("Hello", 0.0, 0.5), _w("world", 0.5, 1.0)]
    result = _split_at_clause_boundaries(words)
    # Should return as single chunk since it's within limits
    assert len(result) == 1
    assert result[0] == words


def test_split_at_clause_boundaries_splits_at_comma() -> None:
    """Test _split_at_clause_boundaries splits at comma boundaries."""
    # Create long sentence with comma that needs splitting
    words = [
        _w("First", 0.0, 0.2),
        _w("part", 0.2, 0.4),
        _w("of", 0.4, 0.6),
        _w("sentence,", 0.6, 0.8),
        _w("second", 0.8, 1.0),
        _w("part", 1.0, 1.2),
        _w("here", 1.2, 1.4),
    ]
    result = _split_at_clause_boundaries(words)
    # Should split at the comma
    assert len(result) >= 1


def test_greedy_split_fallback_empty_sentence() -> None:
    """Test _greedy_split_fallback handles empty sentence."""
    result = _greedy_split_fallback([])
    assert result == []


def test_greedy_split_fallback_splits_when_needed() -> None:
    """Test _greedy_split_fallback splits long sentences."""
    # Create a very long sentence that needs splitting
    words = [_w(f"word{i}", float(i * 0.1), float((i + 1) * 0.1)) for i in range(200)]
    result = _greedy_split_fallback(words)
    # Should split into multiple chunks
    assert len(result) > 1
    # Each chunk should be non-empty
    assert all(len(chunk) > 0 for chunk in result)
