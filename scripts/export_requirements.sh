#!/usr/bin/env bash
# Export all requirements files using PDM
# Usage: ./scripts/export_requirements.sh
set -euo pipefail
pdm export --pyproject --no-hashes -G rocm -G webui -G bench -o requirements-all.txt
pdm export --pyproject --no-hashes -G dev -o requirements-agent.txt
