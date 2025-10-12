"""Formatter for plain text (.txt) output."""

from parakeet_rocm.timestamps.models import AlignedResult


def to_txt(result: AlignedResult, **kwargs: object) -> str:
    """Convert an ``AlignedResult`` to a plain text string.

    Args:
        result: The aligned result containing segments.
        **kwargs: Additional arguments (ignored for plain text output).

    Returns:
        A plain text string with all segment texts joined by newlines.

    """
    return " ".join([segment.text for segment in result.segments])
