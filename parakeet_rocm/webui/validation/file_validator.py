"""File validation utilities for WebUI.

Provides validation functions for audio/video files and output
directories with comprehensive error checking and user-friendly
error messages.
"""

from __future__ import annotations

import pathlib

from parakeet_rocm.utils.constant import SUPPORTED_EXTENSIONS


class FileValidationError(ValueError):
    """Raised when file validation fails.

    This exception provides clear, user-friendly error messages
    for common file validation issues.
    """

    pass


def validate_audio_file(file_path: pathlib.Path | str) -> pathlib.Path:
    """Validate a single audio or video file.

    Checks that the file exists, is a regular file (not a directory),
    has a supported extension, and is not empty.

    Args:
        file_path: Path to the audio/video file.

    Returns:
        Validated Path object.

    Raises:
        FileValidationError: If validation fails with descriptive message.

    Examples:
        >>> validate_audio_file(pathlib.Path("audio.wav"))
        PosixPath('audio.wav')

        >>> validate_audio_file("/path/to/video.mp4")
        PosixPath('/path/to/video.mp4')
    """
    # Convert string to Path if needed
    if isinstance(file_path, str):
        file_path = pathlib.Path(file_path)

    # Check file exists
    if not file_path.exists():
        raise FileValidationError(f"File does not exist: {file_path}")

    # Check it's a file, not a directory
    if not file_path.is_file():
        raise FileValidationError(f"Path is not a file: {file_path}")

    # Check extension is supported (case-insensitive)
    ext = file_path.suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        supported_list = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        raise FileValidationError(
            f"Unsupported file format: {ext}. Supported formats: {supported_list}"
        )

    # Check file is not empty
    if file_path.stat().st_size == 0:
        raise FileValidationError(f"File is empty: {file_path}")

    return file_path


def validate_audio_files(
    file_paths: list[pathlib.Path | str],
) -> list[pathlib.Path]:
    """Validate a list of audio or video files.

    Args:
        file_paths: List of file paths to validate.

    Returns:
        List of validated Path objects.

    Raises:
        FileValidationError: If validation fails for any file.

    Examples:
        >>> validate_audio_files([
        ...     pathlib.Path("audio1.wav"),
        ...     pathlib.Path("audio2.mp3"),
        ... ])
        [PosixPath('audio1.wav'), PosixPath('audio2.mp3')]
    """
    # Check for empty list
    if not file_paths:
        raise FileValidationError("No files provided")

    # Validate each file
    validated_files = []
    for file_path in file_paths:
        validated_file = validate_audio_file(file_path)
        validated_files.append(validated_file)

    return validated_files


def validate_output_directory(
    dir_path: pathlib.Path | str,
) -> pathlib.Path:
    """Validate and optionally create an output directory.

    If the directory doesn't exist, it will be created including
    all parent directories. If it exists, validates it's actually
    a directory.

    Args:
        dir_path: Path to the output directory.

    Returns:
        Validated Path object.

    Raises:
        FileValidationError: If validation fails or directory cannot be created.

    Examples:
        >>> validate_output_directory(pathlib.Path("/tmp/output"))
        PosixPath('/tmp/output')

        >>> validate_output_directory("/path/to/new/output")
        PosixPath('/path/to/new/output')
    """
    # Convert string to Path if needed
    if isinstance(dir_path, str):
        dir_path = pathlib.Path(dir_path)

    # If directory doesn't exist, create it
    if not dir_path.exists():
        try:
            dir_path.mkdir(parents=True, exist_ok=True)
        except PermissionError as e:
            raise FileValidationError(
                f"Permission denied: Cannot create directory {dir_path}"
            ) from e
        except OSError as e:
            raise FileValidationError(f"Cannot create directory {dir_path}: {e}") from e

    # Check it's a directory
    if not dir_path.is_dir():
        raise FileValidationError(f"Path is not a directory: {dir_path}")

    return dir_path
