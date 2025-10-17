"""Unit tests for core.job_manager module.

Tests job lifecycle management including submission, execution,
status tracking, and error handling with mocked transcription.
"""

from __future__ import annotations

import pathlib
from datetime import datetime
from unittest.mock import Mock

import pytest

from parakeet_rocm.webui.core.job_manager import (
    JobManager,
    JobStatus,
    TranscriptionJob,
)
from parakeet_rocm.webui.validation.schemas import TranscriptionConfig


class TestJobStatus:
    """Test JobStatus enum."""

    def test_all_statuses_defined__has_expected_values(self) -> None:
        """JobStatus should have all expected statuses."""
        assert JobStatus.PENDING == "pending"
        assert JobStatus.RUNNING == "running"
        assert JobStatus.COMPLETED == "completed"
        assert JobStatus.FAILED == "failed"
        assert JobStatus.CANCELLED == "cancelled"


class TestTranscriptionJob:
    """Test TranscriptionJob dataclass."""

    def test_default_job__starts_pending(self) -> None:
        """New job should start in PENDING status."""
        job = TranscriptionJob()

        assert job.status == JobStatus.PENDING
        assert job.progress == 0.0

    def test_unique_job_ids__generates_different_ids(self) -> None:
        """Each job should have a unique ID."""
        job1 = TranscriptionJob()
        job2 = TranscriptionJob()

        assert job1.job_id != job2.job_id
        assert len(job1.job_id) > 0

    def test_initial_files__empty_list(self) -> None:
        """Initial job should have empty file list."""
        job = TranscriptionJob()

        assert job.files == []

    def test_initial_outputs__empty_list(self) -> None:
        """Initial job should have empty output list."""
        job = TranscriptionJob()

        assert job.outputs == []

    def test_initial_error__none(self) -> None:
        """Initial job should have no error."""
        job = TranscriptionJob()

        assert job.error is None

    def test_created_at__set_automatically(self) -> None:
        """Job should have creation timestamp."""
        before = datetime.now()
        job = TranscriptionJob()
        after = datetime.now()

        assert before <= job.created_at <= after

    def test_completed_at__initially_none(self) -> None:
        """Completed timestamp should initially be None."""
        job = TranscriptionJob()

        assert job.completed_at is None


