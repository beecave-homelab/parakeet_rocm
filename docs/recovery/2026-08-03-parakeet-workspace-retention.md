# Parakeet workspace retention and reconciliation plan

**Status:** preservation plan — no runtime, deployment, or dependency installation authorized

## Goal

Preserve the local-only Parakeet model-evaluation work and untracked Rich-console candidate before reconciling divergent branch history or deleting the ignored 2.3 GB local package environment.

## Evidence snapshot

- The historical workspace branch `feat/rich-cli-output` is ahead of `origin/feat/rich-cli-output` by six commits and behind it by ten commits.
- Commit `c0bcddd` is the only immediately loss-prone commit: it is not reachable from remote refs and adds 973 lines across model-evaluation documentation, a runner, and an integration test.
- Five older local-only commits are already reachable from remote `main` and/or `dev`.
- Two untracked files existed in the historical workspace:
  - `.python-version` declares Python 3.10.
  - `parakeet_rocm/utils/console.py` is a 3.8 KB Rich helper that differs materially from the current remote rich-CLI implementation. It is preserved here as a recovery candidate, not integrated into the package.
  - `recovery-candidates/MANIFEST.sha256.json` records their historical paths, byte sizes, SHA-256 digests, and the 2026-08-03 equality-verification method. It makes the preservation claim auditable after the historical workspace is retired.
- The preserved historical commit `c0bcddd` changes `pyproject.toml` project version from `0.15.0` to `0.14.0` relative to `main`. The recovery branch explicitly restores `0.15.0` in a follow-up preservation commit, so the archival PR does not carry package-metadata drift. Future integration/cherry-pick work must retain that guard.
- The ignored `__pypackages__/` environment is approximately 2.3 GB and contains ROCm Triton, ROCm TorchAudio, CUDA-bearing bitsandbytes, and ML dependencies. It lacks a `torch` package and `onnxruntime-rocm`, so it is incomplete/mixed and must not be treated as a runnable environment.

## Retention decisions

| Item | Decision | Reason |
| --- | --- | --- |
| `c0bcddd` evaluation work | Keep on this dedicated recovery branch | Sole committed work at immediate loss risk. |
| Existing six-file evaluation diff | Keep unchanged for review | No source reconciliation has been performed. |
| Rich console candidate | Keep under `recovery-candidates/` | Preserve for side-by-side review without silently changing runtime code. |
| `.python-version` | Keep as a recovery record only | Records the historical interpreter selection; not adopted as repository policy. |
| `__pypackages__/` | Retain temporarily; remove only after the gates below | Ignored/rebuildable data, but source preservation and install-contract review must finish first. |

## Reconciliation plan

1. Treat this branch as an archival/review branch. Do not merge it directly and do not use it as the base for PR #42.
2. In a fresh worktree from the current remote rich-CLI PR head, compare `c0bcddd` file-by-file against current `main` and the relevant PR branch.
3. Cherry-pick or reimplement only still-useful evaluation work. Resolve overlaps explicitly in `pyproject.toml`, transcription/CLI code, watch behaviour, and tests. Do not force-push or rewrite historical branches.
4. Review the candidate `console.py` against the remote rich-CLI helper. Decide one of: integrate as a focused follow-up, archive as superseded, or delete after a documented comparison. It is not an approved production change merely because it is preserved here.
5. Keep `.python-version` out of the repository unless maintainers intentionally adopt it as a cross-platform toolchain policy.

## Dependency and cleanup gates

Do not install or execute the historic environment on this host.

Before deleting `__pypackages__/`:

1. Confirm this preservation branch and its draft PR are pushed and independently reviewed.
2. Confirm the intended active source branch/worktree is identified.
3. Define a reproducible dependency contract that separates:
   - lightweight static-review/test dependencies;
   - optional application/runtime dependencies; and
   - ROCm deployment-only dependencies.
4. Confirm reviewers/agents cannot resolve ROCm, Torch, NeMo, CUDA, Demucs, model-download, or deployment dependency groups by default.
5. Record the rebuild command and target environment for ROCm runtime work. It must be a designated ROCm-capable runtime, not a generic Hermes workspace.

After all gates pass, remove only the ignored `__pypackages__/` directory. Expected reclaim: approximately 2.3 GB. No Git history or preserved source artifact is in that directory.

## Validation and review

- `git diff --check` for this recovery branch.
- Markdown link/header review of this plan.
- Independent code review of the draft PR before any cleanup based on it.
- No application execution, dependency installation, GPU action, deployment, reset, rebase, or force-push is part of this plan.
