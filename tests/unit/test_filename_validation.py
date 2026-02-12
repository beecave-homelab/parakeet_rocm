"""Tests for filename validation in ``_validate_filename_component``.

Covers strict mode, relaxed (``allow_unsafe``) mode, and security invariants
that must hold in **both** modes.
"""

from __future__ import annotations

import pytest

from parakeet_rocm.transcription.file_processor import _validate_filename_component


# -----------------------------------------------------------------------
# Strict mode (default) — rejects special characters
# -----------------------------------------------------------------------
class TestStrictMode:
    """Strict mode should only allow ``[A-Za-z0-9_-]`` with an optional dot segment."""

    def test_accepts_simple_name(self) -> None:
        """Simple alphanumeric names pass strict validation."""
        assert _validate_filename_component("hello_world", label="test") == "hello_world"

    def test_accepts_name_with_dot(self) -> None:
        """A single dot segment is allowed."""
        assert _validate_filename_component("file.txt", label="test") == "file.txt"

    def test_rejects_spaces(self) -> None:
        """Spaces are rejected in strict mode."""
        with pytest.raises(ValueError, match="allowlist"):
            _validate_filename_component("hello world", label="test")

    def test_rejects_brackets(self) -> None:
        """Square brackets are rejected in strict mode."""
        with pytest.raises(ValueError, match="allowlist"):
            _validate_filename_component("file[1]", label="test")

    def test_rejects_single_quotes(self) -> None:
        """Single quotes are rejected in strict mode."""
        with pytest.raises(ValueError, match="allowlist"):
            _validate_filename_component("it's", label="test")

    def test_rejects_parentheses(self) -> None:
        """Parentheses are rejected in strict mode."""
        with pytest.raises(ValueError, match="allowlist"):
            _validate_filename_component("file(1)", label="test")


# -----------------------------------------------------------------------
# Relaxed mode — allows special characters
# -----------------------------------------------------------------------
class TestRelaxedMode:
    """Relaxed mode allows spaces, brackets, quotes, and parentheses."""

    def test_allows_spaces(self) -> None:
        """Spaces are allowed in relaxed mode."""
        result = _validate_filename_component(
            "hello world",
            label="test",
            allow_unsafe=True,
        )
        assert result == "hello world"

    def test_allows_brackets(self) -> None:
        """Square brackets are allowed in relaxed mode."""
        result = _validate_filename_component(
            "file[1]",
            label="test",
            allow_unsafe=True,
        )
        assert result == "file[1]"

    def test_allows_single_quotes(self) -> None:
        """Single quotes are allowed in relaxed mode."""
        result = _validate_filename_component(
            "it's",
            label="test",
            allow_unsafe=True,
        )
        assert result == "it's"

    def test_allows_parentheses(self) -> None:
        """Parentheses are allowed in relaxed mode."""
        result = _validate_filename_component(
            "file(1)",
            label="test",
            allow_unsafe=True,
        )
        assert result == "file(1)"

    def test_allows_unicode(self) -> None:
        """Unicode characters are allowed in relaxed mode."""
        result = _validate_filename_component(
            "café",
            label="test",
            allow_unsafe=True,
        )
        assert result == "café"

    def test_allows_mixed_special_chars(self) -> None:
        """Mixed special characters pass in relaxed mode."""
        result = _validate_filename_component(
            "My File [v2] (final)",
            label="test",
            allow_unsafe=True,
        )
        assert result == "My File [v2] (final)"


# -----------------------------------------------------------------------
# Security invariants — must hold in BOTH modes
# -----------------------------------------------------------------------
class TestSecurityInvariants:
    """Security checks enforced regardless of mode."""

    @pytest.mark.parametrize("allow_unsafe", [False, True])
    def test_rejects_empty_string(self, allow_unsafe: bool) -> None:
        """Empty strings are always rejected."""
        with pytest.raises(ValueError, match="non-empty"):
            _validate_filename_component("", label="test", allow_unsafe=allow_unsafe)

    @pytest.mark.parametrize("allow_unsafe", [False, True])
    def test_rejects_forward_slash(self, allow_unsafe: bool) -> None:
        """Forward slashes are always rejected."""
        with pytest.raises(ValueError, match="directory separator"):
            _validate_filename_component("a/b", label="test", allow_unsafe=allow_unsafe)

    @pytest.mark.parametrize("allow_unsafe", [False, True])
    def test_rejects_backslash(self, allow_unsafe: bool) -> None:
        """Backslashes are always rejected."""
        with pytest.raises(ValueError, match="directory separator"):
            _validate_filename_component("a\\b", label="test", allow_unsafe=allow_unsafe)

    @pytest.mark.parametrize("allow_unsafe", [False, True])
    def test_rejects_dot(self, allow_unsafe: bool) -> None:
        """Single dot is always rejected."""
        with pytest.raises(ValueError, match="'\\.' or '\\.\\.'"):
            _validate_filename_component(".", label="test", allow_unsafe=allow_unsafe)

    @pytest.mark.parametrize("allow_unsafe", [False, True])
    def test_rejects_double_dot(self, allow_unsafe: bool) -> None:
        """Double dot is always rejected (caught by multiple-dot check)."""
        with pytest.raises(ValueError, match="more than one '\\.'"):
            _validate_filename_component("..", label="test", allow_unsafe=allow_unsafe)

    @pytest.mark.parametrize("allow_unsafe", [False, True])
    def test_rejects_multiple_dots(self, allow_unsafe: bool) -> None:
        """Multiple dots in a filename are always rejected."""
        with pytest.raises(ValueError, match="more than one '\\.'"):
            _validate_filename_component(
                "file.name.txt",
                label="test",
                allow_unsafe=allow_unsafe,
            )

    def test_rejects_control_chars_relaxed(self) -> None:
        """Control characters are rejected in relaxed mode."""
        with pytest.raises(ValueError, match="control character"):
            _validate_filename_component(
                "file\x00name",
                label="test",
                allow_unsafe=True,
            )

    def test_rejects_tab_relaxed(self) -> None:
        """Tab characters are rejected in relaxed mode."""
        with pytest.raises(ValueError, match="control character"):
            _validate_filename_component(
                "file\tname",
                label="test",
                allow_unsafe=True,
            )

    def test_rejects_del_relaxed(self) -> None:
        """DEL character (0x7F) is rejected in relaxed mode."""
        with pytest.raises(ValueError, match="control character"):
            _validate_filename_component(
                "file\x7fname",
                label="test",
                allow_unsafe=True,
            )
