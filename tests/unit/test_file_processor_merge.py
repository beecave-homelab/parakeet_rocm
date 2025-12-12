"""Tests for merge handling inside the transcription file processor."""

from __future__ import annotations

import pytest

from parakeet_rocm.timestamps.models import AlignedResult, Segment, Word
from parakeet_rocm.transcription import file_processor as fp
from parakeet_rocm.utils.constant import DISPLAY_BUFFER_SEC


def _make_segment(words: list[Word]) -> Segment:
    return Segment(
        text=" ".join(w.word for w in words),
        words=words,
        start=words[0].start,
        end=words[-1].end + DISPLAY_BUFFER_SEC,
    )


def test_merge_word_segments_updates_segments(monkeypatch: pytest.MonkeyPatch) -> None:
    """Merged words should also refresh segment timing.

    The LCS merge shifts later chunks earlier; segments must be regenerated from
    the shifted words to avoid cumulative drift in long files.
    """
    # Chunk A is on time; chunk B is 0.2 s late and contains one new word.
    chunk_a = [
        Word(word="foo", start=0.0, end=0.4),
        Word(word="bar", start=0.4, end=0.8),
    ]
    chunk_b = [
        Word(word="bar", start=0.6, end=1.0),
        Word(word="baz", start=1.0, end=1.4),
    ]

    # The adaptor returns an aligned result that still contains the unshifted
    # timestamps. _merge_word_segments() is expected to correct them.
    initial_words = chunk_a + [chunk_b[-1]]
    aligned = AlignedResult(
        segments=[_make_segment(initial_words)],
        word_segments=initial_words,
    )

    # Patch helpers used by _merge_word_segments
    monkeypatch.setattr(fp, "calc_time_stride", lambda _m, verbose=False: 1.0)

    import parakeet_rocm.timestamps.adapt as adapt_mod

    monkeypatch.setattr(adapt_mod, "adapt_nemo_hypotheses", lambda *_args, **_kwargs: aligned)

    word_lists = [chunk_a, chunk_b]
    monkeypatch.setattr(fp, "get_word_timestamps", lambda _h, _m, _ts: word_lists.pop(0))

    merged = fp._merge_word_segments(  # noqa: SLF001
        hypotheses=[object(), object()],
        model=object(),
        merge_strategy="lcs",
        overlap_duration=1,
        verbose=False,
    )

    # LCS merge shifts chunk B by -0.2s, so baz should start at 0.8 and end at 1.2
    assert merged.word_segments[-1].start == pytest.approx(0.8, rel=1e-3)
    assert merged.word_segments[-1].end == pytest.approx(1.2, rel=1e-3)

    # Segments should be regenerated from the shifted words, not the stale ones
    expected_end = merged.word_segments[-1].end + DISPLAY_BUFFER_SEC
    assert merged.segments[0].end == pytest.approx(expected_end, rel=1e-3)
    assert merged.segments[0].end < aligned.segments[0].end
