"""Unit tests covering audio loading backends and fallbacks.

These tests validate ffmpeg, pydub, and soundfile code paths for
``load_audio`` and helpers, ensuring correct sampling rate handling and
dtype.
"""

from typing import NoReturn

import numpy as np
import pytest

from parakeet_rocm.utils import audio_io

pytestmark = pytest.mark.integration


def test_load_with_ffmpeg(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify ffmpeg-based loader decodes PCM audio at the target rate.

    Asserts that decoded PCM bytes are converted to a NumPy ndarray and
    that the returned sample rate matches the requested value.
    """
    monkeypatch.setattr(audio_io.shutil, "which", lambda cmd: "/usr/bin/ffmpeg")

    class _Result:
        stdout = np.array([0, 32767], dtype=np.int16).tobytes()

    monkeypatch.setattr(audio_io.subprocess, "run", lambda cmd, capture_output, check: _Result())
    data, sr = audio_io._load_with_ffmpeg("dummy", 16000)
    assert sr == 16000 and isinstance(data, np.ndarray)


def test_load_with_pydub(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pydub path should return float32 numpy array and sample rate.

    Args:
        monkeypatch (pytest.MonkeyPatch): Fixture for patching modules.
    """

    class _Seg:
        frame_rate = 8000
        channels = 1

        def get_array_of_samples(self) -> list[int]:
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
        data: np.ndarray,
        orig_sr: int,
        target_sr: int,
        dtype: object,
    ) -> np.ndarray:
        called["resample"] = True
        return data

    monkeypatch.setattr(audio_io.librosa, "resample", _resample)
    data, sr = audio_io.load_audio("f", target_sr=16000)
    assert sr == 16000 and called["resample"]


def test_load_audio_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify that ffmpeg failures fall back to pydub with resampling.

    This test ensures ``load_audio`` returns data produced by the pydub
    fallback and that the resulting sample rate equals ``16000``.
    """
    monkeypatch.setattr(audio_io, "FORCE_FFMPEG", True)

    def _ffmpeg_fail(path: str, sr: int) -> NoReturn:
        raise RuntimeError("fail")

    monkeypatch.setattr(audio_io, "_load_with_ffmpeg", _ffmpeg_fail)
    monkeypatch.setattr(audio_io.sf, "read", lambda *a, **k: (_ffmpeg_fail("", 0)))

    def _pydub(path: str) -> tuple[np.ndarray, int]:
        return (np.array([[0.0, 0.0], [0.0, 0.0]], dtype=np.float32), 8000)

    monkeypatch.setattr(audio_io, "_load_with_pydub", _pydub)
    monkeypatch.setattr(audio_io.librosa, "resample", lambda d, orig_sr, target_sr, dtype: d)

    data, sr = audio_io.load_audio("f", target_sr=16000)
    assert data.shape == (2, 2) or data.shape == (2,) and sr == 16000
