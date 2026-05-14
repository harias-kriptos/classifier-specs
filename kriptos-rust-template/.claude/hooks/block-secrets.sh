#!/usr/bin/env bash
# .claude/hooks/block-secrets.sh
# Blocks Write/Edit/MultiEdit when the proposed content contains likely secrets.
# Operates on stdin (Claude Code hook protocol). Exits 2 with a JSON decision payload
# when a forbidden pattern is matched, otherwise exits 0.

set -euo pipefail

INPUT=$(cat)

# Extract candidate content fields (Write tool: file_text; Edit/MultiEdit: new_str / edits[].new_string)
CONTENT=$(echo "$INPUT" | jq -r '
  [
    .tool_input.file_text       // empty,
    .tool_input.new_str         // empty,
    (.tool_input.edits // [] | map(.new_string) | .[])
  ] | join("\n")
')

# Also check the target path — refuse edits to known-secret files even if content looks clean.
TARGET=$(echo "$INPUT" | jq -r '.tool_input.file_path // .tool_input.path // ""')

case "$TARGET" in
  *".env"|*".env.local"|*".env."*".local"|*".pem"|*".key"|*"id_rsa"*|*"id_ed25519"*)
    echo "{\"decision\":\"block\",\"reason\":\"Refusing to edit a path that typically holds secrets: '$TARGET'. If this is intentional, edit it manually outside Claude Code.\"}" >&2
    exit 2
    ;;
esac

# Patterns that flag obvious leaked credentials. Tuned to avoid false positives on
# documentation strings like "AKIA..." inside markdown code blocks describing the format.
PATTERNS=(
  'AKIA[0-9A-Z]{16}'                        # AWS access key id
  'ASIA[0-9A-Z]{16}'                        # AWS temporary access key id
  'aws_secret_access_key[[:space:]]*=[[:space:]]*[A-Za-z0-9/+=]{40}'
  'AIza[0-9A-Za-z_\-]{35}'                  # Google API key
  'ghp_[0-9A-Za-z]{36}'                     # GitHub personal access token (classic)
  'github_pat_[0-9A-Za-z_]{82}'             # GitHub fine-grained PAT
  'xox[abpsr]-[0-9A-Za-z\-]{10,}'           # Slack tokens
  'sk-ant-api03-[A-Za-z0-9_\-]{93}'         # Anthropic API key
  'sk-[A-Za-z0-9]{48}'                      # OpenAI legacy key
  '-----BEGIN [A-Z ]*PRIVATE KEY-----'      # PEM private key
)

for PATTERN in "${PATTERNS[@]}"; do
  if echo "$CONTENT" | grep -qE "$PATTERN"; then
    REDACTED=$(echo "$PATTERN" | sed 's/[][^$.*+?()|{}\\]//g')
    echo "{\"decision\":\"block\",\"reason\":\"Likely secret detected matching pattern '${REDACTED}'. Move it to an environment variable or AWS Secrets Manager and reference it by name. If this is a documentation example, prefix it with the literal string EXAMPLE_ to bypass the check.\"}" >&2
    exit 2
  fi
done

exit 0
