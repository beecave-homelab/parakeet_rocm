"""Gradio WebUI sub-module for Parakeet-ROCm ASR.

This module provides a production-ready web interface for the
Parakeet-NEMO ASR transcription engine, built with Gradio.

The WebUI follows modern architectural patterns with clean separation
of concerns, protocol-oriented design for testability, and comprehensive
input validation.

Examples:
    Launch the WebUI from code:

    >>> from parakeet_rocm.webui import launch_app
    >>> launch_app()

    Or build and customize the app:

    >>> from parakeet_rocm.webui import build_app
    >>> app = build_app()
    >>> app.launch(server_name="localhost", server_port=7860)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

# Lazy imports to avoid loading Gradio unless needed
__all__ = ["build_app", "launch_app"]

if TYPE_CHECKING:
    import gradio as gr


def build_app() -> gr.Blocks:
    """Build the Gradio WebUI application.

    Returns:
        Configured Gradio Blocks application.
    """
    from parakeet_rocm.webui.app import build_app as _build_app

    return _build_app()


def launch_app(**kwargs: object) -> None:
    """Launch the Gradio WebUI application.

    Args:
        **kwargs: Keyword arguments passed to launch_app function.
    """
    from parakeet_rocm.webui.app import launch_app as _launch_app

    _launch_app(**kwargs)


def main() -> None:
    """CLI entry point for parakeet-webui command with proper --help support."""
    import typer

    from parakeet_rocm.utils.constant import GRADIO_SERVER_NAME, GRADIO_SERVER_PORT

    app = typer.Typer(add_completion=False)

    @app.command()
    def webui(
        host: str = typer.Option(
            GRADIO_SERVER_NAME,
            "--host",
            help="Server hostname or IP address to bind to.",
        ),
        port: int = typer.Option(
            GRADIO_SERVER_PORT,
            "--port",
            help="Server port number.",
        ),
        share: bool = typer.Option(
            False,
            "--share",
            help="Create a public Gradio share link.",
        ),
        debug: bool = typer.Option(
            False,
            "--debug",
            help="Enable debug mode with verbose logging.",
        ),
    ) -> None:
        """Launch the Gradio WebUI for interactive transcription."""
        launch_app(
            server_name=host,
            server_port=port,
            share=share,
            debug=debug,
        )

    app()
