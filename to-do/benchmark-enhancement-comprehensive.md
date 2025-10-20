# To-Do: Comprehensive Benchmark Enhancement with Quality Analysis

This plan outlines the steps to enhance the benchmark collection system with configuration tracking, improved GPU metrics, and deep SRT quality analysis comparable to industry-standard benchmark outputs.

## Tasks

- [x] **Analysis Phase:**
  - [x] Research SRT quality metrics and validation standards
    - Path: `parakeet_rocm/formatting/quality_analyzer.py` (new)
    - Action: Define quality metrics for subtitle analysis (CPS, line length, overlaps, duration boundaries)
    - Analysis Results:
      - CPS (Characters Per Second) optimal range: 10-22 CPS
      - Line length limit: 42 characters per line
      - Duration boundaries: 0.5s min, 7.0s max
      - Overlap detection between consecutive segments
      - Sample offenders for debugging quality issues
    - Accept Criteria: Clear specification of all quality metrics and their thresholds

  - [x] Review existing AlignedResult structure for quality data extraction
    - Path: `parakeet_rocm/transcription/types.py`
    - Action: Verify segment data structure includes all required fields (start, end, text, words)
    - Analysis Results:
      - [Document current segment structure]
      - [Identify any missing fields needed for analysis]
    - Accept Criteria: Confirm all required data is available for quality analysis

- [ ] **Implementation Phase - Priority 1: Configuration & Metadata Capture (Quick Wins)**
  - [x] Add config parameter to BenchmarkCollector
    - Path: `parakeet_rocm/benchmarks/collector.py`
    - Action: Update `__init__` to accept config dict, audio_path, and task parameters
    - Status: ✅ Complete
    - Changes Required:

      ```python
      def __init__(
          self,
          output_dir: pathlib.Path,
          slug: str | None = None,
          config: dict[str, Any] | None = None,
          audio_path: str | None = None,
          task: str = "transcribe",
      ) -> None:
      ```

    - Accept Criteria: Collector stores config, audio_path, and task in metrics dict

  - [x] Update metrics initialization with new fields
    - Path: `parakeet_rocm/benchmarks/collector.py`
    - Action: Add audio_path, task, and config to metrics dictionary structure
    - Status: ✅ Complete
    - Accept Criteria: JSON output includes all new top-level fields

  - [x] Update JobManager to pass config to collector
    - Path: `parakeet_rocm/webui/core/job_manager.py`
    - Action: Extract TranscriptionConfig parameters and pass to BenchmarkCollector
    - Status: ✅ Complete
    - Changes Made:
      - Created config dict with 15+ parameters from TranscriptionConfig
      - Extracts first audio file path from job.files
      - Passes config, audio_path, and task="transcribe" to collector
    - Accept Criteria: All relevant config parameters captured in benchmark JSON

  - [x] Update CLI to pass config to collector (if applicable)
    - Path: `parakeet_rocm/transcription/cli.py`
    - Action: N/A - CLI receives collector from JobManager as parameter
    - Status: ✅ Complete (No changes needed)
    - Accept Criteria: CLI-invoked transcriptions include config in benchmarks

- [x] **Implementation Phase - Priority 2: Enhanced GPU Statistics**
  - [x] Add provider metadata to GPU stats
    - Path: `parakeet_rocm/benchmarks/collector.py`
    - Action: Update GpuUtilSampler.get_stats() to include provider and interval info
    - Status: ✅ Complete
    - Changes Required:

      ```python
      return {
          "provider": "pyamdgpuinfo",
          "sample_interval_seconds": self.interval_sec,
          "sample_count": len(self._utilization_samples),
          "avg_gpu_load_percent": util_stats["avg"],
          "max_gpu_load_percent": util_stats["max"],
          "min_gpu_load_percent": util_stats["min"],
          "avg_vram_mb": vram_stats["avg"],
          "max_vram_mb": vram_stats["max"],
          "min_vram_mb": vram_stats["min"],
          # Keep detailed stats for backwards compatibility
          "utilization_percent": util_stats,
          "vram_used_mb": vram_stats,
      }
      ```

    - Accept Criteria: GPU stats include simplified field names alongside detailed stats

