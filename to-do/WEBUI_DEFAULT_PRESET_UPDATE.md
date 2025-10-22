# WebUI Default Preset & Environment Constants Update

Updated the WebUI to:

1. **Select "default" preset by default** (instead of "balanced")
2. **Add environment constants** for VAD, Stabilize, Demucs, and Word Timestamps
3. **Make "default" preset respect `.env` configuration** for all feature flags

## Changes Made

### 1. Added Environment Variables to `.env`

```bash
#------------------------------------------------------------------------------
# Default Transcription Features
#------------------------------------------------------------------------------
# Enable Voice Activity Detection (True/False)
DEFAULT_VAD=True
# Enable timestamp stabilization with stable-ts (True/False)
DEFAULT_STABILIZE=True
# Enable audio enhancement with Demucs (True/False)
DEFAULT_DEMUCS=True
# Enable word-level timestamps (True/False)
DEFAULT_WORD_TIMESTAMPS=False
```

### 2. Added Constants to `constant.py`

```python
# Default transcription feature flags (override via env)
DEFAULT_VAD: Final[bool] = os.getenv("DEFAULT_VAD", "False").lower() == "true"
DEFAULT_STABILIZE: Final[bool] = (
    os.getenv("DEFAULT_STABILIZE", "False").lower() == "true"
)
DEFAULT_DEMUCS: Final[bool] = (
    os.getenv("DEFAULT_DEMUCS", "False").lower() == "true"
)
DEFAULT_WORD_TIMESTAMPS: Final[bool] = (
    os.getenv("DEFAULT_WORD_TIMESTAMPS", "False").lower() == "true"
)
```

### 3. Updated `presets.py`

**Import constants:**

```python
from parakeet_rocm.utils.constant import (
    DEFAULT_BATCH_SIZE,
    DEFAULT_CHUNK_LEN_SEC,
    DEFAULT_DEMUCS,
    DEFAULT_STABILIZE,
    DEFAULT_VAD,
    DEFAULT_WORD_TIMESTAMPS,
)
```

**Updated "default" preset:**

```python
"default": Preset(
    name="default",
    description="Default settings from environment configuration",
    config=TranscriptionConfig(
        batch_size=DEFAULT_BATCH_SIZE,
        chunk_len_sec=DEFAULT_CHUNK_LEN_SEC,
        word_timestamps=DEFAULT_WORD_TIMESTAMPS,
        stabilize=DEFAULT_STABILIZE,
        vad=DEFAULT_VAD,
        demucs=DEFAULT_DEMUCS,
        fp16=True,
    ),
),
```

### 4. Updated `app.py`

**Changed default preset selection:**

```python
preset_dropdown = gr.Dropdown(
    choices=list(PRESETS.keys()),
    value="default",  # Was: "balanced"
    label="Quick Presets",
    info="Select a preset or customize settings below",
)
```

**Updated UI component defaults to use constants:**

```python
batch_size = gr.Slider(value=DEFAULT_BATCH_SIZE)
chunk_len_sec = gr.Slider(value=DEFAULT_CHUNK_LEN_SEC)
word_timestamps = gr.Checkbox(value=DEFAULT_WORD_TIMESTAMPS)
stabilize = gr.Checkbox(value=DEFAULT_STABILIZE)
vad = gr.Checkbox(value=DEFAULT_VAD)
demucs = gr.Checkbox(value=DEFAULT_DEMUCS)
```

## Current Configuration (from .env)

| Setting | Value | Source |
|---------|-------|--------|
| **Batch Size** | 1 | `BATCH_SIZE=1` |
| **Chunk Length** | 150 seconds | `CHUNK_LEN_SEC=150` |
| **VAD** | ✅ Enabled | `DEFAULT_VAD=True` |
| **Stabilize** | ✅ Enabled | `DEFAULT_STABILIZE=True` |
| **Demucs** | ✅ Enabled | `DEFAULT_DEMUCS=True` |
| **Word Timestamps** | ❌ Disabled | `DEFAULT_WORD_TIMESTAMPS=False` |

## Preset Comparison

| Preset | VAD | Stabilize | Demucs | Batch | Chunk | Source |
|--------|-----|-----------|--------|-------|-------|--------|
| **default** 🔵 | ✅ | ✅ | ✅ | 1 | 150 | .env |
| fast | ❌ | ❌ | ❌ | 16 | 150 | Override |
| balanced | ❌ | ❌ | ❌ | 8 | 150 | Override |
| high_quality | ❌ | ✅ | ❌ | 4 | 150 | Override |
| best | ✅ | ✅ | ✅ | 4 | 150 | Override |

🔵 = Now selected by default in WebUI

## User Experience Changes

### Before

