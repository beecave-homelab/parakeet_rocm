"""Transcription job management and orchestration.

Handles the lifecycle of transcription jobs from submission through
completion, including progress tracking, error handling, and status
management.
"""

from __future__ import annotations

import enum
import pathlib
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime

from parakeet_rocm.transcription import cli_transcribe
from parakeet_rocm.webui.validation.schemas import TranscriptionConfig


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


class JobManager:
    """Manages transcription job lifecycle.

    Coordinates job submission, execution, and tracking. Maintains
    a registry of all active jobs and provides status queries.

    Attributes:
        transcribe_fn: Transcription function (injected for testability).
        jobs: Active jobs keyed by job_id.

    Examples:
        >>> manager = JobManager()
        >>> job = manager.submit_job(files, config)
        >>> result = manager.run_job(job.job_id)
        >>> result.status
        <JobStatus.COMPLETED: 'completed'>
    """

    def __init__(self, transcribe_fn: Callable = cli_transcribe) -> None:
        """Initialize job manager.

        Args:
            transcribe_fn: Transcription function to use (default: cli_transcribe).
                Injected for testability with mocked functions.

        Examples:
            >>> manager = JobManager()
            >>> # Or with custom function for testing
            >>> manager = JobManager(transcribe_fn=mock_transcribe)
        """
        self.transcribe_fn = transcribe_fn
        self.jobs: dict[str, TranscriptionJob] = {}

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
        or FAILED depending on the result.

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
                word_timestamps=job.config.word_timestamps,
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
            )

            # Update job with results
            job.outputs = outputs
            job.status = JobStatus.COMPLETED
            job.progress = 100.0
            job.completed_at = datetime.now()

        except Exception as e:
            # Handle failure
            job.status = JobStatus.FAILED
            job.error = str(e)
            job.completed_at = datetime.now()

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
