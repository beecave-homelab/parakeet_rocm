#!/usr/bin/env bash
set -euo pipefail

# Single transcription run helper.
# Usage:
#   bash scripts/single_run.sh [audio_file]
#
# Default input if none provided:
#   data/samples/voice_sample.wav

INPUT_FILE="${1:-data/samples/voice_sample.wav}"
if [[ ! -f "$INPUT_FILE" ]]; then
  echo "Error: file not found: $INPUT_FILE" >&2
  exit 1
fi

# Prefer running through PDM to ensure the correct environment; fall back to CLI or module.
if command -v pdm >/dev/null 2>&1; then
  RUNNER=(pdm run parakeet-rocm)
elif command -v parakeet-rocm >/dev/null 2>&1; then
  RUNNER=(parakeet-rocm)
else
  RUNNER=(python -m parakeet_rocm.cli)
fi

set -x
"${RUNNER[@]}" transcribe \
  --output-format srt \
  --word-timestamps \
  --benchmark \
  --verbose \
  "$INPUT_FILE"
set +x

echo "Done."
