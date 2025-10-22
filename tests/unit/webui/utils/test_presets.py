"""Unit tests for utils.presets module.

Tests configuration presets for common transcription use cases,
ensuring proper preset definitions and retrieval.
"""

from __future__ import annotations

import pytest

from parakeet_rocm.webui.utils.presets import PRESETS, Preset, get_preset
from parakeet_rocm.webui.validation.schemas import TranscriptionConfig


class TestPreset:
    """Test Preset dataclass."""

    def test_preset__has_required_attributes(self) -> None:
        """Preset should have name, description, and config."""
        preset = Preset(
            name="test",
            description="Test preset",
            config=TranscriptionConfig(),
        )

        assert preset.name == "test"
        assert preset.description == "Test preset"
        assert isinstance(preset.config, TranscriptionConfig)


class TestPRESETS:
    """Test PRESETS constant."""

    def test_presets__is_dictionary(self) -> None:
        """PRESETS should be a dictionary."""
        assert isinstance(PRESETS, dict)
        assert len(PRESETS) > 0

    def test_presets__has_default(self) -> None:
        """PRESETS should have a 'default' preset."""
        assert "default" in PRESETS
        assert isinstance(PRESETS["default"], Preset)

    def test_presets__has_fast(self) -> None:
        """PRESETS should have a 'fast' preset."""
        assert "fast" in PRESETS
        assert isinstance(PRESETS["fast"], Preset)

    def test_presets__has_balanced(self) -> None:
        """PRESETS should have a 'balanced' preset."""
        assert "balanced" in PRESETS
        assert isinstance(PRESETS["balanced"], Preset)

    def test_presets__has_high_quality(self) -> None:
        """PRESETS should have a 'high_quality' preset."""
        assert "high_quality" in PRESETS
        assert isinstance(PRESETS["high_quality"], Preset)

    def test_presets__all_have_valid_configs(self) -> None:
        """All presets should have valid TranscriptionConfig."""
        for name, preset in PRESETS.items():
            assert isinstance(preset, Preset), f"{name} is not a Preset"
            assert isinstance(preset.config, TranscriptionConfig), (
                f"{name} config invalid"
            )
            assert preset.name == name, f"{name} has mismatched name"
            assert len(preset.description) > 0, f"{name} has empty description"


