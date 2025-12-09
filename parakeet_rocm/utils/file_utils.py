"""Utilities for output naming, overwrite protection, and audio path resolution.

All functions are type-hinted and documented. The module exposes:
• `get_unique_filename` – unchanged
• `resolve_input_paths` – expand wildcard patterns / directories into concrete
  paths
• `AUDIO_EXTENSIONS` – set of allowed audio filename extensions
"""

from __future__ import annotations

import pathlib
from collections.abc import Iterable, Sequence
from glob import glob

PathLike = str | pathlib.Path

# Supported audio file extensions (lower-case, dot-prefixed)
# Extended set covering common audio and video containers/codecs that ffmpeg can
# usually decode. Keeping it modest in size avoids pathological glob scans while
# ensuring typical user files are accepted.
AUDIO_EXTENSIONS: set[str] = {
    # audio
    ".wav",
    ".mp3",
    ".aac",
    ".flac",
    ".ogg",
    ".opus",
    ".m4a",
    ".wma",
    ".aiff",
    ".alac",
    ".amr",
    # video
    ".mp4",
    ".mkv",
    ".mov",
    ".avi",
    ".webm",
    ".flv",
    ".ts",
}

__all__ = [
    "AUDIO_EXTENSIONS",
    "get_unique_filename",
    "resolve_input_paths",
]


def get_unique_filename(
    base_path: PathLike,
    overwrite: bool = False,
    separator: str = "-",
) -> pathlib.Path:
    """Generate a unique filename to avoid overwriting existing files.

    If the file does not exist or overwrite is True, returns the original path.
    Otherwise, appends a numbered suffix like " -1", " -2", etc.

    Args:
        base_path: The desired file path.
        overwrite: If True, return the original path even if it exists.
        separator: The separator to use before the number suffix.

    Returns:
        A pathlib.Path that is guaranteed not to exist (unless overwrite=True).

    Raises:
        RuntimeError: If a unique filename cannot be found after 9,999 attempts.

    """
    path = pathlib.Path(base_path)

    if overwrite or not path.exists():
        return path

    # Find the next available number
    counter = 1
    while True:
        new_name = f"{path.stem}{separator}{counter}{path.suffix}"
        new_path = path.parent / new_name
        if not new_path.exists():
            return new_path
        counter += 1

        # Safety check to prevent infinite loops
        if counter > 9999:
            raise RuntimeError(f"Cannot find unique filename for {base_path}")


def _is_audio_file(path: pathlib.Path, exts: Sequence[str] | set[str] | None = None) -> bool:  # noqa: D401
    """Return *True* if *path* points to a supported audio file.

    Args:
        path: File path to test.
        exts: Optional iterable of file extensions to accept; defaults to
            :data:`AUDIO_EXTENSIONS`.

    Returns:
        bool: `True` if the path exists, is a file, and its suffix matches an allowed extension, `False` otherwise.
    """
    _exts = set(ext.lower() for ext in (exts or AUDIO_EXTENSIONS))
    return path.is_file() and path.suffix.lower() in _exts


def resolve_input_paths(
    patterns: Iterable[PathLike] | PathLike,
    *,
    audio_exts: Sequence[str] | set[str] | None = None,
    recursive: bool = True,
) -> list[pathlib.Path]:
    """Expand file/directory/wildcard patterns into a deduplicated list of audio file paths.

    This resolves each pattern (a file path, directory, or shell wildcard) into concrete
    existing files that match the allowed audio extensions. Directories are scanned
    recursively by default; duplicates are removed while preserving the original
    insertion order. Non-existent patterns are ignored.

    Parameters:
        patterns (str | pathlib.Path | Iterable[str | pathlib.Path]):
            One or more file, directory, or glob patterns to resolve.
        audio_exts (Sequence[str] | set[str] | None, optional):
            Allowed file extensions (dot-prefixed, case-insensitive). Defaults to
            AUDIO_EXTENSIONS.
        recursive (bool, optional):
            If True, search directories recursively; otherwise only top-level files
            are considered.

    Returns:
        list[pathlib.Path]:
            A list of existing pathlib.Path objects that match the extension filter,
            in insertion order with duplicates removed.
    """
    if isinstance(patterns, (str, pathlib.Path)):
        patterns = [patterns]

    _exts = set(ext.lower() for ext in (audio_exts or AUDIO_EXTENSIONS))

    resolved: list[pathlib.Path] = []
    seen: set[pathlib.Path] = set()

    def _add(p: pathlib.Path) -> None:
        """Add a Path to the resolved list and seen set if it refers to a supported audio file and has not been added yet.

        Parameters:
            p (pathlib.Path): Candidate path to validate and add as a resolved input file.
        """
        if p not in seen and _is_audio_file(p, _exts):
            seen.add(p)
            resolved.append(p)

    for patt in patterns:
        p = pathlib.Path(patt).expanduser()
        if p.is_dir():
            # Walk directory
            walker = p.rglob("*") if recursive else p.glob("*")
            for child in walker:
                _add(child)
        else:
            # Use glob for wildcard expansion; if no wildcard, treat as literal
            matches = glob(str(p), recursive=True)
            for m in matches:
                _add(pathlib.Path(m))
    return resolved