```txt
WebUI opens → "balanced" preset selected → Features disabled by default
User must manually enable VAD, Stabilize, Demucs
```

### After

```txt
WebUI opens → "default" preset selected → Features enabled per .env
User gets VAD + Stabilize + Demucs automatically (as configured)
```

## Benefits

### ✅ Environment-Driven Configuration

- All defaults controlled via `.env` file
- No code changes needed to adjust defaults
- CLI and WebUI share same configuration

### ✅ Consistent Behavior

- "default" preset matches component defaults
- WebUI respects user's environment configuration
- Predictable behavior across sessions

### ✅ Flexibility

- Users can customize defaults without editing code
- Other presets still available for specific use cases
- Easy to toggle features on/off globally

## Testing

### All Tests Passing ✅

```bash
pdm run pytest tests/unit/webui/ -v -k "test_app or test_preset"
# Result: 21/21 passed
```

### Code Quality ✅

```bash
pdm run ruff check parakeet_rocm/utils/constant.py parakeet_rocm/webui/utils/presets.py parakeet_rocm/webui/app.py
# Result: All checks passed!
```

## Verification

To verify the configuration:

```bash
python3 -c "from parakeet_rocm.utils.constant import DEFAULT_VAD, DEFAULT_STABILIZE, DEFAULT_DEMUCS; print(f'VAD={DEFAULT_VAD}, Stabilize={DEFAULT_STABILIZE}, Demucs={DEFAULT_DEMUCS}')"

# Expected output:
# VAD=True, Stabilize=True, Demucs=True
```

## Files Modified

1. **`.env`** - Added DEFAULT_VAD, DEFAULT_STABILIZE, DEFAULT_DEMUCS, DEFAULT_WORD_TIMESTAMPS
2. **`parakeet_rocm/utils/constant.py`** - Added feature flag constants
3. **`parakeet_rocm/webui/utils/presets.py`** - Updated "default" preset to use constants
4. **`parakeet_rocm/webui/app.py`** - Changed default preset to "default", updated UI defaults

## Configuration Flow

```txt
.env file
    ↓
DEFAULT_VAD=True
DEFAULT_STABILIZE=True
DEFAULT_DEMUCS=True
DEFAULT_WORD_TIMESTAMPS=False
    ↓
utils/constant.py exposes constants
    ↓
├── webui/app.py → UI component defaults
└── webui/utils/presets.py → "default" preset config
```

## Customization Examples

### Example 1: Disable All Features by Default

```bash
# .env
DEFAULT_VAD=False
DEFAULT_STABILIZE=False
DEFAULT_DEMUCS=False
DEFAULT_WORD_TIMESTAMPS=False
```

### Example 2: Enable Only Word Timestamps

```bash
# .env
DEFAULT_VAD=False
DEFAULT_STABILIZE=False
DEFAULT_DEMUCS=False
DEFAULT_WORD_TIMESTAMPS=True
```

### Example 3: High Quality Defaults

```bash
# .env
DEFAULT_VAD=True
DEFAULT_STABILIZE=True
DEFAULT_DEMUCS=True
DEFAULT_WORD_TIMESTAMPS=True
BATCH_SIZE=4
```

## Backward Compatibility

✅ **Fully backward compatible**

- Users without new env vars get code defaults (all False)
- Current `.env` specifies optimized settings for quality
- All existing presets continue to work
- No breaking changes to API

## Use Cases

### Use Case 1: Quality-Focused User

```bash
# .env optimized for best quality (current configuration)
DEFAULT_VAD=True
DEFAULT_STABILIZE=True
DEFAULT_DEMUCS=True
```

✅ Opens WebUI → Gets high-quality defaults immediately

### Use Case 2: Speed-Focused User

```bash
# .env optimized for speed
DEFAULT_VAD=False
DEFAULT_STABILIZE=False
DEFAULT_DEMUCS=False
BATCH_SIZE=16
```

✅ Opens WebUI → Gets fast processing by default

### Use Case 3: Balanced User

```bash
# .env balanced approach
DEFAULT_VAD=False
DEFAULT_STABILIZE=True
DEFAULT_DEMUCS=False
BATCH_SIZE=8
```

✅ Opens WebUI → Gets balanced defaults

## Summary

**Before:**

- WebUI selected "balanced" preset by default
- Feature flags were hardcoded in presets
- Users had to manually enable VAD/Stabilize/Demucs every time

**After:**

- WebUI selects "default" preset by default
- Feature flags respect `.env` configuration
- Users get VAD + Stabilize + Demucs automatically (as configured in `.env`)

**Result:**

- ✅ 21/21 tests passing
- ✅ All ruff checks passing
- ✅ Environment-driven configuration
- ✅ Better user experience

**Ready to use!** Restart the WebUI to see the changes. 🚀
