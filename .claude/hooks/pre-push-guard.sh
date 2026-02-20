#!/usr/bin/env bash
# pre-push-guard.sh
# Runs before every Bash tool call.
# Blocks direct pushes to protected branches (main, production).
#
# Claude Code passes the command via CLAUDE_TOOL_INPUT as JSON.
# We inspect the command for dangerous push patterns and exit 2 to block.
#
# Exit codes:
#   0 = allow the command
#   2 = block the command (Claude Code interprets this as a hook block)

set -euo pipefail

COMMAND=""
if [[ -n "${CLAUDE_TOOL_INPUT:-}" ]]; then
  COMMAND=$(echo "$CLAUDE_TOOL_INPUT" | jq -r '.command // empty' 2>/dev/null || true)
fi

if [[ -z "$COMMAND" ]]; then
  exit 0
fi

PROTECTED_BRANCHES=("main" "master" "production" "prod")

for branch in "${PROTECTED_BRANCHES[@]}"; do
  # Block: git push [origin] main / production (direct push)
  if echo "$COMMAND" | grep -qE "git push.*(origin\s+)?${branch}(\s|$)" 2>/dev/null; then
    # Allow if it's a --delete (deleting a remote branch is OK in some workflows)
    if echo "$COMMAND" | grep -q -- "--delete\|-d\s"; then
      continue
    fi
    echo "[pre-push-guard] BLOCKED: Direct push to protected branch '${branch}' is not allowed." >&2
    echo "[pre-push-guard] Create a feature branch and open a PR instead." >&2
    echo "[pre-push-guard] If you intentionally need to push to '${branch}', do it manually outside of Claude." >&2
    exit 2
  fi

  # Block: git push --force / -f to protected branches
  if echo "$COMMAND" | grep -qE "git push.*(--force|-f).*(origin\s+)?${branch}" 2>/dev/null; then
    echo "[pre-push-guard] BLOCKED: Force push to protected branch '${branch}' is not allowed." >&2
    exit 2
  fi

  if echo "$COMMAND" | grep -qE "git push.*(origin\s+)?${branch}.*(--force|-f)" 2>/dev/null; then
    echo "[pre-push-guard] BLOCKED: Force push to protected branch '${branch}' is not allowed." >&2
    exit 2
  fi
done

exit 0
