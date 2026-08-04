"""Shared Rich console helpers for consistent, semantic CLI output.

All CLI-facing modules should import from this module instead of using bare
``print()`` or unstyled ``typer.echo()``. The helpers below apply a consistent
color scheme and respect ``--quiet`` and standard terminal environment variables
(``NO_COLOR``, ``TERM=dumb``) through Rich's built-in color detection.
"""

from __future__ import annotations

import sys

from rich.console import Console

__all__ = [
    "get_console",
    "get_stderr_console",
    "print_error",
    "print_info",
    "print_success",
    "print_verbose",
    "print_warning",
]

_CONSOLE: Console | None = None
_STDERR_CONSOLE: Console | None = None


def get_console() -> Console:
    """Return the shared stdout ``Console`` instance.

    The console is created lazily so that environment variables in effect at
    first import are respected. Rich automatically disables color when
    ``NO_COLOR`` is set or ``TERM=dumb`` is detected.

    If stdout has been closed (for example during process shutdown), falls back
    to ``sys.__stdout__`` so diagnostic messages still have a writable stream.
    """
    global _CONSOLE  # noqa: PLW0603
    if _CONSOLE is None:
        stdout = sys.stdout if not sys.stdout.closed else sys.__stdout__
        _CONSOLE = Console(
            file=stdout,
            force_terminal=False,
            markup=False,
            highlight=False,
        )
    return _CONSOLE


def get_stderr_console() -> Console:
    """Return the shared stderr ``Console`` instance.

    Errors and warnings are routed to stderr so they remain visible even when
    stdout is redirected.

    If stderr has been closed, falls back to ``sys.__stderr__``.
    """
    global _STDERR_CONSOLE  # noqa: PLW0603
    if _STDERR_CONSOLE is None:
        stderr = sys.stderr if not sys.stderr.closed else sys.__stderr__
        _STDERR_CONSOLE = Console(
            file=stderr,
            force_terminal=False,
            markup=False,
            highlight=False,
        )
    return _STDERR_CONSOLE


def print_error(message: str, *, quiet: bool = False) -> None:
    """Print an error message to stderr in bold red.

    Args:
        message: Text to render.
        quiet: When ``True``, suppress output entirely.
    """
    if not quiet:
        get_stderr_console().print(message, style="bold red")


def print_warning(message: str, *, quiet: bool = False) -> None:
    """Print a warning message to stderr in yellow.

    Args:
        message: Text to render.
        quiet: When ``True``, suppress output entirely.
    """
    if not quiet:
        get_stderr_console().print(message, style="yellow")


def print_success(message: str, *, quiet: bool = False) -> None:
    """Print a success message to stdout in green.

    Args:
        message: Text to render.
        quiet: When ``True``, suppress output entirely.
    """
    if not quiet:
        get_console().print(message, style="green")


def print_info(message: str, *, quiet: bool = False) -> None:
    """Print an informational status message to stdout in cyan.

    Args:
        message: Text to render.
        quiet: When ``True``, suppress output entirely.
    """
    if not quiet:
        get_console().print(message, style="cyan")


def print_verbose(message: str, *, quiet: bool = False, err: bool = False) -> None:
    """Print a verbose/diagnostic message to stdout (or stderr) in dim text.

    Args:
        message: Text to render.
        quiet: When ``True``, suppress output entirely. Callers should generally
            also gate verbose messages behind a ``verbose`` flag.
        err: When ``True``, print to stderr instead of stdout.
    """
    if quiet:
        return
    if err:
        get_stderr_console().print(message, style="dim")
    else:
        get_console().print(message, style="dim")
