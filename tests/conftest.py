"""Shared test fixtures for the parakeet_rocm test suite."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture(autouse=True, scope="session")
def _patch_srt_safe_root(tmp_path_factory: pytest.TempPathFactory) -> None:
    """Relax SRT_SAFE_ROOT so tests using tmp_path are not rejected.

    The production SRT_SAFE_ROOT points at ``<repo>/output``, but pytest
    temporary directories live under ``/tmp``.  Patching the module-level
    constant to ``/tmp`` allows all path-validation helpers in
    ``parakeet_rocm.formatting.refine`` to accept test paths.
    """
    import parakeet_rocm.formatting.refine as refine_mod

    refine_mod.SRT_SAFE_ROOT = Path("/tmp")
