"""Security-focused tests for subtitle refiner I/O."""

from __future__ import annotations

from pathlib import Path

import pytest

from parakeet_rocm.formatting.refine import Cue, SubtitleRefiner


def test_load_srt_rejects_url_path() -> None:
    """Reject non-local URLs when loading SRT files."""
    refiner = SubtitleRefiner()
    with pytest.raises(ValueError, match="local filesystem"):
        refiner.load_srt("https://example.com/sub.srt")


def test_load_srt_rejects_missing_file(tmp_path: Path) -> None:
    """Reject nonexistent files when loading SRT files."""
    refiner = SubtitleRefiner()
    missing_path = tmp_path / "missing.srt"
    with pytest.raises(ValueError, match="does not exist"):
        refiner.load_srt(missing_path)


def test_save_srt_rejects_url_path() -> None:
    """Reject non-local URLs when saving SRT files."""
    refiner = SubtitleRefiner()
    cue = Cue(index=1, start=0.0, end=1.0, text="Hi")
    with pytest.raises(ValueError, match="local filesystem"):
        refiner.save_srt([cue], "https://example.com/out.srt")
