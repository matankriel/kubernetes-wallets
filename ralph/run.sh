#!/usr/bin/env bash
# ralph/run.sh
# Autonomous story implementation loop for Claude Code.
#
# Usage:
#   bash ralph/run.sh                          # Loop all pending stories
#   bash ralph/run.sh --once                   # Process next pending story only
#   bash ralph/run.sh --story STORY-001        # Process a specific story
#   bash ralph/run.sh --dry-run                # Print the prompt without calling Claude
#   bash ralph/run.sh --model claude-opus-4-6  # Override the model
#   bash ralph/run.sh --once --dry-run         # Dry-run the next pending story

set -euo pipefail

# ─── Configuration ────────────────────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PRD_FILE="${SCRIPT_DIR}/prd.json"
PROMPT_FILE="${SCRIPT_DIR}/prompt.md"
LOGS_DIR="${SCRIPT_DIR}/logs"
DEFAULT_MODEL="claude-sonnet-4-6"
MAX_TURNS=200

# ─── Argument Parsing ──────────────────────────────────────────────────────────

ONCE=false
DRY_RUN=false
TARGET_STORY=""
MODEL="${DEFAULT_MODEL}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --once)
      ONCE=true
      shift
      ;;
    --dry-run)
      DRY_RUN=true
      shift
      ;;
    --story)
      TARGET_STORY="$2"
      shift 2
      ;;
    --model)
      MODEL="$2"
      shift 2
      ;;
    --help|-h)
      echo "Usage: bash ralph/run.sh [OPTIONS]"
      echo ""
      echo "Options:"
      echo "  --once               Process only the next pending story, then exit"
      echo "  --story STORY-ID     Process a specific story by ID"
      echo "  --dry-run            Print prompt and story without calling Claude"
      echo "  --model MODEL        Claude model to use (default: ${DEFAULT_MODEL})"
      echo "  --help               Show this help message"
      echo ""
      echo "Examples:"
      echo "  bash ralph/run.sh                          # Loop all pending stories"
      echo "  bash ralph/run.sh --once                   # Process next pending story"
      echo "  bash ralph/run.sh --story STORY-001        # Process a specific story"
      echo "  bash ralph/run.sh --dry-run                # Preview without running"
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      echo "Run 'bash ralph/run.sh --help' for usage." >&2
      exit 1
      ;;
  esac
done

# ─── Dependency Checks ────────────────────────────────────────────────────────

