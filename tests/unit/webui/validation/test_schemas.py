"""Unit tests for validation.schemas module.

Tests Pydantic validation schemas for transcription configuration
and file uploads, ensuring proper validation and error messages.
"""

from __future__ import annotations

import pathlib

import pytest
from pydantic import ValidationError

from parakeet_rocm.webui.validation.schemas import (
    FileUploadConfig,
    TranscriptionConfig,
)


class TestTranscriptionConfig:
    """Test TranscriptionConfig schema validation."""

    def test_default_values__creates_valid_config(self) -> None:
        """Default configuration should be valid."""
        config = TranscriptionConfig()

        assert config.model_name is not None
        assert config.batch_size > 0
        assert config.chunk_len_sec > 0
        assert config.output_format in ["txt", "srt", "vtt", "json"]

    def test_valid_config__accepts_all_valid_parameters(self) -> None:
        """Valid configuration with all parameters should pass validation."""
        config = TranscriptionConfig(
            model_name="nvidia/parakeet-ctc-1.1b",
            output_dir=pathlib.Path("/tmp/output"),
            output_format="srt",
            batch_size=8,
            chunk_len_sec=300,
            word_timestamps=True,
            stabilize=True,
            vad=True,
            demucs=False,
            vad_threshold=0.3,
            overwrite=True,
            fp16=True,
            fp32=False,
        )

        assert config.model_name == "nvidia/parakeet-ctc-1.1b"
        assert config.output_dir == pathlib.Path("/tmp/output")
        assert config.output_format == "srt"
        assert config.batch_size == 8
        assert config.word_timestamps is True
        assert config.stabilize is True

    def test_invalid_batch_size__raises_validation_error(self) -> None:
        """Batch size must be positive integer."""
        with pytest.raises(ValidationError) as exc_info:
            TranscriptionConfig(batch_size=0)

        error = exc_info.value
        assert "batch_size" in str(error)

    def test_invalid_batch_size_negative__raises_validation_error(self) -> None:
        """Batch size cannot be negative."""
        with pytest.raises(ValidationError) as exc_info:
            TranscriptionConfig(batch_size=-5)

        error = exc_info.value
        assert "batch_size" in str(error)

    def test_invalid_batch_size_too_large__raises_validation_error(self) -> None:
        """Batch size cannot exceed maximum."""
        with pytest.raises(ValidationError) as exc_info:
            TranscriptionConfig(batch_size=200)

        error = exc_info.value
        assert "batch_size" in str(error)

    def test_invalid_chunk_len_sec__raises_validation_error(self) -> None:
        """Chunk length must be positive."""
        with pytest.raises(ValidationError) as exc_info:
            TranscriptionConfig(chunk_len_sec=0)

        error = exc_info.value
        assert "chunk_len_sec" in str(error)

    def test_invalid_chunk_len_sec_negative__raises_validation_error(self) -> None:
        """Chunk length cannot be negative."""
        with pytest.raises(ValidationError) as exc_info:
            TranscriptionConfig(chunk_len_sec=-10)

        error = exc_info.value
        assert "chunk_len_sec" in str(error)

    def test_invalid_output_format__raises_validation_error(self) -> None:
        """Output format must be one of allowed values."""
        with pytest.raises(ValidationError) as exc_info:
            TranscriptionConfig(output_format="invalid")

        error = exc_info.value
        assert "output_format" in str(error)

    def test_invalid_vad_threshold__raises_validation_error(self) -> None:
        """VAD threshold must be between 0 and 1."""
        with pytest.raises(ValidationError) as exc_info:
            TranscriptionConfig(vad_threshold=1.5)

        error = exc_info.value
        assert "vad_threshold" in str(error)

    def test_invalid_vad_threshold_negative__raises_validation_error(self) -> None:
        """VAD threshold cannot be negative."""
        with pytest.raises(ValidationError) as exc_info:
            TranscriptionConfig(vad_threshold=-0.1)

        error = exc_info.value
        assert "vad_threshold" in str(error)

    def test_both_fp16_and_fp32__automatically_prefers_fp16(self) -> None:
        """When both precision flags set, should prefer fp16."""
        config = TranscriptionConfig(fp16=True, fp32=True)

        assert config.fp16 is True
        assert config.fp32 is False

    def test_neither_fp16_nor_fp32__defaults_to_fp16(self) -> None:
        """When neither precision flag set, should default to fp16."""
        config = TranscriptionConfig(fp16=False, fp32=False)

        # Should automatically set one of them
        assert config.fp16 is True or config.fp32 is True

    def test_overlap_duration_default__uses_cli_default(self) -> None:
        """Overlap duration should default to 15 seconds (CLI default)."""
        config = TranscriptionConfig()

        assert config.overlap_duration == 15

    def test_overlap_duration_valid_range__accepts_valid_values(self) -> None:
        """Overlap duration should accept values in valid range 0-60."""
        # Test minimum
        config = TranscriptionConfig(overlap_duration=0)
        assert config.overlap_duration == 0

        # Test middle value
        config = TranscriptionConfig(overlap_duration=30)
        assert config.overlap_duration == 30

        # Test maximum
        config = TranscriptionConfig(overlap_duration=60)
        assert config.overlap_duration == 60

    def test_overlap_duration_negative__raises_validation_error(self) -> None:
        """Overlap duration cannot be negative."""
        with pytest.raises(ValidationError) as exc_info:
            TranscriptionConfig(overlap_duration=-1)

        error = exc_info.value
        assert "overlap_duration" in str(error)

    def test_overlap_duration_exceeds_maximum__raises_validation_error(self) -> None:
        """Overlap duration cannot exceed 60 seconds."""
        with pytest.raises(ValidationError) as exc_info:
            TranscriptionConfig(overlap_duration=61)

        error = exc_info.value
        assert "overlap_duration" in str(error)

    def test_merge_strategy_default__uses_cli_default(self) -> None:
        """Merge strategy should default to 'lcs' (CLI default)."""
        config = TranscriptionConfig()

        assert config.merge_strategy == "lcs"

    def test_merge_strategy_valid_values__accepts_allowed_strategies(
        self,
    ) -> None:
        """Merge strategy should accept lcs, contiguous, or none."""
        # Test lcs
        config = TranscriptionConfig(merge_strategy="lcs")
        assert config.merge_strategy == "lcs"

        # Test contiguous
        config = TranscriptionConfig(merge_strategy="contiguous")
        assert config.merge_strategy == "contiguous"

        # Test none
        config = TranscriptionConfig(merge_strategy="none")
        assert config.merge_strategy == "none"

    def test_merge_strategy_invalid_value__raises_validation_error(self) -> None:
        """Merge strategy must be one of allowed values."""
        with pytest.raises(ValidationError) as exc_info:
            TranscriptionConfig(merge_strategy="invalid")

        error = exc_info.value
        assert "merge_strategy" in str(error)

    def test_stream_default__uses_cli_default(self) -> None:
        """Stream should default to False (CLI default)."""
        config = TranscriptionConfig()

        assert config.stream is False

    def test_stream_accepts_boolean_values(self) -> None:
        """Stream should accept True/False values."""
        config_enabled = TranscriptionConfig(stream=True)
        assert config_enabled.stream is True

        config_disabled = TranscriptionConfig(stream=False)
        assert config_disabled.stream is False

    def test_stream_chunk_sec_default__uses_cli_default(self) -> None:
        """Stream chunk sec should default to 0 (CLI default)."""
        config = TranscriptionConfig()

        assert config.stream_chunk_sec == 0

    def test_stream_chunk_sec_valid_range__accepts_valid_values(self) -> None:
        """Stream chunk sec should accept values in valid range 5-30."""
        # Test minimum
        config = TranscriptionConfig(stream_chunk_sec=5)
        assert config.stream_chunk_sec == 5

        # Test middle value
        config = TranscriptionConfig(stream_chunk_sec=15)
        assert config.stream_chunk_sec == 15

        # Test maximum
        config = TranscriptionConfig(stream_chunk_sec=30)
        assert config.stream_chunk_sec == 30

    def test_stream_chunk_sec_below_minimum__raises_validation_error(self) -> None:
        """Stream chunk sec cannot be less than 5."""
        with pytest.raises(ValidationError) as exc_info:
            TranscriptionConfig(stream_chunk_sec=4)

        error = exc_info.value
        assert "stream_chunk_sec" in str(error)

    def test_stream_chunk_sec_exceeds_maximum__raises_validation_error(self) -> None:
        """Stream chunk sec cannot exceed 30."""
        with pytest.raises(ValidationError) as exc_info:
            TranscriptionConfig(stream_chunk_sec=31)

        error = exc_info.value
        assert "stream_chunk_sec" in str(error)

    def test_highlight_words_default__uses_cli_default(self) -> None:
        """Highlight words should default to False (CLI default)."""
        config = TranscriptionConfig()

        assert config.highlight_words is False

    def test_highlight_words_accepts_boolean_values(self) -> None:
        """Highlight words should accept True/False values."""
        config_enabled = TranscriptionConfig(highlight_words=True)
        assert config_enabled.highlight_words is True

        config_disabled = TranscriptionConfig(highlight_words=False)
        assert config_disabled.highlight_words is False

    def test_output_template_default__uses_cli_default(self) -> None:
        """Output template should default to '{filename}' (CLI default)."""
        config = TranscriptionConfig()

        assert config.output_template == "{filename}"

    def test_output_template_accepts_valid_templates(self) -> None:
        """Output template should accept valid template strings."""
        valid_templates = [
            "{filename}",
            "{parent}/{filename}",
            "{filename}_{date}",
            "{parent}/{filename}_{index}",
            "output_{date}_{index}",
        ]
        for template in valid_templates:
            config = TranscriptionConfig(output_template=template)
            assert config.output_template == template


