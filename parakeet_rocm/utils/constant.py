"""Project-wide constants for convenient reuse."""

# pylint: disable=line-too-long

from __future__ import annotations

import os
import pathlib
import sys
from typing import Final

from parakeet_rocm.utils.env_loader import load_project_env

# Ensure .env is loaded exactly once at import time for the whole project
if "pytest" not in sys.modules:
    load_project_env()


# Repository root resolved relative to this file (utils/constant.py → package → repo)
REPO_ROOT: Final[pathlib.Path] = pathlib.Path(__file__).resolve().parents[2]

# Default path of the dotenv file containing runtime overrides
ENV_FILE: Final[pathlib.Path] = REPO_ROOT / ".env"

# Default safe root for subtitle I/O confinement
SRT_SAFE_ROOT: Final[pathlib.Path] = pathlib.Path(
    os.getenv("SRT_SAFE_ROOT", str(REPO_ROOT / "output"))
).resolve()

# Default audio chunk length (seconds) used for segmented inference.
# Can be overridden by CHUNK_LEN_SEC env var.
DEFAULT_CHUNK_LEN_SEC: Final[int] = int(os.getenv("CHUNK_LEN_SEC", "300"))

# Default low-latency chunk length for *pseudo-streaming* mode.
DEFAULT_STREAM_CHUNK_SEC: Final[int] = int(os.getenv("STREAM_CHUNK_SEC", "8"))

# Default batch size for model inference
DEFAULT_BATCH_SIZE: Final[int] = int(os.getenv("BATCH_SIZE", "12"))

# Default transcription feature flags (override via env)
DEFAULT_VAD: Final[bool] = os.getenv("DEFAULT_VAD", "False").lower() == "true"
DEFAULT_STABILIZE: Final[bool] = os.getenv("DEFAULT_STABILIZE", "False").lower() == "true"
DEFAULT_DEMUCS: Final[bool] = os.getenv("DEFAULT_DEMUCS", "False").lower() == "true"
DEFAULT_WORD_TIMESTAMPS: Final[bool] = (
    os.getenv("DEFAULT_WORD_TIMESTAMPS", "False").lower() == "true"
)

# Default Parakeet ASR model name (override via env)
PARAKEET_MODEL_NAME: Final[str] = os.getenv("PARAKEET_MODEL_NAME", "nvidia/parakeet-tdt-0.6b-v3")

# Prefer FFmpeg for audio decoding (1 = yes, 0 = try soundfile first)
FORCE_FFMPEG: Final[bool] = os.getenv("FORCE_FFMPEG", "1") == "1"

# Allow filenames with spaces, brackets, quotes, and other non-ASCII characters.
# Security invariants (path traversal, separators, control chars) remain enforced.
ALLOW_UNSAFE_FILENAMES: Final[bool] = os.getenv("ALLOW_UNSAFE_FILENAMES", "False").lower() == "true"

# Subtitle readability constraints (industry-standard defaults for SRT quality analysis)
# Updated to match reference implementation from insanely_fast_whisper_api
MIN_CPS: Final[float] = float(
    os.getenv("MIN_CPS", "10")
)  # Minimum CPS - below is too slow, awkward pacing
MAX_CPS: Final[float] = float(
    os.getenv("MAX_CPS", "22")
)  # Maximum CPS - above is too fast, hard to read (optimal: 15-18)
MAX_LINE_CHARS: Final[int] = int(os.getenv("MAX_LINE_CHARS", "42"))
MAX_LINES_PER_BLOCK: Final[int] = int(os.getenv("MAX_LINES_PER_BLOCK", "2"))
DISPLAY_BUFFER_SEC: Final[float] = float(
    os.getenv("DISPLAY_BUFFER_SEC", "0.2")
)  # trailing buffer after last word
MIN_SEGMENT_DURATION_SEC: Final[float] = float(
    os.getenv("MIN_SEGMENT_DURATION_SEC", "0.5")
)  # Minimum segment duration for quality analysis
MAX_SEGMENT_DURATION_SEC: Final[float] = float(
    os.getenv("MAX_SEGMENT_DURATION_SEC", "7.0")
)  # Maximum segment duration for readability

# Subtitle punctuation boundaries
BOUNDARY_CHARS: Final[str] = os.getenv("BOUNDARY_CHARS", ".?!…")
CLAUSE_CHARS: Final[str] = os.getenv("CLAUSE_CHARS", ",;:")

# Soft boundary keywords (lowercase) treated as optional breakpoints
SOFT_BOUNDARY_WORDS: Final[tuple[str, ...]] = tuple(
    w.strip().lower()
    for w in os.getenv("SOFT_BOUNDARY_WORDS", "and,but,that,which,who,where,when,while,so").split(
        ","
    )
)

