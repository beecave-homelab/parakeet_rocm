"""Unit tests for parakeet_rocm.models.parakeet module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from parakeet_rocm.models.parakeet import (
    _best_device,
    _ensure_device,
    _load_model,
    clear_model_cache,
    get_model,
    unload_model_to_cpu,
)


def test_best_device() -> None:
    """Returns cuda when available, cpu otherwise."""
    with patch("torch.cuda.is_available", return_value=True):
        assert _best_device() == "cuda"

    with patch("torch.cuda.is_available", return_value=False):
        assert _best_device() == "cpu"


def test_ensure_device_with_exception_and_move(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Tests device detection exception handling and device move."""
    # Mock model that raises exception on parameters() call
    mock_model = MagicMock()
    mock_model.parameters.side_effect = RuntimeError("Cannot access parameters")

    # Mock _best_device to return cuda
    monkeypatch.setattr("parakeet_rocm.models.parakeet._best_device", lambda: "cuda")

    # Should not raise exception, should fall back to cpu and then move to cuda
    _ensure_device(mock_model)

    # Verify model.to was called with cuda
    mock_model.to.assert_called_with("cuda")


def test_ensure_device_already_on_target(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Tests no action when model is already on target device."""
    mock_model = MagicMock()
    mock_param = MagicMock()
    mock_param.device.type = "cpu"
    mock_model.parameters.return_value = [mock_param]

    # Mock _best_device to return cpu
    monkeypatch.setattr("parakeet_rocm.models.parakeet._best_device", lambda: "cpu")

    _ensure_device(mock_model)

    # model.to should not be called since already on target device
    mock_model.to.assert_not_called()


def test_unload_model_to_cpu_exceptions() -> None:
    """Tests exception handling in unload_model_to_cpu."""
    # Test get_model exception
    with patch(
        "parakeet_rocm.models.parakeet.get_model", side_effect=RuntimeError("Model not found")
    ):
        # Should not raise exception
        unload_model_to_cpu()

    # Test torch.cuda.empty_cache exception
    mock_model = MagicMock()
    with (
        patch("parakeet_rocm.models.parakeet.get_model", return_value=mock_model),
        patch("torch.cuda.is_available", return_value=True),
        patch("torch.cuda.empty_cache", side_effect=RuntimeError("Cache clear failed")),
    ):
        unload_model_to_cpu()

        # Model should still be moved to CPU despite cache clear failure
        mock_model.to.assert_called_with("cpu")


def test_unload_model_to_cpu_no_gpu() -> None:
    """Tests unload when GPU is not available."""
    mock_model = MagicMock()
    with (
        patch("parakeet_rocm.models.parakeet.get_model", return_value=mock_model),
        patch("torch.cuda.is_available", return_value=False),
    ):
        unload_model_to_cpu()

        # Model should be moved to CPU
        mock_model.to.assert_called_with("cpu")


def test_clear_model_cache_exception() -> None:
    """Tests exception handling in clear_model_cache."""
    with patch("parakeet_rocm.models.parakeet._get_cached_model") as mock_cached:
        mock_cached.cache_clear.side_effect = RuntimeError("Cache clear failed")

        # Should not raise exception
        clear_model_cache()


@patch("parakeet_rocm.models.parakeet._load_model")
def test_get_model_caching(mock_load: MagicMock) -> None:
    """Tests that get_model uses cached model and ensures device placement."""
    clear_model_cache()
    mock_model = MagicMock()
    mock_load.return_value = mock_model

    # First call should load model
    result1 = get_model("test_model")
    assert result1 is mock_model
    mock_load.assert_called_once_with("test_model")

    # Reset mock to test caching
    mock_load.reset_mock()

    # Second call should use cache (not call _load_model again)
    result2 = get_model("test_model")
    assert result2 is mock_model
    mock_load.assert_not_called()


@patch("parakeet_rocm.models.parakeet._load_model")
def test_get_model_device_ensure(mock_load: MagicMock) -> None:
    """Tests that get_model calls _ensure_device on cached model."""
    clear_model_cache()
    mock_model = MagicMock()
    mock_load.return_value = mock_model

    with patch("parakeet_rocm.models.parakeet._ensure_device") as mock_ensure:
        get_model("test_model")
        # Just verify it was called, not with which specific instance
        mock_ensure.assert_called_once()


@patch("nemo.collections.asr.models.ASRModel.from_pretrained")
def test_load_model(mock_from_pretrained: MagicMock) -> None:
    """Tests _load_model initialization and device placement."""
    mock_model = MagicMock()
    # Make eval() return the same mock instance
    mock_model.eval.return_value = mock_model
    mock_from_pretrained.return_value = mock_model

    with patch("parakeet_rocm.models.parakeet._ensure_device") as mock_ensure:
        result = _load_model("test_model")

        assert result is mock_model
        mock_from_pretrained.assert_called_once_with("test_model")
        mock_model.eval.assert_called_once()
        mock_ensure.assert_called_once_with(mock_model)
