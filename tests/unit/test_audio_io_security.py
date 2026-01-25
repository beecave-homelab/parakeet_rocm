"""Security-focused unit tests for audio I/O helpers."""

from __future__ import annotations

import pytest

from parakeet_rocm.utils import audio_io


def test_validate_audio_path_rejects_url() -> None:
    """Reject URL-like input paths for safety."""
    with pytest.raises(ValueError, match="local filesystem"):
        audio_io._validate_audio_path("https://example.com/audio.wav")


def test_validate_audio_path_rejects_option_prefix() -> None:
    """Reject option-like paths that could be parsed as flags."""
    with pytest.raises(ValueError, match="must not start"):
        audio_io._validate_audio_path("-input.wav")


def test_validate_audio_path_allows_local_path() -> None:
    """Allow regular local filesystem paths."""
    assert audio_io._validate_audio_path("input.wav").name == "input.wav"
