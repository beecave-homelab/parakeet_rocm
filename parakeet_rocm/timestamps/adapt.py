"""Functions for adapting NeMo's timestamped ASR output into a standard format.

The goal is to create a common data structure (``AlignedResult``) usable by
various formatters (e.g., SRT, VTT, JSON) regardless of the specifics of the
ASR model's output.
"""

from __future__ import annotations

from nemo.collections.asr.models import ASRModel
from nemo.collections.asr.parts.utils.rnnt_utils import Hypothesis

from parakeet_rocm.timestamps.models import AlignedResult, Segment, Word
from parakeet_rocm.timestamps.segmentation import segment_words, split_lines
from parakeet_rocm.timestamps.word_timestamps import get_word_timestamps
from parakeet_rocm.utils.constant import (
    MAX_CPS,
    MAX_LINE_CHARS,
    MAX_LINES_PER_BLOCK,
    MAX_SEGMENT_DURATION_SEC,
    MIN_SEGMENT_DURATION_SEC,
)


def _merge_short_segments_pass(
    segments: list[Segment], min_duration: float, min_chars: int
) -> list[Segment]:
    """Merge segments that are too short or have too few characters.

    Args:
        segments: List of segments to process.
        min_duration: Minimum segment duration in seconds.
        min_chars: Minimum character count for standalone segments.

    Returns:
        list[Segment]: Segments with short ones merged.

    """
    merged: list[Segment] = []
    i = 0
    while i < len(segments):
        seg = segments[i]
        chars = len(seg.text.replace("\n", " "))
        dur = seg.end - seg.start
        # Criteria for merging: too short & too few chars
        if i + 1 < len(segments) and (dur < min_duration or chars < min_chars):
            nxt = segments[i + 1]
            # Merge seg + nxt
            merged_words = seg.words + nxt.words
            merged_text = split_lines(" ".join(w.word for w in merged_words))
            seg = Segment(
                text=merged_text,
                words=merged_words,
                start=seg.start,
                end=nxt.end,
            )
            i += 2  # skip next
        else:
            i += 1
        merged.append(seg)
    return merged


def _fix_segment_overlaps(segments: list[Segment], gap_sec: float) -> list[Segment]:
    """Fix overlapping segments by adjusting end times.

    Args:
        segments: List of segments to process.
        gap_sec: Minimum gap to maintain between segments.

    Returns:
        list[Segment]: Segments with overlaps fixed.

    """
    result = segments.copy()
    for j in range(len(result) - 1):
        cur = result[j]
        nxt = result[j + 1]
        if cur.end + gap_sec > nxt.start:
            cur_end_new = max(cur.start + 0.2, nxt.start - gap_sec)
            result[j] = cur.copy(update={"end": cur_end_new})
    return result


def _forward_merge_small_leading_words(
    segments: list[Segment], max_block_chars: int
) -> list[Segment]:
    """Move small leading words from next segment to previous segment.

    This prevents orphan words like "The", "Just" from starting new segments
    when they logically belong to the previous sentence.

    Args:
        segments: List of segments to process.
        max_block_chars: Maximum characters per segment.

    Returns:
        list[Segment]: Segments with small leading words merged.

    """

    def _can_append(prev: Segment, word: Word) -> bool:
        new_text = prev.text.replace("\n", " ") + " " + word.word
        if len(new_text) > max_block_chars:
            return False
        duration = word.end - prev.start
        cps = len(new_text) / max(duration, 1e-3)
        return cps <= MAX_CPS and duration <= MAX_SEGMENT_DURATION_SEC

    merged = segments.copy()
    k = 0
    while k < len(merged) - 1:
        prev = merged[k]
        nxt = merged[k + 1]
        # only attempt if next caption starts with 1 short word (<5 chars)
        first_word = nxt.words[0]
        # Only move small leading words if the previous caption does *not* already
        # end with sentence‐terminating punctuation. This prevents orphan words
        # starting a new sentence (e.g. "The", "Just") from being attached to
        # the preceding caption.
        if (
            len(first_word.word) <= 5
            and not prev.text.strip().endswith((".", "!", "?"))
            and _can_append(prev, first_word)
        ):
            # move word from nxt to prev
            updated_prev_words = prev.words + [first_word]
            updated_prev_text = split_lines(
                " ".join(w.word for w in updated_prev_words)
            )
            merged[k] = prev.copy(
                update={
                    "words": updated_prev_words,
                    "text": updated_prev_text,
                    "end": first_word.end,
                }
            )
            # trim next
            trimmed_words = nxt.words[1:]
            if not trimmed_words:
                merged.pop(k + 1)
                continue  # re-evaluate same k
            trimmed_text = split_lines(" ".join(w.word for w in trimmed_words))
            merged[k + 1] = nxt.copy(
                update={
                    "words": trimmed_words,
                    "text": trimmed_text,
                    "start": trimmed_words[0].start,
                }
            )
        k += 1
    return merged


