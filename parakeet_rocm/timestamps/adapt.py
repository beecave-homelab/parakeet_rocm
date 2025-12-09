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
    """Merge adjacent segments when the earlier segment's duration is less than min_duration or its text has fewer than min_chars characters.

    Parameters:
        segments (list[Segment]): The segments to process.
        min_duration (float): Minimum duration in seconds for a segment to remain standalone.
        min_chars (int): Minimum character count for a segment to remain standalone.

    Returns:
        list[Segment]: A new list of segments where short segments have been merged into their following segments.
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
    """Ensure consecutive segments are separated by at least gap_sec seconds by shortening an earlier segment's end time when necessary.

    If an earlier segment's end would be within gap_sec of the following segment's start, the earlier segment's end is reduced to max(earlier.start + 0.2, next.start - gap_sec).

    Parameters:
        segments (list[Segment]): Ordered list of segments to adjust.
        gap_sec (float): Minimum required gap in seconds between consecutive segments.

    Returns:
        list[Segment]: A new list of segments with end times adjusted to enforce the minimum gap.
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
    """Move short leading words from a segment to the previous segment when doing so preserves caption constraints.

    If the next segment begins with a short word (<= 5 characters), this function will append that word to the previous segment provided the previous segment does not end with sentence-ending punctuation and the resulting previous segment would remain within character, duration, and characters-per-second limits. The function preserves segment ordering and updates start/end times and text for affected segments.

    Parameters:
        segments (list[Segment]): Segments to process.
        max_block_chars (int): Maximum allowed characters for a segment block; used to prevent excessive length when appending a word.

    Returns:
        list[Segment]: A new list of Segment objects with eligible small leading words moved forward.
    """

    def _can_append(prev: Segment, word: Word) -> bool:
        """Decides whether appending a word to an existing segment would respect length, characters-per-second, and maximum-duration constraints.

        @returns `True` if adding the word to the segment would keep the combined text length within the allowed block size, keep characters-per-second at or below the configured limit, and keep the word's span within the maximum segment duration; `False` otherwise.
        """
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
            updated_prev_text = split_lines(" ".join(w.word for w in updated_prev_words))
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


def _merge_tiny_leading_captions(segments: list[Segment], max_block_chars: int) -> list[Segment]:
    """Merge captions that start with very short first lines.

    Args:
        segments: List of segments to process.
        max_block_chars: Maximum characters per segment.

    Returns:
        list[Segment]: New list of segments where tiny leading captions have been merged into the previous segment when the combined text length is <= max_block_chars, the combined duration is <= MAX_SEGMENT_DURATION_SEC, and the combined characters-per-second is <= MAX_CPS.
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


def _ensure_punctuation_endings(segments: list[Segment], max_block_chars: int) -> list[Segment]:
    """Merge segments that don't end with proper punctuation.

    Args:
        segments: List of segments to process.
        max_block_chars: Maximum characters per segment.

    Returns:
        list[Segment]: A new list of segments with adjacent segments merged to ensure sentence-ending punctuation where appropriate.
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
                and (combined_words[-1].end - combined_words[0].start) <= MAX_SEGMENT_DURATION_SEC
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
    """Adapt NeMo Hypothesis objects with word timestamps into an AlignedResult by applying a multi-pass segmentation and refinement pipeline.

    Performs word-timestamp extraction, sentence-aware segmentation, and several refinement passes (short-segment merging, overlap correction, forward-merging of small leading words, merging of tiny leading captions, and punctuation-aware merging) to produce caption-friendly segments.

    Parameters:
        hypotheses (list[Hypothesis]): NeMo hypotheses that include timestamp information.
        model (ASRModel): NeMo ASR model used to derive word timestamps and context.
        time_stride (float | None): Optional override for timestamp stride calculation.

    Returns:
        AlignedResult: Object containing the refined list of segments and the original word-level timestamps.
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
