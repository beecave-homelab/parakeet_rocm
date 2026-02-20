"""Unit tests for project-wide constants."""

from __future__ import annotations

import importlib

import pytest

import parakeet_rocm.utils.constant as constant


def test_api_model_name_falls_back_when_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    """API model name should fall back when env is empty or whitespace."""
    monkeypatch.setenv("API_MODEL_NAME", "   ")
    monkeypatch.setenv("PARAKEET_MODEL_NAME", "nvidia/test-model")

    reloaded = importlib.reload(constant)

    assert reloaded.API_MODEL_NAME == "nvidia/test-model"
