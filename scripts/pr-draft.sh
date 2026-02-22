#!/bin/bash
set -euo pipefail

# Script Description: Create a GitHub *draft* PR via `gh`, using a body file and
# optionally a title. If no title is provided, the first Markdown H1 in the body
# file is used as an auto-title.
# Author: elvee
# Version: 0.1.0
# License: MIT
# Creation Date: 22/02/2026
# Last Modified: 22/02/2026
# Usage: pr-draft.sh BODY_FILE [TITLE]
#
# Examples:
#   ./pr-draft.sh .github/PULL_REQUEST/pr-feature-badgeai-merge.md
#   ./pr-draft.sh .github/PULL_REQUEST/pr-feature-badgeai-merge.md \
#     "feat ✨: Add AI Usage Badge System via Frontmatter"
#   ./pr-draft.sh -f .github/PULL_REQUEST/pr-feature-badgeai-merge.md \
#     --base dev --head frontmatter-badge-ai

SCRIPT_DATE="$(date +%d/%m/%Y)"

# Defaults
DEFAULT_BASE_BRANCH="dev"
DEFAULT_DRAFT="true"

print_ascii_art() {
  # Calvin font (caps): "PR DRAFT"
  echo "
╔═╗ ╦═╗   ╔╦╗ ╦═╗ ╔═╗ ╔═╗ ╔╦╗
╠═╝ ╠╦╝    ║║ ╠╦╝ ╠═╣ ╠╣   ║
╩   ╩╚═   ═╩╝ ╩╚═ ╩ ╩ ╚    ╩

pr-draft.sh  •  ${SCRIPT_DATE}
"
}

show_help() {
  cat <<'EOF'
Usage:
  pr-draft.sh BODY_FILE [TITLE]
  pr-draft.sh -f BODY_FILE [-t TITLE] [--base BRANCH] [--head BRANCH]
             [--draft | --no-draft] [-h]

Arguments:
  BODY_FILE                 Path to the PR body markdown file (required).
  TITLE                     Optional PR title. If omitted, script uses the
                            first Markdown H1 ("# ...") found in BODY_FILE.

Options:
  -f, --body-file FILE      Path to the PR body markdown file (required).
  -t, --title TITLE         PR title (optional; falls back to H1 from body file).
  --base BRANCH             Base branch (default: dev).
  --head BRANCH             Head branch (default: current git branch).
  --draft                   Create as draft PR (default).
  --no-draft                Create as non-draft PR.
  -h, --help                Show this help message.

Notes:
  - Requires: gh
  - If you omit --head, the script uses: git rev-parse --abbrev-ref HEAD
EOF
}

error_exit() {
  echo "Error: $1" >&2
  exit 1
}

require_cmd() {
  local cmd="$1"
  command -v "${cmd}" >/dev/null 2>&1 || error_exit "Missing dependency: ${cmd}"
}

get_current_branch() {
  git rev-parse --abbrev-ref HEAD 2>/dev/null \
    || error_exit "Not a git repo (or git unavailable). Provide --head explicitly."
}

derive_title_from_body() {
  local body_file="$1"
  local derived=""

  # First Markdown H1 line: "# Title" (must be a single # followed by whitespace).
  derived="$(sed -nE 's/^#[[:space:]]+(.+)/\1/p' "${body_file}" | head -n 1 || true)"

  [[ -n "${derived}" ]] || error_exit \
    "No title provided and no H1 ('# ...') found in body file: ${body_file}"

  printf '%s' "${derived}"
}

main() {
  local body_file=""
  local title=""
  local base_branch="${DEFAULT_BASE_BRANCH}"
  local head_branch=""
  local is_draft="${DEFAULT_DRAFT}"

  # Parse options (supports flags and also positional args)
  while [[ $# -gt 0 ]]; do
    case "$1" in
      -f|--body-file)
        [[ $# -ge 2 ]] || error_exit "Missing value for $1"
        body_file="$2"
        shift 2
        ;;
      -t|--title)
        [[ $# -ge 2 ]] || error_exit "Missing value for $1"
        title="$2"
        shift 2
        ;;
      --base)
        [[ $# -ge 2 ]] || error_exit "Missing value for $1"
        base_branch="$2"
        shift 2
        ;;
      --head)
        [[ $# -ge 2 ]] || error_exit "Missing value for $1"
        head_branch="$2"
        shift 2
        ;;
      --draft)
        is_draft="true"
        shift
        ;;
      --no-draft)
        is_draft="false"
        shift
        ;;
      -h|--help)
        show_help
        exit 0
        ;;
      --)
        shift
        break
        ;;
      -*)
        error_exit "Invalid option: $1"
        ;;
      *)
        # Positional: BODY_FILE then optional TITLE
        if [[ -z "${body_file}" ]]; then
          body_file="$1"
        elif [[ -z "${title}" ]]; then
          title="$1"
        else
          error_exit "Unexpected extra argument: $1"
        fi
        shift
        ;;
    esac
  done

  [[ -n "${body_file}" ]] || error_exit "BODY_FILE is required. See -h for help."
  [[ -f "${body_file}" ]] || error_exit "Body file not found: ${body_file}"

  require_cmd gh

  if [[ -z "${head_branch}" ]]; then
    require_cmd git
    head_branch="$(get_current_branch)"
  fi

  if [[ -z "${title}" ]]; then
    title="$(derive_title_from_body "${body_file}")"
  fi

  # Build gh args safely
  local -a gh_args
  gh_args+=(pr create)
  gh_args+=(--base "${base_branch}")
  gh_args+=(--head "${head_branch}")
  gh_args+=(--title "${title}")
  gh_args+=(--body-file "${body_file}")

  if [[ "${is_draft}" == "true" ]]; then
    gh_args+=(--draft)
  fi

  echo "Creating PR with:"
  echo "  base: ${base_branch}"
  echo "  head: ${head_branch}"
  echo "  title: ${title}"
  echo "  body-file: ${body_file}"
  echo

  gh "${gh_args[@]}"
}

print_ascii_art
main "$@"
