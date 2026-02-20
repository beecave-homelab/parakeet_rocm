"""Unit tests for API request/response schemas."""

from __future__ import annotations

import io

import pytest
from fastapi import UploadFile
from pydantic import ValidationError

from parakeet_rocm.api.schemas import TranscriptionRequest
from parakeet_rocm.utils.constant import API_MODEL_NAME


def _make_upload_file(name: str = "sample.wav") -> UploadFile:
    """Create an in-memory UploadFile for schema validation tests.

    Args:
        name: Filename value to attach to the uploaded file.

    Returns:
        UploadFile instance backed by a bytes buffer.
    """
    return UploadFile(file=io.BytesIO(b"audio-bytes"), filename=name)


def test_transcription_request_maps_whisper_alias() -> None:
    """whisper-1 should normalize to the configured Parakeet model name."""
    req = TranscriptionRequest(file=_make_upload_file(), model="whisper-1")
    assert req.model == API_MODEL_NAME


def test_transcription_request_accepts_nvidia_model() -> None:
    """NVIDIA model names should pass validation unchanged."""
    req = TranscriptionRequest(file=_make_upload_file(), model="nvidia/parakeet-tdt-0.6b-v3")
    assert req.model == "nvidia/parakeet-tdt-0.6b-v3"


def test_transcription_request_rejects_invalid_model() -> None:
    """Invalid model names should raise a validation error."""
    with pytest.raises(ValidationError):
        TranscriptionRequest(file=_make_upload_file(), model="gpt-4o-transcribe")


def test_transcription_request_rejects_invalid_response_format() -> None:
    """Unsupported response_format values should fail schema validation."""
    with pytest.raises(ValidationError):
        TranscriptionRequest(
            file=_make_upload_file(),
            model="whisper-1",
            response_format="yaml",  # type: ignore[arg-type]
        )


def test_transcription_request_rejects_invalid_timestamp_granularity() -> None:
    """Unsupported timestamp granularity entries should fail schema validation."""
    with pytest.raises(ValidationError):
        TranscriptionRequest(
            file=_make_upload_file(),
            model="whisper-1",
            timestamp_granularities=["sentence"],  # type: ignore[list-item]
        )
