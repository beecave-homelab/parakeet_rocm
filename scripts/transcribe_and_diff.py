#!/usr/bin/env python3

"""transcribe_and_diff.py.

Unified helper to:
  1) Transcribe an input file into three variants
     (default, stabilize, stabilize+vad+demucs).
  2) Run pairwise SRT readability diffs on the three generated outputs.

With no flags it runs BOTH steps. Use --transcribe or --report to select one.

Author: elvee
Date: 11-08-2025
"""

from __future__ import annotations

import logging
import shutil
import subprocess
import sys
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

import typer

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

DEFAULT_OUT_DIR: Path = Path("data/test_results")
D_DEFAULT: Path = Path("data/output/default")
D_STABILIZE: Path = Path("data/output/stabilize")
D_SVD: Path = Path("data/output/stabilize_vad_demucs")

LOG_FORMAT: str = "[%(levelname)s] %(message)s"

app = typer.Typer(add_completion=False, no_args_is_help=True)


@app.callback()
def _root() -> None:
    """Command group placeholder for transcription and SRT diff workflows.

    Exists so the Typer app exposes a command group (allowing explicit subcommand invocation such as "run"). Currently a no-op; group-level options may be added later.
    """
    # No-op: group-level options could be added here in the future.
    return None


# -----------------------------------------------------------------------------
# Data models
# -----------------------------------------------------------------------------


@dataclass(frozen=True)
class Runners:
    """Holds the resolved runners for transcription and diff reporting.

    Attributes:
        transcribe: Command prefix used to run the transcriber.
        diff_report: Command prefix used to run the SRT diff reporter.

    """

    transcribe: tuple[str, ...]
    diff_report: tuple[str, ...]


# -----------------------------------------------------------------------------
# Utilities
# -----------------------------------------------------------------------------


def command_available(cmd: str) -> bool:
    """Check whether a command is available on the system PATH.

    Parameters:
        cmd (str): Name of the executable or command to probe.

    Returns:
        bool: `True` if the command is found on PATH, `False` otherwise.
    """
    return shutil.which(cmd) is not None


def ensure_dirs(paths: Iterable[Path]) -> None:
    """Ensure each Path in `paths` exists as a directory, creating parent directories when necessary.

    Parameters:
        paths (Iterable[Path]): Directory paths to ensure exist; existing directories are left unchanged.
    """
    for path in paths:
        path.mkdir(parents=True, exist_ok=True)


def resolve_runners() -> Runners:
    """Resolve runners for transcription and reporting, mirroring Bash logic.

    Priority order (transcribe):
        1) `pdm run parakeet-rocm`
        2) `parakeet-rocm`
        3) `python -m parakeet_rocm.cli`

    Priority order (diff):
        - If using `pdm` for transcribe, prefer
          `pdm run python -m scripts.srt_diff_report`
        - Else if `srt-diff-report` exists, use it
        - Else fallback to `python -m scripts.srt_diff_report`

    Returns:
        Runners: The resolved command prefixes.

    """
    if command_available("pdm"):
        transcribe = ("pdm", "run", "parakeet-rocm")
        diff_report = ("pdm", "run", "python", "-m", "scripts.srt_diff_report")
    elif command_available("parakeet-rocm"):
        transcribe = ("parakeet-rocm",)
        if command_available("srt-diff-report"):
            diff_report = ("srt-diff-report",)
        else:
            diff_report = ("python", "-m", "scripts.srt_diff_report")
    else:
        transcribe = ("python", "-m", "parakeet_rocm.cli")
        if command_available("srt-diff-report"):
            diff_report = ("srt-diff-report",)
        else:
            diff_report = ("python", "-m", "scripts.srt_diff_report")

    return Runners(transcribe=transcribe, diff_report=diff_report)