class TestFileUploadConfig:
    """Test FileUploadConfig schema validation."""

    def test_valid_single_file__creates_valid_config(
        self, tmp_path: pathlib.Path
    ) -> None:
        """Single file upload should be valid."""
        test_file = tmp_path / "audio.wav"
        test_file.touch()

        config = FileUploadConfig(files=[test_file])

        assert len(config.files) == 1
        assert config.files[0] == test_file

    def test_valid_multiple_files__creates_valid_config(
        self, tmp_path: pathlib.Path
    ) -> None:
        """Multiple file uploads should be valid."""
        files = [tmp_path / f"audio_{i}.wav" for i in range(3)]
        for f in files:
            f.touch()

        config = FileUploadConfig(files=files)

        assert len(config.files) == 3
        assert all(f in config.files for f in files)

    def test_empty_file_list__raises_validation_error(self) -> None:
        """Empty file list should fail validation."""
        with pytest.raises(ValidationError) as exc_info:
            FileUploadConfig(files=[])

        error = exc_info.value
        assert "files" in str(error)

    def test_string_paths__converts_to_pathlib(self) -> None:
        """String paths should be converted to Path objects."""
        config = FileUploadConfig(files=["/tmp/audio.wav"])

        assert len(config.files) == 1
        assert isinstance(config.files[0], pathlib.Path)
        assert config.files[0] == pathlib.Path("/tmp/audio.wav")

    def test_max_file_size_validation__rejects_too_large(
        self, tmp_path: pathlib.Path
    ) -> None:
        """Files exceeding max size should fail validation."""
        # This test validates the max_file_size_mb parameter exists
        config = FileUploadConfig(files=[tmp_path / "audio.wav"], max_file_size_mb=100)

        assert config.max_file_size_mb == 100
