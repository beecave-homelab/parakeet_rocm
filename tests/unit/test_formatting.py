"""Unit tests for formatting module and FormatterSpec."""

from __future__ import annotations

from parakeet_rocm.formatting import (
    FORMATTERS,
    FormatterSpec,
    get_formatter,
    get_formatter_spec,
)
from parakeet_rocm.timestamps.models import AlignedResult, Segment


class TestFormatterSpec:
    """Tests for FormatterSpec dataclass."""

    def test_formatter_spec_creation(self) -> None:
        """Test creating a FormatterSpec instance."""

        # Arrange
        def dummy_formatter(result: AlignedResult, **kwargs: object) -> str:
            """Placeholder formatter used in tests that always returns a fixed string.

            Parameters:
                result (AlignedResult): The aligned transcription result to format (ignored).
                **kwargs: Arbitrary keyword arguments accepted for API compatibility and ignored.

            Returns:
                str: The fixed string "test".
            """
            return "test"

        # Act
        spec = FormatterSpec(
            format_func=dummy_formatter,
            requires_word_timestamps=True,
            supports_highlighting=True,
            file_extension=".test",
        )

        # Assert
        assert spec.format_func == dummy_formatter
        assert spec.requires_word_timestamps is True
        assert spec.supports_highlighting is True
        assert spec.file_extension == ".test"

    def test_formatter_spec_defaults(self) -> None:
        """Test FormatterSpec default values."""

        # Arrange
        def dummy_formatter(result: AlignedResult, **kwargs: object) -> str:
            """Placeholder formatter used in tests that always returns a fixed string.

            Parameters:
                result (AlignedResult): The aligned transcription result to format (ignored).
                **kwargs: Arbitrary keyword arguments accepted for API compatibility and ignored.

            Returns:
                str: The fixed string "test".
            """
            return "test"

        # Act
        spec = FormatterSpec(
            format_func=dummy_formatter,
            requires_word_timestamps=False,
            supports_highlighting=False,
            file_extension=".txt",
        )

        # Assert
        assert spec.requires_word_timestamps is False
        assert spec.supports_highlighting is False


