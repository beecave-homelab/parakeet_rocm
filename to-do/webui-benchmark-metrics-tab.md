# To-Do: WebUI Benchmark Metrics Tab

This plan outlines the steps to implement a Gradio WebUI tab that surfaces runtime and ROCm GPU benchmark metrics for the active and most recent transcription jobs.

## Tasks

- [ ] **Analysis Phase:**
  - [ ] Research and evaluate tools, patterns, or libraries if needed
    - Path: `parakeet_rocm/webui/`
    - Action: Assess Gradio tab patterns and session/job state handling suitable for displaying live metrics.
    - Analysis Results:
      - Review existing `build_app()` layout in `parakeet_rocm/webui/app.py` to determine where to wrap current outputs with `gr.Tabs`.
      - Inventory `JobManager` responsibilities in `parakeet_rocm/webui/core/job_manager.py`, noting where to persist runtime, GPU, and quality metrics.
      - Map transcription pipeline touchpoints in `parakeet_rocm/transcription/cli.py` and `parakeet_rocm/transcription/file_processor.py` for timing hooks and sampler lifecycle management.
      - Compare configuration constants between this repo and the reference `insanely_fast_whisper_api/benchmarks/collector.py` implementation to understand required adaptations (timezone, output directory naming, dependency availability).
    - Accept Criteria: Document a data-flow diagram showing how metrics travel from transcription execution to the WebUI, including fallback behaviour when GPU telemetry is unavailable.

- [ ] **Implementation Phase (Test-Driven Development):**
  - [ ] Draft failing tests before feature work
    - Path: `tests/benchmarks/`, `tests/webui/`
    - Action: Author red-state tests that encode expected collector outputs, job metric fields, and WebUI rendering before modifying production code.
    - Status: Pending
  - [ ] Introduce benchmark collector utilities
    - Path: `parakeet_rocm/benchmarks/collector.py`
    - Action: Port a scoped version of `BenchmarkCollector` and `GpuUtilSampler` (threaded sampler, JSON writer) with Google-style docstrings, absolute imports, and project-specific configuration constants.
    - Status: Pending
  - [ ] Extend job tracking data model
    - Path: `parakeet_rocm/webui/core/job_manager.py`
    - Action: Augment `TranscriptionJob` to store `runtime_seconds`, `total_wall_seconds`, `gpu_stats`, `format_quality`, and timestamp fields; ensure `run_job()` starts/stops the GPU sampler and attaches collector output paths.
    - Status: Pending
  - [ ] Instrument transcription pipeline
    - Path: `parakeet_rocm/transcription/cli.py`
    - Action: Measure wall-clock runtimes, propagate progress counts, and emit format-quality metrics (e.g., SRT diff placeholders) to the collector invocation.
    - Status: Pending
  - [ ] Capture per-file metrics
    - Path: `parakeet_rocm/transcription/file_processor.py`
    - Action: Gather per-file durations, segment counts, and stabilization logs needed for `format_quality` entries passed back to `JobManager`.
    - Status: Pending
  - [ ] Wire collector entrypoint
    - Path: `parakeet_rocm/transcription/__init__.py`
    - Action: Expose a helper that orchestrates collector usage so both CLI and WebUI share the same benchmarking flow.
    - Status: Pending
  - [ ] Update WebUI to surface metrics
    - Path: `parakeet_rocm/webui/app.py`
    - Action: Wrap the output section in `gr.Tabs`, add a "Benchmarks" tab with live-updating components (JSON, Markdown summaries, optional plots) that show the running job’s metrics and last completed job snapshot.
    - Status: Pending
  - [ ] Session and polling utilities
    - Path: `parakeet_rocm/webui/core/session.py`
    - Action: Add helpers for retrieving the current and previous jobs, and expose endpoints/callbacks for the WebUI polling loop.
    - Status: Pending
  - [ ] Optional persistence toggle
    - Path: `parakeet_rocm/config.py`
    - Action: Add configuration (env-backed) allowing users to enable/disable JSON benchmark persistence and GPU sampling interval adjustments.
    - Status: Pending

- [ ] **Testing Phase:**
  - [ ] Unit or integration tests
    - Path: `tests/benchmarks/test_collector.py`
    - Action: Validate slug generation, timezone handling, JSON payload structure, and GPU sampler fallback behaviour using faked `pyamdgpuinfo` responses.
    - Accept Criteria: Collector tests cover both GPU-present and GPU-absent scenarios.
  - [ ] Job manager integration tests
    - Path: `tests/webui/test_job_manager_metrics.py`
    - Action: Ensure `JobManager.run_job()` populates metrics fields and that errors still surface without leaving stray sampler threads.
    - Accept Criteria: Tests assert metrics defaults when collector disabled and confirm sampler cleanup in success/failure cases.
  - [ ] WebUI component tests
    - Path: `tests/webui/test_metrics_tab.py`
    - Action: Use `gradio.testing` to confirm the Benchmarks tab renders running and last-job payloads, including empty-state messaging.
    - Accept Criteria: Snapshot or DOM assertions verify the tab contents without affecting existing UI tests; ensure red tests become green through implementation.
  - [ ] Linting and coverage compliance
    - Path: `parakeet_rocm/`
    - Action: Run `pdm run ruff check --fix .`, `pdm run ruff format .`, and `pdm run pytest --cov=. --maxfail=1 -q` to satisfy requirements in `AGENTS.md`.
    - Accept Criteria: All lint and test commands pass locally with ≥85% coverage for touched files when applicable.

- [ ] **Documentation Phase:**
  - [ ] Update `project-overview.md` and/or README
    - Path: `project-overview.md`
    - Action: Document the Benchmarks tab workflow, JSON schema stored on disk, required dependencies (`pyamdgpuinfo`), and troubleshooting steps when GPU stats are unavailable.
    - Accept Criteria: Documentation clearly explains how to access and interpret WebUI benchmark metrics, with links to configuration flags and CLI parity.
  - [ ] Reference AGENTS.md coding standards
    - Path: `project-overview.md`
    - Action: Highlight that benchmark-related modules follow `AGENTS.md` guidance (Google docstrings, type hints, Ruff formatting) and direct contributors to the lint/test workflow.
    - Accept Criteria: Documentation explicitly links to `AGENTS.md` and outlines the enforcement commands.

## Related Files

- `parakeet_rocm/webui/app.py`
- `parakeet_rocm/webui/core/job_manager.py`
- `parakeet_rocm/transcription/cli.py`
- `parakeet_rocm/transcription/file_processor.py`
- `parakeet_rocm/transcription/__init__.py`
- `parakeet_rocm/benchmarks/collector.py`
- `tests/webui/test_metrics_tab.py`
- `tests/webui/test_job_manager_metrics.py`
- `tests/benchmarks/test_collector.py`
- `parakeet_rocm/config.py`
- `project-overview.md`

## Future Enhancements

- [ ] Persist benchmark history to disk and display a sortable table of past runs.
- [ ] Visualize GPU utilisation over time within the WebUI using line charts fed by sampler time-series data.
- [ ] Expose an API endpoint to download benchmark JSON bundles for offline analysis or integration with external dashboards.
