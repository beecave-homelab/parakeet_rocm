"""Unit tests for the WebUI JobManager.

These tests stub out the transcription stack so the WebUI job manager can be
exercised without importing NeMo.
"""

from __future__ import annotations

import importlib
import sys
import types
from pathlib import Path

import pytest


class _FakeSampler:
    """Fake GPU sampler used to avoid starting real background threads."""

    def __init__(self, interval_sec: float) -> None:  # noqa: ARG002
        self.started = False
        self.stopped = False

    def start(self) -> None:
        self.started = True

    def stop(self) -> None:
        self.stopped = True

    def get_stats(self) -> dict[str, object]:
        return {"provider": "fake", "sample_count": 0}


class _FakeCollector:
    """Fake benchmark collector for the job manager."""

    def __init__(
        self,
        *,
        output_dir: Path,
        slug: str,
        config: dict[str, object],
        audio_path: str | None,
        task: str,
    ) -> None:
        self.output_dir = output_dir
        self.slug = slug
        self.metrics: dict[str, object] = {
            "config": config,
            "audio_path": audio_path,
            "task": task,
            "format_quality": {},
            "runtime_seconds": 0.0,
            "total_wall_seconds": 0.0,
            "gpu_stats": {},
        }

    def write_json(self) -> Path:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        path = self.output_dir / f"{self.slug}.json"
        path.write_text("{}", encoding="utf-8")
        return path


def _install_fake_transcription(monkeypatch: pytest.MonkeyPatch) -> None:
    """Install a fake `parakeet_rocm.transcription` module.

    Args:
        monkeypatch: Pytest monkeypatch fixture.
    """
    fake_pkg = types.ModuleType("parakeet_rocm.transcription")

    def cli_transcribe(**_kwargs: object) -> list[Path]:
        return []

    fake_pkg.cli_transcribe = cli_transcribe
    monkeypatch.setitem(sys.modules, "parakeet_rocm.transcription", fake_pkg)