check_deps() {
  local missing=()
  for cmd in jq claude; do
    if ! command -v "$cmd" &>/dev/null; then
      missing+=("$cmd")
    fi
  done
  if [[ ${#missing[@]} -gt 0 ]]; then
    echo "[ralph] ERROR: Missing required dependencies: ${missing[*]}" >&2
    echo "[ralph] Install jq: brew install jq / apt install jq" >&2
    echo "[ralph] Install Claude Code: npm install -g @anthropic/claude-code" >&2
    exit 1
  fi
}

# ─── Story Helpers ────────────────────────────────────────────────────────────

# Get the next pending story, sorted by priority (high → medium → low)
get_next_story_id() {
  jq -r '
    .stories
    | map(select(.status == "pending"))
    | sort_by(
        if .priority == "high" then 0
        elif .priority == "medium" then 1
        else 2 end
      )
    | first
    | .id // empty
  ' "$PRD_FILE"
}

# Get a specific field from a story
get_story_field() {
  local story_id="$1"
  local field="$2"
  jq -r --arg id "$story_id" --arg field "$field" \
    '.stories[] | select(.id == $id) | .[$field] // empty' \
    "$PRD_FILE"
}

# Get story status
get_story_status() {
  local story_id="$1"
  get_story_field "$story_id" "status"
}

# Update story status in prd.json
update_story_status() {
  local story_id="$1"
  local new_status="$2"
  local tmp_file="${PRD_FILE}.tmp"

  jq --arg id "$story_id" --arg status "$new_status" \
    '(.stories[] | select(.id == $id)).status = $status' \
    "$PRD_FILE" > "$tmp_file" && mv "$tmp_file" "$PRD_FILE"

  echo "[ralph] Story ${story_id} status → ${new_status}"
}

# Pretty-print a story for dry-run display
print_story() {
  local story_id="$1"
  jq --arg id "$story_id" '.stories[] | select(.id == $id)' "$PRD_FILE"
}

# ─── Core Runner ──────────────────────────────────────────────────────────────

run_story() {
  local story_id="$1"
  local timestamp
  timestamp="$(date +%Y%m%d_%H%M%S)"
  local log_file="${LOGS_DIR}/${timestamp}_${story_id}.log"

  # Validate story exists
  local story_title
  story_title="$(get_story_field "$story_id" "title")"
  if [[ -z "$story_title" ]]; then
    echo "[ralph] ERROR: Story '${story_id}' not found in ${PRD_FILE}" >&2
    return 1
  fi

  local story_status
  story_status="$(get_story_status "$story_id")"

  echo ""
  echo "══════════════════════════════════════════════════════════"
  echo "[ralph] Story:  ${story_id} — ${story_title}"
  echo "[ralph] Status: ${story_status}"
  echo "[ralph] Model:  ${MODEL}"
  echo "[ralph] Log:    ${log_file}"
  echo "══════════════════════════════════════════════════════════"

  # Build the user prompt that Claude will receive (passed as stdin)
  local user_prompt
  user_prompt="$(cat <<EOF
Implement the following story from ralph/prd.json:

$(print_story "$story_id")

Your RALPH_STORY_ID is: ${story_id}
Your RALPH_MODEL is: ${MODEL}
Your RALPH_DRY_RUN is: ${DRY_RUN}

Follow the 5-phase process defined in your system prompt exactly.
At the end, output the RALPH_STATUS line so the run.sh loop can parse it.
EOF
)"

  if [[ "$DRY_RUN" == "true" ]]; then
    echo ""
    echo "[ralph] DRY RUN — would send the following to Claude:"
    echo "────────────────────────────────────────────────────────"
    echo "Model: ${MODEL}"
    echo "System prompt file: ${PROMPT_FILE}"
    echo "Max turns: ${MAX_TURNS}"
    echo ""
    echo "User prompt:"
    echo "$user_prompt"
    echo "────────────────────────────────────────────────────────"
    echo "[ralph] DRY RUN complete. No changes made."
    return 0
  fi

  # Mark story as in-progress
  update_story_status "$story_id" "in-progress"

  # Ensure log directory exists
  mkdir -p "$LOGS_DIR"

  # Run Claude
  echo "[ralph] Starting Claude session..."
  echo ""

  local exit_code=0
  local output=""

  output="$(
    echo "$user_prompt" | claude \
      --print \
      --output-format text \
      --system-prompt-file "$PROMPT_FILE" \
      --max-turns "$MAX_TURNS" \
      --model "$MODEL" \
      --dangerously-skip-permissions \
      2>&1
  )" || exit_code=$?

  # Write full output to log
  {
    echo "═══ RALPH SESSION LOG ═══"
    echo "Story:     ${story_id}"
    echo "Title:     ${story_title}"
    echo "Model:     ${MODEL}"
    echo "Started:   ${timestamp}"
    echo "Completed: $(date +%Y%m%d_%H%M%S)"
    echo "Exit code: ${exit_code}"
    echo "═════════════════════════"
    echo ""
    echo "$output"
  } > "$log_file"

  echo "$output"

  # Parse RALPH_STATUS from output
  local ralph_status=""
  ralph_status="$(echo "$output" | grep -o 'RALPH_STATUS:[[:space:]]*\(SUCCESS\|FAILED\)' | head -1 | sed 's/RALPH_STATUS:[[:space:]]*//' || true)"

  if [[ "$ralph_status" == "SUCCESS" ]]; then
    update_story_status "$story_id" "done"
    echo ""
    echo "[ralph] ✓ Story ${story_id} completed successfully."
    echo "[ralph] Log: ${log_file}"
    return 0
  elif [[ "$ralph_status" == "FAILED" ]]; then
    update_story_status "$story_id" "failed"
    echo ""
    echo "[ralph] ✗ Story ${story_id} failed. Check the log: ${log_file}"
    return 1
  else
    # Claude exited without a RALPH_STATUS line
    update_story_status "$story_id" "failed"
    echo ""
    echo "[ralph] ✗ Story ${story_id}: No RALPH_STATUS found in output (exit code: ${exit_code})."
    echo "[ralph] Log: ${log_file}"
    return 1
  fi
}

# ─── Main Loop ────────────────────────────────────────────────────────────────

main() {
  if [[ "$DRY_RUN" != "true" ]]; then
    check_deps
  else
    # For dry-run, only check jq
    if ! command -v jq &>/dev/null; then
      echo "[ralph] ERROR: jq is required. Install: brew install jq / apt install jq" >&2
      exit 1
    fi
  fi

  if [[ ! -f "$PRD_FILE" ]]; then
    echo "[ralph] ERROR: prd.json not found at ${PRD_FILE}" >&2
    exit 1
  fi

  if [[ ! -f "$PROMPT_FILE" ]]; then
    echo "[ralph] ERROR: prompt.md not found at ${PROMPT_FILE}" >&2
    exit 1
  fi

  echo "[ralph] Starting Ralph loop"
  echo "[ralph] PRD:  ${PRD_FILE}"
  echo "[ralph] Mode: $([ "$DRY_RUN" = "true" ] && echo "DRY RUN" || echo "LIVE")"

  local processed=0
  local failed=0

  if [[ -n "$TARGET_STORY" ]]; then
    # Run a specific story
    local status
    status="$(get_story_status "$TARGET_STORY" 2>/dev/null || echo "not_found")"
    if [[ "$status" == "not_found" ]] || [[ -z "$status" ]]; then
      echo "[ralph] ERROR: Story '${TARGET_STORY}' not found." >&2
      exit 1
    fi
    if [[ "$status" == "done" ]] || [[ "$status" == "in-progress" ]]; then
      echo "[ralph] Story '${TARGET_STORY}' has status '${status}'. Use --force to re-run (not implemented)." >&2
      exit 1
    fi
    if run_story "$TARGET_STORY"; then
      processed=$((processed + 1))
    else
      failed=$((failed + 1))
    fi
  else
    # Loop through pending stories
    while true; do
      local next_id
      next_id="$(get_next_story_id)"

      if [[ -z "$next_id" ]]; then
        echo ""
        echo "[ralph] No more pending stories."
        break
      fi

      if run_story "$next_id"; then
        processed=$((processed + 1))
      else
        failed=$((failed + 1))
      fi

      if [[ "$ONCE" == "true" ]]; then
        echo "[ralph] --once flag set. Stopping after one story."
        break
      fi

      # Brief pause between stories to avoid hammering APIs
      sleep 2
    done
  fi

  echo ""
  echo "══════════════════════════════════════════════════════════"
  echo "[ralph] Done. Processed: ${processed}, Failed: ${failed}"
  echo "══════════════════════════════════════════════════════════"

  if [[ "$failed" -gt 0 ]]; then
    exit 1
  fi
}

main "$@"
