"""Unit tests for unified FastAPI + Gradio application factory."""

from __future__ import annotations

import sys
import types

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


def _install_fake_webui_modules(monkeypatch: pytest.MonkeyPatch) -> dict[str, object]:
    """Install fake WebUI modules consumed by ``create_app``.

    Args:
        monkeypatch: Pytest monkeypatch fixture.

    Returns:
        Mutable state dict tracking startup/shutdown side effects.
    """
    state: dict[str, object] = {
        "idle_thread_started": False,
        "cleanup_called": False,
    }

    fake_webui_app = types.ModuleType("parakeet_rocm.webui.app")

    def build_app(*, job_manager: object | None = None, analytics_enabled: bool = False) -> object:
        del job_manager, analytics_enabled
        return object()

    def _start_idle_offload_thread(_job_manager: object) -> None:
        state["idle_thread_started"] = True

    def _cleanup_models() -> None:
        state["cleanup_called"] = True

    fake_webui_app.build_app = build_app
    fake_webui_app._start_idle_offload_thread = _start_idle_offload_thread
    fake_webui_app._cleanup_models = _cleanup_models
    monkeypatch.setitem(sys.modules, "parakeet_rocm.webui.app", fake_webui_app)

    fake_job_manager = types.ModuleType("parakeet_rocm.webui.core.job_manager")

    class JobManager:
        pass

    fake_job_manager.JobManager = JobManager
    monkeypatch.setitem(sys.modules, "parakeet_rocm.webui.core.job_manager", fake_job_manager)

    fake_gradio = types.ModuleType("gradio")

    def mount_gradio_app(app: FastAPI, _gradio_app: object, *, path: str) -> FastAPI:
        assert path == "/ui"
        return app

    fake_gradio.mount_gradio_app = mount_gradio_app
    monkeypatch.setitem(sys.modules, "gradio", fake_gradio)

    return state


def test_create_app_root_and_health(monkeypatch: pytest.MonkeyPatch) -> None:
    """create_app should expose health endpoint and root redirect."""
    from parakeet_rocm.api import app as api_app

    state = _install_fake_webui_modules(monkeypatch)
    monkeypatch.setattr(api_app, "API_ENABLED", True)
    monkeypatch.setattr(api_app, "API_CORS_ORIGINS", "")

    app = api_app.create_app()
    client = TestClient(app)

    health = client.get("/health")
    assert health.status_code == 200
    assert health.json() == {"status": "ok"}

    root = client.get("/", follow_redirects=False)
    assert root.status_code == 307
    assert root.headers["location"] == "/ui"

    with TestClient(app):
        pass

    assert state["idle_thread_started"] is True
    assert state["cleanup_called"] is True


def test_create_api_app_root_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    """create_api_app should expose API metadata at root without UI redirect."""
    from parakeet_rocm.api import app as api_app

    monkeypatch.setattr(api_app, "API_ENABLED", True)
    monkeypatch.setattr(api_app, "API_CORS_ORIGINS", "")

    app = api_app.create_api_app()
    client = TestClient(app)

    root = client.get("/")
    assert root.status_code == 200
    assert root.json() == {
        "service": "parakeet-rocm-api",
        "docs": "/docs",
        "health": "/health",
    }

    health = client.get("/health")
    assert health.status_code == 200
    assert health.json() == {"status": "ok"}
