# Centralized Logging Implementation

## Overview

Implemented centralized logging configuration across the entire Parakeet-NEMO ASR codebase, providing consistent log output for CLI, WebUI, and background processes.

## Architecture

### Centralized Module: `utils/logging_config.py`

**Core Functions:**

- `configure_logging()` - Configure application-wide logging
- `get_logger(name)` - Get logger instances for modules

**Features:**

- ✅ Single source of truth for logging configuration
- ✅ Configurable log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- ✅ Manages Python logging, NeMo, and Transformers verbosity
- ✅ Support for verbose, quiet, and debug modes
- ✅ Consistent timestamp formatting

## Integration Points

### 1. **WebUI (`parakeet_rocm/webui/app.py`)**

**Startup Logging:**

```python
from parakeet_rocm.utils.logging_config import configure_logging, get_logger

# At launch
configure_logging(level="DEBUG" if debug else "INFO")
logger = get_logger(__name__)
```

**Progress Tracking:**

- ✅ Gradio `gr.Progress()` for visual feedback
- ✅ Console logs for debugging
- ✅ Step-by-step progress updates

**What You'll See:**

```txt
2025-01-16 23:15:00 - parakeet_rocm.webui.app - INFO - Starting transcription for 1 file(s)
2025-01-16 23:15:01 - parakeet_rocm.webui.app - INFO - File validation successful
2025-01-16 23:15:02 - parakeet_rocm.webui.app - INFO - Config: batch=16, chunk=30s, format=srt, stabilize=True
2025-01-16 23:15:03 - parakeet_rocm.webui.app - INFO - Job submitted with ID: abc123-def456
2025-01-16 23:15:05 - parakeet_rocm.webui.app - INFO - Processing file 1/1: audio.wav
2025-01-16 23:16:20 - parakeet_rocm.webui.app - INFO - Transcription completed! Generated 1 output file(s)
```

### 2. **CLI (`parakeet_rocm/transcription/utils.py`)**

**Backward Compatibility:**

```python
def configure_environment(verbose: bool) -> None:
    """Delegates to centralized logging_config."""
    from parakeet_rocm.utils.logging_config import configure_logging
    configure_logging(verbose=verbose)
```

Existing CLI commands work unchanged:

```bash
# Verbose mode
parakeet-rocm transcribe audio.wav --verbose

# Quiet mode
parakeet-rocm transcribe audio.wav --quiet
```

## Log Levels

| Level | When to Use | What You See |
|-------|-------------|--------------|
| **DEBUG** | Development, troubleshooting | All logs + file paths + config details |
| **INFO** | Production WebUI, monitoring | Key events + progress updates |
| **WARNING** | Issues that don't block execution | Validation errors, fallbacks |
| **ERROR** | Failures requiring attention | Transcription failures, exceptions |
| **CRITICAL** | Quiet mode | Only fatal errors |

## WebUI Modes

### Standard Mode (Default)

```bash
docker compose -f docker-compose.dev.yaml up
```

**Logs:** INFO level (key events, progress, completion)

### Debug Mode

```bash
parakeet-rocm webui --debug
```

**Logs:** DEBUG level (verbose, includes file paths, configs)

## Docker Logs

View WebUI logs in real-time:

```bash
# Follow logs
docker compose -f docker-compose.dev.yaml logs -f

# View last 100 lines
docker compose -f docker-compose.dev.yaml logs --tail=100
```

## Example Log Output

### Successful Transcription

```txt
2025-01-16 23:15:00 - parakeet_rocm.webui.app - INFO - Building Gradio WebUI application
2025-01-16 23:15:01 - parakeet_rocm.webui.app - INFO - Starting server on 0.0.0.0:7861
🚀 Launching Parakeet-NEMO WebUI on http://0.0.0.0:7861
2025-01-16 23:15:30 - parakeet_rocm.webui.app - INFO - Starting transcription for 1 file(s)
2025-01-16 23:15:31 - parakeet_rocm.webui.app - INFO - File validation successful
2025-01-16 23:15:32 - parakeet_rocm.webui.app - INFO - Config: batch=16, chunk=30s, format=srt, stabilize=True
2025-01-16 23:15:33 - parakeet_rocm.webui.app - INFO - Job submitted with ID: 7a3b9c41-4d2e-4f8b-9b3a-1e5f6a7b8c9d
2025-01-16 23:15:35 - parakeet_rocm.webui.app - INFO - Initializing transcription pipeline
2025-01-16 23:15:40 - parakeet_rocm.webui.app - INFO - Processing file 1/1: voice_sample.wav
2025-01-16 23:16:45 - parakeet_rocm.webui.app - INFO - Transcription completed! Generated 1 output file(s)
```

### Validation Error

```txt
2025-01-16 23:20:10 - parakeet_rocm.webui.app - WARNING - File validation error: Unsupported format: .xyz
```

### Fatal Error

```txt
2025-01-16 23:25:15 - parakeet_rocm.webui.app - ERROR - Transcription failed: CUDA out of memory
2025-01-16 23:25:16 - parakeet_rocm.webui.app - EXCEPTION - Unexpected error during transcription
Traceback (most recent call last):
  ...
```

## Testing

All WebUI tests passing with new logging:

```bash
pdm run pytest tests/unit/webui/test_app.py -v
# ✅ 5/5 tests passed
```

## Benefits

### Before

- ❌ No centralized logging configuration
- ❌ WebUI had no console output
- ❌ Docker logs only showed startup message
- ❌ No progress feedback except Gradio spinner
- ❌ Inconsistent logging patterns

### After

- ✅ Single `configure_logging()` function
- ✅ WebUI logs to console (visible in Docker logs)
- ✅ Step-by-step progress updates
- ✅ Visual Gradio UI progress bar:
- 🔍 Validating uploaded files... (0%)
- ⚙️ Configuring transcription... (10%)
- 📝 Submitting transcription job... (20%)
- 🎙️ Transcribing N file(s)... (30% - most time spent here)
- ✨ Finalizing results... (95%)
- ✅ Done! (100%)
- ✅ Consistent formatting across CLI and WebUI
- ✅ Configurable verbosity (quiet/info/debug)

## Files Modified

1. **New:** `parakeet_rocm/utils/logging_config.py` - Centralized logging module
2. **Updated:** `parakeet_rocm/webui/app.py` - Added logging + progress tracking
3. **Updated:** `parakeet_rocm/transcription/utils.py` - Delegate to centralized config

## Migration Notes

For developers:

```python
# OLD (don't use)
import logging
logging.basicConfig(...)
logger = logging.getLogger(__name__)

# NEW (use this)
from parakeet_rocm.utils.logging_config import get_logger
logger = get_logger(__name__)
```

## Future Enhancements

Potential improvements:

- [ ] Add log rotation for production deployments
- [ ] Structured logging (JSON format) for log aggregation
- [ ] Per-module log level configuration
- [ ] Log streaming to external monitoring services
- [ ] WebUI log viewer component

## References

- **Main module:** `parakeet_rocm/utils/logging_config.py`
- **WebUI integration:** `parakeet_rocm/webui/app.py`
- **CLI integration:** `parakeet_rocm/transcription/utils.py`
- **Tests:** `tests/unit/webui/test_app.py`
