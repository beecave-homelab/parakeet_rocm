import sys
import types
from pathlib import Path

import pytest

from parakeet_rocm.integrations.stable_ts import refine_word_timestamps
from parakeet_rocm.timestamps.models import Word

pytestmark = pytest.mark.integration


def test_refine_word_timestamps_empty_list() -> None:
    """Returns empty list when input words list is empty."""
    result = refine_word_timestamps([], Path("dummy.wav"))
    assert result == []


def test_refine_word_timestamps_missing_module(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Tests behavior when stable_whisper is not installed."""

    def mock_import_module(name: str) -> object:
        if name == "stable_whisper":
            raise ModuleNotFoundError("No module named 'stable_whisper'")
        return __import__(name)

    monkeypatch.setattr("importlib.import_module", mock_import_module)

    with pytest.raises(RuntimeError, match="stable_whisper is required"):
        refine_word_timestamps(
            [Word(word="test", start=0.0, end=1.0, score=None)], Path("dummy.wav")
        )


def test_refine_word_timestamps_success(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Successful refinement using transcribe_any."""
    dummy = types.SimpleNamespace()
    dummy.__version__ = "2.7.0"

    def _transcribe_any(
        fn: object,
        audio: object,
        **kwargs: object,
    ) -> dict[str, object]:
        return {
            "segments": [
                {
                    "words": [
                        {"word": "hello", "start": 0.0, "end": 0.5},
                        {"word": "world", "start": 0.5, "end": 1.0},
                    ]
                }
            ]
        }

    dummy.transcribe_any = _transcribe_any
    monkeypatch.setitem(sys.modules, "stable_whisper", dummy)

    audio = tmp_path / "a.wav"
    audio.write_bytes(b"fake")

    words = [Word(word="test", start=0.0, end=1.0, score=None)]
    refined = refine_word_timestamps(words, audio)
    assert [w.word for w in refined] == ["hello", "world"]
    assert refined[0].start == 0.0
    assert refined[-1].end == 1.0


@pytest.mark.parametrize(
    "demucs,vad,vad_threshold",
    [
        (True, False, 0.35),  # Demucs only
        (False, True, 0.35),  # VAD only
        (True, True, 0.20),  # Both enabled
    ],
)
def test_refine_word_timestamps_options(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    demucs: bool,
    vad: bool,
    vad_threshold: float,
) -> None:
    """Tests Demucs and VAD options are passed correctly."""
    captured_options = {}
    dummy = types.SimpleNamespace()

    def _transcribe_any(
        fn: object,
        audio: object,
        **kwargs: object,
    ) -> dict[str, object]:
        captured_options.update(kwargs)
        return {
            "segments": [
                {
                    "words": [
                        {"word": "hello", "start": 0.0, "end": 0.5},
                    ]
                }
            ]
        }

    dummy.transcribe_any = _transcribe_any
    monkeypatch.setitem(sys.modules, "stable_whisper", dummy)

    audio = tmp_path / "a.wav"
    audio.write_bytes(b"fake")

    words = [Word(word="test", start=0.0, end=1.0, score=None)]
    refine_word_timestamps(words, audio, demucs=demucs, vad=vad, vad_threshold=vad_threshold)

    # Check that options were set correctly
    if demucs:
        assert captured_options["demucs"] is True
        assert captured_options["denoiser"] == "demucs"
    if vad:
        assert captured_options["vad"] is True
        assert captured_options["vad_threshold"] == vad_threshold
    if demucs or vad:
        assert captured_options["suppress_silence"] is True
        assert captured_options["suppress_word_ts"] is True
        assert captured_options["q_levels"] == 10
        assert captured_options["k_size"] == 3
        assert captured_options["min_word_dur"] == 0.03
        assert captured_options["force_order"] is True


def test_refine_word_timestamps_verbose_logging(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Tests verbose logging output and empty segments fallback."""
    dummy = types.SimpleNamespace()
    dummy.__version__ = "2.7.0"
    call_count = 0

    def _transcribe_any(
        fn: object,
        audio: object,
        **kwargs: object,
    ) -> dict[str, object]:
        nonlocal call_count
        call_count += 1
        # Return empty segments first to trigger fallback
        if call_count == 1:
            return {"segments": []}
        return {
            "segments": [
                {
                    "words": [
                        {"word": "fallback", "start": 0.0, "end": 0.5},
                    ]
                }
            ]
        }

    def _postprocess(
        data: object,
        audio: object,
        **kwargs: object,
    ) -> dict[str, object]:
        return {
            "segments": [
                {
                    "words": [
                        {"word": "postprocessed", "start": 0.0, "end": 0.5},
                    ]
                }
            ]
        }

    dummy.transcribe_any = _transcribe_any
    dummy.postprocess_word_timestamps = _postprocess
    monkeypatch.setitem(sys.modules, "stable_whisper", dummy)

    # Mock torch and torchaudio for version logging
    torch_mock = types.SimpleNamespace(__version__="1.9.0")
    torchaudio_mock = types.SimpleNamespace(__version__="0.9.0")
    torchaudio_mock.get_audio_backend = lambda: "soundfile"
    torchaudio_mock.info = lambda path: types.SimpleNamespace(sample_rate=16000, num_channels=1)

    # Mock silero_vad
    silero_mock = types.SimpleNamespace()

    monkeypatch.setitem(sys.modules, "torch", torch_mock)
    monkeypatch.setitem(sys.modules, "torchaudio", torchaudio_mock)
    monkeypatch.setitem(sys.modules, "silero_vad", silero_mock)

    audio = tmp_path / "a.wav"
    audio.write_bytes(b"fake")

    words = [Word(word="test", start=0.0, end=1.0, score=None)]
    refined = refine_word_timestamps(words, audio, verbose=True, vad=True)

    # Check that verbose output was captured
    captured = capsys.readouterr()
    assert "[stable-ts]" in captured.out
    assert "stable_whisper version: 2.7.0" in captured.out
    assert "torch version: 1.9.0" in captured.out
    assert "torchaudio version: 0.9.0" in captured.out
    assert "silero_vad import: OK" in captured.out
    assert "options: demucs=False, vad=True" in captured.out

    # Should get the postprocessed result due to empty segments fallback
    assert refined[0].word == "postprocessed"
