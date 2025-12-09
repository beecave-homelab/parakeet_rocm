"""Formatter for JSON (.json) output."""

from parakeet_rocm.timestamps.models import AlignedResult


def to_json(result: AlignedResult, **kwargs: object) -> str:
    """
    Convert an AlignedResult into a JSON-formatted string.
    
    Parameters:
        result: The AlignedResult to serialize.
        **kwargs: Additional arguments; ignored for JSON output.
    
    Returns:
        JSON string representation of the result (pretty-printed with two-space indentation).
    """
    return result.model_dump_json(indent=2)