# HIP Python Migration Plan for Parakeet ROCm

## Summary of the Problem

- Running Parakeet-TDT via NeMo on AMD hardware currently triggers warnings because NeMo attempts to import the `cuda-python` package to enable CUDA Graph conditional nodes. When that import fails, decoding falls back to a slower path.
- AMD's ROCm stack ships a drop-in replacement called `hip-python-as-cuda`, which exposes the same module layout (`from cuda import cuda, cudart, nvrtc`) backed by HIP runtimes. Installing it alongside `hip-python` satisfies CUDA Python import checks without installing NVIDIA's stack.
- We need to document the repository changes required to prefer HIP Python when operating on ROCm so that NeMo features expecting CUDA Python become available.

## Required Dependency Changes

1. **Add HIP Python packages to the ROCm extra.**
   - Include both `hip-python` and `hip-python-as-cuda` in `pyproject.toml` under the `rocm` optional dependency group so they are installed alongside ROCm wheels.
   - Version pinning must follow the ROCm release in use (e.g., ROCm 6.2 ships `hip-python==6.2.x`). Document the mapping in the setup guide to avoid mismatches.
2. **Update lockfiles and requirements exports.**
   - Regenerate `pdm.lock`, `requirements-agent.txt`, and any deployment requirement files so CI/CD and container builds also pull the HIP Python wheels.
3. **Container and image updates.**
   - Extend Docker build stages and compose services to install the HIP Python wheels (either via PyPI once available or internal wheelhouse), mirroring how we currently install ROCm-specific wheels like `torch` and `onnxruntime-rocm`.

## Runtime Detection and Configuration

1. **Lightweight capability probe.**
   - Add a small helper (e.g., `parakeet_rocm/utils/gpu_runtime.py`) that tries to import `cuda` and reports whether the bindings come from HIP (`hasattr(cuda, "hip")`) or NVIDIA. This enables logging and conditional logic without scattering import tries throughout the codebase.
2. **Environment toggle for enum hallucination.**
   - Some NeMo checks reference CUDA error enums that HIP never returns. Set `HIP_PYTHON_cudaError_t_HALLUCINATE=1` when launching services (CLI entry point, docker compose env) so HIP Python can synthesize the missing constants and keep those checks from failing.
3. **Fail-fast guidance.**
   - Surface a clear warning (or raise) during CLI start-up when HIP Python bindings are absent but ROCm is detected, pointing the user to the new installation steps.

## Documentation and Tooling Updates

1. **Setup guide additions.**
   - Update `to-do/setup_guide.md` (and the README quickstart) with commands for installing the paired HIP Python wheels, including notes about matching ROCm versions.
   - Document how to set the `HIP_PYTHON_cudaError_t_HALLUCINATE` environment variable in shell sessions, systemd units, and Docker Compose files.
2. **Troubleshooting section.**
   - Add a FAQ entry describing the NeMo warning and the resolution via HIP Python, including how to verify by running `python -c "from cuda import cuda; print(cuda.HIP_PYTHON)"`.
3. **CI validation.**
   - Add a smoke test or CI check that imports `cuda` and asserts the HIP shim is active when the `rocm` extra is installed, preventing regressions.

## Next Steps

1. Implement dependency updates and regenerate lockfiles.
2. Add the runtime helper and integrate logging so we can confirm the shim is in use when decoding.
3. Update documentation and deployment manifests with the new environment expectations.
4. Validate the end-to-end pipeline on an AMD GPU after installing the HIP Python packages to ensure NeMo no longer downgrades decoding speed.

## Implementation Summary

- Optional ROCm dependencies now pin `hip-python==6.2.0` and `hip-python-as-cuda==6.2.0` alongside the ROCm Torch stack so the shim is installed with the extra.
- A `gpu_runtime` utility detects whether the CUDA import is backed by HIP and surfaces warnings in the CLI when bindings are missing.
- Docker Compose, the setup guide, and the README document the `HIP_PYTHON_cudaError_t_HALLUCINATE=1` environment toggle and provide a verification snippet for confirming the shim is active.
