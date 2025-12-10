"""Per-file transcription processing utilities."""

# pylint: disable=import-outside-toplevel

from __future__ import annotations

from collections.abc import Callable, Iterator, Sequence
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol, TypeVar

from rich.progress import Progress, TaskID

from parakeet_rocm.chunking import (
    MERGE_STRATEGIES,
    segment_waveform,
)
from parakeet_rocm.config import (
    OutputConfig,
    StabilizationConfig,
    TranscriptionConfig,
    UIConfig,
)
from parakeet_rocm.formatting import get_formatter_spec
from parakeet_rocm.integrations.stable_ts import refine_word_timestamps
from parakeet_rocm.timestamps.models import AlignedResult, Segment, Word
from parakeet_rocm.timestamps.segmentation import segment_words
from parakeet_rocm.timestamps.word_timestamps import get_word_timestamps
from parakeet_rocm.transcription.utils import calc_time_stride
from parakeet_rocm.utils.audio_io import DEFAULT_SAMPLE_RATE, load_audio
from parakeet_rocm.utils.constant import MAX_CPS, MAX_LINE_CHARS
from parakeet_rocm.utils.file_utils import get_unique_filename

T = TypeVar("T")


class SupportsTranscribe(Protocol):
    """Protocol for ASR models that expose a ``transcribe`` method.

    The signature matches NeMo-like ASR models used in this project.
    """

    def transcribe(
        self,
        *,
        audio: Sequence[Any],
        batch_size: int,
        return_hypotheses: bool,
        verbose: bool,
    ) -> Sequence[Any]:
        """Transcribe a batch of audio samples.

        Parameters:
            audio (Sequence[Any]): Sequence of audio inputs where each item is
                an audio array or buffer for a single sample.
            batch_size (int): Effective batch size to use for inference.
            return_hypotheses (bool): If ``True``, return model hypothesis
                objects containing timing/metadata; if ``False``, return plain
                transcription strings.
            verbose (bool): If ``True``, enable verbose logging during
                transcription.

        Returns:
            Sequence[Any]: Hypothesis objects when ``return_hypotheses`` is
                ``True``, otherwise transcription strings.
        """


class Formatter(Protocol):
    """Protocol for output formatters used by the transcription pipeline."""

    def __call__(self, aligned: AlignedResult, *, highlight_words: bool = ...) -> str:  # noqa: D401
        """Format an aligned result into a textual representation.

        Parameters:
            aligned (AlignedResult): Aligned transcription result to format.
            highlight_words (bool): If ``True``, include word-level
                highlighting or markup in the output.

        Returns:
            str: The formatted transcription.
        """


def _chunks(seq: Sequence[T], size: int) -> Iterator[Sequence[T]]:
    """Yield successive chunks from a sequence.

    Args:
        seq: The input sequence to be chunked.
        size: The maximum size for each yielded chunk.

    Yields:
        Slices of ``seq`` with length up to ``size``.

    """
    for i in range(0, len(seq), size):
        yield seq[i : i + size]


def _transcribe_batches(
    model: SupportsTranscribe,
    segments: Sequence[tuple],
    batch_size: int,
    word_timestamps: bool,
    progress: Progress,
    main_task: TaskID | None,
    no_progress: bool,
) -> tuple[list[Any], list[str]]:
    """Transcribe (audio, offset) segments in batches and update progress.

    Parameters:
        model: ASR model implementing a `transcribe` method.
        segments (Sequence[tuple]): Iterable of (audio, start_offset) tuples to transcribe.
        batch_size (int): Maximum number of segments sent to the model per batch.
        word_timestamps (bool): If True, request hypotheses that include word-level timestamps.
        progress: Rich Progress instance used to report progress.
        main_task: Task ID to advance for progress updates; ignored if None.
        no_progress (bool): If True, do not advance the progress task.

    Returns:
        tuple[list[Any], list[str]]: Pair ``(hypotheses, texts)`` where
            ``hypotheses`` is a list of model hypothesis objects (when
            ``word_timestamps`` is ``True``; each hypothesis has
            ``start_offset`` set) and ``texts`` is a list of plain
            transcription strings (when ``word_timestamps`` is ``False``).
    """
    import torch  # pylint: disable=import-outside-toplevel

    hypotheses = []
    texts: list[str] = []
    for batch in _chunks(segments, batch_size):
        batch_wavs = [seg for seg, _off in batch]
        batch_offsets = [_off for _seg, _off in batch]
        with torch.inference_mode():
            results = model.transcribe(
                audio=batch_wavs,
                batch_size=len(batch_wavs),
                return_hypotheses=word_timestamps,
                verbose=False,
            )
        if not results:
            continue
        if word_timestamps:
            for hyp, off in zip(results, batch_offsets):
                setattr(hyp, "start_offset", off)
            hypotheses.extend(results)
        else:
            texts.extend(
                [hyp.text for hyp in results] if hasattr(results[0], "text") else list(results)
            )
        if not no_progress and main_task is not None:
            progress.advance(main_task, len(batch_wavs))
    return hypotheses, texts