class TestFormatterRegistry:
    """Tests for formatter registry functionality."""

    def test_formatters_registry_contains_all_formats(self) -> None:
        """Test that FORMATTERS registry contains all expected formats."""
        # Assert
        expected_formats = {"txt", "json", "jsonl", "csv", "tsv", "srt", "vtt"}
        assert set(FORMATTERS.keys()) == expected_formats

    def test_all_formatters_are_formatter_specs(self) -> None:
        """Test that all registry entries are FormatterSpec instances."""
        # Assert
        for format_name, spec in FORMATTERS.items():
            assert isinstance(spec, FormatterSpec), f"{format_name} is not a FormatterSpec"

    def test_srt_formatter_spec_metadata(self) -> None:
        """Test SRT formatter has correct metadata."""
        # Act
        spec = FORMATTERS["srt"]

        # Assert
        assert spec.requires_word_timestamps is True
        assert spec.supports_highlighting is True
        assert spec.file_extension == ".srt"
        assert callable(spec.format_func)

    def test_vtt_formatter_spec_metadata(self) -> None:
        """Test VTT formatter has correct metadata."""
        # Act
        spec = FORMATTERS["vtt"]

        # Assert
        assert spec.requires_word_timestamps is True
        assert spec.supports_highlighting is True
        assert spec.file_extension == ".vtt"
        assert callable(spec.format_func)

    def test_txt_formatter_spec_metadata(self) -> None:
        """Test TXT formatter has correct metadata."""
        # Act
        spec = FORMATTERS["txt"]

        # Assert
        assert spec.requires_word_timestamps is False
        assert spec.supports_highlighting is False
        assert spec.file_extension == ".txt"
        assert callable(spec.format_func)

    def test_json_formatter_spec_metadata(self) -> None:
        """Test JSON formatter has correct metadata."""
        # Act
        spec = FORMATTERS["json"]

        # Assert
        assert spec.requires_word_timestamps is False
        assert spec.supports_highlighting is False
        assert spec.file_extension == ".json"
        assert callable(spec.format_func)

    def test_get_formatter_returns_callable(self) -> None:
        """Test get_formatter returns the format function."""
        # Act
        formatter = get_formatter("srt")

        # Assert
        assert callable(formatter)

    def test_get_formatter_case_insensitive(self) -> None:
        """Test get_formatter is case-insensitive."""
        # Act
        formatter_lower = get_formatter("srt")
        formatter_upper = get_formatter("SRT")
        formatter_mixed = get_formatter("SrT")

        # Assert
        assert formatter_lower == formatter_upper == formatter_mixed

    def test_get_formatter_raises_on_unknown_format(self) -> None:
        """Test get_formatter raises ValueError for unknown format."""
        # Act & Assert
        import pytest

        with pytest.raises(ValueError, match="Unsupported format"):
            get_formatter("unknown")

    def test_get_formatter_spec_returns_spec(self) -> None:
        """Test get_formatter_spec returns FormatterSpec."""
        # Act
        spec = get_formatter_spec("srt")

        # Assert
        assert isinstance(spec, FormatterSpec)
        assert spec.requires_word_timestamps is True

    def test_get_formatter_spec_case_insensitive(self) -> None:
        """Test get_formatter_spec is case-insensitive."""
        # Act
        spec_lower = get_formatter_spec("srt")
        spec_upper = get_formatter_spec("SRT")

        # Assert
        assert spec_lower == spec_upper

    def test_get_formatter_spec_raises_on_unknown_format(self) -> None:
        """Test get_formatter_spec raises ValueError for unknown format."""
        # Act & Assert
        import pytest

        with pytest.raises(ValueError, match="Unsupported format"):
            get_formatter_spec("unknown")


class TestFormatterKwargs:
    """Tests for formatter **kwargs support."""

    def test_txt_formatter_ignores_highlight_words(self) -> None:
        """Test TXT formatter gracefully ignores highlight_words."""
        # Arrange
        result = AlignedResult(
            segments=[Segment(text="test", words=[], start=0.0, end=1.0)],
            word_segments=[],
        )
        formatter = get_formatter("txt")

        # Act - should not raise
        output = formatter(result, highlight_words=True)

        # Assert
        assert isinstance(output, str)
        assert "test" in output

    def test_json_formatter_ignores_highlight_words(self) -> None:
        """Test JSON formatter gracefully ignores highlight_words."""
        # Arrange
        result = AlignedResult(
            segments=[Segment(text="test", words=[], start=0.0, end=1.0)],
            word_segments=[],
        )
        formatter = get_formatter("json")

        # Act - should not raise
        output = formatter(result, highlight_words=True)

        # Assert
        assert isinstance(output, str)

    def test_srt_formatter_accepts_highlight_words(self) -> None:
        """Test SRT formatter accepts and uses highlight_words."""
        # Arrange
        from parakeet_rocm.timestamps.models import Word

        words = [Word(word="hello", start=0.0, end=1.0, score=0.9)]
        result = AlignedResult(
            segments=[Segment(text="hello", words=words, start=0.0, end=1.0)],
            word_segments=words,
        )
        formatter = get_formatter("srt")

        # Act
        output_plain = formatter(result, highlight_words=False)
        output_highlighted = formatter(result, highlight_words=True)

        # Assert
        assert isinstance(output_plain, str)
        assert isinstance(output_highlighted, str)
        # Highlighted version should contain <u> tags
        assert "<u>" in output_highlighted or output_highlighted != output_plain


