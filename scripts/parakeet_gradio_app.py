"""Enhanced Gradio WebUI for Parakeet‑NEMO ASR.

This module provides a ready‑to‑run Web UI built with the
[`gradio`](https://gradio.app) framework. It exposes the
transcription capabilities of the `parakeet_rocm` package
through a polished interface with light/dark mode support,
collapsible configuration sections and quick presets for common
use cases.

The underlying logic is adapted from the original project
and uses the same `cli_transcribe` function under the hood. All
configuration options are surfaced via intuitive widgets. A user
can upload one or more audio/video files, adjust the model and
precision settings, choose output formats and more.

To run the app simply execute this file with Python:

```
python parakeet_gradio_app.py
```

It will start a local Gradio server and open the UI in your
default web browser.
"""

from __future__ import annotations

import pathlib

import gradio as gr

from parakeet_rocm.transcribe import cli_transcribe
from parakeet_rocm.utils import constant

DEFAULT_MODEL_NAME = constant.PARAKEET_MODEL_NAME


def enforce_precision(fp16: bool, fp32: bool) -> tuple[bool, bool]:
    """Enforce that only one of fp16/fp32 flags is true.

    If both are selected the function prefers fp16 by returning ``(True, False)``;
    otherwise it returns the original values.

    Args:
        fp16: Whether FP16 precision is requested.
        fp32: Whether FP32 precision is requested.

    Returns:
        A tuple of booleans ``(fp16, fp32)`` with at most one ``True``.

    """
    if fp16 and fp32:
        return True, False
    return fp16, fp32


def transcribe_webui(
    files: list[str],
    model_name: str,
    output_dir: str,
    output_format: str,
    output_template: str,
    batch_size: int,
    chunk_len_sec: int,
    stream: bool,
    stream_chunk_sec: int,
    overlap_duration: int,
    highlight_words: bool,
    word_timestamps: bool,
    merge_strategy: str,
    overwrite: bool,
    verbose: bool,
    no_progress: bool,
    quiet: bool,
    fp16: bool,
    fp32: bool,
) -> list[str]:
    """Invoke the CLI transcription pipeline using values collected from the Gradio UI.

    Parameters:
        files (list[str]): Input audio/video file paths to transcribe.
        model_name (str): Model name or path to use for transcription.
        output_dir (str): Directory where transcription outputs will be written.
        output_format (str): Desired output format (for example
            ``"txt"``, ``"srt"``).
        output_template (str): Filename template for outputs; supports
            placeholders such as ``"{model}"`` and ``"{timestamp}"``.
        batch_size (int): Number of samples processed per batch.
        chunk_len_sec (int): Duration in seconds for each audio chunk.
        stream (bool): Enable streaming transcription mode.
        stream_chunk_sec (int): Chunk size in seconds when streaming is enabled.
        overlap_duration (int): Overlap in seconds between adjacent chunks.
        highlight_words (bool): Include word highlighting in formatted outputs.
        word_timestamps (bool): Include word-level timestamps in outputs.
        merge_strategy (str): Strategy to merge transcribed chunks into final outputs.
        overwrite (bool): Overwrite existing output files if present.
        verbose (bool): Enable verbose CLI output.
        no_progress (bool): Disable progress bar output.
        quiet (bool): Suppress non-error output.
        fp16 (bool): Request FP16 precision (may be adjusted to avoid conflict).
        fp32 (bool): Request FP32 precision (may be adjusted to avoid conflict).

    Returns:
        list[str]: Paths of the generated transcription files as strings.
    """
    fp16, fp32 = enforce_precision(fp16, fp32)
    path_files = [pathlib.Path(f) for f in files]
    outputs = cli_transcribe(
        audio_files=path_files,
        model_name=model_name,
        output_dir=pathlib.Path(output_dir),
        output_format=output_format,
        output_template=output_template,
        batch_size=batch_size,
        chunk_len_sec=chunk_len_sec,
        stream=stream,
        stream_chunk_sec=stream_chunk_sec,
        overlap_duration=overlap_duration,
        highlight_words=highlight_words,
        word_timestamps=word_timestamps,
        merge_strategy=merge_strategy,
        overwrite=overwrite,
        verbose=verbose,
        quiet=quiet,
        no_progress=no_progress,
        fp16=fp16,
        fp32=fp32,
    )
    # Convert all Path objects to strings for Gradio compatibility
    return [str(path) for path in outputs]