def _merge_word_segments(
    hypotheses: list[Any],
    model: SupportsTranscribe,
    merge_strategy: str,
    overlap_duration: int,
    verbose: bool,
) -> AlignedResult:
    """Merge word-level hypotheses from multiple chunks.

    Args:
        hypotheses: List of model hypotheses.
        model: Loaded ASR model.
        merge_strategy: Strategy identifier (``"lcs"`` or ``"contiguous"``).
        overlap_duration: Overlap duration between chunks in seconds.
        verbose: Whether to emit diagnostic messages.

    Returns:
        An ``AlignedResult`` containing merged word segments.

    """
    from parakeet_rocm.timestamps.adapt import adapt_nemo_hypotheses

    time_stride = calc_time_stride(model, verbose)
    aligned_result = adapt_nemo_hypotheses(hypotheses, model, time_stride)
    if merge_strategy != "none" and len(hypotheses) > 1:
        # Retrieve merge function from registry
        merger = MERGE_STRATEGIES[merge_strategy]

        chunk_word_lists: list[list[Word]] = [
            get_word_timestamps([h], model, time_stride) for h in hypotheses
        ]
        merged_words: list[Word] = chunk_word_lists[0]
        for next_words in chunk_word_lists[1:]:
            merged_words = merger(merged_words, next_words, overlap_duration=overlap_duration)
        words_sorted = sorted(merged_words, key=lambda w: w.start)
        merged_words = merger(words_sorted, [], overlap_duration=overlap_duration)
        aligned_result = AlignedResult(
            segments=segment_words(merged_words),
            word_segments=merged_words,
        )
    return aligned_result


def _load_and_prepare_audio(
    audio_path: Path,
    chunk_len_sec: int,
    overlap_duration: int,
    verbose: bool,
    quiet: bool,
) -> tuple[Any, int, list[tuple[Any, int]], float, float]:
    """Load audio file and prepare segments for transcription.

    Args:
        audio_path: Path to the audio file.
        chunk_len_sec: Length of each audio chunk in seconds.
        overlap_duration: Overlap between chunks in seconds.
        verbose: Whether to emit diagnostic messages.
        quiet: Whether to suppress all output.

    Returns:
        A tuple of ``(wav, sample_rate, segments, load_elapsed, duration_sec)``.

    """
    import time

    import typer

    t_load = time.perf_counter()
    wav, sample_rate = load_audio(audio_path, DEFAULT_SAMPLE_RATE)
    load_elapsed = time.perf_counter() - t_load
    duration_sec = len(wav) / float(sample_rate) if sample_rate else 0.0
    segments = segment_waveform(wav, sample_rate, chunk_len_sec, overlap_duration)

    if verbose and not quiet:
        typer.echo(
            "[file] "
            f"{audio_path.name}: sr={sample_rate}, dur={duration_sec:.2f}s, "
            f"segments={len(segments)}, chunk={chunk_len_sec}s, "
            f"overlap={overlap_duration}s, t_load={load_elapsed:.2f}s"
        )
        # show first few segment ranges
        preview = 3
        for i, (_seg, off) in enumerate(segments[:preview]):
            start = off
            end = off + chunk_len_sec
            typer.echo(f"[plan] seg{i}: {start:.2f}s→{end:.2f}s")

    return wav, sample_rate, segments, load_elapsed, duration_sec


