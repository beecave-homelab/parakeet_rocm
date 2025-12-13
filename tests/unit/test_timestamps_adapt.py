"""Unit tests for parakeet_rocm.timestamps.adapt module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from parakeet_rocm.timestamps.adapt import (
    _ensure_punctuation_endings,
    _fix_segment_overlaps,
    _forward_merge_small_leading_words,
    _merge_short_segments_pass,
    _merge_tiny_leading_captions,
    adapt_nemo_hypotheses,
)
from parakeet_rocm.timestamps.models import Segment, Word


def test_merge_short_segments_pass() -> None:
    """Tests merging of adjacent short segments."""
    word1 = Word(word="Hello", start=0.0, end=0.5, score=None)
    word2 = Word(word="world", start=0.5, end=1.0, score=None)
    word3 = Word(word="This", start=1.0, end=1.5, score=None)
    word4 = Word(word="test", start=1.5, end=2.0, score=None)

    # Short segment (duration < min_duration)
    short_seg = Segment(text="Hello world", words=[word1, word2], start=0.0, end=1.0)
    normal_seg = Segment(text="This test", words=[word3, word4], start=1.0, end=2.0)

    result = _merge_short_segments_pass([short_seg, normal_seg], min_duration=1.5, min_chars=15)

    # Should merge short segment with following one
    assert len(result) == 1
    assert result[0].text == "Hello world This test"
    assert result[0].start == 0.0
    assert result[0].end == 2.0


def test_merge_short_segments_pass_by_chars() -> None:
    """Tests merging based on character count threshold."""
    word1 = Word(word="Hi", start=0.0, end=0.3, score=None)
    word2 = Word(word="there", start=0.3, end=0.6, score=None)
    word3 = Word(word="This", start=1.0, end=1.5, score=None)
    word4 = Word(word="test", start=1.5, end=2.0, score=None)

    # Short segment (chars < min_chars)
    short_seg = Segment(text="Hi there", words=[word1, word2], start=0.0, end=0.6)
    normal_seg = Segment(text="This test", words=[word3, word4], start=1.0, end=2.0)

    result = _merge_short_segments_pass([short_seg, normal_seg], min_duration=0.5, min_chars=10)

    # Should merge due to character count
    assert len(result) == 1
    assert result[0].text == "Hi there This test"


def test_merge_short_segments_pass_no_merge() -> None:
    """Tests no merging when segments meet criteria."""
    word1 = Word(word="Hello", start=0.0, end=0.5, score=None)
    word2 = Word(word="world", start=0.5, end=1.0, score=None)
    word3 = Word(word="This", start=1.0, end=1.5, score=None)
    word4 = Word(word="test", start=1.5, end=2.0, score=None)

    seg1 = Segment(text="Hello world", words=[word1, word2], start=0.0, end=1.0)
    seg2 = Segment(text="This test", words=[word3, word4], start=1.0, end=2.0)

    result = _merge_short_segments_pass([seg1, seg2], min_duration=0.5, min_chars=5)

    # No merging needed
    assert len(result) == 2
    assert result[0].text == "Hello world"
    assert result[1].text == "This test"


def test_fix_segment_overlaps() -> None:
    """Tests fixing overlapping segments."""
    word1 = Word(word="Hello", start=0.0, end=0.8, score=None)
    word2 = Word(word="world", start=0.8, end=1.6, score=None)
    word3 = Word(word="This", start=1.5, end=2.0, score=None)
    word4 = Word(word="test", start=2.0, end=2.5, score=None)

    # Overlapping segments (gap < 0.1)
    seg1 = Segment(text="Hello world", words=[word1, word2], start=0.0, end=1.6)
    seg2 = Segment(text="This test", words=[word3, word4], start=1.5, end=2.5)

    result = _fix_segment_overlaps([seg1, seg2], gap_sec=0.1)

    # Should adjust first segment end
    assert len(result) == 2
    assert result[0].end < 1.5  # Should be moved back
    assert result[1].start == 1.5  # Should remain unchanged


def test_fix_segment_overlaps_no_overlap() -> None:
    """Tests no adjustment when segments don't overlap."""
    word1 = Word(word="Hello", start=0.0, end=0.5, score=None)
    word2 = Word(word="world", start=0.5, end=1.0, score=None)
    word3 = Word(word="This", start=1.2, end=1.7, score=None)
    word4 = Word(word="test", start=1.7, end=2.2, score=None)

    # Non-overlapping segments (gap > 0.1)
    seg1 = Segment(text="Hello world", words=[word1, word2], start=0.0, end=1.0)
    seg2 = Segment(text="This test", words=[word3, word4], start=1.2, end=2.2)

    result = _fix_segment_overlaps([seg1, seg2], gap_sec=0.1)

    # No changes needed
    assert len(result) == 2
    assert result[0].end == 1.0
    assert result[1].start == 1.2