# --- Custom styling for Gradio ---
CUSTOM_CSS = """
:root {
  --bg:#f5f7fa;
  --card:#ffffff;
  --fg:#1f2937;
  --muted:#6b7280;
  --radius:10px;
  --shadow:0 12px 30px -4px rgba(31,41,55,0.15);
  --border:1px solid rgba(0,0,0,0.05);
}
[data-theme="dark"] {
  --bg:#0f111a;
  --card:#1f1f2c;
  --fg:#e1e5ee;
  --muted:#9ca3af;
  --shadow:0 12px 30px -4px rgba(0,0,0,0.5);
  --border:1px solid rgba(255,255,255,0.08);
}
body {
  background: var(--bg) !important;
  color: var(--fg) !important;
  transition: background .25s ease, color .25s ease;
  font-family: system-ui,-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,sans-serif;
}
.gradio-container, .gradio-box {
  background: transparent !important;
}
.group-box {
  background: var(--card) !important;
  padding: 1rem 1rem 1.25rem;
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  border: var(--border);
  margin-bottom: 1rem;
}
h1 { font-size:1.75rem; margin-bottom:0.25rem; font-weight:700; }
h2 { font-size:1.25rem; margin:0.4rem 0 0.6rem; font-weight:600; }
h3 { font-size:1rem; margin:0.3rem 0 0.4rem; font-weight:600; }
.small-label {
  font-size: 0.65rem;
  color: var(--muted);
  margin-top: 3px;
}
.warning {
  color: #f59e0b;
  background: #fffbeb;
  border-left: 3px solid #f59e0b;
  padding: 10px;
  border-radius: 4px;
  margin: 10px 0;
}
.output-files {
  margin-top: 1em;
}
.output-files .wrap {
  max-height: 300px;
  overflow-y: auto;
  border: 1px solid var(--border-color-primary);
  border-radius: 4px;
  padding: 10px;
  margin-top: 10px;
  background: var(--card);
}
.download-btn {
  margin-left: 10px;
}
.gradio-button.primary {
  background: #ff6f00 !important;
  border: none !important;
  color: white !important;
}
.gradio-button.primary:hover {
  filter: brightness(1.05);
}
#theme-toggle-btn {
  border-radius: 6px;
  padding: 6px 12px;
  min-width: 100px;
}
* {
  user-select: auto !important;
}
::selection {
  background: rgba(255,111,0,0.2);
  color: inherit;
}
"""

# JavaScript to persist and toggle theme across sessions
CUSTOM_JS = """
(function(){
    const stored = localStorage.getItem("parakeet-theme") || "light";
    function setTheme(t) {
        document.documentElement.setAttribute("data-theme", t);
        localStorage.setItem("parakeet-theme", t);
        const btn = document.getElementById("theme-toggle-btn");
        if (btn) btn.textContent = t === "dark" ? "Light Mode" : "Dark Mode";
    }
    setTheme(stored);
    const btn = document.getElementById("theme-toggle-btn");
    if (btn) {
        btn.addEventListener("click", () => {
            const current = document.documentElement.getAttribute("data-theme");
            setTheme(current === "dark" ? "light" : "dark");
        });
    }
})();
"""


