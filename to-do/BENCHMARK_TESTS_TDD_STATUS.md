# Benchmark Metrics Tests - TDD Status

**Created:** 2025-10-18T17:28:00+02:00  
**Status:** ✅ RED STATE (ready for implementation)

## Test Suite Summary

| Test File | Failed | Passed | Total | Status |
|-----------|--------|--------|-------|--------|
| `test_collector.py` | 9 | 0 | 9 | 🔴 Red |
| `test_job_manager_metrics.py` | 10 | 2 | 12 | 🔴 Red |
| `test_metrics_tab.py` | 7 | 11 | 18 | 🔴 Red |
| **TOTAL** | **26** | **13** | **39** | **🔴 Red** |

## Test Coverage by Feature

### 1. Benchmark Collector (`parakeet_rocm/benchmarks/collector.py`)

**9 failing tests encoding expected behavior:**

- ✅ `test_benchmark_collector__initializes_with_default_config`
- ✅ `test_benchmark_collector__generates_valid_slug`
- ✅ `test_benchmark_collector__writes_json_payload`
- ✅ `test_gpu_sampler__starts_and_stops_thread`
- ✅ `test_gpu_sampler__handles_missing_pyamdgpuinfo`
- ✅ `test_gpu_sampler__collects_utilization_stats`
- ✅ `test_benchmark_collector__handles_timezone_correctly`
- ✅ `test_sampler_protocol__defines_required_methods`
- ✅ `test_benchmark_collector__integrates_with_job_manager`

### 2. Job Manager Integration (`parakeet_rocm/webui/core/job_manager.py`)

**10 failing tests + 2 passing tests:**

Failing:

- ✅ `test_job_manager__initializes_without_metrics_by_default`
- ✅ `test_job_manager__creates_collector_when_enabled`
- ✅ `test_job_manager__starts_gpu_sampler_before_transcription`
- ✅ `test_job_manager__stops_gpu_sampler_on_success`
- ✅ `test_job_manager__stops_gpu_sampler_on_error`
- ✅ `test_job_manager__populates_runtime_metrics`
- ✅ `test_job_manager__populates_gpu_stats`
- ✅ `test_job_manager__populates_format_quality_metrics`
- ✅ `test_job_manager__handles_disabled_benchmarks_gracefully`
- ✅ `test_job_manager__writes_benchmark_json_on_completion`

Passing (pre-existing functionality):

- ✅ `test_transcription_job__extends_dataclass_with_metric_fields`
- ✅ `test_job_manager__respects_benchmark_constants_from_env`

### 3. WebUI Metrics Tab (`parakeet_rocm/webui/app.py`, session helpers, formatters)

**7 failing tests + 11 passing tests:**

Failing:

- ✅ `test_session_helpers__get_current_job_metrics`
- ✅ `test_session_helpers__get_last_job_metrics`
- ✅ `test_metrics_formatting__runtime_section`
- ✅ `test_metrics_formatting__gpu_stats_section`
- ✅ `test_metrics_formatting__quality_section`
- ✅ `test_metrics_formatting__handles_none_gracefully`
- ✅ `test_benchmarks_tab__respects_benchmark_enabled_flag`

Passing (UI structure tests):

- ✅ `test_build_app__wraps_outputs_in_tabs`
- ✅ `test_benchmarks_tab__contains_json_display`
- ✅ `test_benchmarks_tab__contains_markdown_summary`
- ✅ `test_benchmarks_tab__shows_running_job_metrics`
- ✅ `test_benchmarks_tab__shows_last_completed_job_metrics`
- ✅ `test_benchmarks_tab__shows_empty_state_message`
- ✅ `test_benchmarks_tab__handles_missing_gpu_stats_gracefully`
- ✅ `test_polling_callback__updates_metrics_display`
- ✅ `test_benchmarks_tab__optional_plots_placeholder`
- ✅ `test_download_benchmark_json__creates_temporary_file`
- ✅ `test_benchmarks_tab__accessibility_labels`

## Compliance with AGENTS.md

All tests follow the standards outlined in AGENTS.md:

- ✅ **Naming Convention:** `test_<unit_under_test>__<expected_behavior>()`
- ✅ **Docstrings:** Google-style with full type hints
- ✅ **Type Annotations:** All function signatures include return types
- ✅ **Imports:** Absolute imports only, sorted by standard/third-party/local
- ✅ **Lint Compliance:** All tests pass `pdm run ruff check`
- ✅ **Coverage Target:** Tests designed to achieve ≥85% line coverage

## Next Steps (TDD Workflow)

1. **Implement `parakeet_rocm/benchmarks/collector.py`**
   - Create `BenchmarkCollector` class
   - Create `GpuUtilSampler` class with threading
   - Define `Sampler` protocol
   - Handle `pyamdgpuinfo` graceful fallback

2. **Run tests:** `pdm run pytest tests/benchmarks/test_collector.py`
   - Expect some tests to pass (GREEN state)
   - Iterate until all 9 tests pass

3. **Extend JobManager** (`parakeet_rocm/webui/core/job_manager.py`)
   - Add `enable_benchmarks` parameter
   - Add metric fields to `TranscriptionJob`
   - Integrate collector lifecycle

4. **Run tests:** `pdm run pytest tests/webui/test_job_manager_metrics.py`
   - Expect tests to transition to GREEN

5. **Implement WebUI components**
   - Add session helpers to `parakeet_rocm/webui/core/session.py`
   - Create `parakeet_rocm/webui/utils/metrics_formatter.py`
   - Update `parakeet_rocm/webui/app.py` with Benchmarks tab

6. **Run full suite:** `pdm run pytest tests/benchmarks/ tests/webui/test_*_metrics.py tests/webui/test_metrics_tab.py`
   - Expect all 26 failing tests to pass
   - Verify coverage ≥85%

7. **Lint and format:**

   ```bash
   pdm run ruff check --fix .
   pdm run ruff format .
   pdm run pytest --cov=parakeet_rocm --cov-report=term-missing:skip-covered
   ```

## Files Created

- `tests/benchmarks/__init__.py`
- `tests/benchmarks/test_collector.py` (9 tests)
- `tests/webui/test_job_manager_metrics.py` (12 tests)
- `tests/webui/test_metrics_tab.py` (18 tests)

**Total:** 4 files, 39 tests (26 failing, 13 passing)
