"""Formatter for CSV (.csv) output containing segment-level timing."""

from __future__ import annotations

import csv
import io

from parakeet_rocm.timestamps.models import AlignedResult


def to_csv(result: AlignedResult, **kwargs: object) -> str:  # noqa: D401
    """Convert an ``AlignedResult`` into CSV string (segment-level).

    Columns: start, end, text

    Args:
        result: The aligned result containing segments.
        **kwargs: Additional arguments (ignored for CSV output).

    Returns:
        A CSV string with one row per segment.

    """
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["start", "end", "text"])
    for seg in result.segments:
        writer.writerow([seg.start, seg.end, seg.text.replace("\n", " ")])
    return buffer.getvalue()
