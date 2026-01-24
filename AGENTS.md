# AGENTS.md

This guide orients AI agents to the Parakeet-ROCm codebase. Use it alongside
README.md, project-overview.md, and TESTING.md for deeper context.

## Setup & Commands

### Install

- Recommended (PDM + ROCm + WebUI + dev tools):
  - `pdm install -G rocm,webui,dev`
- Runtime only (CLI + ROCm + WebUI):
  - `pdm install -G rocm,webui`
- Fallback (pip, used in Docker build):
  - `pip install -r requirements-all.txt`
- Create local env file:
  - `cp .env.example .env`

### Run / Dev

- CLI (installed script):
  - `parakeet-rocm transcribe data/samples/voice_sample.wav`
- CLI via PDM:
  - `pdm run parakeet-rocm transcribe data/samples/voice_sample.wav`
- Watch mode:
  - `parakeet-rocm transcribe --watch data/watch/ --verbose`
- WebUI:
  - `pdm run parakeet-rocm webui --host 0.0.0.0 --port 7861`
- Docker (WebUI on port 7861):
  - `docker compose up`

### Tests

- All tests:
  - `pdm run pytest`
- Fast unit tests only:
  - `pdm run pytest tests/unit/`
- Skip GPU/slow:
  - `pdm run pytest -m "not (gpu or slow)"`

### Lint / Format

- Ruff lint:
  - `pdm run ruff check .`
- Ruff format:
  - `pdm run ruff format .`
- Auto-fix + format:
  - `pdm run fix`
  - `bash scripts/clean_codebase.sh`

### Build

- Docker image:
  - `docker compose build`
- Python package (wheel/sdist):
  - `pdm build`

### Other Tools

- Local CI pipeline (fix/format/test/coverage):
  - `bash scripts/local-ci.sh`
- SRT diff helper:
  - `bash scripts/transcribe_and_diff.sh <audio_file>`

## Project Structure

```dir
parakeet_rocm/
├── parakeet_rocm/           # Python package
│   ├── cli.py               # Typer CLI entry point
│   ├── config.py            # Configuration dataclasses
│   ├── transcription/       # CLI orchestration + per-file processing
│   ├── models/              # Parakeet model loading + caching
│   ├── chunking/             # Chunking + overlap merge utilities
│   ├── timestamps/          # Alignment, segmentation, word timing models
│   ├── formatting/          # TXT/SRT/VTT/JSON formatters + registry
│   ├── webui/               # Gradio WebUI
│   └── utils/               # Env loading, audio IO, file utils, watcher
├── scripts/                 # Helper scripts (CI, diffing, downloads)
├── tests/                   # unit/, integration/, e2e/, slow/
├── data/                    # samples/, watch/, benchmarks/
├── output/                  # default output dir (gitignored)
├── docker-compose.yaml      # WebUI container runtime
├── Dockerfile               # Container build
├── pyproject.toml           # Dependencies + tooling config
├── README.md                # Quick-start and usage
├── TESTING.md               # Test strategy and conventions
└── project-overview.md      # Architecture and subsystem details
```

## Tech Stack

### Core

- Python 3.10 (runtime target)
- PDM (dependency management, scripts)
- Typer + Rich (CLI and TUI output)
- NVIDIA NeMo ASR (Parakeet-TDT models)
- PyTorch ROCm wheels (optional `rocm` extra)
- Pydantic (alignment and timestamp models)
- FFmpeg/libsndfile/sox (audio decoding)

### Optional / Integrations

- Gradio (WebUI, `webui` extra)
- stable-ts-whisperless, silero-vad, demucs (timestamp refinement)
- pyamdgpuinfo (benchmark telemetry, `bench` extra)

### Development

- Ruff (lint + format)
- pytest + pytest-cov (tests + coverage)

## Architecture & Patterns

### Layered pipeline

- CLI -> transcription orchestration -> model/pipeline utilities.
- File processing and chunking logic live under `transcription/`, `chunking/`.
- Output formatting is centralized in `formatting/` via a registry.

