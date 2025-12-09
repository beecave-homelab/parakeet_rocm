"""Formatter for TSV (.tsv) output at word-level granularity."""

from __future__ import annotations

import csv
import io

from parakeet_rocm.timestamps.models import AlignedResult


def to_tsv(result: AlignedResult, **kwargs: object) -> str:  # noqa: D401
    """
    Format an AlignedResult as a TSV string with one word per row.
    
    Parameters:
        result (AlignedResult): Aligned result whose word_segments will be serialized.
        **kwargs: Additional keyword arguments (accepted but ignored for TSV output).
    
    Returns:
        str: TSV text with header columns `start`, `end`, `word`, and `score`. Each row corresponds to a word segment; `score` is an empty string when the segment's score is falsy.
    """
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter="\t")
    writer.writerow(["start", "end", "word", "score"])
    for word in result.word_segments:
        writer.writerow([word.start, word.end, word.word, word.score or ""])
    return buffer.getvalue()