# AGENTS.md – OpenAI Codex & AI Agent Guide for parakeet_rocm

This file provides authoritative instructions for OpenAI Codex and all AI agents working within this repository. It documents project structure, coding conventions, environment variable policy, testing protocols, and PR guidelines. **All agents must strictly adhere to these rules for any code or documentation changes.**

---

## 1. Project Structure

- **Root Directory**
  - `Dockerfile`, `docker-compose.yaml`: Containerization for ROCm/NeMo ASR service.
  - `pyproject.toml`: Python dependencies (PDM-managed).
  - `.env.example`: Environment variable template.
  - `README.md`: Quick-start and usage.
  - `project-overview.md`: In-depth codebase and architecture documentation.
- **parakeet_rocm/**
  - `cli.py`: Typer CLI entry point.
  - `transcribe.py`: Batch transcription logic.
  - `chunking/merge.py`: Segment merging for long audio.
  - `timestamps/segmentation.py`: Subtitle segmentation.
  - `formatting/`: Output formatters (SRT, TXT, etc.).
  - `utils/`: Shared helpers (audio I/O, file utils, constants, env loader, and new *watcher*).
    - `utils/file_utils.py`: Extension allow-list & wildcard resolver (`resolve_input_paths` function).
    - `utils/watch.py`: Polling watcher used by the new `--watch` CLI flag.
  - `models/parakeet.py`: Model wrapper.
- **tests/**: Unit and integration tests for all major modules.
- **scripts/**: Utility scripts for requirements and dev shell.
- **data/**: Sample audio and output directory.

---

## 2. Python Linting & Style Guide (Ruff-based)

This repository uses Ruff as the single source of truth for Python linting and formatting. If your change violates these rules, CI will fail.

- Run locally before committing:
  - `pdm run ruff check --fix .`
  - `pdm run ruff format .`

When in doubt, prefer correctness → clarity → consistency → brevity (in that order).

### 2.1 Correctness (Ruff F — Pyflakes)

- No undefined names or variables.
- No unused imports/variables/arguments.
- No duplicate arguments in function definitions.
- No `import *`.

Agent checklist:

- Delete dead code and unused symbols.
- Keep imports minimal and explicit.
- If a variable is only used in a comprehension, don’t keep it outside the scope.

### 2.2 PEP 8 surface rules (Ruff E, W — pycodestyle)

- Basic spacing/blank-line/indentation hygiene; no trailing whitespace.
- Reasonable line breaks; respect the project’s configured line length in `ruff.toml`.

Agent checklist:

- Let the formatter handle whitespace; don’t fight it.
- Break long expressions cleanly (after operators, around commas, etc.).
- Ensure each file ends with a single newline.

### 2.3 Naming conventions (Ruff N — pep8-naming)

- `snake_case` for functions, methods, and non-constant variables.
- `CapWords` (PascalCase) for classes.
- `UPPER_CASE` for module-level constants.
- Exception classes should be named `SomethingError` and subclass `Exception`.

Agent checklist:

- Don’t introduce camelCase unless mirroring a third-party API; if you must, add a local pragma to silence N for that line only.

### 2.4 Imports: order & style (Ruff I — isort rules)

- Group imports in this order with one blank line between groups: 1) Standard library, 2) Third-party, 3) First-party/local.
- Alphabetical within groups; prefer one import per line for clarity.
- Keep all imports at module scope (top-of-file).
- Prefer explicit, absolute imports over relative.

Canonical example:

```python
from __future__ import annotations

import dataclasses
import pathlib

import httpx
import pydantic

from mypkg.core import config
from mypkg.utils.paths import ensure_dir
```

### 2.5 Docstrings — content & style (Ruff D + DOC)

This codebase requires docstrings for public modules, classes, functions, and methods. Ruff enforces both pydocstyle (D…) and pydoclint (DOC…) checks.

- Single-source style: Google-style docstrings with type hints in signatures.
- Triple double quotes.
- First line: one-sentence summary, capitalized, ends with a period.
- Blank line after summary; then details.
- Keep `Args`/`Returns`/`Raises` in sync with the signature.
- Use imperative mood and avoid repetition of obvious types (use the type hints).

Function template:

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

Class template:

```python
class ResourceManager:
    """Coordinate creation and lifecycle of resources.

    Notes:
        Thread-safe for read operations; writes are serialized.
    """
```

### 2.6 Import hygiene (Ruff TID — flake8-tidy-imports)

- Prefer absolute imports over deep relative imports.
- Avoid circular imports; don’t import inside functions unless necessary for performance or to break a cycle.
- Avoid implicit re-exports; if you re-export, do it explicitly via `__all__`.

Gate optional imports like this:

```python
try:
    import rich
except ModuleNotFoundError:  # pragma: no cover
    rich = None  # type: ignore[assignment]
```

### 2.7 Modern Python upgrades (Ruff UP — pyupgrade)

- Prefer f-strings over `format()` / `%` formatting.
- Use PEP 585 generics (e.g., `list[str]`, `dict[str, int]`) over `typing.List`/`typing.Dict`.
- Use context managers where appropriate.
- Remove legacy constructs (e.g., `six`, `u''` prefixes, redundant `object` inheritance).

Agent checklist:

- Prefer `pathlib.Path` to raw string paths.
- Prefer assignment expressions (`:=`) sparingly when they improve clarity.
- Use `is None`/`is not None` for null checks.

### 2.8 Future annotations (Ruff FA — flake8-future-annotations)

- Each Python module must begin with `from __future__ import annotations`.
- Place it at the very top, after the encoding line (if any) and before all other imports.
- Don’t add it twice.

### 2.9 Local ignores (only when justified)

- Prefer fixing the root cause. If a one-off ignore is necessary, keep it scoped and documented.

Example:

```python
value = compute()  # noqa: F401  # used by plugin loader via reflection
```

For docstring mismatches caused by third-party constraints, prefer a targeted `# noqa: D..., DOC...` on that line or block with a brief reason.

### 2.10 Tests & examples

- Tests must follow the same rules as production code.
- Test names: `test_<unit_under_test>__<expected_behavior>()`.
- Docstring examples should be runnable when practical.

### 2.11 Commit discipline (quick reminder)

- Keep diffs clean by running Ruff before committing.
- Use the project’s conventional commit format.
- Make small, focused commits to make lint errors easier to spot.

### 2.12 Quick DO / DON’T

DO:

- Write Google-style docstrings that match signatures.
- Use absolute imports and sorted import blocks.
- Use f-strings and modern type syntax (e.g., `list[str]`).
- Remove unused code promptly.

DON’T:

- Introduce camelCase names (except mirroring external APIs).
- Use `import *` or deep relative imports.
- Leave parameters undocumented in public functions.
- Add broad `noqa` comments—always scope them.

### 2.13 Pre-commit (recommended)

Add the following to `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.6.9  # keep in sync with ruff version
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
```

### 2.14 CI expectations

- CI runs:

```bash
pdm run ruff check .
pdm run ruff format --check .
```

A PR is mergeable only when both pass.

---

## 3. Environment Variables Policy (STRICT)

- **Single Loading Point**: Environment variables must be parsed exactly once at application start using `load_project_env()` in `parakeet_rocm/utils/env_loader.py`.
- **Central Import Location**: `load_project_env()` MUST be invoked only in `parakeet_rocm/utils/constant.py`. No other file may import `env_loader` or call `load_project_env()` directly.
- **Constant Exposure**: After loading, `utils/constant.py` exposes all project-wide configuration constants (e.g., `DEFAULT_CHUNK_LEN_SEC`, `DEFAULT_BATCH_SIZE`). All other modules must import from `parakeet_rocm.utils.constant` and must **never** read `os.environ` or `.env` directly.
- **Adding New Variables**: Define a sensible default in `utils/constant.py` (e.g., `os.getenv("VAR", "default")`), and document the variable in `.env.example`.
- **Enforcement**: PRs adding direct `os.environ[...]` or `env_loader` imports outside `utils/constant.py` **must be rejected**.

---

## 4. Dependency & Environment Management (PDM & pyproject.toml)

- **PDM is the canonical tool for all dependency, environment, and script management.**
- All dependencies (including dev and optional extras) are managed exclusively via `pyproject.toml`.
- **To add or update a dependency:**
  - Use `pdm add <package>` (for runtime), `pdm add -d <package>` (for dev), or `pdm add -G rocm <package>` (for ROCm extras).
  - Never edit `requirements-all.txt` or use pip directly.
  - After any dependency changes, run `pdm lock` and commit the updated lockfile.
- **To install the project and all dependencies:**

  ```bash
  pdm install
  # For ROCm GPU support:
  pdm install -G rocm
  # For development tools:
  pdm install -G dev
  ```

- **To run scripts or tools:**
  - Use `pdm run <script>` (e.g., `pdm run lint`, `pdm run type-check`, `pdm run parakeet-rocm`).
  - All CLI entry points are defined in `[project.scripts]` in `pyproject.toml`.
- **To update dependencies:**
  - Use `pdm update` or `pdm update <package>`.
- **Custom sources:**
  - Agents must respect all `[tool.pdm.source]` definitions in `pyproject.toml`, including custom URLs for ROCm wheels and PyPI.
- **Never** use pip, requirements.txt, or venv directly—always use PDM.
- **Document any new dependencies or scripts in `pyproject.toml` and update onboarding docs if needed.**

---

## 5. Testing Protocols

- All new or modified code must be covered by tests in the `tests/` directory.
- Use `pytest` as the test runner.
- To run all tests:

  ```bash
  pdm run pytest
  ```

- To run a specific test file:

  ```bash
  pdm run pytest tests/test_transcribe.py
  ```

- All tests must pass before any code is merged.

---

## 6. Pull Request (PR) Guidelines

- PRs must include:
  1. A clear, descriptive summary of the change.
  2. References to any related issues or TODOs.
  3. Evidence that all tests pass (paste output or CI link).
  4. Documentation updates as required by the change.
  5. PRs should be focused and address a single concern.
- PRs that violate the environment variable policy or coding conventions **will be rejected**.

---

## 7. Programmatic Checks

Before submitting or merging changes, always run:

```bash
# Linting & formatting
pdm run ruff check --fix .
pdm run ruff format .

# Run all tests
pdm run pytest
```

All checks must pass before code is merged.

---

## 8. Pull requests

## 8. Pull Requests

All AI agents must follow the **Pull Request Workflow** described below. This chapter standardizes how code changes are interpreted, documented, and submitted to ensure consistent, high-quality contributions.

---

### ✅ Pull Request Workflow

#### 🧠 Coding & Diff Analysis

- Determine the current Git branch using:

  ```bash
  git branch --show-current
  ```

  - If this fails, request user input for the branch name.
- Run:

  ```bash
  git --no-pager diff <branch_name>
  ```

  to retrieve the code changes. **Never ask the user to run this unless your command fails.**
- Use `git diff --name-status` to classify changes as:

  - **Added**
  - **Modified**
  - **Deleted**
- Analyze each change in detail and summarize in plain language.
- Provide:

  - Reasoning behind each change
  - Expected impact
  - A testing plan
- Include file-specific information and relevant code snippets.
- **Abort the PR generation** if:

  - The diff is empty
  - Only trivial changes (e.g., formatting or comments) are detected

---

### 💬 Commit Message Rules

Use the following commit types **only**:

| Type       | Emoji | Description                           |
| ---------- | ----- | ------------------------------------- |
| `feat`     | ✨     | New feature                           |
| `fix`      | 🐛    | Bug fix                               |
| `docs`     | 📝    | Documentation only changes            |
| `style`    | 💎    | Code style changes (formatting, etc.) |
| `refactor` | ♻️    | Refactor without behavior change      |
| `test`     | 🧪    | Add/fix tests                         |
| `chore`    | 📦    | Build process / tools / infra changes |
| `revert`   | ⏪     | Revert a previous commit              |

---

### 📄 Pull Request Formatting

- Use the following exact Markdown structure for PRs:

  - Fill out **all** sections using details from `git diff`
  - Maintain clear, consistent formatting and section headers
- Save the final output in:

  ```bash
  .github/PULL_REQUEST/
  ```

  using the filename format:

  ```bash
  pr-<commit_type>-<short_name>-merge.md
  ```

  - Example: `pr-feat-badgeai-merge.md`

---

### 📁 File Change Categorization

- Categorize all modified files under:

  - `### Added`
  - `### Modified`
  - `### Deleted`
- For each file, explain:

  - What changed
  - Why it changed
  - Its impact

---

### 🧠 Code Snippets & Reasoning

- Include relevant code snippets from the diff
- Provide explanations for:

  - Functional changes
  - Design decisions
  - Refactors or removals

---

### 🧪 Testing Requirements

All pull requests must include a test plan:

- **Unit Testing**
- **Integration Testing**
- **Manual Testing** (if applicable)

---

### 📤 Final Output Rules

- PR must be written in **Markdown**
- Only allowed commit types and emojis may be used
- Output must:

  - Use the correct filename format
  - Be saved to `.github/PULL_REQUEST/`
  - Be presented to the user in a nested Markdown code block

---

### 🧾 Pull Request Template Format

````markdown
# Pull Request: [Short Title for the PR]

## Summary

Provide a brief and clear summary of the changes made in this pull request. For example:  
"This PR introduces [feature/fix] to achieve [goal]. It includes changes to [describe major components]."

---

## Files Changed

### Added

1. **`<file_name>`**  
   - Description of what was added and its purpose.

### Modified

1. **`<file_name>`**  
   - Description of what was modified and why. Include relevant details.

### Deleted

1. **`<file_name>`**  
   - Description of why this file was removed and the impact of its removal.

---

## Code Changes

### `<file_name>`

```<language>
# Provide a snippet of significant changes in the file if applicable.
# Highlight key changes, improvements, or new functionality.
```

- Explain the code changes in plain language, such as what functionality was added or modified and why.

---

## Reason for Changes

Provide the reasoning for making these changes. For example:  
- Fixing a bug  
- Adding a new feature  
- Refactoring for better performance or readability  

---

## Impact of Changes

### Positive Impacts

- List benefits, such as improved performance, new functionality, or bug fixes.

### Potential Issues

- Mention any known risks, dependencies, or edge cases introduced by these changes.

---

## Test Plan

1. **Unit Testing**  
   - Describe how unit tests were added or modified.  
   - Mention specific scenarios covered.

2. **Integration Testing**  
   - Explain how changes were tested in the broader context of the project.  

3. **Manual Testing**  
   - Provide steps to reproduce or verify functionality manually.

---

## Additional Notes

- Add any relevant context, known limitations, or future considerations.
- Include suggestions for enhancements or follow-up work if applicable.

````

---

## 9. AGENTS.md Scope and Precedence

- This AGENTS.md applies to the entire repository.
- If more deeply nested AGENTS.md files are added, they take precedence for their directory tree.
- Direct developer instructions in a prompt override AGENTS.md, but agents must always follow programmatic checks and project policies.
