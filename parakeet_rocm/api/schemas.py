"""OpenAI-compatible request and response schemas for the REST API."""

from __future__ import annotations

from typing import Literal

from fastapi import UploadFile
from pydantic import BaseModel, Field, field_validator

from parakeet_rocm.utils.constant import API_MODEL_NAME

OpenAIResponseFormat = Literal["json", "text", "srt", "verbose_json", "vtt"]
TimestampGranularity = Literal["word", "segment"]


class TranscriptionRequest(BaseModel):
    """Validate OpenAI-compatible transcription form parameters.

    Notes:
        ``language``, ``prompt``, and ``temperature`` are accepted for compatibility,
        but ignored by the current Parakeet CTC pipeline.
    """

    model_config = {"arbitrary_types_allowed": True}

    file: UploadFile = Field(..., description="Audio file to transcribe.")
    model: str = Field(
        ...,
        description=(
            "Model identifier. Accepts 'whisper-1' alias or explicit NVIDIA model "
            "names like 'nvidia/parakeet-tdt-0.6b-v3'."
        ),
    )
    language: str | None = Field(
        default=None,
        description=(
            "Optional ISO-639-1 language code for OpenAI compatibility. Ignored by "
            "Parakeet v3 because language is auto-detected."
        ),
    )
    prompt: str | None = Field(
        default=None,
        description=(
            "Optional prompt for OpenAI compatibility. Ignored because Parakeet CTC "
            "transcription has no prompt-conditioning equivalent."
        ),
    )
    temperature: float | None = Field(
        default=None,
        description=(
            "Optional temperature for OpenAI compatibility. Ignored because Parakeet "
            "CTC decoding is deterministic."
        ),
    )
    response_format: OpenAIResponseFormat = Field(
        default="json",
        description="Output format: json, text, srt, vtt, or verbose_json.",
    )
    timestamp_granularities: list[TimestampGranularity] | None = Field(
        default=None,
        description=(
            "Optional timestamp granularity controls for verbose_json. "
            "Allowed values: 'word' and 'segment'."
        ),
    )

    @field_validator("model")
    @classmethod
    def validate_and_map_model(cls, value: str) -> str:
        """Normalize accepted model aliases to internal Parakeet model names.

        Args:
            value: Raw model string from the API request.

        Returns:
            Normalized model name used internally by Parakeet.

        Raises:
            ValueError: If the provided model does not match accepted values.
        """
        if value == "whisper-1":
            return API_MODEL_NAME
        if value.startswith("nvidia/"):
            return value
        msg = "Model must be 'whisper-1' or start with 'nvidia/'."
        raise ValueError(msg)


class TranscriptionResponseJson(BaseModel):
    """OpenAI-compatible JSON response payload."""

    text: str


class TranscriptionWord(BaseModel):
    """Word-level timing entry in OpenAI verbose JSON format."""

    word: str
    start: float
    end: float


class TranscriptionSegment(BaseModel):
    """Segment-level timing entry in OpenAI verbose JSON format."""

    id: int
    seek: int
    start: float
    end: float
    text: str
    tokens: list[int]
    temperature: float
    avg_logprob: float
    compression_ratio: float
    no_speech_prob: float
    words: list[TranscriptionWord] | None = None


class TranscriptionResponseVerbose(BaseModel):
    """OpenAI-compatible verbose_json transcription response payload."""

    task: Literal["transcribe"]
    language: str
    duration: float
    text: str
    segments: list[TranscriptionSegment] | None = None
    words: list[TranscriptionWord] | None = None


class ErrorObject(BaseModel):
    """OpenAI-style error object."""

    message: str
    type: str
    code: str


class ErrorResponse(BaseModel):
    """OpenAI-style top-level error response wrapper."""

    error: ErrorObject