### Configuration

- Configuration dataclasses in `config.py` group related settings.
- Environment variables are loaded once in `utils/env_loader.py` and exposed as
  typed constants in `utils/constant.py`.

### Extensibility

- Formatters and merge strategies are registered through dictionaries so new
  options can be added without changing call sites.
- Model loading is lazy and cached to avoid reloading large weights.

### Data models

- Timestamp/segment data is represented with Pydantic models in `timestamps/`.

## Code Style & Patterns

### Python conventions

- Keep type annotations on public functions and tests.
- Use dataclasses for configuration objects.
- Keep optional integrations (stable-ts, WebUI) lazily imported to avoid
  import-time failures when extras are missing.
- Follow Ruff configuration in `pyproject.toml` (line length 100).
- Docstrings follow Google style (see Ruff pydocstyle config).

### Testing

- Follow the test guide in TESTING.md (markers, AAA pattern, tmp_path usage).
- Unit tests must be hermetic; do not download models or require GPUs.

## Git / PR Workflow

- Keep PRs focused and update tests when behavior changes.
- Run `bash scripts/local-ci.sh` before opening a PR when possible.
- If you update dependencies or versions, update `pyproject.toml`,
  `requirements-all.txt` (if used), and `VERSIONS.md`.

## Boundaries

### Always

- Load env config via `utils/env_loader.py` and update `utils/constant.py` when
  adding new configuration values.
- Keep new formats/strategies registered in their respective registries.
- Add or update tests for behavior changes and apply correct markers.

### Ask First

- Changing default model names or GPU/ROCm runtime settings.
- Modifying Dockerfile or docker-compose.yaml behavior.
- Removing test coverage or altering marker conventions.

### Never

- Download large models or assets in unit tests.
- Commit generated outputs, large binaries, or benchmark artifacts.
- Hardcode secrets or API keys.

## Common Tasks

### Add a new output formatter

1. Implement the formatter in `parakeet_rocm/formatting/_<fmt>.py`.
2. Register it in `parakeet_rocm/formatting/__init__.py` with the correct
   extension and `requires_word_timestamps` flag.
3. Add unit tests in `tests/unit/test_formatting.py`.

### Add a merge strategy

1. Implement the function in `parakeet_rocm/chunking/merge.py`.
2. Register it in `MERGE_STRATEGIES`.
3. Update CLI help/options in `parakeet_rocm/cli.py`.
4. Add tests in `tests/unit/test_merge.py`.

### Add a CLI option

1. Add the option in `parakeet_rocm/cli.py`.
2. Wire it through `config.py` (dataclasses) and the transcription pipeline.
3. Update README.md/project-overview.md if user-facing.
4. Add tests (unit/integration as appropriate).

### Add an environment variable

1. Add to `.env.example` and document it.
2. Add a typed constant in `parakeet_rocm/utils/constant.py`.
3. Thread the value through config dataclasses if needed.
4. Update docs (README or project-overview).

### Update WebUI behavior

1. Make UI changes in `parakeet_rocm/webui/app.py` and related helpers.
2. Keep CLI launch behavior in `parakeet_rocm/webui/cli.py` in sync.
3. Add/update WebUI tests in `tests/unit/test_webui_*`.

## Troubleshooting

- ROCm wheels not found: install with `pdm install -G rocm` and ensure the
  `rocm-wheels` source in `pyproject.toml` is available.
- Missing FFmpeg/libsndfile: install system packages or use Docker.
- GPU tests skipped: ensure sample audio exists and GPU is available; tests
  skip when `CI=true` or GPU is absent.
- Watch mode ignores files: confirm extensions are listed in
  `utils/file_utils.AUDIO_EXTENSIONS` and WebUI uses
  `utils/constant.SUPPORTED_EXTENSIONS`.
- WebUI port conflicts: update `GRADIO_SERVER_PORT` in `.env` or pass `--port`.