def test_job_manager_run_job_success_no_benchmarks(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """JobManager should complete a job and populate metrics when benchmarks disabled."""
    _install_fake_transcription(monkeypatch)
    sys.modules.pop("parakeet_rocm.webui.core.job_manager", None)

    job_manager_mod = importlib.import_module("parakeet_rocm.webui.core.job_manager")
    config = importlib.import_module("parakeet_rocm.webui.validation.schemas").TranscriptionConfig(
        output_dir=tmp_path,
        output_format="srt",
        allow_unsafe_filenames=True,
    )

    outputs = [tmp_path / "out.srt"]

    def transcribe_fn(**kwargs: object) -> list[Path]:
        assert kwargs["no_progress"] is True
        assert kwargs["quiet"] is True
        assert kwargs["verbose"] is False
        assert kwargs["allow_unsafe_filenames"] is True
        return outputs

    manager = job_manager_mod.JobManager(transcribe_fn=transcribe_fn, enable_benchmarks=False)
    job = manager.submit_job(files=[tmp_path / "in.wav"], config=config)
    result = manager.run_job(job.job_id)

    assert result.status == job_manager_mod.JobStatus.COMPLETED
    assert result.outputs == outputs
    assert result.progress == 100.0
    assert result.runtime_seconds is not None
    assert result.total_wall_seconds is not None
    assert result.metrics is not None

    assert manager.get_last_completed_job() is result
    assert manager.get_current_job() is None


def test_job_manager_run_job_success_with_benchmarks(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """JobManager should start sampler and write benchmark JSON when enabled."""
    _install_fake_transcription(monkeypatch)
    sys.modules.pop("parakeet_rocm.webui.core.job_manager", None)

    job_manager_mod = importlib.import_module("parakeet_rocm.webui.core.job_manager")

    monkeypatch.setattr(job_manager_mod, "BenchmarkCollector", _FakeCollector)
    monkeypatch.setattr(job_manager_mod, "GpuUtilSampler", _FakeSampler)
    monkeypatch.setattr(job_manager_mod, "BENCHMARK_OUTPUT_DIR", tmp_path)

    config = importlib.import_module("parakeet_rocm.webui.validation.schemas").TranscriptionConfig(
        output_dir=tmp_path,
        output_format="srt",
    )

    def transcribe_fn(**kwargs: object) -> list[Path]:
        cb = kwargs.get("progress_callback")
        assert cb is not None
        cb(1, 2)
        cb(2, 2)
        collector = kwargs.get("collector")
        assert collector is not None
        collector.metrics["format_quality"] = {"srt": {"score": 1.0}}
        return [tmp_path / "out.srt"]

    manager = job_manager_mod.JobManager(transcribe_fn=transcribe_fn, enable_benchmarks=True)
    job = manager.submit_job(files=[tmp_path / "in.wav"], config=config)

    def progress_cb(cur: int, total: int) -> None:
        assert 0 < cur <= total

    result = manager.run_job(job.job_id, progress_callback=progress_cb)

    assert result.status == job_manager_mod.JobStatus.COMPLETED
    assert result.benchmark_path is not None
    assert result.benchmark_path.exists()
    assert result.gpu_stats is not None
    assert result.format_quality == {"srt": {"score": 1.0}}


def test_job_manager_run_job_failure_sets_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """JobManager should mark job as FAILED and set error when transcribe raises."""
    _install_fake_transcription(monkeypatch)
    sys.modules.pop("parakeet_rocm.webui.core.job_manager", None)

    job_manager_mod = importlib.import_module("parakeet_rocm.webui.core.job_manager")

    monkeypatch.setattr(job_manager_mod, "BenchmarkCollector", _FakeCollector)
    monkeypatch.setattr(job_manager_mod, "GpuUtilSampler", _FakeSampler)
    monkeypatch.setattr(job_manager_mod, "BENCHMARK_OUTPUT_DIR", tmp_path)

    config = importlib.import_module("parakeet_rocm.webui.validation.schemas").TranscriptionConfig(
        output_dir=tmp_path,
        output_format="srt",
    )

    def transcribe_fn(**_kwargs: object) -> list[Path]:
        raise RuntimeError("boom")

    manager = job_manager_mod.JobManager(transcribe_fn=transcribe_fn, enable_benchmarks=True)
    job = manager.submit_job(files=[tmp_path / "in.wav"], config=config)
    result = manager.run_job(job.job_id)

    assert result.status == job_manager_mod.JobStatus.FAILED
    assert result.error == "boom"


def test_job_manager_list_jobs_orders_newest_first(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """list_jobs should return jobs in reverse chronological order."""
    _install_fake_transcription(monkeypatch)
    sys.modules.pop("parakeet_rocm.webui.core.job_manager", None)

    job_manager_mod = importlib.import_module("parakeet_rocm.webui.core.job_manager")
    config = importlib.import_module("parakeet_rocm.webui.validation.schemas").TranscriptionConfig(
        output_dir=tmp_path,
        output_format="srt",
    )

    manager = job_manager_mod.JobManager(transcribe_fn=lambda **_k: [], enable_benchmarks=False)

    job1 = manager.submit_job(files=[tmp_path / "a.wav"], config=config)
    job2 = manager.submit_job(files=[tmp_path / "b.wav"], config=config)
    jobs = manager.list_jobs()

    assert jobs[0] == job2
    assert jobs[1] == job1


def test_job_manager_get_job_returns_registered_job(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """get_job should return the same job object stored in manager."""
    _install_fake_transcription(monkeypatch)
    sys.modules.pop("parakeet_rocm.webui.core.job_manager", None)

    job_manager_mod = importlib.import_module("parakeet_rocm.webui.core.job_manager")
    config = importlib.import_module("parakeet_rocm.webui.validation.schemas").TranscriptionConfig(
        output_dir=tmp_path,
        output_format="srt",
    )

    manager = job_manager_mod.JobManager(transcribe_fn=lambda **_k: [], enable_benchmarks=False)
    job = manager.submit_job(files=[tmp_path / "a.wav"], config=config)

    assert manager.get_job(job.job_id) is job
