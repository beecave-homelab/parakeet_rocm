from __future__ import annotations

from collections.abc import Sequence

import numpy as np
from numpy import typing as npt

from parakeet_rocm.timestamps.word_timestamps import get_word_timestamps


class _Tensor:
    """Represent a lightweight NumPy-backed tensor for tests.

    Args:
        arr: Sequence of numeric values used to build the tensor.
    """

    def __init__(
        self,
        arr: (Sequence[float | int] | npt.NDArray[np.float_] | npt.NDArray[np.int_]),
    ) -> None:
        self.arr = np.array(arr)

    def detach(self) -> _Tensor:
        """Return a detached reference of the tensor.

        Returns:
            _Tensor: The tensor instance itself.
        """
        return self

    def cpu(self) -> _Tensor:
        """Return a CPU-backed tensor reference.

        Returns:
            _Tensor: The tensor instance itself.
        """
        return self

    def numpy(
        self,
    ) -> npt.NDArray[np.floating] | npt.NDArray[np.integer]:
        """Expose the underlying NumPy array.

        Returns:
            NDArray: The wrapped NumPy array.
        """
        return self.arr


class _Hypo:
    """Contain hypothesis tensors required by `get_word_timestamps`.

    Args:
        ids: Token identifier sequence for the hypothesis.
        times: Timestamp sequence aligned with `ids`.
        offset: Start offset applied to the timestamps.
    """

    def __init__(
        self,
        ids: Sequence[int] | npt.NDArray[np.int_],
        times: Sequence[float] | npt.NDArray[np.float_],
        offset: float = 0.0,
    ) -> None:
        self.y_sequence = _Tensor(ids)
        self.timestamp = _Tensor(times)
        self.start_offset = offset


class _Tokenizer:
    """Provide a minimal tokenizer implementation for the tests."""

    mapping = {0: "▁hello", 1: "▁world"}

    def ids_to_tokens(self, ids: Sequence[int]) -> list[str]:
        """Convert identifiers to token strings.

        Args:
            ids: Sequence of token identifiers.

        Returns:
            list[str]: Token strings mapped from the identifiers.
        """
        return [self.mapping[i] for i in ids]

    def ids_to_text(self, ids: Sequence[int]) -> str:
        """Convert identifiers to a contiguous text string.

        Args:
            ids: Sequence of token identifiers.

        Returns:
            str: Concatenated tokens without word boundaries.
        """
        return "".join(self.mapping[i] for i in ids)


class _Model:
    """Bundle tokenizer dependencies expected by `get_word_timestamps`."""

    tokenizer = _Tokenizer()


def test_get_word_timestamps() -> None:
    """Test basic word timestamp extraction with time_stride."""
    hypos = [_Hypo([0, 1], [0.0, 1.0], 0.0)]
    words = get_word_timestamps(hypos, _Model(), time_stride=0.1)
    assert [w.word for w in words] == ["hello", "world"]


def test_get_word_timestamps_without_time_stride() -> None:
    """Test word timestamps without time_stride scaling."""
    hypos = [_Hypo([0, 1], [0.0, 1.0], 0.0)]
    words = get_word_timestamps(hypos, _Model(), time_stride=None)
    assert [w.word for w in words] == ["hello", "world"]
    # Without time_stride, timestamps are unscaled
    assert words[0].start == 0.0
    assert words[1].start == 1.0


def test_get_word_timestamps_invalid_hypothesis() -> None:
    """Test handling of hypothesis without required attributes."""

    class _InvalidHypo:
        """Invalid hypothesis lacking the attributes required by the helper."""

        pass  # Missing y_sequence and timestamp

    hypos = [_InvalidHypo(), _Hypo([0], [0.0])]
    words = get_word_timestamps(hypos, _Model(), time_stride=0.1)
    # Should skip invalid hypo and process valid one
    assert len(words) == 1
    assert words[0].word == "hello"


def test_get_word_timestamps_empty_hypotheses() -> None:
    """Test with empty hypothesis list."""
    words = get_word_timestamps([], _Model(), time_stride=0.1)
    assert words == []


def test_get_word_timestamps_deduplication() -> None:
    """Test deduplication of overlapping words from chunks."""
    # Create two hypotheses with overlapping words
    # First hypo: "hello" 0.0-10.0, "world" 10.0-10.0
    # Second hypo: "hello" 0.5-0.5 (within first hello's range, filtered)
    hypos = [
        # "hello" 0.0-10.0, "world" 10.0-10.0
        _Hypo([0, 1], [0.0, 10.0], 0.0),
        # "hello" 0.5-0.5 (within first hello's range)
        _Hypo([0], [0.5], 0.0),
    ]
    words = get_word_timestamps(hypos, _Model(), time_stride=1.0)

    # After sorting and dedup:
    # - First "hello" 0.0-10.0, last_end=10.0
    # - Second "hello" starts at 0.5, which is < 10.0 - 0.03, so skipped
    # - First "world" starts at 10.0, which is >= 10.0 - 0.03, so kept
    assert len(words) == 2
    assert words[0].word == "hello"
    assert words[1].word == "world"
