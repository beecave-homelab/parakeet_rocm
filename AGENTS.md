# AGENTS.md — Parakeet-ROCm Agent Guide

This guide documents how to work effectively in the **parakeet-rocm** codebase. It covers setup, architecture, and the required coding rules enforced by Ruff + Pytest. When in doubt, prefer **correctness → clarity → consistency → brevity** (in that order).

## Table of Contents

- [Setup & Commands](#setup--commands)
- [Project Structure](#project-structure)
- [Tech Stack](#tech-stack)
- [Architecture & Patterns](#architecture--patterns)
- [Code Style & Patterns](#code-style--patterns)
  - [1) Correctness (Ruff F - Pyflakes)](#1-correctness-ruff-f---pyflakes)
  - [2) PEP 8 surface rules (Ruff E, W - pycodestyle)](#2-pep-8-surface-rules-ruff-e-w---pycodestyle)
  - [3) Naming conventions (Ruff N - pep8-naming)](#3-naming-conventions-ruff-n---pep8-naming)
  - [4) Imports: order & style (Ruff I - isort rules)](#4-imports-order--style-ruff-i---isort-rules)
  - [5) Docstrings — content & style (Ruff D + DOC)](#5-docstrings--content--style-ruff-d--doc)
  - [6) Import hygiene (Ruff TID - flake8-tidy-imports)](#6-import-hygiene-ruff-tid---flake8-tidy-imports)
  - [7) Modern Python upgrades (Ruff UP - pyupgrade)](#7-modern-python-upgrades-ruff-up---pyupgrade)
  - [8) Future annotations (Ruff FA - flake8-future-annotations)](#8-future-annotations-ruff-fa---flake8-future-annotations)
  - [9) Local ignores (only when justified)](#9-local-ignores-only-when-justified)
  - [10) Tests & examples (Pytest + Coverage)](#10-tests--examples-pytest--coverage)
  - [11) Commit discipline](#11-commit-discipline)
  - [12) Quick DO / DON’T](#12-quick-do--dont)
  - [13) Pre-commit (recommended)](#13-pre-commit-recommended)
  - [14) CI expectations](#14-ci-expectations)
  - [15) SOLID design principles — Explanation & Integration](#15-solid-design-principles--explanation--integration)
  - [16) Configuration management — environment variables & constants](#16-configuration-management--environment-variables--constants)
  - [Final note (code style)](#final-note-code-style)
- [Git / PR Workflow](#git--pr-workflow)
- [Boundaries](#boundaries)
- [Common Tasks](#common-tasks)
- [Troubleshooting](#troubleshooting)

______________________________________________________________________

## Setup & Commands

### Install

**Recommended (Docker / ROCm-enabled runtime):**

```bash
pip install pdm
pdm install -G rocm,webui
docker compose build
```

**Local development prerequisites:** Python 3.10, ROCm 7.0, PDM >= 2.15, and ROCm PyTorch wheels configured in your PDM source list. See `README.md` for the full setup steps and fallbacks.

If you are not using Docker, the fallback dependency install used in README is:

```bash
pdm install -G rocm,webui
# or run in a virtualenv
pip install -r requirements-all.txt
```

### Environment configuration

```bash
cp .env.example .env
```

Environment variables are loaded once in `parakeet_rocm/utils/constant.py`. Do not access `os.environ` elsewhere.

### Run / Dev

```bash
parakeet-rocm --help
parakeet-rocm transcribe data/samples/sample.wav
docker compose up
```

### Tests

```bash
# Fast unit tests only
pdm run pytest tests/unit/

# Full suite (unit + integration + e2e)
pdm run pytest

# Coverage
pdm run pytest tests/unit/ --cov=parakeet_rocm --cov-report=term-missing:skip-covered
```

### Lint / Format

```bash
pdm run ruff check --fix .
pdm run ruff format .
```

### Build

```bash
pdm build
```

### Tooling & scripts

```bash
pdm run local-ci
pdm run srt-diff-report  # PDM dev script (not an installed console command)
bash scripts/clean_codebase.sh
```

______________________________________________________________________

## Project Structure

```text
parakeet_rocm/
├── parakeet_rocm/           # Core package (CLI, pipeline, WebUI, utils)
├── tests/                   # Unit, integration, e2e, and slow tests
├── scripts/                 # CI helpers, report generators, local tooling
├── docs/                    # Additional docs (if present)
├── data/                    # Sample input data
├── output/                  # Default output location
├── docker-compose.yaml      # Docker entrypoints
├── Dockerfile               # Container build
├── project-overview.md      # Architecture + patterns reference
├── TESTING.md               # Test strategy + markers
├── .env.example             # Environment variable reference
└── pyproject.toml           # Dependencies, scripts, Ruff, Pytest config
```

**Key package areas:**

- `parakeet_rocm/cli.py`: Typer CLI entrypoint and command wiring.
- `parakeet_rocm/transcription/`: File processing pipeline and protocols.
- `parakeet_rocm/chunking/`: Chunking and merge strategies.
- `parakeet_rocm/formatting/`: Output formatter registry and implementations.
- `parakeet_rocm/webui/`: Gradio WebUI app and UI components.
- `parakeet_rocm/utils/`: Constants, env loader, path helpers, audio I/O.

**Path aliases:** None. Use absolute imports from `parakeet_rocm`.

______________________________________________________________________

## Tech Stack

### Core

- Python 3.10 (runtime and typing target)
- PDM (dependency management and scripts)
- Hatchling (build backend)

### CLI & UX

- Typer + Rich for CLI commands, progress, and help output

### ASR + Audio

- NVIDIA NeMo ASR toolkit, plus torch/torchaudio ROCm builds (optional group)
- Stable-ts, Silero VAD, Demucs for refinement and pre-processing
- librosa, soundfile, pydub, numpy, scipy for audio handling

### Dev Tooling

- Ruff for linting/formatting
- Pytest + pytest-cov for tests and coverage

### Optional Web UI

- Gradio WebUI (`parakeet_rocm/webui`) via the `webui` extra

### Benchmarks

- `pyamdgpuinfo` for optional GPU metric collection (bench extra)

______________________________________________________________________

## Architecture & Patterns

The project uses a layered architecture that separates CLI orchestration, model handling, pipeline processing, WebUI, and utilities. Key patterns include:

- **Protocols for dependency injection** (e.g., `SupportsTranscribe`, `Formatter`) to decouple ASR backends.
- **Registry pattern** for output formatters and merge strategies.
- **Lazy imports** for heavy dependencies (NeMo, stable-ts, Gradio) to keep startup light.
- **Centralized configuration** in `parakeet_rocm/utils/constant.py`, loaded once by `env_loader`.

### Required approach when extending functionality (modular-first)

When adding features, agents **must extend via modules/interfaces**, not by piling logic into existing entrypoints.

1. **Respect layer boundaries**

   - Keep `cli.py`, API routes, and WebUI handlers as thin orchestration layers.
   - Put domain logic in dedicated package modules (for example `transcription/`, `chunking/`, `formatting/`, `api/`).
   - Avoid cross-layer shortcuts (for example WebUI code directly mutating transcription internals).

2. **Prefer extension points over conditionals**

   - Add/extend protocols, strategies, and registries instead of introducing large `if/elif` trees in hot paths.
   - New behavior should be pluggable (new implementation + registration), not invasive edits across many callers.

3. **Centralize configuration for new features**

   - New env/config values must be added in `parakeet_rocm/utils/constant.py` and documented in `.env.example`.
   - Do not read `os.getenv`/`os.environ` in feature modules.

4. **Keep dependencies injectable and testable**

   - Depend on abstractions (`Protocol`/ABC) where practical.
   - Add unit tests for new modules and integration tests for wiring (CLI/API/WebUI) without duplicating heavy logic.

5. **Make changes coherent with existing architecture docs**

   - If the feature introduces a new module boundary or pattern, update `project-overview.md` and relevant docstrings.

### Modular extension anti-patterns (must avoid)

- Adding business logic directly in CLI command functions, route handlers, or UI callback bodies.
- Introducing feature flags as scattered conditionals across unrelated modules.
- Duplicating mapping/validation/config logic separately for CLI, API, and WebUI.
- Adding new integration behavior without a protocol/strategy boundary when one is warranted.

Refer to `project-overview.md` for the full data flow diagrams and architectural notes.

______________________________________________________________________

## Code Style & Patterns

This repository uses **Ruff** as the single source of truth for linting/formatting and **Pytest** (with **pytest-cov**) for tests & coverage. CI fails when these rules are violated.

Run locally before committing:

```bash
# Lint & format (Ruff)
pdm run ruff check --fix .
pdm run ruff format .

# Tests & coverage (adjust --cov target if needed)
pdm run pytest --maxfail=1 -q
pdm run pytest --cov=. --cov-report=term-missing:skip-covered --cov-report=xml
```

When in doubt, prefer **correctness → clarity → consistency → brevity** (in that order).

______________________________________________________________________

## 1) Correctness (Ruff F - Pyflakes)

### What It Enforces — Correctness

- No undefined names/variables.
- No unused imports/variables/arguments.
- No duplicate arguments in function definitions.
- No `import *`.

### Agent Checklist — Correctness

- Remove dead code and unused symbols.
- Keep imports minimal and explicit.
- Use local scopes (comprehensions, context managers) where appropriate.
- Do **not** read configuration from `os.environ` directly outside the dedicated constants module (see section 16).

______________________________________________________________________

### 2) PEP 8 surface rules (Ruff E, W - pycodestyle)

### What It Enforces — PEP 8 Surface

- Spacing/blank-line/indentation hygiene.
- No trailing whitespace.
- Reasonable line breaks; respect the configured line length (see `pyproject.toml` or `ruff.toml`).

### Agent Checklist — PEP 8 Surface

- Let the formatter handle whitespace.
- Break long expressions cleanly (after operators, around commas).
- End files with exactly one trailing newline.

______________________________________________________________________

### 3) Naming conventions (Ruff N - pep8-naming)

### What It Enforces — Naming

- `snake_case` for functions, methods, and non-constant variables.
- `CapWords` (PascalCase) for classes.
- `UPPER_CASE` for module-level constants.
- Exceptions end with `Error` and subclass `Exception`.

### Agent Checklist — Naming

- Avoid camelCase unless mirroring a third-party API; if unavoidable, use a targeted pragma for that line only.

______________________________________________________________________

### 4) Imports: order & style (Ruff I - isort rules)

### What It Enforces — Imports

- Group imports: 1) Standard library, 2) Third-party, 3) First-party/local.
- Alphabetical within groups; one blank line between groups.
- Prefer one import per line for clarity.

### Agent Checklist — Imports

- Keep imports at module scope (top of file).
- Only alias when it adds clarity (e.g., `import numpy as np`).

### Canonical example — Imports

```python
from __future__ import annotations

import dataclasses
import pathlib

import httpx
import pydantic

from yourpkg.core import config
from yourpkg.utils.paths import ensure_dir
```

*(Replace `yourpkg` with your top-level package. In app-only repos, keep first-party imports minimal.)*

______________________________________________________________________

### 5) Docstrings — content & style (Ruff D + DOC)

Public modules, classes, functions, and methods **must have docstrings**. Ruff enforces **pydocstyle** (`D…`) and **pydoclint** (`DOC…`).

**Single-source style**: **Google-style** docstrings with type hints in signatures.

### Rules of Thumb — Docstrings

- Triple double quotes.
- First line: one-sentence summary, capitalized, ends with a period.
- Blank line after summary, then details.
- Keep `Args/Returns/Raises` in sync with the signature.
- Use imperative mood (“Return…”, “Validate…”). Don’t repeat obvious types (use type hints).

### Function Template — Docstrings

```python
def frobnicate(path: pathlib.Path, *, force: bool = False) -> str:
    """Frobnicate the resource at ``path``.

    Performs an idempotent frobnication. If ``force`` is true, existing
    artifacts will be replaced.

    Args:
        path: Filesystem location of the target resource.
        force: Replace previously generated artifacts if present.

    Returns:
        A stable identifier for the frobnicated resource.

    Raises:
        FileNotFoundError: If ``path`` does not exist.
        PermissionError: If write access is denied.
    """
```

### Class Template — Docstrings

```python
class ResourceManager:
    """Coordinate creation and lifecycle of resources.

    Notes:
        Thread-safe for read operations; writes are serialized.
    """
```

______________________________________________________________________

### 6) Import hygiene (Ruff TID - flake8-tidy-imports)

### What It Enforces — Import Hygiene

- Prefer absolute imports over deep relative imports.
- Avoid circular imports; import inside functions only for performance or to break a cycle.
- Avoid broad implicit re-exports; if you re-export, do it explicitly via `__all__`.

### Agent Checklist — Import Hygiene

```python
try:
    import rich
except ModuleNotFoundError:  # pragma: no cover
    rich = None  # type: ignore[assignment]
```

______________________________________________________________________

### 7) Modern Python upgrades (Ruff UP - pyupgrade)

### What It Prefers — Modernization

- f-strings over `format()` / `%`.
- PEP 585 generics (`list[str]`, `dict[str, int]`) over `typing.List`, `typing.Dict`, etc.
- Context managers where appropriate.
- Remove legacy constructs (`six`, `u''`, redundant `object`).

### Agent Checklist — Modernization

- Use `pathlib.Path` for filesystem paths.
- Use assignment expressions (`:=`) sparingly and only when clearer.
- Prefer `is None`/`is not None`.

______________________________________________________________________

### 8) Future annotations (Ruff FA - flake8-future-annotations)

### Guidance — Future Annotations

- Targeting **Python < 3.11**: place at the top of every module:

  ```python
  from __future__ import annotations
  ```

- Targeting **Python ≥ 3.11**: you may omit it; align the `FA` rule in Ruff config.

______________________________________________________________________

### 9) Local ignores (only when justified)

### Policy — Local Ignores

Prefer fixing the root cause. If a one-off ignore is necessary, keep it **scoped and documented**:

```python
value = compute()  # noqa: F401  # used by plugin loader via reflection
```

For docstring mismatches caused by third-party constraints, use a targeted `# noqa: D…, DOC…` with a brief reason.

______________________________________________________________________

### 10) Tests & examples (Pytest + Coverage)

### Expectations — Tests

- Tests follow the same rules as production code.
- Naming: `test_<unit_under_test>__<expected_behavior>()`.
- Keep tests deterministic; avoid hidden network/filesystem dependencies without fixtures.

### Minimal Example — Tests

```python
def add(a: int, b: int) -> int:
    """Return the sum of two integers.

    Examples:
        >>> add(2, 3)
        5
    """
```

### Running — Tests & Coverage

```bash
# Quick
pdm run pytest -q

# Coverage (adjust --cov target to your package or ".")
pdm run pytest --cov=. --cov-report=term-missing:skip-covered --cov-report=xml
```

### Coverage Policy — Threshold

- Guideline: **≥ 85%** line coverage, with critical paths covered.
- Make CI fail below the threshold (see “CI expectations”).

______________________________________________________________________

### 11) Commit discipline

### Expectations — Commits

Run Ruff and tests **before** committing. Keep commits small and focused.

Use your project’s conventional commit format.

______________________________________________________________________

### 12) Quick DO / DON’T

### DO — Practices

- Google-style docstrings that match signatures.
- Absolute imports and sorted import blocks.
- f-strings and modern type syntax (`list[str]`).
- Remove unused code promptly.
- Use Pytest fixtures for reusable setup; prefer `tmp_path` for temp files.

### DON’T — Anti-patterns

- Introduce camelCase (except when mirroring external APIs).
- Use `import *` or deep relative imports.
- Leave parameters undocumented in public functions.
- Add broad `noqa`—always keep ignores narrow and justified.

______________________________________________________________________

### 13) Pre-commit (recommended)

### Configuration — Pre-commit

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.6.9  # keep in sync with your chosen Ruff version
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
```

______________________________________________________________________

### 14) CI expectations

### Commands — CI

```bash
# Lint & format
pdm run ruff check .
pdm run ruff format --check .

# Tests & coverage
pdm run pytest --cov=. --cov-report=term-missing:skip-covered --cov-report=xml --maxfail=1
```

### Policy — CI Coverage

Enforce a minimum coverage threshold (example: 85%). Fail the pipeline if below.

______________________________________________________________________

### 15) SOLID design principles — Explanation & Integration

The **SOLID** principles help you design maintainable, testable, and extensible Python code. This section explains each principle concisely and shows how it maps to our linting, docs, and tests.

### S — Single Responsibility Principle (SRP)

- **Definition**: A module/class should have **one reason to change** (one cohesive responsibility).
- **Pythonic approach**:
  - Keep classes small; factor out I/O, parsing, and domain logic into distinct units.
  - Prefer composition over “god classes”.
- **In practice**:
  - Split functions that both “validate & write to disk” into separate units.
  - Move side-effects (I/O, network) behind narrow interfaces.
- **How we enforce/integrate**:
  - **Docs**: Each public class/function docstring states its single responsibility.
  - **Tests**: Unit tests focus on one behavior per test (narrow fixtures).
  - **Lint**: Large files/functions are a smell (consider refactor even if Ruff passes).

### O — Open/Closed Principle (OCP)

- **Definition**: Software entities should be **open for extension, closed for modification**.
- **Pythonic approach**:
  - Rely on **polymorphism** via abstract base classes or `typing.Protocol`.
  - Inject strategies or policies instead of hard-coding conditionals.
- **In practice**:
  - Define `Storage` protocol with `write()` and implement `FileStorage`, `S3Storage` without changing callers.
- **How we enforce/integrate**:
  - **Docs**: Document stable extension points (interfaces/protocols) in module/class docstrings.
  - **Tests**: Parametrize tests across multiple implementations to validate substitutability.
  - **Lint**: Keep imports clean; avoid “if type == …” switches in hot paths.

### L — Liskov Substitution Principle (LSP)

- **Definition**: Subtypes must be **substitutable** for their base types without breaking expectations.
- **Pythonic approach**:
  - Subclasses must not strengthen preconditions or weaken postconditions.
  - Keep method signatures compatible (types/return values/raised errors).
- **In practice**:
  - If base `Repository.get(id) -> Model | None`, a subtype must not start raising on “not found”.
- **How we enforce/integrate**:
  - **Docs**: State behavioral contracts and possible exceptions in docstrings.
  - **Tests**: Run the same behavior tests against base and derived implementations (parametrized).
  - **Lint**: Ruff won’t prove LSP, but naming and import rules reduce confusion; rely on tests/contracts.

### I — Interface Segregation Principle (ISP)

- **Definition**: Prefer **small, role-specific interfaces** over fat interfaces.
- **Pythonic approach**:
  - Use multiple `Protocol`s (or ABCs) with narrowly scoped methods.
  - Accept only what you need at call sites (e.g., `Readable` protocol, not `FileLikeAndNetworkAndCache`).
- **In practice**:
  - Split `DataStore` into `Readable` and `Writable` where consumers only need one.
- **How we enforce/integrate**:
  - **Docs**: Clarify the minimal interface needed by a function/class (in the Args section).
  - **Tests**: Provide tiny fakes/mocks that implement just the required protocol.
  - **Lint**: Keep imports modular; avoid cyclic dependencies driven by bloated interfaces.

### D — Dependency Inversion Principle (DIP)

- **Definition**: High-level modules **depend on abstractions**, not concrete details.
- **Pythonic approach**:
  - Use constructor or function **dependency injection** of protocols/ABCs.
  - Keep wiring in a thin composition/bootstrap layer.
- **In practice**:
  - Class accepts `Clock` protocol; production uses `SystemClock`, tests pass `FrozenClock`.
- **How we enforce/integrate**:
  - **Docs**: Document injected dependencies and their contracts.
  - **Tests**: Replace dependencies with fakes/stubs; no slow/global state in unit tests.
  - **Lint**: Absolute imports and clean layering reduce unintended tight coupling.

### SOLID — Minimal example (Protocols + DI)

```python
from __future__ import annotations
from typing import Protocol
import pathlib

class Storage(Protocol):
    def write(self, path: pathlib.Path, data: bytes) -> None: ...

class FileStorage:
    def write(self, path: pathlib.Path, data: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

class Uploader:
    """Upload artifacts using an injected Storage (DIP, OCP, ISP).

    Args:
        storage: Minimal interface that supports 'write'.
    """
    def __init__(self, storage: Storage) -> None:
        self._storage = storage  # DIP

    def publish(self, dest: pathlib.Path, payload: bytes) -> None:
        # SRP: only orchestrates publication; no direct filesystem logic here.
        self._storage.write(dest, payload)

# LSP test idea: any Storage conformer can be used transparently (FakeStorage, S3Storage, ...).
```

### SOLID — Agent Checklist

- **SRP**: One responsibility per module/class; split I/O from domain logic.
- **OCP**: Use protocols/ABCs and strategy injection to extend without edits.
- **LSP**: Keep subtype behavior/contract compatible; parametrize tests over implementations.
- **ISP**: Prefer small protocols; accept only what you need.
- **DIP**: Depend on abstractions; inject dependencies (avoid hard-coded singletons/globals).

______________________________________________________________________

### 16) Configuration management — environment variables & constants

These rules standardize how environment variables are loaded and accessed across the codebase. They prevent config sprawl, enable testing, and align with **SRP** and **DIP**.

### 16.1 Single loading point

- Environment variables are parsed **exactly once** at application start.
- The loader function is `load_project_env()` located at `parakeet_rocm/utils/env_loader.py` and is invoked only from `parakeet_rocm/utils/constant.py`.

### 16.2 Central import location

- `load_project_env()` **MUST** be invoked **only** inside `parakeet_rocm/utils/constant.py`.
- No other file may import `env_loader` or call `load_project_env()` directly.

### 16.3 Constant exposure

- After loading, `parakeet_rocm/utils/constant.py` exposes project-wide configuration constants (e.g., `DEFAULT_CHUNK_LEN_SEC`, `DEFAULT_BATCH_SIZE`).
- All other modules (e.g., `parakeet_rocm/cli.py`, `parakeet_rocm/transcription/file_processor.py`) **must import from** `parakeet_rocm.utils.constant` instead of reading `os.environ` or `.env`.

### 16.4 Adding new variables

- Define a sensible default in `parakeet_rocm/utils/constant.py` using `os.getenv("VAR_NAME", "default")` or typed parsing logic.
- Document every variable in `.env.example` with a short description and default.

Note: The OpenAI-compatible API can override its model independently via
`API_MODEL_NAME` (``whisper-1`` resolves to this value). This also controls API
warmup/offload behavior.

### 16.5 Enforcement policy

- Pull requests that add direct `os.environ[...]` access or import `env_loader` outside `utils/constant.py` **must be rejected**.

- Suggested CI guardrail (example grep check):

  ```bash
  # deny direct env reads outside constants module
  ! git grep -nE 'os\\.environ\\[|os\\.getenv\\(' -- ':!parakeet_rocm/utils/constant.py' ':!**/tests/**'
  ```

### 16.6 Logging policy (centralized only)

- All application logging (CLI, API, WebUI, transcription, benchmarks, background workers) **must** use `parakeet_rocm/utils/logging_config.py` as the single logging entrypoint.
- Logger instances must be created via `from parakeet_rocm.utils.logging_config import get_logger` and `logger = get_logger(__name__)`.
- Logging setup/configuration must go through `configure_logging(...)`; do **not** call `logging.basicConfig(...)`, `logging.disable(...)`, or ad-hoc global logging configuration outside `logging_config.py`.
- Direct `import logging` in feature modules should be avoided unless strictly required for non-configuration internals; direct `logging.getLogger(...)` usage outside `logging_config.py` is disallowed.
- Pull requests introducing non-centralized logging patterns **must be rejected**.

- Suggested CI guardrail (example grep checks):

  ```bash
  # deny direct logger construction outside centralized logging module
  ! git grep -n 'logging.getLogger(' -- ':!parakeet_rocm/utils/logging_config.py' ':!**/tests/**'

  # deny ad-hoc logging setup outside centralized logging module
  ! git grep -nE 'logging\\.basicConfig\\(|logging\\.disable\\(' -- ':!parakeet_rocm/utils/logging_config.py' ':!**/tests/**'
  ```

### 16.7 Example layout (illustrative)

```python
# parakeet_rocm/utils/env_loader.py
from __future__ import annotations

from dotenv import load_dotenv


def load_project_env() -> None:
    """Load environment variables from .env (if present)."""
    load_dotenv()
```

```python
# parakeet_rocm/utils/constant.py
from __future__ import annotations

import os

from parakeet_rocm.utils.env_loader import load_project_env


# Load once (single source of truth)
load_project_env()

# Exposed constants (typed, with sensible defaults)
DEFAULT_CHUNK_LEN_SEC: int = int(os.getenv("CHUNK_LEN_SEC", "300"))
DEFAULT_BATCH_SIZE: int = int(os.getenv("BATCH_SIZE", "12"))
PARAKEET_MODEL_NAME: str = os.getenv("PARAKEET_MODEL_NAME", "nvidia/parakeet-tdt-0.6b-v3")
```

```python
# parakeet_rocm/cli.py  (or any other module)
from __future__ import annotations
from parakeet_rocm.utils.constant import DEFAULT_BATCH_SIZE

def run() -> None:
    # Use constants; do not read os.environ here
    ...
```

### 16.8 Testing guidance for configuration

- Unit tests may override constants via monkeypatching the **constants module attributes**, not the environment loader:

  ```python
  def test_behavior_with_small_batch(monkeypatch):
      import parakeet_rocm.utils.constant as C
      monkeypatch.setattr(C, "DEFAULT_BATCH_SIZE", 2, raising=True)
      ...
  ```

- For integration tests that need environment variations, set env **before** importing `parakeet_rocm.utils.constant` to ensure one-time load semantics and update the correct variable (`BATCH_SIZE`) used by the constants module:

  ```python
  import importlib
  import os

  os.environ["BATCH_SIZE"] = "4"
  import parakeet_rocm.utils.constant as C

  importlib.reload(C)  # if necessary in the same process
  ```

- Document any new variables in `.env.example` and ensure coverage includes both defaulted and overridden paths.

### 16.9 Build guidance

- When building the project, ensure that the `parakeet_rocm/utils/constant.py` file is updated with the latest environment variables.
- Use the `pdm build` command to build the project.

### Final note (code style)

If you must deviate (e.g., third-party naming or unavoidable import patterns), add a **short comment** explaining why and keep the ignore as narrow as possible.

______________________________________________________________________

## Git / PR Workflow

- Run `pdm run ruff check --fix .`, `pdm run ruff format .`, and relevant pytest suites before opening a PR.
- Keep commits small and focused; follow the repository's conventional commit format.
- For major changes, open an issue or discussion first (as noted in `README.md`).

______________________________________________________________________

## Boundaries

### ✅ Always

- Centralize configuration in `parakeet_rocm/utils/constant.py` and document changes in `.env.example`.
- Use safe, validated filesystem paths only. Always validate inputs (reject URLs/option-style paths, confine to configured roots like `SRT_SAFE_ROOT`) before any file I/O to avoid CodeQL alerts and path traversal risks.
- Keep new CLI options in sync with Typer help output and the README usage examples.
- Add or update tests alongside behavior changes; prefer unit tests for core logic.

### ⚠️ Ask First

- Changing default model IDs, batch sizes, or chunking behavior.
- Modifying Docker base images, ROCm versions, or GPU requirements.
- Reworking CLI command names or output format semantics.

### 🚫 Never

- Read environment variables directly outside the constants module.
- Add GPU-heavy tests to the default test suite without proper markers and skips.
- Remove ROCm compatibility or optional dependency groups without review.

______________________________________________________________________

## Common Tasks

### Run a transcription locally

```bash
parakeet-rocm transcribe data/samples/sample.wav
```

### Add a new output format

1. Implement the formatter in `parakeet_rocm/formatting/`.
2. Register it in the formatter registry (`parakeet_rocm/formatting/__init__.py`).
3. Add tests in `tests/unit/` and update README usage if exposed to CLI.

### Add a new merge strategy

1. Add the function in `parakeet_rocm/chunking/merge.py`.
2. Register it in `MERGE_STRATEGIES` and cover with unit tests.

### Add a new environment variable

1. Add the default in `parakeet_rocm/utils/constant.py`.
2. Document it in `.env.example`.
3. Add tests that monkeypatch the constant or reload the module as needed.

### Launch the WebUI

```bash
parakeet-rocm webui
```

### Run a targeted test suite

```bash
pdm run pytest tests/unit/test_formatting.py::test_srt_formatter_basic
```

______________________________________________________________________

## Troubleshooting

### ROCm or GPU installation issues

- Prefer Docker setup when local ROCm tooling is unreliable.
- Ensure ROCm 7.0 matches the expected version in pyproject and Docker builds.
- Verify `PYTORCH_HIP_ALLOC_CONF` and `HSA_OVERRIDE_GFX_VERSION` are set per `.env.example`.

### GPU tests failing in CI

- Ensure tests are marked with `@pytest.mark.gpu`, `@pytest.mark.slow`, and `@pytest.mark.e2e`.
- Skip GPU tests when `CI=true` to keep pipelines green.

### Missing configuration

- If the app fails on startup, confirm `.env` exists and was copied from `.env.example`.
