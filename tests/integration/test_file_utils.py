"""Tests for file utilities."""

import os
import pathlib
import tempfile
from collections.abc import Generator

import pytest

from parakeet_rocm.utils.file_utils import ensure_dir_writable, get_unique_filename

pytestmark = pytest.mark.integration


@pytest.fixture
def temp_dir() -> Generator[pathlib.Path, None, None]:
    """Create a temporary directory for a test and yield its path.

    Yields:
        pathlib.Path: Path to the temporary directory. The directory is
            removed automatically when the fixture context exits.
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield pathlib.Path(tmp_dir)


def test_get_unique_filename_no_conflict(temp_dir: pathlib.Path) -> None:
    """Test that original filename is returned when no conflict exists."""
    test_path = temp_dir / "test.txt"
    result = get_unique_filename(test_path)
    assert result == test_path
    assert not result.exists()


def test_get_unique_filename_with_overwrite(temp_dir: pathlib.Path) -> None:
    """Test that original filename is returned when overwrite=True."""
    test_path = temp_dir / "test.txt"
    test_path.write_text("existing content")

    result = get_unique_filename(test_path, overwrite=True)
    assert result == test_path
    assert result.exists()


def test_get_unique_filename_with_conflict(temp_dir: pathlib.Path) -> None:
    """Test that numbered suffix is appended when file exists."""
    test_path = temp_dir / "test.txt"
    test_path.write_text("existing content")

    result = get_unique_filename(test_path, separator="-")
    expected = temp_dir / "test-1.txt"
    assert result == expected
    assert not result.exists()


def test_get_unique_filename_multiple_conflicts(temp_dir: pathlib.Path) -> None:
    """Test that correct number is chosen for multiple conflicts."""
    test_path = temp_dir / "test.txt"
    test_path.write_text("existing content")

    # Create existing numbered files
    (temp_dir / "test-1.txt").write_text("content 1")
    (temp_dir / "test-2.txt").write_text("content 2")

    result = get_unique_filename(test_path, separator="-")
    expected = temp_dir / "test-3.txt"
    assert result == expected
    assert not result.exists()


def test_get_unique_filename_custom_separator(temp_dir: pathlib.Path) -> None:
    """Test that custom separator works correctly."""
    test_path = temp_dir / "test.txt"
    test_path.write_text("existing content")

    result = get_unique_filename(test_path, separator="_")
    expected = temp_dir / "test_1.txt"
    assert result == expected


def test_get_unique_filename_with_extension(temp_dir: pathlib.Path) -> None:
    """Test that file extensions are preserved correctly."""
    test_path = temp_dir / "document.srt"
    test_path.write_text("existing content")

    result = get_unique_filename(test_path, separator="-")
    expected = temp_dir / "document-1.srt"
    assert result == expected


class TestEnsureDirWritable:
    """Tests for ensure_dir_writable."""

    def test_writable_existing_dir(self, temp_dir: pathlib.Path) -> None:
        """Test that an existing writable directory passes validation."""
        result = ensure_dir_writable(temp_dir)
        assert result == temp_dir
        assert result.is_dir()

    def test_creates_missing_dir(self, temp_dir: pathlib.Path) -> None:
        """Test that a non-existent directory is created and validated."""
        target = temp_dir / "nested" / "subdir"
        assert not target.exists()
        result = ensure_dir_writable(target)
        assert result.is_dir()

    @pytest.mark.skipif(os.geteuid() == 0, reason="root bypasses file permissions")
    def test_readonly_dir_raises_os_error(self, temp_dir: pathlib.Path) -> None:
        """Test that a read-only directory raises OSError with helpful message."""
        readonly_dir = temp_dir / "readonly"
        readonly_dir.mkdir()
        readonly_dir.chmod(0o444)
        try:
            with pytest.raises(OSError, match="not writable"):
                ensure_dir_writable(readonly_dir)
        finally:
            readonly_dir.chmod(0o755)

    @pytest.mark.skipif(os.geteuid() == 0, reason="root bypasses file permissions")
    def test_custom_label_in_error(self, temp_dir: pathlib.Path) -> None:
        """Test that the custom label appears in the error message."""
        readonly_dir = temp_dir / "ro"
        readonly_dir.mkdir()
        readonly_dir.chmod(0o444)
        try:
            with pytest.raises(OSError, match="Benchmark directory"):
                ensure_dir_writable(readonly_dir, label="Benchmark directory")
        finally:
            readonly_dir.chmod(0o755)

    def test_probe_file_cleaned_up(self, temp_dir: pathlib.Path) -> None:
        """Test that the write probe file is deleted after validation."""
        ensure_dir_writable(temp_dir)
        probe_files = list(temp_dir.glob(".write_probe_*"))
        # NamedTemporaryFile(delete=True) handles cleanup automatically
        assert probe_files == []

    def test_string_path_input(self, temp_dir: pathlib.Path) -> None:
        """Test that a string path is accepted and converted."""
        result = ensure_dir_writable(str(temp_dir))
        assert isinstance(result, pathlib.Path)
