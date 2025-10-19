#!/usr/bin/env bash
# Export a fully pinned requirements-all.txt using PDM
# Usage: ./scripts/export_requirements.sh
set -euo pipefail

echo "Exporting pdm.lock to requirements-all-dev-nh-nm.txt..."
pdm export --no-hashes --no-markers --dev -G rocm -G webui -o requirements-all-dev-nh-nm.txt
echo "Exporting requirements-all-dev-nh-nm.txt was succesfull."

echo "Exporting pdm.lock to requirements-all-dev-nh.txt..."
pdm export --no-hashes --dev -G rocm -G webui -o requirements-all-dev-nh.txt
echo "Exporting requirements-all-dev-nh.txt was succesfull."
