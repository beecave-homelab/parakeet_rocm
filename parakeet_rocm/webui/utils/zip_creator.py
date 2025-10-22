"""ZIP archive creator for bulk file downloads.

Provides functionality to create compressed ZIP archives from multiple files,
following SOLID principles for maintainability and testability.
"""

from __future__ import annotations

import pathlib
import tempfile
import zipfile
from collections.abc import Sequence


class ZipCreator:
    """Creates ZIP archives from multiple files for bulk downloads.

    This class follows the Single Responsibility Principle by focusing
    solely on ZIP archive creation. It provides a clean interface for
    creating compressed archives from file collections.

    Examples:
        >>> creator = ZipCreator()
        >>> files = [Path("file1.srt"), Path("file2.srt")]
        >>> output = Path("transcriptions.zip")
        >>> creator.create_zip(files, output)
        PosixPath('transcriptions.zip')

        >>> # Create temporary ZIP
        >>> temp_zip = creator.create_temporary_zip(files)
        >>> temp_zip.exists()
        True
    """

    def __init__(
        self,
        compression: int = zipfile.ZIP_DEFLATED,
        compression_level: int = 9,
    ) -> None:
        """Initialize ZipCreator with compression settings.

        Args:
            compression: Compression method (default: ZIP_DEFLATED).
            compression_level: Compression level 0-9 (default: 9 for maximum).

        Examples:
            >>> creator = ZipCreator()
            >>> creator = ZipCreator(compression_level=6)  # Faster, less compression
        """
        self.compression = compression
        self.compression_level = compression_level

    def create_zip(
        self,
        files: Sequence[pathlib.Path],
        output_path: pathlib.Path,
    ) -> pathlib.Path:
        """Create a ZIP archive containing the specified files.

        Args:
            files: Sequence of file paths to include in the archive.
            output_path: Path where the ZIP file should be created.

        Returns:
            Path to the created ZIP archive.

        Raises:
            ValueError: If files list is empty.
            FileNotFoundError: If any input file does not exist.

        Examples:
            >>> creator = ZipCreator()
            >>> files = [Path("output.srt"), Path("output.vtt")]
            >>> zip_path = creator.create_zip(files, Path("downloads.zip"))
            >>> zip_path.exists()
            True
        """
        if not files:
            raise ValueError("Cannot create ZIP archive: at least one file required")

        # Validate all files exist before creating archive
        for file_path in files:
            if not file_path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")

        # Create ZIP archive
        with zipfile.ZipFile(
            output_path,
            mode="w",
            compression=self.compression,
            compresslevel=self.compression_level,
        ) as zf:
            for file_path in files:
                # Store only the filename, not the full path
                # This keeps the ZIP structure flat and simple
                arcname = file_path.name
                zf.write(file_path, arcname=arcname)

        return output_path

    def create_temporary_zip(
        self,
        files: Sequence[pathlib.Path],
        prefix: str = "transcriptions_",
        suffix: str = ".zip",
    ) -> pathlib.Path:
        """Create a temporary ZIP archive with auto-generated filename.

        The temporary file is created in the system's temp directory
        and will persist until manually deleted. Delegates to create_zip()
        for actual archive creation.

        Args:
            files: Sequence of file paths to include in the archive.
            prefix: Filename prefix (default: "transcriptions_").
            suffix: Filename suffix (default: ".zip").

        Returns:
            Path to the created temporary ZIP archive.

        Note:
            Propagates ValueError and FileNotFoundError from create_zip().

        Examples:
            >>> creator = ZipCreator()
            >>> files = [Path("output.srt")]
            >>> temp_zip = creator.create_temporary_zip(files)
            >>> temp_zip.name.startswith("transcriptions_")
            True
            >>> temp_zip.suffix
            '.zip'
        """
        # Create temporary file with delete=False so it persists
        with tempfile.NamedTemporaryFile(
            mode="wb",
            prefix=prefix,
            suffix=suffix,
            delete=False,
        ) as tmp_file:
            temp_path = pathlib.Path(tmp_file.name)

        # Create the ZIP archive at the temporary location
        return self.create_zip(files, temp_path)
