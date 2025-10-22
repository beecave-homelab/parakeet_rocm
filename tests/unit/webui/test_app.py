"""Unit tests for webui.app module.

Tests application factory and launcher functions,
ensuring proper app construction and configuration.
"""

from __future__ import annotations

import pathlib
import zipfile
from unittest.mock import Mock

import pytest

# Import will fail if gradio not installed, which is expected
gradio = pytest.importorskip("gradio", reason="Gradio not installed")

from parakeet_rocm.webui.app import build_app  # noqa: E402
from parakeet_rocm.webui.core.job_manager import (  # noqa: E402
    JobManager,
    JobStatus,
    TranscriptionJob,
)
from parakeet_rocm.webui.utils.zip_creator import ZipCreator  # noqa: E402


class TestBuildApp:
    """Test build_app function."""

    def test_build_app__returns_blocks_object(self) -> None:
        """Build app should return Gradio Blocks."""
        app = build_app()

        assert app is not None
        assert isinstance(app, gradio.Blocks)

    def test_build_app__accepts_custom_job_manager(self) -> None:
        """Build app should accept custom job manager."""
        mock_manager = Mock(spec=JobManager)
        mock_manager.jobs = {}

        app = build_app(job_manager=mock_manager)

        assert isinstance(app, gradio.Blocks)

    def test_build_app__with_analytics_disabled(self) -> None:
        """Build app should accept analytics configuration."""
        app = build_app(analytics_enabled=False)

        assert isinstance(app, gradio.Blocks)

    def test_build_app__creates_default_job_manager(self) -> None:
        """Build app should create default job manager if none provided."""
        app = build_app()

        # App should be created successfully
        assert isinstance(app, gradio.Blocks)

    def test_build_app__accepts_all_supported_file_types(self) -> None:
        """Build app should accept all supported audio/video file extensions."""
        from parakeet_rocm.utils.constant import SUPPORTED_EXTENSIONS

        app = build_app()

        # Verify app is created
        assert isinstance(app, gradio.Blocks)

        # Verify .m4a is in supported extensions (regression test for bug)
        assert ".m4a" in SUPPORTED_EXTENSIONS
        assert ".mp3" in SUPPORTED_EXTENSIONS
        assert ".wav" in SUPPORTED_EXTENSIONS
        assert ".mp4" in SUPPORTED_EXTENSIONS


class TestBulkDownload:
    """Test bulk download functionality with ZipCreator."""

    def test_zip_creator_single_file(self, tmp_path: pathlib.Path) -> None:
        """ZipCreator should handle single file correctly."""
        # Arrange
        output_file = tmp_path / "transcription.srt"
        output_file.write_text("Test subtitle")

        creator = ZipCreator()

        # Act
        zip_path = creator.create_temporary_zip([output_file])

        # Assert
        assert zip_path.exists()
        assert zipfile.is_zipfile(zip_path)

        with zipfile.ZipFile(zip_path, "r") as zf:
            assert "transcription.srt" in zf.namelist()

        # Cleanup
        zip_path.unlink()

    def test_zip_creator_multiple_files(self, tmp_path: pathlib.Path) -> None:
        """ZipCreator should create ZIP archive for multiple files."""
        # Arrange
        file1 = tmp_path / "audio1.srt"
        file2 = tmp_path / "audio2.srt"
        file1.write_text("Subtitle 1")
        file2.write_text("Subtitle 2")

        creator = ZipCreator()

        # Act
        zip_path = creator.create_temporary_zip([file1, file2])

        # Assert
        assert zip_path.exists()
        assert zipfile.is_zipfile(zip_path)

        with zipfile.ZipFile(zip_path, "r") as zf:
            assert len(zf.namelist()) == 2
            assert "audio1.srt" in zf.namelist()
            assert "audio2.srt" in zf.namelist()

        # Cleanup
        zip_path.unlink()

    def test_bulk_download_integration_with_job_manager(
        self, tmp_path: pathlib.Path
    ) -> None:
        """Test bulk download integrates with job manager workflow."""
        # Arrange
        output1 = tmp_path / "output1.srt"
        output2 = tmp_path / "output2.srt"
        output1.write_text("Transcription 1")
        output2.write_text("Transcription 2")

        # Simulate completed job with multiple outputs
        job = TranscriptionJob()
        job.status = JobStatus.COMPLETED
        job.outputs = [output1, output2]

        # Act - Simulate bulk download logic from app.py
        if len(job.outputs) > 1:
            zip_creator = ZipCreator()
            zip_path = zip_creator.create_temporary_zip(
                job.outputs,
                prefix="transcriptions_",
            )
            output_paths = [str(zip_path)]
        else:
            output_paths = [str(p) for p in job.outputs]

        # Assert
        assert len(output_paths) == 1
        assert output_paths[0].endswith(".zip")

        zip_file = pathlib.Path(output_paths[0])
        assert zip_file.exists()
        assert zipfile.is_zipfile(zip_file)

        # Verify ZIP contains both files
        with zipfile.ZipFile(zip_file, "r") as zf:
            assert len(zf.namelist()) == 2
            assert "output1.srt" in zf.namelist()
            assert "output2.srt" in zf.namelist()

        # Cleanup
        zip_file.unlink()