def build_ui() -> gr.Blocks:
    """Build the Gradio Blocks user interface for the WebUI.

    The UI includes upload and model inputs, collapsible output and
    transcription controls (including precision toggles, batching,
    chunking, streaming, and merge options), preset quick actions, a
    Transcribe action wired to the transcription handler, and
    client-side theme persistence.

    Returns:
        gr.Blocks: Assembled Gradio Blocks object representing the
            complete web UI.
    """
    with gr.Blocks(
        title="Parakeet‑NEMO ASR WebUI", css=CUSTOM_CSS, analytics_enabled=False
    ) as demo:
        # Header row
        with gr.Row():
            with gr.Column(scale=3):
                gr.Markdown("## Parakeet‑NEMO ASR WebUI")
                gr.Markdown(
                    "**Upload audio/video and configure transcription settings.**  \n"
                    "Fast presets, streaming, precision control, and\n"
                    "customizable outputs."
                )
            with gr.Column(scale=1, min_width=150):
                with gr.Row():
                    gr.Button(
                        "Toggle",
                        elem_id="theme-toggle-btn",
                        variant="secondary",
                        size="sm",
                    )
                gr.Markdown('<div class="small-label">Switch Light / Dark. Preference saved.</div>')

        # Always visible inputs
        with gr.Row():
            with gr.Column(scale=2):
                gr.Markdown("### Input & Model")
                with gr.Column(elem_classes=["group-box"]):
                    files = gr.File(
                        label="Upload Audio / Video",
                        file_count="multiple",
                        type="filepath",
                    )
                    gr.Markdown(
                        '<div class="small-label">Supports common audio/video containers.</div>'
                    )
                    model_name = gr.Textbox(
                        label="Model Name or Path",
                        value=constant.PARAKEET_MODEL_NAME,
                    )
                    gr.Markdown(
                        '<div class="small-label">Local path or pretrained model identifier.</div>'
                    )

        # Collapsible: output settings
        with gr.Row():
            with gr.Column(scale=2):
                with gr.Accordion("Output Settings", open=False):
                    with gr.Column(elem_classes=["group-box"]):
                        output_dir = gr.Textbox(
                            label="Output Directory",
                            value="./output",
                        )
                        gr.Markdown(
                            '<div class="small-label">'
                            "Where transcription files will be "
                            "written.</div>"
                        )
                        output_format = gr.Dropdown(
                            ["txt", "srt", "vtt", "json"],
                            label="Output Format",
                            value="txt",
                        )
                        output_template = gr.Textbox(
                            label="Output Filename Template",
                            value="{filename}",
                        )
                        gr.Markdown(
                            '<div class="small-label">'
                            "Use placeholders like {filename}, "
                            "{lang}.</div>"
                        )
                        gr.Markdown(
                            '<div class="small-label">'
                            "You can also use {model} and {timestamp}.</div>"
                        )
            with gr.Column(scale=3):
                with gr.Accordion("Transcription Controls", open=False):
                    with gr.Column(elem_classes=["group-box"]):
                        with gr.Row():
                            batch_size = gr.Slider(
                                1,
                                128,
                                step=1,
                                value=constant.DEFAULT_BATCH_SIZE,
                                label="Batch Size",
                            )
                            chunk_len_sec = gr.Slider(
                                1,
                                600,
                                step=1,
                                value=constant.DEFAULT_CHUNK_LEN_SEC,
                                label="Chunk Length (sec)",
                            )
                        with gr.Row():
                            stream = gr.Checkbox(label="Stream Mode")
                            stream_chunk_sec = gr.Slider(
                                0,
                                60,
                                step=1,
                                value=0,
                                label="Stream Chunk Length (sec)",
                            )
                            overlap_duration = gr.Slider(
                                0,
                                60,
                                step=1,
                                value=15,
                                label="Overlap Duration (sec)",
                            )
                        with gr.Row():
                            highlight_words = gr.Checkbox(label="Highlight Words")
                            word_timestamps = gr.Checkbox(label="Word Timestamps")
                            merge_strategy = gr.Dropdown(
                                ["none", "contiguous", "lcs"],
                                label="Merge Strategy",
                                value="lcs",
                            )
                with gr.Accordion("Execution Flags", open=False):
                    with gr.Column(elem_classes=["group-box"]):
                        with gr.Row():
                            overwrite = gr.Checkbox(label="Overwrite Outputs")
                            verbose = gr.Checkbox(label="Verbose Output")
                            no_progress = gr.Checkbox(label="Disable Progress Bar")
                            quiet = gr.Checkbox(label="Quiet Mode")
                        with gr.Row():
                            fp16 = gr.Checkbox(label="Use FP16 Precision")
                            fp32 = gr.Checkbox(label="Use FP32 Precision")
                        # Placeholder for precision warning
                        fp_warning_output = gr.HTML()

        # Presets
        with gr.Accordion("Presets / Quick Actions", open=False):
            with gr.Row():
                default_preset = gr.Button("Default Fast")
                high_quality = gr.Button("High Quality")
                stream_preset = gr.Button("Streaming Mode")

        # Main action and output
        with gr.Row():
            transcribe_btn = gr.Button("Transcribe", variant="primary", size="lg")
            _status = gr.Markdown("", visible=False)
        output_files = gr.Files(label="Transcription Outputs", interactive=False)

        # Inject custom JS for theme persistence
        gr.HTML(
            f"""
        <script>
        {CUSTOM_JS}
        </script>
        """
        )

        # Precision enforcement callback: displays a warning and adjusts toggles
        def enforce_and_warn(fp16_val: bool, fp32_val: bool) -> tuple[str, bool, bool]:
            """Validate FP16/FP32 selections and produce a warning message if both are selected.

            Parameters:
                fp16_val (bool): Current FP16 selection state.
                fp32_val (bool): Current FP32 selection state.

            Returns:
                tuple[str, bool, bool]: Tuple ``(html_warning, fp16, fp32)``
                    where ``html_warning`` is an HTML warning string if both
                    precisions were selected (otherwise an empty string), and
                    ``fp16``/``fp32`` are the enforced precision flags (FP16
                    is chosen when both were selected).
            """
            if fp16_val and fp32_val:
                return (
                    "<div class='warning'>FP16 and FP32 both selected; "
                    "FP16 will take precedence.</div>",
                    True,
                    False,
                )
            return ("", fp16_val, fp32_val)

        fp16.change(
            fn=enforce_and_warn,
            inputs=[fp16, fp32],
            outputs=[fp_warning_output, fp16, fp32],
        )
        fp32.change(
            fn=enforce_and_warn,
            inputs=[fp16, fp32],
            outputs=[fp_warning_output, fp16, fp32],
        )

        # Preset callbacks
        def apply_default() -> tuple[
            str,
            str,
            str,
            str,
            int,
            int,
            bool,
            int,
            int,
            bool,
            bool,
            str,
            bool,
            bool,
            bool,
            bool,
            bool,
            bool,
        ]:
            """Return the default preset values for transcription controls.

            Returns:
                A tuple of 18 elements representing the default
                configuration in this order:

                1. model_name: Default model identifier/path.
                2. output_dir: Default output directory path.
                3. output_format: Default export format.
                4. output_template: Default filename template.
                5. batch_size: Default batch size for processing.
                6. chunk_len_sec: Default chunk length in seconds.
                7. stream: Whether streaming mode is enabled by default.
                8. stream_chunk_sec: Default stream chunk length in
                    seconds.
                9. overlap_duration: Default overlap duration between
                    chunks (seconds).
                10. highlight_words: Whether to highlight words by
                    default.
                11. word_timestamps: Whether to include word-level
                    timestamps by default.
                12. merge_strategy: Default segment merge strategy.
                13. overwrite: Whether to overwrite existing outputs by
                    default.
                14. verbose: Whether verbose output is enabled by
                    default.
                15. no_progress: Whether the progress bar is disabled by
                    default.
                16. quiet: Whether quiet mode is enabled by default.
                17. fp16: Whether FP16 precision is enabled by default.
                18. fp32: Whether FP32 precision is enabled by default.
            """
            return (
                constant.PARAKEET_MODEL_NAME,
                "./output",
                "txt",
                "{filename}",
                constant.DEFAULT_BATCH_SIZE,
                constant.DEFAULT_CHUNK_LEN_SEC,
                False,
                0,
                15,
                False,
                False,
                "lcs",
                False,
                False,
                False,
                False,
                True,
                False,
            )

        def apply_high_quality() -> tuple[
            str,
            str,
            str,
            str,
            int,
            int,
            bool,
            int,
            int,
            bool,
            bool,
            str,
            bool,
            bool,
            bool,
            bool,
            bool,
            bool,
        ]:
            """Return a preset configuration for higher-quality runs.

            Returns:
                A tuple with preset values in this order:

                - model_name: Default model name/path to use.
                - output_dir: Default output directory path.
                - output_format: Output file format (for example
                  ``"txt"``).
                - output_template: Filename template for outputs (may
                  include placeholders like ``"{filename}"``).
                - batch_size: Number of files processed per batch.
                - chunk_len_sec: Chunk length in seconds for
                  non-streaming processing.
                - stream: Whether streaming mode is enabled.
                - stream_chunk_sec: Chunk length in seconds when
                  streaming is enabled.
                - overlap_duration: Overlap duration in seconds between
                  chunks.
                - highlight_words: Whether to enable word highlighting
                  in output.
                - word_timestamps: Whether to include per-word
                  timestamps.
                - merge_strategy: Strategy used to merge chunked
                  transcriptions (for example ``"lcs"``).
                - overwrite: Whether to overwrite existing output
                  files.
                - verbose: Whether to enable verbose output.
                - no_progress: Whether to disable the progress bar.
                - quiet: Whether to suppress non-critical output.
                - fp16: Whether to prefer FP16 precision.
                - fp32: Whether to prefer FP32 precision.
            """
            return (
                DEFAULT_MODEL_NAME,
                "./output",
                "txt",
                "{filename}",
                4,
                300,
                False,
                0,
                30,
                True,
                True,
                "lcs",
                True,
                True,
                False,
                False,
                False,
                False,
            )

        def apply_streaming() -> tuple[
            str,
            str,
            str,
            str,
            int,
            int,
            bool,
            int,
            int,
            bool,
            bool,
            str,
            bool,
            bool,
            bool,
            bool,
            bool,
            bool,
        ]:
            """Return preset UI values configured for streaming transcription.

            Returns:
                A tuple with values for the UI controls in this order:
                (model_name, output_dir, output_format, output_template, batch_size,
                 chunk_len_sec, stream, stream_chunk_sec, overlap_duration,
                 highlight_words, word_timestamps, merge_strategy, overwrite, verbose,
                 no_progress, quiet, fp16, fp32)

                - model_name: default model name/path to use.
                - output_dir: directory where outputs will be written.
                - output_format: output file format (e.g., "txt", "json").
                - output_template: filename template for outputs.
                - batch_size: number of files to process per batch.
                - chunk_len_sec: chunk length in seconds for non-streaming chunking.
                - stream: enable streaming transcription mode.
                - stream_chunk_sec: chunk length in seconds when streaming.
                - overlap_duration: overlap duration in seconds between chunks.
                - highlight_words: enable highlighted words in output.
                - word_timestamps: include word-level timestamps in output.
                - merge_strategy: strategy for merging chunked transcriptions.
                - overwrite: allow overwriting existing output files.
                - verbose: enable verbose logging/output.
                - no_progress: disable progress bar display.
                - quiet: enable quiet mode (minimal output).
                - fp16: prefer FP16 precision.
                - fp32: prefer FP32 precision.
            """
            return (
                DEFAULT_MODEL_NAME,
                "./output",
                "txt",
                "{filename}",
                8,
                60,
                True,
                5,
                10,
                False,
                False,
                "contiguous",
                False,
                False,
                False,
                False,
                True,
                False,
            )

        default_preset.click(
            fn=apply_default,
            inputs=[],
            outputs=[
                model_name,
                output_dir,
                output_format,
                output_template,
                batch_size,
                chunk_len_sec,
                stream,
                stream_chunk_sec,
                overlap_duration,
                highlight_words,
                word_timestamps,
                merge_strategy,
                overwrite,
                verbose,
                no_progress,
                quiet,
                fp16,
                fp32,
            ],
        )
        high_quality.click(
            fn=apply_high_quality,
            inputs=[],
            outputs=[
                model_name,
                output_dir,
                output_format,
                output_template,
                batch_size,
                chunk_len_sec,
                stream,
                stream_chunk_sec,
                overlap_duration,
                highlight_words,
                word_timestamps,
                merge_strategy,
                overwrite,
                verbose,
                no_progress,
                quiet,
                fp16,
                fp32,
            ],
        )
        stream_preset.click(
            fn=apply_streaming,
            inputs=[],
            outputs=[
                model_name,
                output_dir,
                output_format,
                output_template,
                batch_size,
                chunk_len_sec,
                stream,
                stream_chunk_sec,
                overlap_duration,
                highlight_words,
                word_timestamps,
                merge_strategy,
                overwrite,
                verbose,
                no_progress,
                quiet,
                fp16,
                fp32,
            ],
        )

        # Transcribe button callback
        transcribe_btn.click(
            fn=transcribe_webui,
            inputs=[
                files,
                model_name,
                output_dir,
                output_format,
                output_template,
                batch_size,
                chunk_len_sec,
                stream,
                stream_chunk_sec,
                overlap_duration,
                highlight_words,
                word_timestamps,
                merge_strategy,
                overwrite,
                verbose,
                no_progress,
                quiet,
                fp16,
                fp32,
            ],
            outputs=output_files,
        )

    return demo


if __name__ == "__main__":
    # Build and launch the Gradio demo
    demo_app = build_ui()
    # Launch with configured server settings
    demo_app.launch(
        server_name=constant.GRADIO_SERVER_NAME,
        server_port=constant.GRADIO_SERVER_PORT,
        share=False,  # Keep share=False by default for security
        show_error=True,
        favicon_path=None,
        auth=None,
        auth_message=None,
        prevent_thread_lock=False,
        show_api=True,
        debug=False,
        max_threads=40,
    )
