# Pull Request: API auth, model overrides, and logging polish

## Summary

Add API auth and model override controls, improve warmup/offload behavior, tighten logging defaults, extend WebUI/CLI configuration wiring, and bump the release version with updated docs/tests.

## Why

- Enforce optional bearer-token authentication for the OpenAI-compatible API.
- Allow API-only model selection without changing the global Parakeet model.
- Reduce noisy dependency logs while keeping overrides possible.

## Notable changes (reviewer focus)

- New API auth helper and integration into transcription routes.
- API model aliasing now resolves to `API_MODEL_NAME`, with warmup/offload using the same value.
- Warmup runs asynchronously to avoid delaying API startup.
- Logging configuration now applies dependency verbosity consistently and honors env overrides.
- WebUI job manager passes `allow_unsafe_filenames` from config.
- WebUI theme/CSS are applied consistently across mounted and standalone UI.
- Version bumped to v0.14.0 across pyproject, package init, README, and VERSIONS.

## Files changed

- **Counts:** 29 files changed (A 2, M 27, D 0).
- **Key touchpoints:** API auth/mapping/schemas/routes, logging config, WebUI wiring, Docker/deploy config, tests, docs.

<details>
<summary>File lists (auto)</summary>

### Added

- `parakeet_rocm/api/auth.py`
- `tests/unit/test_constant.py`

### Modified

- `.dockerignore`
- `.env.example`
- `AGENTS.md`
- `docker-compose.yaml`
- `parakeet_rocm/api/app.py`
- `parakeet_rocm/api/mapping.py`
- `parakeet_rocm/api/routes.py`
- `parakeet_rocm/api/schemas.py`
- `parakeet_rocm/cli.py`
- `parakeet_rocm/utils/constant.py`
- `parakeet_rocm/utils/logging_config.py`
- `parakeet_rocm/webui/app.py`
- `parakeet_rocm/webui/core/job_manager.py`
- `parakeet_rocm/webui/validation/schemas.py`
- `project-overview.md`
- `pyproject.toml`
- `README.md`
- `scripts/hf_models.py`
- `VERSIONS.md`
- `parakeet_rocm/__init__.py`
- `tests/integration/test_api_integration.py`
- `tests/unit/test_api_app.py`
- `tests/unit/test_api_mapping.py`
- `tests/unit/test_api_routes.py`
- `tests/unit/test_api_schemas.py`
- `tests/unit/test_logging_config.py`
- `tests/unit/test_webui_job_manager.py`

### Deleted

- `N/A`

</details>

## Test plan

- [x] Unit: `scripts/local-ci.sh` (includes unit suite).
- [x] Integration: `scripts/local-ci.sh` (includes integration suite).
- [ ] Manual: N/A.

## Risks & rollback

- **Risks:** API auth could reject requests if token wiring is misconfigured; async warmup may increase first-request latency; dependency log level changes could affect observability expectations.
- **Rollback:** Revert this PR or redeploy the previous image.

## Additional notes

- API-only model override is controlled by `API_MODEL_NAME`; `whisper-1` resolves to this value.