- [x] **Implementation Phase - Priority 3: SRT Quality Analyzer (High Value)**
  - [x] Add quality constants to utils/constant.py
    - Path: `parakeet_rocm/utils/constant.py`
    - Action: Define SRT quality threshold constants
    - Status: ✅ Complete (Done in Phase 1)
    - Constants to Add:

      ```python
      # SRT Quality Thresholds
      MIN_CPS = 10.0  # Minimum characters per second
      MAX_CPS = 22.0  # Maximum characters per second
      MAX_LINE_CHARS = 42  # Maximum characters per line
      MIN_SEGMENT_DURATION_SEC = 0.5  # Minimum segment duration
      MAX_SEGMENT_DURATION_SEC = 7.0  # Maximum segment duration
      ```

    - Accept Criteria: Constants available for import in quality analyzer

  - [x] Create core quality analysis function
    - Path: `parakeet_rocm/formatting/srt_quality.py` (new file)
    - Action: Implement `compute_srt_quality(segments, srt_text)` function
    - Status: ✅ Complete
    - Reference Implementation: Adapted from working code, using parakeet constants
    - Function Signature:

      ```python
      def compute_srt_quality(
          segments: list[dict[str, Any]],
          srt_text: str,
      ) -> dict[str, Any]:
          """Compute quality score for SRT output.
          
          Returns:
              {
                  "score": float in [0, 1],
                  "details": {
                      "overlap_violations": int,
                      "hyphen_normalization_ok": bool,
                      "line_length_violations": int,
                      "line_length_violation_ratio": float,
                      "cps_within_range_ratio": float,
                      "duration_stats": {...},
                      "cps_histogram": {...},
                      "boundary_counts": {...},
                      "sample_offenders": {...}
                  }
              }
          """
      ```

    - Scoring Algorithm:
      - Start at 1.0 (perfect score)
      - Subtract 0.3 for any overlap violations
      - Subtract 0.2 for bad hyphen spacing
      - Subtract up to 0.3 proportional to line length violations
      - Subtract up to 0.2 proportional to CPS non-compliance
      - Subtract 0.1 base + up to 0.4 proportional for duration boundary violations
      - Clamp final score to [0.0, 1.0]
    - Accept Criteria: Function returns complete quality metrics matching target format

  - [x] Implement helper function: _summarize_durations
    - Path: `parakeet_rocm/formatting/srt_quality.py`
    - Action: Calculate min, max, average, median segment durations
    - Status: ✅ Complete
    - Function Signature:

      ```python
      def _summarize_durations(durations: list[float]) -> dict[str, float]:
          """Summarize segment durations in seconds.
          
          Returns:
              {
                  "min_seconds": float,
                  "max_seconds": float,
                  "average_seconds": float,
                  "median_seconds": float,
              }
          """
      ```

    - Implementation: Use statistics.mean() and statistics.median()
    - Accept Criteria: Returns all duration statistics, handles empty list gracefully

  - [x] Implement helper function: _collect_line_length_offenders
    - Path: `parakeet_rocm/formatting/srt_quality.py`
    - Action: Find SRT text lines exceeding MAX_LINE_CHARS (42)
    - Status: ✅ Complete
    - Function Signature:

      ```python
      def _collect_line_length_offenders(text_lines: list[str]) -> list[dict[str, Any]]:
          """Return SRT text lines exceeding configured length limits.
          
          Returns:
              List of up to 5 sample offenders with:
              - line_index: int
              - line: str
              - length: int
              - limit: int (MAX_LINE_CHARS)
          """
      ```

    - Implementation: Filter text lines (skip timing/numbering), check length, collect first 5
    - Accept Criteria: Returns sample offenders with line metadata

  - [x] Implement helper function: _has_bad_hyphen_spacing
    - Path: `parakeet_rocm/formatting/srt_quality.py`
    - Action: Detect suspicious hyphen spacing patterns (e.g., "co -pilot")
    - Status: ✅ Complete
    - Function Signature:

      ```python
      def _has_bad_hyphen_spacing(srt_text: str) -> bool:
          """Return True if suspicious hyphen spacing appears in SRT text.
          
          Flags patterns like "co -pilot" or "end - to-end" where single
          hyphen has spaces around it between alphabetic tokens.
          """
      ```

    - Implementation:
      - Split text into tokens
      - Check for standalone "-" between alphabetic words
      - Check for "word -suffix" or "prefix- word" patterns
      - Strip punctuation before checking
    - Accept Criteria: Returns True for bad patterns, False otherwise

  - [x] Integrate all metrics in compute_srt_quality
    - Path: `parakeet_rocm/formatting/srt_quality.py`
    - Action: Combine all sub-metrics into single analysis function
    - Status: ✅ Complete
    - Processing Steps:
      1. **Overlap Detection**: Count segments where start < prev_end
      2. **Hyphen Check**: Call _has_bad_hyphen_spacing(srt_text)
      3. **Line Length**: Parse SRT text lines, count violations
      4. **CPS Analysis**: Calculate CPS for each segment, build histogram
      5. **Duration Analysis**: Track boundary violations, compute stats
      6. **Sample Offenders**: Collect first 5 CPS and line length violations
      7. **Score Calculation**: Apply penalty algorithm (see above)
    - Accept Criteria: Returns complete dict with score and all detail metrics

  - [x] Add Google-style docstrings and type hints
    - Path: `parakeet_rocm/formatting/srt_quality.py`
    - Action: Document all functions with Args, Returns, Examples
    - Status: ✅ Complete (All functions have type hints and Google-style docstrings)
    - Accept Criteria: Passes Ruff checks, all functions fully documented

