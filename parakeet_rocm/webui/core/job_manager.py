"""Transcription job management and orchestration.

Handles the lifecycle of transcription jobs from submission through
completion, including progress tracking, error handling, and status
management.
"""

from __future__ import annotations

import enum
import logging
import pathlib
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from parakeet_rocm.benchmarks.collector import BenchmarkCollector, GpuUtilSampler
from parakeet_rocm.transcription import cli_transcribe
from parakeet_rocm.utils.constant import (
    BENCHMARK_OUTPUT_DIR,
    BENCHMARK_PERSISTENCE_ENABLED,
    GPU_SAMPLER_INTERVAL_SEC,
)
from parakeet_rocm.webui.validation.schemas import TranscriptionConfig

logger = logging.getLogger(__name__)


class JobStatus(str, enum.Enum):  # noqa: UP042
    """Status of a transcription job.

    Attributes:
        PENDING: Job created but not yet started.
        RUNNING: Job currently executing.
        COMPLETED: Job finished successfully.
        FAILED: Job failed with error.
        CANCELLED: Job cancelled by user.
    """

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TranscriptionJob:
    """Represents a transcription job.

    Tracks all information about a single transcription job including
    configuration, status, progress, and outputs.

    Attributes:
        job_id: Unique job identifier.
        files: Input audio/video files.
        config: Transcription configuration.
        status: Current job status.
        progress: Progress percentage (0-100).
        outputs: Generated output file paths.
        error: Error message if status is FAILED.
        created_at: Job creation timestamp.
        completed_at: Job completion timestamp.
        runtime_seconds: Actual transcription time (excludes overhead).
        total_wall_seconds: Total elapsed time (includes overhead).
        gpu_stats: GPU utilization statistics from sampler.
        format_quality: Subtitle quality metrics.
        benchmark_path: Path to saved benchmark JSON file.

    Examples:
        >>> job = TranscriptionJob()
        >>> job.status
        <JobStatus.PENDING: 'pending'>

        >>> job.job_id
        'a1b2c3d4-...'
    """

    job_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    files: list[pathlib.Path] = field(default_factory=list)
    config: TranscriptionConfig | None = None
    status: JobStatus = JobStatus.PENDING
    progress: float = 0.0
    outputs: list[pathlib.Path] = field(default_factory=list)
    error: str | None = None
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: datetime | None = None
    runtime_seconds: float | None = None
    total_wall_seconds: float | None = None
    gpu_stats: dict[str, Any] | None = None
    format_quality: dict[str, Any] | None = None
    benchmark_path: pathlib.Path | None = None

    @property
    def metrics(self) -> dict[str, Any] | None:
        """Aggregate metrics dictionary for compatibility with session helpers.

        Returns:
            Dictionary containing all metric fields, or None if no metrics collected.
        """
        if self.runtime_seconds is None:
            return None

        return {
            "runtime_seconds": self.runtime_seconds,
            "total_wall_seconds": self.total_wall_seconds,
            "gpu_stats": self.gpu_stats or {},
            "format_quality": self.format_quality or {},
            "benchmark_path": str(self.benchmark_path) if self.benchmark_path else None,
        }


