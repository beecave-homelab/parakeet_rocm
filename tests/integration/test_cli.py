"""Unit tests for CLI integration."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from typer.testing import CliRunner, Result

try:  # pragma: no cover - handled in tests
    from parakeet_rocm.cli import app as cli_app
except ModuleNotFoundError:  # pragma: no cover
    cli_app = None
    pytest.skip("parakeet_rocm package not importable", allow_module_level=True)

# Path to sample audio for tests
AUDIO_PATH = Path(__file__).parents[2] / "data" / "samples" / "sample_mono.wav"


def _gpu_available() -> bool:
    """Return whether a usable GPU is available for CLI smoke tests.

    Returns:
        True if `torch` is importable and reports CUDA/ROCm availability.
    """
    try:
        import torch
    except ModuleNotFoundError:
        return False
    return bool(torch.cuda.is_available())


pytestmark = [
    pytest.mark.integration,
    pytest.mark.e2e,
    pytest.mark.gpu,
    pytest.mark.slow,
    pytest.mark.skipif(not AUDIO_PATH.is_file(), reason="sample_mono.wav not present for CLI test"),
    pytest.mark.skipif(
        os.getenv("CI") == "true",
        reason="GPU test skipped in CI environment",
    ),
    pytest.mark.skipif(
        not _gpu_available(),
        reason="GPU test skipped because no GPU is available",
    ),
]


def _invoke_cli(*args: str) -> Result:
    """Invoke the Typer CLI ``transcribe`` subcommand and return the result.

    Args:
        *args: Arguments to pass to the `transcribe` subcommand.

    Returns:
        The CliRunner invocation result containing the exit code, stdout,
        and stderr.
    """
    runner = CliRunner()
    # Always invoke the `transcribe` subcommand explicitly
    return runner.invoke(cli_app, ["transcribe", *args])


def test_cli_txt(tmp_path: Path) -> None:
    """Smoke-test that the CLI transcribes a sample audio to a TXT file.

    This test exercises the full model pipeline and requires GPU hardware;
    it will be skipped in CI environments. It invokes the CLI transcribe
    command on the bundled sample audio, asserts a successful exit code,
    and verifies that at least one produced TXT file is non-empty.

    Args:
        tmp_path: Pytest temporary directory fixture used to create the output
            directory.
    """
    outdir = tmp_path / "out"
    result = _invoke_cli(
        str(AUDIO_PATH),
        "--output-dir",
        str(outdir),
        "--output-format",
        "txt",
    )
    # Typer returns 0 on success
    assert result.exit_code == 0, result.stderr
    txt_files = list(outdir.glob("*.txt"))
    assert txt_files, "No TXT file produced"
    assert txt_files[0].read_text().strip(), "TXT file is empty"


def test_cli_srt_word_timestamps(tmp_path: Path) -> None:
    """Verify the CLI produces an SRT file with word-level timestamps.

    Invokes the transcribe command with ``--output-format srt`` and
    ``--word-timestamps``, asserts a zero exit code, ensures that at least
    one ``.srt`` file is created in the temporary output directory, and
    checks that the first SRT entry index equals ``"1"``.

    Args:
        tmp_path: Pytest temporary directory fixture used to create the output
            directory.
    """
    outdir = tmp_path / "out"
    result = _invoke_cli(
        str(AUDIO_PATH),
        "--output-dir",
        str(outdir),
        "--output-format",
        "srt",
        "--word-timestamps",
    )
    assert result.exit_code == 0, result.stderr
    srt_files = list(outdir.glob("*.srt"))
    assert srt_files, "No SRT file produced"
    first_lines = srt_files[0].read_text().splitlines()[:4]
    # Basic SRT structure check
    assert first_lines and first_lines[0].strip() == "1", "Invalid SRT format"