# Interjection whitelist allowing stand-alone short cues
INTERJECTION_WHITELIST: Final[tuple[str, ...]] = tuple(
    w.strip().lower()
    for w in os.getenv("INTERJECTION_WHITELIST", "whoa,wow,what,oh,hey,ah").split(",")
)

# Caption block character limits
# Hard limit (two full lines using MAX_LINE_CHARS) unless overridden
MAX_BLOCK_CHARS: Final[int] = int(
    os.getenv(
        "MAX_BLOCK_CHARS",
        str(MAX_LINE_CHARS * MAX_LINES_PER_BLOCK),
    )
)
# Softer limit used when evaluating potential merges; allows slight overflow
MAX_BLOCK_CHARS_SOFT: Final[int] = int(os.getenv("MAX_BLOCK_CHARS_SOFT", "90"))

# Legacy caption segmentation thresholds (kept for backward compatibility)
SEGMENT_MAX_GAP_SEC: Final[float] = float(os.getenv("SEGMENT_MAX_GAP_SEC", "1.0"))
SEGMENT_MAX_DURATION_SEC: Final[float] = MAX_SEGMENT_DURATION_SEC  # alias
SEGMENT_MAX_WORDS: Final[int] = int(os.getenv("SEGMENT_MAX_WORDS", "40"))

# Logging configuration
NEMO_LOG_LEVEL: Final[str] = os.getenv("NEMO_LOG_LEVEL", "ERROR")
TRANSFORMERS_VERBOSITY: Final[str] = os.getenv("TRANSFORMERS_VERBOSITY", "ERROR")

# Idle unload timeout (seconds). When watching for files, unload GPU model to CPU
# after this period of inactivity to free VRAM. Can be overridden via env.
IDLE_UNLOAD_TIMEOUT_SEC: Final[int] = int(os.getenv("IDLE_UNLOAD_TIMEOUT_SEC", "300"))
# Fully clear model cache after this idle duration (seconds). Useful to reduce
# host RAM usage when the service remains idle for longer. Default 360s (6 min)
# for testing; adjust as needed for production.
IDLE_CLEAR_TIMEOUT_SEC: Final[int] = int(os.getenv("IDLE_CLEAR_TIMEOUT_SEC", "360"))

# Gradio configuration
GRADIO_SERVER_PORT: Final[int] = int(os.getenv("GRADIO_SERVER_PORT", "7861"))
GRADIO_SERVER_NAME: Final[str] = os.getenv("GRADIO_SERVER_NAME", "0.0.0.0")
GRADIO_ANALYTICS_ENABLED: Final[bool] = (
    os.getenv("GRADIO_ANALYTICS_ENABLED", "False").lower() == "true"
)

# OpenAI-compatible REST API configuration
API_ENABLED: Final[bool] = os.getenv("API_ENABLED", "True").lower() == "true"
API_CORS_ORIGINS: Final[str] = os.getenv("API_CORS_ORIGINS", "")
API_SERVER_NAME: Final[str] = os.getenv("API_SERVER_NAME", GRADIO_SERVER_NAME)
API_SERVER_PORT: Final[int] = int(os.getenv("API_SERVER_PORT", "8080"))

# Gradio WebUI theme colors
WEBUI_PRIMARY_HUE: Final[str] = os.getenv("WEBUI_PRIMARY_HUE", "blue")
WEBUI_SECONDARY_HUE: Final[str] = os.getenv("WEBUI_SECONDARY_HUE", "slate")
WEBUI_NEUTRAL_HUE: Final[str] = os.getenv("WEBUI_NEUTRAL_HUE", "slate")

# Supported audio/video file formats for transcription and WebUI
SUPPORTED_AUDIO_EXTENSIONS: Final[frozenset[str]] = frozenset({
    ".wav",
    ".mp3",
    ".flac",
    ".ogg",
    ".m4a",
    ".aac",
    ".wma",
    ".opus",
})

SUPPORTED_VIDEO_EXTENSIONS: Final[frozenset[str]] = frozenset({
    ".mp4",
    ".mkv",
    ".avi",
    ".mov",
    ".webm",
    ".flv",
    ".wmv",
})

SUPPORTED_EXTENSIONS: Final[frozenset[str]] = (
    SUPPORTED_AUDIO_EXTENSIONS | SUPPORTED_VIDEO_EXTENSIONS
)

# Benchmark collection configuration
BENCHMARK_PERSISTENCE_ENABLED: Final[bool] = (
    os.getenv("BENCHMARK_PERSISTENCE_ENABLED", "False").lower() == "true"
)
GPU_SAMPLER_INTERVAL_SEC: Final[float] = float(os.getenv("GPU_SAMPLER_INTERVAL_SEC", "1.0"))
BENCHMARK_OUTPUT_DIR: Final[pathlib.Path] = pathlib.Path(
    os.getenv("BENCHMARK_OUTPUT_DIR", "data/benchmarks")
)
