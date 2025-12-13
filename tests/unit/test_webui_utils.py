"""Unit tests for WebUI utility modules."""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from parakeet_rocm.webui.utils.metrics_formatter import (
    format_gpu_stats_section,
    format_quality_section,
    format_runtime_section,
)
from parakeet_rocm.webui.utils.presets import get_preset
from parakeet_rocm.webui.utils.zip_creator import ZipCreator


def test_format_runtime_section_handles_missing_values() -> None:
    """format_runtime_section should return N/A output when missing inputs."""
    md = format_runtime_section(None, None)
    assert "N/A" in md


def test_format_runtime_section_with_overhead() -> None:
    """format_runtime_section should include overhead for wall > runtime."""
    md = format_runtime_section(10.0, 12.0)
    assert "00:10" in md
    assert "00:12" in md
    assert "overhead" in md


def test_format_runtime_section_supports_hours() -> None:
    """format_runtime_section should format HH:MM:SS durations when needed."""
    md = format_runtime_section(3725.0, 3725.0)
    assert "01:02:05" in md


def test_format_gpu_stats_section_handles_missing() -> None:
    """format_gpu_stats_section should emit an unavailable message."""
    md = format_gpu_stats_section(None)
    assert "unavailable" in md


def test_format_gpu_stats_section_formats_util_and_vram() -> None:
    """format_gpu_stats_section should format utilization and VRAM."""
    md = format_gpu_stats_section({
        "utilization_percent": {"avg": 50.0, "min": 10.0, "max": 90.0, "p95": 88.0},
        "vram_used_mb": {"avg": 2048.0, "min": 1024.0, "max": 4096.0},
    })
    assert "Utilization" in md
    assert "VRAM" in md


def test_format_quality_section_handles_missing() -> None:
    """format_quality_section should return N/A when missing."""
    md = format_quality_section(None)
    assert "N/A" in md


def test_format_quality_section_includes_fields() -> None:
    """format_quality_section should include supported keys."""
    md = format_quality_section({
        "total_segments": 3,
        "avg_duration_sec": 1.23,
        "readability_score": 90.0,
    })
    assert "Segments" in md
    assert "Avg Duration" in md
    assert "Readability Score" in md


def test_get_preset_returns_copy() -> None:
    """get_preset should deep-copy config so callers can mutate safely."""
    preset1 = get_preset("default")
    preset2 = get_preset("default")

    assert preset1 is not preset2
    assert preset1.config is not preset2.config

    preset1.config.batch_size = 123
    assert preset2.config.batch_size != 123


def test_get_preset_unknown_raises() -> None:
    """Unknown preset names should raise KeyError."""
    with pytest.raises(KeyError):
        get_preset("missing")


def test_zip_creator_create_zip_validates_inputs(tmp_path: Path) -> None:
    """ZipCreator should validate files list and existence."""
    creator = ZipCreator()

    with pytest.raises(ValueError):
        creator.create_zip([], tmp_path / "x.zip")

    with pytest.raises(FileNotFoundError):
        creator.create_zip([tmp_path / "missing.srt"], tmp_path / "x.zip")


def test_zip_creator_creates_zip(tmp_path: Path) -> None:
    """ZipCreator should write a zip with flat filenames."""
    f1 = tmp_path / "a.srt"
    f2 = tmp_path / "b.srt"
    f1.write_text("a", encoding="utf-8")
    f2.write_text("b", encoding="utf-8")

    out = tmp_path / "out.zip"
    creator = ZipCreator()
    created = creator.create_zip([f1, f2], out)

    assert created.exists()
    with zipfile.ZipFile(created) as zf:
        assert set(zf.namelist()) == {"a.srt", "b.srt"}


def test_zip_creator_creates_temporary_zip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """create_temporary_zip should return an existing zip path."""

    class _Tmp:
        def __init__(self, name: str) -> None:
            self.name = name

        def __enter__(self) -> _Tmp:
            return self

        def __exit__(
            self,
            _exc_type: type[BaseException] | None,
            _exc: BaseException | None,
            _tb: object | None,
        ) -> None:
            return None

    def fake_named_tempfile(**_kwargs: object) -> _Tmp:
        return _Tmp(str(tmp_path / "temp.zip"))

    import tempfile

    monkeypatch.setattr(tempfile, "NamedTemporaryFile", fake_named_tempfile)

    f1 = tmp_path / "a.srt"
    f1.write_text("a", encoding="utf-8")

    creator = ZipCreator()
    zip_path = creator.create_temporary_zip([f1])
    assert zip_path.exists()
