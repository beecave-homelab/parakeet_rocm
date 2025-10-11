"""Tests for wildcard resolution and watch functionality."""

from __future__ import annotations

import pathlib

import pytest

from parakeet_rocm.utils.file_utils import (
    AUDIO_EXTENSIONS,
    resolve_input_paths,
)
from parakeet_rocm.utils.watch import (
    _default_sig_handler,
    _needs_transcription,
    watch_and_transcribe,
)


@pytest.fixture()
def temp_audio_dir(tmp_path: pathlib.Path) -> pathlib.Path:
    """Create a temporary directory with sample audio and noise files.

    Returns:
        pathlib.Path: Populated temporary directory path.

    """
    (tmp_path / "a.wav").write_bytes(b"0")
    (tmp_path / "b.mp3").write_bytes(b"0")
    (tmp_path / "ignore.txt").write_text("x")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "c.flac").write_bytes(b"0")
    return tmp_path


def test_resolve_input_paths_pattern(temp_audio_dir: pathlib.Path) -> None:
    """Ensure wildcard patterns resolve audio files in sorted order."""
    pattern = str(temp_audio_dir / "*.wav")
    results = resolve_input_paths([pattern])
    assert len(results) == 1 and results[0].name == "a.wav"


def test_resolve_input_paths_directory_recursive(temp_audio_dir: pathlib.Path) -> None:
    """Ensure directory expansion includes nested audio files only."""
    results = resolve_input_paths([temp_audio_dir])
    names = {p.name for p in results}
    assert names.issuperset({"a.wav", "b.mp3", "c.flac"})
    assert "ignore.txt" not in names


class ExitLoopError(Exception):
    """Break the watch loop during testing without side effects."""


def test_watch_and_transcribe(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> None:
    """Verify `watch_and_transcribe()` processes only unseen audio files."""
    audio_file = tmp_path / "new.wav"
    audio_file.write_bytes(b"0")

    called: list[pathlib.Path] = []

    def _mock_transcribe(paths: list[pathlib.Path]) -> None:
        called.extend(paths)
        # create dummy output file to simulate transcription result
        (tmp_path / "output").mkdir(exist_ok=True)

    # Monkeypatch time.sleep to raise after first iteration to exit loop
    def _sleep(_secs: float) -> None:
        raise ExitLoopError()

    monkeypatch.setattr("time.sleep", _sleep)
    monkeypatch.setattr("signal.signal", lambda *a, **k: None)

    with pytest.raises(ExitLoopError):
        watch_and_transcribe(
            patterns=[str(audio_file)],
            transcribe_fn=_mock_transcribe,
            poll_interval=0,
            output_dir=tmp_path,
            output_format="txt",
            output_template="{filename}",
            audio_exts=AUDIO_EXTENSIONS,
            verbose=False,
        )

    assert audio_file in called


def test_default_sig_handler_exits() -> None:
    """Ensure the default signal handler raises `SystemExit`."""
    with pytest.raises(SystemExit):
        _default_sig_handler(2, None)


def test_needs_transcription(tmp_path: pathlib.Path) -> None:
    """_needs_transcription detects existing output files."""
    audio = tmp_path / "a.wav"
    audio.write_text("x")
    out = tmp_path / "a.txt"
    assert _needs_transcription(audio, tmp_path, "{filename}", "txt")
    out.write_text("done")
    assert not _needs_transcription(audio, tmp_path, "{filename}", "txt")


def test_watch_and_transcribe_verbose(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> None:
    """Validate verbose mode behavior when existing outputs are present."""
    new_file = tmp_path / "fresh.wav"
    new_file.write_bytes(b"0")
    old_file = tmp_path / "old.wav"
    old_file.write_bytes(b"0")
    (tmp_path / "old.txt").write_text("done")

    captured: list[pathlib.Path] = []

    def _mock_transcribe(paths: list[pathlib.Path]) -> None:  # noqa: D401
        captured.extend(paths)

    def _sleep(_secs: float) -> None:  # noqa: D401
        raise ExitLoopError()

    monkeypatch.setattr("time.sleep", _sleep)
    monkeypatch.setattr("signal.signal", lambda *a, **k: None)

    with pytest.raises(ExitLoopError):
        watch_and_transcribe(
            patterns=[str(tmp_path / "*.wav")],
            transcribe_fn=_mock_transcribe,
            poll_interval=0,
            output_dir=tmp_path,
            output_format="txt",
            output_template="{filename}",
            audio_exts=AUDIO_EXTENSIONS,
            verbose=True,
        )

    assert new_file in captured and old_file not in captured
