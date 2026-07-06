#!/usr/bin/env python3
"""Compare two NeMo Parakeet ASR models on one or more audio files.

The script transcribes the same audio with both a baseline model (default:
``nvidia/parakeet-tdt-0.6b-v3``) and a candidate model, exercising the same
pipeline the CLI uses: model loading, chunked transcription, word-level
timestamps (when supported), benchmark metrics, and all built-in output
formats. Results are written as JSON and Markdown for reproducible comparison.

This is intentionally a standalone script rather than CLI subcommand so it can
be evolved and run without changing the public CLI contract.
"""

from __future__ import annotations

import json
import logging
import re
import sys
import time
from collections.abc import Sequence
from dataclasses import asdict, dataclass, field
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

import typer

from parakeet_rocm.benchmarks.collector import BenchmarkCollector, GpuUtilSampler
from parakeet_rocm.formatting import FORMATTERS
from parakeet_rocm.models.parakeet import clear_model_cache, get_model
from parakeet_rocm.timestamps.adapt import adapt_nemo_hypotheses
from parakeet_rocm.transcription.file_processor import _load_and_prepare_audio, _transcribe_batches
from parakeet_rocm.transcription.utils import calc_time_stride, configure_environment
from parakeet_rocm.utils.constant import (
    BENCHMARK_OUTPUT_DIR,
    DEFAULT_BATCH_SIZE,
    DEFAULT_CHUNK_LEN_SEC,
    PARAKEET_MODEL_NAME,
    SUPPORTED_EXTENSIONS,
)
from parakeet_rocm.utils.logging_config import get_logger

logger = get_logger(__name__)

app = typer.Typer(add_completion=False, no_args_is_help=True)


def _slugify(value: str) -> str:
    """Convert a model name into a safe filename component.

    Returns:
        str: Sanitised model name safe for use in filenames.
    """
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("._-")
    return cleaned or "model"


@dataclass
class ModelResult:
    """Per-model transcription result and metadata."""

    model_name: str
    transcription: str = ""
    word_count: int = 0
    segment_count: int = 0
    runtime_seconds: float = 0.0
    load_seconds: float = 0.0
    audio_duration_sec: float = 0.0
    gpu_stats: dict[str, Any] | None = field(default=None)
    timestamp_compatible: bool = False
    timestamp_notes: str = ""
    output_paths: dict[str, str] = field(default_factory=dict)
    error: str | None = None


@dataclass
class ComparisonResult:
    """Comparison output for one audio file."""

    audio_path: str
    baseline: ModelResult
    candidate: ModelResult
    audio_duration_sec: float = 0.0
    text_similarity_ratio: float = 0.0
    notes: list[str] = field(default_factory=list)


@dataclass
class EvaluationRun:
    """Top-level result for the whole evaluation run."""

    baseline_model: str
    candidate_model: str
    files: list[ComparisonResult] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def _text_similarity(a: str, b: str) -> float:
    """Return a normalised sequence-similarity ratio between two word lists.

    Each transcription is normalised to lower-case words before comparing the
    ordered word sequences with ``SequenceMatcher``.

    Args:
        a: First transcription.
        b: Second transcription.

    Returns:
        Similarity in [0.0, 1.0] based on ordered word-sequence matching.
    """
    a_words = re.sub(r"\s+", " ", a.strip().lower()).split()
    b_words = re.sub(r"\s+", " ", b.strip().lower()).split()
    if not a_words and not b_words:
        return 1.0
    if not a_words or not b_words:
        return 0.0
    return SequenceMatcher(None, a_words, b_words).ratio()


