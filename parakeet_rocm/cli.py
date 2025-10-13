"""Command-line interface for the Parakeet-NeMo ASR application using Typer.

Replaces the older `argparse`-based CLI with a more robust and user-friendly
interface that supports subcommands, rich help messages, and improved argument
handling.

Features:
- `transcribe` command for running ASR on audio files.
- Options for model selection, output formatting, and batch processing.
- Verbose mode for detailed logging.
"""

import pathlib
from typing import Annotated

import typer

from parakeet_rocm import __version__
from parakeet_rocm.utils.constant import (
    DEFAULT_BATCH_SIZE,
    DEFAULT_CHUNK_LEN_SEC,
    PARAKEET_MODEL_NAME,
)

# Placeholder for lazy import; enables monkeypatching in tests.
RESOLVE_INPUT_PATHS = None  # type: ignore[assignment]


# Create the main Typer application instance
def version_callback(value: bool) -> None:
    """Show the application's version and exit.

    Args:
        value: When True, print the version and exit.

    Raises:
        typer.Exit: Always raised after printing when value is True.

    """
    if value:
        print(f"parakeet-rocm version: {__version__}")
        raise typer.Exit()


app = typer.Typer(
    name="parakeet-rocm",
    help=(
        "A CLI for transcribing audio files using NVIDIA Parakeet-TDT via NeMo on ROCm."
    ),
    add_completion=False,
)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            help="Show the application's version and exit.",
            callback=version_callback,
            is_eager=True,  # still OK
        ),
    ] = False,
) -> None:
    """Root command acts like `transcribe` without a subcommand.

    Args:
        ctx: Typer context.
        version: Whether to print version and exit.

    Raises:
        typer.Exit: Raised to terminate after displaying help or version.

    """
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit()


def _setup_watch_mode(
    watch: list[str],
    model_name: str,
    output_dir: pathlib.Path,
    output_format: str,
    output_template: str,
    batch_size: int,
    chunk_len_sec: int,
    stream: bool,
    stream_chunk_sec: int,
    overlap_duration: int,
    highlight_words: bool,
    word_timestamps: bool,
    stabilize: bool,
    demucs: bool,
    vad: bool,
    vad_threshold: float,
    merge_strategy: str,
    overwrite: bool,
    verbose: bool,
    quiet: bool,
    no_progress: bool,
    fp32: bool,
    fp16: bool,
) -> None:
    """Set up and start watch mode for automatic transcription of new files.

    Args:
        watch: Directory or glob patterns to monitor.
        model_name: Hugging Face model ID or local path.
        output_dir: Directory to save transcription outputs.
        output_format: Output format (txt, srt, vtt, json, etc.).
        output_template: Template for output filenames.
        batch_size: Batch size for transcription inference.
        chunk_len_sec: Chunk length in seconds.
        stream: Enable pseudo-streaming mode.
        stream_chunk_sec: Chunk length for streaming mode.
        overlap_duration: Overlap duration between chunks.
        highlight_words: Enable word highlighting in SRT/VTT.
        word_timestamps: Enable word-level timestamps.
        stabilize: Enable stable-ts refinement.
        demucs: Enable Demucs source separation.
        vad: Enable voice activity detection.
        vad_threshold: VAD threshold value.
        merge_strategy: Strategy for merging overlapping chunks.
        overwrite: Overwrite existing output files.
        verbose: Enable verbose logging.
        quiet: Suppress non-essential output.
        no_progress: Disable progress bars.
        fp32: Force FP32 precision.
        fp16: Enable FP16 precision.

    Note:
        This function blocks until the watcher is stopped.

    """
    # Lazy import watcher to avoid unnecessary deps if not used
    from importlib import import_module  # pylint: disable=import-outside-toplevel

    watcher = import_module("parakeet_rocm.utils.watch").watch_and_transcribe

    # Determine base directories for mirroring subdirectories under --watch
    # Only directory paths are considered watch bases. Glob patterns are ignored
    # for mirroring to avoid ambiguous roots.
    base_dirs = []
    for w in watch:
        try:
            p = pathlib.Path(w).resolve()
            if p.is_dir():
                base_dirs.append(p)
        except Exception:
            # Ignore invalid paths; watcher will handle patterns
            pass

    def _transcribe_fn(new_files: list[pathlib.Path]) -> None:
        _impl = import_module("parakeet_rocm.transcribe").cli_transcribe
        _impl(
            audio_files=new_files,
            model_name=model_name,
            output_dir=output_dir,
            output_format=output_format,
            output_template=output_template,
            watch_base_dirs=base_dirs,
            batch_size=batch_size,
            chunk_len_sec=chunk_len_sec,
            stream=stream,
            stream_chunk_sec=stream_chunk_sec,
            overlap_duration=overlap_duration,
            highlight_words=highlight_words,
            word_timestamps=word_timestamps,
            stabilize=stabilize,
            demucs=demucs,
            vad=vad,
            vad_threshold=vad_threshold,
            merge_strategy=merge_strategy,
            overwrite=overwrite,
            verbose=verbose,
            quiet=quiet,
            no_progress=no_progress,
            fp32=fp32,
            fp16=fp16,
        )

    # Start watcher loop (blocking)
    return watcher(
        patterns=watch,
        transcribe_fn=_transcribe_fn,
        output_dir=output_dir,
        output_format=output_format,
        output_template=output_template,
        watch_base_dirs=base_dirs,
        verbose=verbose,
    )