class TestJsonlFormatter:
    """Tests for JSONL formatter specifically."""

    def test_jsonl_formatter_with_segment_instances(self) -> None:
        """Test JSONL formatter with proper Segment instances."""
        # Arrange
        from parakeet_rocm.timestamps.models import Word

        words = [Word(word="hello", start=0.0, end=1.0, score=0.9)]
        segment = Segment(text="hello world", words=words, start=0.0, end=2.0)
        result = AlignedResult(segments=[segment], word_segments=words)
        formatter = get_formatter("jsonl")

        # Act
        output = formatter(result)

        # Assert
        assert isinstance(output, str)
        lines = output.strip().split("\n")
        assert len(lines) == 1
        # Should be valid JSON
        import json

        parsed = json.loads(lines[0])
        assert parsed["text"] == "hello world"
        assert parsed["start"] == 0.0
        assert parsed["end"] == 2.0

    def test_jsonl_formatter_with_dict_segments(self) -> None:
        """Test JSONL formatter fallback for plain dict segments."""
        # Arrange
        # Create an AlignedResult with plain dicts as segments (edge case)
        result = AlignedResult(segments=[], word_segments=[])
        # Manually inject a dict segment to test fallback
        result.segments = [{"text": "test segment", "start": 0.0, "end": 1.0}]  # type: ignore[assignment]
        formatter = get_formatter("jsonl")

        # Act
        output = formatter(result)

        # Assert
        assert isinstance(output, str)
        lines = output.strip().split("\n")
        assert len(lines) == 1
        import json

        parsed = json.loads(lines[0])
        assert parsed["text"] == "test segment"
        assert parsed["start"] == 0.0
        assert parsed["end"] == 1.0

    def test_jsonl_formatter_with_multiple_segments(self) -> None:
        """Test JSONL formatter with multiple segments."""
        # Arrange
        seg1 = Segment(text="first", words=[], start=0.0, end=1.0)
        seg2 = Segment(text="second", words=[], start=1.0, end=2.0)
        result = AlignedResult(segments=[seg1, seg2], word_segments=[])
        formatter = get_formatter("jsonl")

        # Act
        output = formatter(result)

        # Assert
        lines = output.strip().split("\n")
        assert len(lines) == 2
        import json

        parsed1 = json.loads(lines[0])
        parsed2 = json.loads(lines[1])
        assert parsed1["text"] == "first"
        assert parsed2["text"] == "second"

    def test_jsonl_formatter_with_empty_result(self) -> None:
        """Test JSONL formatter with empty result."""
        # Arrange
        result = AlignedResult(segments=[], word_segments=[])
        formatter = get_formatter("jsonl")

        # Act
        output = formatter(result)

        # Assert
        assert output == ""


class TestVttFormatter:
    """Tests for VTT formatter specifically."""

    def test_vtt_formatter_without_highlighting(self) -> None:
        """Test VTT formatter without word highlighting."""
        # Arrange
        from parakeet_rocm.timestamps.models import Word

        words = [Word(word="hello", start=0.0, end=1.0, score=0.9)]
        segment = Segment(text="hello world", words=words, start=0.0, end=2.0)
        result = AlignedResult(segments=[segment], word_segments=words)
        formatter = get_formatter("vtt")

        # Act
        output = formatter(result, highlight_words=False)

        # Assert
        assert isinstance(output, str)
        assert "WEBVTT" in output
        assert "hello world" in output
        assert "<c.highlight>" not in output

    def test_vtt_formatter_with_highlighting(self) -> None:
        """Test VTT formatter with word highlighting."""
        # Arrange
        from parakeet_rocm.timestamps.models import Word

        words = [
            Word(word="hello", start=0.0, end=1.0, score=0.9),
            Word(word="world", start=1.0, end=2.0, score=0.9),
        ]
        segment = Segment(text="hello world", words=words, start=0.0, end=2.0)
        result = AlignedResult(segments=[segment], word_segments=words)
        formatter = get_formatter("vtt")

        # Act
        output = formatter(result, highlight_words=True)

        # Assert
        assert isinstance(output, str)
        assert "WEBVTT" in output
        assert "<c.highlight>hello</c.highlight>" in output
        assert "<c.highlight>world</c.highlight>" in output
