"""OpenAI-compatible REST API package for Parakeet-ROCm."""

from __future__ import annotations

from parakeet_rocm.api.app import create_api_app, create_app

__all__ = ["create_app", "create_api_app"]