def _apply_stabilization(
    aligned_result: AlignedResult,
    audio_path: Path,
    stabilization_config: StabilizationConfig,
    ui_config: UIConfig,
) -> AlignedResult:
    """Apply timestamp stabilization to word-level segments when enabled.

    Parameters:
        aligned_result (AlignedResult): Aligned result containing word-level
            segments to refine.
        audio_path (Path): Path to the source audio file used for
            refinement.
        stabilization_config (StabilizationConfig): Options controlling
            stabilization (for example Demucs, VAD, thresholds).
        ui_config (UIConfig): UI/logging settings that control verbose
            diagnostic output.

    Returns:
        AlignedResult: Refined aligned result when stabilization runs
            successfully; otherwise the original ``aligned_result``.
    """
    import time

    import typer

    if not stabilization_config.enabled:
        return aligned_result

    try:
        # Pre-stabilization diagnostics
        pre_words: list[Word] = list(aligned_result.word_segments or [])
        if ui_config.verbose and not ui_config.quiet:
            # Detect package versions without importing heavy modules
            try:  # Python 3.10+: importlib.metadata
                from importlib.metadata import (  # type: ignore
                    PackageNotFoundError,
                    version,
                )
            except ImportError:  # pragma: no cover - extremely unlikely
                version = None  # type: ignore
                package_not_found_error = Exception  # type: ignore
            else:
                # Create a lowercase alias for linting/PEP8 compliance
                package_not_found_error = PackageNotFoundError  # type: ignore

            sw_ver = None
            demucs_ver = None
            vad_ver = None
            if version is not None:
                try:
                    sw_ver = version("stable-ts")
                except package_not_found_error:  # type: ignore
                    sw_ver = None
                if sw_ver is None:
                    try:
                        sw_ver = version("stable_whisper")
                    except package_not_found_error:  # type: ignore
                        sw_ver = None
                if stabilization_config.demucs:
                    try:
                        demucs_ver = version("demucs")
                    except package_not_found_error:  # type: ignore
                        demucs_ver = None
                if stabilization_config.vad:
                    try:
                        vad_ver = version("silero-vad")
                    except package_not_found_error:  # type: ignore
                        vad_ver = None

            # Echo options about to be used by stable-ts
            vad_thr = stabilization_config.vad_threshold if stabilization_config.vad else None
            typer.echo(
                "[stable-ts] preparing: "
                f"version={sw_ver or 'unknown'} "
                f"options={{'demucs': {stabilization_config.demucs}, "
                f"'vad': {stabilization_config.vad}, "
                f"'vad_threshold': {vad_thr}}}"
            )
            if stabilization_config.demucs:
                typer.echo(f"[demucs] enabled: package_version={demucs_ver or 'unknown'}")
            if stabilization_config.vad:
                typer.echo(
                    f"[vad] enabled: "
                    f"threshold={stabilization_config.vad_threshold:.2f} "
                    f"package_version={vad_ver or 'unknown'}"
                )
            if stabilization_config.demucs or stabilization_config.vad:
                # We default to stronger silence-suppression-based
                # realignment so that Demucs/VAD effects are observable
                # during stabilization.
                typer.echo(
                    "[stable-ts] realign: suppress_silence=True "
                    "suppress_word_ts=True q_levels=10 k_size=3 "
                    "min_word_dur=0.03 force_order=True"
                )

        t_stab = time.perf_counter()
        refined = refine_word_timestamps(
            aligned_result.word_segments,
            audio_path,
            demucs=stabilization_config.demucs,
            vad=stabilization_config.vad,
            vad_threshold=stabilization_config.vad_threshold,
            verbose=bool(ui_config.verbose and not ui_config.quiet),
        )
        stab_elapsed = time.perf_counter() - t_stab
        new_segments = segment_words(refined)
        aligned_result = AlignedResult(
            segments=new_segments,
            word_segments=refined,
        )
        if ui_config.verbose and not ui_config.quiet:
            # Keep existing summary line
            typer.echo(
                "[stable-ts] api=transcribe_any "
                f"demucs={stabilization_config.demucs} vad={stabilization_config.vad} "
                f"thr={stabilization_config.vad_threshold} t_stab={stab_elapsed:.2f}s"
            )
            # Post-stabilization stats to help verify VAD/Demucs effects
            n_pre = len(pre_words)
            n_post = len(refined)
            common = min(n_pre, n_post)
            changed = 0
            for i in range(common):
                ds = abs(refined[i].start - pre_words[i].start)
                de = abs(refined[i].end - pre_words[i].end)
                if ds > 0.02 or de > 0.02:  # consider >20ms as a change
                    changed += 1
            pct_changed = (100.0 * changed / common) if common else 0.0
            start_shift = (refined[0].start - pre_words[0].start) if (n_pre and n_post) else 0.0
            end_shift = (refined[-1].end - pre_words[-1].end) if (n_pre and n_post) else 0.0
            words_removed = max(0, (n_pre - n_post)) if n_pre and n_post else 0
            typer.echo(
                "[stable-ts] result: "
                f"segments={len(new_segments)} "
                f"words_pre={n_pre} words_post={n_post} "
                f"changed≈{changed} ({pct_changed:.1f}%) "
                f"start_shift={start_shift:+.2f}s "
                f"end_shift={end_shift:+.2f}s"
            )
            if stabilization_config.vad:
                typer.echo(f"[vad] post-stab: words_removed={words_removed}")
    except RuntimeError as exc:
        if ui_config.verbose and not ui_config.quiet:
            typer.echo(f"Stabilization skipped: {exc}", err=True)

    return aligned_result


