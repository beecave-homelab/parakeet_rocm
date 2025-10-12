"""Formatter for JSON (.json) output."""

from parakeet_rocm.timestamps.models import AlignedResult


def to_json(result: AlignedResult, **kwargs: object) -> str:
    """Convert an ``AlignedResult`` to a JSON string.

    Args:
        result: The aligned result containing segments.
        **kwargs: Additional arguments (ignored for JSON output).

    Returns:
        A JSON string representation of the result.

    """
    return result.model_dump_json(indent=2)
