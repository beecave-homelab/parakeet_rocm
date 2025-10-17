"""Unit tests for validation.file_validator module.

Tests file validation utilities for audio/video files and
output directories with comprehensive error handling.
"""

from __future__ import annotations

import pathlib

import pytest

from parakeet_rocm.webui.validation.file_validator import (
    FileValidationError,
    validate_audio_file,
    validate_audio_files,
    validate_output_directory,
)


class TestValidateAudioFile:
    """Test validate_audio_file function."""

    def test_valid_wav_file__returns_path(self, tmp_path: pathlib.Path) -> None:
        """Valid WAV file should pass validation."""
        audio_file = tmp_path / "test.wav"
        audio_file.write_bytes(b"fake wav content")

        result = validate_audio_file(audio_file)

        assert result == audio_file
        assert isinstance(result, pathlib.Path)

    def test_valid_mp3_file__returns_path(self, tmp_path: pathlib.Path) -> None:
        """Valid MP3 file should pass validation."""
        audio_file = tmp_path / "test.mp3"
        audio_file.write_bytes(b"fake mp3 content")

        result = validate_audio_file(audio_file)

        assert result == audio_file

    def test_valid_mp4_video__returns_path(self, tmp_path: pathlib.Path) -> None:
        """Valid MP4 video file should pass validation."""
        video_file = tmp_path / "test.mp4"
        video_file.write_bytes(b"fake mp4 content")

        result = validate_audio_file(video_file)

        assert result == video_file

    def test_nonexistent_file__raises_validation_error(
        self, tmp_path: pathlib.Path
    ) -> None:
        """Non-existent file should fail validation."""
        nonexistent = tmp_path / "nonexistent.wav"

        with pytest.raises(FileValidationError) as exc_info:
            validate_audio_file(nonexistent)

        assert "does not exist" in str(exc_info.value).lower()

    def test_directory_not_file__raises_validation_error(
        self, tmp_path: pathlib.Path
    ) -> None:
        """Directory should fail validation."""
        directory = tmp_path / "subdir"
        directory.mkdir()

        with pytest.raises(FileValidationError) as exc_info:
            validate_audio_file(directory)

        assert "not a file" in str(exc_info.value).lower()

    def test_unsupported_extension__raises_validation_error(
        self, tmp_path: pathlib.Path
    ) -> None:
        """File with unsupported extension should fail validation."""
        invalid_file = tmp_path / "test.txt"
        invalid_file.write_text("not audio")

        with pytest.raises(FileValidationError) as exc_info:
            validate_audio_file(invalid_file)

        assert "unsupported" in str(exc_info.value).lower()

    def test_empty_file__raises_validation_error(self, tmp_path: pathlib.Path) -> None:
        """Empty file should fail validation."""
        empty_file = tmp_path / "empty.wav"
        empty_file.touch()

        with pytest.raises(FileValidationError) as exc_info:
            validate_audio_file(empty_file)

        assert "empty" in str(exc_info.value).lower()

    def test_case_insensitive_extension__returns_path(
        self, tmp_path: pathlib.Path
    ) -> None:
        """File extensions should be case-insensitive."""
        audio_file = tmp_path / "test.WAV"
        audio_file.write_bytes(b"fake wav content")

        result = validate_audio_file(audio_file)

        assert result == audio_file


class TestValidateAudioFiles:
    """Test validate_audio_files function for batch validation."""

    def test_multiple_valid_files__returns_all_paths(
        self, tmp_path: pathlib.Path
    ) -> None:
        """Multiple valid files should all pass validation."""
        files = []
        for i in range(3):
            f = tmp_path / f"audio_{i}.wav"
            f.write_bytes(b"fake content")
            files.append(f)

        results = validate_audio_files(files)

        assert len(results) == 3
        assert all(f in results for f in files)

    def test_empty_list__raises_validation_error(self) -> None:
        """Empty file list should fail validation."""
        with pytest.raises(FileValidationError) as exc_info:
            validate_audio_files([])

        assert "no files" in str(exc_info.value).lower()

    def test_mixed_valid_invalid__raises_on_first_invalid(
        self, tmp_path: pathlib.Path
    ) -> None:
        """Should fail on first invalid file in batch."""
        valid_file = tmp_path / "valid.wav"
        valid_file.write_bytes(b"content")
        invalid_file = tmp_path / "nonexistent.wav"

        with pytest.raises(FileValidationError):
            validate_audio_files([valid_file, invalid_file])

    def test_duplicate_files__accepted(self, tmp_path: pathlib.Path) -> None:
        """Duplicate file paths should be accepted."""
        audio_file = tmp_path / "audio.wav"
        audio_file.write_bytes(b"fake content")

        results = validate_audio_files([audio_file, audio_file])

        assert len(results) == 2
        assert results[0] == results[1]


class TestValidateOutputDirectory:
    """Test validate_output_directory function."""

    def test_existing_directory__returns_path(self, tmp_path: pathlib.Path) -> None:
        """Existing directory should pass validation."""
        result = validate_output_directory(tmp_path)

        assert result == tmp_path
        assert result.is_dir()

    def test_nonexistent_directory__creates_and_returns(
        self, tmp_path: pathlib.Path
    ) -> None:
        """Non-existent directory should be created."""
        new_dir = tmp_path / "new_output"

        result = validate_output_directory(new_dir)

        assert result == new_dir
        assert result.exists()
        assert result.is_dir()

    def test_nested_directory__creates_parents(self, tmp_path: pathlib.Path) -> None:
        """Nested directory should create all parent directories."""
        nested_dir = tmp_path / "a" / "b" / "c"

        result = validate_output_directory(nested_dir)

        assert result == nested_dir
        assert result.exists()
        assert result.is_dir()

    def test_file_not_directory__raises_validation_error(
        self, tmp_path: pathlib.Path
    ) -> None:
        """Existing file (not directory) should fail validation."""
        file_path = tmp_path / "not_a_dir.txt"
        file_path.write_text("content")

        with pytest.raises(FileValidationError) as exc_info:
            validate_output_directory(file_path)

        assert "not a directory" in str(exc_info.value).lower()

    def test_permission_denied__raises_validation_error(
        self, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Permission denied should raise validation error."""
        restricted_dir = tmp_path / "restricted"

        # Mock mkdir to raise PermissionError
        def mock_mkdir(*args, **kwargs) -> None:  # type: ignore[misc]
            raise PermissionError("Permission denied")

        monkeypatch.setattr(pathlib.Path, "mkdir", mock_mkdir)

        with pytest.raises(FileValidationError) as exc_info:
            validate_output_directory(restricted_dir)

        assert "permission" in str(exc_info.value).lower()

    def test_string_path__converts_to_pathlib(self, tmp_path: pathlib.Path) -> None:
        """String path should be converted to Path object."""
        result = validate_output_directory(str(tmp_path))

        assert isinstance(result, pathlib.Path)
        assert result == tmp_path
