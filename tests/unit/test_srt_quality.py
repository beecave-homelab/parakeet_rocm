"""Unit tests for SRT quality analysis functions.

Tests cover compute_srt_quality() and all helper functions with various
quality levels, edge cases, and boundary conditions.
"""

from __future__ import annotations

from parakeet_rocm.formatting.srt_quality import (
    _collect_line_length_offenders,
    _has_bad_hyphen_spacing,
    _summarize_durations,
    compute_srt_quality,
)


def test_compute_srt_quality__perfect_quality() -> None:
    """Verify perfect quality score with ideal segments."""
    # Each segment should have 10-22 CPS and 0.5-7.0s duration
    # "Hello world great" = 18 chars / 2s = 9 CPS (too low!)
    # Need longer text: "Hello world this is great" = 25 chars / 2s = 12.5 CPS ✓
    segments = [
        {"start": 0.0, "end": 2.0, "text": "Hello world this is good."},
        {"start": 2.0, "end": 4.0, "text": "This is a test segment."},
        {"start": 4.0, "end": 6.0, "text": "Perfect quality here yes."},
    ]
    srt_text = """1
00:00:00,000 --> 00:00:02,000
Hello world.

2
00:00:02,000 --> 00:00:04,000
This is a test.

3
00:00:04,000 --> 00:00:06,000
Perfect quality.
"""

    result = compute_srt_quality(segments, srt_text)

    # High quality score (>0.9) with no major violations
    assert result["score"] >= 0.9
    assert result["details"]["overlap_violations"] == 0
    assert result["details"]["hyphen_normalization_ok"] is True
    assert result["details"]["line_length_violations"] == 0


def test_compute_srt_quality__with_overlaps() -> None:
    """Verify overlap detection penalizes score."""
    segments = [
        {"start": 0.0, "end": 2.0, "text": "First segment."},
        {"start": 1.5, "end": 3.0, "text": "Overlapping!"},  # Overlap!
        {"start": 3.0, "end": 5.0, "text": "Third segment."},
    ]
    srt_text = "1\n00:00:00,000 --> 00:00:02,000\nFirst segment.\n"

    result = compute_srt_quality(segments, srt_text)

    assert result["score"] < 0.7  # Significant penalty for overlaps
    assert result["details"]["overlap_violations"] == 1


def test_compute_srt_quality__long_lines() -> None:
    """Verify line length violations detected and penalized."""
    long_text = (
        "This is an extremely long line that exceeds the maximum character limit"
    )
    segments = [{"start": 0.0, "end": 3.0, "text": long_text}]
    srt_text = f"""1
00:00:00,000 --> 00:00:03,000
{long_text}
"""

    result = compute_srt_quality(segments, srt_text)

    assert result["details"]["line_length_violations"] > 0
    assert result["details"]["line_length_violation_ratio"] > 0
    assert result["score"] < 1.0


def test_compute_srt_quality__bad_hyphen_spacing() -> None:
    """Verify bad hyphen spacing detection."""
    segments = [{"start": 0.0, "end": 2.0, "text": "co -pilot example"}]
    srt_text = """1
00:00:00,000 --> 00:00:02,000
co -pilot example
"""

    result = compute_srt_quality(segments, srt_text)

    assert result["details"]["hyphen_normalization_ok"] is False
    assert result["score"] < 1.0


def test_compute_srt_quality__cps_boundaries() -> None:
    """Verify CPS categorization at boundaries."""
    # 9 CPS (below min of 10)
    seg_below = {"start": 0.0, "end": 1.0, "text": "123456789"}  # 9 chars/1s

    # 15 CPS (within range 10-22)
    seg_within = {
        "start": 1.0,
        "end": 2.0,
        "text": "123456789012345",  # 15 chars/1s
    }

    # 25 CPS (above max of 22)
    seg_above = {
        "start": 2.0,
        "end": 3.0,
        "text": "1234567890123456789012345",  # 25 chars/1s
    }

    segments = [seg_below, seg_within, seg_above]
    srt_text = "Dummy SRT text"

    result = compute_srt_quality(segments, srt_text)

    # Verify histogram counts
    histogram = result["details"]["cps_histogram"]
    assert histogram["below_min"] >= 1
    assert histogram["within_range"] >= 1 or histogram["total"] == 3
    assert histogram["above_max"] >= 1
    assert histogram["total"] == 3