def _merge_tiny_leading_captions(
    segments: list[Segment], max_block_chars: int
) -> list[Segment]:
    """Merge captions that start with very short first lines.

    Args:
        segments: List of segments to process.
        max_block_chars: Maximum characters per segment.

    Returns:
        list[Segment]: Segments with tiny leading captions merged.

    """
    merged = segments.copy()
    m = 0
    while m < len(merged) - 1:
        cur = merged[m]
        nxt = merged[m + 1]
        first_line = nxt.text.split("\n", 1)[0]
        if len(first_line) <= 12 or len(first_line.split()) <= 2:
            combined_words = cur.words + nxt.words
            combined_text_plain = " ".join(w.word for w in combined_words)
            duration = combined_words[-1].end - combined_words[0].start
            cps = len(combined_text_plain) / max(duration, 1e-3)
            if (
                len(combined_text_plain) <= max_block_chars
                and duration <= MAX_SEGMENT_DURATION_SEC
                and cps <= MAX_CPS
            ):
                cur = cur.copy(
                    update={
                        "words": combined_words,
                        "text": split_lines(combined_text_plain),
                        "end": nxt.end,
                    }
                )
                merged[m] = cur
                merged.pop(m + 1)
                continue
        m += 1
    return merged


def _ensure_punctuation_endings(
    segments: list[Segment], max_block_chars: int
) -> list[Segment]:
    """Merge segments that don't end with proper punctuation.

    Args:
        segments: List of segments to process.
        max_block_chars: Maximum characters per segment.

    Returns:
        list[Segment]: Segments with proper punctuation endings.

    """
    merged = segments.copy()
    j = 0
    while j < len(merged) - 1:
        cur = merged[j]
        nxt = merged[j + 1]
        if not cur.text.strip().endswith((".", "!", "?")):
            combined_words = cur.words + nxt.words
            combined_text_plain = " ".join(w.word for w in combined_words)
            if (
                len(combined_text_plain) <= max_block_chars
                and (combined_words[-1].end - combined_words[0].start)
                <= MAX_SEGMENT_DURATION_SEC
                and (
                    len(combined_text_plain)
                    / max(combined_words[-1].end - combined_words[0].start, 1e-3)
                )
                <= MAX_CPS
            ):
                cur = cur.copy(
                    update={
                        "words": combined_words,
                        "text": split_lines(combined_text_plain),
                        "end": nxt.end,
                    }
                )
                merged[j] = cur
                merged.pop(j + 1)
                continue  # re-evaluate merged cur with following
        j += 1
    return merged


def adapt_nemo_hypotheses(
    hypotheses: list[Hypothesis], model: ASRModel, time_stride: float | None = None
) -> AlignedResult:
    """Convert a list of NeMo Hypothesis objects into a standard ``AlignedResult``.

    This function orchestrates a multi-pass refinement pipeline:
    1. Extract word timestamps from NeMo hypotheses
    2. Apply sentence-aware segmentation
    3. Merge short segments
    4. Fix overlapping segments
    5. Forward-merge small leading words
    6. Merge tiny leading captions
    7. Ensure segments end with proper punctuation

    Args:
        hypotheses: List of NeMo Hypothesis objects with timestamps.
        model: NeMo ASR model used for transcription.
        time_stride: Optional time stride for timestamp calculation.

    Returns:
        AlignedResult: The adapted result containing segments and word segments.

    """
    word_timestamps = get_word_timestamps(hypotheses, model, time_stride)

    if not word_timestamps:
        return AlignedResult(segments=[], word_segments=[])

    # Configuration constants
    max_block_chars = MAX_LINE_CHARS * MAX_LINES_PER_BLOCK
    post_gap_sec = 0.05  # minimal gap to keep between captions
    min_chars_for_standalone = 15

    # Step 1: Apply sentence-aware segmentation
    segments = segment_words(word_timestamps)

    # Step 2: Merge short segments
    segments = _merge_short_segments_pass(
        segments, MIN_SEGMENT_DURATION_SEC, min_chars_for_standalone
    )

    # Step 3: Fix overlapping segments
    segments = _fix_segment_overlaps(segments, post_gap_sec)

    # Step 4: Forward-merge small leading words
    segments = _forward_merge_small_leading_words(segments, max_block_chars)

    # Step 5: Merge tiny leading captions
    segments = _merge_tiny_leading_captions(segments, max_block_chars)

    # Step 6: Ensure segments end with proper punctuation
    segments = _ensure_punctuation_endings(segments, max_block_chars)

    return AlignedResult(segments=segments, word_segments=word_timestamps)
