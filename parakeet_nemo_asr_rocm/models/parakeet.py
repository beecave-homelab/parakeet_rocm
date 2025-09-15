"""Model accessors for NVIDIA Parakeet (NeMo) with lazy cache and idle unload.

This module exposes helpers to lazily load the Parakeet-TDT model with an LRU
cache and to offload the model from GPU VRAM when the application is idle.

Functions ensure the model is always placed on the best available device when
requested, and allow moving the cached instance back to CPU to free VRAM.
"""

from __future__ import annotations

from functools import lru_cache

import nemo.collections.asr as nemo_asr
import torch
from nemo.collections.asr.models import ASRModel

from parakeet_nemo_asr_rocm.utils.constant import PARAKEET_MODEL_NAME

__all__ = [
    "get_model",
    "unload_model_to_cpu",
    "clear_model_cache",
]


def _best_device() -> str:
    """Return the preferred device string.

    Returns:
        str: ``"cuda"`` when CUDA/ROCm is available, else ``"cpu"``.

    """
    return "cuda" if torch.cuda.is_available() else "cpu"


def _ensure_device(
    model: ASRModel,
    *,
    device: str | None = None,
) -> None:
    """Move the model to the specified or best device if needed.

    Args:
        model (nemo_asr.models.ASRModel): The NeMo ASR model instance.
        device (str | None): Target device (``"cuda"`` or ``"cpu"``). If
            ``None``, uses the best available device.

    """
    target = device or _best_device()
    try:
        current = next(model.parameters()).device.type  # type: ignore[attr-defined]
    except Exception:
        current = "cpu"
    if current != target:
        model.to(target)


def _load_model(model_name: str) -> ASRModel:
    """Load and initialize the Parakeet ASR model.

    This function downloads the pre-trained model from NVIDIA's NGC, sets it
    to evaluation mode, and moves it to the appropriate device (GPU if
    available, otherwise CPU).

    Args:
        model_name (str): Model identifier for ``nemo_asr.models.ASRModel``.

    Returns:
        ASRModel: The initialized ASRModel instance.

    """
    model = nemo_asr.models.ASRModel.from_pretrained(model_name).eval()
    _ensure_device(model)
    return model


@lru_cache(maxsize=4)
def _get_cached_model(model_name: str = PARAKEET_MODEL_NAME) -> ASRModel:
    """Return a cached Parakeet ASR model instance.

    Args:
        model_name (str): The model name or path.

    Returns:
        ASRModel: Cached model instance (no device adjustments).

    """
    return _load_model(model_name)


def get_model(model_name: str = PARAKEET_MODEL_NAME) -> ASRModel:
    """Access the cached model and ensure correct device placement.

    This accessor promotes a previously offloaded CPU model back to GPU when
    available, while reusing the same cached instance.

    Args:
        model_name (str): The model name or path.

    Returns:
        ASRModel: Cached and device-correct model instance.

    """
    model = _get_cached_model(model_name)
    _ensure_device(model)
    return model


def unload_model_to_cpu(model_name: str = PARAKEET_MODEL_NAME) -> None:
    """Move the cached model to CPU and free GPU VRAM if possible.

    This keeps the model weights in host RAM for quicker future reuse while
    releasing GPU memory. If CUDA/ROCm is not available or the model is
    already on CPU, this is a no-op.

    Args:
        model_name (str): The model key used by :func:`get_model`.

    """
    try:
        # Retrieve cached instance without altering cache state
        model = get_model(model_name)
    except Exception:
        return
    # Always place on CPU
    model.to("cpu")
    if torch.cuda.is_available():
        try:
            torch.cuda.empty_cache()
        except Exception:
            pass


def clear_model_cache() -> None:
    """Completely clear the cached model(s).

    Use this when a full teardown is desired. The next call to :func:`get_model`
    will re-download/reload the model and place it on the best device.
    """
    try:
        _get_cached_model.cache_clear()  # type: ignore[attr-defined]
    except Exception:
        pass
