"""Subtitle refinement utilities.

This module provides a `SubtitleRefiner` that post-processes SRT files to meet
readability guidelines defined in `utils.constant`:

* Minimum cue duration (`MIN_SEGMENT_DURATION_SEC`, default 1.0 s)
* Maximum characters per second (`MAX_CPS`, default 17)
* Mandatory gap between cues in frames (`GAP_FRAMES`, default 2)
* Video frame-rate (`FPS`, default 25)
* Maximum characters per line (`MAX_LINE_CHARS`, default 42)

All values fall back to the defaults above if *utils.constant* does not expose
an attribute (keeps the refiner usable even before constants are added).

No changes are made to the actual words – only timing and line breaks are
altered. This ensures the original ASR text remains intact.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants – import from utils.constant with graceful fallbacks
# ---------------------------------------------------------------------------
from parakeet_rocm.utils import constant as _c  # pylint: disable=import-error

BOUNDARY_CHARS = getattr(_c, "BOUNDARY_CHARS", ".?!…")
CLAUSE_CHARS = getattr(_c, "CLAUSE_CHARS", ",;:")
SOFT_BOUNDARY_WORDS = getattr(_c, "SOFT_BOUNDARY_WORDS", ("and", "but", "that"))
INTERJECTION_WHITELIST = getattr(
    _c, "INTERJECTION_WHITELIST", ("whoa", "wow", "what", "oh", "hey", "ah")
)

MAX_CPS: int = getattr(_c, "MAX_CPS", 17)
MAX_LINE_CHARS: int = getattr(_c, "MAX_LINE_CHARS", 42)
MIN_DUR: float = getattr(_c, "MIN_SEGMENT_DURATION_SEC", 1.0)
FPS: int = getattr(_c, "FPS", 25)  # video frame-rate (assumed constant)
GAP_FRAMES: int = getattr(_c, "GAP_FRAMES", 2)
GAP_SEC: float = GAP_FRAMES / FPS

# ---------------------------------------------------------------------------
# Regex helpers
# ---------------------------------------------------------------------------
_TIME_RE = re.compile(r"^(\d\d):(\d\d):(\d\d),(\d\d\d)$")


@dataclass
class Cue:
    """Simple container for an SRT cue."""

    index: int
    start: float  # seconds
    end: float  # seconds
    text: str

    # ---------------------------------------------------------------------
    # Formatting helpers
    # ---------------------------------------------------------------------
    def to_srt(self) -> str:
        """Render the cue as a single SRT block.

        Returns:
            The SRT block containing the cue index, timestamp range, and trimmed text, ending with a newline.
        """
        return (
            f"{self.index}\n{_format_ts(self.start)} --> {_format_ts(self.end)}\n"
            f"{self.text.strip()}\n"
        )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
class SubtitleRefiner:
    """Refines SRT cues for readability.

    Workflow:
        refiner = SubtitleRefiner()
        cues = refiner.load_srt(input_path)
        refined = refiner.refine(cues)
        refiner.save_srt(refined, output_path)
    """

    def __init__(
        self,
        max_cps: int = MAX_CPS,
        min_dur: float = MIN_DUR,
        gap_frames: int = GAP_FRAMES,
        fps: int = FPS,
        max_line_chars: int = MAX_LINE_CHARS,
        max_lines_per_block: int = getattr(_c, "MAX_LINES_PER_BLOCK", 2),
    ) -> None:
        """Create a SubtitleRefiner configured with readability constraints for SRT refinement.

        Initializes thresholds and derived values used when merging, enforcing gaps, and wrapping subtitle cues:
        - max_cps: target maximum characters per second allowed per cue.
        - min_dur: minimum cue duration in seconds before considering merges.
        - gap_frames and fps: used to compute the minimum inter-cue gap in seconds (stored as `self.gap`).
        - max_line_chars and max_lines_per_block: limits used when wrapping cue text into lines.
        Also computes `self.max_block_chars` (maximum characters per merged block) and `self.max_dur` (maximum segment duration), using module-level constants when available.
        """
        self.max_cps = max_cps
        self.min_dur = min_dur
        self.gap = gap_frames / fps
        self.max_line_chars = max_line_chars
        self.max_lines_per_block = max_lines_per_block
        self.max_block_chars = getattr(_c, "MAX_BLOCK_CHARS", max_line_chars * 2)
        self.max_dur = getattr(_c, "MAX_SEGMENT_DURATION_SEC", 6.0)

    # ---------------------------------------------------------------------
    # I/O
    # ---------------------------------------------------------------------
    def load_srt(self, path: Path | str) -> list[Cue]:
        """Parse an SRT file into a list of Cue objects preserving file order.

        Args:
            path (Path | str): Path to the SRT file to read.

        Returns:
            list[Cue]: Parsed cues in the order they appear in the file.
        """
        text = Path(path).read_text(encoding="utf-8", errors="ignore")
        blocks = re.split(r"\n{2,}", text.strip())
        cues: list[Cue] = []
        for block in blocks:
            lines = block.strip().splitlines()
            if len(lines) < 2:
                continue
            index = int(lines[0].strip())
            start_str, end_str = lines[1].split(" --> ")
            start = _parse_ts(start_str)
            end = _parse_ts(end_str)
            body = "\n".join(lines[2:])
            cues.append(Cue(index=index, start=start, end=end, text=body))
        return cues

    def save_srt(self, cues: Sequence[Cue], path: Path | str) -> None:
        """Write cues to an SRT file, reindexing cues sequentially.

        Overwrites the destination file using UTF-8 encoding and ensures the file ends with a single trailing newline.

        Parameters:
            cues (Sequence[Cue]): Cues to write; each cue's index will be replaced with its sequential position.
            path (Path | str): Destination file path to write (file will be created or overwritten).
        """
        out_lines = []
        for i, cue in enumerate(cues, start=1):
            cue.index = i  # re-index
            out_lines.append(cue.to_srt())
        Path(path).write_text("\n\n".join(out_lines) + "\n", encoding="utf-8")

    # ---------------------------------------------------------------------
    # Core refinement
    # ---------------------------------------------------------------------
    def refine(self, cues: list[Cue]) -> list[Cue]:
        """Refine subtitle cues by merging short or fast segments, enforcing minimum gaps, and wrapping text to line/block limits.

        Parameters:
            cues (list[Cue]): Input cues to refine.

        Returns:
            list[Cue]: Refined cues with adjusted timings and wrapped text.
        """
        if not cues:
            return []

        cues = self._merge_short_or_fast(cues)
        cues = self._enforce_gaps(cues)
        cues = self._wrap_lines(cues)
        return cues

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _merge_short_or_fast(self, cues: list[Cue]) -> list[Cue]:
        """Refines a sequence of cues by merging adjacent cues when doing so improves readability while respecting configured limits.

        Merges a cue with the following cue when one or more merge triggers are present (current cue duration is shorter than configured minimum unless it is an interjection, characters-per-second exceeds the configured maximum, or the gap to the next cue is smaller than the configured gap) and the merged block would remain within configured limits (merged duration does not exceed max duration, merged text length does not exceed max block characters) and the merged text ends at a permissible boundary. Merged cues preserve the start time of the first cue and adopt the end time and text of the merged block.

        Parameters:
            cues (list[Cue]): Ordered list of subtitle cues to refine.

        Returns:
            list[Cue]: A new list of cues with eligible adjacent cues merged; cues retain their original order and timing constraints are enforced.
        """
        merged: list[Cue] = []
        i = 0
        while i < len(cues):
            current = cues[i]
            while i + 1 < len(cues):
                nxt = cues[i + 1]
                dur = current.end - current.start
                interjection = _is_interjection(current.text)
                cps = len(current.text.replace("\n", " ")) / max(dur, 1e-3)
                gap = nxt.start - current.end

                # Prospective merged values
                prospective_end = nxt.end
                prospective_text = f"{current.text.strip()} \n{nxt.text.strip()}"
                prospective_dur = prospective_end - current.start

                if (
                    (
                        (dur < self.min_dur and not interjection)
                        or cps > self.max_cps
                        or gap < self.gap
                    )
                    and prospective_dur <= self.max_dur
                    and len(prospective_text) <= self.max_block_chars
                    and _is_boundary(prospective_text)  # only merge if boundary reached
                ):
                    # merge
                    current.end = prospective_end
                    current.text = prospective_text
                    i += 1
                else:
                    break
            merged.append(current)
            i += 1
        return merged

    def _enforce_gaps(self, cues: list[Cue]) -> list[Cue]:
        """Ensure a minimum gap between consecutive cues by shifting timings.

        Args:
            cues: Cues whose timings will be adjusted in-place.

        Returns:
            list[Cue]: The adjusted list of cues (same instances as input).

        """
        for prev, curr in zip(cues, cues[1:]):
            required_start = prev.end + self.gap
            if curr.start < required_start:
                shift = required_start - curr.start
                curr.start += shift
                curr.end += shift
        return cues

    def _wrap_lines(self, cues: list[Cue]) -> list[Cue]:
        """Wrap subtitle cue text so each line is at most max_line_chars and each cue contains at most max_lines_per_block lines.

        If a cue would exceed the line limit, this method attempts to split the text at a sentence or clause boundary near the middle, then falls back to splitting near the middle if no suitable boundary is found. The cue.text values are updated in place.

        Args:
            cues (list[Cue]): Cues whose text will be wrapped.

        Returns:
            list[Cue]: The same cue objects with updated text.
        """
        wrapped_cues: list[Cue] = []
        for cue in cues:
            words = cue.text.replace("\n", " ").split()
            new_lines: list[str] = []
            line: list[str] = []
            for word in words:
                prospective = " ".join([*line, word]) if line else word
                if len(prospective) <= self.max_line_chars:
                    line.append(word)
                else:
                    new_lines.append(" ".join(line))
                    line = [word]
            if line:
                new_lines.append(" ".join(line))
            # Smarter split: prefer splitting at punctuation or soft boundary words
            if len(new_lines) > self.max_lines_per_block:
                joined = " ".join(words)
                # try find punctuation near middle
                mid = len(joined) // 2
                punct_idx = max(joined.rfind(ch, 0, mid) for ch in BOUNDARY_CHARS + CLAUSE_CHARS)
                if punct_idx == -1:
                    # try soft boundary word index
                    for w in SOFT_BOUNDARY_WORDS:
                        idx = joined.rfind(f" {w} ", 0, mid)
                        if idx > punct_idx:
                            punct_idx = idx + len(w) // 2
                if punct_idx == -1:
                    punct_idx = joined.rfind(" ", 0, mid)
                    if punct_idx == -1:
                        punct_idx = joined.find(" ", mid)
                new_lines = [
                    joined[:punct_idx].strip(),
                    joined[punct_idx + 1 :].strip(),
                ]
            if len(new_lines) > self.max_lines_per_block:
                joined = " ".join(words)
                mid = len(joined) // 2
                split_idx = joined.rfind(" ", 0, mid)
                if split_idx == -1:
                    split_idx = joined.find(" ", mid)
                new_lines = [
                    joined[:split_idx].strip(),
                    joined[split_idx + 1 :].strip(),
                ]
            cue.text = "\n".join(new_lines)
            wrapped_cues.append(cue)
        return wrapped_cues


def _is_interjection(text: str) -> bool:
    """Determines whether the given text is a standalone interjection listed in INTERJECTION_WHITELIST.

    The check removes any non-letter characters and lowercases the result before comparing.

    Returns:
        True if the cleaned text matches an entry in INTERJECTION_WHITELIST, False otherwise.
    """
    pure = re.sub(r"[^A-Za-z]", "", text).lower()
    return pure in INTERJECTION_WHITELIST


def _is_boundary(text: str) -> bool:
    """Determine whether text ends with a sentence or clause boundary.

    Checks the last character for punctuation in BOUNDARY_CHARS or CLAUSE_CHARS, or whether the final word (after stripping trailing punctuation) is in SOFT_BOUNDARY_WORDS.

    Args:
        text (str): The cue text to inspect.

    Returns:
        bool: True if the text ends with a recognized boundary, False otherwise.
    """
    stripped = text.rstrip()
    if not stripped:
        return False
    last = stripped[-1]
    if last in BOUNDARY_CHARS or last in CLAUSE_CHARS:
        return True
    # Soft boundary word
    last_word = stripped.split()[-1].lower().strip(",;:.")
    return last_word in SOFT_BOUNDARY_WORDS


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def _parse_ts(ts: str) -> float:
    """Convert timestamp ``HH:MM:SS,mmm`` to seconds.

    Args:
        ts: Timestamp string in ``HH:MM:SS,mmm`` format.

    Returns:
        float: The timestamp converted to seconds.

    Raises:
        ValueError: If the timestamp string is not in the expected format.

    """
    match = _TIME_RE.match(ts.strip())
    if not match:
        raise ValueError(f"Invalid timestamp '{ts}'")
    hh, mm, ss, ms = map(int, match.groups())
    return hh * 3600 + mm * 60 + ss + ms / 1000.0


def _format_ts(seconds: float) -> str:
    """Convert seconds to ``HH:MM:SS,mmm`` string.

    Args:
        seconds: Number of seconds to format.

    Returns:
        str: Timestamp string in ``HH:MM:SS,mmm`` format.

    """
    ms_total = int(round(seconds * 1000))
    hh, rem = divmod(ms_total, 3600_000)
    mm, rem = divmod(rem, 60_000)
    ss, ms = divmod(rem, 1000)
    return f"{hh:02d}:{mm:02d}:{ss:02d},{ms:03d}"
