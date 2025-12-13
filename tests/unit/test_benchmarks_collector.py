"""Unit tests for benchmark collection utilities."""

from __future__ import annotations

import json
import sys
import types
from pathlib import Path

import pytest


def test_benchmarks_package_exports() -> None:
    """The benchmarks package should expose its public API."""
    import parakeet_rocm.benchmarks as benchmarks

    assert hasattr(benchmarks, "BenchmarkCollector")
    assert hasattr(benchmarks, "GpuUtilSampler")
    assert hasattr(benchmarks, "Sampler")


def test_benchmark_collector_writes_json(tmp_path: Path) -> None:
    """BenchmarkCollector should create directories and write JSON output."""
    from parakeet_rocm.benchmarks.collector import BenchmarkCollector

    out_dir = tmp_path / "benchmarks"
    collector = BenchmarkCollector(
        output_dir=out_dir,
        slug="my-run",
        config={"k": "v"},
    )

    collector.metrics["runtime_seconds"] = 1.23
    collector.add_file_metrics(
        "audio.wav",
        duration_sec=2.0,
        segment_count=3,
        processing_time_sec=4.0,
    )

    written = collector.write_json()
    assert written.exists()
    data = json.loads(written.read_text(encoding="utf-8"))
    assert data["config"] == {"k": "v"}
    assert data["runtime_seconds"] == 1.23
    assert data["files"][0]["filename"] == "audio.wav"


def test_benchmark_collector_slug_sanitization(tmp_path: Path) -> None:
    """Slug should be sanitized and prefixed with a timestamp."""
    from parakeet_rocm.benchmarks.collector import BenchmarkCollector

    collector = BenchmarkCollector(output_dir=tmp_path, slug="hello-world 123")
    assert "hello_world_123" in collector.slug


def test_benchmark_collector_add_quality_analysis(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Quality analysis should be stored under format_quality."""
    # Fake compute_srt_quality to avoid pulling in heavy dependencies.
    fake_mod = types.ModuleType("parakeet_rocm.formatting.srt_quality")

    def compute_srt_quality(
        segments: list[dict[str, object]],
        srt_text: str,
    ) -> dict[str, object]:
        return {"score": 0.5, "segments": len(segments), "len": len(srt_text)}

    fake_mod.compute_srt_quality = compute_srt_quality
    monkeypatch.setitem(sys.modules, "parakeet_rocm.formatting.srt_quality", fake_mod)

    from parakeet_rocm.benchmarks.collector import BenchmarkCollector

    collector = BenchmarkCollector(output_dir=tmp_path)
    collector.add_quality_analysis(
        segments=[{"start": 0.0, "end": 1.0, "text": "hi"}],
        srt_text="1\n00:00:00,000 --> 00:00:01,000\nhi\n",
        output_format="srt",
    )

    assert collector.metrics["format_quality"]["srt"]["score"] == 0.5


def test_gpu_sampler_no_dependency(monkeypatch: pytest.MonkeyPatch) -> None:
    """GpuUtilSampler should no-op when pyamdgpuinfo is unavailable."""
    import parakeet_rocm.benchmarks.collector as collector_mod

    monkeypatch.setattr(collector_mod, "pyamdgpuinfo", None)
    sampler = collector_mod.GpuUtilSampler(interval_sec=0.01)

    sampler.start()
    sampler.stop()
    assert sampler.get_stats() is None


def test_gpu_sampler_stats_computation(monkeypatch: pytest.MonkeyPatch) -> None:
    """GpuUtilSampler should aggregate samples when provider is available."""
    import parakeet_rocm.benchmarks.collector as collector_mod

    monkeypatch.setattr(collector_mod, "pyamdgpuinfo", object())
    sampler = collector_mod.GpuUtilSampler(interval_sec=0.01)

    sampler._utilization_samples = [10.0, 20.0, 30.0, 40.0, 50.0]  # noqa: SLF001
    sampler._vram_used_samples = [100.0, 200.0, 300.0, 400.0, 500.0]  # noqa: SLF001

    stats = sampler.get_stats()
    assert stats is not None
    assert stats["sample_count"] == 5
    assert stats["avg_gpu_load_percent"] == pytest.approx(30.0)
    assert stats["avg_vram_mb"] == pytest.approx(300.0)
    assert stats["utilization_percent"]["p90"] == 50.0
