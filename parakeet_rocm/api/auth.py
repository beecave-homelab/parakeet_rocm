"""Authentication helpers for OpenAI-compatible API routes."""

from __future__ import annotations

import secrets

from fastapi import Request
from fastapi.responses import JSONResponse

from parakeet_rocm.api.schemas import ErrorObject, ErrorResponse
from parakeet_rocm.utils.constant import API_BEARER_TOKEN


def _build_unauthorized_response() -> JSONResponse:
    """Build a standard OpenAI-style invalid API key response.

    Returns:
        JSON response with unauthorized status and OpenAI-style error payload.
    """
    payload = ErrorResponse(
        error=ErrorObject(
            message="Invalid authentication credentials.",
            type="invalid_request_error",
            code="invalid_api_key",
        )
    ).model_dump()
    return JSONResponse(status_code=401, content=payload)


def require_api_bearer_token(request: Request) -> JSONResponse | None:
    """Validate API bearer authentication when configured.

    Auth is disabled (open mode) when ``API_BEARER_TOKEN`` is unset/empty.

    Args:
        request: Incoming request containing optional Authorization header.

    Returns:
        ``None`` when request is authorized (or auth is disabled).
        Unauthorized JSON response when authentication fails.
    """
    expected_token = API_BEARER_TOKEN
    if not expected_token:
        return None

    authorization_header = request.headers.get("Authorization", "").strip()
    scheme, _, token = authorization_header.partition(" ")
    provided_token = token.strip()

    if scheme.lower() != "bearer" or not provided_token:
        return _build_unauthorized_response()

    if not secrets.compare_digest(provided_token, expected_token):
        return _build_unauthorized_response()

    return None
