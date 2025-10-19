"""Benchmark collector and GPU telemetry utilities.

This module provides tools for capturing runtime metrics, GPU utilization stats,
and quality metrics during transcription jobs. It includes graceful fallback when
GPU telemetry dependencies are unavailable.

Classes:
    BenchmarkCollector: Main collector for aggregating and persisting metrics
    GpuUtilSampler: Threaded GPU utilization sampler
    Sampler: Protocol defining the sampler interface

Usage:
    collector = BenchmarkCollector(output_dir=Path("./benchmarks"))
    sampler = GpuUtilSampler(interval_sec=1.0)

    sampler.start()
    # ... run transcription ...
    sampler.stop()

    collector.metrics["gpu_stats"] = sampler.get_stats()
    collector.write_json()
"""

from __future__ import annotations

import json
import logging
import pathlib
import statistics
import threading
from datetime import datetime, timezone  # noqa: UP017
from typing import Any, Protocol

logger = logging.getLogger(__name__)

# Graceful import fallback per AGENTS.md § 6
try:
    import pyamdgpuinfo  # type: ignore[import-untyped]
except ModuleNotFoundError:  # pragma: no cover
    pyamdgpuinfo = None  # type: ignore[assignment]
    logger.warning(
        "pyamdgpuinfo not available; GPU telemetry will be disabled. "
        "Install with: pdm add pyamdgpuinfo"
    )


class Sampler(Protocol):
    """Protocol defining the interface for GPU samplers.

    This protocol allows alternative GPU telemetry implementations to be used
    interchangeably with the standard GpuUtilSampler.

    Methods:
        start: Begin collecting samples in background thread.
        stop: Stop collection and join thread.
        get_stats: Retrieve aggregated statistics.
    """

    def start(self) -> None:
        """Start the sampler thread."""
        ...

    def stop(self) -> None:
        """Stop the sampler thread and wait for it to finish."""
        ...

    def get_stats(self) -> dict[str, Any] | None:
        """Retrieve aggregated statistics from collected samples.

        Returns:
            Dictionary with aggregated metrics, or None if unavailable.
        """
        ...


class GpuUtilSampler:
    """Threaded GPU utilization sampler for AMD ROCm GPUs.

    Samples GPU metrics at regular intervals in a background thread and computes
    aggregated statistics (min, max, avg, percentiles).

    Attributes:
        interval_sec: Sampling interval in seconds.

    Example:
        >>> sampler = GpuUtilSampler(interval_sec=1.0)
        >>> sampler.start()
        >>> time.sleep(10)  # Run workload
        >>> sampler.stop()
        >>> stats = sampler.get_stats()
        >>> print(stats["utilization_percent"]["avg"])
    """

    def __init__(self, interval_sec: float = 1.0) -> None:
        """Initialize GPU sampler with specified interval.

        Args:
            interval_sec: Time between samples in seconds (default: 1.0).
        """
        self.interval_sec = interval_sec
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._utilization_samples: list[float] = []
        self._vram_used_samples: list[float] = []
        self._lock = threading.Lock()

    def start(self) -> None:
        """Start sampling GPU metrics in background thread.

        Does nothing if pyamdgpuinfo is unavailable.
        """
        if pyamdgpuinfo is None:
            logger.debug("Skipping GPU sampler start (pyamdgpuinfo unavailable)")
            return

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._sample_loop, daemon=True)
        self._thread.start()
        logger.debug(f"GPU sampler started (interval={self.interval_sec}s)")

    def stop(self) -> None:
        """Stop sampling and wait for thread to finish.

        Safe to call even if pyamdgpuinfo is unavailable or thread not started.
        """
        if self._thread is None:
            return

        self._stop_event.set()
        self._thread.join(timeout=5.0)
        logger.debug("GPU sampler stopped")

    def _sample_loop(self) -> None:
        """Background thread loop for collecting GPU metrics.

        Runs until stop_event is set, sampling at specified interval.
        """
        while not self._stop_event.is_set():
            try:
                gpu = pyamdgpuinfo.get_gpu(0)  # First GPU
                util = gpu.query_load()  # Returns 0-100
                vram_used_bytes = gpu.query_vram_usage()  # Returns bytes as int
                vram_used_mb = vram_used_bytes / (1024 * 1024)  # Convert to MB

                with self._lock:
                    self._utilization_samples.append(float(util))
                    self._vram_used_samples.append(float(vram_used_mb))

            except Exception as e:  # pragma: no cover
                logger.warning(f"GPU sampling error: {e}")

            self._stop_event.wait(timeout=self.interval_sec)

    def get_stats(self) -> dict[str, Any] | None:
        """Retrieve aggregated GPU statistics from collected samples.

        Computes min, max, avg, and percentiles (p50, p90, p95) for utilization
        and VRAM usage.

        Returns:
            Dictionary with aggregated metrics, or None if no samples collected
            or pyamdgpuinfo unavailable.

        Example:
            {
                "utilization_percent": {"min": 60, "max": 90, "avg": 75.2, ...},
                "vram_used_mb": {"min": 3800, "max": 4200, "avg": 4096, ...},
                "sample_count": 42
            }
        """
        if pyamdgpuinfo is None:
            return None

        with self._lock:
            if not self._utilization_samples:
                return {}

            return {
                "utilization_percent": self._compute_stats(self._utilization_samples),
                "vram_used_mb": self._compute_stats(self._vram_used_samples),
                "sample_count": len(self._utilization_samples),
            }

    @staticmethod
    def _compute_stats(samples: list[float]) -> dict[str, float]:
        """Compute statistical aggregates for a list of samples.

        Args:
            samples: List of numeric samples.

        Returns:
            Dictionary with min, max, avg, p50, p90, p95 keys.
        """
        if not samples:
            return {}

        sorted_samples = sorted(samples)
        return {
            "min": min(samples),
            "max": max(samples),
            "avg": statistics.mean(samples),
            "p50": statistics.median(samples),
            "p90": sorted_samples[int(len(sorted_samples) * 0.90)],
            "p95": sorted_samples[int(len(sorted_samples) * 0.95)],
        }


