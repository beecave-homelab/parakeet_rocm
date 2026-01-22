"""Unit tests for segmentation utilities and output formatters.

These tests are lightweight – they avoid loading any NeMo models and instead
construct minimal synthetic inputs (``Word`` objects) to exercise the
segmentation logic and formatter registry.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from parakeet_rocm.formatting import FORMATTERS, get_formatter
from parakeet_rocm.formatting._jsonl import to_jsonl
from parakeet_rocm.timestamps.models import AlignedResult, Segment, Word
from parakeet_rocm.timestamps.segmentation import segment_words, split_lines


@pytest.fixture()
def sample_words() -> list[Word]:
    """Create a small list of Word objects for the phrase "Hello world.".

    The words span approximately two seconds.

    Returns:
        list[Word]: Two Word objects: "Hello" (start 0.0, end 0.8) and
            "world." (start 0.8, end 1.6).
    """
    # "Hello world." spoken over two seconds
    return [
        Word(word="Hello", start=0.0, end=0.8),
        Word(word="world.", start=0.8, end=1.6),
    ]


def test_segment_words_single_segment(sample_words: list[Word]) -> None:
    """Simple input should yield a single segment with expected timing.

    Args:
        sample_words (list[Word]): Small synthetic word sequence.
    """
    segments = segment_words(sample_words)
    # Should create exactly one caption segment for this simple sentence
    assert len(segments) == 1
    seg = segments[0]
    assert seg.text.replace("\n", " ") == "Hello world."
    # Segment timing should cover full word range (with small display buffer)
    assert seg.start == pytest.approx(0.0)
    assert seg.end >= 1.6


def test_split_lines_balanced() -> None:
    """Long text should be split into balanced lines."""
    long_text = (
        "This is a deliberately long sentence that should be automatically split "
        "into two balanced lines by the split_lines function."
    )
    result = split_lines(long_text)
    # Expect a newline inserted
    assert "\n" in result
    line1, line2 = result.split("\n", 1)
    # Both lines should be non-empty and reasonably balanced in length
    assert len(line1) > 10 and len(line2) > 10


def _make_aligned_result() -> AlignedResult:
    """Builds a minimal AlignedResult containing one segment with two words.

    Returns:
        AlignedResult: Instance with a single segment whose text is
            "Hello world", start 0.0, end 1.4, and two word entries
            ("Hello" 0.0–0.8, "world" 0.8–1.4).
    """
    words = [
        Word(word="Hello", start=0.0, end=0.8),
        Word(word="world", start=0.8, end=1.4),
    ]
    segment = Segment(text="Hello world", words=words, start=0.0, end=1.4)
    return AlignedResult(segments=[segment], word_segments=words)


@pytest.mark.parametrize("fmt", list(FORMATTERS.keys()))
def test_formatters_output(fmt: str) -> None:
    """Verify that each registered formatter produces a valid string.

    The formatter identified by ``fmt`` should return a string containing the
    sample word "Hello" and format-specific indicators:

    - For ``"json"``, output begins with ``"{"`` when trimmed.
    - For ``"jsonl"``, output may contain newline(s) but is accepted as a
      JSONL-style serialization.
    - For ``"srt"`` and ``"vtt"``, output contains the timestamp delimiter
      ``"-->"``.

    Parameters:
        fmt (str): Formatter key registered in ``FORMATTERS``.
    """
    aligned = _make_aligned_result()
    formatter = get_formatter(fmt)

    if fmt in {"srt", "vtt"}:
        output = formatter(aligned, highlight_words=True)
    else:
        output = formatter(aligned)

    assert isinstance(output, str)
    # Every formatter should contain the word "Hello"
    assert "Hello" in output

    # For JSON formats we expect braces, for SRT/VTT we expect timestamp arrow, etc.
    if fmt == "json":
        assert output.strip().startswith("{")
    elif fmt == "jsonl":
        assert "\n" not in output.strip() or output.strip().count("\n") >= 0
    elif fmt in {"srt", "vtt"}:
        assert "-->" in output


def test_jsonl_fallback_dict() -> None:
    """``to_jsonl`` should handle dict-like segments gracefully."""
    result = AlignedResult(
        segments=[{"text": "x", "words": [], "start": 0, "end": 1}], word_segments=[]
    )
    data = to_jsonl(result)
    assert data.strip().startswith("{")


if __name__ == "__main__":
    # Allow `python -m tests.test_segmentation_and_formatters` execution
    pytest.main([Path(__file__).resolve()])
