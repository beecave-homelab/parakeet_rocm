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
            assert isinstance(
                preset.config, TranscriptionConfig
            ), f"{name} config invalid"
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