def test_forward_merge_small_leading_words() -> None:
    """Tests moving small leading words forward."""
    word1 = Word(word="Hello", start=0.0, end=0.5, score=None)
    word2 = Word(word="world", start=0.5, end=1.0, score=None)
    word3 = Word(word="a", start=1.0, end=1.2, score=None)  # Small word
    word4 = Word(word="test", start=1.2, end=1.7, score=None)

    seg1 = Segment(text="Hello world", words=[word1, word2], start=0.0, end=1.0)
    seg2 = Segment(text="a test", words=[word3, word4], start=1.0, end=1.7)

    result = _forward_merge_small_leading_words([seg1, seg2], max_block_chars=50)

    # Should move "a" to previous segment
    assert len(result) == 2
    assert "a" in result[0].text
    assert "a" not in result[1].text


def test_forward_merge_small_leading_words_with_punctuation() -> None:
    """Tests no merging when previous segment ends with punctuation."""
    word1 = Word(word="Hello", start=0.0, end=0.5, score=None)
    word2 = Word(word="world", start=0.5, end=1.0, score=None)
    word3 = Word(word="a", start=1.0, end=1.2, score=None)  # Small word
    word4 = Word(word="test", start=1.2, end=1.7, score=None)

    seg1 = Segment(
        text="Hello world.", words=[word1, word2], start=0.0, end=1.0
    )  # Ends with period
    seg2 = Segment(text="a test", words=[word3, word4], start=1.0, end=1.7)

    result = _forward_merge_small_leading_words([seg1, seg2], max_block_chars=50)

    # Should not merge due to punctuation
    assert len(result) == 2
    assert result[0].text == "Hello world."
    assert result[1].text == "a test"


def test_forward_merge_small_leading_words_single_word_segment() -> None:
    """Tests handling when next segment becomes empty after moving word."""
    word1 = Word(word="Hello", start=0.0, end=0.5, score=None)
    word2 = Word(word="world", start=0.5, end=1.0, score=None)
    word3 = Word(word="a", start=1.0, end=1.2, score=None)  # Only word

    seg1 = Segment(text="Hello world", words=[word1, word2], start=0.0, end=1.0)
    seg2 = Segment(text="a", words=[word3], start=1.0, end=1.2)

    result = _forward_merge_small_leading_words([seg1, seg2], max_block_chars=50)

    # Should remove empty segment
    assert len(result) == 1
    assert "a" in result[0].text


def test_merge_tiny_leading_captions() -> None:
    """Tests merging captions with tiny first lines."""
    word1 = Word(word="Hello", start=0.0, end=0.5, score=None)
    word2 = Word(word="world", start=0.5, end=1.0, score=None)
    word3 = Word(word="Hi", start=1.0, end=1.2, score=None)
    word4 = Word(word="there", start=1.2, end=1.7, score=None)

    seg1 = Segment(text="Hello world", words=[word1, word2], start=0.0, end=1.0)
    seg2 = Segment(text="Hi\nthere", words=[word3, word4], start=1.0, end=1.7)  # Tiny first line

    result = _merge_tiny_leading_captions([seg1, seg2], max_block_chars=50)

    # Should merge due to tiny first line
    assert len(result) == 1
    assert "Hello world Hi there" in result[0].text.replace("\n", " ")


def test_merge_tiny_leading_captions_two_words() -> None:
    """Tests merging captions with exactly two words on first line."""
    word1 = Word(word="Hello", start=0.0, end=0.5, score=None)
    word2 = Word(word="world", start=0.5, end=1.0, score=None)
    word3 = Word(word="Hi", start=1.0, end=1.2, score=None)
    word4 = Word(word="there", start=1.2, end=1.7, score=None)

    seg1 = Segment(text="Hello world", words=[word1, word2], start=0.0, end=1.0)
    seg2 = Segment(text="Hi there", words=[word3, word4], start=1.0, end=1.7)  # Two words

    result = _merge_tiny_leading_captions([seg1, seg2], max_block_chars=50)

    # Should merge due to two words on first line
    assert len(result) == 1
    assert result[0].start == 0.0
    assert result[0].end == 1.7
    assert result[0].text.replace("\n", " ") == "Hello world Hi there"
    assert [w.word for w in result[0].words] == ["Hello", "world", "Hi", "there"]

