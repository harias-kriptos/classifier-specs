#!/usr/bin/env bash
# .claude/hooks/block-dangerous-commands.sh
# Reads the Bash tool input from stdin and blocks known-dangerous patterns.

set -euo pipefail

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // ""')

# Patterns that are always blocked
BLOCKED_PATTERNS=(
  "rm -rf[[:space:]]+(\/|~|\$HOME|\.\.)"   # destructive rm
  "git push --force"                        # force push
  "git push -f"
  "curl .* \| bash"                         # remote code execution
  "wget .* \| bash"
  ":\(\)\{ :\|:& \};:"                      # fork bomb
)

for PATTERN in "${BLOCKED_PATTERNS[@]}"; do
  if echo "$COMMAND" | grep -qE "$PATTERN"; then
    echo "{\"decision\":\"block\",\"reason\":\"Blocked command pattern: '$PATTERN'. This command is not allowed in automated sessions.\"}" >&2
    exit 2
  fi
done

exit 0
