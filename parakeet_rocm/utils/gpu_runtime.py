# ruff: noqa: D401
"""Helpers for introspecting and preparing the active GPU runtime bindings."""

from __future__ import annotations

import importlib
import logging
import os
import sys
from dataclasses import dataclass
from typing import Literal

RuntimeBackend = Literal["hip-python", "cuda-python", "missing"]


@dataclass(slots=True)
class GpuRuntimeInfo:
    """Metadata describing which CUDA/HIP Python bindings are active."""

    backend: RuntimeBackend
    hip_shim: bool
    module_name: str | None
    error: str | None = None

    @property
    def is_available(self) -> bool:
        """Return ``True`` when CUDA-compatible bindings are present."""
        return self.backend != "missing"


__all__ = [
    "GpuRuntimeInfo",
    "RuntimeBackend",
    "detect_gpu_runtime",
    "log_gpu_runtime",
    "prepare_gpu_runtime",
]


def detect_gpu_runtime() -> GpuRuntimeInfo:
    """Detect whether CUDA or HIP Python bindings are available.

    Returns:
        GpuRuntimeInfo: Metadata about the detected runtime.
    """
    try:
        cuda_module = importlib.import_module("cuda")
    except ModuleNotFoundError as exc:
        return GpuRuntimeInfo(
            backend="missing",
            hip_shim=False,
            module_name=None,
            error=str(exc),
        )
    except Exception as exc:  # pragma: no cover - defensive guard
        return GpuRuntimeInfo(
            backend="missing",
            hip_shim=False,
            module_name=None,
            error=f"{type(exc).__name__}: {exc}",
        )

    hip_shim = bool(
        getattr(cuda_module, "HIP_PYTHON", False)
        or hasattr(cuda_module, "hip")
        or hasattr(cuda_module, "hip_python_mod")
        or hasattr(cuda_module, "HIP_PYTHON_VERSION")
    )

    backend: RuntimeBackend = "hip-python" if hip_shim else "cuda-python"
    module_name = getattr(cuda_module, "__name__", "cuda")

    return GpuRuntimeInfo(
        backend=backend,
        hip_shim=hip_shim,
        module_name=module_name,
    )


def log_gpu_runtime(logger: logging.Logger | None = None) -> GpuRuntimeInfo:
    """Log a diagnostic message about the detected GPU runtime.

    Args:
        logger: Optional logger to emit messages.

    Returns:
        GpuRuntimeInfo: Metadata about the detected runtime.
    """
    info = detect_gpu_runtime()
    active_logger = logger or logging.getLogger(__name__)

    if not info.is_available:
        message = (
            "CUDA Python bindings unavailable; install hip-python-as-cuda on ROCm."
        )
        if info.error:
            message = f"{message} ({info.error})"
        active_logger.warning(message)
        return info

    if info.hip_shim:
        active_logger.info(
            "Detected HIP Python CUDA interoperability layer (module: %s).",
            info.module_name or "cuda",
        )
    else:
        active_logger.info(
            "Detected native CUDA Python bindings (module: %s).",
            info.module_name or "cuda",
        )

    return info


def prepare_gpu_runtime(logger: logging.Logger | None = None) -> GpuRuntimeInfo:
    """Prepare CUDA/HIP Python runtime for better library compatibility.

    Ensures that when running with the HIP CUDA interoperability shim,
    environment and module attributes expected by libraries (e.g., NeMo)
    are present before any heavy imports occur.

    Specifically:
    - Set ``HIP_PYTHON_cudaError_t_HALLUCINATE=1`` when using HIP shim so that
      CUDA error enums referenced by some libraries are synthesized.
    - Ensure the imported ``cuda`` module exposes ``__version__`` to satisfy
      code paths that check the CUDA Python package version.

    Args:
        logger: Optional logger to emit informational messages.

    Returns:
        A ``GpuRuntimeInfo`` describing the detected runtime.
    """
    active_logger = logger or logging.getLogger(__name__)

    # Prefer PyTorch to determine ROCm runtime early, before importing cuda
    is_rocm = False
    try:
        import torch  # local import

        is_rocm = getattr(getattr(torch, "version", object()), "hip", None) is not None
    except Exception:  # pragma: no cover - torch may be unavailable in some envs
        is_rocm = False

    if is_rocm:
        os.environ.setdefault("HIP_PYTHON_cudaError_t_HALLUCINATE", "1")

    # Now import cuda and detect shim
    try:
        cuda_module = importlib.import_module("cuda")
    except Exception as exc:  # pragma: no cover - defensive
        active_logger.debug("Unable to import 'cuda' during preparation: %s", exc)
        return GpuRuntimeInfo(
            backend="missing",
            hip_shim=False,
            module_name=None,
            error=f"{type(exc).__name__}: {exc}",
        )

    hip_shim_detected = bool(
        getattr(cuda_module, "HIP_PYTHON", False)
        or hasattr(cuda_module, "hip")
        or hasattr(cuda_module, "hip_python_mod")
        or hasattr(cuda_module, "HIP_PYTHON_VERSION")
        or is_rocm
    )

    # Ensure cuda.__version__ is available if missing
    if not hasattr(cuda_module, "__version__"):
        version = getattr(cuda_module, "HIP_PYTHON_VERSION", None)
        if version is None and is_rocm:
            version = "0.0.0"
        if version is not None:
            try:
                setattr(cuda_module, "__version__", version)
                sys.modules.get("cuda", cuda_module).__dict__["__version__"] = version
            except Exception:  # pragma: no cover
                pass

    if hip_shim_detected:
        active_logger.debug(
            "Prepared HIP CUDA shim (hallucinate enums, ensure cuda.__version__)."
        )

    backend: RuntimeBackend = "hip-python" if hip_shim_detected else "cuda-python"
    return GpuRuntimeInfo(
        backend=backend,
        hip_shim=hip_shim_detected,
        module_name=getattr(cuda_module, "__name__", "cuda"),
    )
