"""Unit tests for WebUI validation helpers and schemas."""

from __future__ import annotations

import pathlib
from pathlib import Path

import pytest

from parakeet_rocm.webui.validation import file_validator
from parakeet_rocm.webui.validation.schemas import FileUploadConfig, TranscriptionConfig


def test_validate_audio_file_happy_path(tmp_path: Path) -> None:
    """validate_audio_file should accept existing, non-empty supported files."""
    p = tmp_path / "a.wav"
    p.write_text("x", encoding="utf-8")
    assert file_validator.validate_audio_file(p) == p


def test_validate_audio_file_rejects_missing(tmp_path: Path) -> None:
    """validate_audio_file should raise for missing paths."""
    with pytest.raises(file_validator.FileValidationError):
        file_validator.validate_audio_file(tmp_path / "missing.wav")


def test_validate_audio_file_rejects_directory(tmp_path: Path) -> None:
    """validate_audio_file should reject directories."""
    d = tmp_path / "dir.wav"
    d.mkdir()
    with pytest.raises(file_validator.FileValidationError):
        file_validator.validate_audio_file(d)


def test_validate_audio_file_rejects_unsupported_extension(tmp_path: Path) -> None:
    """validate_audio_file should reject unsupported extensions."""
    p = tmp_path / "a.xyz"
    p.write_text("x", encoding="utf-8")
    with pytest.raises(file_validator.FileValidationError):
        file_validator.validate_audio_file(p)


def test_validate_audio_file_rejects_empty_file(tmp_path: Path) -> None:
    """validate_audio_file should reject empty files."""
    p = tmp_path / "a.wav"
    p.write_bytes(b"")
    with pytest.raises(file_validator.FileValidationError):
        file_validator.validate_audio_file(p)


def test_validate_audio_files_requires_non_empty_list() -> None:
    """validate_audio_files should raise on empty list."""
    with pytest.raises(file_validator.FileValidationError):
        file_validator.validate_audio_files([])


def test_validate_audio_files_converts_and_validates(tmp_path: Path) -> None:
    """validate_audio_files should validate all entries."""
    p1 = tmp_path / "a.wav"
    p2 = tmp_path / "b.mp3"
    p1.write_text("x", encoding="utf-8")
    p2.write_text("y", encoding="utf-8")

    validated = file_validator.validate_audio_files([str(p1), p2])
    assert validated == [p1, p2]


def test_validate_output_directory_creates(tmp_path: Path) -> None:
    """validate_output_directory should create missing directory."""
    target = tmp_path / "out"
    validated = file_validator.validate_output_directory(target)
    assert validated.exists()
    assert validated.is_dir()


def test_validate_output_directory_accepts_string_path(tmp_path: Path) -> None:
    """validate_output_directory should accept string inputs."""
    target = tmp_path / "out_str"
    validated = file_validator.validate_output_directory(str(target))
    assert validated == target


def test_validate_output_directory_rejects_file(tmp_path: Path) -> None:
    """validate_output_directory should reject file paths."""
    p = tmp_path / "out"
    p.write_text("x", encoding="utf-8")
    with pytest.raises(file_validator.FileValidationError):
        file_validator.validate_output_directory(p)


def test_validate_output_directory_permission_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """validate_output_directory should wrap PermissionError as FileValidationError."""
    target = tmp_path / "no_perm"

    def raise_perm(*_args: object, **_kwargs: object) -> None:
        raise PermissionError("no")

    monkeypatch.setattr(pathlib.Path, "mkdir", raise_perm)
    with pytest.raises(file_validator.FileValidationError):
        file_validator.validate_output_directory(target)


def test_validate_output_directory_os_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """validate_output_directory should wrap OSError as FileValidationError."""
    target = tmp_path / "os_err"

    def raise_os(*_args: object, **_kwargs: object) -> None:
        raise OSError("no")

    monkeypatch.setattr(pathlib.Path, "mkdir", raise_os)
    with pytest.raises(file_validator.FileValidationError):
        file_validator.validate_output_directory(target)


def test_transcription_config_stream_chunk_validation() -> None:
    """TranscriptionConfig should validate stream chunk size constraints."""
    assert TranscriptionConfig(stream_chunk_sec=0).stream_chunk_sec == 0

    with pytest.raises(ValueError):
        TranscriptionConfig(stream_chunk_sec=4)

    with pytest.raises(ValueError):
        TranscriptionConfig(stream_chunk_sec=31)


def test_transcription_config_precision_flags() -> None:
    """TranscriptionConfig should normalize precision flags."""
    cfg = TranscriptionConfig(fp16=True, fp32=True)
    assert cfg.fp16 is True
    assert cfg.fp32 is False

    cfg2 = TranscriptionConfig(fp16=False, fp32=False)
    assert cfg2.fp16 is True


def test_file_upload_config_converts_paths(tmp_path: Path) -> None:
    """FileUploadConfig should convert strings into Paths."""
    p = tmp_path / "a.wav"
    cfg = FileUploadConfig(files=[str(p)])
    assert cfg.files == [p]