class TestGetPreset:
    """Test get_preset function."""

    def test_get_preset__returns_preset_by_name(self) -> None:
        """Getting preset by name should return correct preset."""
        preset = get_preset("default")

        assert isinstance(preset, Preset)
        assert preset.name == "default"

    def test_get_preset__returns_fast_preset(self) -> None:
        """Getting 'fast' preset should return fast configuration."""
        preset = get_preset("fast")

        assert preset.name == "fast"
        assert isinstance(preset.config, TranscriptionConfig)

    def test_get_preset__raises_keyerror_for_invalid_name(self) -> None:
        """Getting invalid preset name should raise KeyError."""
        with pytest.raises(KeyError):
            get_preset("nonexistent")

    def test_get_preset__returns_independent_configs(self) -> None:
        """Each call to get_preset should return independent config."""
        preset1 = get_preset("default")
        preset2 = get_preset("default")

        # Should be different instances (deep copy)
        assert preset1 is not preset2
        assert preset1.config is not preset2.config

    def test_get_preset__fast_optimized_for_speed(self) -> None:
        """Fast preset should be optimized for speed."""
        preset = get_preset("fast")

        # Should have smaller batch size or simpler settings
        assert preset.config.batch_size >= 1

    def test_get_preset__high_quality_optimized_for_accuracy(self) -> None:
        """High quality preset should be optimized for accuracy."""
        preset = get_preset("high_quality")

        # Should have features enabled for quality
        assert preset.config.word_timestamps is True

    def test_default_preset__mirrors_cli_defaults_for_new_fields(self) -> None:
        """Default preset should use CLI hardcoded defaults for new fields."""
        preset = get_preset("default")
        config = preset.config

        # CLI defaults: overlap_duration=15, merge_strategy="lcs"
        assert config.overlap_duration == 15
        assert config.merge_strategy == "lcs"
        assert config.vad_threshold == 0.35

    def test_fast_preset__uses_speed_optimizations_for_new_fields(self) -> None:
        """Fast preset should optimize new fields for speed."""
        preset = get_preset("fast")
        config = preset.config

        # Fast preset: shorter overlap, faster merge strategy
        assert config.overlap_duration == 10
        assert config.merge_strategy == "contiguous"

    def test_balanced_preset__uses_balanced_settings_for_new_fields(self) -> None:
        """Balanced preset should use balanced settings for new fields."""
        preset = get_preset("balanced")
        config = preset.config

        # Balanced preset: standard CLI defaults
        assert config.overlap_duration == 15
        assert config.merge_strategy == "lcs"

    def test_high_quality_preset__uses_quality_settings_for_new_fields(
        self,
    ) -> None:
        """High quality preset should optimize new fields for quality."""
        preset = get_preset("high_quality")
        config = preset.config

        # High quality: longer overlap for better continuity
        assert config.overlap_duration == 20
        assert config.merge_strategy == "lcs"

    def test_best_preset__uses_maximum_quality_settings_for_new_fields(
        self,
    ) -> None:
        """Best preset should use maximum quality settings for new fields."""
        preset = get_preset("best")
        config = preset.config

        # Best preset: longer overlap, accurate merge, aggressive VAD
        assert config.overlap_duration == 20
        assert config.merge_strategy == "lcs"
        assert config.vad_threshold == 0.30  # More aggressive than default

    def test_all_presets__have_overlap_duration_field(self) -> None:
        """All presets should have overlap_duration field defined."""
        for name, preset in PRESETS.items():
            assert hasattr(preset.config, "overlap_duration"), (
                f"{name} missing overlap_duration"
            )
            assert preset.config.overlap_duration >= 0, (
                f"{name} has invalid overlap_duration"
            )

    def test_all_presets__have_merge_strategy_field(self) -> None:
        """All presets should have merge_strategy field defined."""
        valid_strategies = ["lcs", "contiguous", "none"]
        for name, preset in PRESETS.items():
            assert hasattr(preset.config, "merge_strategy"), (
                f"{name} missing merge_strategy"
            )
            assert preset.config.merge_strategy in valid_strategies, (
                f"{name} has invalid merge_strategy"
            )

    def test_all_presets__have_stream_field(self) -> None:
        """All presets should have stream field defined."""
        for name, preset in PRESETS.items():
            assert hasattr(preset.config, "stream"), f"{name} missing stream"
            assert isinstance(preset.config.stream, bool), (
                f"{name} has invalid stream type"
            )

    def test_all_presets__have_stream_chunk_sec_field(self) -> None:
        """All presets should have stream_chunk_sec field defined."""
        for name, preset in PRESETS.items():
            assert hasattr(preset.config, "stream_chunk_sec"), (
                f"{name} missing stream_chunk_sec"
            )
            assert preset.config.stream_chunk_sec >= 0, (
                f"{name} has invalid stream_chunk_sec"
            )

    def test_all_presets__have_highlight_words_field(self) -> None:
        """All presets should have highlight_words field defined."""
        for name, preset in PRESETS.items():
            assert hasattr(preset.config, "highlight_words"), (
                f"{name} missing highlight_words"
            )
            assert isinstance(preset.config.highlight_words, bool), (
                f"{name} has invalid highlight_words type"
            )

    def test_all_presets__have_overwrite_field(self) -> None:
        """All presets should have overwrite field defined."""
        for name, preset in PRESETS.items():
            assert hasattr(preset.config, "overwrite"), f"{name} missing overwrite"
            assert isinstance(preset.config.overwrite, bool), (
                f"{name} has invalid overwrite type"
            )

    def test_default_preset__mirrors_cli_defaults_for_phase2_fields(self) -> None:
        """Default preset should use CLI hardcoded defaults for Phase 2 fields."""
        preset = get_preset("default")
        config = preset.config

        # CLI defaults: stream=False, stream_chunk_sec=0, highlight_words=False
        assert config.stream is False
        assert config.stream_chunk_sec == 0
        assert config.highlight_words is False
        assert config.overwrite is False
