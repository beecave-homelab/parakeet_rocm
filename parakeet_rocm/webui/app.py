"""Gradio WebUI application factory.

Builds and launches the complete web application using a layered
architecture with dependency injection for testability.
"""

from __future__ import annotations

import pathlib

import gradio as gr

from parakeet_rocm.utils.constant import (
    DEFAULT_BATCH_SIZE,
    DEFAULT_CHUNK_LEN_SEC,
    DEFAULT_DEMUCS,
    DEFAULT_STABILIZE,
    DEFAULT_VAD,
    DEFAULT_WORD_TIMESTAMPS,
    GRADIO_ANALYTICS_ENABLED,
    GRADIO_SERVER_NAME,
    GRADIO_SERVER_PORT,
    SUPPORTED_EXTENSIONS,
)
from parakeet_rocm.utils.logging_config import configure_logging, get_logger
from parakeet_rocm.webui.core.job_manager import JobManager, JobStatus
from parakeet_rocm.webui.core.session import SessionManager
from parakeet_rocm.webui.ui.theme import configure_theme
from parakeet_rocm.webui.utils.presets import PRESETS, get_preset
from parakeet_rocm.webui.utils.zip_creator import ZipCreator
from parakeet_rocm.webui.validation.file_validator import (
    FileValidationError,
    validate_audio_files,
)

# Module logger
logger = get_logger(__name__)


