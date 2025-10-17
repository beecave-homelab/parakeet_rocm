# Callback-Based Progress Tracking Implementation

## Overview

Implemented callback-based progress tracking to integrate the existing Rich Progress infrastructure (used by CLI) with the Gradio WebUI, providing **real-time segment-by-segment progress updates**.

## Problem Statement

**Before:**

- WebUI progress bar jumped to 90% instantly
- Progress loop completed before actual transcription started
- No visibility into actual transcription progress
- Existing Rich Progress infrastructure was disabled (`no_progress=True`)

**After:**

- Real-time progress updates from actual transcription batches
- Progress bar accurately reflects segment processing
- Reuses existing Rich Progress tracking logic
- Clean callback-based architecture

## Architecture: Callback Flow

```txt
WebUI (Gradio)
├─ Create progress callback function
│  └─ Maps batch progress → Gradio progress (0.3-0.95)
│
└─ Pass to job_manager.run_job(callback)
   └─ Pass to cli_transcribe(callback)
      └─ Pass to transcribe_file(callback)
         └─ Pass to _transcribe_batches(callback)
            └─ Call callback(current, total) after each batch
               └─ Updates Gradio progress bar ✅
```

## Implementation Details

### 1. Core Progress Tracking (`file_processor.py`)

**Modified `_transcribe_batches()`** to accept and call progress callback:

```python
def _transcribe_batches(
    ...
    progress_callback: callable | None = None,
) -> tuple[list[Any], list[str]]:
    total_segments = len(segments)
    processed_segments = 0
    
    for batch in _chunks(segments, batch_size):
        # ... transcribe batch ...
        
        processed_segments += len(batch_wavs)
        
        # Rich Progress (CLI)
        if not no_progress and main_task is not None:
            progress.advance(main_task, len(batch_wavs))
        
        # External callback (WebUI) ✅
        if progress_callback is not None:
            progress_callback(processed_segments, total_segments)
```

**Modified `transcribe_file()`** to accept and pass callback through.

### 2. CLI Integration (`cli.py`)

**Modified `cli_transcribe()`** to accept optional callback:

```python
def cli_transcribe(
    *,
    ...
    progress_callback: callable | None = None,
) -> list[Path]:
    """Run batch transcription.
    
    Args:
        ...
        progress_callback: Optional callback for external progress tracking.
            Called with (current, total) after each batch. Used by WebUI.
    """
    # Pass through to transcribe_file
    output_path = transcribe_file(
        ...
        progress_callback=progress_callback,
    )
```

### 3. Job Manager (`job_manager.py`)

**Modified `run_job()`** to accept and pass callback:

```python
def run_job(
    self, job_id: str, progress_callback: callable | None = None
) -> TranscriptionJob:
    """Execute a transcription job.
    
    Args:
        job_id: ID of job to run.
        progress_callback: Optional callback for progress updates.
            Called with (current, total) after each batch.
    """
    outputs = self.transcribe_fn(
        ...
        no_progress=progress_callback is None,  # Enable when callback provided
        progress_callback=progress_callback,
    )
```

### 4. WebUI Integration (`app.py`)

**Created Gradio progress callback** and passed to job manager:

```python
# Create callback to update Gradio progress from batch progress
def update_gradio_progress(current: int, total: int) -> None:
    """Update Gradio progress bar from transcription batches."""
    # Map batch progress (0-total) to Gradio progress (0.3-0.95)
    batch_fraction = current / total if total > 0 else 0
    gradio_progress = 0.3 + (batch_fraction * 0.65)
    progress(
        gradio_progress,
        desc=f"🎙️ Transcribing batch {current}/{total}...",
    )
    logger.debug(f"Progress: {current}/{total} batches ({gradio_progress:.1%})")

# Run transcription with progress callback
result = job_manager.run_job(
    job.job_id, progress_callback=update_gradio_progress
)
```

## Progress Mapping

**Gradio Progress Stages:**

