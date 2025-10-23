from __future__ import annotations

import logging
from types import SimpleNamespace

import pytest

from parakeet_rocm.utils import gpu_runtime


def test_detect_gpu_runtime_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    """Missing module returns metadata indicating no bindings."""

    def _raise(_name: str) -> None:
        raise ModuleNotFoundError("No module named 'cuda'")

    monkeypatch.setattr(gpu_runtime.importlib, "import_module", _raise)

    info = gpu_runtime.detect_gpu_runtime()

    assert info.backend == "missing"
    assert not info.is_available
    assert info.error is not None


def test_detect_gpu_runtime_hip(monkeypatch: pytest.MonkeyPatch) -> None:
    """HIP shim is detected when the cuda module exposes HIP markers."""

    stub = SimpleNamespace(__name__="cuda", hip=True)
    monkeypatch.setattr(gpu_runtime.importlib, "import_module", lambda _name: stub)

    info = gpu_runtime.detect_gpu_runtime()

    assert info.backend == "hip-python"
    assert info.hip_shim is True
    assert info.is_available


def test_log_gpu_runtime_native_cuda(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Logging helper surfaces info about native CUDA bindings."""

    stub = SimpleNamespace(__name__="cuda")
    monkeypatch.setattr(gpu_runtime.importlib, "import_module", lambda _name: stub)

    with caplog.at_level(logging.INFO):
        info = gpu_runtime.log_gpu_runtime()

    assert info.backend == "cuda-python"
    assert "native CUDA Python" in caplog.text


def test_log_gpu_runtime_warns_when_missing(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Logging helper emits a warning when bindings are absent."""

    def _raise(_name: str) -> None:
        raise ModuleNotFoundError("cuda not installed")

    monkeypatch.setattr(gpu_runtime.importlib, "import_module", _raise)

    with caplog.at_level(logging.WARNING):
        info = gpu_runtime.log_gpu_runtime()

    assert info.backend == "missing"
    assert "hip-python-as-cuda" in caplog.text
