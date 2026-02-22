#!/bin/bash
set -euo pipefail

# Script Description: Create a GitHub PR via `gh` using a body file and optional
# title. If no body file is provided, the script interactively lets you pick one
# from a default directory. If no title is provided, the first Markdown H1 in the
# body file becomes the title.
# Author: elvee
# Version: 0.2.8
# License: MIT
# Creation Date: 22/02/2026
# Last Modified: 22/02/2026
# Usage: pr-draft.sh [OPTIONS]

DEFAULT_PR_BODY_DIR=".github/PULL_REQUEST"
DEFAULT_BASE_BRANCH="main"
DEFAULT_DRAFT="true"

print_ascii_art() {
  cat >&2 <<'EOF'
┌─┐ ┬─┐   ┌┬┐ ┬─┐ ┌─┐ ┌─┐ ┌┬┐
├─┘ ├┬┘    ││ ├┬┘ ├─┤ ├┤   │
┴   ┴└─   ─┴┘ ┴└─ ┴ ┴ └    ┴
EOF
  echo >&2
  echo "pr-draft.sh  •  $(date +%d/%m/%Y)" >&2
  echo >&2
}

show_help() {
  cat <<EOF
Usage: $0 [OPTIONS] [BODY_FILE] [TITLE]

Options:
  -f, --body-file FILE      Path to PR body file (skips interactive picker).
  -t, --title TITLE         PR title (optional; falls back to H1 in body file).
  -d, --dir DIR             Directory for interactive body-file picker
                            (default: ${DEFAULT_PR_BODY_DIR})
  --base BRANCH             Base branch (default: ${DEFAULT_BASE_BRANCH})
  --head BRANCH             Head branch (default: current git branch)
  --draft                   Create as draft PR (default)
  --no-draft                Create as non-draft PR
  -i, --interactive         Force interactive body-file picker (ignores -f)
  -n, --dry-run             Print the gh command that would run (no changes)
  -h, --help                Show this help message

Tips:
  Copy exact dry-run command:
    $0 --dry-run | pbcopy
EOF
}

error_exit() { echo "Error: $1" >&2; exit 1; }
require_cmd() { command -v "$1" >/dev/null 2>&1 || error_exit "Missing dependency: $1"; }

get_current_branch() {
  local branch=""
  branch="$(git rev-parse --abbrev-ref HEAD 2>/dev/null)" \
    || error_exit "Not a git repo (or git unavailable). Provide --head explicitly."
  [[ "${branch}" != "HEAD" ]] \
    || error_exit "Detached HEAD detected. Provide --head explicitly."
  printf '%s\n' "${branch}"
}

normalize_title() {
  local s="$1"
  s="$(printf '%s' "${s}" | tr '\r\n\t' '   ')"
  s="$(printf '%s' "${s}" | awk '{$1=$1; print}')"
  printf '%s' "${s}"
}

derive_title_from_body() {
  local body_file="$1"
  local derived=""
  derived="$(sed -nE 's/^#[[:space:]]+(.+)/\1/p' "${body_file}" | head -n 1 || true)"
  [[ -n "${derived}" ]] || error_exit "No title provided and no H1 ('# ...') found in body file: ${body_file}"
  normalize_title "${derived}"
}