def _format_and_save_output(
    aligned_result: AlignedResult,
    formatter: Formatter | Callable[[AlignedResult], str],
    output_config: OutputConfig,
    audio_path: Path,
    file_idx: int,
    watch_base_dirs: Sequence[Path] | None,
    ui_config: UIConfig,
) -> Path:
    """Format an aligned result and write the output to a file.

    The transcription is formatted using ``formatter``. The output filename
    is resolved from ``output_config.output_template`` (substituting
    ``filename`` and ``index``), optionally mirroring the audio file's
    subdirectory under one of ``watch_base_dirs``. The target directory is
    created if needed and the formatted text is written. When
    ``ui_config.verbose`` is true and not quiet, a short summary including the
    output filename, overwrite mode, block count, and time range is printed.

    Parameters:
        aligned_result: Aligned transcription result to format and save.
        formatter: Callable that formats an ``AlignedResult`` to a string (may
            support ``highlight_words``).
        output_config: Configuration controlling output template, directory,
            overwrite, and highlighting.
        audio_path: Path to the source audio file (used for template
            substitution and directory mirroring).
        file_idx: Numeric index used for template substitution when
            generating the filename.
        watch_base_dirs: Optional base directories whose relative subpaths
            are preserved under the output directory.
        ui_config: UI configuration controlling verbose and quiet logging
            behaviour.

    Returns:
        Path: Path to the written output file.

    Raises:
        ValueError: If ``output_config.output_template`` contains an unknown
            placeholder.
    """
    import typer

    # Get formatter spec to check if highlighting is supported
    formatter_spec = get_formatter_spec(output_config.output_format)

    formatted_text = (
        formatter(aligned_result, highlight_words=output_config.highlight_words)
        if formatter_spec.supports_highlighting
        else formatter(aligned_result)
    )

    parent_name = audio_path.parent.name
    date_str = datetime.now().strftime("%Y%m%d")
    template_context = {
        "filename": audio_path.stem,
        "index": file_idx,
        "parent": parent_name,
        "date": date_str,
    }

    try:
        filename_part = output_config.output_template.format(**template_context)
    except KeyError as exc:  # pragma: no cover
        raise ValueError(f"Unknown placeholder in --output-template: {exc}") from exc

    # Mirror subdirectory structure if audio originates from a subfolder under
    # any provided watch base directory.
    target_dir = output_config.output_dir
    if watch_base_dirs:
        for base in watch_base_dirs:
            try:
                rel = audio_path.parent.relative_to(base)
            except Exception:
                continue
            else:
                if str(rel) != "." and str(rel) != "":
                    target_dir = output_config.output_dir / rel
                break

    # Ensure directory exists before writing
    target_dir.mkdir(parents=True, exist_ok=True)

    base_output_path = target_dir / f"{filename_part}{formatter_spec.file_extension}"
    output_path = get_unique_filename(base_output_path, overwrite=output_config.overwrite)
    output_path.write_text(formatted_text, encoding="utf-8")
    if ui_config.verbose and not ui_config.quiet:
        # Report coverage window if segments are present
        if aligned_result.segments:
            first_ts = aligned_result.segments[0].start
            last_ts = aligned_result.segments[-1].end
            typer.echo(
                "[output] "
                f"path={output_path.name} overwrite={output_config.overwrite} "
                f"blocks={len(aligned_result.segments)} "
                f"range={first_ts:.2f}s→{last_ts:.2f}s"
            )
        else:
            typer.echo(
                f"[output] path={output_path.name} overwrite={output_config.overwrite} blocks=0"
            )
    return output_path


