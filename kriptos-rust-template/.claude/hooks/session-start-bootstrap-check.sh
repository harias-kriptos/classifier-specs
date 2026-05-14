#!/usr/bin/env bash
# .claude/hooks/session-start-bootstrap-check.sh
#
# Runs once per Claude Code session (matcher: SessionStart). Detects whether
# this repo is bootstrapped and whether the superpowers plugin is installed,
# and emits additionalContext that steers Claude toward the right first action.
#
# Language-agnostic: "has source code" means at least one non-test, non-config
# file under src/. Adjust SOURCE_GLOBS below if your project uses a different
# layout.
#
# Output protocol: a single JSON object on stdout with {"hookSpecificOutput":
# {"hookEventName":"SessionStart","additionalContext":"..."}}. Empty output
# is also valid and means "no extra context".
#
# Non-blocking: never exits non-zero on bootstrap state (only on its own
# malfunction). Steering happens via context, not via refusal.

set -euo pipefail

cd "$CLAUDE_PROJECT_DIR" || exit 0

# ----- detection ------------------------------------------------------------

bootstrapped="no"
if [ -d specs ]; then
  if find specs -maxdepth 1 -name '*.md' -not -name 'SPEC_TEMPLATE.md' \
       -not -empty 2>/dev/null | grep -q .; then
    bootstrapped="yes"
  fi
fi

# "has_src" = any file under src/ (any extension) excluding common test markers
has_src="no"
if [ -d src ] && find src -type f \
     -not -name '*_test.*' \
     -not -name 'test_*' \
     -not -path '*/tests/*' \
     2>/dev/null | grep -q .; then
  has_src="yes"
fi

has_tests="no"
if [ -d tests ] && find tests -type f 2>/dev/null | grep -q .; then
  has_tests="yes"
fi

# superpowers detection: try `claude plugin list`, fall back to "unknown" when
# the CLI is not on PATH (CI runners, devcontainers without the CLI installed).
superpowers="unknown"
if command -v claude >/dev/null 2>&1; then
  if claude plugin list 2>/dev/null | grep -qi 'superpowers'; then
    superpowers="installed"
  else
    superpowers="missing"
  fi
fi

# ----- message composition --------------------------------------------------

msg=""

if [ "$bootstrapped" = "yes" ] && [ "$has_src" = "yes" ]; then
  spec_count=$(find specs -maxdepth 1 -name '*.md' -not -name 'SPEC_TEMPLATE.md' 2>/dev/null | wc -l | tr -d ' ')
  msg="Repo state check: bootstrapped (specs/ has ${spec_count} spec(s), src/ present, tests/=$has_tests). Proceed normally against the latest spec. Reminder: every code change must trace to a failing test commit per CLAUDE.md."

elif [ "$bootstrapped" = "no" ] && [ "$superpowers" = "installed" ]; then
  msg="Repo state check: PRE-BOOTSTRAP and superpowers is installed. Your first action this session must be to bootstrap the project before any feature work. Run, in order: (1) /superpowers:brainstorming to design the first vertical slice with the user, using CLAUDE.md as context; (2) /superpowers:writing-plans to break that design into specs/001-*.md + todo.md; (3) only after specs/001-*.md exists, start the RED-GREEN-REFACTOR cycle. Do NOT skip to implementation, even if the user asks for it directly — push back and explain the bootstrap requirement."

elif [ "$bootstrapped" = "no" ] && [ "$superpowers" = "missing" ]; then
  msg="Repo state check: PRE-BOOTSTRAP and superpowers is NOT installed. Two paths forward, in priority order: (1) tell the user to install superpowers with 'claude plugin install superpowers@claude-plugins-official' and restart the session — this is the team's standard workflow; OR (2) if the user confirms they want to proceed without superpowers, run './scripts/bootstrap.sh' which generates a minimal specs/001-stub.md + src/ skeleton + tests/ scaffolding so the rest of the workflow can run. Do NOT skip to implementation. Ask the user which path before doing anything else."

elif [ "$bootstrapped" = "no" ] && [ "$superpowers" = "unknown" ]; then
  msg="Repo state check: PRE-BOOTSTRAP and the claude CLI is not available in this environment, so superpowers status cannot be verified. Assume the team standard (superpowers) is preferred. Ask the user to confirm superpowers is available; if it is, run /superpowers:brainstorming first. If not, fall back to './scripts/bootstrap.sh'. Either way, do not start implementation before specs/001-*.md exists."

elif [ "$bootstrapped" = "yes" ] && [ "$has_src" = "no" ]; then
  msg="Repo state check: specs exist but src/ is empty. The bootstrap is half-done — you have a plan but no code. Pick up at the RED phase: read the latest specs/NNN-*.md, write the first failing test, commit it with 'chore(failing): <behavior>', then implement minimally."
fi

if [ -n "$msg" ]; then
  escaped=$(printf '%s' "$msg" | python3 -c 'import json,sys;print(json.dumps(sys.stdin.read()))')
  printf '{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":%s}}\n' "$escaped"
fi

exit 0
