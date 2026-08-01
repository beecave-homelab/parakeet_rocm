"""WebUI icon asset locations and head markup."""

from __future__ import annotations

from pathlib import Path

WEBUI_ASSET_DIR = Path(__file__).with_name("assets")
"""Directory containing public WebUI icon assets."""

WEBUI_HEAD_HTML = """\
<link rel="icon" href="./assets/favicon.ico" sizes="any">
<link rel="icon" type="image/png" sizes="192x192" href="./assets/icon-192.png">
<link rel="apple-touch-icon" sizes="180x180" href="./assets/apple-touch-icon.png">
<link rel="manifest" href="./assets/manifest.webmanifest">
<meta name="theme-color" content="#071827">
"""
"""Route-relative icon metadata injected into the mounted Gradio page."""
