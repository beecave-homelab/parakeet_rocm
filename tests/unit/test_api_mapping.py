"""Unit tests for API mapping helpers."""

from __future__ import annotations

from pathlib import Path

from parakeet_rocm.api.mapping import (
    convert_aligned_result_to_verbose,
    get_audio_duration,
    infer_language_for_model,
    map_model_name,
    map_response_format,
)
from parakeet_rocm.timestamps.models import AlignedResult, Segment, Word
from parakeet_rocm.utils.constant import PARAKEET_MODEL_NAME


def _build_aligned_result() -> AlignedResult:
    """Build a minimal aligned result fixture.

    Returns:
        AlignedResult containing one segment and two words.
    """
    words = [
        Word(word="hello", start=0.0, end=0.4),
        Word(word="world", start=0.5, end=1.0),
    ]
    segment = Segment(text="hello world", words=words, start=0.0, end=1.0)
    return AlignedResult(segments=[segment], word_segments=words)


def test_map_model_name_aliases() -> None:
    """Model aliases should map to supported internal model names."""
    assert map_model_name("whisper-1") == PARAKEET_MODEL_NAME
    assert map_model_name("nvidia/parakeet-tdt-0.6b-v3") == "nvidia/parakeet-tdt-0.6b-v3"
    assert map_model_name("invalid-model") is None


def test_map_response_format_supported_values() -> None:
    """Response format mappings should match API compatibility contract."""
    assert map_response_format("json") == "text_only"
    assert map_response_format("text") == "txt"
    assert map_response_format("srt") == "srt"
    assert map_response_format("vtt") == "vtt"
    assert map_response_format("verbose_json") == "json"


def test_infer_language_for_model_returns_en_for_v2() -> None:
    """English-only model variants should report English language."""
    assert infer_language_for_model("nvidia/parakeet-tdt-0.6b-v2") == "en"


def test_infer_language_for_model_returns_und_for_multilingual_or_unknown() -> None:
    """Multilingual/unknown variants should report undetermined language."""
    assert infer_language_for_model("nvidia/parakeet-tdt-0.6b-v3") == "und"
    assert infer_language_for_model("nvidia/custom-model") == "und"


def test_convert_aligned_result_verbose_with_both_granularities() -> None:
    """Verbose conversion should include both segments and words when requested."""
    aligned = _build_aligned_result()
    payload = convert_aligned_result_to_verbose(aligned, ["segment", "word"])

    assert payload["text"] == "hello world"
    assert payload["segments"] is not None
    assert payload["words"] is not None
    assert payload["segments"][0]["text"] == "hello world"
    assert payload["words"][0]["word"] == "hello"


def test_convert_aligned_result_verbose_segments_only() -> None:
    """Verbose conversion should omit words when only segment granularity is requested."""
    aligned = _build_aligned_result()
    payload = convert_aligned_result_to_verbose(aligned, ["segment"])

    assert payload["segments"] is not None
    assert payload["words"] is None
    assert payload["segments"][0]["words"] is None


def test_convert_aligned_result_verbose_normalizes_embedded_newlines() -> None:
    """Verbose text should normalize segment line breaks into spaces."""
    words = [Word(word="hello", start=0.0, end=0.4)]
    aligned = AlignedResult(
        segments=[
            Segment(text="hello\nworld", words=words, start=0.0, end=1.0),
            Segment(text="again", words=words, start=1.0, end=2.0),
        ],
        word_segments=words,
    )

    payload = convert_aligned_result_to_verbose(aligned, ["segment", "word"])

    assert payload["text"] == "hello world again"


def test_get_audio_duration_missing_file_returns_zero(tmp_path: Path) -> None:
    """Duration probe should return 0.0 for unreadable paths."""
    missing = tmp_path / "missing.wav"
    assert get_audio_duration(missing) == 0.0