class TestJobManager:
    """Test JobManager class with mocked transcription."""

    def test_submit_job__creates_new_job(self, tmp_path: pathlib.Path) -> None:
        """Submitting job should create new TranscriptionJob."""
        manager = JobManager()
        files = [tmp_path / "audio.wav"]
        config = TranscriptionConfig()

        job = manager.submit_job(files, config)

        assert isinstance(job, TranscriptionJob)
        assert job.status == JobStatus.PENDING
        assert job.files == files
        assert job.config == config

    def test_submit_job__adds_to_manager(self, tmp_path: pathlib.Path) -> None:
        """Submitted job should be tracked by manager."""
        manager = JobManager()
        files = [tmp_path / "audio.wav"]
        config = TranscriptionConfig()

        job = manager.submit_job(files, config)

        assert job.job_id in manager.jobs
        assert manager.jobs[job.job_id] == job

    def test_get_job__returns_correct_job(self, tmp_path: pathlib.Path) -> None:
        """Getting job by ID should return correct job."""
        manager = JobManager()
        files = [tmp_path / "audio.wav"]
        config = TranscriptionConfig()
        job = manager.submit_job(files, config)

        retrieved = manager.get_job(job.job_id)

        assert retrieved == job
        assert retrieved.job_id == job.job_id

    def test_get_nonexistent_job__raises_keyerror(self) -> None:
        """Getting non-existent job should raise KeyError."""
        manager = JobManager()

        with pytest.raises(KeyError):
            manager.get_job("nonexistent-id")

    def test_run_job_success__completes_job(self, tmp_path: pathlib.Path) -> None:
        """Running job successfully should complete it."""
        # Mock transcription function
        mock_transcribe = Mock(
            return_value=[tmp_path / "output.srt", tmp_path / "output2.srt"]
        )
        manager = JobManager(transcribe_fn=mock_transcribe)

        files = [tmp_path / "audio.wav"]
        config = TranscriptionConfig()
        job = manager.submit_job(files, config)

        result = manager.run_job(job.job_id)

        assert result.status == JobStatus.COMPLETED
        assert result.progress == 100.0
        assert len(result.outputs) == 2
        assert result.error is None
        assert result.completed_at is not None

    def test_run_job_success__calls_transcribe_fn(self, tmp_path: pathlib.Path) -> None:
        """Running job should call transcribe function with correct args."""
        mock_transcribe = Mock(return_value=[tmp_path / "output.srt"])
        manager = JobManager(transcribe_fn=mock_transcribe)

        files = [tmp_path / "audio.wav"]
        config = TranscriptionConfig(
            model_name="test-model",
            batch_size=16,
            word_timestamps=True,
        )
        job = manager.submit_job(files, config)

        manager.run_job(job.job_id)

        # Verify transcribe function was called with correct parameters
        mock_transcribe.assert_called_once()
        call_kwargs = mock_transcribe.call_args.kwargs
        assert call_kwargs["audio_files"] == files
        assert call_kwargs["model_name"] == "test-model"
        assert call_kwargs["batch_size"] == 16
        assert call_kwargs["word_timestamps"] is True

    def test_run_job_failure__marks_as_failed(self, tmp_path: pathlib.Path) -> None:
        """Job failure should mark job as FAILED with error."""
        # Mock transcription function that raises exception
        mock_transcribe = Mock(side_effect=RuntimeError("Transcription failed"))
        manager = JobManager(transcribe_fn=mock_transcribe)

        files = [tmp_path / "audio.wav"]
        config = TranscriptionConfig()
        job = manager.submit_job(files, config)

        result = manager.run_job(job.job_id)

        assert result.status == JobStatus.FAILED
        assert "Transcription failed" in result.error
        assert result.completed_at is not None

    def test_run_job__sets_running_status(self, tmp_path: pathlib.Path) -> None:
        """Job should be marked RUNNING during execution."""

        # Mock transcription that allows us to check state
        def transcribe_fn(**kwargs) -> list[pathlib.Path]:  # type: ignore[misc]
            # At this point, job should be RUNNING
            job = manager.get_job(job_id)
            assert job.status == JobStatus.RUNNING
            return [tmp_path / "output.srt"]

        manager = JobManager(transcribe_fn=transcribe_fn)
        files = [tmp_path / "audio.wav"]
        config = TranscriptionConfig()
        job = manager.submit_job(files, config)
        job_id = job.job_id

        manager.run_job(job_id)

    def test_list_jobs__returns_all_jobs(self, tmp_path: pathlib.Path) -> None:
        """Listing jobs should return all jobs."""
        manager = JobManager()
        config = TranscriptionConfig()

        job1 = manager.submit_job([tmp_path / "a1.wav"], config)
        job2 = manager.submit_job([tmp_path / "a2.wav"], config)
        job3 = manager.submit_job([tmp_path / "a3.wav"], config)

        jobs = manager.list_jobs()

        assert len(jobs) == 3
        # Jobs should be in reverse chronological order (newest first)
        assert jobs[0] == job3
        assert jobs[1] == job2
        assert jobs[2] == job1

    def test_list_jobs_empty__returns_empty_list(self) -> None:
        """Listing jobs when empty should return empty list."""
        manager = JobManager()

        jobs = manager.list_jobs()

        assert jobs == []

    def test_multiple_jobs__tracked_independently(self, tmp_path: pathlib.Path) -> None:
        """Multiple jobs should be tracked independently."""
        mock_transcribe = Mock(return_value=[tmp_path / "output.srt"])
        manager = JobManager(transcribe_fn=mock_transcribe)
        config = TranscriptionConfig()

        job1 = manager.submit_job([tmp_path / "a1.wav"], config)
        job2 = manager.submit_job([tmp_path / "a2.wav"], config)

        # Run only job1
        manager.run_job(job1.job_id)

        # Verify job1 completed, job2 still pending
        assert manager.get_job(job1.job_id).status == JobStatus.COMPLETED
        assert manager.get_job(job2.job_id).status == JobStatus.PENDING
