"""Metrics formatting utilities for WebUI display.

Provides functions for formatting benchmark metrics into human-readable
Markdown strings suitable for display in the WebUI Benchmarks tab.

Functions:
    format_runtime_section: Format runtime and wall-clock timing metrics.
    format_gpu_stats_section: Format GPU utilization and VRAM usage stats.
    format_quality_section: Format subtitle quality metrics.

Example:
    >>> runtime_md = format_runtime_section(
    ...     runtime_seconds=42.5, total_wall_seconds=45.0
    ... )
    >>> print(runtime_md)
    ### Runtime
    - **Transcription Time**: 00:42
    - **Total Time**: 00:45 (6% overhead)
"""

from __future__ import annotations

from typing import Any


def format_runtime_section(
    runtime_seconds: float | None,
    total_wall_seconds: float | None,
) -> str:
    r"""Format runtime metrics as Markdown.

    Args:
        runtime_seconds: Actual transcription time in seconds.
        total_wall_seconds: Total elapsed time including overhead.

    Returns:
        Markdown-formatted runtime section.

    Examples:
        >>> format_runtime_section(42.5, 45.0)
        '### Runtime\\n- **Transcription Time**: 00:42...'
    """
    if runtime_seconds is None or total_wall_seconds is None:
        return "### Runtime\n- **Status**: N/A\n"

    runtime_str = _format_duration(runtime_seconds)
    wall_str = _format_duration(total_wall_seconds)

    if total_wall_seconds > runtime_seconds:
        overhead_pct = (total_wall_seconds - runtime_seconds) / total_wall_seconds * 100
        overhead_str = f" ({overhead_pct:.0f}% overhead)"
    else:
        overhead_str = ""

    return (
        f"### Runtime\n"
        f"- **Transcription Time**: {runtime_str}\n"
        f"- **Total Time**: {wall_str}{overhead_str}\n"
    )


def format_gpu_stats_section(gpu_stats: dict[str, Any] | None) -> str:
    """Format GPU statistics as Markdown.

    Args:
        gpu_stats: Dictionary with utilization_percent and vram_used_mb keys.

    Returns:
        Markdown-formatted GPU stats section.

    Examples:
        >>> stats = {
        ...     "utilization_percent": {"avg": 75.2, "min": 60, "max": 90, "p95": 88},
        ...     "vram_used_mb": {"avg": 4096, "min": 3800, "max": 4200}
        ... }
        >>> print(format_gpu_stats_section(stats))
        ### GPU Statistics
        - **Utilization**: 75% avg (60-90%, p95: 88%)
        - **VRAM**: 4.0 GB avg (3.7-4.1 GB)
    """
    if not gpu_stats or not isinstance(gpu_stats, dict):
        return "### GPU Statistics\n- **Status**: GPU stats unavailable\n"

    util = gpu_stats.get("utilization_percent", {})
    vram = gpu_stats.get("vram_used_mb", {})

    lines = ["### GPU Statistics\n"]

    if util:
        avg = util.get("avg", 0)
        min_val = util.get("min", 0)
        max_val = util.get("max", 0)
        p95 = util.get("p95", 0)
        lines.append(
            f"- **Utilization**: {avg:.0f}% avg ({min_val:.0f}-{max_val:.0f}%, p95: {p95:.0f}%)\n"
        )

    if vram:
        avg_gb = vram.get("avg", 0) / 1024
        min_gb = vram.get("min", 0) / 1024
        max_gb = vram.get("max", 0) / 1024
        lines.append(f"- **VRAM**: {avg_gb:.1f} GB avg ({min_gb:.1f}-{max_gb:.1f} GB)\n")

    if not util and not vram:
        lines.append("- **Status**: No data collected\n")

    return "".join(lines)


def format_quality_section(quality: dict[str, Any] | None) -> str:
    """Format subtitle quality metrics as Markdown.

    Args:
        quality: Dictionary with segment counts and quality scores.

    Returns:
        Markdown-formatted quality section.

    Examples:
        >>> quality = {
        ...     "total_segments": 150,
        ...     "avg_duration_sec": 3.2,
        ...     "readability_score": 87.5
        ... }
        >>> print(format_quality_section(quality))
        ### Quality Metrics
        - **Segments**: 150 total
        - **Avg Duration**: 3.2s
        - **Readability Score**: 87.5/100
    """
    if not quality or not isinstance(quality, dict):
        return "### Quality Metrics\n- **Status**: N/A\n"

    lines = ["### Quality Metrics\n"]

    if "total_segments" in quality:
        lines.append(f"- **Segments**: {quality['total_segments']} total\n")

    if "avg_duration_sec" in quality:
        lines.append(f"- **Avg Duration**: {quality['avg_duration_sec']:.1f}s\n")

    if "readability_score" in quality:
        score = quality["readability_score"]
        lines.append(f"- **Readability Score**: {score:.1f}/100\n")

    if len(lines) == 1:  # Only header
        lines.append("- **Status**: No quality metrics available\n")

    return "".join(lines)


def _format_duration(seconds: float) -> str:
    """Format duration in seconds as MM:SS or HH:MM:SS.

    Args:
        seconds: Duration in seconds.

    Returns:
        Formatted time string.

    Examples:
        >>> _format_duration(42.5)
        '00:42'
        >>> _format_duration(3725.0)
        '01:02:05'
    """
    total_sec = int(seconds)
    hours = total_sec // 3600
    minutes = (total_sec % 3600) // 60
    secs = total_sec % 60

    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"
