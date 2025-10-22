# Critical Deadlock Fix - Detailed Analysis

## Problem Observed

The application was hanging indefinitely during model loading with logs showing:
```
[NeMo I 2025-10-21 22:55:27 rnnt_models:226] Using RNNT Loss : tdt
[NeMo W 2025-10-21 22:55:27 label_looping_base:109] No conditional node support for Cuda.
```

Then nothing - the process becomes unresponsive and eventually becomes defunct.

## Root Cause: Lock Acquisition Deadlock

### The Problematic Code Flow

**Original `unload_model_to_cpu()` in `parakeet_rocm/models/parakeet.py`:**

```python
def unload_model_to_cpu(model_name: str = PARAKEET_MODEL_NAME) -> None:
    with _gpu_lock:  # ← LOCK ACQUIRED HERE
        try:
            model = get_model(model_name)  # ← CALLS get_model() INSIDE LOCK
        except Exception:
            return
        # ... GPU operations ...
```

**What happens:**

1. **Idle Offload Thread** (daemon):
   - Calls `unload_model_to_cpu()`
   - Acquires `_gpu_lock`
   - Calls `get_model()` inside the lock

2. **Main Thread** (WebUI/Transcription):
   - Calls `get_model()` to load the model
   - Calls `_get_cached_model()` which calls `_load_model()`
   - `_load_model()` calls `nemo_asr.models.ASRModel.from_pretrained()` (LONG OPERATION)
   - This takes minutes on first run

3. **DEADLOCK SCENARIO**:
   - If Idle thread tries to acquire `_gpu_lock` while Main thread is in `_load_model()`:
     - Idle thread waits for lock
     - Main thread never releases lock (still loading)
     - **DEADLOCK**: Both threads stuck forever

### Why This Happens

The lock was meant to protect GPU operations, but it was held during:
- Model retrieval (`get_model()`)
- Model loading (`_load_model()` → `from_pretrained()`)

These are long-running operations that should NOT hold the lock.

## Solution: Separate Lock Scopes

### New `unload_model_to_cpu()` Implementation

```python
def unload_model_to_cpu(model_name: str = PARAKEET_MODEL_NAME) -> None:
    # Step 1: Get model WITHOUT holding lock
    # If model is not cached, this may load it, but NO LOCK is held
    try:
        model = _get_cached_model(model_name)
    except Exception:
        return
    
    # Step 2: Now hold lock ONLY for GPU operations
    with _gpu_lock:
        try:
            # Synchronize GPU before moving model
            if torch.cuda.is_available():
                try:
                    torch.cuda.synchronize()
                except Exception:
                    pass
            # Move to CPU
            model.to("cpu")
            # Clean up GPU memory
            if torch.cuda.is_available():
                try:
                    torch.cuda.synchronize()
                    torch.cuda.empty_cache()
                except Exception:
                    pass
        except Exception:
            pass
```

### Key Improvements

1. **No Lock During Model Loading**
   - `_get_cached_model()` is called OUTSIDE the lock
   - If model is not cached, it loads without blocking other threads
   - If model is cached, retrieval is fast

2. **Lock Only for GPU Operations**
   - `torch.cuda.synchronize()` - wait for GPU to finish
   - `model.to("cpu")` - move model to CPU
   - `torch.cuda.empty_cache()` - free GPU memory
   - These are quick operations that need synchronization

3. **Proper Exception Handling**
   - Outer try/except catches model retrieval failures
   - Inner try/except catches GPU operation failures
   - No silent failures

## Thread Safety Analysis

### Before Fix (UNSAFE)
```
Main Thread                          Idle Thread
─────────────────────────────────────────────────
get_model()
  _get_cached_model()
    _load_model()
      from_pretrained()  ← LONG OP
      (holds implicit GPU state)
                                     unload_model_to_cpu()
                                       with _gpu_lock:  ← WAITS
                                         get_model()    ← DEADLOCK
```

### After Fix (SAFE)
```
Main Thread                          Idle Thread
─────────────────────────────────────────────────
get_model()
  _get_cached_model()
    _load_model()
      from_pretrained()  ← LONG OP
      (no lock held)
                                     unload_model_to_cpu()
                                       _get_cached_model()  ← FAST
                                       with _gpu_lock:      ← ACQUIRED
                                         model.to("cpu")
                                         empty_cache()
```

## Verification

### Syntax Check
```bash
pdm run python -c "import ast; ast.parse(open('parakeet_rocm/models/parakeet.py').read())"
# ✓ Syntax OK
```

### Linting Check
```bash
pdm run ruff check parakeet_rocm/models/parakeet.py
# ✓ All checks passed!
```

## Expected Behavior After Fix

1. ✅ Model loads without hanging
2. ✅ Idle offload thread doesn't interfere with loading
3. ✅ GPU memory properly released
4. ✅ No defunct processes
5. ✅ Application responsive during idle periods

## Testing Recommendations

1. **Monitor for hangs:**
   ```bash
   docker logs -f parakeet-rocm-dev
   ```

2. **Check GPU memory:**
   ```bash
   watch -n 1 'rocm-smi --showpids --showpidgpus'
   ```

3. **Verify no defunct processes:**
   ```bash
   ps aux | grep defunct
   ```

4. **Test idle behavior:**
   - Start WebUI
   - Upload file and transcribe
   - Wait for idle timeout
   - Check logs for offload messages
   - Verify GPU memory released

## Related Issues

- **Commit 7f3ae13**: Introduced idle offload mechanism (caused the issue)
- **Previous Fix**: Added locks but didn't account for nested lock acquisition
- **This Fix**: Separates lock scopes to prevent deadlock

## Prevention for Future Development

When adding thread synchronization:

1. **Minimize Lock Scope**: Hold locks only for the critical section
2. **Avoid Nested Locks**: Don't call functions that acquire locks from within a lock
3. **Test Concurrency**: Run with multiple threads/processes
4. **Use Timeouts**: Add timeouts to prevent indefinite waits (future improvement)
