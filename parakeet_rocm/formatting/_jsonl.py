"""Formatter for JSON Lines (.jsonl) output.

Each line contains a JSON object representing a single *Segment* in the aligned
result.
"""

from __future__ import annotations

from parakeet_rocm.timestamps.models import AlignedResult, Segment


def to_jsonl(result: AlignedResult, **kwargs: object) -> str:  # noqa: D401
    """Convert an ``AlignedResult`` into JSON Lines string (one *Segment* per line).

    Args:
        result: The aligned result containing segments.
        **kwargs: Additional arguments (ignored for JSONL output).

    Returns:
        A JSON Lines string where each line is a JSON object for one segment.

    """
    lines: list[str] = []
    for segment in result.segments:
        # Use pydantic's ``model_dump_json`` for compact serialisation.
        if isinstance(segment, Segment):
            lines.append(segment.model_dump_json())
        else:  # Fallback in case segments are plain dicts
            import json

            lines.append(json.dumps(segment, ensure_ascii=False))
    return "\n".join(lines)
