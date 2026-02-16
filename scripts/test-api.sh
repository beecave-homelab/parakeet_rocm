#!/bin/bash
set -euo pipefail

# Script Description: Run a suite of curl-based smoke tests against the API.
# Author: elvee
# Version: 0.1.0
# License: MIT
# Creation Date: 16/02/2026
# Last Modified: 16/02/2026
# Usage: ./test-api.sh [OPTIONS]

# Constants
DEFAULT_BASE_URL="http://localhost:8080"
DEFAULT_AUDIO_FILE="data/samples/voice_sample.wav"
DEFAULT_MODEL="whisper-1"
DEFAULT_OUT_DIR="${PWD}/tmp/test-api"
DEFAULT_TIMEOUT_SECONDS="60"

# ASCII Art
print_ascii_art() {
  echo "
╔╦╗╔═╗╔═╗╔╦╗  ╔═╗╔═╗╦
 ║ ║╣ ╚═╗ ║   ╠═╣╠═╝║
 ╩ ╚═╝╚═╝ ╩   ╩ ╩╩  ╩
  "
}

# Function to display help
show_help() {
  echo "
Usage: $0 [OPTIONS]

Options:
  -u, --base-url URL          Base URL of the API (default: $DEFAULT_BASE_URL)
  -f, --file PATH             Audio file to upload (default: $DEFAULT_AUDIO_FILE)
  -m, --model MODEL           Model name (default: $DEFAULT_MODEL)
  -o, --out-dir DIR           Output directory (default: $DEFAULT_OUT_DIR)
  -t, --timeout SECONDS       Curl max-time (default: $DEFAULT_TIMEOUT_SECONDS)
  -h, --help                  Show this help message

Examples:
  $0
  $0 --base-url http://localhost:8080 --file data/samples/voice_sample.wav
  $0 -m whisper-1 -o ./tmp/test-api
"
}

# Function for error handling
error_exit() {
  echo "Error: $1" >&2
  exit 1
}

# Check required commands exist
require_cmd() {
  local cmd="$1"
  command -v "${cmd}" >/dev/null 2>&1 || error_exit "Missing dependency: ${cmd}"
}

# Run a GET and optionally pretty-print JSON if jq is available.
run_get() {
  local url="$1"
  local label="$2"
  local timeout_seconds="$3"

  echo
  echo "==> ${label}"
  echo "GET ${url}"

  if command -v jq >/dev/null 2>&1; then
    curl -sS --max-time "${timeout_seconds}" "${url}" | jq .
  else
    curl -sS --max-time "${timeout_seconds}" "${url}"
  fi
}

