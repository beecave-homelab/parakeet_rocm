# Test Suite Reorganization Summary

## Overview

The test suite has been reorganized to follow the `/test-suite` workflow best practices, with proper directory structure, pytest markers, and comprehensive documentation.

**Updated**: December 7, 2025 - Test counts verified and synchronized with current test suite state.

## Changes Made

### 1. Directory Structure Reorganization

**Before:**

```dir
tests/
├── integration/
│   └── test_cli.py
├── test_*.py (20+ files mixed together)
└── __init__.py
```

**After:**

```dir
tests/
├── unit/                # Fast, hermetic unit tests (56 tests)
│   ├── test_adapt_core.py
│   ├── test_chunker.py
│   ├── test_cli_unit.py
│   ├── test_config.py
│   ├── test_env_loader.py
│   ├── test_formatting.py
│   ├── test_merge.py
│   ├── test_refine.py
│   ├── test_segmentation_and_formatters.py
│   ├── test_segmentation_core.py
│   ├── test_transcription_utils.py
│   └── test_word_timestamps.py
├── integration/         # Cross-boundary tests (20 tests)
│   ├── test_audio_io.py
│   ├── test_cli.py (GPU/E2E tests)
│   ├── test_file_processor.py
│   ├── test_file_utils.py
│   ├── test_stable_ts.py
│   └── test_watch_and_file_utils.py
├── e2e/                 # End-to-end workflow tests (19 tests)
│   ├── test_srt_diff_report.py
│   ├── test_transcribe.py (placeholder, skipped)
│   └── test_transcribe_and_diff.py
├── slow/                # Resource-intensive tests (reserved)
└── __init__.py
```

### 2. Pytest Configuration Enhancements

**Added to `pyproject.toml`:**

```toml
[tool.pytest.ini_options]
addopts = ["-q", "--strict-markers"]
testpaths = ["tests/unit", "tests/integration", "tests/e2e", "tests/slow"]

# Test markers per /test-suite workflow
markers = [
  "integration: crosses filesystem, network, subprocess, or GPU boundaries",
  "slow: long-running or resource-heavy tests (>5s)",
  "e2e: full workflow smoke tests",
  "gpu: requires GPU or accelerator hardware",
]

filterwarnings = [
  "ignore::DeprecationWarning:pydantic.*",
]
```

### 3. Test Markers Implementation

**Updated `tests/integration/test_cli.py`:**

- Replaced `@pytest.mark.skipif` with proper markers
- Added `@pytest.mark.gpu`, `@pytest.mark.e2e`, `@pytest.mark.slow`
- Added comprehensive docstrings
- Added type annotations for all functions

**Example:**

```python
@pytest.mark.gpu
@pytest.mark.e2e
@pytest.mark.slow
def test_cli_txt(tmp_path: Path) -> None:
    """Smoke-test CLI transcribe to TXT output.
    
    Requires GPU hardware and loads full model pipeline.
    
    Args:
        tmp_path: Pytest fixture providing temporary directory.
    """
    if os.getenv("CI") == "true":
        pytest.skip("GPU test skipped in CI environment")
    # ...
```

### 4. Documentation

**Created `TESTING.md`:**

- Comprehensive testing guide
- Quick start commands
- Test organization principles
- Writing tests guidelines (AAA pattern, fixtures, etc.)
- Coverage goals and best practices
- GPU testing guidelines
- Debugging commands
- CI integration notes

### 5. Test Organization Principles

**Unit Tests (tests/unit/):**

- Fast, deterministic, hermetic
- No external I/O or dependencies
- Pure business logic testing
- Run by default in CI

**Integration Tests (tests/integration/):**

- Cross filesystem, subprocess, external tool boundaries
- Use `tmp_path` for isolation
- Test interactions with ffmpeg, pydub, file system
- Opt-in via marker or directory

**E2E Tests (tests/e2e/):**

