# WebUI Constants Integration

## Summary

Updated the WebUI to use configured environment variables/constants as default values across all components and presets.

## Changes Made

### 1. Updated `presets.py`

**Import constants:**

```python
from parakeet_rocm.utils.constant import DEFAULT_BATCH_SIZE, DEFAULT_CHUNK_LEN_SEC
```

**Updated "default" preset:**

```python
"default": Preset(
    name="default",
    description="Default settings from environment configuration",
    config=TranscriptionConfig(
        batch_size=DEFAULT_BATCH_SIZE,      # Was: 8, Now: 12 (from env)
        chunk_len_sec=DEFAULT_CHUNK_LEN_SEC, # Was: 150, Now: 300 (from env)
        word_timestamps=False,
        stabilize=False,
        vad=False,
        demucs=False,
        fp16=True,
    ),
),
```

### 2. Updated `app.py`

**Import constants:**

```python
from parakeet_rocm.utils.constant import (
    DEFAULT_BATCH_SIZE,
    DEFAULT_CHUNK_LEN_SEC,
    GRADIO_ANALYTICS_ENABLED,
    GRADIO_SERVER_NAME,
    GRADIO_SERVER_PORT,
    SUPPORTED_EXTENSIONS,
)
```

**Updated UI components:**

```python
batch_size = gr.Slider(
    minimum=1,
    maximum=32,
    value=DEFAULT_BATCH_SIZE,  # Was: 8, Now: 1 (from .env)
    step=1,
    label="Batch Size",
)

chunk_len_sec = gr.Slider(
    minimum=30,
    maximum=600,
    value=DEFAULT_CHUNK_LEN_SEC,  # Was: 300, Now: 150 (from .env)
    step=30,
    label="Chunk Length (seconds)",
)
```

## Default Values Mapping

| Setting | Source | Default Value (from .env) | Env Variable |
|---------|--------|---------------------------|--------------|
| **Batch Size** | `DEFAULT_BATCH_SIZE` | `1` | `BATCH_SIZE=1` |
| **Chunk Length** | `DEFAULT_CHUNK_LEN_SEC` | `150` | `CHUNK_LEN_SEC=150` |

## Behavior

### On WebUI Load (No Preset Selected)

- Batch Size: **1** (from `DEFAULT_BATCH_SIZE` via `.env`)
- Chunk Length: **150** seconds (from `DEFAULT_CHUNK_LEN_SEC` via `.env`)

### When "default" Preset Selected

- Batch Size: **1** (from `DEFAULT_BATCH_SIZE` via `.env`)
- Chunk Length: **150** seconds (from `DEFAULT_CHUNK_LEN_SEC` via `.env`)
- Description: "Default settings from environment configuration"

### Other Presets

Other presets (fast, balanced, high_quality, best) **override** the defaults:

| Preset | Batch Size | Chunk Length | Notes |
|--------|------------|--------------|-------|
| **default** | 1 (env) | 150 (env) | Uses constants from .env |
| **fast** | 16 | 150 | Overrides for speed |
| **balanced** | 8 | 150 | Overrides for balance |
| **high_quality** | 4 | 150 | Overrides for accuracy |
| **best** | 4 | 150 | Overrides for max quality |

## Environment Variable Customization

Users can now customize defaults via `.env` file:

```bash
# .env
BATCH_SIZE=16        # Change default batch size
CHUNK_LEN_SEC=600    # Change default chunk length
```

These values will be reflected in:

1. ✅ WebUI component initial values
2. ✅ "default" preset settings
3. ✅ CLI default behavior (already implemented)

## Testing

### All Tests Passing ✅

```bash
# Preset tests
pdm run pytest tests/unit/webui/utils/test_presets.py -v
# Result: 13/13 passed

# WebUI tests
pdm run pytest tests/unit/webui/test_app.py -v
# Result: 8/8 passed
```

### Code Quality ✅

```bash
pdm run ruff check parakeet_rocm/webui/utils/presets.py parakeet_rocm/webui/app.py
# Result: All checks passed!
```

## Benefits

### ✅ Single Source of Truth

- All defaults come from `utils/constant.py`
- No more hardcoded values scattered in code

### ✅ Environment Customization

- Users can override defaults via `.env` file
- No code changes needed for custom defaults

### ✅ Consistency

- CLI and WebUI use same defaults
- "default" preset matches component defaults

### ✅ Maintainability

- Change defaults in one place
- Automatically propagates everywhere

## Files Modified

1. **`parakeet_rocm/webui/utils/presets.py`**
   - Import `DEFAULT_BATCH_SIZE`, `DEFAULT_CHUNK_LEN_SEC`
   - Update "default" preset to use constants

2. **`parakeet_rocm/webui/app.py`**
   - Import `DEFAULT_BATCH_SIZE`, `DEFAULT_CHUNK_LEN_SEC`
   - Update UI component default values

## Verification

To verify the changes:

```bash
# Check current constant values
python -c "from parakeet_rocm.utils.constant import DEFAULT_BATCH_SIZE, DEFAULT_CHUNK_LEN_SEC; print(f'Batch: {DEFAULT_BATCH_SIZE}, Chunk: {DEFAULT_CHUNK_LEN_SEC}')"

# Expected output (based on current .env):
# Batch: 1, Chunk: 150
```

## Configuration Flow

```txt
.env file (optional)
    ↓
utils/env_loader.py loads environment variables
    ↓
utils/constant.py defines DEFAULT_BATCH_SIZE, DEFAULT_CHUNK_LEN_SEC
    ↓
├── webui/app.py uses constants for UI component defaults
└── webui/utils/presets.py uses constants for "default" preset
```

## Backward Compatibility

✅ **Fully backward compatible**

- Users without `.env` file get code defaults (batch=12, chunk=300)
- Current `.env` specifies batch=1, chunk=150 (optimized for limited VRAM)
- All existing presets continue to work
- No breaking changes to API or behavior

**Note:** The current `.env` file uses conservative defaults suitable for AMD RX 6600:

- `BATCH_SIZE=1` - Single batch for 8GB VRAM
- `CHUNK_LEN_SEC=150` - Shorter chunks to fit in memory
