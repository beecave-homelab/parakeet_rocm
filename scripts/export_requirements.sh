#!/usr/bin/env bash
# Export a fully pinned requirements-all.txt using PDM
# Usage: ./scripts/export_requirements.sh
set -euo pipefail
pdm export --pyproject --no-hashes -G rocm -o requirements-all.txt
