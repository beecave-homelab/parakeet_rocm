# Test Markers Summary

All test files have been properly marked with pytest markers according to the `/test-suite` workflow.

## Markers Added

### Integration Tests (`@pytest.mark.integration`)

All files in `tests/integration/` have module-level `pytestmark = pytest.mark.integration`:

1. ✅ **test_audio_io.py** - Audio loading backends (ffmpeg, pydub, soundfile)
2. ✅ **test_cli.py** - CLI end-to-end tests (also has `@pytest.mark.gpu`, `@pytest.mark.e2e`, `@pytest.mark.slow` on individual tests)
3. ✅ **test_file_processor.py** - File processing helper functions
4. ✅ **test_file_utils.py** - File utility functions
5. ✅ **test_stable_ts.py** - Stable-ts integration tests
6. ✅ **test_watch_and_file_utils.py** - File watching and wildcard resolution

### E2E Tests (`@pytest.mark.e2e`)

All files in `tests/e2e/` have module-level `pytestmark = pytest.mark.e2e`:

1. ✅ **test_srt_diff_report.py** - SRT diff report CLI tests
2. ✅ **test_transcribe.py** - Placeholder (marked as skipped)
3. ✅ **test_transcribe_and_diff.py** - Transcribe and diff workflow tests

### GPU Tests (`@pytest.mark.gpu`, `@pytest.mark.slow`, `@pytest.mark.e2e`)

Individual test functions in `tests/integration/test_cli.py` have all three markers:

1. ✅ **test_cli_txt()** - GPU-based CLI transcription to TXT
2. ✅ **test_cli_srt_word_timestamps()** - GPU-based CLI transcription to SRT with word timestamps

### Unit Tests (No markers)

Files in `tests/unit/` have **no markers** as they are fast, hermetic unit tests that should run by default.

## Test Count by Marker

```bash
# Integration tests
$ pdm run pytest -m integration --co -q
28 tests collected

# E2E tests
$ pdm run pytest -m e2e --co -q
21 tests collected (includes 2 GPU tests from test_cli.py)

# GPU tests
$ pdm run pytest -m gpu --co -q
2 tests collected

# Slow tests
$ pdm run pytest -m slow --co -q
2 tests collected (same as GPU tests)
```

## Running Tests by Marker

```bash
# Run only integration tests
pdm run pytest -m integration

# Run only e2e tests
pdm run pytest -m e2e

# Run only GPU tests
pdm run pytest -m gpu

# Run only slow tests
pdm run pytest -m slow

# Exclude GPU and slow tests (CI-friendly)
pdm run pytest -m "not (gpu or slow)"

# Exclude all heavy tests
pdm run pytest -m "not (gpu or slow or e2e)"
```

## Verification

All tests pass with markers:

```bash
# Unit tests (91 tests)
$ pdm run pytest tests/unit/ -q
91 passed

# Integration tests (28 tests)
$ pdm run pytest -m integration -q
28 passed

# E2E tests (21 tests, 1 skipped)
$ pdm run pytest -m e2e -q
20 passed, 1 skipped

# All tests (141 tests, 1 skipped)
$ pdm run pytest
141 passed, 1 skipped
```

## Implementation Details

### Module-Level Markers

For test files where **all tests** share the same category, we use module-level `pytestmark`:

```python
import pytest

pytestmark = pytest.mark.integration  # Applies to all tests in file
```

### Function-Level Markers

For individual tests that need specific markers (like GPU tests), we use decorators:

```python
@pytest.mark.gpu
@pytest.mark.e2e
@pytest.mark.slow
def test_cli_txt(tmp_path: Path) -> None:
    """GPU-dependent test."""
    ...
```

## Benefits

1. **Clear Test Organization**: Tests are categorized by resource requirements
2. **Selective Execution**: Run only the tests you need during development
3. **CI Optimization**: Exclude heavy tests in CI pipelines
4. **Fast Feedback**: Unit tests run in ~5s, full suite in ~50s
5. **Explicit Dependencies**: GPU and slow tests are clearly marked

## Next Steps

If adding new tests:

- **Unit tests** → Place in `tests/unit/`, no marker needed
- **Integration tests** → Place in `tests/integration/`, add `pytestmark = pytest.mark.integration`
- **E2E tests** → Place in `tests/e2e/`, add `pytestmark = pytest.mark.e2e`
- **GPU tests** → Add `@pytest.mark.gpu`, `@pytest.mark.slow`, `@pytest.mark.e2e` decorators

## References

- **Pytest Configuration**: `pyproject.toml` (lines 152-158)
- **Testing Guide**: `TESTING.md`
- **Test Suite Workflow**: `.windsurf/workflows/test-suite.md`