pick_body_file_interactive() {
  local dir="$1"
  [[ -d "${dir}" ]] || error_exit "Directory not found: ${dir}"

  local -a files=()
  local f=""
  while IFS= read -r f; do files+=("${f}"); done \
    < <(find "${dir}" -maxdepth 1 -type f \( -name "*.md" -o -name "*.markdown" \) | sort)

  (( ${#files[@]} > 0 )) || error_exit "No markdown files found in: ${dir}"

  echo "Select a PR body file from: ${dir}" >&2
  local PS3="Enter a number (or Ctrl+C to quit): "
  select f in "${files[@]}"; do
    [[ -n "${f:-}" ]] || { echo "Invalid selection. Try again." >&2; continue; }
    printf '%s' "${f}"
    return 0
  done
}

main() {
  require_cmd gh
  require_cmd git

  local body_file=""
  local title=""
  local pr_body_dir="${DEFAULT_PR_BODY_DIR}"
  local base_branch="${DEFAULT_BASE_BRANCH}"
  local head_branch=""
  local is_draft="${DEFAULT_DRAFT}"
  local force_interactive="false"
  local dry_run="false"

  while [[ $# -gt 0 ]]; do
    case "$1" in
      -f|--body-file) [[ $# -ge 2 ]] || error_exit "Missing value for $1"; body_file="$2"; shift 2 ;;
      -t|--title)     [[ $# -ge 2 ]] || error_exit "Missing value for $1"; title="$2"; shift 2 ;;
      -d|--dir)       [[ $# -ge 2 ]] || error_exit "Missing value for $1"; pr_body_dir="$2"; shift 2 ;;
      --base)         [[ $# -ge 2 ]] || error_exit "Missing value for $1"; base_branch="$2"; shift 2 ;;
      --head)         [[ $# -ge 2 ]] || error_exit "Missing value for $1"; head_branch="$2"; shift 2 ;;
      --draft)        is_draft="true"; shift ;;
      --no-draft)     is_draft="false"; shift ;;
      -i|--interactive) force_interactive="true"; shift ;;
      -n|--dry-run)   dry_run="true"; shift ;;
      -h|--help)      show_help; exit 0 ;;
      --) shift; break ;;
      -*) error_exit "Invalid option: $1" ;;
      *)
        if [[ -z "${body_file}" ]]; then body_file="$1"
        elif [[ -z "${title}" ]]; then title="$1"
        else error_exit "Unexpected extra argument: $1"
        fi
        shift
        ;;
    esac
  done

  while [[ $# -gt 0 ]]; do
    if [[ -z "${body_file}" ]]; then body_file="$1"
    elif [[ -z "${title}" ]]; then title="$1"
    else error_exit "Unexpected extra argument: $1"
    fi
    shift
  done

  print_ascii_art

  if [[ "${force_interactive}" == "true" || -z "${body_file}" ]]; then
    body_file="$(pick_body_file_interactive "${pr_body_dir}")"
    echo >&2
  fi
  [[ -f "${body_file}" ]] || error_exit "Body file not found: ${body_file}"

  [[ -n "${head_branch}" ]] || head_branch="$(get_current_branch)"

  [[ "${base_branch}" != "${head_branch}" ]] || error_exit \
    "Base and head are both '${base_branch}'. Pass --head <feature-branch> or --base <base-branch>."

  if [[ -n "${title}" ]]; then
    title="$(normalize_title "${title}")"
  else
    title="$(derive_title_from_body "${body_file}")"
  fi

  local -a gh_args=(pr create --base "${base_branch}" --head "${head_branch}" --title "${title}" --body-file "${body_file}")
  [[ "${is_draft}" == "true" ]] && gh_args+=(--draft)

  echo "Creating PR with:" >&2
  echo "  base: ${base_branch}" >&2
  echo "  head: ${head_branch}" >&2
  echo "  title: ${title}" >&2
  echo "  body-file: ${body_file}" >&2
  echo "  draft: ${is_draft}" >&2
  echo "  dry-run: ${dry_run}" >&2
  echo >&2

  if [[ "${dry_run}" == "true" ]]; then
    local preview
    preview="$(printf 'gh'; printf ' %q' "${gh_args[@]}")"

    # Als stdout een terminal is: toon preview op stderr (niet dubbel).
    # Als stdout NIET een terminal is (pipe/redirect): print preview op stdout.
    if [[ -t 1 ]]; then
      echo "Dry-run: command preview:" >&2
      echo "  ${preview}" >&2
    else
      printf '%s\n' "${preview}"
    fi

    return 0
  fi

  gh "${gh_args[@]}"
}

main "$@"
