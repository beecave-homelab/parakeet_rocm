"""Directory / pattern watcher that triggers transcription.

This module centralises the ``--watch`` implementation so that the top-level
`cli.py` remains a thin argument parser.

The primary entry point is :func:`watch_and_transcribe`, which blocks and
continuously monitors for new audio files that match the given *patterns*.

It uses :func:`parakeet_rocm.utils.file_utils.resolve_input_paths` to
expand wildcards and directories. Already-transcribed files are skipped by
checking whether an output file would be generated (using
:func:`parakeet_rocm.utils.file_utils.get_unique_filename` with
``overwrite=False``). If the unique filename differs from the intended one, it
assumes a transcription already exists.
"""

from __future__ import annotations

import signal
import sys
import time
from collections.abc import Callable, Iterable, Sequence
from pathlib import Path
from types import FrameType

from parakeet_rocm.models.parakeet import (
    clear_model_cache,
    unload_model_to_cpu,
)
from parakeet_rocm.utils.constant import (
    IDLE_CLEAR_TIMEOUT_SEC,
    IDLE_UNLOAD_TIMEOUT_SEC,
)
from parakeet_rocm.utils.file_utils import (
    AUDIO_EXTENSIONS,
    get_unique_filename,
    resolve_input_paths,
)

__all__ = ["watch_and_transcribe"]


def _default_sig_handler(_signum: int, _frame: FrameType | None) -> None:  # noqa: D401
    """Handle ``SIGINT`` (Ctrl-C) gracefully.

    Args:
        _signum: Received POSIX signal number (unused).
        _frame: Current stack frame (unused).

    """
    print("\n[watch] Stopping…")
    try:
        unload_model_to_cpu()
    finally:
        clear_model_cache()
    sys.exit(0)


def _needs_transcription(
    path: Path,
    output_dir: Path,
    output_template: str,
    output_format: str,
    watch_base_dirs: Sequence[Path] | None = None,
) -> bool:  # noqa: D401
    """Check whether *path* still needs to be transcribed.

    Args:
        path: Audio file under consideration.
        output_dir: Directory where output files are written.
        output_template: Filename template provided by the CLI.
        output_format: Desired output extension (``txt``, ``srt``, …).
        watch_base_dirs: Optional base directories used by ``--watch``. If
            provided and ``path`` is within one of these directories, the output
            will mirror the subdirectory structure beneath the base directory.

    Returns:
        ``True`` if no output file exists for *path* yet, ``False`` otherwise.

    """
    target_name = output_template.format(
        parent=path.parent.name,
        filename=path.stem,
        index="",  # handled elsewhere
        date="",  # handled elsewhere
    )
    # Mirror subdirectory structure under any matched watch base dir
    target_dir = output_dir
    if watch_base_dirs:
        for base in watch_base_dirs:
            try:
                rel = path.parent.relative_to(base)
            except Exception:
                continue
            else:
                # If "rel" is not empty (i.e., file is in a subdirectory), mirror it
                if str(rel) != "." and str(rel) != "":
                    target_dir = output_dir / rel
                break
    candidate = target_dir / f"{target_name}.{output_format}"
    # If unique filename differs, file exists ⇒ already transcribed
    return get_unique_filename(candidate, overwrite=False) == candidate


def watch_and_transcribe(
    *,
    patterns: Iterable[str | Path],
    transcribe_fn: Callable[[list[Path]], None],
    poll_interval: float = 2.0,
    output_dir: Path,
    output_format: str,
    output_template: str,
    watch_base_dirs: Sequence[Path] | None = None,
    audio_exts: Sequence[str] | None = None,
    verbose: bool = False,
) -> None:
    """Monitor *patterns* and transcribe newly detected audio files.

    This is a lightweight polling implementation to avoid adding extra
    dependencies such as *watchdog*. A sleep-poll loop every few seconds is
    usually sufficient for batch-style workflows.

    Args:
        patterns: Directory, file, or glob pattern(s) to monitor.
        transcribe_fn: Callback that receives a list of newly detected audio
            files to transcribe.
        poll_interval: Seconds between directory scans.
        output_dir: Directory where transcription outputs are written.
        output_format: Output format (e.g. ``"txt"``, ``"srt"``).
        output_template: Template string used to construct output filenames.
        audio_exts: Allowed audio extensions. ``None`` defaults to
            :data:`parakeet_rocm.utils.file_utils.AUDIO_EXTENSIONS`.
        watch_base_dirs: Optional base directories to mirror under
            ``output_dir`` when files are detected within subdirectories of the
            watched path(s).
        verbose: If *True*, prints watcher debug information to *stdout*.

    """
    print(
        f"[watch] Monitoring {', '.join(map(str, patterns))} …  (Press Ctrl+C to stop)"
    )

    signal.signal(signal.SIGINT, _default_sig_handler)
    try:
        signal.signal(signal.SIGTERM, _default_sig_handler)
    except Exception:
        pass

    seen: set[Path] = set()
    last_activity = time.monotonic()
    unloaded = False  # prevent spamming unload calls/logs while idle
    cleared = False  # whether we already cleared the model cache

    while True:
        all_matches = resolve_input_paths(
            patterns, audio_exts=audio_exts or AUDIO_EXTENSIONS
        )
        if verbose:
            print(f"[watch] Scan found {len(all_matches)} candidate file(s)")
        new_paths: list[Path] = []
        for p in all_matches:
            if p in seen:
                if verbose:
                    print(f"[watch] ✗ Already processed: {p}")
                continue
            if _needs_transcription(
                p,
                output_dir,
                output_template,
                output_format,
                watch_base_dirs=watch_base_dirs,
            ):
                new_paths.append(p)
                seen.add(p)
            else:
                if verbose:
                    print(f"[watch] ✗ Output exists, skipping: {p}")
        if new_paths:
            if verbose:
                print(f"[watch] Found {len(new_paths)} new file(s):")
                for file in new_paths:
                    print(f"- {file}")
            transcribe_fn(new_paths)
            # Mark activity and reset idle state
            last_activity = time.monotonic()
            if unloaded or cleared:
                # A new job arrived after idle; the model will be promoted back
                # to GPU automatically on next get_model(). Reset flag.
                unloaded = False
                cleared = False
        else:
            if verbose:
                print("[watch] No new files – waiting…")
            # Idle handling: offload model to CPU if idle timeout exceeded
            now = time.monotonic()
            if not unloaded and (now - last_activity) >= IDLE_UNLOAD_TIMEOUT_SEC:
                try:
                    if verbose:
                        print(
                            f"[watch] Idle for >= {IDLE_UNLOAD_TIMEOUT_SEC}s – "
                            "offloading model to CPU"
                        )
                    unload_model_to_cpu()
                finally:
                    unloaded = True
            # If still idle past clear timeout, drop the cache entirely
            if not cleared and (now - last_activity) >= IDLE_CLEAR_TIMEOUT_SEC:
                try:
                    if verbose:
                        print(
                            f"[watch] Idle for >= {IDLE_CLEAR_TIMEOUT_SEC}s – "
                            "clearing model cache"
                        )
                    clear_model_cache()
                finally:
                    cleared = True
        time.sleep(poll_interval)