def test_ensure_punctuation_endings() -> None:
    """Tests merging segments without proper punctuation."""
    word1 = Word(word="Hello", start=0.0, end=0.5, score=None)
    word2 = Word(word="world", start=0.5, end=1.0, score=None)
    word3 = Word(word="This", start=1.0, end=1.5, score=None)
    word4 = Word(word="test", start=1.5, end=2.0, score=None)

    seg1 = Segment(text="Hello world", words=[word1, word2], start=0.0, end=1.0)  # No punctuation
    seg2 = Segment(text="This test", words=[word3, word4], start=1.0, end=2.0)

    result = _ensure_punctuation_endings([seg1, seg2], max_block_chars=50)

    # Should merge to ensure punctuation ending
    assert len(result) == 1
    assert result[0].text == "Hello world This test"


def test_ensure_punctuation_endings_with_punctuation() -> None:
    """Tests no merging when segment already has punctuation."""
    word1 = Word(word="Hello", start=0.0, end=0.5, score=None)
    word2 = Word(word="world", start=0.5, end=1.0, score=None)
    word3 = Word(word="This", start=1.0, end=1.5, score=None)
    word4 = Word(word="test", start=1.5, end=2.0, score=None)

    seg1 = Segment(text="Hello world.", words=[word1, word2], start=0.0, end=1.0)  # Has punctuation
    seg2 = Segment(text="This test", words=[word3, word4], start=1.0, end=2.0)

    result = _ensure_punctuation_endings([seg1, seg2], max_block_chars=50)

    # Should not merge
    assert len(result) == 2
    assert result[0].text == "Hello world."


def test_ensure_punctuation_endings_question_mark() -> None:
    """Tests no merging when segment ends with question mark."""
    word1 = Word(word="Hello", start=0.0, end=0.5, score=None)
    word2 = Word(word="world", start=0.5, end=1.0, score=None)
    word3 = Word(word="This", start=1.0, end=1.5, score=None)
    word4 = Word(word="test", start=1.5, end=2.0, score=None)

    seg1 = Segment(
        text="Hello world?", words=[word1, word2], start=0.0, end=1.0
    )  # Has question mark
    seg2 = Segment(text="This test", words=[word3, word4], start=1.0, end=2.0)

    result = _ensure_punctuation_endings([seg1, seg2], max_block_chars=50)

    # Should not merge
    assert len(result) == 2
    assert result[0].text == "Hello world?"


@patch("parakeet_rocm.timestamps.adapt.get_word_timestamps")
@patch("parakeet_rocm.timestamps.adapt.segment_words")
def test_adapt_nemo_hypotheses_empty_words(
    mock_segment_words: MagicMock,
    mock_get_word_timestamps: MagicMock,
) -> None:
    """Tests adapt_nemo_hypotheses with empty word timestamps."""
    mock_get_word_timestamps.return_value = []

    result = adapt_nemo_hypotheses([], MagicMock())

    assert result.segments == []
    assert result.word_segments == []
    mock_get_word_timestamps.assert_called_once()
    mock_segment_words.assert_not_called()


@patch("parakeet_rocm.timestamps.adapt.get_word_timestamps")
@patch("parakeet_rocm.timestamps.adapt.segment_words")
def test_adapt_nemo_hypotheses_full_pipeline(
    mock_segment_words: MagicMock,
    mock_get_word_timestamps: MagicMock,
) -> None:
    """Tests adapt_nemo_hypotheses with full processing pipeline."""
    word1 = Word(word="Hello", start=0.0, end=0.5, score=None)
    word2 = Word(word="world", start=0.5, end=1.0, score=None)

    mock_get_word_timestamps.return_value = [word1, word2]

    # Mock initial segments
    initial_seg = Segment(text="Hello world", words=[word1, word2], start=0.0, end=1.0)
    mock_segment_words.return_value = [initial_seg]

    model_mock = MagicMock()
    result = adapt_nemo_hypotheses([], model_mock, time_stride=0.02)

    # Should call all processing steps
    mock_get_word_timestamps.assert_called_once_with([], model_mock, 0.02)
    mock_segment_words.assert_called_once_with([word1, word2])

    # Should return processed result
    assert len(result.segments) >= 1
    assert result.word_segments == [word1, word2]
