"""Unit tests for centralized logging configuration."""

from __future__ import annotations

import logging
import os
import sys
import types

import pytest


def test_configure_logging_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """Default logging config should set INFO and quiet dependency verbosity."""
    import parakeet_rocm.utils.logging_config as logging_config

    calls: list[dict[str, object]] = []

    def fake_basic_config(**kwargs: object) -> None:
        calls.append(kwargs)

    monkeypatch.setattr(logging, "basicConfig", fake_basic_config)

    monkeypatch.delenv("NEMO_LOG_LEVEL", raising=False)
    monkeypatch.delenv("TRANSFORMERS_VERBOSITY", raising=False)

    logging_config.configure_logging()

    assert calls
    assert calls[0]["level"] == logging.INFO
    assert os.getenv("NEMO_LOG_LEVEL") is None
    assert os.getenv("TRANSFORMERS_VERBOSITY") is None


def test_configure_logging__honors_env_dependency_levels(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Default mode should honor centralized dependency verbosity constants."""
    import parakeet_rocm.utils.logging_config as logging_config

    calls: list[dict[str, object]] = []

    def fake_basic_config(**kwargs: object) -> None:
        calls.append(kwargs)

    monkeypatch.setattr(logging, "basicConfig", fake_basic_config)
    monkeypatch.setenv("NEMO_LOG_LEVEL", "KEEP")
    monkeypatch.setenv("TRANSFORMERS_VERBOSITY", "keep")
    monkeypatch.setattr(logging_config, "NEMO_LOG_LEVEL", "WARNING")
    monkeypatch.setattr(logging_config, "TRANSFORMERS_VERBOSITY", "warning")

    logging_config.configure_logging()

    assert calls[0]["level"] == logging.INFO
    assert os.getenv("NEMO_LOG_LEVEL") == "KEEP"
    assert os.getenv("TRANSFORMERS_VERBOSITY") == "keep"


def test_configure_logging_verbose(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verbose mode should set DEBUG and bump dependency verbosity."""
    import parakeet_rocm.utils.logging_config as logging_config

    calls: list[dict[str, object]] = []

    def fake_basic_config(**kwargs: object) -> None:
        calls.append(kwargs)

    monkeypatch.setattr(logging, "basicConfig", fake_basic_config)

    logging_config.configure_logging(verbose=True)

    assert calls[0]["level"] == logging.DEBUG


def test_configure_logging_quiet(monkeypatch: pytest.MonkeyPatch) -> None:
    """Quiet mode should suppress warnings and disable tqdm when present."""
    import parakeet_rocm.utils.logging_config as logging_config

    calls: list[dict[str, object]] = []

    def fake_basic_config(**kwargs: object) -> None:
        calls.append(kwargs)

    monkeypatch.setattr(logging, "basicConfig", fake_basic_config)

    # Fake tqdm module so the quiet-path patches it.
    tqdm_mod = types.ModuleType("tqdm")

    def tqdm(iterable: object = None, **_kwargs: object) -> object:
        return iterable

    tqdm_mod.tqdm = tqdm
    monkeypatch.setitem(sys.modules, "tqdm", tqdm_mod)

    logging_config.configure_logging(quiet=True)

    assert calls[0]["level"] == logging.CRITICAL

    # tqdm.tqdm should have been wrapped with functools.partial(disable=True)
    assert hasattr(tqdm_mod, "tqdm")


def test_get_logger_returns_logger() -> None:
    """get_logger should return a standard library logger."""
    from parakeet_rocm.utils.logging_config import get_logger

    logger = get_logger("parakeet_rocm.tests")
    assert isinstance(logger, logging.Logger)


def test_configure_logging_suppresses_noisy_multipart_loggers() -> None:
    """Multipart parser debug internals should be clamped to WARNING level."""
    from parakeet_rocm.utils.logging_config import configure_logging

    configure_logging(level="DEBUG")

    assert logging.getLogger("python_multipart").level == logging.WARNING
    assert logging.getLogger("python_multipart.multipart").level == logging.WARNING
    assert logging.getLogger("multipart").level == logging.WARNING