class BenchmarkCollector:
    """Collector for aggregating and persisting benchmark metrics.

    Aggregates runtime, GPU, and quality metrics for transcription jobs and
    writes them to JSON files with timestamped slugs.

    Attributes:
        output_dir: Directory where JSON benchmarks are written.
        slug: Unique identifier for this benchmark run (timestamp-based).
        metrics: Dictionary containing all collected metrics.
        timestamp: ISO-8601 timestamp when collector was created.

    Example:
        >>> collector = BenchmarkCollector(output_dir=Path("./benchmarks"))
        >>> collector.metrics["runtime_seconds"] = 42.5
        >>> collector.add_file_metrics("test.wav", 120.5, 45, 12.3)
        >>> path = collector.write_json()
    """

    def __init__(
        self, output_dir: pathlib.Path, slug: str | None = None
    ) -> None:
        """Initialize benchmark collector.

        Args:
            output_dir: Directory for writing benchmark JSON files.
            slug: Optional slug for this run (generated if not provided).
        """
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Generate slug: YYYYMMDD_HHMMSS_<name>
        now = datetime.now(tz=timezone.utc)  # noqa: UP017
        timestamp_prefix = now.strftime("%Y%m%d_%H%M%S")

        if slug:
            # Sanitize slug: replace spaces/special chars with underscores
            sanitized = slug.replace(" ", "_").replace("-", "_")
            self.slug = f"{timestamp_prefix}_{sanitized}"
        else:
            self.slug = timestamp_prefix

        self.timestamp = now.isoformat()

        # Initialize metrics structure
        self.metrics: dict[str, Any] = {
            "slug": self.slug,
            "timestamp": self.timestamp,
            "runtime_seconds": 0.0,
            "total_wall_seconds": 0.0,
            "gpu_stats": {},
            "format_quality": {},
            "files": [],
        }

        logger.debug(f"BenchmarkCollector initialized: slug={self.slug}")

    def add_file_metrics(
        self,
        filename: str,
        duration_sec: float,
        segment_count: int,
        processing_time_sec: float,
    ) -> None:
        """Add per-file metrics to the collector.

        Args:
            filename: Name of the processed file.
            duration_sec: Audio duration in seconds.
            segment_count: Number of segments/subtitles generated.
            processing_time_sec: Time spent processing this file.
        """
        file_metrics = {
            "filename": filename,
            "duration_sec": duration_sec,
            "segment_count": segment_count,
            "processing_time_sec": processing_time_sec,
        }
        self.metrics["files"].append(file_metrics)
        logger.debug(f"Added file metrics: {filename} ({duration_sec}s)")

    def write_json(self) -> pathlib.Path:
        """Write metrics to JSON file in output directory.

        Returns:
            Path to the written JSON file.
        """
        output_path = self.output_dir / f"{self.slug}.json"

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(self.metrics, f, indent=2, ensure_ascii=False)

        logger.info(f"Benchmark written: {output_path}")
        return output_path