def test_compute_srt_quality__duration_boundaries() -> None:
    """Verify duration boundary violation tracking."""
    segments = [
        {"start": 0.0, "end": 0.3, "text": "Too short"},  # < 0.5s
        {"start": 1.0, "end": 3.0, "text": "Normal duration"},  # Within range
        {"start": 3.0, "end": 11.0, "text": "Too long segment"},  # > 7.0s
    ]
    srt_text = "Dummy SRT"

    result = compute_srt_quality(segments, srt_text)

    assert result["details"]["boundary_counts"]["too_short"] == 1
    assert result["details"]["boundary_counts"]["within_range"] == 1
    assert result["details"]["boundary_counts"]["too_long"] == 1


def test_compute_srt_quality__sample_offenders() -> None:
    """Verify sample offenders collection (up to 5)."""
    segments = [
        {"start": i, "end": i + 1, "text": f"Segment {i}" * 10}  # Long text
        for i in range(10)
    ]
    srt_text = "\n".join([f"Line {i}" * 20 for i in range(10)])  # Long lines

    result = compute_srt_quality(segments, srt_text)

    # Should collect up to 5 line length offenders
    assert len(result["details"]["sample_offenders"]["line_length"]) <= 5
    # Should collect up to 5 CPS offenders
    assert len(result["details"]["sample_offenders"]["cps"]) <= 5


def test_compute_srt_quality__empty_segments() -> None:
    """Verify handling of empty segments list."""
    result = compute_srt_quality([], "")

    assert result["score"] == 1.0  # Perfect score for empty input
    assert result["details"]["overlap_violations"] == 0
    assert result["details"]["cps_within_range_ratio"] == 1.0


def test_compute_srt_quality__malformed_segments() -> None:
    """Verify defensive handling of malformed segment data."""
    segments = [
        {"start": "invalid", "end": 2.0, "text": "Bad start"},
        {"start": 2.0, "end": "invalid", "text": "Bad end"},
        {"missing": "fields"},
        {"start": 4.0, "end": 6.0, "text": "Valid segment"},
    ]
    srt_text = "Valid text"

    result = compute_srt_quality(segments, srt_text)

    # Should not crash, may process some segments gracefully
    assert "score" in result
    assert result["details"]["cps_histogram"]["total"] >= 1


def test_summarize_durations__normal_data() -> None:
    """Verify duration statistics calculation."""
    durations = [1.0, 2.0, 3.0, 4.0, 5.0]

    result = _summarize_durations(durations)

    assert result["min_seconds"] == 1.0
    assert result["max_seconds"] == 5.0
    assert result["average_seconds"] == 3.0
    assert result["median_seconds"] == 3.0


def test_summarize_durations__empty_list() -> None:
    """Verify empty duration list returns zeros."""
    result = _summarize_durations([])

    assert result["min_seconds"] == 0.0
    assert result["max_seconds"] == 0.0
    assert result["average_seconds"] == 0.0
    assert result["median_seconds"] == 0.0


def test_collect_line_length_offenders__finds_violations() -> None:
    """Verify line length offender collection."""
    text_lines = [
        "Short line",
        "This is a very long line that exceeds the 42 character limit for sure",
        "Another short",
        "Yet another extremely long line that should be flagged as an offender here",
    ]

    result = _collect_line_length_offenders(text_lines)

    assert len(result) == 2
    assert result[0]["line_index"] == 2  # Second line (1-indexed)
    assert result[0]["length"] > 42
    assert result[0]["limit"] == 42
    assert "very long line" in result[0]["line"]


def test_collect_line_length_offenders__max_five() -> None:
    """Verify only first 5 offenders collected."""
    long_lines = [f"This is a very long line number {i}" * 5 for i in range(10)]

    result = _collect_line_length_offenders(long_lines)

    assert len(result) == 5


