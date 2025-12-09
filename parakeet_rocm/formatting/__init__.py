"""Registry of output formatters for transcriptions.

Allows easy extension with new formats by adding a formatter function and
registering it in the ``FORMATTERS`` dictionary.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from parakeet_rocm.timestamps.models import AlignedResult

from ._csv import to_csv
from ._json import to_json
from ._jsonl import to_jsonl
from ._srt import to_srt
from ._tsv import to_tsv
from ._txt import to_txt
from ._vtt import to_vtt


@dataclass
class FormatterSpec:
    """Metadata and function for a specific output format.

    Attributes:
        format_func: The formatter function that converts AlignedResult to string.
        requires_word_timestamps: Whether this format requires word-level timestamps.
        supports_highlighting: Whether this format supports word highlighting.
        file_extension: The file extension for this format (including the dot).

    """

    format_func: Callable[[AlignedResult], str]
    requires_word_timestamps: bool
    supports_highlighting: bool
    file_extension: str


# A registry mapping format names to their respective formatter specifications.
FORMATTERS: dict[str, FormatterSpec] = {
    "txt": FormatterSpec(
        format_func=to_txt,
        requires_word_timestamps=False,
        supports_highlighting=False,
        file_extension=".txt",
    ),
    "json": FormatterSpec(
        format_func=to_json,
        requires_word_timestamps=False,
        supports_highlighting=False,
        file_extension=".json",
    ),
    "jsonl": FormatterSpec(
        format_func=to_jsonl,
        requires_word_timestamps=False,
        supports_highlighting=False,
        file_extension=".jsonl",
    ),
    "csv": FormatterSpec(
        format_func=to_csv,
        requires_word_timestamps=True,
        supports_highlighting=False,
        file_extension=".csv",
    ),
    "tsv": FormatterSpec(
        format_func=to_tsv,
        requires_word_timestamps=True,
        supports_highlighting=False,
        file_extension=".tsv",
    ),
    "srt": FormatterSpec(
        format_func=to_srt,
        requires_word_timestamps=True,
        supports_highlighting=True,
        file_extension=".srt",
    ),
    "vtt": FormatterSpec(
        format_func=to_vtt,
        requires_word_timestamps=True,
        supports_highlighting=True,
        file_extension=".vtt",
    ),
}


def get_formatter(format_name: str) -> Callable[[AlignedResult], str]:
    """Get the formatter function registered for the given format name.

    Parameters:
        format_name (str): Format identifier, case-insensitive (e.g., "txt", "json").

    Returns:
        Callable[[AlignedResult], str]: Formatter that converts an
            ``AlignedResult`` to a formatted string.

    Raises:
        ValueError: If `format_name` is not supported.
    """
    spec = FORMATTERS.get(format_name.lower())
    if not spec:
        supported = list(FORMATTERS.keys())
        raise ValueError(f"Unsupported format: '{format_name}'. Supported formats are: {supported}")
    return spec.format_func


def get_formatter_spec(format_name: str) -> FormatterSpec:
    """Retrieve the FormatterSpec metadata for the given output format name.

    Parameters:
        format_name (str): Case-insensitive format identifier (e.g., "txt", "json").

    Returns:
        FormatterSpec: The metadata and formatter function for the requested format.

    Raises:
        ValueError: If the specified format_name is not supported.
    """
    spec = FORMATTERS.get(format_name.lower())
    if not spec:
        supported = list(FORMATTERS.keys())
        raise ValueError(f"Unsupported format: '{format_name}'. Supported formats are: {supported}")
    return spec
