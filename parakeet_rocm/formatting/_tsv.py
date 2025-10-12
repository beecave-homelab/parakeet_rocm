"""Formatter for TSV (.tsv) output at word-level granularity."""

from __future__ import annotations

import csv
import io

from parakeet_rocm.timestamps.models import AlignedResult


def to_tsv(result: AlignedResult, **kwargs: object) -> str:  # noqa: D401
    """Convert an ``AlignedResult`` into TSV string (one word per row).

    Args:
        result: The aligned result containing word segments.
        **kwargs: Additional arguments (ignored for TSV output).

    Returns:
        A TSV string with columns: start, end, word, and score (one word per row).

    """
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter="\t")
    writer.writerow(["start", "end", "word", "score"])
    for word in result.word_segments:
        writer.writerow([word.start, word.end, word.word, word.score or ""])
    return buffer.getvalue()