@app.command()
def transcribe(
    audio_files: Annotated[
        list[str] | None,
        typer.Argument(
            help=("Path(s) or wildcard pattern(s) to audio files (e.g. '*.wav')."),
            show_default=False,
        ),
    ] = None,
    # Inputs
    watch: Annotated[
        list[str] | None,
        typer.Option(
            "--watch",
            help=(
                "Watch directory/pattern for new audio files and transcribe "
                "automatically."
            ),
        ),
    ] = None,
    # Model
    model_name: Annotated[
        str,
        typer.Option(
            "--model",
            help=("Hugging Face Hub model ID or local path to the NeMo ASR model."),
        ),
    ] = PARAKEET_MODEL_NAME,
    # Outputs
    output_dir: Annotated[
        pathlib.Path,
        typer.Option(
            "--output-dir",
            "-o",
            help="Directory to save the transcription outputs.",
            file_okay=False,
            dir_okay=True,
            writable=True,
            resolve_path=True,
        ),
    ] = "./output",
    output_format: Annotated[
        str,
        typer.Option(
            help=("Format for the output file(s) (e.g., txt, srt, vtt, json).")
        ),
    ] = "txt",
    output_template: Annotated[
        str,
        typer.Option(
            help=(
                "Template for output filenames. "
                "Supports placeholders: {parent}, {filename}, {index}, {date}."
            ),
        ),
    ] = "{filename}",
    overwrite: Annotated[
        bool,
        typer.Option(
            "--overwrite",
            help=(
                "Overwrite existing output files instead of appendingnumbered suffixes."
            ),
        ),
    ] = False,
    # Timestamps and subtitles
    word_timestamps: Annotated[
        bool,
        typer.Option(
            "--word-timestamps",
            help="Enable word-level timestamp generation.",
        ),
    ] = False,
    highlight_words: Annotated[
        bool,
        typer.Option(
            "--highlight-words",
            help="Highlight each word in SRT/VTT outputs (e.g., bold).",
        ),
    ] = False,
    stabilize: Annotated[
        bool,
        typer.Option(
            "--stabilize",
            help="Refine word timestamps using stable-ts.",
        ),
    ] = False,
    vad: Annotated[
        bool,
        typer.Option(
            "--vad",
            help="Enable voice activity detection during stabilization.",
        ),
    ] = False,
    demucs: Annotated[
        bool,
        typer.Option(
            "--demucs",
            help="Use Demucs denoiser during stabilization.",
        ),
    ] = False,
    vad_threshold: Annotated[
        float,
        typer.Option(
            "--vad-threshold",
            help="VAD probability threshold for suppression.",
        ),
    ] = 0.35,
    # Chunking and streaming
    chunk_len_sec: Annotated[
        int,
        typer.Option(help="Segment length in seconds for chunked transcription."),
    ] = DEFAULT_CHUNK_LEN_SEC,
    overlap_duration: Annotated[
        int,
        typer.Option(
            "--overlap-duration",
            help=("Overlap between consecutive chunks in seconds (for long audio)."),
        ),
    ] = 15,
    stream: Annotated[
        bool,
        typer.Option(
            "--stream",
            help="Enable pseudo-streaming mode (low-latency small chunks)",
        ),
    ] = False,
    stream_chunk_sec: Annotated[
        int,
        typer.Option(
            "--stream-chunk-sec",
            help=(
                "Chunk length in seconds when --stream is enabled (overrides default)."
            ),
        ),
    ] = 0,
    merge_strategy: Annotated[
        str,
        typer.Option(
            "--merge-strategy",
            help=(
                "Strategy for merging overlapping chunks: 'none' (concatenate), "
                "'contiguous' (fast merge), or 'lcs' (accurate, default)"
            ),
            case_sensitive=False,
        ),
    ] = "lcs",
    # Performance
    batch_size: Annotated[
        int, typer.Option(help="Batch size for transcription inference.")
    ] = DEFAULT_BATCH_SIZE,
    fp16: Annotated[
        bool,
        typer.Option(
            "--fp16",
            help=(
                "Enable half-precision (FP16) inference for faster processing on "
                "compatible hardware."
            ),
        ),
    ] = False,
    fp32: Annotated[
        bool,
        typer.Option(
            "--fp32",
            help=(
                "Force full-precision (FP32) inference. Default if no precision "
                "flag is provided."
            ),
        ),
    ] = False,
    # UX and logging
    no_progress: Annotated[
        bool,
        typer.Option(
            "--no-progress",
            help="Disable the Rich progress bar (silent mode).",
        ),
    ] = False,
    quiet: Annotated[
        bool,
        typer.Option(
            "--quiet",
            help=(
                "Suppress console messages except the progress bar and final output."
            ),
        ),
    ] = False,
    verbose: Annotated[
        bool,
        typer.Option(
            "--verbose",
            help="Enable verbose output.",
        ),
    ] = False,
) -> list[pathlib.Path] | None:
    """Transcribe audio files using the specified NeMo Parakeet model.

    Args:
        audio_files: Explicit paths or patterns to transcribe.
        watch: Directory or glob(s) to monitor for new audio files.
        model_name: Hugging Face model ID or local path.
        output_dir: Directory to save transcription outputs.
        output_format: Output format, e.g. ``txt``, ``srt``, ``vtt`` or ``json``.
        output_template: Filename template supporting placeholders.
        overwrite: Overwrite existing outputs when True.
        word_timestamps: Enable word-level timestamps.
        highlight_words: Highlight words in subtitle outputs.
        stabilize: Refine timestamps using stable-ts.
        vad: Enable VAD during stabilization.
        demucs: Enable Demucs denoising during stabilization.
        vad_threshold: VAD probability threshold.
        chunk_len_sec: Chunk length in seconds.
        overlap_duration: Overlap between chunks in seconds.
        stream: Enable pseudo-streaming mode.
        stream_chunk_sec: Streaming chunk size in seconds.
        merge_strategy: Strategy for merging overlapping chunks.
        batch_size: Batch size for inference.
        fp16: Use half precision.
        fp32: Use full precision.
        no_progress: Disable progress bar output.
        quiet: Suppress non-error output.
        verbose: Enable verbose logging.

    Returns:
        A list of created output paths, or ``None`` when running in watch mode.

    Raises:
        typer.BadParameter: When neither ``audio_files`` nor ``--watch`` provided.

    """
    # Delegation to heavy implementation (lazy import)
    from importlib import import_module  # pylint: disable=import-outside-toplevel

    # Normalise default
    if audio_files is None:
        audio_files = []

    # Validate input combinations
    if not audio_files and not watch:
        raise typer.BadParameter("Provide AUDIO_FILES or --watch pattern(s).")

    # Expand provided audio file patterns now (for immediate run or watcher seed)
    global RESOLVE_INPUT_PATHS  # pylint: disable=global-statement
    if RESOLVE_INPUT_PATHS is None:
        from parakeet_rocm.utils.file_utils import (  # pylint: disable=import-outside-toplevel
            resolve_input_paths as _resolve_input_paths,
        )

        RESOLVE_INPUT_PATHS = _resolve_input_paths

    resolved_paths = RESOLVE_INPUT_PATHS(audio_files)

    if watch:
        return _setup_watch_mode(
            watch=watch,
            model_name=model_name,
            output_dir=output_dir,
            output_format=output_format,
            output_template=output_template,
            batch_size=batch_size,
            chunk_len_sec=chunk_len_sec,
            stream=stream,
            stream_chunk_sec=stream_chunk_sec,
            overlap_duration=overlap_duration,
            highlight_words=highlight_words,
            word_timestamps=word_timestamps,
            stabilize=stabilize,
            demucs=demucs,
            vad=vad,
            vad_threshold=vad_threshold,
            merge_strategy=merge_strategy,
            overwrite=overwrite,
            verbose=verbose,
            quiet=quiet,
            no_progress=no_progress,
            fp32=fp32,
            fp16=fp16,
        )

    # No watch mode: immediate transcription
    _impl = import_module("parakeet_rocm.transcribe").cli_transcribe

    return _impl(
        audio_files=resolved_paths,
        model_name=model_name,
        output_dir=output_dir,
        output_format=output_format,
        output_template=output_template,
        batch_size=batch_size,
        chunk_len_sec=chunk_len_sec,
        stream=stream,
        stream_chunk_sec=stream_chunk_sec,
        overlap_duration=overlap_duration,
        highlight_words=highlight_words,
        word_timestamps=word_timestamps,
        stabilize=stabilize,
        demucs=demucs,
        vad=vad,
        vad_threshold=vad_threshold,
        merge_strategy=merge_strategy,
        overwrite=overwrite,
        verbose=verbose,
        quiet=quiet,
        no_progress=no_progress,
        fp32=fp32,
        fp16=fp16,
    )