def _collect_one(
    audio_path: Path,
    model_name: str,
    output_dir: Path,
    chunk_len_sec: int,
    batch_size: int,
    word_timestamps: bool,
    formats: Sequence[str],
) -> ModelResult:
    """Transcribe a single audio file with one model and collect metrics.

    Returns:
        ModelResult: Transcription result, timing metrics, and output paths.
    """
    result = ModelResult(model_name=model_name)

    t_load_start = time.perf_counter()
    try:
        model = get_model(model_name)
    except Exception as exc:  # pragma: no cover - exercised in GPU integration tests
        logger.exception("failed to load model %s", model_name)
        result.error = f"load failed: {exc}"
        return result
    result.load_seconds = time.perf_counter() - t_load_start

    collector = BenchmarkCollector(
        output_dir=BENCHMARK_OUTPUT_DIR,
        slug=f"eval_{_slugify(model_name)}_{audio_path.stem}",
        config={
            "model_name": model_name,
            "batch_size": batch_size,
            "chunk_len_sec": chunk_len_sec,
            "word_timestamps": word_timestamps,
        },
        audio_path=str(audio_path),
        task="evaluate_model",
    )

    try:
        _wav, _sample_rate, segments, load_elapsed, duration_sec = _load_and_prepare_audio(
            audio_path=audio_path,
            chunk_len_sec=chunk_len_sec,
            overlap_duration=0,
            verbose=False,
            quiet=True,
        )
    except Exception as exc:  # pragma: no cover - exercised in GPU integration tests
        logger.exception("failed to load audio %s", audio_path)
        result.error = f"audio load failed: {exc}"
        return result

    result.runtime_seconds = load_elapsed
    result.audio_duration_sec = duration_sec

    try:
        t_infer = time.perf_counter()
        from rich.progress import Progress

        sampler = GpuUtilSampler(interval_sec=1.0)
        sampler.start()
        try:
            with Progress(disable=True) as progress:
                main_task = progress.add_task("transcribe", total=len(segments))
                hypotheses, texts = _transcribe_batches(
                    model=model,
                    segments=segments,
                    batch_size=batch_size,
                    word_timestamps=word_timestamps,
                    progress=progress,
                    main_task=main_task,
                    no_progress=True,
                    batch_progress_callback=None,
                )
        finally:
            sampler.stop()
        result.runtime_seconds += time.perf_counter() - t_infer
        result.gpu_stats = sampler.get_stats()

        if word_timestamps and hypotheses:
            try:
                time_stride = calc_time_stride(model, verbose=False)
                aligned = adapt_nemo_hypotheses(hypotheses, model, time_stride)
                result.transcription = " ".join(
                    seg.text.replace("\n", " ") for seg in aligned.segments
                )
                result.word_count = len(aligned.word_segments)
                result.segment_count = len(aligned.segments)
                result.timestamp_compatible = True
                result.timestamp_notes = "adapt_nemo_hypotheses succeeded"

                for fmt in formats:
                    spec = FORMATTERS.get(fmt)
                    if spec is None:
                        continue
                    try:
                        text = spec.format_func(aligned)
                        out_path = output_dir / f"{audio_path.stem}_{_slugify(model_name)}.{fmt}"
                        out_path.write_text(text, encoding="utf-8")
                        result.output_paths[fmt] = str(out_path)
                    except Exception as fmt_exc:  # pragma: no cover
                        logger.warning(
                            "format %s failed for %s: %s",
                            fmt,
                            model_name,
                            fmt_exc,
                        )
            except Exception as exc:  # pragma: no cover - exercised in GPU tests
                logger.exception("word timestamp adaptation failed for %s", model_name)
                result.timestamp_compatible = False
                result.timestamp_notes = f"word timestamp adaptation failed: {exc}"
                result.transcription = ""
                result.word_count = 0
                result.segment_count = 0
        elif texts:
            result.transcription = " ".join(texts)
            result.word_count = len(result.transcription.split())
            result.segment_count = 0
            result.timestamp_compatible = False
            result.timestamp_notes = "plain text transcription (word timestamps disabled)"
        else:
            result.timestamp_notes = "no transcription output returned"

    except Exception as exc:  # pragma: no cover - exercised in GPU integration tests
        logger.exception("inference failed for %s on %s", model_name, audio_path)
        result.error = f"inference failed: {exc}"

    collector.metrics["runtime_seconds"] = result.runtime_seconds
    collector.metrics["gpu_stats"] = result.gpu_stats or {}
    collector.add_file_metrics(
        filename=audio_path.name,
        duration_sec=duration_sec,
        segment_count=result.segment_count,
        processing_time_sec=result.runtime_seconds,
    )
    try:
        collector.write_json()
    except Exception:  # pragma: no cover
        logger.debug("benchmark write failed", exc_info=True)

    return result


