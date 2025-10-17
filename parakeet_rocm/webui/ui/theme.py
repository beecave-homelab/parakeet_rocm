"""Gradio theme configuration for WebUI.

Provides a modern, professional theme for the Parakeet-NEMO WebUI
based on Gradio's Soft theme with custom branding and colors.
"""

from __future__ import annotations

import gradio as gr


def configure_theme(
    *,
    primary_hue: str | gr.themes.Color = "blue",
    secondary_hue: str | gr.themes.Color = "slate",
    neutral_hue: str | gr.themes.Color = "slate",
    font: tuple[str, ...] | str = (
        "Inter",
        "ui-sans-serif",
        "system-ui",
        "sans-serif",
    ),
) -> gr.themes.Soft:
    """Configure and return the Gradio theme for WebUI.

    Creates a modern, professional theme based on Gradio's Soft theme
    with custom colors and typography optimized for the transcription
    workflow.

    Args:
        primary_hue: Primary color hue for interactive elements.
        secondary_hue: Secondary color hue for supporting elements.
        neutral_hue: Neutral color hue for backgrounds and borders.
        font: Font stack for the interface.

    Returns:
        Configured Gradio Soft theme ready to use.

    Examples:
        >>> theme = configure_theme()
        >>> with gr.Blocks(theme=theme) as demo:
        ...     gr.Markdown("Hello!")

        >>> # Custom colors
        >>> theme = configure_theme(primary_hue="indigo")
    """
    theme = gr.themes.Soft(
        primary_hue=primary_hue,
        secondary_hue=secondary_hue,
        neutral_hue=neutral_hue,
        font=font,
    ).set(
        # Spacing and sizing
        body_background_fill="*neutral_50",
        body_background_fill_dark="*neutral_950",
        block_background_fill="white",
        block_background_fill_dark="*neutral_900",
        block_border_width="1px",
        block_border_width_dark="1px",
        block_radius="*radius_lg",
        block_shadow="*shadow_drop_lg",
        block_shadow_dark="none",
        # Input elements
        input_background_fill="white",
        input_background_fill_dark="*neutral_800",
        input_border_width="1px",
        input_radius="*radius_md",
        # Buttons
        button_primary_background_fill="*primary_500",
        button_primary_background_fill_dark="*primary_600",
        button_primary_background_fill_hover="*primary_600",
        button_primary_background_fill_hover_dark="*primary_500",
        button_primary_text_color="white",
        button_primary_text_color_dark="white",
        button_secondary_background_fill="*neutral_100",
        button_secondary_background_fill_dark="*neutral_700",
        button_secondary_text_color="*neutral_800",
        button_secondary_text_color_dark="*neutral_100",
        # Typography
        body_text_size="*text_md",
        body_text_color="*neutral_800",
        body_text_color_dark="*neutral_100",
        # Layout
        layout_gap="*spacing_lg",
        container_radius="*radius_lg",
    )

    return theme
