# ruff: noqa: D401
"""Helpers for introspecting the active GPU runtime bindings."""

from __future__ import annotations

import importlib
import logging
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
]


def detect_gpu_runtime() -> GpuRuntimeInfo:
    """Detect whether CUDA or HIP Python bindings are available."""

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
    )

    backend: RuntimeBackend = "hip-python" if hip_shim else "cuda-python"
    module_name = getattr(cuda_module, "__name__", "cuda")

    return GpuRuntimeInfo(
        backend=backend,
        hip_shim=hip_shim,
        module_name=module_name,
    )


def log_gpu_runtime(logger: logging.Logger | None = None) -> GpuRuntimeInfo:
    """Log a diagnostic message about the detected GPU runtime."""

    info = detect_gpu_runtime()
    active_logger = logger or logging.getLogger(__name__)

    if not info.is_available:
        message = "CUDA Python bindings unavailable; install hip-python-as-cuda on ROCm."
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