# Run a POST multipart/form-data request.
# Writes body to output_file and returns HTTP status via stdout.
run_post_form() {
  local url="$1"
  local file_path="$2"
  local model="$3"
  local response_format="$4"
  local out_file="$5"
  local timeout_seconds="$6"
  shift 6
  local extra_form_fields=("$@")

  local http_code=""
  local curl_args=(
    -sS
    --max-time "${timeout_seconds}"
    -o "${out_file}"
    -w "%{http_code}"
    -X POST "${url}"
    -F "file=@${file_path}"
    -F "model=${model}"
    -F "response_format=${response_format}"
  )

  if [[ ${#extra_form_fields[@]} -gt 0 ]]; then
    local field=""
    for field in "${extra_form_fields[@]}"; do
      curl_args+=(-F "${field}")
    done
  fi

  http_code="$(curl "${curl_args[@]}")"
  echo "${http_code}"
}

# Function for main logic
main_logic() {
  local base_url="$1"
  local audio_file="$2"
  local model="$3"
  local out_dir="$4"
  local timeout_seconds="$5"

  require_cmd curl

  if [[ ! -f "${audio_file}" ]]; then
    error_exit "Audio file not found: ${audio_file}"
  fi

  mkdir -p "${out_dir}"

  local health_url="${base_url}/health"
  local openapi_url="${base_url}/openapi.json"
  local transcribe_url="${base_url}/v1/audio/transcriptions"

  # 0) Quick sanity checks
  run_get "${health_url}" "0) Health check" "${timeout_seconds}"

  echo
  echo "==> 0) OpenAPI paths (keys)"
  echo "GET ${openapi_url}"
  if command -v jq >/dev/null 2>&1; then
    curl -sS --max-time "${timeout_seconds}" "${openapi_url}" \
      | jq '.paths | keys'
  else
    curl -sS --max-time "${timeout_seconds}" "${openapi_url}"
  fi

  # 1) JSON response (OpenAI-style)
  echo
  echo "==> 1) JSON response (OpenAI-style)"
  local out_json="${out_dir}/1-json.json"
  local code=""
  code="$(run_post_form \
    "${transcribe_url}" \
    "${audio_file}" \
    "${model}" \
    "json" \
    "${out_json}" \
    "${timeout_seconds}")"
  echo "HTTP ${code} -> ${out_json}"
  if command -v jq >/dev/null 2>&1; then
    jq . "${out_json}"
  else
    cat "${out_json}"
  fi

  # 2) Plain text response
  echo
  echo "==> 2) Plain text response"
  local out_text="${out_dir}/2-text.txt"
  code="$(run_post_form \
    "${transcribe_url}" \
    "${audio_file}" \
    "${model}" \
    "text" \
    "${out_text}" \
    "${timeout_seconds}")"
  echo "HTTP ${code} -> ${out_text}"
  cat "${out_text}"

  # 3) Verbose JSON + timestamp granularities
  echo
  echo "==> 3) Verbose JSON + timestamp granularities"
  local out_verbose="${out_dir}/3-verbose_json.json"
  code="$(run_post_form \
    "${transcribe_url}" \
    "${audio_file}" \
    "${model}" \
    "verbose_json" \
    "${out_verbose}" \
    "${timeout_seconds}" \
    "timestamp_granularities=word" \
    "timestamp_granularities=segment")"
  echo "HTTP ${code} -> ${out_verbose}"
  if command -v jq >/dev/null 2>&1; then
    jq . "${out_verbose}"
  else
    cat "${out_verbose}"
  fi

  # 4) SRT format
  echo
  echo "==> 4) SRT format"
  local out_srt="${out_dir}/4-subs.srt"
  code="$(run_post_form \
    "${transcribe_url}" \
    "${audio_file}" \
    "${model}" \
    "srt" \
    "${out_srt}" \
    "${timeout_seconds}")"
  echo "HTTP ${code} -> ${out_srt}"
  cat "${out_srt}"

  # 5) VTT format
  echo
  echo "==> 5) VTT format"
  local out_vtt="${out_dir}/5-subs.vtt"
  code="$(run_post_form \
    "${transcribe_url}" \
    "${audio_file}" \
    "${model}" \
    "vtt" \
    "${out_vtt}" \
    "${timeout_seconds}")"
  echo "HTTP ${code} -> ${out_vtt}"
  cat "${out_vtt}"

  # 6) Negative test: invalid model
  echo
  echo "==> 6) Negative test: invalid model"
  local out_bad="${out_dir}/6-invalid-model.json"

  set +e
  code="$(run_post_form \
    "${transcribe_url}" \
    "${audio_file}" \
    "not-a-real-model" \
    "json" \
    "${out_bad}" \
    "${timeout_seconds}")"
  set -e

  echo "HTTP ${code} -> ${out_bad}"
  if command -v jq >/dev/null 2>&1; then
    jq . "${out_bad}"
  else
    cat "${out_bad}"
  fi

  echo
  echo "Done. Outputs saved in: ${out_dir}"
}

# Main function
main() {
  local base_url="${DEFAULT_BASE_URL}"
  local audio_file="${DEFAULT_AUDIO_FILE}"
  local model="${DEFAULT_MODEL}"
  local out_dir="${DEFAULT_OUT_DIR}"
  local timeout_seconds="${DEFAULT_TIMEOUT_SECONDS}"

  while [[ $# -gt 0 ]]; do
    case "$1" in
      -u|--base-url)
        base_url="$2"
        shift 2
        ;;
      -f|--file)
        audio_file="$2"
        shift 2
        ;;
      -m|--model)
        model="$2"
        shift 2
        ;;
      -o|--out-dir)
        out_dir="$2"
        shift 2
        ;;
      -t|--timeout)
        timeout_seconds="$2"
        shift 2
        ;;
      -h|--help)
        show_help
        exit 0
        ;;
      *)
        error_exit "Invalid option: $1"
        ;;
    esac
  done

  main_logic "${base_url}" "${audio_file}" "${model}" "${out_dir}" \
    "${timeout_seconds}"
}

print_ascii_art
main "$@"
