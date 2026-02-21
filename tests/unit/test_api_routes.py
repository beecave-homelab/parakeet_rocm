"""Unit tests for OpenAI-compatible API routes."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from parakeet_rocm.api import auth, routes
from parakeet_rocm.timestamps.models import AlignedResult, Segment, Word


@pytest.fixture
def test_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """Build a minimal FastAPI app including the API router.

    Returns:
        Test client for exercising API routes.
    """
    app = FastAPI()
    app.include_router(routes.router)
    monkeypatch.setattr(routes, "validate_audio_file", lambda p: p)
    monkeypatch.setattr(routes, "get_model", lambda _model_name: object())
    monkeypatch.setattr(auth, "API_BEARER_TOKEN", None)
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


def test_create_transcription__returns_json_response(
    test_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """API should return OpenAI-style JSON transcription response."""
    monkeypatch.setattr(routes, "cli_transcribe", _mock_cli_transcribe_factory())

    response = test_client.post(
        "/v1/audio/transcriptions",
        files={"file": ("audio.wav", b"fake-audio", "audio/wav")},
        data={"model": "whisper-1", "response_format": "json"},
    )

    assert response.status_code == 200
    assert response.json() == {"text": "hello world"}


def test_create_transcription__requires_bearer_auth_when_token_configured(
    test_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """API should return 401 when auth token is configured and header is missing."""
    monkeypatch.setattr(routes, "cli_transcribe", _mock_cli_transcribe_factory())
    monkeypatch.setattr(auth, "API_BEARER_TOKEN", "sk-secret")

    response = test_client.post(
        "/v1/audio/transcriptions",
        files={"file": ("audio.wav", b"fake-audio", "audio/wav")},
        data={"model": "whisper-1", "response_format": "json"},
    )

    assert response.status_code == 401
    assert response.json() == {
        "error": {
            "message": "Invalid authentication credentials.",
            "type": "invalid_request_error",
            "code": "invalid_api_key",
        }
    }


def test_create_transcription__rejects_non_bearer_auth_scheme(
    test_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """API should reject authorization headers that do not use Bearer scheme."""
    monkeypatch.setattr(routes, "cli_transcribe", _mock_cli_transcribe_factory())
    monkeypatch.setattr(auth, "API_BEARER_TOKEN", "sk-secret")

    response = test_client.post(
        "/v1/audio/transcriptions",
        files={"file": ("audio.wav", b"fake-audio", "audio/wav")},
        data={"model": "whisper-1", "response_format": "json"},
        headers={"Authorization": "Basic abc123"},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_api_key"


def test_create_transcription__rejects_wrong_bearer_token(
    test_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """API should reject incorrect bearer tokens when auth is enabled."""
    monkeypatch.setattr(routes, "cli_transcribe", _mock_cli_transcribe_factory())
    monkeypatch.setattr(auth, "API_BEARER_TOKEN", "sk-secret")

    response = test_client.post(
        "/v1/audio/transcriptions",
        files={"file": ("audio.wav", b"fake-audio", "audio/wav")},
        data={"model": "whisper-1", "response_format": "json"},
        headers={"Authorization": "Bearer sk-wrong"},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_api_key"


def test_create_transcription__accepts_valid_bearer_token(
    test_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """API should process requests with valid bearer token when auth is enabled."""
    monkeypatch.setattr(routes, "cli_transcribe", _mock_cli_transcribe_factory())
    monkeypatch.setattr(auth, "API_BEARER_TOKEN", "sk-secret")

    response = test_client.post(
        "/v1/audio/transcriptions",
        files={"file": ("audio.wav", b"fake-audio", "audio/wav")},
        data={"model": "whisper-1", "response_format": "json"},
        headers={"Authorization": "Bearer sk-secret"},
    )

    assert response.status_code == 200
    assert response.json() == {"text": "hello world"}


def test_create_transcription__logs_origin_and_settings(
    test_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Debug logs should include request origin and effective settings."""
    monkeypatch.setattr(routes, "cli_transcribe", _mock_cli_transcribe_factory())
    caplog.set_level("DEBUG", logger=routes.logger.name)

    response = test_client.post(
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
    assert "API transcription timing:" in caplog.text


def test_create_transcription__uses_api_default_batch_and_chunk(
    test_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """API route should pass API-specific default batch/chunk values to transcription."""
    captured_kwargs: dict[str, object] = {}

    def _capture_cli_transcribe(**kwargs: object) -> list[Path]:
        captured_kwargs.update(kwargs)
        output_dir = Path(kwargs["output_dir"])
        output_dir.mkdir(parents=True, exist_ok=True)
        out_file = output_dir / "out.txt"
        out_file.write_text("hello world", encoding="utf-8")
        return [out_file]

    monkeypatch.setattr(routes, "API_DEFAULT_BATCH_SIZE", 3)
    monkeypatch.setattr(routes, "API_DEFAULT_CHUNK_LEN_SEC", 30)
    monkeypatch.setattr(routes, "cli_transcribe", _capture_cli_transcribe)

    response = test_client.post(
        "/v1/audio/transcriptions",
        files={"file": ("audio.wav", b"fake-audio", "audio/wav")},
        data={"model": "whisper-1", "response_format": "json"},
    )

    assert response.status_code == 200
    assert captured_kwargs["batch_size"] == 3
    assert captured_kwargs["chunk_len_sec"] == 30


def test_create_transcription__returns_text_response(
    test_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """API should return plain text when ``response_format=text``."""
    monkeypatch.setattr(routes, "cli_transcribe", _mock_cli_transcribe_factory())

    response = test_client.post(
        "/v1/audio/transcriptions",
        files={"file": ("audio.wav", b"fake-audio", "audio/wav")},
        data={"model": "whisper-1", "response_format": "text"},
    )

    assert response.status_code == 200
    assert response.text == "hello world"


def test_create_transcription__returns_verbose_json_response(
    test_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """API should return verbose_json payload with segment and word data."""
    monkeypatch.setattr(routes, "cli_transcribe", _mock_cli_transcribe_factory())
    monkeypatch.setattr(routes, "get_audio_duration", lambda _path: 1.0)

    response = test_client.post(
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


def test_create_transcription__invalid_generated_verbose_json_returns_server_error(
    test_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Malformed generated verbose JSON should return a server error response."""

    def _mock_invalid_verbose_json(**kwargs: object) -> list[Path]:
        output_dir = Path(kwargs["output_dir"])
        output_dir.mkdir(parents=True, exist_ok=True)
        out_file = output_dir / "out.txt"
        out_file.write_text('{"segments": [}', encoding="utf-8")
        return [out_file]

    monkeypatch.setattr(routes, "cli_transcribe", _mock_invalid_verbose_json)

    response = test_client.post(
        "/v1/audio/transcriptions",
        files=[
            ("file", ("audio.wav", b"fake-audio", "audio/wav")),
            ("model", (None, "whisper-1")),
            ("response_format", (None, "verbose_json")),
            ("timestamp_granularities", (None, "word")),
            ("timestamp_granularities", (None, "segment")),
        ],
    )

    assert response.status_code == 500
    payload = response.json()
    assert payload["error"]["code"] == "invalid_json_output"
    assert payload["error"]["message"] == "Server produced invalid JSON for verbose response."


def test_create_transcription__ffmpeg_format_error_returns_invalid_audio_format(
    test_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Audio decoding runtime failures should return invalid_audio_format."""

    def _raise_ffmpeg_format_error(**_kwargs: object) -> list[Path]:
        msg = "FFmpeg failed: unknown format while decoding input"
        raise RuntimeError(msg)

    monkeypatch.setattr(routes, "cli_transcribe", _raise_ffmpeg_format_error)

    response = test_client.post(
        "/v1/audio/transcriptions",
        files={"file": ("audio.wav", b"fake-audio", "audio/wav")},
        data={"model": "whisper-1", "response_format": "json"},
    )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["code"] == "invalid_audio_format"


def test_create_transcription__unrelated_format_error_returns_runtime_error(
    test_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unrelated format runtime failures should not be misclassified as audio errors."""

    def _raise_unrelated_format_error(**_kwargs: object) -> list[Path]:
        msg = "Template format key missing from internal formatter map"
        raise RuntimeError(msg)

    monkeypatch.setattr(routes, "cli_transcribe", _raise_unrelated_format_error)

    response = test_client.post(
        "/v1/audio/transcriptions",
        files={"file": ("audio.wav", b"fake-audio", "audio/wav")},
        data={"model": "whisper-1", "response_format": "json"},
    )

    assert response.status_code == 500
    payload = response.json()
    assert payload["error"]["code"] == "runtime_error"


def test_create_transcription__rejects_invalid_model(
    test_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """API should return an OpenAI-style invalid_model error."""
    monkeypatch.setattr(routes, "cli_transcribe", _mock_cli_transcribe_factory())

    response = test_client.post(
        "/v1/audio/transcriptions",
        files={"file": ("audio.wav", b"fake-audio", "audio/wav")},
        data={"model": "gpt-4o-transcribe", "response_format": "json"},
    )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["code"] == "invalid_model"
    assert payload["error"]["message"] == "Model must be 'whisper-1' or start with 'nvidia/'."


def test_create_transcription__rejects_unsupported_format(
    test_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """API should return an OpenAI-style unsupported_format error."""
    monkeypatch.setattr(routes, "cli_transcribe", _mock_cli_transcribe_factory())

    response = test_client.post(
        "/v1/audio/transcriptions",
        files={"file": ("audio.wav", b"fake-audio", "audio/wav")},
        data={"model": "whisper-1", "response_format": "yaml"},
    )

    assert response.status_code == 400
    payload = response.json()
    assert payload["error"]["code"] == "unsupported_format"


def test_create_transcription__requires_file_field(test_client: TestClient) -> None:
    """API should reject requests missing the required file form field."""
    response = test_client.post(
        "/v1/audio/transcriptions",
        data={"model": "whisper-1", "response_format": "json"},
    )

    assert response.status_code == 422
    detail = response.json().get("detail", [])
    assert any(item.get("loc") == ["body", "file"] for item in detail)
