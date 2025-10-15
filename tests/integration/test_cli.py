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

pytestmark = pytest.mark.skipif(
    not AUDIO_PATH.is_file(), reason="sample_mono.wav not present for CLI test"
)


def _invoke_cli(*args: str) -> Result:
    """Utility to invoke the Typer CLI and return result.

    Args:
        *args: CLI arguments to pass to transcribe command.

    Returns:
        Result object from the CLI invocation.
    """
    runner = CliRunner()
    # Always invoke the `transcribe` subcommand explicitly
    return runner.invoke(cli_app, ["transcribe", *args])


@pytest.mark.gpu
@pytest.mark.e2e
@pytest.mark.slow
def test_cli_txt(tmp_path: Path) -> None:
    """Smoke-test CLI transcribe to TXT output without word timestamps.

    Requires GPU hardware and loads full model pipeline.

    Args:
        tmp_path: Pytest fixture providing temporary directory.
    """
    if os.getenv("CI") == "true":
        pytest.skip("GPU test skipped in CI environment")

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


@pytest.mark.gpu
@pytest.mark.e2e
@pytest.mark.slow
def test_cli_srt_word_timestamps(tmp_path: Path) -> None:
    """CLI should produce SRT when word timestamps enabled.

    Requires GPU hardware and loads full model pipeline.

    Args:
        tmp_path: Pytest fixture providing temporary directory.
    """
    if os.getenv("CI") == "true":
        pytest.skip("GPU test skipped in CI environment")

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