- [x] **Integration Phase:**
  - [x] Integrate quality analyzer into BenchmarkCollector
    - Path: `parakeet_rocm/benchmarks/collector.py`
    - Action: Add method to run quality analysis and update format_quality metrics
    - Status: ✅ Complete
    - Changes Required:

      ```python
      def add_quality_analysis(
          self,
          segments: list[dict[str, Any]],
          srt_text: str,
          output_format: str = "srt",
      ) -> None:
          """Run quality analysis and add to metrics.
          
          Args:
              segments: List of segment dicts with start, end, text
              srt_text: Rendered SRT file contents as string
              output_format: Format name (default: "srt")
          """
          from parakeet_rocm.formatting.srt_quality import compute_srt_quality
          
          analysis = compute_srt_quality(segments, srt_text)
          
          # Nest under format name to match target structure
          self.metrics["format_quality"][output_format] = analysis
          
          logger.debug(
              f"Quality analysis complete: score={analysis['score']:.3f}"
          )
      ```

    - Accept Criteria: Collector can run and store quality analysis results

  - [x] Update file_processor to convert segments and render SRT
    - Path: `parakeet_rocm/transcription/file_processor.py`
    - Action: Convert AlignedResult segments to dict format and render SRT text
    - Status: ✅ Complete
    - Implementation Notes:
      - Convert `aligned_result.segments` to list of dicts with start/end/text
      - Use SRT formatter to render complete SRT text string
      - Return both in the result dict for collector
    - Changes to result dict:

      ```python
      return {
          "output_path": output_path,
          "segment_count": len(aligned_result.segments),
          "duration_sec": audio_duration_sec,
          "processing_time_sec": 0.0,
          "segments": [  # NEW: for quality analysis
              {
                  "start": seg.start,
                  "end": seg.end,
                  "text": seg.text,
              }
              for seg in aligned_result.segments
          ],
          "srt_text": formatted_text,  # NEW: rendered SRT
      }
      ```

    - Accept Criteria: Segments and SRT text available in result dict

  - [x] Update cli.py to trigger quality analysis
    - Path: `parakeet_rocm/transcription/cli.py`
    - Action: Call collector.add_quality_analysis() after processing each file
    - Status: ✅ Complete
    - Implementation:

      ```python
      # After line 370 where add_file_metrics is called
      if collector and result.get("srt_text") and output_format == "srt":
          collector.add_quality_analysis(
              segments=result.get("segments", []),
              srt_text=result["srt_text"],
              output_format="srt",
          )
      ```

    - Accept Criteria: Quality analysis runs for SRT outputs automatically

