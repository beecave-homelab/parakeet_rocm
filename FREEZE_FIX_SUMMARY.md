# GPU Freeze Issue - Root Cause & Fixes

## Problem Summary

The application was freezing within the Docker container, leaving a defunct process (PID 6925) with 2.35GB of stuck GPU VRAM. The active process (PID 1453) held 843MB, indicating incomplete GPU resource cleanup.

## Root Cause Analysis

### Primary Issue: GPU Memory Deadlock

The freeze was caused by a **race condition in the idle offload mechanism** introduced in commit `7f3ae13`:

1. **Unsynchronized GPU Operations** (`parakeet_rocm/webui/app.py:97-146`)
   - Daemon thread calls `unload_model_to_cpu()` and `clear_model_cache()` without synchronization
   - These operations could execute while the main transcription thread held GPU locks
   - `torch.cuda.empty_cache()` would block indefinitely if GPU operations were pending

2. **Blocking Points**
   - `stable_whisper.transcribe_any()` holds GPU locks during Demucs/VAD preprocessing
   - No `torch.cuda.synchronize()` before cleanup operations
   - No timeout protection on GPU operations

3. **Why Process Became Defunct**
   - Parent process (Gradio/WebUI) terminated while child thread held GPU resources
   - GPU driver couldn't release the stuck VRAM
   - Zombie process remained with orphaned GPU context

## Fixes Applied

### 1. Thread-Safe GPU Operations (`parakeet_rocm/models/parakeet.py`)

**Added global GPU lock:**
```python
_gpu_lock = threading.RLock()
```

**Protected `unload_model_to_cpu()`:**
- Wrapped entire operation with `_gpu_lock`
- Added `torch.cuda.synchronize()` before moving model to CPU
- Added `torch.cuda.synchronize()` after moving model
- Ensures GPU operations complete before cleanup

**Protected `clear_model_cache()`:**
- Wrapped cache clearing with `_gpu_lock`
- Prevents concurrent access to model cache

### 2. Improved Error Handling (`parakeet_rocm/webui/app.py`)

**Enhanced idle offload thread:**
- Added explicit exception logging instead of silent failures
- Better error messages for debugging
- Proper exception handling in all code paths
- Fixed line length violations (PEP 8 compliance)

## Changes Made

### File: `parakeet_rocm/models/parakeet.py`
- Added `threading` import
- Added `_gpu_lock = threading.RLock()` at module level
- Wrapped `unload_model_to_cpu()` with lock and synchronization
- Wrapped `clear_model_cache()` with lock

### File: `parakeet_rocm/webui/app.py`
- Fixed import ordering (alphabetical within groups)
- Enhanced exception logging in idle offload thread
- Improved code formatting for PEP 8 compliance

## Testing Recommendations

1. **Monitor GPU Memory:**
   ```bash
   watch -n 1 'rocm-smi --showpids --showpidgpus'
   ```

2. **Run Extended Tests:**
   ```bash
   pdm run pytest tests/ -v
   ```

3. **Test Idle Behavior:**
   - Start WebUI
   - Run transcription
   - Wait for idle timeout (check logs for offload messages)
   - Verify GPU memory is released

4. **Check for Defunct Processes:**
   ```bash
   ps aux | grep defunct
   ```

## Expected Behavior After Fix

- ✅ No defunct processes after application shutdown
- ✅ GPU VRAM properly released when idle
- ✅ Model offloaded to CPU after `IDLE_UNLOAD_TIMEOUT_SEC`
- ✅ Model cache cleared after `IDLE_CLEAR_TIMEOUT_SEC`
- ✅ Graceful error handling with informative logging
- ✅ No GPU deadlocks during concurrent operations

## Prevention

The fixes ensure:
1. **Atomic GPU Operations**: Lock prevents race conditions
2. **Proper Synchronization**: `torch.cuda.synchronize()` ensures GPU is ready
3. **Better Observability**: Exception logging helps identify future issues
4. **Thread Safety**: RLock allows recursive locking if needed

## Related Commits

- `7f3ae13`: Introduced idle offload mechanism (caused the issue)
- Current: Fixes race condition and adds thread safety
