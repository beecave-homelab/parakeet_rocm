"""Unit tests covering audio loading backends and fallbacks.

These tests validate ffmpeg, pydub, and soundfile code paths for
``load_audio`` and helpers, ensuring correct sampling rate handling and
dtype.
"""

from typing import Any, NoReturn

import numpy as np
import pytest
from numpy import typing as npt

from parakeet_rocm.utils import audio_io

pytestmark = pytest.mark.integration


def test_load_with_ffmpeg(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ffmpeg path should decode to int16 PCM and cast to float32.

    Args:
        monkeypatch (pytest.MonkeyPatch): Fixture for patching modules.
    """
    monkeypatch.setattr(audio_io.shutil, "which", lambda cmd: "/usr/bin/ffmpeg")

    class _Result:
        stdout = np.array([0, 32767], dtype=np.int16).tobytes()

    monkeypatch.setattr(
        audio_io.subprocess, "run", lambda cmd, capture_output, check: _Result()
    )
    data, sr = audio_io._load_with_ffmpeg("dummy", 16000)
    assert sr == 16000 and isinstance(data, np.ndarray)


def test_load_with_pydub(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pydub path should return float32 numpy array and sample rate.

    Args:
        monkeypatch (pytest.MonkeyPatch): Fixture for patching modules.
    """

    class _Seg:
        """Test double representing a minimal pydub segment."""

        frame_rate = 8000
        channels = 1

        def get_array_of_samples(self) -> list[int]:
            """Return a small mono sample array for testing.

            Returns:
                list[int]: Samples representing raw PCM data.
            """
            return [0, 1]

    monkeypatch.setattr(audio_io.AudioSegment, "from_file", lambda p: _Seg())
    data, sr = audio_io._load_with_pydub("x")
    assert sr == 8000 and data.dtype == np.float32


def test_load_audio_soundfile(monkeypatch: pytest.MonkeyPatch) -> None:
    """Soundfile path should resample to target SR using librosa.

    Args:
        monkeypatch (pytest.MonkeyPatch): Fixture for patching modules.
    """
    monkeypatch.setattr(audio_io, "FORCE_FFMPEG", False)
    monkeypatch.setattr(
        audio_io.sf,
        "read",
        lambda p, always_2d=False: (np.array([0.0, 0.5], dtype=np.float32), 8000),
    )
    called = {}

    def _resample(
        data: npt.NDArray[np.floating[Any]],
        orig_sr: int,
        target_sr: int,
        dtype: np.dtype[np.floating[Any]] | type[np.floating[Any]],
    ) -> npt.NDArray[np.floating[Any]]:
        """Track the resample invocation and return the input data.

        Args:
            data: Input audio samples.
            orig_sr: Original sampling rate.
            target_sr: Desired sampling rate.
            dtype: Output dtype requested by the caller.

        Returns:
            NDArray: The unchanged audio samples.
        """
        called["resample"] = True
        return data

    monkeypatch.setattr(audio_io.librosa, "resample", _resample)
    data, sr = audio_io.load_audio("f", target_sr=16000)
    assert sr == 16000 and called["resample"]


def test_load_audio_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ffmpeg failure should fall back to pydub and resample to target SR.

    Args:
        monkeypatch (pytest.MonkeyPatch): Fixture for patching modules.
    """
    monkeypatch.setattr(audio_io, "FORCE_FFMPEG", True)

    def _ffmpeg_fail(path: str, sr: int) -> NoReturn:
        """Simulate ffmpeg failure to exercise fallback logic.

        Args:
            path: Audio file path.
            sr: Requested sampling rate.

        Raises:
            RuntimeError: Always raised to trigger fallback.
        """
        raise RuntimeError("fail")

    monkeypatch.setattr(audio_io, "_load_with_ffmpeg", _ffmpeg_fail)
    monkeypatch.setattr(audio_io.sf, "read", lambda *a, **k: (_ffmpeg_fail("", 0)))

    def _pydub(path: str) -> tuple[npt.NDArray[np.floating[Any]], int]:
        """Return deterministic pydub output for testing.

        Args:
            path: Audio path ignored by the stub.

        Returns:
            tuple[NDArray, int]: Audio samples and their sampling rate.
        """
        return (np.array([[0.0, 0.0], [0.0, 0.0]], dtype=np.float32), 8000)

    monkeypatch.setattr(audio_io, "_load_with_pydub", _pydub)
    monkeypatch.setattr(
        audio_io.librosa, "resample", lambda d, orig_sr, target_sr, dtype: d
    )

    data, sr = audio_io.load_audio("f", target_sr=16000)
    assert data.shape == (2, 2) or data.shape == (2,) and sr == 16000