def _compare(
    audio_path: Path,
    baseline_name: str,
    candidate_name: str,
    output_dir: Path,
    chunk_len_sec: int,
    batch_size: int,
    word_timestamps: bool,
    formats: Sequence[str],
) -> ComparisonResult:
    """Run both models on one audio file and compare.

    Returns:
        ComparisonResult: Side-by-side result for the audio file.
    """
    clear_model_cache()
    baseline = _collect_one(
        audio_path,
        baseline_name,
        output_dir,
        chunk_len_sec=chunk_len_sec,
        batch_size=batch_size,
        word_timestamps=word_timestamps,
        formats=formats,
    )
    clear_model_cache()
    candidate = _collect_one(
        audio_path,
        candidate_name,
        output_dir,
        chunk_len_sec=chunk_len_sec,
        batch_size=batch_size,
        word_timestamps=word_timestamps,
        formats=formats,
    )
    clear_model_cache()

    duration_sec = max(baseline.audio_duration_sec, candidate.audio_duration_sec)
    notes: list[str] = []

    if baseline.transcription and candidate.transcription:
        similarity = _text_similarity(baseline.transcription, candidate.transcription)
    else:
        similarity = 0.0
        if baseline.error:
            notes.append(f"baseline error: {baseline.error}")
        if candidate.error:
            notes.append(f"candidate error: {candidate.error}")
        if not baseline.transcription and not baseline.error:
            notes.append("baseline produced empty transcription")
        if not candidate.transcription and not candidate.error:
            notes.append("candidate produced empty transcription")

    if baseline.timestamp_compatible != candidate.timestamp_compatible:
        notes.append(
            "timestamp compatibility differs: baseline="
            f"{baseline.timestamp_compatible}, candidate={candidate.timestamp_compatible}"
        )

    if baseline.gpu_stats or candidate.gpu_stats:
        notes.append(
            f"GPU telemetry available: baseline={baseline.gpu_stats is not None}, "
            f"candidate={candidate.gpu_stats is not None}"
        )

    return ComparisonResult(
        audio_path=str(audio_path),
        audio_duration_sec=duration_sec,
        baseline=baseline,
        candidate=candidate,
        text_similarity_ratio=similarity,
        notes=notes,
    )


def _serialise(obj: object) -> object:
    """Convert dataclasses and paths to JSON-safe structures.

    Args:
        obj: Object to serialise.

    Returns:
        JSON-safe representation of ``obj``.
    """
    if isinstance(obj, Path):
        return str(obj)
    if isinstance(obj, ModelResult):
        return asdict(obj)
    if isinstance(obj, ComparisonResult):
        return asdict(obj)
    if isinstance(obj, EvaluationRun):
        return asdict(obj)
    return obj