def run(cmd: Sequence[str]) -> None:
    """Execute the given command sequence after logging it.

    Parameters:
        cmd (Sequence[str]): The command and its arguments as a sequence of strings.

    Raises:
        subprocess.CalledProcessError: If the invoked process exits with a non-zero status.
    """
    logging.debug("Running: %s", " ".join(cmd))
    subprocess.run(cmd, check=True)


def find_srt(dir_path: Path, stem: str) -> Path | None:
    """Finds an SRT file in dir_path matching the given stem.

    Searches for an exact match '<stem>.srt' first; if not found, returns the most recently modified file matching '<stem>*.srt'.

    Parameters:
        dir_path (Path): Directory to search.
        stem (str): Base filename without extension to match.

    Returns:
        Path | None: Path to the matched SRT file, or None if no match is found.
    """
    exact = dir_path / f"{stem}.srt"
    if exact.is_file():
        return exact

    candidates = sorted(
        dir_path.glob(f"{stem}*.srt"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return candidates[0] if candidates else None


# -----------------------------------------------------------------------------
# Core actions
# -----------------------------------------------------------------------------


def transcribe_three(runners: Runners, input_file: Path) -> None:
    """Transcribe the given audio file into three SRT variants and write outputs to the configured variant directories.

    Creates three transcription variants: default, stabilize, and stabilize with VAD+Demucs, producing SRT output in the module's D_DEFAULT, D_STABILIZE, and D_SVD directories.

    Parameters:
        runners (Runners): Resolved command prefixes; the `transcribe` prefix is used to invoke the transcriber.
        input_file (Path): Path to the input audio file to transcribe.
    """
    ensure_dirs([D_DEFAULT, D_STABILIZE, D_SVD])

    base: list[str] = list(runners.transcribe) + [
        "transcribe",
        "--word-timestamps",
        "--output-format",
        "srt",
    ]

    # default
    run(base + ["--output-dir", str(D_DEFAULT), str(input_file)])

    # stabilize
    run(
        base
        + [
            "--output-dir",
            str(D_STABILIZE),
            "--stabilize",
            str(input_file),
        ]
    )

    # stabilize + vad + demucs
    run(
        base
        + [
            "--output-dir",
            str(D_SVD),
            "--stabilize",
            "--vad",
            "--demucs",
            str(input_file),
        ]
    )


def report_diffs(
    runners: Runners,
    stem: str,
    out_dir: Path,
    show_violations: int,
) -> None:
    """Run pairwise SRT readability diffs between the three variants.

    Pairs:
      - default vs stabilize
      - default vs stabilize_vad_demucs
      - stabilize vs stabilize_vad_demucs

    Args:
        runners: Resolved runners with the diff-report command prefix.
        stem: Base filename (without extension) used to find SRT files.
        out_dir: Directory to write Markdown and JSON reports to.
        show_violations: If > 0, limit top-N violations per category.

    Raises:
        FileNotFoundError: If any of the expected SRT files are missing.

    """
    ensure_dirs([out_dir])

    srt_default = find_srt(D_DEFAULT, stem)
    srt_stab = find_srt(D_STABILIZE, stem)
    srt_svd = find_srt(D_SVD, stem)

    if not (srt_default and srt_stab and srt_svd):
        msg_lines = [
            f"Missing SRT(s) for '{stem}'. Ensure transcription step ran.",
            f"  default:       {D_DEFAULT / (stem + '.srt')} (or newest {stem}*.srt)",
            f"  stabilize:     {D_STABILIZE / (stem + '.srt')} (or newest {stem}*.srt)",
            f"  vad+demucs:    {D_SVD / (stem + '.srt')} (or newest {stem}*.srt)",
        ]
        raise FileNotFoundError("\n".join(msg_lines))

    pairs: list[tuple[tuple[str, Path], tuple[str, Path]]] = [
        (("default", srt_default), ("stabilize", srt_stab)),
        (("default", srt_default), ("stabilize_vad_demucs", srt_svd)),
        (("stabilize", srt_stab), ("stabilize_vad_demucs", srt_svd)),
    ]

    for (left_label, left_path), (right_label, right_path) in pairs:
        base_name = f"srt_diff_{left_label}_vs_{right_label}_{stem}"
        md_out = out_dir / f"{base_name}.md"
        json_out = out_dir / f"{base_name}.json"

        cmd_md: list[str] = list(runners.diff_report) + [
            str(left_path),
            str(right_path),
            "--output-format",
            "markdown",
            "-o",
            str(md_out),
        ]
        if show_violations > 0:
            cmd_md += ["--show-violations", str(show_violations)]
        run(cmd_md)

        cmd_json: list[str] = list(runners.diff_report) + [
            str(left_path),
            str(right_path),
            "--output-format",
            "json",
            "-o",
            str(json_out),
        ]
        if show_violations > 0:
            cmd_json += ["--show-violations", str(show_violations)]
        run(cmd_json)


# -----------------------------------------------------------------------------
# CLI (Typer)
# -----------------------------------------------------------------------------


@app.command("run")
def cli(
    audio_file: Path = typer.Argument(..., help="Path to the input audio file."),
    transcribe: bool = typer.Option(False, "--transcribe", help="Run only the transcription step."),
    report: bool = typer.Option(False, "--report", help="Run only the reporting step."),
    show_violations: int = typer.Option(
        0,
        "--show-violations",
        min=0,
        help="If > 0, show top-N violations per category in reports.",
    ),
    out_dir: Path = typer.Option(
        DEFAULT_OUT_DIR,
        "--out-dir",
        help="Directory to write markdown/json reports to.",
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable debug logging."),
) -> None:
    """Transcribe an audio file (3 variants) and/or generate SRT diff reports.

    With no explicit mode flags, this runs both steps in sequence.

    Raises:
        typer.BadParameter: If mutually exclusive flags `--transcribe` and
            `--report` are provided together.
        typer.Exit: If the input audio file does not exist or cannot be read.

    """
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format=LOG_FORMAT)

    if transcribe and report:
        # Ensure the message is visible on stdout for tests that assert on it.
        typer.echo("Use ONLY one of --transcribe or --report (or neither for both).")
        raise typer.BadParameter("Use ONLY one of --transcribe or --report (or neither for both).")

    # Manual validation to print a Click-like message on stdout (tests assert on stdout)
    if not audio_file.exists():
        typer.echo(f"Invalid value for 'AUDIO_FILE': File '{audio_file}' does not exist.")
        raise typer.Exit(code=2)

    stem = audio_file.stem
    ensure_dirs([out_dir, D_DEFAULT, D_STABILIZE, D_SVD])

    try:
        runners = resolve_runners()
        logging.info("Transcribe runner: %s", " ".join(runners.transcribe))
        logging.info("Diff runner:       %s", " ".join(runners.diff_report))

        if transcribe:
            transcribe_three(runners, audio_file)
        elif report:
            report_diffs(
                runners=runners,
                stem=stem,
                out_dir=out_dir,
                show_violations=show_violations,
            )
        else:
            transcribe_three(runners, audio_file)
            report_diffs(
                runners=runners,
                stem=stem,
                out_dir=out_dir,
                show_violations=show_violations,
            )

        logging.info("Done.")
    except FileNotFoundError as exc:
        logging.error("%s", exc)
        raise typer.Exit(code=2) from exc
    except subprocess.CalledProcessError as exc:
        logging.error("Command failed with exit code %s", exc.returncode)
        raise typer.Exit(code=exc.returncode or 1) from exc
    # No broad catch-all: allow unexpected exceptions to propagate naturally.


# -----------------------------------------------------------------------------
# Main guard
# -----------------------------------------------------------------------------


def main() -> None:
    """Entrypoint for running via python -m or direct execution."""
    app()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logging.error("Interrupted by user.")
        sys.exit(130)