| Stage | Progress % | Description |
|-------|-----------|-------------|
| Validation | 0% - 10% | File validation |
| Configuration | 10% - 20% | Config setup |
| Job Submission | 20% - 30% | Job submitted |
| **Transcription** | **30% - 95%** | **Actual batch processing** ⭐ |
| Finalization | 95% - 100% | Results finalized |

**The 30%-95% range is dynamically updated based on batch progress!**

## Benefits

### ✅ Reuses Existing Infrastructure

- No duplicate progress tracking code
- Leverages battle-tested Rich Progress logic
- Maintains CLI behavior unchanged

### ✅ Real-Time Accuracy

- Progress updates after **each batch** (not per file)
- Accurate reflection of actual transcription work
- Users see meaningful progress during long transcriptions

### ✅ Clean Architecture

- Callback pattern keeps concerns separated
- Gradio logic stays in WebUI
- Core transcription logic unchanged
- Easy to test with mock callbacks

### ✅ Backward Compatible

- CLI behavior unchanged
- Optional callback parameter (defaults to None)
- WebUI can choose to enable/disable

## Example Progress Output

**For a file with 100 segments, batch_size=16:**

```txt
🎙️ Transcribing batch 16/100...   (40% Gradio progress)
🎙️ Transcribing batch 32/100...   (52% Gradio progress)
🎙️ Transcribing batch 48/100...   (61% Gradio progress)
🎙️ Transcribing batch 64/100...   (72% Gradio progress)
🎙️ Transcribing batch 80/100...   (82% Gradio progress)
🎙️ Transcribing batch 96/100...   (92% Gradio progress)
🎙️ Transcribing batch 100/100...  (95% Gradio progress)
✨ Finalizing results...           (95% Gradio progress)
✅ Done!                            (100% Gradio progress)
```

## Files Modified

1. **`parakeet_rocm/transcription/file_processor.py`**
   - Added `progress_callback` parameter to `_transcribe_batches()`
   - Added `progress_callback` parameter to `transcribe_file()`
   - Call callback after each batch with `(current, total)`

2. **`parakeet_rocm/transcription/cli.py`**
   - Added `progress_callback` parameter to `cli_transcribe()`
   - Pass callback through to `transcribe_file()`

3. **`parakeet_rocm/webui/core/job_manager.py`**
   - Added `progress_callback` parameter to `run_job()`
   - Pass callback to `cli_transcribe()`
   - Enable Rich Progress when callback is provided

4. **`parakeet_rocm/webui/app.py`**
   - Created `update_gradio_progress()` callback function
   - Maps batch progress to Gradio progress (0.3-0.95)
   - Pass callback to `job_manager.run_job()`

## Testing

✅ **All unit tests passing**: 5/5 WebUI tests
✅ **Ruff checks passing**: No linting errors
✅ **Backward compatible**: CLI behavior unchanged

## Usage

**WebUI (automatic):**

```bash
docker compose -f docker-compose.dev.yaml up
# Progress bar now updates in real-time!
```

**CLI (unchanged):**

```bash
parakeet-rocm transcribe audio.wav
# Rich Progress bar works as before
```

**Programmatic (optional callback):**

```python
from parakeet_rocm.transcription import cli_transcribe

def my_progress(current, total):
    print(f"Progress: {current}/{total}")

cli_transcribe(
    audio_files=[Path("audio.wav")],
    progress_callback=my_progress  # Optional!
)
```

## Future Enhancements

Potential improvements:

- [ ] Add ETA calculation based on batch timing
- [ ] Per-file progress tracking for multi-file jobs
- [ ] Progress persistence for long-running jobs
- [ ] WebSocket-based progress streaming
- [ ] Progress callback for stabilization phase

## References

- **Core tracking**: `parakeet_rocm/transcription/file_processor.py`
- **CLI integration**: `parakeet_rocm/transcription/cli.py`
- **Job manager**: `parakeet_rocm/webui/core/job_manager.py`
- **WebUI integration**: `parakeet_rocm/webui/app.py`
- **Tests**: `tests/unit/webui/test_app.py`