- Full workflow validation
- Black-box testing
- Complete pipeline tests
- Often combined with `@pytest.mark.slow`

**GPU Tests:**

- Always marked with `@pytest.mark.gpu`
- Skip gracefully in CI
- Include proper hardware requirement documentation

## Test Execution Commands

### Fast Development Workflow

```bash
# Run only unit tests (fastest, ~5s)
pdm run pytest tests/unit/

# Run with coverage
pdm run pytest tests/unit/ --cov=parakeet_rocm --cov-report=term-missing
```

### Integration Testing

```bash
# Run integration tests
pdm run pytest tests/integration/

# Exclude GPU tests
pdm run pytest tests/integration/ -m "not gpu"
```

### Full Test Suite

```bash
# All tests (unit + integration + e2e)
pdm run pytest

# Exclude heavy tests (recommended for quick CI)
pdm run pytest -m "not (gpu or slow or e2e)"
```

### Specific Markers

```bash
# GPU tests only
pdm run pytest -m gpu

# E2E tests only
pdm run pytest -m e2e

# Integration tests only
pdm run pytest -m integration
```

## Test Count Summary

- **Total Tests**: 95
  - **Unit**: 56 tests (59%)
  - **Integration**: 20 tests (21%)
  - **E2E**: 19 tests (20%)
  - **GPU**: 2 tests (marked, skipped in CI)

## Coverage Impact

The reorganization maintains comprehensive test coverage with focused improvements:

- ✅ **Unit tests**: 56 tests covering core business logic
- ✅ **Integration tests**: 20 tests covering cross-boundary functionality
- ✅ **E2E tests**: 19 tests covering full workflows (1 skipped placeholder)
- ✅ **GPU tests**: 2 tests marked and skipped in CI environments

**Test Organization Benefits:**

- Clear separation by resource requirements and test complexity
- Fast unit test feedback (~5s execution)
- Selective execution for development workflows
- CI-optimized test subsets for different scenarios

## Benefits

### 1. **Clarity**

- Tests are organized by type and resource requirements
- Easy to understand what each test suite covers
- Clear separation of concerns

### 2. **Performance**

- Fast unit tests can run in isolation (~5s)
- Developers can skip slow/GPU tests during rapid iteration
- CI can run appropriate test subsets

### 3. **Maintainability**

- Tests follow consistent patterns (AAA, type hints, docstrings)
- Proper fixture usage and isolation
- Comprehensive documentation

### 4. **CI/CD Integration**

- GPU tests skip automatically in CI
- Markers allow selective test execution
- Fast feedback loop for developers

### 5. **Best Practices**

- Follows `/test-suite` workflow principles
- Adheres to AGENTS.md coding standards
- Comprehensive testing guide for contributors

## Migration Guide for Contributors

If you're working with existing code:

1. **Unit tests** → Place in `tests/unit/`
   - Pure logic, no I/O
   - Fast and deterministic

2. **Integration tests** → Place in `tests/integration/`
   - File system operations
   - External tool interactions
   - Add `@pytest.mark.integration`

3. **E2E tests** → Place in `tests/e2e/`
   - Full workflow tests
   - Add `@pytest.mark.e2e`

4. **GPU tests** → Place in `tests/integration/` or `tests/e2e/`
   - Add markers: `@pytest.mark.gpu`, `@pytest.mark.slow`, `@pytest.mark.e2e`
   - Include CI skip logic

## Future Enhancements

- [ ] Add property-based tests using `hypothesis`
- [ ] Implement snapshot testing for stable outputs
- [ ] Add performance benchmarking suite
- [ ] Create test fixtures package for reusable test data
- [ ] Set up parallel test execution for faster CI

## References

- **Testing Guide**: `TESTING.md`
- **Coding Standards**: `AGENTS.md`
- **Test Suite Workflow**: `.windsurf/workflows/test-suite.md`
- **Pytest Configuration**: `pyproject.toml` (lines 137-163)
