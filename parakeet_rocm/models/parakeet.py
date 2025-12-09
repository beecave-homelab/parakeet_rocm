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

from parakeet_rocm.utils.constant import PARAKEET_MODEL_NAME

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
    """
    Ensure the given ASR model is placed on the specified device or the best available device.
    
    If `device` is None, selects the preferred device (GPU if available, otherwise CPU). If the model's current device cannot be determined, it is assumed to be "cpu". If the model is already on the target device no action is taken.
    
    Parameters:
        model (nemo_asr.models.ASRModel): The NeMo ASR model instance to move.
        device (str | None): Target device `"cuda"` or `"cpu"`. If `None`, the preferred device will be used.
    """
    target = device or _best_device()
    try:
        current = next(model.parameters()).device.type  # type: ignore[attr-defined]
    except Exception:
        current = "cpu"
    if current != target:
        model.to(target)


def _load_model(model_name: str) -> ASRModel:
    """
    Load and initialize a Parakeet ASR model by its identifier.
    
    The returned model is set to evaluation mode and placed on the best available device (GPU if available, otherwise CPU).
    
    Parameters:
        model_name (str): Identifier of the pretrained Parakeet model to load.
    
    Returns:
        ASRModel: An initialized ASRModel instance prepared for inference.
    """
    model = nemo_asr.models.ASRModel.from_pretrained(model_name).eval()
    _ensure_device(model)
    return model


@lru_cache(maxsize=4)
def _get_cached_model(model_name: str = PARAKEET_MODEL_NAME) -> ASRModel:
    """
    Retrieve a cached Parakeet ASR model instance.
    
    Parameters:
        model_name (str): Model name or local path identifying the pretrained Parakeet model.
    
    Returns:
        ASRModel: The cached ASRModel instance. This function does not modify the model's device placement.
    """
    return _load_model(model_name)


def get_model(model_name: str = PARAKEET_MODEL_NAME) -> ASRModel:
    """
    Retrieve the cached Parakeet ASR model and ensure it is on the best available device.
    
    Parameters:
        model_name (str): Model identifier or path to load if not already cached.
    
    Returns:
        model (ASRModel): The cached ASRModel instance placed on the appropriate device.
    """
    model = _get_cached_model(model_name)
    _ensure_device(model)
    return model


def unload_model_to_cpu(model_name: str = PARAKEET_MODEL_NAME) -> None:
    """
    Move the cached Parakeet model to CPU to free GPU VRAM while keeping weights in host memory.
    
    If the model is already on CPU or no GPU is available, this performs no harmful action. After moving the model to CPU, attempts to release GPU memory by emptying the CUDA cache when available.
    
    Parameters:
        model_name (str): Name or key of the cached Parakeet model to unload from GPU.
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
    """
    Clear the internal LRU cache of loaded model instances.
    
    After this call, cached models are discarded and will be recreated when next requested.
    """
    try:
        _get_cached_model.cache_clear()  # type: ignore[attr-defined]
    except Exception:
        pass