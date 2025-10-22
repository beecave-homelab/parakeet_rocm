from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from typer.testing import CliRunner, Result

try:  # pragma: no cover - handled in tests
    import parakeet_rocm.cli as cli_module
    from parakeet_rocm.cli import app as cli_app
except ModuleNotFoundError:  # pragma: no cover
    cli_app = None
    cli_module = None
    pytest.skip("parakeet_rocm package not importable", allow_module_level=True)


def _invoke_cli(*args: str) -> Result:
    runner = CliRunner()
    return runner.invoke(cli_app, ["transcribe", *args])


@pytest.mark.unit
def test_cli__benchmark_writes_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """CLI with --benchmark should persist a JSON file to the given directory.

    The test avoids running the heavy transcription by monkeypatching the
    delegated implementation in parakeet_rocm.transcribe. It also bypasses
    real file resolution.
    """
    # Stub RESOLVE_INPUT_PATHS to avoid filesystem dependencies
    monkeypatch.setattr(
        cli_module,
        "RESOLVE_INPUT_PATHS",
        lambda paths: [tmp_path / "fake.wav"],
        raising=False,
    )

    # Stub transcribe implementation to be fast and return a path
    def _fake_cli_transcribe(**kwargs: object) -> list[Path]:  # noqa: ANN401
        outdir = kwargs.get("output_dir", tmp_path)
        fmt = kwargs.get("output_format", "txt")
        p = Path(outdir) / f"stub_output.{fmt}"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("ok", encoding="utf-8")
        # Ensure collector path is exercised
        collector = kwargs.get("collector")
        if collector is not None:
            # Provide minimal per-file metrics to make JSON more realistic
            if hasattr(collector, "add_file_metrics"):
                collector.add_file_metrics(
                    filename="fake.wav",
                    duration_sec=1.0,
                    segment_count=1,
                    processing_time_sec=0.0,
                )
        return [p]

    def _fake_import_module(name: str) -> SimpleNamespace:
        if name == "parakeet_rocm.transcribe":
            return SimpleNamespace(cli_transcribe=_fake_cli_transcribe)
        raise ImportError(name)

    monkeypatch.setattr(
        cli_module, "import_module", _fake_import_module, raising=True
    )

    bench_dir = tmp_path / "bench"
    res = _invoke_cli(
        str(tmp_path / "fake.wav"),
        "--output-dir",
        str(tmp_path / "out"),
        "--output-format",
        "txt",
        "--benchmark",
        "--benchmark-output-dir",
        str(bench_dir),
        "--gpu-sampler-interval-sec",
        "0.01",
    )

    assert res.exit_code == 0, res.stderr
    files = list(bench_dir.glob("*.json"))
    assert files, "Benchmark JSON not written"

    data = json.loads(files[0].read_text(encoding="utf-8"))
    # Top-level fields set by BenchmarkCollector and CLI wrapper
    assert "slug" in data and "timestamp" in data
    assert data.get("task") == "transcribe"
    assert "config" in data and isinstance(data["config"], dict)
    assert "gpu_stats" in data  # may be empty dict when sampler yields no data
    assert "files" in data and isinstance(data["files"], list)


@pytest.mark.unit
def test_cli__benchmark_defaults_to_env_dir_when_not_set(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When --benchmark is used without explicit output dir.

    The CLI should default to the BENCHMARK_OUTPUT_DIR from constants.
    """
    # Point BENCHMARK_OUTPUT_DIR to tmp_path/auto
    from parakeet_rocm import utils as _utils_pkg  # type: ignore  # noqa: F401
    from parakeet_rocm.utils import constant as constants

    monkeypatch.setattr(
        constants, "BENCHMARK_OUTPUT_DIR", tmp_path / "auto", raising=True
    )

    # Stubs
    monkeypatch.setattr(
        cli_module,
        "RESOLVE_INPUT_PATHS",
        lambda paths: [tmp_path / "fake.wav"],
        raising=False,
    )

    def _fake_cli_transcribe(**kwargs: object) -> list[Path]:  # noqa: ANN401
        return [tmp_path / "out" / "out.txt"]

    def _fake_import_module(name: str) -> SimpleNamespace:
        if name == "parakeet_rocm.transcribe":
            return SimpleNamespace(cli_transcribe=_fake_cli_transcribe)
        raise ImportError(name)

    monkeypatch.setattr(cli_module, "import_module", _fake_import_module, raising=True)

    res = _invoke_cli(
        str(tmp_path / "fake.wav"), "--output-format", "txt", "--benchmark"
    )
    assert res.exit_code == 0, res.stderr
    files = list((tmp_path / "auto").glob("*.json"))
    assert files, "Benchmark JSON not written to default BENCHMARK_OUTPUT_DIR"