def build_app(
    *,
    job_manager: JobManager | None = None,
    analytics_enabled: bool = GRADIO_ANALYTICS_ENABLED,
) -> gr.Blocks:
    """Build the Gradio WebUI application.

    Creates a complete web interface for the Parakeet-NEMO ASR system
    with file upload, configuration, and transcription capabilities.

    Args:
        job_manager: Job manager instance (creates default if None).
        analytics_enabled: Enable Gradio analytics tracking.

    Returns:
        Configured Gradio Blocks application ready to launch.

    Examples:
        >>> app = build_app()
        >>> app.launch()

        >>> # With custom job manager
        >>> manager = JobManager()
        >>> app = build_app(job_manager=manager)
    """
    # Initialize dependencies
    if job_manager is None:
        job_manager = JobManager()

    session_manager = SessionManager()
    theme = configure_theme()

    # Build application
    with gr.Blocks(
        title="Parakeet-NEMO ASR WebUI",
        theme=theme,
        analytics_enabled=analytics_enabled,
        css=".gradio-container { max-width: 1200px; margin: auto; }",
    ) as app:
        # Session state (for future use)
        _session_state = gr.State(session_manager.create_session())  # noqa: F841

        # Header
        gr.Markdown("# 🎤 Parakeet-NEMO ASR WebUI")
        gr.Markdown(
            "Upload audio or video files and transcribe them using "
            "NVIDIA's Parakeet-NEMO model."
        )

        # File upload section
        with gr.Group():
            gr.Markdown("### 📁 Upload Files")
            file_upload = gr.File(
                label="Audio/Video Files",
                file_count="multiple",
                file_types=list(SUPPORTED_EXTENSIONS),
            )

        # Configuration section
        with gr.Group():
            gr.Markdown("### ⚙️ Configuration")

            with gr.Row():
                preset_dropdown = gr.Dropdown(
                    choices=list(PRESETS.keys()),
                    value="default",
                    label="Quick Presets",
                    info="Select a preset or customize settings below",
                )

            with gr.Accordion("Advanced Settings", open=False):
                with gr.Row():
                    batch_size = gr.Slider(
                        minimum=1,
                        maximum=32,
                        value=DEFAULT_BATCH_SIZE,
                        step=1,
                        label="Batch Size",
                    )
                    chunk_len_sec = gr.Slider(
                        minimum=30,
                        maximum=600,
                        value=DEFAULT_CHUNK_LEN_SEC,
                        step=30,
                        label="Chunk Length (seconds)",
                    )

                with gr.Row():
                    word_timestamps = gr.Checkbox(
                        label="Word-level Timestamps",
                        value=DEFAULT_WORD_TIMESTAMPS,
                    )
                    stabilize = gr.Checkbox(
                        label="Stabilize Timestamps (stable-ts)",
                        value=DEFAULT_STABILIZE,
                    )
                    vad = gr.Checkbox(
                        label="Voice Activity Detection",
                        value=DEFAULT_VAD,
                    )
                    demucs = gr.Checkbox(
                        label="Audio Enhancement (Demucs)",
                        value=DEFAULT_DEMUCS,
                    )

                output_format = gr.Dropdown(
                    choices=["txt", "srt", "vtt", "json"],
                    value="srt",
                    label="Output Format",
                )

        # Action buttons
        with gr.Row():
            transcribe_btn = gr.Button(
                "🚀 Start Transcription",
                variant="primary",
                size="lg",
            )
            clear_btn = gr.Button("Clear", variant="secondary")

        # Output section
        with gr.Group():
            gr.Markdown("### 📊 Results")
            status_output = gr.Textbox(
                label="Status",
                interactive=False,
                show_label=True,
            )
            with gr.Row():
                output_files = gr.File(
                    label="Output Files",
                    file_count="multiple",
                    interactive=False,
                    visible=True,
                )
                download_button = gr.DownloadButton(
                    label="📦 Download ZIP",
                    visible=False,
                    variant="primary",
                    size="lg",
                )

        # Event handlers
        def apply_preset(preset_name: str) -> dict:  # type: ignore[type-arg]
            """Apply preset configuration.

            Returns:
                Dictionary of updated component values.
            """
            try:
                preset = get_preset(preset_name)
                config = preset.config
                return {
                    batch_size: config.batch_size,
                    chunk_len_sec: config.chunk_len_sec,
                    word_timestamps: config.word_timestamps,
                    stabilize: config.stabilize,
                    vad: config.vad,
                    demucs: config.demucs,
                    output_format: config.output_format,
                }
            except KeyError:
                return {}

        def transcribe_files(  # type: ignore[no-untyped-def]
            files,
            batch_size_val,
            chunk_len_val,
            word_ts,
            stab,
            vad_val,
            demucs_val,
            out_format,
            progress=gr.Progress(),
        ):
            """Handle transcription request with progress tracking.

            Args:
                files: Uploaded audio/video files.
                batch_size_val: Batch size for inference.
                chunk_len_val: Chunk length in seconds.
                word_ts: Enable word timestamps.
                stab: Enable stabilization.
                vad_val: Enable VAD.
                demucs_val: Enable Demucs.
                out_format: Output format (txt/srt/json).
                progress: Gradio progress tracker.

            Returns:
                Tuple of (status_message, output_files).
            """
            if not files:
                logger.warning("Transcription requested with no files uploaded")
                return "❌ Please upload files first.", None

            try:
                # Step 1: Validate files
                progress(0.0, desc="🔍 Validating uploaded files...")
                logger.info(f"Starting transcription for {len(files)} file(s)")
                file_paths = [pathlib.Path(f.name) for f in files]
                logger.debug(f"File paths: {[str(p) for p in file_paths]}")
                validate_audio_files(file_paths)
                logger.info("File validation successful")

                # Step 2: Create configuration
                progress(0.1, desc="⚙️ Configuring transcription...")
                from parakeet_rocm.webui.validation.schemas import TranscriptionConfig

                config = TranscriptionConfig(
                    batch_size=batch_size_val,
                    chunk_len_sec=chunk_len_val,
                    word_timestamps=word_ts,
                    stabilize=stab,
                    vad=vad_val,
                    demucs=demucs_val,
                    output_format=out_format,
                )
                logger.info(
                    f"Config: batch={batch_size_val}, chunk={chunk_len_val}s, "
                    f"format={out_format}, stabilize={stab}"
                )

                # Step 3: Submit job
                progress(0.2, desc="📝 Submitting transcription job...")
                job = job_manager.submit_job(file_paths, config)
                logger.info(f"Job submitted with ID: {job.job_id}")

                # Step 4: Run transcription with real-time progress tracking
                logger.info(
                    f"Starting transcription for {len(files)} file(s): "
                    f"{[p.name for p in file_paths]}"
                )

                # Create callback to update Gradio progress from batch progress
                def update_gradio_progress(current: int, total: int) -> None:
                    """Update Gradio progress bar from transcription batches."""
                    # Map batch progress (0-total) to Gradio progress (0.3-0.95)
                    batch_fraction = current / total if total > 0 else 0
                    gradio_progress = 0.3 + (batch_fraction * 0.65)
                    progress(
                        gradio_progress,
                        desc=f"🎙️ Transcribing batch {current}/{total}...",
                    )
                    logger.debug(
                        f"Progress: {current}/{total} batches ({gradio_progress:.1%})"
                    )

                # Run transcription with progress callback
                result = job_manager.run_job(
                    job.job_id, progress_callback=update_gradio_progress
                )

                # Step 5: Finalize
                progress(0.95, desc="✨ Finalizing results...")

                if result.status == JobStatus.COMPLETED:
                    logger.info(
                        f"Transcription completed! Generated {len(result.outputs)} "
                        f"output file(s)"
                    )

                    # Handle bulk download for multiple files
                    if len(result.outputs) > 1:
                        logger.info("Multiple files detected, creating ZIP archive")
                        zip_creator = ZipCreator()
                        zip_path = zip_creator.create_temporary_zip(
                            result.outputs,
                            prefix="transcriptions_",
                        )
                        logger.info(f"Created ZIP archive: {zip_path}")
                        status_msg = (
                            f"✅ Transcription completed! "
                            f"Processed {len(files)} file(s). "
                            f"Generated {len(result.outputs)} output(s). "
                            f"Click the download button below."
                        )
                        logger.debug(f"ZIP archive created: {zip_path}")
                        progress(1.0, desc="✅ Done!")
                        # Return: status, file_list (hidden),
                        # download_button (visible + file)
                        return (
                            status_msg,
                            gr.update(visible=False),
                            gr.update(visible=True, value=str(zip_path)),
                        )
                    else:
                        # Single file - return as-is
                        status_msg = (
                            f"✅ Transcription completed! "
                            f"Processed {len(files)} file(s). "
                            f"Generated {len(result.outputs)} output(s)."
                        )
                        output_paths = [str(p) for p in result.outputs]
                        logger.debug(f"Output paths: {output_paths}")
                        progress(1.0, desc="✅ Done!")
                        # Return: status, file_list (visible), download_button (hidden)
                        return (
                            status_msg,
                            gr.update(visible=True, value=output_paths),
                            gr.update(visible=False),
                        )
                else:
                    error_msg = f"❌ Transcription failed: {result.error}"
                    logger.error(f"Transcription failed: {result.error}")
                    # Return: error status, hide both file list and button
                    return (
                        error_msg,
                        gr.update(visible=False, value=None),
                        gr.update(visible=False),
                    )

            except FileValidationError as e:
                logger.warning(f"File validation error: {e}")
                return (
                    f"❌ Validation error: {e}",
                    gr.update(visible=False, value=None),
                    gr.update(visible=False),
                )
            except Exception as e:
                logger.exception(f"Unexpected error during transcription: {e}")
                return (
                    f"❌ Error: {e}",
                    gr.update(visible=False, value=None),
                    gr.update(visible=False),
                )

        def clear_all() -> dict:  # type: ignore[type-arg]
            """Clear all inputs and outputs.

            Returns:
                Dictionary of cleared component values.
            """
            return {
                file_upload: None,
                status_output: "",
                output_files: None,
                download_button: gr.update(visible=False, value=None),
            }

        # Connect event handlers
        preset_dropdown.change(
            fn=apply_preset,
            inputs=[preset_dropdown],
            outputs=[
                batch_size,
                chunk_len_sec,
                word_timestamps,
                stabilize,
                vad,
                demucs,
                output_format,
            ],
        )

        transcribe_btn.click(
            fn=transcribe_files,
            inputs=[
                file_upload,
                batch_size,
                chunk_len_sec,
                word_timestamps,
                stabilize,
                vad,
                demucs,
                output_format,
            ],
            outputs=[status_output, output_files, download_button],
        )

        clear_btn.click(
            fn=clear_all,
            inputs=[],
            outputs=[file_upload, status_output, output_files, download_button],
        )

    return app


