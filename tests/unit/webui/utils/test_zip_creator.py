"""Unit tests for ZipCreator class.

Tests for creating ZIP archives from multiple files for bulk downloads.
"""

from __future__ import annotations

import pathlib
import zipfile

import pytest

from parakeet_rocm.webui.utils.zip_creator import ZipCreator


class TestZipCreator:
    """Test suite for ZipCreator class."""

    def test_create_zip_from_single_file(self, tmp_path: pathlib.Path) -> None:
        """Test creating a ZIP archive from a single file.

        Args:
            tmp_path: Pytest temporary directory fixture.
        """
        # Arrange
        source_file = tmp_path / "test.txt"
        source_file.write_text("Hello, World!")
        output_zip = tmp_path / "output.zip"

        creator = ZipCreator()

        # Act
        result = creator.create_zip([source_file], output_zip)

        # Assert
        assert result == output_zip
        assert output_zip.exists()
        assert zipfile.is_zipfile(output_zip)

        # Verify contents
        with zipfile.ZipFile(output_zip, "r") as zf:
            assert "test.txt" in zf.namelist()
            assert zf.read("test.txt").decode() == "Hello, World!"

    def test_create_zip_from_multiple_files(self, tmp_path: pathlib.Path) -> None:
        """Test creating a ZIP archive from multiple files.

        Args:
            tmp_path: Pytest temporary directory fixture.
        """
        # Arrange
        file1 = tmp_path / "file1.srt"
        file2 = tmp_path / "file2.srt"
        file1.write_text("Subtitle 1")
        file2.write_text("Subtitle 2")
        output_zip = tmp_path / "bulk.zip"

        creator = ZipCreator()

        # Act
        result = creator.create_zip([file1, file2], output_zip)

        # Assert
        assert result == output_zip
        assert output_zip.exists()

        with zipfile.ZipFile(output_zip, "r") as zf:
            assert len(zf.namelist()) == 2
            assert "file1.srt" in zf.namelist()
            assert "file2.srt" in zf.namelist()
            assert zf.read("file1.srt").decode() == "Subtitle 1"
            assert zf.read("file2.srt").decode() == "Subtitle 2"

    def test_create_zip_with_nested_paths(self, tmp_path: pathlib.Path) -> None:
        """Test creating a ZIP archive preserving directory structure.

        Args:
            tmp_path: Pytest temporary directory fixture.
        """
        # Arrange
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        file1 = tmp_path / "root.txt"
        file2 = subdir / "nested.txt"
        file1.write_text("Root file")
        file2.write_text("Nested file")
        output_zip = tmp_path / "nested.zip"

        creator = ZipCreator()

        # Act
        result = creator.create_zip([file1, file2], output_zip)

        # Assert
        assert result == output_zip
        with zipfile.ZipFile(output_zip, "r") as zf:
            # Should store only filename, not full path
            assert "root.txt" in zf.namelist()
            assert "nested.txt" in zf.namelist()

    def test_create_zip_empty_file_list_raises_error(
        self, tmp_path: pathlib.Path
    ) -> None:
        """Test that creating a ZIP from empty file list raises ValueError.

        Args:
            tmp_path: Pytest temporary directory fixture.
        """
        # Arrange
        output_zip = tmp_path / "empty.zip"
        creator = ZipCreator()

        # Act & Assert
        with pytest.raises(ValueError, match="at least one file"):
            creator.create_zip([], output_zip)

    def test_create_zip_nonexistent_file_raises_error(
        self, tmp_path: pathlib.Path
    ) -> None:
        """Test that creating a ZIP from nonexistent file raises FileNotFoundError.

        Args:
            tmp_path: Pytest temporary directory fixture.
        """
        # Arrange
        nonexistent = tmp_path / "does_not_exist.txt"
        output_zip = tmp_path / "output.zip"
        creator = ZipCreator()

        # Act & Assert
        with pytest.raises(FileNotFoundError):
            creator.create_zip([nonexistent], output_zip)

    def test_create_zip_overwrites_existing_file(self, tmp_path: pathlib.Path) -> None:
        """Test that creating a ZIP overwrites existing output file.

        Args:
            tmp_path: Pytest temporary directory fixture.
        """
        # Arrange
        source_file = tmp_path / "test.txt"
        source_file.write_text("New content")
        output_zip = tmp_path / "output.zip"
        output_zip.write_text("Old content")

        creator = ZipCreator()

        # Act
        result = creator.create_zip([source_file], output_zip)

        # Assert
        assert result == output_zip
        assert zipfile.is_zipfile(output_zip)

    def test_create_zip_with_custom_archive_name(self, tmp_path: pathlib.Path) -> None:
        """Test creating a ZIP with custom archive name prefix.

        Args:
            tmp_path: Pytest temporary directory fixture.
        """
        # Arrange
        file1 = tmp_path / "audio1.srt"
        file1.write_text("Subtitle 1")
        output_zip = tmp_path / "transcriptions.zip"

        creator = ZipCreator()

        # Act
        result = creator.create_zip([file1], output_zip)

        # Assert
        assert result.name == "transcriptions.zip"
        assert result.exists()

    def test_create_zip_compression_level(self, tmp_path: pathlib.Path) -> None:
        """Test that ZIP uses compression.

        Args:
            tmp_path: Pytest temporary directory fixture.
        """
        # Arrange
        large_file = tmp_path / "large.txt"
        large_file.write_text("A" * 10000)  # 10KB of 'A's
        output_zip = tmp_path / "compressed.zip"

        creator = ZipCreator()

        # Act
        result = creator.create_zip([large_file], output_zip)

        # Assert
        # Compressed size should be much smaller than original
        original_size = large_file.stat().st_size
        compressed_size = result.stat().st_size
        assert compressed_size < original_size / 2  # At least 50% compression

    def test_create_zip_preserves_file_extensions(self, tmp_path: pathlib.Path) -> None:
        """Test that ZIP preserves various file extensions.

        Args:
            tmp_path: Pytest temporary directory fixture.
        """
        # Arrange
        files = [
            tmp_path / "file.srt",
            tmp_path / "file.vtt",
            tmp_path / "file.txt",
            tmp_path / "file.json",
        ]
        for f in files:
            f.write_text(f"Content of {f.name}")
        output_zip = tmp_path / "multi_format.zip"

        creator = ZipCreator()

        # Act
        result = creator.create_zip(files, output_zip)

        # Assert
        with zipfile.ZipFile(result, "r") as zf:
            expected_files = {"file.srt", "file.vtt", "file.txt", "file.json"}
            assert set(zf.namelist()) == expected_files

    def test_create_temporary_zip(self, tmp_path: pathlib.Path) -> None:
        """Test creating a ZIP in a temporary directory with auto-naming.

        Args:
            tmp_path: Pytest temporary directory fixture.
        """
        # Arrange
        source_file = tmp_path / "test.txt"
        source_file.write_text("Test")

        creator = ZipCreator()

        # Act
        result = creator.create_temporary_zip([source_file])

        # Assert
        assert result.exists()
        assert result.suffix == ".zip"
        assert zipfile.is_zipfile(result)

        # Cleanup
        result.unlink()
