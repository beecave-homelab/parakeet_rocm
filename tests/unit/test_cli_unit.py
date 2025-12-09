"""Unit tests for the top-level CLI entry points.

These tests validate help output, version callback behavior, and the
transcribe command wiring without loading heavy dependencies.
"""

import importlib
from pathlib import Path

import pytest
import typer
from typer.testing import CliRunner

from parakeet_rocm import cli


def test_version_callback() -> None:
    """Ensure ``--version`` callback exits the process cleanly."""
    with pytest.raises(typer.Exit):
        cli.version_callback(True)


def test_main_help() -> None:
    """Invoking the app without args should print usage and exit 0."""
    runner = CliRunner()
    result = runner.invoke(cli.app, [])
    assert result.exit_code == 0
    assert "Usage" in result.stdout


def test_transcribe_basic(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """
    Verify that transcribe resolves input paths, delegates to the transcribe implementation, and returns the returned output paths.
    """
    audio = tmp_path / "a.wav"
    audio.write_text("x")
    monkeypatch.setattr(cli, "RESOLVE_INPUT_PATHS", lambda files: [audio])

    class DummyModule:
        @staticmethod
        def cli_transcribe(**kwargs):
            DummyModule.called = kwargs.get("audio_files")
            return [Path("out.txt")]

    def fake_import_module(name):
        return DummyModule

    monkeypatch.setattr(importlib, "import_module", fake_import_module)
    result = cli.transcribe(
        audio_files=[str(audio)], output_dir=tmp_path, output_format="txt"
    )
    assert DummyModule.called == [audio]
    assert result == [Path("out.txt")]


def test_transcribe_watch_mode(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """
    Invoke the watcher module when `--watch` is provided and verify the watch-based transcribe flow returns no immediate outputs.
    
    This test stubs importlib.import_module and `RESOLVE_INPUT_PATHS` to simulate watcher behavior and asserts that `cli.transcribe` returns an empty list.
    
    Parameters:
        monkeypatch (pytest.MonkeyPatch): Pytest fixture used to override imports and functions.
        tmp_path (Path): Temporary directory used as the output directory.
    """

    def fake_import_module(_name):
        """
        Provide a test double for importlib.import_module that returns lightweight fake modules used by transcribe/watch tests.
        
        Parameters:
            _name (str): Module name requested; used to decide which fake module to return.
        
        Returns:
            module (type): A fake module class:
                - If `_name` ends with `"utils.watch"`, returns a `Watch` class with a static
                  `watch_and_transcribe(**kwargs)` method that invokes the `transcribe_fn` callback
                  with `[Path("file.wav")]` and returns an empty list.
                - Otherwise returns a `Trans` class with a static `cli_transcribe(**_kwargs)` method
                  that sets `Trans.called = True` and returns an empty list.
        """
        if _name.endswith("utils.watch"):

            class Watch:
                @staticmethod
                def watch_and_transcribe(**kwargs):
                    kwargs["transcribe_fn"]([Path("file.wav")])
                    return []

            return Watch

        class Trans:
            @staticmethod
            def cli_transcribe(**_kwargs):
                Trans.called = True
                return []

        return Trans

    monkeypatch.setattr(importlib, "import_module", fake_import_module)
    monkeypatch.setattr(cli, "RESOLVE_INPUT_PATHS", lambda files: [])
    result = cli.transcribe(
        audio_files=None, watch=["*.wav"], output_dir=tmp_path, output_format="txt"
    )
    assert result == []


def test_transcribe_requires_input() -> None:
    """CLI should require at least one input source (files or --watch)."""
    with pytest.raises(cli.typer.BadParameter):
        cli.transcribe(audio_files=None, watch=None)