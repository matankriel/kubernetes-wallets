#!/usr/bin/env bash
# post-edit-lint.sh
# Runs after every Edit, Write, or NotebookEdit tool call.
# Lints only the file(s) that were just modified.
#
# Claude Code passes the edited file path via the CLAUDE_TOOL_INPUT env var as JSON.
# We extract the file_path from it and run a targeted lint.
#
# If no linter is configured or the file type is not supported, exits 0 silently.

set -euo pipefail

# Extract the file path from the tool input JSON
# CLAUDE_TOOL_INPUT is set by Claude Code for PostToolUse hooks
FILE_PATH=""
if [[ -n "${CLAUDE_TOOL_INPUT:-}" ]]; then
  FILE_PATH=$(echo "$CLAUDE_TOOL_INPUT" | jq -r '.file_path // empty' 2>/dev/null || true)
fi

if [[ -z "$FILE_PATH" ]]; then
  exit 0
fi

# Only lint if the file exists
if [[ ! -f "$FILE_PATH" ]]; then
  exit 0
fi

EXT="${FILE_PATH##*.}"

case "$EXT" in
  js|jsx|ts|tsx|mjs|cjs)
    if command -v eslint &>/dev/null; then
      echo "[post-edit-lint] Linting $FILE_PATH..."
      eslint --fix "$FILE_PATH" 2>&1 || true
    elif [[ -f "package.json" ]] && grep -q '"lint"' package.json; then
      echo "[post-edit-lint] Running npm run lint on $FILE_PATH..."
      npm run lint -- --fix "$FILE_PATH" 2>&1 || true
    fi
    ;;
  py)
    if command -v ruff &>/dev/null; then
      echo "[post-edit-lint] Linting $FILE_PATH with ruff..."
      ruff check --fix "$FILE_PATH" 2>&1 || true
    elif command -v flake8 &>/dev/null; then
      echo "[post-edit-lint] Linting $FILE_PATH with flake8..."
      flake8 "$FILE_PATH" 2>&1 || true
    fi
    ;;
  go)
    if command -v gofmt &>/dev/null; then
      echo "[post-edit-lint] Formatting $FILE_PATH with gofmt..."
      gofmt -w "$FILE_PATH" 2>&1 || true
    fi
    if command -v golint &>/dev/null; then
      echo "[post-edit-lint] Linting $FILE_PATH with golint..."
      golint "$FILE_PATH" 2>&1 || true
    fi
    ;;
  sh|bash)
    if command -v shellcheck &>/dev/null; then
      echo "[post-edit-lint] Checking $FILE_PATH with shellcheck..."
      shellcheck "$FILE_PATH" 2>&1 || true
    fi
    ;;
  *)
    # No linter for this file type — exit silently
    exit 0
    ;;
esac

exit 0
