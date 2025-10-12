"""Unit tests for configuration dataclasses."""

from __future__ import annotations

from pathlib import Path

from parakeet_rocm.config import (
    OutputConfig,
    StabilizationConfig,
    TranscriptionConfig,
    UIConfig,
)
from parakeet_rocm.utils.constant import DEFAULT_BATCH_SIZE, DEFAULT_CHUNK_LEN_SEC


def test_transcription_config_defaults() -> None:
    """Test TranscriptionConfig default values."""
    config = TranscriptionConfig()
    # Verify defaults match project constants (which may be overridden by .env)
    assert config.batch_size == DEFAULT_BATCH_SIZE
    assert config.chunk_len_sec == DEFAULT_CHUNK_LEN_SEC
    assert config.overlap_duration == 15
    assert config.word_timestamps is False
    assert config.merge_strategy == "lcs"


def test_transcription_config_custom_values() -> None:
    """Test TranscriptionConfig with custom values."""
    config = TranscriptionConfig(
        batch_size=8,
        chunk_len_sec=120,
        overlap_duration=10,
        word_timestamps=True,
        merge_strategy="contiguous",
    )
    assert config.batch_size == 8
    assert config.chunk_len_sec == 120
    assert config.overlap_duration == 10
    assert config.word_timestamps is True
    assert config.merge_strategy == "contiguous"


def test_stabilization_config_defaults() -> None:
    """Test StabilizationConfig default values."""
    config = StabilizationConfig()
    assert config.enabled is False
    assert config.demucs is False
    assert config.vad is False
    assert config.vad_threshold == 0.35


def test_stabilization_config_custom_values() -> None:
    """Test StabilizationConfig with custom values."""
    config = StabilizationConfig(
        enabled=True,
        demucs=True,
        vad=True,
        vad_threshold=0.5,
    )
    assert config.enabled is True
    assert config.demucs is True
    assert config.vad is True
    assert config.vad_threshold == 0.5


def test_output_config_required_fields() -> None:
    """Test OutputConfig requires certain fields."""
    config = OutputConfig(
        output_dir=Path("/tmp/output"),
        output_format="srt",
        output_template="{filename}",
    )
    assert config.output_dir == Path("/tmp/output")
    assert config.output_format == "srt"
    assert config.output_template == "{filename}"
    assert config.overwrite is False
    assert config.highlight_words is False


def test_output_config_custom_values() -> None:
    """Test OutputConfig with custom values."""
    config = OutputConfig(
        output_dir=Path("/custom/path"),
        output_format="vtt",
        output_template="{index}_{filename}",
        overwrite=True,
        highlight_words=True,
    )
    assert config.output_dir == Path("/custom/path")
    assert config.output_format == "vtt"
    assert config.output_template == "{index}_{filename}"
    assert config.overwrite is True
    assert config.highlight_words is True


def test_ui_config_defaults() -> None:
    """Test UIConfig default values."""
    config = UIConfig()
    assert config.verbose is False
    assert config.quiet is False
    assert config.no_progress is False


def test_ui_config_custom_values() -> None:
    """Test UIConfig with custom values."""
    config = UIConfig(
        verbose=True,
        quiet=False,
        no_progress=True,
    )
    assert config.verbose is True
    assert config.quiet is False
    assert config.no_progress is True


def test_config_objects_are_dataclasses() -> None:
    """Test that config objects are proper dataclasses."""
    from dataclasses import is_dataclass

    assert is_dataclass(TranscriptionConfig)
    assert is_dataclass(StabilizationConfig)
    assert is_dataclass(OutputConfig)
    assert is_dataclass(UIConfig)


def test_config_objects_support_equality() -> None:
    """Test that config objects support equality comparison."""
    config1 = TranscriptionConfig(batch_size=8)
    config2 = TranscriptionConfig(batch_size=8)
    config3 = TranscriptionConfig(batch_size=12)

    assert config1 == config2
    assert config1 != config3


def test_config_objects_are_immutable_by_convention() -> None:
    """Test that config objects can be modified (dataclasses are mutable by default).

    Note:
        Dataclasses are mutable by default. If immutability is desired,
        use frozen=True in the dataclass decorator.

    """
    config = TranscriptionConfig(batch_size=8)
    # Dataclasses are mutable by default
    config.batch_size = 16
    assert config.batch_size == 16
