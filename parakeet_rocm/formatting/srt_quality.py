"""Compute basic quality metrics for SRT subtitle output."""

from __future__ import annotations

from typing import Any

from parakeet_rocm.utils.constant import (
    MAX_CPS,
    MAX_LINE_CHARS,
    MAX_LINES_PER_BLOCK,
    MAX_SEGMENT_DURATION_SEC,
    MIN_CPS,
    MIN_SEGMENT_DURATION_SEC,
)


def compute_srt_quality(
    segments: list[dict[str, Any]],
    srt_text: str,
) -> dict[str, Any]:
    """Compute quality metrics for SRT output.

    Args:
        segments: List of segment dictionaries with ``start``, ``end``, and ``text`` keys.
        srt_text: Rendered SRT contents.

    Returns:
        Dictionary of quality metrics suitable for benchmark output.
    """
    if not segments:
        return {
            "total_segments": 0,
            "avg_duration_sec": 0.0,
            "avg_cps": 0.0,
            "duration_ok_rate": 0.0,
            "cps_ok_rate": 0.0,
            "line_ok_rate": 0.0,
            "readability_score": 0.0,
            "score": 0.0,
            "srt_length": len(srt_text),
        }

    total_duration = 0.0
    total_cps = 0.0
    duration_ok = 0
    cps_ok = 0
    line_ok = 0

    for segment in segments:
        start = float(segment.get("start", 0.0) or 0.0)
        end = float(segment.get("end", 0.0) or 0.0)
        duration = max(end - start, 0.0)
        total_duration += duration

        text = str(segment.get("text", "") or "").strip()
        normalized_text = " ".join(text.split())
        cps_value = len(normalized_text) / max(duration, 1e-6)
        total_cps += cps_value

        if MIN_SEGMENT_DURATION_SEC <= duration <= MAX_SEGMENT_DURATION_SEC:
            duration_ok += 1
        if MIN_CPS <= cps_value <= MAX_CPS:
            cps_ok += 1

        lines = text.splitlines() or [""]
        if len(lines) <= MAX_LINES_PER_BLOCK and all(len(line) <= MAX_LINE_CHARS for line in lines):
            line_ok += 1

    total_segments = len(segments)
    avg_duration = total_duration / total_segments
    avg_cps = total_cps / total_segments
    duration_ok_rate = duration_ok / total_segments
    cps_ok_rate = cps_ok / total_segments
    line_ok_rate = line_ok / total_segments

    readability_score = 100.0 * (0.4 * duration_ok_rate + 0.4 * cps_ok_rate + 0.2 * line_ok_rate)

    return {
        "total_segments": total_segments,
        "avg_duration_sec": avg_duration,
        "avg_cps": avg_cps,
        "duration_ok_rate": duration_ok_rate,
        "cps_ok_rate": cps_ok_rate,
        "line_ok_rate": line_ok_rate,
        "readability_score": readability_score,
        "score": readability_score / 100.0,
        "srt_length": len(srt_text),
    }
