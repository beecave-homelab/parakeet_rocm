"""Unit tests for cancellation in batch transcription loop."""

from __future__ import annotations

import threading
import time
from typing import Any
from unittest.mock import MagicMock

import pytest

from parakeet_rocm.transcription.file_processor import _transcribe_batches


class MockModel:
    """Mock ASR model that sleeps to simulate long processing."""

    def __init__(self, sleep_per_batch: float = 0.1) -> None:
        """Initialize mock model.

        Args:
            sleep_per_batch: Time to sleep per batch in seconds.
        """
        self.sleep_per_batch = sleep_per_batch
        self.batches_processed = 0

    def transcribe(
        self,
        *,
        audio: list[Any],
        batch_size: int,
        return_hypotheses: bool,
        verbose: bool,
    ) -> list[Any]:
        """Mock transcribe method that sleeps.

        Args:
            audio: Batch of audio arrays.
            batch_size: Effective batch size.
            return_hypotheses: Whether to return hypothesis objects.
            verbose: Verbosity flag.

        Returns:
            List of mock hypothesis objects or strings.
        """
        time.sleep(self.sleep_per_batch)
        self.batches_processed += 1

        if return_hypotheses:
            # Return mock hypothesis objects
            return [MagicMock(text=f"batch_{self.batches_processed}_{i}") for i in range(len(audio))]
        return [f"batch_{self.batches_processed}_{i}" for i in range(len(audio))]


def test_cancellation_stops_batch_processing() -> None:
    """Test that setting cancel_event stops batch processing early."""
    # Create mock model that sleeps 0.1s per batch
    model = MockModel(sleep_per_batch=0.1)

    # Create 10 segments (will be processed in batches of 2)
    segments = [(f"audio_{i}", i * 10) for i in range(10)]

    # Create cancel event
    cancel_event = threading.Event()

    # Create mock progress
    progress = MagicMock()

    # Schedule cancellation after 0.25s (should allow ~2 batches)
    def set_cancel() -> None:
        time.sleep(0.25)
        cancel_event.set()

    cancel_thread = threading.Thread(target=set_cancel, daemon=True)
    cancel_thread.start()

    # Run transcription with batch_size=2
    hypotheses, texts = _transcribe_batches(
        model=model,
        segments=segments,
        batch_size=2,
        word_timestamps=False,
        progress=progress,
        main_task=None,
        no_progress=True,
        progress_callback=None,
        cancel_event=cancel_event,
    )

    # Wait for cancel thread to finish
    cancel_thread.join(timeout=1.0)

    # Should have processed fewer than all batches
    assert model.batches_processed < 5, (
        f"Expected fewer than 5 batches, got {model.batches_processed}"
    )

    # Should have some results but not all
    assert len(texts) < 10, f"Expected fewer than 10 results, got {len(texts)}"
    assert len(texts) > 0, "Expected at least some results"


def test_no_cancellation_processes_all_batches() -> None:
    """Test that without cancellation, all batches are processed."""
    model = MockModel(sleep_per_batch=0.01)
    segments = [(f"audio_{i}", i * 10) for i in range(6)]

    progress = MagicMock()

    hypotheses, texts = _transcribe_batches(
        model=model,
        segments=segments,
        batch_size=2,
        word_timestamps=False,
        progress=progress,
        main_task=None,
        no_progress=True,
        progress_callback=None,
        cancel_event=None,
    )

    # All batches should be processed
    assert model.batches_processed == 3
    assert len(texts) == 6


def test_immediate_cancellation_processes_no_batches() -> None:
    """Test that pre-set cancel_event prevents any batch processing."""
    model = MockModel(sleep_per_batch=0.01)
    segments = [(f"audio_{i}", i * 10) for i in range(6)]

    # Set cancel event before starting
    cancel_event = threading.Event()
    cancel_event.set()

    progress = MagicMock()

    hypotheses, texts = _transcribe_batches(
        model=model,
        segments=segments,
        batch_size=2,
        word_timestamps=False,
        progress=progress,
        main_task=None,
        no_progress=True,
        progress_callback=None,
        cancel_event=cancel_event,
    )

    # No batches should be processed
    assert model.batches_processed == 0
    assert len(texts) == 0
    assert len(hypotheses) == 0


def test_cancellation_with_word_timestamps() -> None:
    """Test cancellation works correctly with word_timestamps=True."""
    model = MockModel(sleep_per_batch=0.1)
    segments = [(f"audio_{i}", i * 10) for i in range(8)]

    cancel_event = threading.Event()

    # Schedule cancellation after 0.15s
    def set_cancel() -> None:
        time.sleep(0.15)
        cancel_event.set()

    cancel_thread = threading.Thread(target=set_cancel, daemon=True)
    cancel_thread.start()

    progress = MagicMock()

    hypotheses, texts = _transcribe_batches(
        model=model,
        segments=segments,
        batch_size=2,
        word_timestamps=True,
        progress=progress,
        main_task=None,
        no_progress=True,
        progress_callback=None,
        cancel_event=cancel_event,
    )

    cancel_thread.join(timeout=1.0)

    # Should have some hypotheses but not all
    assert len(hypotheses) < 8
    assert len(hypotheses) > 0
    # texts should be empty when word_timestamps=True
    assert len(texts) == 0