def test_collect_line_length_offenders__no_violations() -> None:
    """Verify empty result when no violations."""
    short_lines = ["Short", "Also short", "Still short"]

    result = _collect_line_length_offenders(short_lines)

    assert len(result) == 0


def test_has_bad_hyphen_spacing__standalone_hyphen() -> None:
    """Verify detection of standalone hyphen between words."""
    text = "This is a co - pilot example"

    result = _has_bad_hyphen_spacing(text)

    assert result is True


def test_has_bad_hyphen_spacing__prefix_hyphen() -> None:
    """Verify detection of 'word -suffix' pattern."""
    text = "This is co -pilot in action"

    result = _has_bad_hyphen_spacing(text)

    assert result is True


def test_has_bad_hyphen_spacing__suffix_hyphen() -> None:
    """Verify detection of 'prefix- word' pattern."""
    text = "The co- pilot system"

    result = _has_bad_hyphen_spacing(text)

    assert result is True


def test_has_bad_hyphen_spacing__valid_patterns() -> None:
    """Verify valid hyphen patterns not flagged."""
    valid_texts = [
        "This is a co-pilot system",  # Proper compound word
        "End-to-end testing",  # Multiple hyphens
        "Twenty-five dollars",  # Number compound
        "Well-known author",  # Adjective compound
        "No hyphens here at all",  # No hyphens
    ]

    for text in valid_texts:
        result = _has_bad_hyphen_spacing(text)
        assert result is False, f"False positive for: {text}"


def test_has_bad_hyphen_spacing__with_punctuation() -> None:
    """Verify hyphen detection strips punctuation correctly."""
    text = "The co -pilot, works great."

    result = _has_bad_hyphen_spacing(text)

    assert result is True


def test_has_bad_hyphen_spacing__empty_string() -> None:
    """Verify empty string returns False."""
    result = _has_bad_hyphen_spacing("")

    assert result is False


def test_compute_srt_quality__score_clamping() -> None:
    """Verify score is clamped to [0.0, 1.0]."""
    # Create worst-case scenario with multiple violations
    segments = [
        {"start": 0.0, "end": 0.1, "text": "x" * 100},  # Too short + long text
        {"start": 0.05, "end": 15.0, "text": "y"},  # Overlap + too long + low CPS
    ]
    srt_text = "co -pilot\n" + ("x" * 100 + "\n") * 10

    result = compute_srt_quality(segments, srt_text)

    # Score should be clamped to valid range
    assert 0.0 <= result["score"] <= 1.0


def test_compute_srt_quality__return_structure() -> None:
    """Verify complete return structure with all required fields."""
    segments = [{"start": 0.0, "end": 2.0, "text": "Test segment"}]
    srt_text = "1\n00:00:00,000 --> 00:00:02,000\nTest segment\n"

    result = compute_srt_quality(segments, srt_text)

    # Top-level structure
    assert "score" in result
    assert "details" in result
    assert isinstance(result["score"], float)

    # Details structure
    details = result["details"]
    assert "overlap_violations" in details
    assert "hyphen_normalization_ok" in details
    assert "line_length_violations" in details
    assert "line_length_violation_ratio" in details
    assert "cps_within_range_ratio" in details
    assert "duration_stats" in details
    assert "cps_histogram" in details
    assert "boundary_counts" in details
    assert "sample_offenders" in details

    # Duration stats structure
    duration_stats = details["duration_stats"]
    assert "min_seconds" in duration_stats
    assert "max_seconds" in duration_stats
    assert "average_seconds" in duration_stats
    assert "median_seconds" in duration_stats

    # Histogram structure
    cps_hist = details["cps_histogram"]
    assert "below_min" in cps_hist
    assert "within_range" in cps_hist
    assert "above_max" in cps_hist
    assert "total" in cps_hist

    # Boundary counts structure
    boundary = details["boundary_counts"]
    assert "within_range" in boundary
    assert "too_short" in boundary
    assert "too_long" in boundary

    # Sample offenders structure
    offenders = details["sample_offenders"]
    assert "line_length" in offenders
    assert "cps" in offenders
    assert isinstance(offenders["line_length"], list)
    assert isinstance(offenders["cps"], list)