def transcribe_file(
    audio_path: Path,
    *,
    model: SupportsTranscribe,
    formatter: Formatter | Callable[[AlignedResult], str],
    file_idx: int,
    transcription_config: TranscriptionConfig,
    stabilization_config: StabilizationConfig,
    output_config: OutputConfig,
    ui_config: UIConfig,
    watch_base_dirs: Sequence[Path] | None = None,
    progress: Progress | None = None,
    main_task: TaskID | None = None,
) -> Path | None:
    """Transcribe a single audio file and save formatted output.

    This function orchestrates the transcription pipeline by calling focused
    helper functions for each stage: audio loading, transcription, merging,
    stabilization, and output formatting.

    Args:
        audio_path: Path to the audio file.
        model: Loaded ASR model.
        formatter: Output formatter callable.
        file_idx: Index of the audio file for template substitution.
        transcription_config: Configuration for transcription settings.
        stabilization_config: Configuration for stable-ts refinement.
        output_config: Configuration for output settings.
        ui_config: Configuration for UI and logging.
        watch_base_dirs: Optional base directories used by ``--watch``. If
            provided and ``audio_path`` is within one of these directories, the
            output will mirror the subdirectory structure beneath the base
            directory, e.g. ``<output-dir>/<sub-dir>/``.
        progress: Rich progress instance for updates.
        main_task: Task handle within the progress bar.

    Returns:
        Path to the created file or ``None`` if processing failed.

    """
    import time

    import typer

    # Step 1: Load and prepare audio
    wav, sample_rate, segments, load_elapsed, duration_sec = _load_and_prepare_audio(
        audio_path=audio_path,
        chunk_len_sec=transcription_config.chunk_len_sec,
        overlap_duration=transcription_config.overlap_duration,
        verbose=ui_config.verbose,
        quiet=ui_config.quiet,
    )

    # Step 2: Transcribe audio segments
    t_asr = time.perf_counter()
    if progress is None:
        from rich.progress import Progress as ProgressClass

        progress = ProgressClass()

    hypotheses, texts = _transcribe_batches(
        model=model,
        segments=segments,
        batch_size=transcription_config.batch_size,
        word_timestamps=transcription_config.word_timestamps,
        progress=progress,
        main_task=main_task,
        no_progress=ui_config.no_progress,
    )
    asr_elapsed = time.perf_counter() - t_asr

    if ui_config.verbose and not ui_config.quiet:
        n_hyps = len(hypotheses) if transcription_config.word_timestamps else 0
        n_txt = len(texts) if not transcription_config.word_timestamps else 0
        typer.echo(f"[asr] batches done: hyps={n_hyps}texts={n_txt}, t_asr={asr_elapsed:.2f}s")

    # Step 3: Process transcription results
    if transcription_config.word_timestamps:
        if not hypotheses:
            if not ui_config.quiet:
                typer.echo(
                    f"Warning: No transcription generated for {audio_path.name}",
                    err=True,
                )
            return None

        # Merge word segments from multiple chunks
        aligned_result = _merge_word_segments(
            hypotheses=hypotheses,
            model=model,
            merge_strategy=transcription_config.merge_strategy,
            overlap_duration=transcription_config.overlap_duration,
            verbose=ui_config.verbose,
        )

        # Apply stabilization if enabled
        aligned_result = _apply_stabilization(
            aligned_result=aligned_result,
            audio_path=audio_path,
            stabilization_config=stabilization_config,
            ui_config=ui_config,
        )
    else:
        # Text-only output (no word timestamps)
        formatter_spec = get_formatter_spec(output_config.output_format)
        if formatter_spec.requires_word_timestamps:
            if not ui_config.quiet:
                typer.echo(
                    (
                        "Error: Format "
                        f"'{output_config.output_format}' requires word timestamps. "
                        "Please use --word-timestamps."
                    ),
                    err=True,
                )
            return None
        full_text = " ".join(texts)
        mock_segment = Segment(text=full_text, words=[], start=0, end=0)
        aligned_result = AlignedResult(segments=[mock_segment], word_segments=[])

    # Debug output for subtitle segments
    if ui_config.verbose and transcription_config.word_timestamps and not ui_config.quiet:
        typer.echo("\n--- Subtitle Segments Debug ---")
        for i, seg in enumerate(aligned_result.segments[:10]):
            chars = len(seg.text.replace("\n", " "))
            dur = seg.end - seg.start
            cps = chars / max(dur, 1e-3)
            lines = seg.text.count("\n") + 1
            flag = (
                "⚠︎"
                if cps > MAX_CPS or any(len(line) > MAX_LINE_CHARS for line in seg.text.split("\n"))
                else "OK"
            )
            typer.echo(
                f"Seg {i}: {chars} chars, {dur:.2f}s, {cps:.1f} cps, "
                f"{lines} lines [{flag}] -> '"
                f"{seg.text.replace(chr(10), ' | ')}'"
            )
        typer.echo("------------------------------\n")

    # Step 4: Format and save output
    return _format_and_save_output(
        aligned_result=aligned_result,
        formatter=formatter,
        output_config=output_config,
        audio_path=audio_path,
        file_idx=file_idx,
        watch_base_dirs=watch_base_dirs,
        ui_config=ui_config,
    )