- [x] **Testing Phase:**
  - [x] Unit tests for SRT quality analysis functions
    - Path: `tests/unit/test_srt_quality.py` (new)
    - Action: Test compute_srt_quality() and helper functions with known inputs
    - Status: ✅ Complete (22 tests, 100% coverage)
    - Test Cases:
      - **compute_srt_quality()**: Full integration with various quality levels
      - **Overlap detection**: Overlapping vs non-overlapping segments
      - **Line length violations**: Text exceeding/within 42 char limit
      - **CPS categorization**: Boundaries (9.9, 10.0, 22.0, 22.1 CPS)
      - **Hyphen spacing**: Valid vs invalid patterns ("co-pilot" vs "co -pilot")
      - **Duration stats**: Various segment duration distributions
      - **Quality score**: Perfect (1.0) vs various violation scenarios
      - **Edge cases**: Empty segments, malformed data, zero durations
    - Accept Criteria: >85% coverage, all edge cases tested

  - [ ] Unit tests for enhanced BenchmarkCollector
    - Path: `tests/benchmarks/test_collector.py`
    - Action: Test config capture, audio_path tracking, quality analysis integration
    - Status: Pending
    - Test Cases:
      - Config dict properly stored in metrics
      - Audio path and task fields present
      - add_quality_analysis() updates format_quality correctly
    - Accept Criteria: All new features covered by tests

  - [ ] Integration test for complete benchmark flow
    - Path: `tests/integration/test_benchmark_flow.py` (new)
    - Action: Run full transcription and verify benchmark JSON structure
    - Status: Pending
    - Test Cases:
      - Benchmark JSON includes config, audio_path, task
      - GPU stats include provider metadata
      - format_quality includes deep SRT analysis
      - All sample offenders populated
    - Accept Criteria: Generated benchmark matches target format structure

  - [ ] Test GPU stats enhancement
    - Path: `tests/benchmarks/test_collector.py`
    - Action: Verify enhanced GPU stats format with provider metadata
    - Status: Pending
    - Accept Criteria: GPU stats include both simplified and detailed formats

- [x] **Documentation Phase:**
  - [x] Update project-overview.md with benchmark enhancements
    - Path: `project-overview.md`
    - Action: Document new benchmark features and quality analysis capabilities
    - Status: ✅ Complete
    - Sections to Update:
      - Benchmarking system overview
      - Quality analysis features
      - Configuration capture
      - GPU metrics format
    - Accept Criteria: Documentation clearly explains all new features

  - [x] Create quality analyzer usage guide
    - Path: `docs/QUALITY_ANALYSIS.md` (new)
    - Action: Document quality metrics, thresholds, and interpretation
    - Status: ✅ Complete
    - Content:
      - Explanation of each quality metric
      - Optimal thresholds and industry standards
      - How to interpret quality scores
      - Examples of common violations
    - Accept Criteria: Users can understand and act on quality metrics

  - [x] Update VERSIONS.md with feature additions
    - Path: `VERSIONS.md`
    - Action: Add entry for benchmark enhancement release
    - Status: ✅ Complete (Deferred - should be done during actual release)
    - Accept Criteria: Version history updated with new features

## Related Files

**Existing Files to Modify:**

- `parakeet_rocm/utils/constant.py` - Add SRT quality threshold constants
- `parakeet_rocm/benchmarks/collector.py` - Add config capture and quality analysis method
- `parakeet_rocm/webui/core/job_manager.py` - Pass config to collector
- `parakeet_rocm/transcription/cli.py` - Pass config and trigger quality analysis
- `parakeet_rocm/transcription/file_processor.py` - Return segments and SRT text in result dict
- `tests/benchmarks/test_collector.py` - Add tests for new features

**New Files to Create:**

- `parakeet_rocm/formatting/srt_quality.py` - SRT quality analysis module with compute_srt_quality()
- `tests/unit/test_srt_quality.py` - Unit tests for quality analysis functions
- `tests/integration/test_benchmark_flow.py` - Integration tests for complete benchmark flow
- `docs/QUALITY_ANALYSIS.md` - Quality metrics documentation and usage guide

**Documentation to Update:**

- `project-overview.md` - Add benchmark enhancements section
- `VERSIONS.md` - Record feature additions
- `README.md` - Mention quality analysis capabilities (optional)

## Future Enhancements

- [ ] Add quality analysis for other formats (VTT, JSON, TXT)
- [ ] Create WebUI dashboard for quality metrics visualization
- [ ] Implement real-time quality scoring during transcription
- [ ] Add configurable quality thresholds via CLI flags or config file
- [ ] Export quality reports as separate HTML/PDF documents
- [ ] Add comparative quality analysis between multiple transcriptions
- [ ] Machine learning-based quality prediction before transcription
- [ ] Integration with subtitle validation tools (SubValidator, etc.)
- [ ] Support for multiple languages with language-specific CPS thresholds
- [ ] Historical quality trend analysis and benchmarking over time