class JobManager:
    """Manages transcription job lifecycle.

    Coordinates job submission, execution, and tracking. Maintains
    a registry of all active jobs and provides status queries.

    Attributes:
        transcribe_fn: Transcription function (injected for testability).
        jobs: Active jobs keyed by job_id.
        benchmark_enabled: Whether benchmark collection is enabled.
        _current_job_id: ID of currently running job.
        _last_completed_job_id: ID of last successfully completed job.

    Examples:
        >>> manager = JobManager()
        >>> job = manager.submit_job(files, config)
        >>> result = manager.run_job(job.job_id)
        >>> result.status
        <JobStatus.COMPLETED: 'completed'>
    """

    def __init__(
        self,
        transcribe_fn: Callable = cli_transcribe,
        enable_benchmarks: bool | None = None,
    ) -> None:
        """Initialize job manager.

        Args:
            transcribe_fn: Transcription function to use (default: cli_transcribe).
                Injected for testability with mocked functions.
            enable_benchmarks: Enable benchmark collection. If None, uses
                BENCHMARK_PERSISTENCE_ENABLED from environment.

        Examples:
            >>> manager = JobManager()
            >>> # Or with custom function for testing
            >>> manager = JobManager(transcribe_fn=mock_transcribe)
            >>> # Or with benchmarks enabled
            >>> manager = JobManager(enable_benchmarks=True)
        """
        self.transcribe_fn = transcribe_fn
        self.jobs: dict[str, TranscriptionJob] = {}
        self.benchmark_enabled = (
            enable_benchmarks
            if enable_benchmarks is not None
            else BENCHMARK_PERSISTENCE_ENABLED
        )
        self._current_job_id: str | None = None
        self._last_completed_job_id: str | None = None

        status = "enabled" if self.benchmark_enabled else "disabled"
        logger.debug(f"JobManager initialized (benchmarks={status})")

    def submit_job(
        self,
        files: list[pathlib.Path],
        config: TranscriptionConfig,
    ) -> TranscriptionJob:
        """Submit a new transcription job.

        Creates a new job and registers it with the manager.
        The job starts in PENDING status.

        Args:
            files: Input files to transcribe.
            config: Validated transcription configuration.

        Returns:
            Created TranscriptionJob object.

        Examples:
            >>> manager = JobManager()
            >>> files = [pathlib.Path("audio.wav")]
            >>> config = TranscriptionConfig()
            >>> job = manager.submit_job(files, config)
            >>> job.status
            <JobStatus.PENDING: 'pending'>
        """
        job = TranscriptionJob(files=files, config=config)
        self.jobs[job.job_id] = job
        return job

    def run_job(
        self, job_id: str, progress_callback: callable | None = None
    ) -> TranscriptionJob:
        """Execute a transcription job.

        Runs the transcription function with the job's configuration.
        Updates job status to RUNNING during execution, then COMPLETED
        or FAILED depending on the result. Collects benchmark metrics
        if enabled.

        Args:
            job_id: ID of job to run.
            progress_callback: Optional callback for progress updates.
                Called with (current, total) after each batch.

        Returns:
            Updated TranscriptionJob object.

        Examples:
            >>> manager = JobManager()
            >>> job = manager.submit_job(files, config)
            >>> result = manager.run_job(job.job_id)
            >>> result.status
            <JobStatus.COMPLETED: 'completed'>
        """
        job = self.jobs[job_id]
        job.status = JobStatus.RUNNING
        self._current_job_id = job_id

        # Initialize benchmark collector if enabled
        collector: BenchmarkCollector | None = None
        sampler: GpuUtilSampler | None = None

        if self.benchmark_enabled:
            collector = BenchmarkCollector(
                output_dir=BENCHMARK_OUTPUT_DIR,
                slug=f"job_{job_id[:8]}",
            )
            sampler = GpuUtilSampler(interval_sec=GPU_SAMPLER_INTERVAL_SEC)
            sampler.start()
            logger.debug(f"Started GPU sampler for job {job_id}")

        wall_start = time.time()
        runtime_start = time.time()

        try:
            # Execute transcription with job configuration
            # Enable progress tracking when callback is provided
            outputs = self.transcribe_fn(
                audio_files=job.files,
                model_name=job.config.model_name,
                output_dir=job.config.output_dir,
                output_format=job.config.output_format,
                batch_size=job.config.batch_size,
                chunk_len_sec=job.config.chunk_len_sec,
                overlap_duration=job.config.overlap_duration,
                stream=job.config.stream,
                stream_chunk_sec=job.config.stream_chunk_sec,
                word_timestamps=job.config.word_timestamps,
                merge_strategy=job.config.merge_strategy,
                highlight_words=job.config.highlight_words,
                stabilize=job.config.stabilize,
                vad=job.config.vad,
                demucs=job.config.demucs,
                vad_threshold=job.config.vad_threshold,
                overwrite=job.config.overwrite,
                verbose=False,
                quiet=True,
                no_progress=progress_callback is None,  # Enable when callback provided
                fp16=job.config.fp16,
                fp32=job.config.fp32,
                progress_callback=progress_callback,
                collector=collector,  # Pass collector for metrics gathering
            )

            # Calculate timing metrics
            runtime_end = time.time()
            wall_end = time.time()

            # Update job with results
            job.outputs = outputs
            job.status = JobStatus.COMPLETED
            job.progress = 100.0
            job.completed_at = datetime.now()
            job.runtime_seconds = runtime_end - runtime_start
            job.total_wall_seconds = wall_end - wall_start

            # Collect benchmark metrics if enabled
            if self.benchmark_enabled and collector and sampler:
                sampler.stop()
                job.gpu_stats = sampler.get_stats()

                # Update collector with metrics
                # (format_quality populated by cli_transcribe)
                collector.metrics["runtime_seconds"] = job.runtime_seconds
                collector.metrics["total_wall_seconds"] = job.total_wall_seconds
                collector.metrics["gpu_stats"] = job.gpu_stats or {}
                # format_quality already populated by cli_transcribe via collector
                job.format_quality = collector.metrics.get("format_quality", {})

                # Write benchmark JSON
                job.benchmark_path = collector.write_json()
                logger.info(f"Benchmark saved: {job.benchmark_path}")
                logger.debug(
                    f"Job metrics populated: runtime={job.runtime_seconds:.2f}s, "
                    f"wall={job.total_wall_seconds:.2f}s, "
                    f"gpu_stats={'present' if job.gpu_stats else 'empty'}, "
                    f"format_quality={'present' if job.format_quality else 'empty'}"
                )

            self._last_completed_job_id = job_id
            logger.debug(f"Last completed job ID set to: {job_id[:8]}")

        except Exception as e:
            # Stop sampler on error
            if sampler:
                sampler.stop()
                logger.debug("Stopped GPU sampler after error")

            # Handle failure
            job.status = JobStatus.FAILED
            job.error = str(e)
            job.completed_at = datetime.now()

        finally:
            self._current_job_id = None

        return job

    def get_job(self, job_id: str) -> TranscriptionJob:
        """Retrieve job by ID.

        Args:
            job_id: Job identifier.

        Returns:
            TranscriptionJob object.

        Examples:
            >>> manager = JobManager()
            >>> job = manager.submit_job(files, config)
            >>> retrieved = manager.get_job(job.job_id)
            >>> retrieved == job
            True
        """
        return self.jobs[job_id]

    def list_jobs(self) -> list[TranscriptionJob]:
        """List all jobs.

        Returns jobs in reverse chronological order (newest first).

        Returns:
            List of all TranscriptionJob objects, newest first.

        Examples:
            >>> manager = JobManager()
            >>> job1 = manager.submit_job(files1, config)
            >>> job2 = manager.submit_job(files2, config)
            >>> jobs = manager.list_jobs()
            >>> jobs[0] == job2  # Newest first
            True
        """
        return sorted(
            self.jobs.values(),
            key=lambda j: j.created_at,
            reverse=True,
        )

    def get_current_job(self) -> TranscriptionJob | None:
        """Get the currently running job.

        Returns:
            TranscriptionJob if a job is running, otherwise None.

        Examples:
            >>> manager = JobManager()
            >>> job = manager.submit_job(files, config)
            >>> # In another thread: manager.run_job(job.job_id)
            >>> current = manager.get_current_job()
            >>> current.status
            <JobStatus.RUNNING: 'running'>
        """
        if self._current_job_id:
            return self.jobs.get(self._current_job_id)
        return None

    def get_last_completed_job(self) -> TranscriptionJob | None:
        """Get the most recently completed job.

        Returns:
            TranscriptionJob of last successful completion, or None.

        Examples:
            >>> manager = JobManager()
            >>> job = manager.submit_job(files, config)
            >>> manager.run_job(job.job_id)
            >>> last = manager.get_last_completed_job()
            >>> last.status
            <JobStatus.COMPLETED: 'completed'>
        """
        if self._last_completed_job_id:
            return self.jobs.get(self._last_completed_job_id)
        return None
