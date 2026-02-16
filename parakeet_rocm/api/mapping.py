"""Mapping utilities between OpenAI API parameters and Parakeet internals."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import soundfile as sf

from parakeet_rocm.timestamps.models import AlignedResult
from parakeet_rocm.utils.constant import PARAKEET_MODEL_NAME


def map_model_name(model_name: str) -> str | None:
    """Map an OpenAI-compatible model name to a Parakeet model identifier.

    Args:
        model_name: Requested model name from API clients.

    Returns:
        The mapped model identifier when recognized, otherwise ``None``.
    """
    if model_name == "whisper-1":
        return PARAKEET_MODEL_NAME
    if model_name.startswith("nvidia/"):
        return model_name
    return None


def map_response_format(response_format: str) -> str:
    """Map OpenAI response formats to internal output format selectors.

    Args:
        response_format: OpenAI response format string.

    Returns:
        Internal response selector. ``text_only`` indicates plain transcript text,
        while ``json``, ``txt``, ``srt``, and ``vtt`` map to file output formats.

    Raises:
        ValueError: If the provided format is unsupported.
    """
    mapping = {
        "json": "text_only",
        "text": "txt",
        "srt": "srt",
        "vtt": "vtt",
        "verbose_json": "json",
    }
    mapped = mapping.get(response_format)
    if mapped is None:
        msg = f"Unsupported response format: {response_format}"
        raise ValueError(msg)
    return mapped


def infer_language_for_model(model_name: str) -> str:
    """Infer the response language code based on model capabilities.

    Args:
        model_name: Internal Parakeet model identifier.

    Returns:
        BCP-47 language code. ``en`` is returned for English-only models.
        ``und`` (undetermined) is returned for multilingual models where
        language detection metadata is not yet exposed.
    """
    if model_name.endswith("-v2"):
        return "en"
    return "und"


def convert_aligned_result_to_verbose(
    aligned_result: AlignedResult,
    timestamp_granularities: list[str] | None,
) -> dict[str, Any]:
    """Convert ``AlignedResult`` into OpenAI verbose JSON compatible structures.

    Args:
        aligned_result: Internal timestamped transcription result.
        timestamp_granularities: Requested verbose timestamp granularities.

    Returns:
        Dictionary containing text, segments, and words fields for the final
        OpenAI verbose response.
    """
    granularities = set(timestamp_granularities or ["segment", "word"])
    include_segments = "segment" in granularities
    include_words = "word" in granularities

    words = (
        [
            {
                "word": word.word,
                "start": word.start,
                "end": word.end,
            }
            for word in aligned_result.word_segments
        ]
        if include_words
        else None
    )

    segments = None
    if include_segments:
        segments = []
        for index, segment in enumerate(aligned_result.segments):
            segment_words = None
            if include_words:
                segment_words = [
                    {
                        "word": word.word,
                        "start": word.start,
                        "end": word.end,
                    }
                    for word in segment.words
                ]

            segments.append({
                "id": index,
                "seek": 0,
                "start": segment.start,
                "end": segment.end,
                "text": segment.text,
                "tokens": [],
                "temperature": 0.0,
                "avg_logprob": 0.0,
                "compression_ratio": 1.0,
                "no_speech_prob": 0.0,
                "words": segment_words,
            })

    text = " ".join(segment.text.strip() for segment in aligned_result.segments).strip()
    return {
        "text": text,
        "segments": segments,
        "words": words,
    }


def get_audio_duration(audio_path: Path) -> float:
    """Get audio duration in seconds from a media file.

    Args:
        audio_path: Path to the input audio file.

    Returns:
        Duration in seconds, or 0.0 when probing fails.
    """
    try:
        info = sf.info(str(audio_path))
    except (RuntimeError, OSError, ValueError):
        return 0.0
    return float(info.duration)