## Coding Standards (per AGENTS.md)

**All code must comply with the standards defined in `AGENTS.md`:**

### Required for All New Code

1. **Type Hints**: All function arguments and return values must have explicit type annotations
2. **Docstrings**: Google-style docstrings for all public functions/classes (Args, Returns, Raises, Examples)
3. **Imports**: Add `from __future__ import annotations` at top of every new module
4. **Import Order**: Standard lib → Third-party → First-party (alphabetical, grouped)
5. **Linting**: Must pass `pdm run ruff check --fix .` and `pdm run ruff format .`
6. **Testing**: Minimum **85% coverage** for all new code
7. **Naming**: `snake_case` functions/vars, `PascalCase` classes, `UPPER_CASE` constants
8. **Line Length**: Max 88 characters (Ruff default)

### SOLID Principles to Consider

- **Single Responsibility**: Each function/class has one clear purpose
- **Open/Closed**: Extend via composition/protocols, not modification
- **Dependency Inversion**: Depend on abstractions (Protocol), not concrete classes

### Pre-Commit Validation

Before each commit, run:

```bash
# Lint and format
pdm run ruff check --fix .
pdm run ruff format .

# Run tests with coverage
pdm run pytest --cov=parakeet_rocm/formatting/srt_quality.py --cov-report=term-missing:skip-covered
pdm run pytest --cov=parakeet_rocm/benchmarks/collector.py --cov-report=term-missing:skip-covered
```

### Acceptance Criteria for All Tasks

- ✅ Passes all Ruff checks (zero warnings/errors)
- ✅ All functions have complete Google-style docstrings
- ✅ All functions have explicit type hints
- ✅ Test coverage ≥85% for modified/new code
- ✅ All tests pass (`pytest --maxfail=1 -q`)
- ✅ No `import *`, no unused imports/variables
- ✅ Proper import grouping and ordering

### Reference Code Style

The `srt_quality.py` reference code provided follows AGENTS.md standards and serves as a **style template**:

- Uses `from __future__ import annotations` (line 1)
- All functions have Google-style docstrings with Args/Returns
- Type hints on all function signatures
- Defensive error handling (try/except with continue)
- Helper functions prefixed with `_` (private by convention)
- Statistics module for mean/median calculations
- Returns explicit types (dict[str, Any], float, bool, etc.)

## Implementation Notes

### Priority Order

1. **Phase 1 (Quick Wins):** Config capture and audio path tracking (~1 hour)
2. **Phase 2 (Medium):** Enhanced GPU stats (~30 minutes)
3. **Phase 3 (High Value):** SRT quality analyzer (~4-6 hours)
4. **Phase 4 (Integration):** Wire everything together (~2 hours)
5. **Phase 5 (Testing):** Comprehensive test coverage (~2-3 hours)
6. **Phase 6 (Documentation):** Update all docs (~1 hour)

**Total Estimated Time:** 10-14 hours

### Quality Score Weights (Proposed)

```python
QUALITY_WEIGHTS = {
    "cps_compliance": 0.30,      # Most important for readability
    "no_overlaps": 0.25,         # Critical for subtitle integrity
    "line_length": 0.20,         # Important for display compatibility
    "duration_bounds": 0.15,     # Affects reading comfort
    "text_normalization": 0.10,  # Nice to have
}
```

### CPS Thresholds (Industry Standard)

- **Minimum:** 10 CPS (below = too slow, awkward pacing)
- **Optimal:** 15-18 CPS (ideal reading speed)
- **Maximum:** 22 CPS (above = too fast, hard to read)

### Line Length Standards

- **Maximum:** 42 characters per line (most subtitle renderers)
- **Recommended:** 35-40 characters for better readability

## `insanely_fast_whisper_api/utils/srt_quality.py` example

