"""FastAPI application factory for combined REST API and Gradio UI serving."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, Response

from parakeet_rocm.api.routes import router as api_router
from parakeet_rocm.utils.constant import API_CORS_ORIGINS, API_ENABLED


def create_app(*, include_ui: bool = True) -> FastAPI:
    """Create a FastAPI application with optional mounted Gradio UI.

    Returns:
        Configured FastAPI application instance.
    """
    app = FastAPI(
        title="Parakeet-ROCm API",
        docs_url="/docs",
        openapi_url="/openapi.json",
        redoc_url="/redoc",
    )

    if API_ENABLED:
        app.include_router(api_router)

    origins = [origin.strip() for origin in API_CORS_ORIGINS.split(",") if origin.strip()]
    if origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    @app.get("/health")
    async def health() -> dict[str, str]:
        """Return a minimal health status payload."""
        return {"status": "ok"}

    if not include_ui:

        @app.get("/")
        async def root() -> dict[str, str]:
            """Return API-mode service metadata for root requests.

            Returns:
                API-mode metadata containing docs and health endpoint paths.
            """
            return {
                "service": "parakeet-rocm-api",
                "docs": "/docs",
                "health": "/health",
            }

        return app

    from parakeet_rocm.webui.app import _cleanup_models, _start_idle_offload_thread, build_app
    from parakeet_rocm.webui.core.job_manager import JobManager

    # Single-process architecture: both API and Gradio share the same model cache.
    job_manager = JobManager()
    gradio_app = build_app(job_manager=job_manager)

    @app.on_event("startup")
    async def _on_startup() -> None:
        """Start background model idle offload worker."""
        _start_idle_offload_thread(job_manager)

    @app.on_event("shutdown")
    async def _on_shutdown() -> None:
        """Run best-effort model cleanup during server shutdown."""
        _cleanup_models()

    @app.get("/")
    async def root() -> Response:
        """Redirect root traffic to the mounted Gradio UI.

        Returns:
            Redirect response to ``/ui``.
        """
        return RedirectResponse(url="/ui", status_code=307)

    import gradio as gr

    return gr.mount_gradio_app(app, gradio_app, path="/ui")


def create_api_app() -> FastAPI:
    """Create API-only FastAPI app without mounted Gradio UI.

    Returns:
        Configured FastAPI application instance exposing REST endpoints only.
    """
    return create_app(include_ui=False)
