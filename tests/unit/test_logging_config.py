"""Unit tests for centralized logging configuration."""

from __future__ import annotations

import logging
import os
import sys
import types

import pytest


def test_configure_logging_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """Default logging config should set INFO and set default env vars."""
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
    assert os.environ["NEMO_LOG_LEVEL"] == "WARNING"
    assert os.environ["TRANSFORMERS_VERBOSITY"] == "warning"


def test_configure_logging_verbose(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verbose mode should set DEBUG and bump dependency verbosity."""
    import parakeet_rocm.utils.logging_config as logging_config

    calls: list[dict[str, object]] = []

    def fake_basic_config(**kwargs: object) -> None:
        calls.append(kwargs)

    monkeypatch.setattr(logging, "basicConfig", fake_basic_config)

    logging_config.configure_logging(verbose=True)

    assert calls[0]["level"] == logging.DEBUG
    assert os.environ["NEMO_LOG_LEVEL"] == "INFO"
    assert os.environ["TRANSFORMERS_VERBOSITY"] == "info"


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
    assert os.environ["NEMO_LOG_LEVEL"]
    assert os.environ["TRANSFORMERS_VERBOSITY"]

    # tqdm.tqdm should have been wrapped with functools.partial(disable=True)
    assert hasattr(tqdm_mod, "tqdm")


def test_get_logger_returns_logger() -> None:
    """get_logger should return a standard library logger."""
    from parakeet_rocm.utils.logging_config import get_logger

    logger = get_logger("parakeet_rocm.tests")
    assert isinstance(logger, logging.Logger)