def _write_json(run: EvaluationRun, output_dir: Path) -> Path:
    """Write the evaluation run as JSON.

    Returns:
        Path: Path to the written JSON report.
    """
    slug_baseline = _slugify(run.baseline_model)
    slug_candidate = _slugify(run.candidate_model)
    out = output_dir / f"evaluation_{slug_baseline}_vs_{slug_candidate}.json"
    out.write_text(
        json.dumps(run, default=_serialise, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return out


def _write_markdown(run: EvaluationRun, output_dir: Path) -> Path:
    """Write a human-readable Markdown report.

    Returns:
        Path: Path to the written Markdown report.
    """
    slug_baseline = _slugify(run.baseline_model)
    slug_candidate = _slugify(run.candidate_model)
    out = output_dir / f"evaluation_{slug_baseline}_vs_{slug_candidate}.md"
    lines: list[str] = [
        "# Model evaluation report",
        "",
        f"- Baseline: `{run.baseline_model}`",
        f"- Candidate: `{run.candidate_model}`",
        "",
    ]
    if run.notes:
        lines.extend(["## Run-level notes", "", *(f"- {note}" for note in run.notes), ""])

    for result in run.files:
        lines.extend([
            f"## {Path(result.audio_path).name}",
            "",
            f"Duration: {result.audio_duration_sec:.2f}s",
            f"Text similarity ratio: {result.text_similarity_ratio:.3f}",
            "",
            "### Baseline",
            "",
            f"- Model: `{result.baseline.model_name}`",
            f"- Runtime: {result.baseline.runtime_seconds:.2f}s",
            f"- Load time: {result.baseline.load_seconds:.2f}s",
            f"- Audio duration: {result.baseline.audio_duration_sec:.2f}s",
            f"- GPU stats: {result.baseline.gpu_stats or 'none'}",
            f"- Word count: {result.baseline.word_count}",
            f"- Segment count: {result.baseline.segment_count}",
            f"- Timestamp compatible: {result.baseline.timestamp_compatible}",
            f"- Timestamp notes: {result.baseline.timestamp_notes}",
            f"- Error: {result.baseline.error or 'none'}",
            "",
            "### Candidate",
            "",
            f"- Model: `{result.candidate.model_name}`",
            f"- Runtime: {result.candidate.runtime_seconds:.2f}s",
            f"- Load time: {result.candidate.load_seconds:.2f}s",
            f"- Audio duration: {result.candidate.audio_duration_sec:.2f}s",
            f"- GPU stats: {result.candidate.gpu_stats or 'none'}",
            f"- Word count: {result.candidate.word_count}",
            f"- Segment count: {result.candidate.segment_count}",
            f"- Timestamp compatible: {result.candidate.timestamp_compatible}",
            f"- Timestamp notes: {result.candidate.timestamp_notes}",
            f"- Error: {result.candidate.error or 'none'}",
            "",
        ])
        if result.baseline.output_paths:
            lines.extend(["#### Baseline output files", ""])
            for fmt, path in sorted(result.baseline.output_paths.items()):
                lines.append(f"- {fmt}: `{path}`")
            lines.append("")
        if result.candidate.output_paths:
            lines.extend(["#### Candidate output files", ""])
            for fmt, path in sorted(result.candidate.output_paths.items()):
                lines.append(f"- {fmt}: `{path}`")
            lines.append("")
        if result.notes:
            lines.extend(["### Comparison notes", "", *(f"- {note}" for note in result.notes), ""])

    out.write_text("\n".join(lines), encoding="utf-8")
    return out


@app.command("run")
def run_evaluation(
    audio: Path = typer.Argument(
        ...,
        help="Path to an audio file or directory of audio files.",
        exists=True,
        file_okay=True,
        dir_okay=True,
        readable=True,
    ),
    baseline: str = typer.Option(
        PARAKEET_MODEL_NAME,
        "--baseline",
        help="Baseline Parakeet model name.",
    ),
    candidate: str = typer.Option(
        "nvidia/parakeet-unified-en-0.6b",
        "--candidate",
        help="Candidate Parakeet model name to evaluate.",
    ),
    output_dir: Path = typer.Option(
        Path("data/evaluation_results"),
        "--output-dir",
        help="Directory for JSON/Markdown reports and per-format outputs.",
    ),
    chunk_len_sec: int = typer.Option(
        DEFAULT_CHUNK_LEN_SEC,
        "--chunk-len-sec",
        help="Chunk length in seconds.",
    ),
    batch_size: int = typer.Option(
        DEFAULT_BATCH_SIZE,
        "--batch-size",
        help="Batch size for model inference.",
    ),
    word_timestamps: bool = typer.Option(
        True,
        "--word-timestamps/--no-word-timestamps",
        help="Request word-level timestamps from the model.",
    ),
    formats: str = typer.Option(
        "txt,json,jsonl,csv,tsv,srt,vtt",
        "--formats",
        help="Comma-separated list of output formats to exercise.",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Enable verbose logging.",
    ),
) -> None:
    """Compare baseline and candidate ASR models on the provided audio.

    Writes a JSON report and a Markdown report to ``--output-dir``.

    Raises:
        typer.Exit: If an invalid output format is requested or no audio files
            are found.
    """
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=log_level)
    configure_environment(verbose)

    output_dir.mkdir(parents=True, exist_ok=True)

    requested_formats = [fmt.strip().lower() for fmt in formats.split(",") if fmt.strip()]
    invalid_formats = [fmt for fmt in requested_formats if fmt not in FORMATTERS]
    if invalid_formats:
        typer.echo(f"Unsupported formats: {invalid_formats}", err=True)
        raise typer.Exit(code=2)

    if audio.is_file():
        audio_files = [audio]
    else:
        audio_files = sorted(
            p for p in audio.iterdir() if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS
        )
        if not audio_files:
            typer.echo(f"No supported audio files found in {audio}", err=True)
            raise typer.Exit(code=2)

    run = EvaluationRun(baseline_model=baseline, candidate_model=candidate)

    for audio_path in audio_files:
        logger.info("evaluating %s", audio_path)
        comparison = _compare(
            audio_path=audio_path,
            baseline_name=baseline,
            candidate_name=candidate,
            output_dir=output_dir,
            chunk_len_sec=chunk_len_sec,
            batch_size=batch_size,
            word_timestamps=word_timestamps,
            formats=requested_formats,
        )
        run.files.append(comparison)

    if not run.files:
        run.notes.append("no files processed")

    json_path = _write_json(run, output_dir)
    md_path = _write_markdown(run, output_dir)
    logger.info("wrote JSON report: %s", json_path)
    logger.info("wrote Markdown report: %s", md_path)


def main() -> None:
    """Entrypoint for ``python -m scripts.evaluate_model``."""
    app()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.warning("interrupted by user")
        sys.exit(130)