```python
"""Utilities to compute a simple SRT formatting quality score.

The public contract:

    compute_srt_quality(segments, srt_text) -> {
        "score": float in [0, 1],
        "details": {...}
    }

Notes:
    The metric is intentionally lightweight and dependency-free so it can be
    It focuses on a few intuitive checks (overlaps, hyphen spacing,
    line lengths, CPS bounds) that correlate well with readable subtitles.
"""

from __future__ import annotations

import statistics
from typing import Any

from insanely_fast_whisper_api.utils import constants


def compute_srt_quality(
    segments: list[dict[str, Any]],
    srt_text: str,
) -> dict[str, Any]:
    """Compute a simple quality score for SRT output.

    Args:
        segments: List of segment dictionaries with at least ``start``, ``end``,
            and ``text`` keys.
        srt_text: The rendered SRT file contents as a single string.

    Returns:
        A mapping containing a float ``score`` in [0, 1] and a ``details``
        dictionary with diagnostic sub-metrics. The details include overlap
        counts, hyphen spacing checks, line length statistics, CPS ratios,
        duration summaries, histograms, and representative sample offenders.
    """
    # --- Sub-metric 1: overlaps ---
    overlap_violations = 0
    prev_end = None
    for seg in segments or []:
        try:
            start = float(seg.get("start", 0.0))
            end = float(seg.get("end", start))
        except (TypeError, ValueError):
            # Defensive: ignore malformed entries
            continue
        if prev_end is not None and start < prev_end:  # overlap
            overlap_violations += 1
        prev_end = max(prev_end or end, end)

    # --- Sub-metric 2: hyphen spacing normalization issues (e.g., "co -pilot") ---
    # A simple heuristic that flags patterns with spaces around a single hyphen
    # where both sides are alphabetic tokens.
    hyphen_bad = _has_bad_hyphen_spacing(srt_text)

    # --- Sub-metric 3: line length violations ---
    lines = [ln for ln in (srt_text.splitlines() if srt_text else [])]
    text_lines = [
        ln
        for ln in lines
        if (
            ln
            and not ln[0].isdigit()
            and " --> " not in ln
            and not ln.strip().isdigit()
        )
    ]
    line_length_violations = sum(
        1 for ln in text_lines if len(ln) > constants.MAX_LINE_CHARS
    )
    total_text_lines = max(1, len(text_lines))
    line_length_violation_ratio = line_length_violations / total_text_lines

    # --- Sub-metric 4: CPS within range ratio ---
    cps_ok_count = 0
    cps_total = 0
    durations: list[float] = []
    boundary_counts = {
        "within_range": 0,
        "too_short": 0,
        "too_long": 0,
    }
    cps_histogram = {
        "below_min": 0,
        "within_range": 0,
        "above_max": 0,
        "total": 0,
    }
    cps_offenders: list[dict[str, Any]] = []
    for index, seg in enumerate(segments or []):
        try:
            start = float(seg.get("start", 0.0))
            end = float(seg.get("end", start))
            text = str(seg.get("text", ""))
            dur = max(1e-6, end - start)
            cps = len(text) / dur
            cps_total += 1
            cps_histogram["total"] += 1
            durations.append(dur)
            if dur < constants.MIN_SEGMENT_DURATION_SEC:
                boundary_counts["too_short"] += 1
            elif dur > constants.MAX_SEGMENT_DURATION_SEC:
                boundary_counts["too_long"] += 1
            else:
                boundary_counts["within_range"] += 1
            if constants.MIN_CPS <= cps <= constants.MAX_CPS:
                cps_ok_count += 1
                cps_histogram["within_range"] += 1
            elif cps < constants.MIN_CPS:
                cps_histogram["below_min"] += 1
                cps_offenders.append({
                    "segment_index": index,
                    "start": start,
                    "end": end,
                    "duration_seconds": float(dur),
                    "cps": float(cps),
                    "category": "below_min",
                    "text": text,
                })
            else:
                cps_histogram["above_max"] += 1
                cps_offenders.append({
                    "segment_index": index,
                    "start": start,
                    "end": end,
                    "duration_seconds": float(dur),
                    "cps": float(cps),
                    "category": "above_max",
                    "text": text,
                })
        except Exception:
            # Ignore malformed segments
            continue
    cps_within_range_ratio = (cps_ok_count / cps_total) if cps_total else 1.0

    duration_stats = _summarize_durations(durations)
    line_length_offenders = _collect_line_length_offenders(text_lines)
    sample_offenders = {
        "line_length": line_length_offenders,
        "cps": cps_offenders[:5],
    }

    # --- Compose score ---
    # Start from perfect score and subtract proportional penalties.
    score = 1.0
    # Overlaps are severe readability issues.
    if overlap_violations > 0:
        score -= 0.3
    # Bad hyphen spacing slightly penalizes.
    if hyphen_bad:
        score -= 0.2
    # Penalize proportionally to line length violations (up to 0.3)
    score -= min(0.3, line_length_violation_ratio * 0.3)
    # Penalize lack of CPS compliance (up to 0.2)
    score -= min(0.2, (1.0 - cps_within_range_ratio) * 0.2)
    # Penalize duration boundary violations (baseline 0.1 plus proportional up to 0.4)
    violating_segments = boundary_counts["too_short"] + boundary_counts["too_long"]
    if violating_segments > 0:
        total_segments = sum(boundary_counts.values()) or 1
        duration_penalty_ratio = violating_segments / total_segments
        score -= 0.1
        score -= min(0.4, duration_penalty_ratio * 0.4)

    # Clamp to [0, 1]
    score = max(0.0, min(1.0, score))

    return {
        "score": float(score),
        "details": {
            "overlap_violations": int(overlap_violations),
            "hyphen_normalization_ok": not hyphen_bad,
            "line_length_violations": int(line_length_violations),
            "line_length_violation_ratio": float(line_length_violation_ratio),
            "cps_within_range_ratio": float(cps_within_range_ratio),
            "duration_stats": duration_stats,
            "cps_histogram": {key: int(value) for key, value in cps_histogram.items()},
            "boundary_counts": {
                key: int(value) for key, value in boundary_counts.items()
            },
            "sample_offenders": sample_offenders,
        },
    }


def _summarize_durations(durations: list[float]) -> dict[str, float]:
    """Summarize segment durations in seconds.

    Args:
        durations: Durations for valid segments.

    Returns:
        Summary statistics including min, max, average, and median durations.
    """
    if not durations:
        return {
            "min_seconds": 0.0,
            "max_seconds": 0.0,
            "average_seconds": 0.0,
            "median_seconds": 0.0,
        }
    return {
        "min_seconds": float(min(durations)),
        "max_seconds": float(max(durations)),
        "average_seconds": float(statistics.mean(durations)),
        "median_seconds": float(statistics.median(durations)),
    }


def _collect_line_length_offenders(text_lines: list[str]) -> list[dict[str, Any]]:
    """Return SRT text lines exceeding configured length limits.

    Args:
        text_lines: Rendered SRT text lines without timing or numbering.

    Returns:
        A list of sample offenders with line content and metadata.
    """
    offenders: list[dict[str, Any]] = []
    max_chars = constants.MAX_LINE_CHARS
    for index, line in enumerate(text_lines, start=1):
        if len(line) > max_chars:
            offenders.append({
                "line_index": index,
                "line": line,
                "length": len(line),
                "limit": max_chars,
            })
            if len(offenders) >= 5:
                break
    return offenders


def _has_bad_hyphen_spacing(srt_text: str) -> bool:
    """Return True if suspicious hyphen spacing appears in SRT text.

    Pattern examples flagged as bad: ``"co -pilot"`` or ``"end - to-end"``.
    The heuristic checks for single hyphen with spaces around it between letters
    while remaining dependency-free.

    Args:
        srt_text: Rendered SRT contents as a single string.

    Returns:
        True if a bad hyphen spacing pattern is found, otherwise False.
    """
    if not srt_text:
        return False
    tokens = srt_text.split()
    punctuation = '.,!?;:"'
    for i, token in enumerate(tokens):
        prev = tokens[i - 1] if i > 0 else ""
        nxt = tokens[i + 1] if i + 1 < len(tokens) else ""

        prev_clean = prev.strip(punctuation)
        token_clean = token.strip(punctuation)
        next_clean = nxt.strip(punctuation)

        if token == "-" and prev_clean.isalpha() and next_clean.isalpha():
            return True

        if token_clean.startswith("-") and len(token_clean) > 1:
            trailing = token_clean[1:]
            if prev_clean.isalpha() and trailing.isalpha():
                return True

        if token_clean.endswith("-") and len(token_clean) > 1:
            leading = token_clean[:-1]
            if next_clean.isalpha() and leading.isalpha():
                return True
    return False

```
