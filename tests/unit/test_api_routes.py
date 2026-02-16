"""Unit tests for OpenAI-compatible API routes."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from parakeet_rocm.api import routes
from parakeet_rocm.timestamps.models import AlignedResult, Segment, Word


def _build_test_app() -> TestClient:
    """Build a minimal FastAPI app including the API router.

    Returns:
        Test client for exercising API routes.
    """
    app = FastAPI()
    app.include_router(routes.router)
    return TestClient(app)


def _mock_cli_transcribe_factory() -> Callable[..., list[Path]]:
    """Create a mock ``cli_transcribe`` implementation for route tests.

    Returns:
        Function that writes deterministic output files into output_dir.
    """

    def _mock_cli_transcribe(**kwargs: object) -> list[Path]:
        output_dir = Path(kwargs["output_dir"])
        output_dir.mkdir(parents=True, exist_ok=True)
        out_file = output_dir / "out.txt"
        output_format = str(kwargs["output_format"])

        if output_format == "json":
            words = [
                Word(word="hello", start=0.0, end=0.4),
                Word(word="world", start=0.5, end=1.0),
            ]
            segment = Segment(text="hello world", words=words, start=0.0, end=1.0)
            payload = AlignedResult(
                segments=[segment],
                word_segments=words,
            ).model_dump_json(indent=2)
            out_file.write_text(payload, encoding="utf-8")
        elif output_format == "srt":
            out_file.write_text(
                "1\n00:00:00,000 --> 00:00:01,000\nhello world\n",
                encoding="utf-8",
            )
        elif output_format == "vtt":
            out_file.write_text(
                "WEBVTT\n\n00:00:00.000 --> 00:00:01.000\nhello world\n",
                encoding="utf-8",
            )
        else:
            out_file.write_text("hello world", encoding="utf-8")

        return [out_file]

    return _mock_cli_transcribe


def test_transcription_json_response(monkeypatch: pytest.MonkeyPatch) -> None:
    """API should return OpenAI-style JSON transcription response."""
    client = _build_test_app()
    monkeypatch.setattr(routes, "cli_transcribe", _mock_cli_transcribe_factory())

    response = client.post(
        "/v1/audio/transcriptions",
        files={"file": ("audio.wav", b"fake-audio", "audio/wav")},
        data={"model": "whisper-1", "response_format": "json"},
    )

    assert response.status_code == 200
    assert response.json() == {"text": "hello world"}


def test_transcription_json_response_logs_origin_and_settings(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Debug logs should include request origin and effective settings."""
    client = _build_test_app()
    monkeypatch.setattr(routes, "cli_transcribe", _mock_cli_transcribe_factory())
    caplog.set_level("DEBUG", logger=routes.logger.name)

    response = client.post(
        "/v1/audio/transcriptions",
        files={"file": ("audio.wav", b"fake-audio", "audio/wav")},
        data={"model": "whisper-1", "response_format": "json"},
        headers={"Authorization": "Bearer sk-test", "api-key": "sk-test"},
    )

    assert response.status_code == 200
    assert response.json() == {"text": "hello world"}
    assert "origin=testclient" in caplog.text
    assert "sk-test" not in caplog.text
    assert "API transcription settings:" in caplog.text
    assert "batch_size=1" in caplog.text
    assert "merge_strategy=lcs" in caplog.text


def test_transcription_text_response(monkeypatch: pytest.MonkeyPatch) -> None:
    """API should return plain text when ``response_format=text``."""
    client = _build_test_app()
    monkeypatch.setattr(routes, "cli_transcribe", _mock_cli_transcribe_factory())

    response = client.post(
        "/v1/audio/transcriptions",
        files={"file": ("audio.wav", b"fake-audio", "audio/wav")},
        data={"model": "whisper-1", "response_format": "text"},
    )

    assert response.status_code == 200
    assert response.text == "hello world"


def test_transcription_verbose_json_response(monkeypatch: pytest.MonkeyPatch) -> None:
    """API should return verbose_json payload with segment and word data."""
    client = _build_test_app()
    monkeypatch.setattr(routes, "cli_transcribe", _mock_cli_transcribe_factory())
    monkeypatch.setattr(routes, "get_audio_duration", lambda _path: 1.0)

    response = client.post(
        "/v1/audio/transcriptions",
        files=[
            ("file", ("audio.wav", b"fake-audio", "audio/wav")),
            ("model", (None, "whisper-1")),
            ("response_format", (None, "verbose_json")),
            ("timestamp_granularities", (None, "word")),
            ("timestamp_granularities", (None, "segment")),
        ],
    )

    assert response.status_code == 200
    body = response.json()
    assert body["task"] == "transcribe"
    assert body["language"] == "und"
    assert body["text"] == "hello world"
    assert body["duration"] == 1.0
    assert body["segments"]
    assert body["words"]


def test_transcription_rejects_invalid_model(monkeypatch: pytest.MonkeyPatch) -> None:
    """API should return an OpenAI-style invalid_model error."""
    client = _build_test_app()
    monkeypatch.setattr(routes, "cli_transcribe", _mock_cli_transcribe_factory())

    response = client.post(
        "/v1/audio/transcriptions",
        files={"file": ("audio.wav", b"fake-audio", "audio/wav")},
        data={"model": "gpt-4o-transcribe", "response_format": "json"},
    )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["code"] == "invalid_model"
    assert payload["error"]["message"] == "Model must be 'whisper-1' or start with 'nvidia/'."


def test_transcription_rejects_unsupported_format(monkeypatch: pytest.MonkeyPatch) -> None:
    """API should return an OpenAI-style unsupported_format error."""
    client = _build_test_app()
    monkeypatch.setattr(routes, "cli_transcribe", _mock_cli_transcribe_factory())

    response = client.post(
        "/v1/audio/transcriptions",
        files={"file": ("audio.wav", b"fake-audio", "audio/wav")},
        data={"model": "whisper-1", "response_format": "yaml"},
    )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["code"] == "unsupported_format"


def test_transcription_requires_file_field() -> None:
    """API should reject requests missing the required file form field."""
    client = _build_test_app()

    response = client.post(
        "/v1/audio/transcriptions",
        data={"model": "whisper-1", "response_format": "json"},
    )

    assert response.status_code == 422
    detail = response.json().get("detail", [])
    assert any(item.get("loc") == ["body", "file"] for item in detail)
