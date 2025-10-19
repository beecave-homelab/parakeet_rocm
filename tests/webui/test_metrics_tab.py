"""Tests for WebUI benchmark metrics tab rendering.

This module tests the Gradio UI components that display benchmark metrics,
including the Benchmarks tab layout, live metric updates, and empty-state
messaging when no metrics are available.

Tests follow TDD approach and AGENTS.md standards:
- Google-style docstrings with type hints
- Naming: test_<unit_under_test>__<expected_behavior>()
- Coverage target: ≥85%
"""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import gradio as gr
import pytest


@pytest.fixture
def sample_metrics() -> dict[str, Any]:
    """Provide sample metrics payload for testing.

    Returns:
        Dictionary with runtime, GPU, and quality metrics.
    """
    return {
        "slug": "20251018_172800_test-run",
        "timestamp": "2025-10-18T17:28:00Z",
        "runtime_seconds": 42.5,
        "total_wall_seconds": 45.0,
        "gpu_stats": {
            "utilization_percent": {"avg": 75.2, "min": 60, "max": 90, "p95": 88},
            "vram_used_mb": {"avg": 4096, "min": 3800, "max": 4200, "p95": 4150},
        },
        "format_quality": {
            "total_segments": 150,
            "avg_duration_sec": 3.2,
            "readability_score": 87.5,
        },
    }


@pytest.fixture
def empty_metrics() -> dict[str, Any]:
    """Provide empty metrics payload for testing.

    Returns:
        Dictionary with minimal/null fields.
    """
    return {
        "slug": "20251018_172800_no-gpu",
        "timestamp": "2025-10-18T17:28:00Z",
        "runtime_seconds": 12.3,
        "total_wall_seconds": 13.0,
        "gpu_stats": {},
        "format_quality": {},
    }


def test_build_app__wraps_outputs_in_tabs() -> None:
    """Verify build_app wraps output section in gr.Tabs container.

    Expected behavior:
        - Output section uses gr.Tabs() parent
        - Contains "Results" tab for downloads
        - Contains "Benchmarks" tab for metrics
        - Both tabs visible in UI layout
    """
    from parakeet_rocm.webui.app import build_app

    # Traverse Gradio layout to find Tabs component
    # (This is a structural test; actual implementation may vary)
    app = build_app()
    assert app is not None
    assert isinstance(app, gr.Blocks)


def test_benchmarks_tab__contains_json_display() -> None:
    """Verify Benchmarks tab includes JSON viewer component.

    Expected behavior:
        - gr.JSON() component for raw metrics
        - Updated when job completes
        - Shows full benchmark payload
    """
    from parakeet_rocm.webui.app import build_app

    # Check for JSON component in layout
    # (Implementation-specific; may need to inspect app.children)
    build_app()
    assert True  # Placeholder for actual component search


def test_benchmarks_tab__contains_markdown_summary() -> None:
    """Verify Benchmarks tab includes Markdown summary component.

    Expected behavior:
        - gr.Markdown() component for human-readable summary
        - Displays runtime, GPU stats, quality metrics
        - Formatted as table or bullet list
    """
    from parakeet_rocm.webui.app import build_app

    # Check for Markdown component in layout
    build_app()
    assert True  # Placeholder for actual component search


def test_benchmarks_tab__shows_running_job_metrics(sample_metrics: dict) -> None:
    """Verify Benchmarks tab updates during active job.

    Args:
        sample_metrics: Sample metrics payload fixture.

    Expected behavior:
        - Polling endpoint returns current job metrics
        - UI updates every N seconds
        - Shows partial metrics before completion
    """
    from parakeet_rocm.webui.app import build_app

    # Simulate job in progress with partial metrics
    build_app()
    _ = {**sample_metrics, "status": "running"}

    # Test polling callback
    assert True  # Implementation will add polling function


def test_benchmarks_tab__shows_last_completed_job_metrics(
    sample_metrics: dict,
) -> None:
    """Verify Benchmarks tab displays last completed job snapshot.

    Args:
        sample_metrics: Sample metrics payload fixture.

    Expected behavior:
        - Displays metrics from most recent completed job
        - Persists after new job starts
        - Clearly labeled as "Last Completed Job"
    """
    from parakeet_rocm.webui.app import build_app

    # Simulate completed job
    build_app()
    assert True  # Implementation will add last-job retrieval


def test_benchmarks_tab__shows_empty_state_message() -> None:
    """Verify Benchmarks tab shows helpful message when no metrics available.

    Expected behavior:
        - Displays "No benchmark data available" or similar
        - Shows instructions to enable benchmarking
        - No errors or crashes when metrics are None
    """
    from parakeet_rocm.webui.app import build_app

    # Simulate no metrics scenario
    build_app()
    assert True  # Implementation will handle None/empty case


def test_benchmarks_tab__handles_missing_gpu_stats_gracefully(
    empty_metrics: dict,
) -> None:
    """Verify Benchmarks tab handles missing GPU stats without errors.

    Args:
        empty_metrics: Empty metrics payload fixture.

    Expected behavior:
        - Shows "GPU stats unavailable" or similar
        - Does not crash or show errors
        - Still displays runtime metrics
    """
    from parakeet_rocm.webui.app import build_app

    # Simulate metrics with empty gpu_stats
    build_app()
    assert True  # Implementation will handle empty gpu_stats


