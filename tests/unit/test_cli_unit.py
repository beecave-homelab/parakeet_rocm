"""Unit tests for the top-level CLI entry points.

These tests validate help output, version callback behavior, and the
transcribe command wiring without loading heavy dependencies.
"""

from __future__ import annotations

import importlib
from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest
import typer
from typer.testing import CliRunner

from parakeet_rocm import cli


class _DummyModule:
    """Test double implementing minimal transcription interface."""

    called: list[Path] | None = None

    @staticmethod
    def cli_transcribe(**kwargs: object) -> list[Path]:
        """Record provided audio files and return dummy output paths.

        Args:
            kwargs: Keyword arguments supplied to the CLI entry point.

        Returns:
            list[Path]: Paths to the generated transcripts.
        """
        args = cast(dict[str, object], kwargs)
        _DummyModule.called = cast(list[Path] | None, args.get("audio_files"))
        return [Path("out.txt")]


class _WatchStub:
    """Stub watch module that proxies callbacks to ``transcribe_fn``."""

    @staticmethod
    def watch_and_transcribe(**kwargs: object) -> list[Path]:
        """Invoke the provided transcribe callback and return no outputs.

        Args:
            kwargs: Keyword arguments including the transcription callback.

        Returns:
            list[Path]: Empty list because no outputs are generated.
        """
        args = cast(dict[str, object], kwargs)
        transcribe_fn = cast(Callable[[list[Path]], object], args["transcribe_fn"])
        transcribe_fn([Path("file.wav")])
        return []


class _TransStub:
    """Stub transcription module for non-watch execution paths."""

    called: bool = False

    @staticmethod
    def cli_transcribe(**_kwargs: object) -> list[Path]:
        """Flag invocation and return an empty transcript list.

        Args:
            _kwargs: Unused transcription keyword arguments.

        Returns:
            list[Path]: Empty list because no outputs are generated.
        """
        _TransStub.called = True
        return []


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
    """Basic transcribe call should resolve inputs and return paths.

    Args:
        monkeypatch (pytest.MonkeyPatch): Pytest monkeypatch fixture.
        tmp_path (Path): Temporary directory for test files.
    """
    audio = tmp_path / "a.wav"
    audio.write_text("x")
    monkeypatch.setattr(cli, "RESOLVE_INPUT_PATHS", lambda files: [audio])

    _DummyModule.called = None

    def fake_import_module(name: str) -> type[_DummyModule]:
        """Return a dummy module for the requested import path.

        Args:
            name: Dotted import path requested by the CLI.

        Returns:
            type[_DummyModule]: Test module to satisfy the import.
        """
        return _DummyModule

    monkeypatch.setattr(importlib, "import_module", fake_import_module)
    result = cli.transcribe(
        audio_files=[str(audio)], output_dir=tmp_path, output_format="txt"
    )
    assert _DummyModule.called == [audio]
    assert result == [Path("out.txt")]


def test_transcribe_watch_mode(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """When --watch is used, the watcher module should be invoked.

    Args:
        monkeypatch (pytest.MonkeyPatch): Pytest monkeypatch fixture.
        tmp_path (Path): Temporary directory for test files.
    """
    _TransStub.called = False

    def fake_import_module(_name: str) -> type[_WatchStub] | type[_TransStub]:
        """Return watch or transcribe stubs depending on the import path.

        Args:
            _name: Dotted import path requested by the CLI.

        Returns:
            type[_WatchStub] | type[_TransStub]: Stub class matching the path.
        """
        if _name.endswith("utils.watch"):
            return _WatchStub
        return _TransStub

    monkeypatch.setattr(importlib, "import_module", fake_import_module)
    monkeypatch.setattr(cli, "RESOLVE_INPUT_PATHS", lambda files: [])
    result = cli.transcribe(
        audio_files=None, watch=["*.wav"], output_dir=tmp_path, output_format="txt"
    )
    assert result == []
    assert _TransStub.called


def test_transcribe_requires_input() -> None:
    """CLI should require at least one input source (files or --watch)."""
    with pytest.raises(cli.typer.BadParameter):
        cli.transcribe(audio_files=None, watch=None)
