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
    fake_webui_app.WEBUI_CONTAINER_CSS = ".gradio-container { max-width: 1200px; margin: auto; }"
    monkeypatch.setitem(sys.modules, "parakeet_rocm.webui.app", fake_webui_app)

    fake_job_manager = types.ModuleType("parakeet_rocm.webui.core.job_manager")

    class JobManager:
        pass

    fake_job_manager.JobManager = JobManager
    monkeypatch.setitem(sys.modules, "parakeet_rocm.webui.core.job_manager", fake_job_manager)

    fake_gradio = types.ModuleType("gradio")

    class _Themes:
        class Color:  # noqa: D106
            pass

        class Soft:  # noqa: D106
            def __init__(self, **_kwargs: object) -> None:
                return None

            def set(self, **_kwargs: object) -> _Themes.Soft:
                return self

    fake_gradio.themes = _Themes

    def mount_gradio_app(
        app: FastAPI,
        _gradio_app: object,
        *,
        path: str,
        theme: object | None = None,
        css: str | None = None,
    ) -> FastAPI:
        assert path == "/ui"
        assert theme is not None
        assert css is not None
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
    monkeypatch.setattr(api_app, "API_BEARER_TOKEN", "sk-test")
    monkeypatch.setattr(api_app, "API_MODEL_WARMUP_ON_START", False)
    monkeypatch.setattr(api_app, "_start_api_idle_offload_thread", lambda: None)

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


def test_create_api_app_warms_model_when_opted_in(monkeypatch: pytest.MonkeyPatch) -> None:
    """create_api_app should schedule model warmup on startup when enabled."""
    from parakeet_rocm.api import app as api_app

    state = {"warmup_thread_started": False}

    def _start_warmup_thread() -> None:
        state["warmup_thread_started"] = True

    monkeypatch.setattr(api_app, "API_ENABLED", True)
    monkeypatch.setattr(api_app, "API_CORS_ORIGINS", "")
    monkeypatch.setattr(api_app, "API_BEARER_TOKEN", "sk-test")
    monkeypatch.setattr(api_app, "API_MODEL_WARMUP_ON_START", True)
    monkeypatch.setattr(api_app, "_start_api_warmup_thread", _start_warmup_thread)
    monkeypatch.setattr(api_app, "_start_api_idle_offload_thread", lambda: None)

    app = api_app.create_api_app()

    with TestClient(app):
        pass

    assert state["warmup_thread_started"] is True


def test_create_api_app_logs_warning_when_auth_token_unset(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """create_api_app should warn operators when API auth is disabled."""
    from parakeet_rocm.api import app as api_app

    monkeypatch.setattr(api_app, "API_ENABLED", True)
    monkeypatch.setattr(api_app, "API_CORS_ORIGINS", "")
    monkeypatch.setattr(api_app, "API_BEARER_TOKEN", None)
    monkeypatch.setattr(api_app, "API_MODEL_WARMUP_ON_START", False)
    monkeypatch.setattr(api_app, "_start_api_idle_offload_thread", lambda: None)
    caplog.set_level("WARNING", logger=api_app.logger.name)

    api_app.create_api_app()

    assert "API_BEARER_TOKEN is not set" in caplog.text


def test_create_api_app_root_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    """create_api_app should expose API metadata at root without UI redirect."""
    from parakeet_rocm.api import app as api_app

    monkeypatch.setattr(api_app, "API_ENABLED", True)
    monkeypatch.setattr(api_app, "API_CORS_ORIGINS", "")
    monkeypatch.setattr(api_app, "API_BEARER_TOKEN", "sk-test")

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
