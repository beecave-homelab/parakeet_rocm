"""Unit tests for stabilization skip on cancellation."""

from __future__ import annotations

import threading
from pathlib import Path
from unittest.mock import patch

from parakeet_rocm.config import StabilizationConfig, UIConfig
from parakeet_rocm.timestamps.models import AlignedResult, Segment, Word
from parakeet_rocm.transcription.file_processor import _apply_stabilization


def test_stabilization_skipped_when_cancelled() -> None:
    """Test that stabilization is skipped when cancel_event is set."""
    # Create a simple aligned result
    words = [
        Word(word="hello", start=0.0, end=0.5, probability=0.9),
        Word(word="world", start=0.6, end=1.0, probability=0.9),
    ]
    segment = Segment(text="hello world", words=words, start=0.0, end=1.0)
    aligned_result = AlignedResult(segments=[segment], word_segments=words)

    # Create configs
    stabilization_config = StabilizationConfig(
        enabled=True, demucs=False, vad=False, vad_threshold=0.35
    )
    ui_config = UIConfig(verbose=False, quiet=True, no_progress=True)

    # Set cancel event
    cancel_event = threading.Event()
    cancel_event.set()

    # Mock the refine_word_timestamps function to track if it's called
    with patch(
        "parakeet_rocm.transcription.file_processor.refine_word_timestamps"
    ) as mock_refine:
        result = _apply_stabilization(
            aligned_result=aligned_result,
            audio_path=Path("/fake/audio.wav"),
            stabilization_config=stabilization_config,
            ui_config=ui_config,
            cancel_event=cancel_event,
        )

        # refine_word_timestamps should NOT have been called
        mock_refine.assert_not_called()

        # Result should be unchanged
        assert result is aligned_result
        assert len(result.word_segments) == 2
        assert result.word_segments[0].word == "hello"


def test_stabilization_runs_when_not_cancelled() -> None:
    """Test that stabilization runs normally when cancel_event is not set."""
    # Create a simple aligned result
    words = [
        Word(word="hello", start=0.0, end=0.5, probability=0.9),
        Word(word="world", start=0.6, end=1.0, probability=0.9),
    ]
    segment = Segment(text="hello world", words=words, start=0.0, end=1.0)
    aligned_result = AlignedResult(segments=[segment], word_segments=words)

    # Create configs
    stabilization_config = StabilizationConfig(
        enabled=True, demucs=False, vad=False, vad_threshold=0.35
    )
    ui_config = UIConfig(verbose=False, quiet=True, no_progress=True)

    # Do NOT set cancel event (None)
    cancel_event = None

    # Mock the refine_word_timestamps function
    refined_words = [
        Word(word="hello", start=0.05, end=0.55, probability=0.9),
        Word(word="world", start=0.65, end=1.05, probability=0.9),
    ]

    with patch(
        "parakeet_rocm.transcription.file_processor.refine_word_timestamps",
        return_value=refined_words,
    ) as mock_refine:
        with patch(
            "parakeet_rocm.transcription.file_processor.segment_words",
            return_value=[
                Segment(text="hello world", words=refined_words, start=0.05, end=1.05)
            ],
        ):
            result = _apply_stabilization(
                aligned_result=aligned_result,
                audio_path=Path("/fake/audio.wav"),
                stabilization_config=stabilization_config,
                ui_config=ui_config,
                cancel_event=cancel_event,
            )

            # refine_word_timestamps SHOULD have been called
            mock_refine.assert_called_once()

            # Result should be updated
            assert result.word_segments == refined_words


def test_stabilization_disabled_not_called() -> None:
    """Test that stabilization is not called when disabled in config."""
    words = [Word(word="test", start=0.0, end=0.5, probability=0.9)]
    segment = Segment(text="test", words=words, start=0.0, end=0.5)
    aligned_result = AlignedResult(segments=[segment], word_segments=words)

    # Stabilization disabled
    stabilization_config = StabilizationConfig(
        enabled=False, demucs=False, vad=False, vad_threshold=0.35
    )
    ui_config = UIConfig(verbose=False, quiet=True, no_progress=True)

    with patch(
        "parakeet_rocm.transcription.file_processor.refine_word_timestamps"
    ) as mock_refine:
        result = _apply_stabilization(
            aligned_result=aligned_result,
            audio_path=Path("/fake/audio.wav"),
            stabilization_config=stabilization_config,
            ui_config=ui_config,
            cancel_event=None,
        )

        # Should not be called when disabled
        mock_refine.assert_not_called()
        assert result is aligned_result


def test_stabilization_with_unset_cancel_event() -> None:
    """Test that stabilization runs when cancel_event exists but is not set."""
    words = [Word(word="test", start=0.0, end=0.5, probability=0.9)]
    segment = Segment(text="test", words=words, start=0.0, end=0.5)
    aligned_result = AlignedResult(segments=[segment], word_segments=words)

    stabilization_config = StabilizationConfig(
        enabled=True, demucs=False, vad=False, vad_threshold=0.35
    )
    ui_config = UIConfig(verbose=False, quiet=True, no_progress=True)

    # Create cancel event but don't set it
    cancel_event = threading.Event()

    refined_words = [Word(word="test", start=0.05, end=0.55, probability=0.9)]

    with patch(
        "parakeet_rocm.transcription.file_processor.refine_word_timestamps",
        return_value=refined_words,
    ) as mock_refine:
        with patch(
            "parakeet_rocm.transcription.file_processor.segment_words",
            return_value=[
                Segment(text="test", words=refined_words, start=0.05, end=0.55)
            ],
        ):
            result = _apply_stabilization(
                aligned_result=aligned_result,
                audio_path=Path("/fake/audio.wav"),
                stabilization_config=stabilization_config,
                ui_config=ui_config,
                cancel_event=cancel_event,
            )

            # Should be called since event is not set
            mock_refine.assert_called_once()
            assert result.word_segments == refined_words