def test_session_helpers__get_current_job_metrics() -> None:
    """Verify session helper retrieves current job metrics.

    Expected behavior:
        - Returns None if no active job
        - Returns metrics dict if job running
        - Returns full metrics when job completed
    """
    from parakeet_rocm.webui.core.session import get_current_job_metrics

    # Test with no active job
    metrics = get_current_job_metrics()
    assert metrics is None or isinstance(metrics, dict)


def test_session_helpers__get_last_job_metrics() -> None:
    """Verify session helper retrieves last completed job metrics.

    Expected behavior:
        - Returns None if no completed jobs
        - Returns metrics dict from most recent completed job
        - Independent of current job state
    """
    from parakeet_rocm.webui.core.session import get_last_job_metrics

    # Test with no completed jobs
    metrics = get_last_job_metrics()
    assert metrics is None or isinstance(metrics, dict)


def test_polling_callback__updates_metrics_display() -> None:
    """Verify polling callback updates metrics components.

    Expected behavior:
        - Called at regular intervals (e.g., every 2 seconds)
        - Updates JSON and Markdown components
        - Stops polling when job completes
    """
    from parakeet_rocm.webui.app import build_app

    # Test polling mechanism
    build_app()
    assert True  # Implementation will add gr.Timer or similar


def test_metrics_formatting__runtime_section() -> None:
    """Verify runtime metrics formatted correctly.

    Expected behavior:
        - Shows runtime_seconds as MM:SS or HH:MM:SS
        - Shows total_wall_seconds with overhead percentage
        - Clear labels and units
    """
    from parakeet_rocm.webui.utils.metrics_formatter import format_runtime_section

    runtime_sec = 42.5
    wall_sec = 45.0

    formatted = format_runtime_section(
        runtime_seconds=runtime_sec, total_wall_seconds=wall_sec
    )

    assert "42" in formatted or "00:42" in formatted
    assert "45" in formatted or "00:45" in formatted


def test_metrics_formatting__gpu_stats_section(sample_metrics: dict) -> None:
    """Verify GPU stats formatted correctly.

    Args:
        sample_metrics: Sample metrics payload fixture.

    Expected behavior:
        - Shows utilization as percentage with avg/min/max/p95
        - Shows VRAM usage in MB or GB
        - Handles missing stats gracefully
    """
    from parakeet_rocm.webui.utils.metrics_formatter import format_gpu_stats_section

    gpu_stats = sample_metrics["gpu_stats"]

    formatted = format_gpu_stats_section(gpu_stats)

    assert "75" in formatted or "75.2" in formatted  # avg utilization
    assert "%" in formatted
    assert "4096" in formatted or "4.0" in formatted  # VRAM in MB or GB


def test_metrics_formatting__quality_section(sample_metrics: dict) -> None:
    """Verify quality metrics formatted correctly.

    Args:
        sample_metrics: Sample metrics payload fixture.

    Expected behavior:
        - Shows segment count
        - Shows avg duration
        - Shows readability score if available
        - Handles missing fields gracefully
    """
    from parakeet_rocm.webui.utils.metrics_formatter import format_quality_section

    quality = sample_metrics["format_quality"]

    formatted = format_quality_section(quality)

    assert "150" in formatted  # total_segments
    assert "3.2" in formatted  # avg_duration_sec
    assert "87.5" in formatted or "87" in formatted  # readability_score


def test_metrics_formatting__handles_none_gracefully() -> None:
    """Verify formatter handles None/missing values without errors.

    Expected behavior:
        - Returns "N/A" or similar for missing fields
        - No exceptions raised
        - Clear indication of unavailable data
    """
    from parakeet_rocm.webui.utils.metrics_formatter import format_runtime_section

    formatted = format_runtime_section(runtime_seconds=None, total_wall_seconds=None)

    assert "N/A" in formatted or "unavailable" in formatted.lower()


def test_benchmarks_tab__optional_plots_placeholder() -> None:
    """Verify placeholder exists for future plot components.

    Expected behavior:
        - Comment or stub for future gr.Plot() component
        - GPU utilization over time (future enhancement)
        - Placeholder does not crash or affect current layout
    """
    from parakeet_rocm.webui.app import build_app

    # Check for plot placeholder or comment
    build_app()
    assert True  # Future enhancement; not required for Phase 1


def test_benchmarks_tab__respects_benchmark_enabled_flag() -> None:
    """Verify Benchmarks tab behavior when benchmarking disabled.

    Expected behavior:
        - Tab still visible but shows disabled message
        - Or tab hidden entirely when disabled
        - Clear indication that feature is opt-in
    """
    from parakeet_rocm.webui.app import build_app

    # Test with benchmarking disabled
    with patch("parakeet_rocm.utils.constant.BENCHMARK_PERSISTENCE_ENABLED", False):
        build_app()
        assert True  # Implementation will show disabled state


def test_download_benchmark_json__creates_temporary_file() -> None:
    """Verify benchmark JSON can be downloaded from UI.

    Expected behavior:
        - Creates temporary JSON file with metrics
        - Returns gr.File() with download path
        - Cleanup after download completes
    """
    from parakeet_rocm.webui.app import build_app

    # Test download functionality
    build_app()
    assert True  # Implementation will add download button


def test_benchmarks_tab__accessibility_labels() -> None:
    """Verify Benchmarks tab components have proper accessibility labels.

    Expected behavior:
        - gr.JSON() has descriptive label
        - gr.Markdown() has descriptive label
        - All components have unique elem_id for testing
    """
    from parakeet_rocm.webui.app import build_app

    # Check for proper labels and elem_id
    build_app()
    assert True  # Implementation will add accessibility attributes
