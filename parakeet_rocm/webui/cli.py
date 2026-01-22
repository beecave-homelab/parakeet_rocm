"""Typer CLI for launching the Parakeet-ROCm WebUI."""

from __future__ import annotations

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
    from parakeet_rocm.webui import launch_app

    launch_app(
        server_name=host,
        server_port=port,
        share=share,
        debug=debug,
    )


def main() -> None:
    """Run the WebUI CLI."""
    app()
