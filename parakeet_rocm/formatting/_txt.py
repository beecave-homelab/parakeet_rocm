"""Formatter for plain text (.txt) output."""

from parakeet_rocm.timestamps.models import AlignedResult


def to_txt(result: AlignedResult, **kwargs: object) -> str:
    """
    Format an AlignedResult as plain text by concatenating its segment texts.
    
    Parameters:
        result (AlignedResult): The aligned result containing ordered segments whose `text` values will be concatenated.
        **kwargs: Additional keyword arguments (ignored for plain text output).
    
    Returns:
        str: A single string of all segment texts joined with a single space; returns an empty string if there are no segments.
    """
    return " ".join([segment.text for segment in result.segments])