"""Unit tests for WebUI lazy-import `__getattr__` modules."""

from __future__ import annotations

import sys
import types
from collections.abc import Callable

import pytest


def test_webui_init_wrappers(monkeypatch: pytest.MonkeyPatch) -> None:
    """parakeet_rocm.webui should forward to parakeet_rocm.webui.app."""
    fake_app = types.ModuleType("parakeet_rocm.webui.app")

    def build_app() -> object:
        return object()

    called: dict[str, object] = {}

    def launch_app(**kwargs: object) -> None:
        called.update(kwargs)

    fake_app.build_app = build_app
    fake_app.launch_app = launch_app

    monkeypatch.setitem(sys.modules, "parakeet_rocm.webui.app", fake_app)

    import parakeet_rocm.webui as webui

    assert webui.build_app() is not None
    webui.launch_app(server_port=1234)
    assert called["server_port"] == 1234


def test_webui_main_executes(monkeypatch: pytest.MonkeyPatch) -> None:
    """webui.main() should wire typer and call launch_app with defaults."""
    called: dict[str, object] = {}

    fake_app = types.ModuleType("parakeet_rocm.webui.app")

    def launch_app(**kwargs: object) -> None:
        called.update(kwargs)

    fake_app.launch_app = launch_app
    fake_app.build_app = lambda: object()
    monkeypatch.setitem(sys.modules, "parakeet_rocm.webui.app", fake_app)

    typer_mod = types.ModuleType("typer")

    def option(default: object, *_args: object, **_kwargs: object) -> object:
        return default

    class _Typer:
        def __init__(self, *args: object, **kwargs: object) -> None:
            self._cmd = None

        def command(self) -> Callable[[Callable[..., object]], Callable[..., object]]:
            def deco(fn: Callable[..., object]) -> Callable[..., object]:
                self._cmd = fn
                return fn

            return deco

        def __call__(self) -> None:
            assert self._cmd is not None
            self._cmd()

    typer_mod.Typer = _Typer
    typer_mod.Option = option
    monkeypatch.setitem(sys.modules, "typer", typer_mod)

    sys.modules.pop("parakeet_rocm.webui.cli", None)
    sys.modules.pop("parakeet_rocm.webui", None)
    import parakeet_rocm.webui.cli as webui

    webui.main()
    assert "server_name" in called
    assert "server_port" in called


def test_core_init_lazy_exports(monkeypatch: pytest.MonkeyPatch) -> None:
    """webui.core should lazy-import expected symbols."""
    jm = types.ModuleType("parakeet_rocm.webui.core.job_manager")
    sm = types.ModuleType("parakeet_rocm.webui.core.session")

    class JobManager:
        pass

    class JobStatus:
        pass

    class TranscriptionJob:
        pass

    class SessionManager:
        pass
        pass

    jm.JobManager = JobManager
    jm.JobStatus = JobStatus
    jm.TranscriptionJob = TranscriptionJob
    sm.SessionManager = SessionManager

    monkeypatch.setitem(sys.modules, "parakeet_rocm.webui.core.job_manager", jm)
    monkeypatch.setitem(sys.modules, "parakeet_rocm.webui.core.session", sm)

    import parakeet_rocm.webui.core as core

    assert core.JobManager is JobManager
    assert core.JobStatus is JobStatus
    assert core.TranscriptionJob is TranscriptionJob
    assert core.SessionManager is SessionManager

    with pytest.raises(AttributeError):
        getattr(core, "Missing")


def test_ui_init_lazy_exports(monkeypatch: pytest.MonkeyPatch) -> None:
    """webui.ui should lazy-import configure_theme."""
    theme_mod = types.ModuleType("parakeet_rocm.webui.ui.theme")

    def configure_theme() -> object:
        return object()

    theme_mod.configure_theme = configure_theme
    monkeypatch.setitem(sys.modules, "parakeet_rocm.webui.ui.theme", theme_mod)

    import parakeet_rocm.webui.ui as ui

    assert ui.configure_theme is configure_theme

    with pytest.raises(AttributeError):
        getattr(ui, "Missing")


def test_ui_components_init_lazy_exports(monkeypatch: pytest.MonkeyPatch) -> None:
    """webui.ui.components should lazy-import component classes."""
    module_names = {
        "file_uploader": "FileUploader",
        "config_panel": "ConfigPanel",
        "progress_tracker": "ProgressTracker",
        "result_viewer": "ResultViewer",
    }

    for mod_suffix, attr in module_names.items():
        mod = types.ModuleType(f"parakeet_rocm.webui.ui.components.{mod_suffix}")
        mod.__dict__[attr] = type(attr, (), {})
        monkeypatch.setitem(sys.modules, mod.__name__, mod)

    import parakeet_rocm.webui.ui.components as components

    assert components.FileUploader.__name__ == "FileUploader"
    assert components.ConfigPanel.__name__ == "ConfigPanel"
    assert components.ProgressTracker.__name__ == "ProgressTracker"
    assert components.ResultViewer.__name__ == "ResultViewer"


def test_ui_pages_init_lazy_exports(monkeypatch: pytest.MonkeyPatch) -> None:
    """webui.ui.pages should lazy-import MainPage."""
    mod = types.ModuleType("parakeet_rocm.webui.ui.pages.main")
    mod.MainPage = type("MainPage", (), {})
    monkeypatch.setitem(sys.modules, mod.__name__, mod)

    import parakeet_rocm.webui.ui.pages as pages

    assert pages.MainPage.__name__ == "MainPage"


def test_utils_init_lazy_exports(monkeypatch: pytest.MonkeyPatch) -> None:
    """webui.utils should lazy-import PRESETS and get_preset."""
    presets_mod = types.ModuleType("parakeet_rocm.webui.utils.presets")
    x_obj = object()
    presets_mod.PRESETS = {"x": x_obj}

    def get_preset(name: str) -> object:
        return presets_mod.PRESETS[name]

    presets_mod.get_preset = get_preset
    monkeypatch.setitem(sys.modules, presets_mod.__name__, presets_mod)

    import parakeet_rocm.webui.utils as utils

    assert utils.PRESETS["x"] is x_obj
    assert utils.get_preset("x") is x_obj


def test_validation_init_lazy_exports(monkeypatch: pytest.MonkeyPatch) -> None:
    """webui.validation should lazy-import schema and validator functions."""
    schemas_mod = types.ModuleType("parakeet_rocm.webui.validation.schemas")
    schemas_mod.TranscriptionConfig = type("TranscriptionConfig", (), {})
    schemas_mod.FileUploadConfig = type("FileUploadConfig", (), {})

    validator_mod = types.ModuleType("parakeet_rocm.webui.validation.file_validator")

    def validate_audio_file(path: object) -> object:  # noqa: ARG001
        return object()

    def validate_output_directory(path: object) -> object:  # noqa: ARG001
        return object()

    validator_mod.validate_audio_file = validate_audio_file
    validator_mod.validate_output_directory = validate_output_directory

    monkeypatch.setitem(sys.modules, schemas_mod.__name__, schemas_mod)
    monkeypatch.setitem(sys.modules, validator_mod.__name__, validator_mod)

    import parakeet_rocm.webui.validation as validation

    assert validation.TranscriptionConfig.__name__ == "TranscriptionConfig"
    assert validation.FileUploadConfig.__name__ == "FileUploadConfig"
    assert validation.validate_audio_file(object())
    assert validation.validate_output_directory(object())

    with pytest.raises(AttributeError):
        getattr(validation, "Missing")
