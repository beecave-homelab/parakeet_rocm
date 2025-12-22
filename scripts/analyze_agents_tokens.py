"""Analyze token usage for an AGENTS.md-style instruction file.

This script helps you understand roughly how much context budget an instruction
file consumes. It reports:
- Line count
- Word count
- Token count (uses ``tiktoken`` if installed; otherwise a heuristic)
- A severity band (green/yellow/orange/red) based on token thresholds

The goal is to let you keep AGENTS.md within a target budget so it can be
included in agent prompts without crowding out task context.
"""

from __future__ import annotations

import argparse
import pathlib
import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class Thresholds:
    """Token thresholds for classification.

    The bands are inclusive of the lower bound and exclusive of the next band's
    lower bound.

    Attributes:
        green_max: Upper bound for the green band.
        yellow_max: Upper bound for the yellow band.
        orange_max: Upper bound for the orange band.
    """

    green_max: int
    yellow_max: int
    orange_max: int


@dataclass(frozen=True)
class AnalysisResult:
    """Aggregate statistics for a single text file.

    Attributes:
        path: Filesystem path that was analyzed.
        lines: Number of newline-delimited lines.
        words: Number of whitespace-separated words.
        tokens: Number of tokens (exact if ``tiktoken`` is available; otherwise
            estimated).
        token_method: Description of the method used for token counting.
    """

    path: pathlib.Path
    lines: int
    words: int
    tokens: int
    token_method: str


def _count_words(text: str) -> int:
    """Count words in a string.

    Args:
        text: Input text.

    Returns:
        Number of whitespace-separated words.
    """
    return len(text.split())


def _count_lines(text: str) -> int:
    """Count lines in a string.

    Args:
        text: Input text.

    Returns:
        Number of lines.
    """
    return 0 if not text else text.count("\n") + 1


def _try_count_tokens_tiktoken(text: str, model: str) -> tuple[int, str] | None:
    """Count tokens using ``tiktoken`` if available.

    Args:
        text: Input text.
        model: Model name used to select an encoding.

    Returns:
        Tuple of (tokens, method_description) if available; otherwise None.
    """
    try:
        import tiktoken  # type: ignore
    except ModuleNotFoundError:
        return None

    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        encoding = tiktoken.get_encoding("cl100k_base")

    return len(encoding.encode(text)), f"tiktoken({encoding.name})"


def _count_tokens_heuristic(text: str) -> tuple[int, str]:
    """Estimate tokens when exact tokenization is unavailable.

    This uses a pragmatic heuristic that tends to be "good enough" for
    markdown/English text:

    - 1 token ~= 4 characters (OpenAI guidance) for typical English.
    - We take the max of char-based estimate and a word-based estimate.

    Args:
        text: Input text.

    Returns:
        Tuple of (estimated_tokens, method_description).
    """
    stripped = text.strip()
    if not stripped:
        return 0, "heuristic(empty)"

    chars = len(stripped)
    words = _count_words(stripped)

    char_estimate = max(1, round(chars / 4))
    word_estimate = max(1, round(words / 0.75))

    return max(char_estimate, word_estimate), "heuristic(max(chars/4, words/0.75))"


def analyze_file(path: pathlib.Path, *, model: str) -> AnalysisResult:
    """Analyze a text file and compute lines/words/tokens.

    Args:
        path: Path to the file to analyze.
        model: Model name to use for selecting a tokenizer when ``tiktoken`` is
            available.

    Returns:
        The computed analysis result.

    Raises:
        FileNotFoundError: If ``path`` does not exist.
        IsADirectoryError: If ``path`` is a directory.
        UnicodeDecodeError: If the file cannot be decoded as UTF-8.
    """
    if not path.exists():
        raise FileNotFoundError(str(path))
    if path.is_dir():
        raise IsADirectoryError(str(path))

    text = path.read_text(encoding="utf-8")

    lines = _count_lines(text)
    words = _count_words(text)

    tiktoken_result = _try_count_tokens_tiktoken(text, model=model)
    if tiktoken_result is not None:
        tokens, token_method = tiktoken_result
    else:
        tokens, token_method = _count_tokens_heuristic(text)

    return AnalysisResult(
        path=path,
        lines=lines,
        words=words,
        tokens=tokens,
        token_method=token_method,
    )


def classify_tokens(tokens: int, thresholds: Thresholds) -> str:
    """Classify token usage into a severity band.

    Args:
        tokens: Token count.
        thresholds: Threshold configuration.

    Returns:
        One of: "green", "yellow", "orange", "red".
    """
    if tokens <= thresholds.green_max:
        return "green"
    if tokens <= thresholds.yellow_max:
        return "yellow"
    if tokens <= thresholds.orange_max:
        return "orange"
    return "red"


def _format_human_int(value: int) -> str:
    """Format an integer with thousands separators.

    Args:
        value: Integer value.

    Returns:
        Human-friendly string.
    """
    return f"{value:,}"


def _build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser.

    Returns:
        Configured argument parser.
    """
    parser = argparse.ArgumentParser(
        prog="analyze_agents_tokens.py",
        description="Analyze lines/words/tokens for AGENTS.md and classify usage.",
    )
    parser.add_argument(
        "path",
        nargs="?",
        default="AGENTS.md",
        help="Path to AGENTS.md (default: ./AGENTS.md)",
    )
    parser.add_argument(
        "--model",
        default="gpt-4o-mini",
        help=(
            "Tokenizer model name for tiktoken (default: gpt-4o-mini). "
            "If unknown, cl100k_base will be used."
        ),
    )
    parser.add_argument(
        "--green-max",
        type=int,
        default=2_000,
        help="Max tokens for green (default: 2000)",
    )
    parser.add_argument(
        "--yellow-max",
        type=int,
        default=4_000,
        help="Max tokens for yellow (default: 4000)",
    )
    parser.add_argument(
        "--orange-max",
        type=int,
        default=8_000,
        help="Max tokens for orange (default: 8000)",
    )
    return parser


def main() -> int:
    """Run the CLI entrypoint.

    Returns:
        Process exit code.
    """
    parser = _build_parser()
    args = parser.parse_args()

    thresholds = Thresholds(
        green_max=args.green_max,
        yellow_max=args.yellow_max,
        orange_max=args.orange_max,
    )

    try:
        result = analyze_file(pathlib.Path(args.path), model=args.model)
    except (FileNotFoundError, IsADirectoryError, UnicodeDecodeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    band = classify_tokens(result.tokens, thresholds)

    print("AGENTS.md Token Usage")
    print("=")
    print(f"Path:        {result.path}")
    print(f"Lines:       {_format_human_int(result.lines)}")
    print(f"Words:       {_format_human_int(result.words)}")
    print(f"Tokens:      {_format_human_int(result.tokens)}")
    print(f"Tokenizer:   {result.token_method}")
    print("-")
    print("Thresholds (tokens)")
    print(f"  green:  <= {_format_human_int(thresholds.green_max)}")
    print(
        f"  yellow: <= {_format_human_int(thresholds.yellow_max)}"
        f" (>{_format_human_int(thresholds.green_max)})"
    )
    print(
        f"  orange: <= {_format_human_int(thresholds.orange_max)}"
        f" (>{_format_human_int(thresholds.yellow_max)})"
    )
    print(f"  red:    >  {_format_human_int(thresholds.orange_max)}")
    print("-")
    print(f"Status: {band}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