def launch_app(
    *,
    server_name: str = GRADIO_SERVER_NAME,
    server_port: int = GRADIO_SERVER_PORT,
    share: bool = False,
    debug: bool = False,
    **kwargs,  # type: ignore[no-untyped-def]
) -> None:
    """Launch the Gradio WebUI application.

    Builds and starts the web server with specified configuration.

    Args:
        server_name: Server hostname or IP address.
        server_port: Server port number.
        share: Create public Gradio share link.
        debug: Enable debug mode with verbose logging.
        **kwargs: Additional arguments passed to Gradio launch.

    Examples:
        >>> # Launch on localhost
        >>> launch_app()

        >>> # Launch with public sharing
        >>> launch_app(share=True)

        >>> # Custom port and debug mode
        >>> launch_app(server_port=8080, debug=True)
    """
    # Configure centralized logging
    configure_logging(level="DEBUG" if debug else "INFO")

    logger.info("Building Gradio WebUI application")
    app = build_app()

    print(f"🚀 Launching Parakeet-NEMO WebUI on http://{server_name}:{server_port}")
    if debug:
        print("📊 Debug mode enabled - check console for detailed logs")

    logger.info(f"Starting server on {server_name}:{server_port}")
    app.launch(
        server_name=server_name,
        server_port=server_port,
        share=share,
        debug=debug,
        show_error=True,
        quiet=not debug,
        **kwargs,
    )
