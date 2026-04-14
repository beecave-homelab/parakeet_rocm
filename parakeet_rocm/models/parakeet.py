"""Model accessors for NVIDIA Parakeet (NeMo) with lazy cache and idle unload.

This module exposes helpers to lazily load the Parakeet-TDT model with an LRU
cache and to offload the model from GPU VRAM when the application is idle.

Functions ensure the model is always placed on the best available device when
requested, and allow moving the cached instance back to CPU to free VRAM.

``unload_model_to_cpu`` is a no-load offload operation: it uses
``_peek_cached_model`` to check the LRU cache's internal mapping directly,
so it never triggers a model load or device promotion on cache miss.  A
module-level lock (``_cache_lock``) serialises the full offload (model move +
VRAM release) and cache-clear operations to prevent race conditions between
idle-offload threads and ``clear_model_cache``.
"""

from __future__ import annotations

import threading
from functools import lru_cache

import nemo.collections.asr as nemo_asr
import torch
from nemo.collections.asr.models import ASRModel

from parakeet_rocm.utils.constant import PARAKEET_MODEL_NAME
from parakeet_rocm.utils.logging_config import get_logger

logger = get_logger(__name__)

__all__ = [
    "get_model",
    "unload_model_to_cpu",
    "clear_model_cache",
]

_cache_lock = threading.Lock()


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
    """Ensure a model is placed on the target or best-available device.

    If ``device`` is ``None``, selects the preferred device (GPU if
    available, otherwise CPU). If the model's current device cannot be
    determined, it is assumed to be ``"cpu"``. If the model is already on
    the target device, no action is taken.

    Parameters:
        model (nemo_asr.models.ASRModel): NeMo ASR model instance to move.
        device (str | None): Target device (``"cuda"`` or ``"cpu"``). If
            ``None``, the preferred device is used.
    """
    target = device or _best_device()
    try:
        current = next(model.parameters()).device.type  # type: ignore[attr-defined]
    except Exception:
        current = "cpu"
    if current != target:
        model.to(target)


def _load_model(model_name: str) -> ASRModel:
    """Load and initialize a Parakeet ASR model by its identifier.

    The returned model is set to evaluation mode and placed on the best
    available device (GPU if available, otherwise CPU).

    Parameters:
        model_name (str): Identifier of the pretrained Parakeet model to
            load.

    Returns:
        ASRModel: Initialised ASR model instance prepared for inference.
    """
    model = nemo_asr.models.ASRModel.from_pretrained(model_name).eval()
    _ensure_device(model)
    return model


@lru_cache(maxsize=4)
def _get_cached_model(model_name: str = PARAKEET_MODEL_NAME) -> ASRModel:
    """Retrieve a cached Parakeet ASR model instance.

    Parameters:
        model_name (str): Model name or local path identifying the pretrained Parakeet model.

    Returns:
        ASRModel: Cached ASR model instance. This function does not modify
            the model's device placement.
    """
    return _load_model(model_name)


def _peek_cached_model(model_name: str = PARAKEET_MODEL_NAME) -> ASRModel | None:
    """Return the cached model for *model_name* without triggering a load.

    Inspects the LRU cache's internal mapping directly.  Returns ``None``
    when the key is not present, avoiding the cache-miss load that
    ``_get_cached_model`` would trigger.

    Parameters:
        model_name (str): Model name to look up in the cache.

    Returns:
        ASRModel | None: The cached model, or ``None`` if not present.
    """
    # lru_cache stores results in an internal dict-like .__wrapped__ closure.
    # Accessing cache_parameters / cache_info does not trigger a load.
    # The safest way to peek is to check the underlying OrderedDict.
    try:
        cache_dict = _get_cached_model.cache_parameters()  # type: ignore[attr-defined]
    except Exception:
        return None
    return cache_dict.get(model_name)  # type: ignore[union-attr]


def get_model(model_name: str = PARAKEET_MODEL_NAME) -> ASRModel:
    """Retrieve the cached Parakeet ASR model and ensure it is on the best available device.

    Parameters:
        model_name (str): Model identifier or path to load if not already cached.

    Returns:
        model (ASRModel): The cached ASRModel instance placed on the appropriate device.
    """
    model = _get_cached_model(model_name)
    _ensure_device(model)
    return model


def unload_model_to_cpu(model_name: str = PARAKEET_MODEL_NAME) -> None:
    """Move the cached model to CPU to free GPU VRAM.

    This is a no-op when no model is cached or the model is already on CPU.
    The function never triggers a model load or device promotion on cache
    miss.

    Parameters:
        model_name (str): Name or key of the cached Parakeet model to unload
            from GPU.
    """
    with _cache_lock:
        try:
            model = _peek_cached_model(model_name)
        except Exception:
            logger.debug("failed to peek cached model %s", model_name, exc_info=True)
            return
        if model is None:
            return
        try:
            current = next(model.parameters()).device.type  # type: ignore[attr-defined]
        except Exception:
            logger.debug(
                "failed to read model parameters for %s, assuming CPU",
                model_name,
                exc_info=True,
            )
            current = "cpu"
        if current != "cpu":
            model.to("cpu")
        if torch.cuda.is_available():
            try:
                torch.cuda.empty_cache()
            except Exception:
                logger.debug("torch.cuda.empty_cache() failed", exc_info=True)


def clear_model_cache() -> None:
    """Clear the internal LRU cache of loaded model instances.

    After this call, cached models are discarded and will be recreated when
    next requested.
    """
    with _cache_lock:
        try:
            _get_cached_model.cache_clear()  # type: ignore[attr-defined]
        except Exception:
            logger.debug("cache_clear() failed", exc_info=True)
