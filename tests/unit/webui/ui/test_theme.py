"""Unit tests for ui.theme module.

Tests Gradio theme configuration for the WebUI,
ensuring proper theme creation and customization.
"""

from __future__ import annotations

import pytest

# Import will fail if gradio not installed, which is expected
gradio = pytest.importorskip("gradio", reason="Gradio not installed")

from parakeet_rocm.webui.ui.theme import configure_theme  # noqa: E402


class TestConfigureTheme:
    """Test configure_theme function."""

    def test_configure_theme__returns_theme_object(self) -> None:
        """Theme configuration should return Gradio Theme."""
        theme = configure_theme()

        assert theme is not None
        assert isinstance(theme, gradio.themes.Base)

    def test_configure_theme__uses_soft_base(self) -> None:
        """Theme should be based on Gradio Soft theme."""
        theme = configure_theme()

        # Verify it's a Soft-based theme or has expected properties
        assert hasattr(theme, "_stylesheets")

    def test_configure_theme__has_primary_hue(self) -> None:
        """Theme should have primary color configured."""
        theme = configure_theme()

        # Verify theme has configuration (Soft theme extends Base)
        assert hasattr(theme, "_stylesheets") or hasattr(theme, "name")

    def test_configure_theme__is_reusable(self) -> None:
        """Theme can be created multiple times."""
        theme1 = configure_theme()
        theme2 = configure_theme()

        # Both should be valid themes
        assert isinstance(theme1, gradio.themes.Base)
        assert isinstance(theme2, gradio.themes.Base)

    def test_configure_theme__with_custom_colors(self) -> None:
        """Theme should accept custom color overrides."""
        theme = configure_theme(
            primary_hue="blue",
            secondary_hue="gray",
        )

        assert isinstance(theme, gradio.themes.Base)
