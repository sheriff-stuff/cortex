#!/usr/bin/env bash
# PostToolUse hook: check if TASKS.md was edited and all tasks are done

# Read hook input from stdin
INPUT=$(cat)

# Extract file_path without jq — grep for it in the JSON
FILE_PATH=$(echo "$INPUT" | grep -o '"file_path"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed 's/.*"file_path"[[:space:]]*:[[:space:]]*"//;s/"$//')

# Only care about TASKS.md edits
if [[ "$FILE_PATH" != *"TASKS.md"* ]]; then
  exit 0
fi

# Find TASKS.md relative to the hook script location
TASKS_FILE="$(cd "$(dirname "$0")/../.." && pwd)/TASKS.md"
if [[ ! -f "$TASKS_FILE" ]]; then
  exit 0
fi

# Count pending/in-progress tasks in Backend, Frontend, and QA sections (skip the Legend)
PENDING=$(sed -n '/^## Backend/,/^## Comms Log/p' "$TASKS_FILE" | grep -c -E '^\- \[ \]|^\- \[~\]' || true)

if [[ "$PENDING" -eq 0 ]]; then
  cat <<'HOOK_JSON'
{
  "hookSpecificOutput": {
    "hookEventName": "PostToolUse",
    "additionalContext": "REMINDER: All tasks in TASKS.md appear to be done. Follow the 'When All Tasks Are Done' protocol:\n1. Make sure you created QA tickets under '## QA' in TASKS.md for all testable work you completed.\n2. Review what you changed this session. Check if CLAUDE.md or README.md need updating (new commands, architecture changes, gotchas, dependencies).\n3. If updates are needed, enter plan mode and propose the specific edits. Do NOT write them directly — wait for user approval.\n4. Tell the user you are done and what you propose to update."
  }
}
HOOK_JSON
fi
